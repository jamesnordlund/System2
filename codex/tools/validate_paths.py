#!/usr/bin/env python3
"""
validate_paths.py - Codex runtime file path validator for System2

Usage:
    python3 codex/tools/validate_paths.py <allowlist.regex> <path1> [path2 ...]

Exit codes:
    0 - all paths allowed
    1 - usage or internal error
    2 - one or more paths blocked
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable, List


def normalize_path(raw: str, cwd: Path) -> str:
    """Return a normalized relative POSIX path for regex checks."""
    path = Path(raw)
    if path.is_absolute():
        try:
            path = path.relative_to(cwd)
        except ValueError:
            # Keep absolute path when outside cwd so allowlists can reject it.
            return path.as_posix()
    normalized = path.as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def load_patterns(pattern_file: Path) -> List[re.Pattern]:
    patterns: List[re.Pattern] = []
    for line in pattern_file.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(re.compile(stripped))
    return patterns


def is_allowed(path: str, patterns: Iterable[re.Pattern]) -> bool:
    return any(pat.fullmatch(path) for pat in patterns)


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: validate_paths.py <allowlist.regex> <path1> [path2 ...]", file=sys.stderr)
        return 1

    pattern_file = Path(sys.argv[1])
    if not pattern_file.is_file():
        print(f"Pattern file not found: {pattern_file}", file=sys.stderr)
        return 1

    try:
        patterns = load_patterns(pattern_file)
    except re.error as exc:
        print(f"Invalid regex in {pattern_file}: {exc}", file=sys.stderr)
        return 1

    if not patterns:
        print(f"No patterns found in {pattern_file}", file=sys.stderr)
        return 1

    cwd = Path.cwd().resolve()
    blocked: List[str] = []

    for raw in sys.argv[2:]:
        norm = normalize_path(raw, cwd)
        if not is_allowed(norm, patterns):
            blocked.append(norm)

    if blocked:
        print("Blocked paths:")
        for path in blocked:
            print(f"  - {path}")
        return 2

    print("All paths allowed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
