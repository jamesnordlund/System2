#!/usr/bin/env python3
"""Advisory boundary enforcement — warns when edits cross module boundaries."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hook_utils import get_tool_input, log_warn

HOOK_NAME = "boundary-check"
BOUNDARIES_FILE = "spec/module-boundaries.json"


def find_boundaries_file() -> str | None:
    candidate = os.path.join(os.getcwd(), BOUNDARIES_FILE)
    return candidate if os.path.isfile(candidate) else None


def load_boundaries(path: str) -> list | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log_warn(HOOK_NAME, f"failed to parse {BOUNDARIES_FILE}: {exc}")
        return None

    if not isinstance(data, dict):
        log_warn(HOOK_NAME, f"{BOUNDARIES_FILE} is not a JSON object")
        return None

    boundaries = data.get("boundaries")
    if not isinstance(boundaries, list):
        log_warn(HOOK_NAME, f"{BOUNDARIES_FILE} missing 'boundaries' array")
        return None

    return boundaries


def find_module(file_path: str, boundaries: list) -> dict | None:
    """Return the boundary dict for the longest-prefix-matching module."""
    best_match = None
    best_length = 0
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            continue
        module_prefix = boundary.get("module", "")
        if not module_prefix:
            continue
        if file_path.startswith(module_prefix) and len(module_prefix) > best_length:
            best_match = boundary
            best_length = len(module_prefix)
    return best_match


def normalize_file_path(path: str) -> str:
    """Collapse absolute/relative to a plain relative path for prefix matching."""
    if os.path.isabs(path):
        try:
            path = os.path.relpath(path, os.getcwd())
        except ValueError:
            pass
    if path.startswith("./"):
        path = path[2:]
    return path


def check_boundary_context(file_path: str, boundaries: list) -> str | None:
    """Return an advisory warning if the file's module has forbidden imports, else None."""
    module = find_module(file_path, boundaries)
    if module is None:
        return None

    forbidden = module.get("forbidden_imports_from")
    if not isinstance(forbidden, list) or not forbidden:
        return None

    module_prefix = module.get("module", "")
    return (
        f"File '{file_path}' is in module '{module_prefix}' which declares "
        f"forbidden imports from: {forbidden}."
    )


def main() -> int:
    boundaries_path = find_boundaries_file()
    if boundaries_path is None:
        return 0

    boundaries = load_boundaries(boundaries_path)
    if boundaries is None:
        return 0

    payload = get_tool_input()
    if payload is None:
        return 0
    file_path = payload.get("file_path")
    if file_path is None:
        return 0

    file_path = normalize_file_path(file_path)

    warning = check_boundary_context(file_path, boundaries)
    if warning is not None:
        print(f"[{HOOK_NAME}] WARN: {warning}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
