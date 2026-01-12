# Claude Code Hooks

This directory contains Python hooks for Claude Code that enhance developer safety, code quality, and user experience during agent-assisted development.

## Table of Contents

- [Overview](#overview)
- [Hook Summary](#hook-summary)
- [Installation](#installation)
- [Hook Reference](#hook-reference)
  - [dangerous-command-blocker.py](#dangerous-command-blockerpy)
  - [sensitive-file-protector.py](#sensitive-file-protectorpy)
  - [auto-formatter.py](#auto-formatterpy)
  - [type-checker.py](#type-checkerpy)
  - [tts-notify.py](#tts-notifypy)
  - [validate-file-paths.py](#validate-file-pathspy)
- [Pattern File Format](#pattern-file-format)
- [Enabling Hooks](#enabling-hooks)
- [Troubleshooting](#troubleshooting)

## Overview

Claude Code hooks integrate with lifecycle events to provide automated safety checks, code formatting, type checking, and notifications. Hooks are Python scripts invoked by Claude Code at specific points during tool execution.

**Key principles:**
- PreToolUse hooks can block operations (exit code 2)
- PostToolUse hooks are informational only (always exit 0)
- Stop hooks run at session completion (always exit 0)
- All hooks are opt-in and must be explicitly configured

## Hook Summary

| Hook | Trigger | Purpose | Exit Codes |
|------|---------|---------|------------|
| `dangerous-command-blocker.py` | PreToolUse (Bash) | Block destructive shell commands | 0=allow, 1=error, 2=block |
| `sensitive-file-protector.py` | PreToolUse (Read\|Edit\|Write\|Bash) | Protect credentials and secrets | 0=allow, 1=error, 2=block |
| `auto-formatter.py` | PostToolUse (Edit\|Write) | Auto-format modified files | 0 (always) |
| `type-checker.py` | PostToolUse (Edit\|Write) | Run type checkers on modified files | 0 (always) |
| `tts-notify.py` | Stop, SubagentStop | Announce task completion audibly | 0 (always) |
| `validate-file-paths.py` | PreToolUse (any) | Validate file paths against allowlist | 0=allowed, 1=blocked |

## Installation

No external dependencies required. All hooks use Python 3.8+ standard library only.

```bash
# Verify hooks are executable
chmod +x scripts/claude-hooks/*.py

# Test syntax
for f in scripts/claude-hooks/*.py; do python3 -m py_compile "$f"; done
```

---

## Hook Reference

### dangerous-command-blocker.py

Blocks dangerous Bash commands that could cause data loss or system damage.

**Trigger:** PreToolUse (Bash)

**Usage:**
```
python3 dangerous-command-blocker.py [allowlist-file]
```

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `TOOL_NAME` | Must be "Bash" |
| `TOOL_INPUT` | JSON object with `{"command": "..."}` |

**CLI Arguments:**
| Argument | Required | Description |
|----------|----------|-------------|
| `allowlist-file` | No | Path to regex file for user-defined exceptions |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Command allowed |
| 1 | Parse error or missing input (implicit block) |
| 2 | Command blocked (stdout contains JSON reason) |

**Blocked Patterns:**
- `rm -rf /` or `rm -rf /*` (root filesystem)
- `rm -rf .` (current directory)
- `sudo rm -rf` (any path with elevated privileges)
- `chmod 777` (world-writable permissions)
- `git reset --hard` (discards uncommitted changes)
- `git push --force` to main/master (including `--force-with-lease`)
- `DROP TABLE` (SQL table deletion)
- `DELETE FROM` without WHERE clause (SQL mass deletion)

**Echo/Print Exclusion:** Commands like `echo "rm -rf /"` are allowed since they only print text.

**Configuration Example:**
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/dangerous-command-blocker.py"
```

With allowlist:
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/dangerous-command-blocker.py .claude/hooks/dangerous-commands-allowlist.regex"
```

---

### sensitive-file-protector.py

Blocks access to credential and secret files to prevent accidental exposure.

**Trigger:** PreToolUse (Read, Edit, Write, Bash)

**Usage:**
```
python3 sensitive-file-protector.py [patterns-file]
```

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `TOOL_NAME` | One of: Read, Edit, Write, Bash |
| `TOOL_INPUT` | JSON with `file_path` or `command` field |

**CLI Arguments:**
| Argument | Required | Description |
|----------|----------|-------------|
| `patterns-file` | No | Path to additional sensitive path patterns |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Access allowed |
| 1 | Parse error or missing input (implicit block) |
| 2 | Access blocked (stdout contains JSON reason) |

**Default Protected Patterns:**
- `.env` and `.env.*` files
- `~/.ssh/` directory
- `~/.aws/` directory
- `~/.gnupg/` directory
- Files containing "credentials" or "secrets" (case-insensitive)
- Key files: `*.pem`, `*.key`, `id_rsa`, `id_ed25519`, `id_ecdsa`
- Auth configs: `.netrc`, `.npmrc`, `.pypirc`

**Path Normalization:**
- Expands `~` to home directory
- Resolves symlinks via `os.path.realpath()`
- Handles relative paths (`./`, `../`)

**Configuration Example:**
```yaml
hooks:
  PreToolUse:
    - matcher: "Read|Edit|Write|Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/sensitive-file-protector.py"
```

With additional patterns:
```yaml
hooks:
  PreToolUse:
    - matcher: "Read|Edit|Write|Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/sensitive-file-protector.py .claude/hooks/sensitive-patterns.regex"
```

---

### auto-formatter.py

Automatically runs code formatters on files after modification.

**Trigger:** PostToolUse (Edit, Write)

**Usage:**
```
python3 auto-formatter.py
```

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `TOOL_NAME` | One of: Edit, Write |
| `TOOL_INPUT` | JSON with `{"file_path": "..."}` |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Always (formatter success, failure, or missing) |

**Supported Formatters:**
| Extension | Formatter | Command |
|-----------|-----------|---------|
| `.js`, `.jsx`, `.ts`, `.tsx` | prettier | `prettier --write` |
| `.json`, `.md`, `.css`, `.html` | prettier | `prettier --write` |
| `.py` | black | `black` |
| `.go` | gofmt | `gofmt -w` |

**Behavior:**
- Detects file extension and selects appropriate formatter
- Checks if formatter is installed via `shutil.which()`
- Logs warning and exits 0 if formatter not found
- Runs formatter with 30-second timeout
- Gracefully handles deleted files
- Forwards formatter stderr to hook stderr

**Configuration Example:**
```yaml
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/auto-formatter.py"
```

---

### type-checker.py

Runs type checkers on modified files and surfaces errors to stderr.

**Trigger:** PostToolUse (Edit, Write)

**Usage:**
```
python3 type-checker.py
```

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `TOOL_NAME` | One of: Edit, Write |
| `TOOL_INPUT` | JSON with `{"file_path": "..."}` |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Always (type errors logged to stderr) |

**Supported Type Checkers:**
| Extension | Checker | Command |
|-----------|---------|---------|
| `.ts`, `.tsx` | tsc | `tsc --noEmit <file>` |
| `.py` | mypy | `mypy <file>` |

**Behavior:**
- Detects file extension and selects appropriate type checker
- Checks if type checker is installed via `shutil.which()`
- Runs type checker on single file with 30-second timeout
- Outputs type errors to stderr (informational only)
- Never blocks - always exits 0

**Configuration Example:**
```yaml
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/auto-formatter.py"  # Format first
        - type: command
          command: "python3 ./scripts/claude-hooks/type-checker.py"    # Then type check
```

---

### tts-notify.py

Announces task completion audibly using platform-specific text-to-speech.

**Trigger:** Stop, SubagentStop

**Usage:**
```
python3 tts-notify.py <stop|subagent>
```

**CLI Arguments:**
| Argument | Required | Description |
|----------|----------|-------------|
| `stop` | Yes (one of) | Speaks "Task complete" |
| `subagent` | Yes (one of) | Speaks "Subagent complete" |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Always (TTS failure is silent) |

**Platform Support:**
| Platform | TTS Command |
|----------|-------------|
| macOS | `say` (built-in) |
| Windows | PowerShell `SpeechSynthesizer` |
| Linux | `espeak` or `spd-say` (if installed) |

**Behavior:**
- Detects platform via `sys.platform`
- Falls back silently if TTS not available
- 10-second timeout for TTS command
- All failures are silent (never outputs errors)

**Configuration Example:**
```yaml
hooks:
  Stop:
    - type: command
      command: "python3 ./scripts/claude-hooks/tts-notify.py stop"
  SubagentStop:
    - type: command
      command: "python3 ./scripts/claude-hooks/tts-notify.py subagent"
```

---

### validate-file-paths.py

Validates file paths in tool input against an allowlist pattern file.

**Trigger:** PreToolUse (any tool with file paths)

**Usage:**
```
python3 validate-file-paths.py <allowlist-file>
```

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `TOOL_INPUT` | JSON containing file path fields |

**CLI Arguments:**
| Argument | Required | Description |
|----------|----------|-------------|
| `allowlist-file` | Yes | Path to regex allowlist file |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | All paths match allowlist |
| 1 | Path not allowed or error |

**Configuration Example:**
```yaml
hooks:
  PreToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/validate-file-paths.py .claude/allowlists/executor.regex"
```

---

## Pattern File Format

Pattern files (allowlists, sensitive patterns) use a simple line-based format:

```
# Comment lines start with #
# Empty lines are ignored
# One regex pattern per line
# Patterns are combined with OR

# Example: allow files in src/ and tests/
^src/.*$
^tests/.*$

# Example: allow specific dangerous commands
^rm -rf \./safe-to-delete-dir$
^git push --force origin hotfix-.*$
```

**Rules:**
- Lines starting with `#` are comments
- Empty lines are ignored
- Each non-comment line is a regex pattern
- Patterns are combined with OR (any match = allow/block)
- Invalid regex causes the hook to exit with error

---

## Enabling Hooks

Hooks can be enabled in two places:

### 1. Agent Frontmatter (`.claude/agents/*.md`)

```yaml
---
name: executor
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/dangerous-command-blocker.py"
    - matcher: "Read|Edit|Write|Bash"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/sensitive-file-protector.py"
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/auto-formatter.py"
        - type: command
          command: "python3 ./scripts/claude-hooks/type-checker.py"
  Stop:
    - type: command
      command: "python3 ./scripts/claude-hooks/tts-notify.py stop"
  SubagentStop:
    - type: command
      command: "python3 ./scripts/claude-hooks/tts-notify.py subagent"
---
```

### 2. Settings File (`.claude/settings.json` or `.claude/settings.local.json`)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/claude-hooks/dangerous-command-blocker.py"
          }
        ]
      }
    ]
  }
}
```

### Matcher Syntax

The `matcher` field uses regex to match tool names:
- `"Bash"` - matches Bash tool only
- `"Read|Edit|Write"` - matches Read, Edit, or Write tools
- `".*"` - matches all tools

### Hook Execution Order

1. All PreToolUse hooks run before tool execution (first block wins)
2. Tool executes if all PreToolUse hooks pass
3. All PostToolUse hooks run after tool completion (in configuration order)

**Recommended Order:** Run `auto-formatter.py` before `type-checker.py` so type checking sees formatted code.

---

## Troubleshooting

### Verify Hooks Are Running

Enable debug logging:
```bash
export CLAUDE_HOOK_DEBUG=1
```

When set, hooks output additional debug information to stderr:
- Full TOOL_INPUT (sanitized)
- Pattern matching details
- Subprocess command and timing

### Check Hook Syntax

```bash
python3 -m py_compile scripts/claude-hooks/dangerous-command-blocker.py
```

### Manual Testing

Test a hook directly with environment variables:

```bash
# Test dangerous command blocker
TOOL_NAME=Bash TOOL_INPUT='{"command":"rm -rf /"}' \
  python3 scripts/claude-hooks/dangerous-command-blocker.py
echo "Exit code: $?"

# Test sensitive file protector
TOOL_NAME=Read TOOL_INPUT='{"file_path":".env"}' \
  python3 scripts/claude-hooks/sensitive-file-protector.py
echo "Exit code: $?"

# Test TTS
python3 scripts/claude-hooks/tts-notify.py stop
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Hook not running | Matcher regex doesn't match tool | Check matcher syntax against tool name |
| "TOOL_INPUT is not set" | Hook invoked outside Claude Code | Set TOOL_INPUT env var for testing |
| Pattern file errors | Invalid regex in pattern file | Validate regex syntax; check for unescaped special chars |
| Formatter not found | Tool not in PATH | Install formatter (`npm i -g prettier`, `pip install black`) |
| Permission denied | Script not executable | Run `chmod +x scripts/claude-hooks/*.py` |
| Import errors | Running from wrong directory | Use absolute path or set PYTHONPATH |

### Log Output Format

All hooks log to stderr with a consistent prefix:

```
[hook-name] LEVEL: message
```

Levels:
- `INFO` - Normal operation
- `WARN` - Non-fatal issues (tool missing, file deleted)
- `ERROR` - Failures affecting functionality

Examples:
```
[dangerous-command-blocker] WARN: Blocked command: rm -rf /...
[auto-formatter] INFO: Running prettier on src/app.ts
[type-checker] WARN: mypy not found in PATH, skipping type check
```

### Block Response Format

When a PreToolUse hook blocks with exit code 2, it outputs JSON to stdout:

```json
{
  "decision": "block",
  "reason": "Blocked: rm -rf / would delete the root filesystem"
}
```

---

## Shared Utilities

The `_hook_utils.py` module provides common functions used by all hooks:

| Function | Description |
|----------|-------------|
| `load_patterns(file_path)` | Load and compile regex patterns from file |
| `collect_paths(value, results)` | Recursively extract file paths from JSON |
| `normalize_path(path)` | Generate path variants (tilde expansion, symlink resolution) |
| `block_response(reason)` | Print JSON block response and exit 2 |
| `log_info/warn/error(hook, msg)` | Log to stderr with hook prefix |
| `get_tool_input()` | Parse TOOL_INPUT env var as JSON |
| `get_tool_name()` | Read TOOL_NAME env var |
| `check_command_exists(cmd)` | Check if command is in PATH |
| `run_subprocess(args, timeout)` | Safe list-based subprocess execution |

---

## Security Considerations

- **No shell execution:** All subprocess calls use `shell=False` to prevent injection
- **Input validation:** TOOL_INPUT is parsed as JSON, never executed
- **Path normalization:** Symlinks resolved to prevent bypass
- **Allowlist approach:** Dangerous patterns are blocked by default; allowlists are opt-in
- **Fail-safe defaults:** PreToolUse hooks block on parse errors (exit 1)
