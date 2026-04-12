#!/usr/bin/env python3
"""
change-budget-reporter.py - Advisory budget reporter for Claude Code

SubagentStop hook that reads .task-budget.json from the repo root
and prints the budgeted limits to stderr for post-execution review.

Always exits 0 (advisory only). If .task-budget.json is absent,
exits silently.

Usage (SubagentStop hook):
    python3 change-budget-reporter.py

Exit codes:
    0 - Always (advisory hook)
"""
from __future__ import annotations

import json
import os
import sys

HOOK_NAME = "change-budget-reporter"
BUDGET_FILE = ".task-budget.json"


def find_budget_file() -> str | None:
    candidate = os.path.join(os.getcwd(), BUDGET_FILE)
    return candidate if os.path.isfile(candidate) else None


def load_budget(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print(f"[{HOOK_NAME}] WARN: {BUDGET_FILE} is not a JSON object", file=sys.stderr)
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[{HOOK_NAME}] WARN: failed to read {BUDGET_FILE}: {exc}", file=sys.stderr)
        return None


def report_budget(budget: dict) -> None:
    lines = [f"[{HOOK_NAME}] Budget constraints for current task:"]

    max_files = budget.get("max_files")
    if max_files is not None:
        lines.append(f"  Max files: {max_files}")

    max_new_symbols = budget.get("max_new_symbols")
    if max_new_symbols is not None:
        lines.append(f"  Max new symbols: {max_new_symbols}")

    interface_policy = budget.get("interface_policy")
    if interface_policy is not None:
        lines.append(f"  Interface policy: {interface_policy}")

    print("\n".join(lines), file=sys.stderr)


def main() -> int:
    budget_path = find_budget_file()
    if budget_path is None:
        return 0

    budget = load_budget(budget_path)
    if budget is None:
        return 0

    report_budget(budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
