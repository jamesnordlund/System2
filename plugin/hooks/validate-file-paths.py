#!/usr/bin/env python3
import json
import os
import re
import sys

PATH_KEYS = {
    "file_path",
    "filepath",
    "path",
    "target_file",
    "filename",
    "file",
}


def load_patterns(file_path: str) -> re.Pattern:
    patterns = []
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            patterns.append(stripped)
    if not patterns:
        print(f"allowlist file has no patterns: {file_path}", file=sys.stderr)
        sys.exit(1)
    if len(patterns) == 1:
        combined = patterns[0]
    else:
        combined = "|".join(f"(?:{pattern})" for pattern in patterns)
    try:
        return re.compile(combined)
    except re.error as exc:
        print(f"invalid allowlist regex: {exc}", file=sys.stderr)
        sys.exit(1)


def collect_paths(value, results):
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and key.lower() in PATH_KEYS:
                results.append(item)
            else:
                collect_paths(item, results)
    elif isinstance(value, list):
        for item in value:
            collect_paths(item, results)


def normalize_candidates(path: str) -> list:
    candidates = [path]
    if path.startswith("./"):
        candidates.append(path[2:])
    if os.path.isabs(path):
        try:
            candidates.append(os.path.relpath(path, os.getcwd()))
        except ValueError:
            pass
    return list(dict.fromkeys(candidates))


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate-file-paths.py <allowlist-file>", file=sys.stderr)
        return 1

    allowlist_file = sys.argv[1]
    pattern = load_patterns(allowlist_file)

    tool_input = os.environ.get("TOOL_INPUT")
    if tool_input is None:
        print("TOOL_INPUT is not set", file=sys.stderr)
        return 1

    try:
        payload = json.loads(tool_input)
    except json.JSONDecodeError as exc:
        print(f"TOOL_INPUT is not valid JSON: {exc}", file=sys.stderr)
        return 1

    paths = []
    if isinstance(payload, str):
        paths.append(payload)
    else:
        collect_paths(payload, paths)

    if not paths:
        print("no file paths found in TOOL_INPUT", file=sys.stderr)
        return 1

    for path in paths:
        if not isinstance(path, str):
            continue
        matched = False
        for candidate in normalize_candidates(path):
            if pattern.match(candidate):
                matched = True
                break
        if not matched:
            print(
                f"file path not allowed: {path} (allowlist: {allowlist_file})",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
