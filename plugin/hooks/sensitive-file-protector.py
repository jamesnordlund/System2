#!/usr/bin/env python3
"""Blocks access to credential and secret files."""
from __future__ import annotations

import os
import re
import shlex
import sys
from typing import Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hook_utils import (
    block_response,
    collect_paths,
    get_tool_input,
    get_tool_name,
    log_info,
    log_warn,
    normalize_path,
)

HOOK_NAME = "sensitive-file-protector"

# Default sensitive file patterns with descriptions
# Each tuple: (pattern, description)
SENSITIVE_PATTERNS: list[Tuple[re.Pattern, str]] = [
    # Environment files
    (re.compile(r"(^|/|\\)\.env$"), "Environment file (.env)"),
    (re.compile(r"(^|/|\\)\.env\.[a-zA-Z0-9_-]+$"), "Environment file (.env.*)"),

    # SSH directory and keys
    (re.compile(r"(^|/|\\)\.ssh(/|\\|$)"), "SSH directory (~/.ssh/)"),

    # Cloud credentials directories
    (re.compile(r"(^|/|\\)\.aws(/|\\|$)"), "AWS credentials directory (~/.aws/)"),
    (re.compile(r"(^|/|\\)\.gnupg(/|\\|$)"), "GPG directory (~/.gnupg/)"),

    # Generic credential/secrets files (case-insensitive)
    (re.compile(r"credentials", re.IGNORECASE), "File containing 'credentials'"),
    (re.compile(r"secrets", re.IGNORECASE), "File containing 'secrets'"),

    # Key files by extension
    (re.compile(r"\.pem$", re.IGNORECASE), "PEM certificate/key file (*.pem)"),
    (re.compile(r"\.key$", re.IGNORECASE), "Key file (*.key)"),

    # SSH private key filenames
    (re.compile(r"(^|/|\\)id_rsa$"), "RSA private key (id_rsa)"),
    (re.compile(r"(^|/|\\)id_ed25519$"), "Ed25519 private key (id_ed25519)"),
    (re.compile(r"(^|/|\\)id_ecdsa$"), "ECDSA private key (id_ecdsa)"),

    # Auth config files
    (re.compile(r"(^|/|\\)\.netrc$"), "Netrc credentials file (.netrc)"),
    (re.compile(r"(^|/|\\)\.npmrc$"), "NPM config file (.npmrc) - may contain tokens"),
    (re.compile(r"(^|/|\\)\.pypirc$"), "PyPI config file (.pypirc) - may contain tokens"),
]


def extract_paths_from_bash_command(command: str) -> list[str]:
    """Extract potential file paths from a Bash command string via shlex."""
    paths: list[str] = []

    try:
        # Use shlex to safely parse the command into tokens
        tokens = shlex.split(command)
    except ValueError:
        # If shlex fails (unclosed quotes, etc.), fall back to simple splitting
        tokens = command.split()

    for token in tokens:
        # Skip flags (start with -)
        if token.startswith("-"):
            continue

        # Check if token looks like a file path
        # - Contains path separator
        # - Starts with ~ (home directory)
        # - Starts with . (relative path or hidden file)
        # - Is a bare filename that matches sensitive patterns
        if ("/" in token or "\\" in token or
                token.startswith("~") or
                token.startswith(".") or
                token.startswith("$")):
            paths.append(token)
        # Also check for bare filenames that might be sensitive
        # e.g., "cat id_rsa" or "vim credentials.json"
        elif any(
            pattern.search(token)
            for pattern, _ in SENSITIVE_PATTERNS
        ):
            paths.append(token)

    return paths


def check_sensitive_path(
    path: str,
    additional_patterns: list[Tuple[re.Pattern, str]] | None = None,
) -> Tuple[bool, str]:
    """Check if a path matches any built-in or additional sensitive pattern."""
    candidates = normalize_path(path)

    all_patterns = list(SENSITIVE_PATTERNS)
    if additional_patterns:
        all_patterns.extend(additional_patterns)

    for candidate in candidates:
        for pattern, description in all_patterns:
            if pattern.search(candidate):
                return (True, description)

    return (False, "")


def load_additional_patterns(file_path: str) -> list[Tuple[re.Pattern, str]] | None:
    """Load additional sensitive patterns from a file. Returns None on failure."""
    try:
        patterns: list[Tuple[re.Pattern, str]] = []
        with open(file_path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                try:
                    compiled = re.compile(stripped)
                    patterns.append((compiled, f"Custom pattern: {stripped}"))
                except re.error as exc:
                    log_warn(HOOK_NAME, f"Invalid regex in patterns file: {stripped} ({exc})")
                    continue

        if patterns:
            return patterns
        return None
    except FileNotFoundError:
        log_warn(HOOK_NAME, f"Patterns file not found: {file_path}")
        return None
    except OSError as exc:
        log_warn(HOOK_NAME, f"Error reading patterns file: {exc}")
        return None


def main() -> int:
    # Parse optional patterns file argument — fail hard if a patterns file
    # was explicitly provided but cannot be loaded, to prevent silent gaps.
    additional_patterns: list[Tuple[re.Pattern, str]] | None = None
    if len(sys.argv) > 1:
        patterns_file = sys.argv[1]
        additional_patterns = load_additional_patterns(patterns_file)
        if additional_patterns is None:
            log_warn(
                HOOK_NAME,
                f"Patterns file provided but could not be loaded: {patterns_file}"
            )
            block_response(
                f"Blocked: sensitive-patterns file could not be loaded ({patterns_file}). "
                "Cannot verify file safety without the custom patterns."
            )
        else:
            log_info(
                HOOK_NAME,
                f"Loaded {len(additional_patterns)} additional patterns from {patterns_file}"
            )

    # Get tool name and input
    tool_name = get_tool_name()
    tool_input = get_tool_input()
    if tool_input is None:
        return 1

    # Extract paths based on tool type
    paths_to_check: list[str] = []

    if tool_name == "Bash":
        # Extract paths from command string
        command = tool_input.get("command", "")
        if command:
            paths_to_check.extend(extract_paths_from_bash_command(command))
    elif tool_name in ("Read", "Edit", "Write"):
        # Extract file_path directly
        file_path = tool_input.get("file_path", "")
        if file_path:
            paths_to_check.append(file_path)
        # Also collect any nested paths
        collected: list[str] = []
        collect_paths(tool_input, collected)
        paths_to_check.extend(collected)
    else:
        # For other tools, try to extract any paths from the input
        collected: list[str] = []
        collect_paths(tool_input, collected)
        paths_to_check.extend(collected)

    # Deduplicate paths while preserving order
    paths_to_check = list(dict.fromkeys(paths_to_check))

    if not paths_to_check:
        # No paths to check, allow the operation
        return 0

    # Check each path against sensitive patterns
    for path in paths_to_check:
        is_sensitive, reason = check_sensitive_path(path, additional_patterns)
        if is_sensitive:
            log_warn(HOOK_NAME, f"Blocked access to sensitive path: {path}")
            block_response(
                f"Blocked: Access to '{path}' is not allowed - {reason}"
            )
            # block_response exits with code 2, so this is unreachable
            return 2

    # All paths are safe
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
