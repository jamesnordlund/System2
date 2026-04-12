#!/usr/bin/env python3
"""Runs code formatters on files after Edit or Write."""
from __future__ import annotations

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hook_utils import (
    get_tool_input,
    log_info,
    log_warn,
    run_subprocess,
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
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()

    if ext_lower not in FORMATTER_MAP:
        return None

    formatter_name, base_args = FORMATTER_MAP[ext_lower]
    # Append the file path to the command arguments
    command_args = base_args + [file_path]
    return (formatter_name, command_args)


def main() -> None:
    payload = get_tool_input()
    if payload is None:
        log_warn(HOOK_NAME, "Could not parse TOOL_INPUT, skipping formatting")
        sys.exit(0)

    file_path = payload.get("file_path")
    if not file_path:
        sys.exit(0)

    if not os.path.exists(file_path):
        log_warn(HOOK_NAME, f"File does not exist (may have been deleted): {file_path}")
        sys.exit(0)

    formatter_result = get_formatter_for_file(file_path)
    if formatter_result is None:
        sys.exit(0)

    formatter_name, command_args = formatter_result

    if not shutil.which(formatter_name):
        log_warn(HOOK_NAME, f"{formatter_name} not found in PATH, skipping formatting for {file_path}")
        sys.exit(0)

    log_info(HOOK_NAME, f"Running {formatter_name} on {file_path}")

    returncode, stdout, stderr = run_subprocess(command_args)
    if stderr:
        print(stderr, file=sys.stderr, end="")
    if returncode == -1 and "timed out" in stderr.lower():
        log_warn(HOOK_NAME, f"{formatter_name} timed out after 30s")

    sys.exit(0)


if __name__ == "__main__":
    main()
