#!/usr/bin/env python3
"""Shared utilities for Claude Code hooks."""
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
    """Load regex patterns from a file (one per line, # comments, blank lines ignored).

    Raises SystemExit if file has no patterns or contains invalid regex.
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
    """Recursively extract file paths from a JSON structure."""
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
    """Return deduplicated path variations (tilde, symlink, relative/absolute)."""
    candidates: list[str] = [path]

    if path.startswith("./"):
        candidates.append(path[2:])

    if os.path.isabs(path):
        try:
            candidates.append(os.path.relpath(path, os.getcwd()))
        except ValueError:
            pass

    if path.startswith("~"):
        expanded = os.path.expanduser(path)
        candidates.append(expanded)
        try:
            candidates.append(os.path.relpath(expanded, os.getcwd()))
        except ValueError:
            pass

    try:
        real_path = os.path.realpath(path)
        if real_path != path:
            candidates.append(real_path)
    except OSError:
        pass

    return list(dict.fromkeys(candidates))


def block_response(reason: str) -> None:
    """Print a JSON block response to stdout and exit with code 2."""
    response = {"decision": "block", "reason": reason}
    print(json.dumps(response))
    sys.exit(2)


def log_info(hook_name: str, message: str) -> None:
    print(f"[{hook_name}] INFO: {message}", file=sys.stderr)


def log_warn(hook_name: str, message: str) -> None:
    print(f"[{hook_name}] WARN: {message}", file=sys.stderr)


def log_error(hook_name: str, message: str) -> None:
    print(f"[{hook_name}] ERROR: {message}", file=sys.stderr)


def get_tool_input() -> dict | None:
    """Parse TOOL_INPUT env var as JSON. Returns None on missing/invalid input."""
    tool_input = os.environ.get("TOOL_INPUT")
    if tool_input is None:
        print("TOOL_INPUT is not set", file=sys.stderr)
        return None

    try:
        payload = json.loads(tool_input)
    except json.JSONDecodeError as exc:
        print(f"TOOL_INPUT is not valid JSON: {exc}", file=sys.stderr)
        return None

    if not isinstance(payload, dict):
        print("TOOL_INPUT must be a JSON object", file=sys.stderr)
        return None

    return payload


def get_tool_name() -> str:
    return os.environ.get("TOOL_NAME", "")


def run_subprocess(
    args: list, timeout: int = 30
) -> tuple[int, str, str]:
    """Execute a subprocess safely. Returns (return_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (-1, "", "Process timed out")
    except FileNotFoundError:
        return (-1, "", f"Command not found: {args[0] if args else 'empty'}")
    except OSError as exc:
        return (-1, "", f"OS error: {exc}")
