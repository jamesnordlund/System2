#!/usr/bin/env python3
"""
sensitive-file-protector.py - Claude Code PreToolUse hook

Blocks access to credential and secret files to prevent accidental exposure of
sensitive data through Read, Edit, Write, or Bash tool operations.

Inspiration: https://github.com/disler/claude-code-damage-control
Hook architecture: https://github.com/anthropics/claude-code/wiki/Hooks
Pattern loading adapted from: validate-file-paths.py in this repository
"""
from __future__ import annotations

import os
import re
import shlex
import sys
from typing import Tuple

# Import shared utilities
try:
    from _hook_utils import (
        get_tool_input,
        get_tool_name,
        load_patterns,
        normalize_path,
        block_response,
        log_info,
        log_warn,
        collect_paths,
    )
except ImportError:
    # Handle case where script is run directly with different import path
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_hook_utils",
        os.path.join(os.path.dirname(__file__), "_hook_utils.py")
    )
    _hook_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_hook_utils)
    get_tool_input = _hook_utils.get_tool_input
    get_tool_name = _hook_utils.get_tool_name
    load_patterns = _hook_utils.load_patterns
    normalize_path = _hook_utils.normalize_path
    block_response = _hook_utils.block_response
    log_info = _hook_utils.log_info
    log_warn = _hook_utils.log_warn
    collect_paths = _hook_utils.collect_paths

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
    """Extract file paths from a Bash command string.

    Uses shell lexical analysis to parse command arguments, then filters
    for strings that look like file paths (contain path separators, ~ or start with .).

    Args:
        command: The Bash command string to analyze.

    Returns:
        List of potential file paths found in the command.
    """
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


def check_sensitive_path(path: str) -> Tuple[bool, str]:
    """Check if a path matches any sensitive file pattern.

    Normalizes the path (expands ~, resolves symlinks) and checks all
    normalized variants against the sensitive patterns.

    Args:
        path: The file path to check.

    Returns:
        Tuple of (is_sensitive, reason). If is_sensitive is True, reason
        contains the description of why the path is sensitive.
    """
    # Get all normalized variants of the path
    candidates = normalize_path(path)

    # Also add resolved real path after tilde expansion
    if path.startswith("~"):
        expanded = os.path.expanduser(path)
        candidates.append(expanded)
        try:
            real_expanded = os.path.realpath(expanded)
            if real_expanded != expanded:
                candidates.append(real_expanded)
        except OSError:
            pass

    # Check each candidate against each pattern
    for candidate in candidates:
        for pattern, description in SENSITIVE_PATTERNS:
            if pattern.search(candidate):
                return (True, description)

    return (False, "")


def check_sensitive_path_with_additional(
    path: str, additional_patterns: list[Tuple[re.Pattern, str]] | None
) -> Tuple[bool, str]:
    """Check if a path matches sensitive patterns including additional ones.

    Args:
        path: The file path to check.
        additional_patterns: Optional list of additional (pattern, description) tuples.

    Returns:
        Tuple of (is_sensitive, reason).
    """
    # First check built-in patterns
    is_sensitive, reason = check_sensitive_path(path)
    if is_sensitive:
        return (is_sensitive, reason)

    # Then check additional patterns if provided
    if additional_patterns:
        candidates = normalize_path(path)
        if path.startswith("~"):
            expanded = os.path.expanduser(path)
            candidates.append(expanded)
            try:
                real_expanded = os.path.realpath(expanded)
                if real_expanded != expanded:
                    candidates.append(real_expanded)
            except OSError:
                pass

        for candidate in candidates:
            for pattern, description in additional_patterns:
                if pattern.search(candidate):
                    return (True, description)

    return (False, "")


def load_additional_patterns(file_path: str) -> list[Tuple[re.Pattern, str]] | None:
    """Load additional sensitive patterns from a file.

    Args:
        file_path: Path to the patterns file.

    Returns:
        List of (compiled_pattern, description) tuples, or None if loading fails.
    """
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
    """Main entry point for the sensitive file protector hook.

    Returns:
        Exit code: 0 to allow, 1 for errors, 2 to block (with JSON on stdout).
    """
    # Parse optional patterns file argument
    additional_patterns: list[Tuple[re.Pattern, str]] | None = None
    if len(sys.argv) > 1:
        patterns_file = sys.argv[1]
        additional_patterns = load_additional_patterns(patterns_file)
        if additional_patterns:
            log_info(
                HOOK_NAME,
                f"Loaded {len(additional_patterns)} additional patterns from {patterns_file}"
            )

    # Get tool name and input
    tool_name = get_tool_name()
    tool_input = get_tool_input()

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
        is_sensitive, reason = check_sensitive_path_with_additional(
            path, additional_patterns
        )
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
