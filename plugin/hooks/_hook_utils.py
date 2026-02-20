#!/usr/bin/env python3
"""
_hook_utils.py - Shared utilities for Claude Code hooks

This module provides common functions used by all Claude Code hooks in this
repository, including pattern loading, path extraction, logging, and subprocess
execution.

Inspiration:
- Hook architecture: https://github.com/anthropics/claude-code/wiki/Hooks
- Pattern loading: validate-file-paths.py in this repository
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any

# Keys that typically contain file paths in TOOL_INPUT JSON
PATH_KEYS = {
    "file_path",
    "filepath",
    "path",
    "target_file",
    "filename",
    "file",
}


def load_patterns(file_path: str) -> re.Pattern:
    """Load and compile regex patterns from a file.

    Adapted from validate-file-paths.py. Reads a file containing one regex
    pattern per line, ignoring empty lines and lines starting with #.
    Combines all patterns with OR and compiles into a single regex.

    Args:
        file_path: Path to the pattern file.

    Returns:
        Compiled regex pattern combining all patterns from the file.

    Raises:
        SystemExit: If file has no patterns or contains invalid regex.
    """
    patterns: list[str] = []
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            patterns.append(stripped)

    if not patterns:
        print(f"pattern file has no patterns: {file_path}", file=sys.stderr)
        sys.exit(1)

    if len(patterns) == 1:
        combined = patterns[0]
    else:
        combined = "|".join(f"(?:{pattern})" for pattern in patterns)

    try:
        return re.compile(combined)
    except re.error as exc:
        print(f"invalid regex in pattern file: {exc}", file=sys.stderr)
        sys.exit(1)


def collect_paths(value: Any, results: list) -> None:
    """Recursively extract file paths from a JSON structure.

    Adapted from validate-file-paths.py. Walks through nested dicts and lists,
    collecting string values from keys that match PATH_KEYS.

    Args:
        value: The JSON value to search (dict, list, or primitive).
        results: List to append found paths to (modified in place).
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and key.lower() in PATH_KEYS:
                results.append(item)
            else:
                collect_paths(item, results)
    elif isinstance(value, list):
        for item in value:
            collect_paths(item, results)


def normalize_path(path: str) -> list[str]:
    """Generate path variations with tilde expansion and symlink resolution.

    Produces multiple candidate paths for pattern matching to handle:
    - Relative vs absolute paths
    - Leading ./
    - Tilde expansion (~)
    - Symlink resolution

    Args:
        path: The original path string.

    Returns:
        List of path variations (deduplicated, order preserved).
    """
    candidates: list[str] = [path]

    # Strip leading ./
    if path.startswith("./"):
        candidates.append(path[2:])

    # Convert absolute to relative
    if os.path.isabs(path):
        try:
            candidates.append(os.path.relpath(path, os.getcwd()))
        except ValueError:
            pass

    # Expand ~ to home directory
    if path.startswith("~"):
        expanded = os.path.expanduser(path)
        candidates.append(expanded)
        # Also add relative from cwd
        try:
            candidates.append(os.path.relpath(expanded, os.getcwd()))
        except ValueError:
            pass

    # Resolve symlinks for real path
    try:
        real_path = os.path.realpath(path)
        if real_path != path:
            candidates.append(real_path)
    except OSError:
        pass

    # Deduplicate while preserving order
    return list(dict.fromkeys(candidates))


def block_response(reason: str) -> None:
    """Print a JSON block response to stdout and exit with code 2.

    This is the standard response format for PreToolUse hooks that want to
    block a tool invocation.

    Args:
        reason: Human-readable explanation for why the tool was blocked.
    """
    response = {"decision": "block", "reason": reason}
    print(json.dumps(response))
    sys.exit(2)


def log_info(hook_name: str, message: str) -> None:
    """Print an info message to stderr with hook prefix.

    Args:
        hook_name: Name of the hook (e.g., "dangerous-command-blocker").
        message: The message to log.
    """
    print(f"[{hook_name}] INFO: {message}", file=sys.stderr)


def log_warn(hook_name: str, message: str) -> None:
    """Print a warning message to stderr with hook prefix.

    Args:
        hook_name: Name of the hook (e.g., "dangerous-command-blocker").
        message: The message to log.
    """
    print(f"[{hook_name}] WARN: {message}", file=sys.stderr)


def log_error(hook_name: str, message: str) -> None:
    """Print an error message to stderr with hook prefix.

    Args:
        hook_name: Name of the hook (e.g., "dangerous-command-blocker").
        message: The message to log.
    """
    print(f"[{hook_name}] ERROR: {message}", file=sys.stderr)


def get_tool_input() -> dict:
    """Parse the TOOL_INPUT environment variable as JSON.

    Returns:
        Parsed JSON as a dictionary.

    Raises:
        SystemExit: If TOOL_INPUT is not set or is not valid JSON.
    """
    tool_input = os.environ.get("TOOL_INPUT")
    if tool_input is None:
        print("TOOL_INPUT is not set", file=sys.stderr)
        sys.exit(1)

    try:
        payload = json.loads(tool_input)
    except json.JSONDecodeError as exc:
        print(f"TOOL_INPUT is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(payload, dict):
        print("TOOL_INPUT must be a JSON object", file=sys.stderr)
        sys.exit(1)

    return payload


def get_tool_name() -> str:
    """Read the TOOL_NAME environment variable.

    Returns:
        The tool name string, or empty string if not set.
    """
    return os.environ.get("TOOL_NAME", "")


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists in PATH.

    Args:
        cmd: The command name to check (e.g., "prettier", "black").

    Returns:
        True if the command is found in PATH, False otherwise.
    """
    return shutil.which(cmd) is not None


def run_subprocess(
    args: list, timeout: int = 30
) -> tuple[int, str, str]:
    """Execute a subprocess safely using list-based invocation.

    This function NEVER uses shell=True to prevent command injection.

    Args:
        args: List of command and arguments (e.g., ["prettier", "--write", "file.js"]).
        timeout: Maximum execution time in seconds (default: 30).

    Returns:
        Tuple of (return_code, stdout, stderr).
        On timeout, returns (-1, "", "Process timed out").
        On other errors, returns (-1, "", error_message).
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,  # Explicitly disable shell to prevent injection
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", "Process timed out")
    except FileNotFoundError:
        return (-1, "", f"Command not found: {args[0] if args else 'empty'}")
    except OSError as exc:
        return (-1, "", f"OS error: {exc}")
