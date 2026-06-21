#!/usr/bin/env bash
#
# deprecation-notice.sh — SessionStart hook.
#
# System2 moved from github.com/jamesnordlund/System2 to
# github.com/DeliberateCode/System2. This old marketplace is frozen. When the
# plugin is loaded from the old location, show the user a one-time notice (per
# machine) nudging them to switch to the new marketplace, and inform Claude so
# it can help if asked.
#
# Emits JSON: `systemMessage` is displayed to the user; `additionalContext`
# (under hookSpecificOutput) is injected into Claude's context.

marker="${HOME}/.claude/.system2-moved-notice"

# Already shown on this machine — stay silent.
if [ -f "$marker" ]; then
  exit 0
fi
mkdir -p "${HOME}/.claude" 2>/dev/null || true
touch "$marker" 2>/dev/null || true

user_msg="⚠️  System2 has moved to https://github.com/DeliberateCode/System2

You installed it from the old location (jamesnordlund/System2), which is now
frozen and will receive no further updates. To switch to the maintained
version, run:

  /plugin marketplace remove system2-marketplace
  /plugin marketplace add DeliberateCode/System2
  /plugin install system2@system2-marketplace"

claude_ctx="NOTE: The System2 plugin is installed from the DEPRECATED marketplace \
jamesnordlund/System2, which is frozen. It has moved to DeliberateCode/System2. \
If the user asks about updating or reinstalling System2, tell them to run: \
'/plugin marketplace remove system2-marketplace' then \
'/plugin marketplace add DeliberateCode/System2' then \
'/plugin install system2@system2-marketplace'."

# Prefer python3 for safe JSON encoding (already a dependency of this plugin's
# hooks). Fall back to a plain stdout notice if python3 is unavailable.
if command -v python3 >/dev/null 2>&1; then
  python3 - "$user_msg" "$claude_ctx" <<'PY'
import json, sys
print(json.dumps({
    "systemMessage": sys.argv[1],
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": sys.argv[2],
    },
}))
PY
else
  printf '%s\n' "$user_msg"
fi

exit 0
