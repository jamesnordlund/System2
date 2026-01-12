#!/usr/bin/env python3
"""
dangerous-command-blocker.py - Claude Code PreToolUse hook

Blocks dangerous Bash commands that could cause data loss or system damage.

Inspiration: https://github.com/RoaringFerrum/claude-code-bash-guardian
Pattern architecture: https://github.com/anthropics/claude-code/wiki/Hooks
Pattern loading adapted from: validate-file-paths.py in this repository
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import Tuple

from _hook_utils import (
    block_response,
    get_tool_input,
    get_tool_name,
    load_patterns,
    log_info,
    log_warn,
)

HOOK_NAME = "dangerous-command-blocker"

# Dangerous command patterns: (compiled_regex, human_readable_reason)
# These patterns are designed to catch destructive commands while minimizing false positives.
# Security note: Patterns cover short flags (-rf), long flags (--recursive --force),
# and separated flags (-r -f) to prevent bypass attempts.

# Helper regex for matching rm with recursive+force flags in various forms:
# - Short combined: -rf, -fr, -rfi, etc.
# - Short separated: -r -f, -f -r, -r ... -f
# - Long flags: --recursive --force, --force --recursive
# - Mixed: -r --force, --recursive -f
_RM_RF_FLAGS = (
    r'('
    r'-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|'  # -rf, -rfi, -fir, etc.
    r'-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*|'  # -fr, -fri, etc.
    r'-r\s+-f|-f\s+-r|'  # -r -f, -f -r (separated)
    r'-[a-zA-Z]*r[a-zA-Z]*\s+-[a-zA-Z]*f[a-zA-Z]*|'  # -ri -f etc.
    r'-[a-zA-Z]*f[a-zA-Z]*\s+-[a-zA-Z]*r[a-zA-Z]*|'  # -fi -r etc.
    r'--recursive\s+--force|--force\s+--recursive|'  # long flags
    r'--recursive\s+-f|-f\s+--recursive|'  # mixed
    r'-r\s+--force|--force\s+-r|'  # mixed
    r'--recursive[^|;&]*-f|-f[^|;&]*--recursive|'  # long + short anywhere
    r'-r[^|;&]*--force|--force[^|;&]*-r'  # short + long anywhere
    r')'
)

DANGER_PATTERNS: list[Tuple[re.Pattern, str]] = [
    # rm -rf with root path (/, /*)
    (
        re.compile(
            r'\brm\s+' + _RM_RF_FLAGS + r'\s*(/|/\*)\s*($|;|\||&)',
            re.MULTILINE,
        ),
        "rm -rf targeting root filesystem (/) is extremely dangerous",
    ),
    # rm -rf with current directory (. or ./)
    (
        re.compile(
            r'\brm\s+' + _RM_RF_FLAGS + r'\s*\./?(?:\s|$|;|\||&)',
            re.MULTILINE,
        ),
        "rm -rf targeting current directory (.) could delete critical files",
    ),
    # rm -rf with parent directory (.. or ../)
    (
        re.compile(
            r'\brm\s+' + _RM_RF_FLAGS + r'\s*\.\./?(?:\s|$|;|\||&)',
            re.MULTILINE,
        ),
        "rm -rf targeting parent directory (..) could delete critical files",
    ),
    # sudo rm -rf (any path) - elevated privilege is always dangerous
    (
        re.compile(
            r'\bsudo\s+rm\s+' + _RM_RF_FLAGS + r'\s+',
            re.MULTILINE,
        ),
        "sudo rm -rf with elevated privileges is extremely dangerous",
    ),
    # chmod 777 (any path) - world-writable and executable
    (
        re.compile(r'\bchmod\s+(.*\s+)?777\s+', re.MULTILINE),
        "chmod 777 makes files world-writable and executable, a security risk",
    ),
    # git reset --hard - loses uncommitted changes
    (
        re.compile(r'\bgit\s+reset\s+--hard\b', re.MULTILINE),
        "git reset --hard discards uncommitted changes permanently",
    ),
    # git push --force / -f to main/master (including --force-with-lease)
    # Pattern covers: git push --force origin main, git push origin main --force, etc.
    (
        re.compile(
            r'\bgit\s+push\s+[^;|&]*--force(-with-lease)?[^;|&]*\b(main|master)\b',
            re.MULTILINE,
        ),
        "git push --force to main/master can destroy shared commit history",
    ),
    (
        re.compile(
            r'\bgit\s+push\s+[^;|&]*\b(main|master)\b[^;|&]*--force(-with-lease)?',
            re.MULTILINE,
        ),
        "git push --force to main/master can destroy shared commit history",
    ),
    (
        re.compile(
            r'\bgit\s+push\s+[^;|&]*-f\s+[^;|&]*\b(main|master)\b',
            re.MULTILINE,
        ),
        "git push -f to main/master can destroy shared commit history",
    ),
    (
        re.compile(
            r'\bgit\s+push\s+[^;|&]*\b(main|master)\b[^;|&]*\s+-f\b',
            re.MULTILINE,
        ),
        "git push -f to main/master can destroy shared commit history",
    ),
    # DROP TABLE (case-insensitive)
    (
        re.compile(r'\bDROP\s+TABLE\b', re.IGNORECASE),
        "DROP TABLE would permanently delete database table and its data",
    ),
    # DELETE FROM without WHERE clause (case-insensitive)
    # Matches DELETE FROM table_name; or DELETE FROM table_name (end of string/command)
    (
        re.compile(
            r'\bDELETE\s+FROM\s+\w+\s*($|;|\|)',
            re.IGNORECASE | re.MULTILINE,
        ),
        "DELETE FROM without WHERE clause would delete all rows in the table",
    ),
]

# Pattern to identify echo/printf statements
ECHO_PRINT_PATTERN = re.compile(r'^[\s]*(echo|printf)\s+', re.MULTILINE)

# Pattern to match quoted strings (single or double quotes)
QUOTED_STRING_PATTERN = re.compile(r'''(["'])(?:(?!\1)[^\\]|\\.)*\1''')


def is_echo_or_print_only(command: str, match_span: Tuple[int, int]) -> bool:
    """Check if a pattern match occurs only within an echo/printf string literal.

    This allows commands like `echo "rm -rf /"` to pass through, since they are
    just printing text, not executing dangerous commands.

    Args:
        command: The full command string.
        match_span: Tuple of (start, end) positions of the dangerous pattern match.

    Returns:
        True if the match is only inside a quoted string following echo/printf.
    """
    match_start, match_end = match_span

    # Find all quoted strings in the command
    quoted_regions: list[Tuple[int, int]] = []
    for quoted_match in QUOTED_STRING_PATTERN.finditer(command):
        quoted_regions.append((quoted_match.start(), quoted_match.end()))

    # Check if the match is entirely within a quoted region
    match_in_quotes = False
    for q_start, q_end in quoted_regions:
        if q_start <= match_start and match_end <= q_end:
            match_in_quotes = True
            break

    if not match_in_quotes:
        return False

    # Check if this is an echo/printf command
    # We need to find if echo/printf appears before the quoted string
    for q_start, q_end in quoted_regions:
        if q_start <= match_start and match_end <= q_end:
            # Look at the part of command before this quoted string
            prefix = command[:q_start]
            # Check if the prefix ends with echo/printf pattern
            # Strip trailing whitespace and check
            prefix_stripped = prefix.rstrip()
            if re.search(r'(echo|printf)\s*$', prefix_stripped):
                return True
    return False


def check_dangerous_pattern(command: str) -> Tuple[bool, str]:
    """Check if a command matches any dangerous patterns.

    Handles piped/chained commands by checking each segment.

    Args:
        command: The Bash command string to check.

    Returns:
        Tuple of (is_dangerous, reason). If not dangerous, reason is empty.
    """
    # Split command by pipes and command separators to check each segment
    # This handles cases like: echo foo | rm -rf /
    # We check the full command first, then individual segments
    segments = re.split(r'[|;&]', command)

    for pattern, reason in DANGER_PATTERNS:
        # Check the full command
        match = pattern.search(command)
        if match:
            if not is_echo_or_print_only(command, match.span()):
                return (True, reason)

        # Also check individual segments (for piped commands)
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            match = pattern.search(segment)
            if match:
                if not is_echo_or_print_only(segment, match.span()):
                    return (True, reason)

    return (False, "")


def main() -> None:
    """Main entry point for the dangerous command blocker hook."""
    parser = argparse.ArgumentParser(
        description="Block dangerous Bash commands in Claude Code"
    )
    parser.add_argument(
        "allowlist",
        nargs="?",
        help="Optional path to a regex allowlist file for user exceptions",
    )
    args = parser.parse_args()

    # Verify we're being invoked for Bash tool
    tool_name = get_tool_name()
    if tool_name != "Bash":
        # Not a Bash command, nothing to check
        sys.exit(0)

    # Parse TOOL_INPUT
    payload = get_tool_input()
    command = payload.get("command", "")

    if not command:
        # No command to check
        sys.exit(0)

    # Load allowlist if provided
    allowlist_pattern: re.Pattern | None = None
    if args.allowlist:
        try:
            allowlist_pattern = load_patterns(args.allowlist)
        except FileNotFoundError:
            log_warn(HOOK_NAME, f"Allowlist file not found: {args.allowlist}")
            # Continue without allowlist
        except SystemExit:
            # load_patterns exits on error, but we want to continue without allowlist
            log_warn(HOOK_NAME, f"Failed to load allowlist: {args.allowlist}")
            allowlist_pattern = None

    # Check allowlist first - if command matches allowlist, allow it
    if allowlist_pattern and allowlist_pattern.search(command):
        log_info(HOOK_NAME, f"Command allowed by allowlist: {command[:50]}...")
        sys.exit(0)

    # Check for dangerous patterns
    is_dangerous, reason = check_dangerous_pattern(command)

    if is_dangerous:
        log_warn(HOOK_NAME, f"Blocked command: {command[:100]}...")
        block_response(f"Blocked: {reason}")
    else:
        # Command is safe
        sys.exit(0)


if __name__ == "__main__":
    main()
