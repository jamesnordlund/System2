#!/usr/bin/env python3
"""
auto-formatter.py - Claude Code PostToolUse hook

Automatically runs code formatters on files after they are modified via Edit or Write tools.
Supports multiple formatters based on file extension with graceful degradation when
formatters are not installed.

Inspiration: https://docs.anthropic.com/en/docs/claude-code/hooks
Pattern inspired by: validate-file-paths.py and _hook_utils.py in this repository
"""
from __future__ import annotations

import os
import subprocess
import sys

# Import shared utilities from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hook_utils import (
    check_command_exists,
    get_tool_input,
    log_info,
    log_warn,
)

HOOK_NAME = "auto-formatter"

# Map file extensions to formatters
# Format: extension -> (formatter_name, command_args)
# command_args should NOT include the file path; it will be appended
FORMATTER_MAP: dict[str, tuple[str, list[str]]] = {
    ".js": ("prettier", ["prettier", "--write"]),
    ".jsx": ("prettier", ["prettier", "--write"]),
    ".ts": ("prettier", ["prettier", "--write"]),
    ".tsx": ("prettier", ["prettier", "--write"]),
    ".json": ("prettier", ["prettier", "--write"]),
    ".md": ("prettier", ["prettier", "--write"]),
    ".css": ("prettier", ["prettier", "--write"]),
    ".html": ("prettier", ["prettier", "--write"]),
    ".py": ("black", ["black"]),
    ".go": ("gofmt", ["gofmt", "-w"]),
}


def get_formatter_for_file(file_path: str) -> tuple[str, list[str]] | None:
    """Determine the appropriate formatter for a file based on its extension.

    Args:
        file_path: Path to the file being formatted.

    Returns:
        Tuple of (formatter_name, command_args) where command_args includes
        the file path appended, or None if no formatter matches.
    """
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()

    if ext_lower not in FORMATTER_MAP:
        return None

    formatter_name, base_args = FORMATTER_MAP[ext_lower]
    # Append the file path to the command arguments
    command_args = base_args + [file_path]
    return (formatter_name, command_args)


def main() -> None:
    """Main entry point for the auto-formatter hook.

    Parses TOOL_INPUT to extract the file path, determines the appropriate
    formatter, and runs it if installed. Always exits with code 0.
    """
    # Parse TOOL_INPUT to get the file path
    payload = get_tool_input()
    file_path = payload.get("file_path")

    if not file_path:
        # No file_path in input, nothing to format
        sys.exit(0)

    # Check if file exists (may have been deleted after Edit/Write)
    if not os.path.exists(file_path):
        log_warn(HOOK_NAME, f"File does not exist (may have been deleted): {file_path}")
        sys.exit(0)

    # Determine formatter for this file type
    formatter_result = get_formatter_for_file(file_path)
    if formatter_result is None:
        # No formatter for this extension, silently exit
        sys.exit(0)

    formatter_name, command_args = formatter_result

    # Check if formatter is installed
    if not check_command_exists(formatter_name):
        log_warn(HOOK_NAME, f"{formatter_name} not found in PATH, skipping formatting for {file_path}")
        sys.exit(0)

    # Log what we're doing
    log_info(HOOK_NAME, f"Running {formatter_name} on {file_path}")

    # Run the formatter with timeout
    try:
        result = subprocess.run(
            command_args,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,  # Explicitly disable shell to prevent injection
        )

        # Forward stderr to hook stderr if there's any output
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")

    except subprocess.TimeoutExpired as exc:
        # Kill the process if it times out
        if exc.args and hasattr(exc, "cmd"):
            log_warn(HOOK_NAME, f"{formatter_name} timed out after 30s, killing process")
        else:
            log_warn(HOOK_NAME, f"{formatter_name} timed out after 30s")
        # Process is already terminated by subprocess.run on timeout
        sys.exit(0)

    except FileNotFoundError:
        log_warn(HOOK_NAME, f"{formatter_name} not found: {command_args[0]}")
        sys.exit(0)

    except OSError as exc:
        log_warn(HOOK_NAME, f"OS error running {formatter_name}: {exc}")
        sys.exit(0)

    # Always exit 0 regardless of formatter outcome
    sys.exit(0)


if __name__ == "__main__":
    main()
