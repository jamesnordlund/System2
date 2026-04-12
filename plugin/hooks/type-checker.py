#!/usr/bin/env python3
"""Runs type checkers on modified files and surfaces errors to stderr."""
from __future__ import annotations

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hook_utils import (
    get_tool_input,
    log_error,
    log_info,
    log_warn,
    run_subprocess,
)

HOOK_NAME = "type-checker"

# Map file extensions to type checkers
# Each entry is: extension -> (checker_command, additional_args)
TYPE_CHECKER_MAP: dict[str, tuple[str, list[str]]] = {
    ".ts": ("tsc", ["--noEmit"]),
    ".tsx": ("tsc", ["--noEmit"]),
    ".py": ("mypy", []),
}

# Timeout for type checker execution in seconds
TYPE_CHECK_TIMEOUT = 30


def get_type_checker_for_file(file_path: str) -> tuple[str, list[str]] | None:
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()

    if ext_lower in TYPE_CHECKER_MAP:
        checker_cmd, extra_args = TYPE_CHECKER_MAP[ext_lower]
        # Build full command args: [checker, extra_args..., file_path]
        command_args = [checker_cmd] + extra_args + [file_path]
        return (checker_cmd, command_args)

    return None


def main() -> int:
    payload = get_tool_input()
    if payload is None:
        log_warn(HOOK_NAME, "Could not parse TOOL_INPUT")
        return 0

    file_path = payload.get("file_path")
    if not file_path:
        return 0

    checker_result = get_type_checker_for_file(file_path)
    if checker_result is None:
        return 0

    checker_name, command_args = checker_result

    if not shutil.which(checker_name):
        log_warn(HOOK_NAME, f"{checker_name} not found in PATH, skipping type check")
        return 0

    # Run type checker
    log_info(HOOK_NAME, f"Running {checker_name} on {file_path}")

    returncode, stdout, stderr = run_subprocess(command_args, timeout=TYPE_CHECK_TIMEOUT)

    # Handle timeout
    if returncode == -1 and "timed out" in stderr.lower():
        log_warn(HOOK_NAME, f"{checker_name} timed out after {TYPE_CHECK_TIMEOUT}s")
        return 0

    # Handle other subprocess errors
    if returncode == -1:
        log_error(HOOK_NAME, f"Failed to run {checker_name}: {stderr}")
        return 0

    # Print type checker output to stderr (both stdout and stderr from the checker)
    # Type checkers may output errors to either stream
    if stdout:
        print(stdout, file=sys.stderr, end="")
    if stderr:
        print(stderr, file=sys.stderr, end="")

    # Log summary
    if returncode == 0:
        log_info(HOOK_NAME, f"{checker_name} completed with no errors")
    else:
        log_warn(HOOK_NAME, f"{checker_name} found type errors (exit code {returncode})")

    # Always exit 0 - this is informational only
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
