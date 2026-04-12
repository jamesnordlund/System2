#!/usr/bin/env python3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _hook_utils import collect_paths, load_patterns, normalize_path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate-file-paths.py <allowlist-file>", file=sys.stderr)
        return 1

    allowlist_file = sys.argv[1]
    pattern = load_patterns(allowlist_file)

    # Check for task-lease file in the same directory as the primary allowlist.
    # Fail open: if the lease file is malformed, log a warning and proceed
    # without lease enforcement. The lease is a scope restriction, not a
    # security boundary — the allowlist still enforces file-level security.
    lease_file = os.path.join(os.path.dirname(allowlist_file), ".task-lease.regex")
    lease_pattern = None
    if os.path.isfile(lease_file):
        try:
            lease_pattern = load_patterns(lease_file)
        except SystemExit:
            print(
                f"WARN: task-lease file could not be loaded: {lease_file}, proceeding without lease",
                file=sys.stderr,
            )
            lease_pattern = None

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
        allowlist_ok = False
        lease_ok = False
        # Break only when a candidate passes both gates; a candidate that
        # matches the allowlist but not the lease keeps searching for a
        # normalized form that satisfies both.
        for candidate in normalize_path(path):
            if pattern.match(candidate):
                allowlist_ok = True
                if lease_pattern is None or lease_pattern.match(candidate):
                    lease_ok = True
                    break
        if not allowlist_ok:
            print(
                f"file path not allowed: {path} (allowlist: {allowlist_file})",
                file=sys.stderr,
            )
            return 1
        if not lease_ok:
            print(
                f"file path blocked by task lease: {path} (lease: {lease_file})",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
