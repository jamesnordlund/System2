# Example Hook Configurations

This document provides examples of how to configure the Claude Code hooks
in your project. Hooks can be configured in two places:

1. **`.claude/settings.json`** - Project-wide settings
2. **Agent frontmatter in `.claude/agents/*.md`** - Per-agent settings

## Important Notes

- Hooks are **opt-in** and must be explicitly configured
- PreToolUse hooks can block tool execution (exit code 2)
- PostToolUse hooks cannot block and should always exit 0
- Stop/SubagentStop hooks run at session completion

---

## Configuration in `.claude/settings.json`

Add hooks to your settings.json file to enable them project-wide:

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
      },
      {
        "matcher": "Read|Edit|Write|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/claude-hooks/sensitive-file-protector.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/claude-hooks/auto-formatter.py"
          },
          {
            "type": "command",
            "command": "python3 ./scripts/claude-hooks/type-checker.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "python3 ./scripts/claude-hooks/tts-notify.py stop"
      }
    ],
    "SubagentStop": [
      {
        "type": "command",
        "command": "python3 ./scripts/claude-hooks/tts-notify.py subagent"
      }
    ]
  }
}
```

### With Custom Pattern Files

To use custom allowlist or additional patterns files:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/claude-hooks/dangerous-command-blocker.py .claude/hooks/dangerous-commands-allowlist.regex"
          }
        ]
      },
      {
        "matcher": "Read|Edit|Write|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ./scripts/claude-hooks/sensitive-file-protector.py .claude/hooks/sensitive-patterns.regex"
          }
        ]
      }
    ]
  }
}
```

---

## Configuration in Agent Frontmatter

Add hooks to the YAML frontmatter of agent definition files:

```yaml
---
name: executor
description: Implements approved tasks with verification
tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Bash
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

---

## Hook Execution Order

When multiple hooks are configured for the same event:

1. **PreToolUse**: Hooks run sequentially; first block wins
2. **PostToolUse**: Hooks run sequentially; all run regardless of exit code
3. **Stop/SubagentStop**: All hooks run

For PostToolUse, ordering matters:
- Auto-formatter should run BEFORE type-checker
- This ensures type-checking is done on formatted code

---

## Environment Variables

Hooks receive context via environment variables:

| Variable | Description | Available In |
|----------|-------------|--------------|
| `TOOL_NAME` | Name of the tool (Bash, Read, Edit, Write) | PreToolUse, PostToolUse |
| `TOOL_INPUT` | JSON string with tool arguments | PreToolUse, PostToolUse |
| `TOOL_OUTPUT` | JSON string with tool result | PostToolUse only |

### Example TOOL_INPUT values

**Bash tool:**
```json
{"command": "ls -la"}
```

**Read tool:**
```json
{"file_path": "/path/to/file.txt"}
```

**Edit tool:**
```json
{"file_path": "/path/to/file.txt", "old_string": "...", "new_string": "..."}
```

**Write tool:**
```json
{"file_path": "/path/to/file.txt", "content": "..."}
```

---

## Exit Codes

### PreToolUse Hooks (DCB, SFP)

| Exit Code | Meaning |
|-----------|---------|
| 0 | Allow the tool to execute |
| 1 | Error occurred (implicit block) |
| 2 | Block with reason (stdout contains JSON) |

When blocking, output JSON to stdout:
```json
{"decision": "block", "reason": "Command blocked: rm -rf / is dangerous"}
```

### PostToolUse Hooks (AFM, TYC)

| Exit Code | Meaning |
|-----------|---------|
| 0 | Always (success or failure) |

PostToolUse hooks should always exit 0 to avoid disrupting the workflow.

### Stop Hooks (TTS)

| Exit Code | Meaning |
|-----------|---------|
| 0 | Always |

---

## Debugging

Enable verbose logging with the environment variable:

```bash
export CLAUDE_HOOK_DEBUG=1
```

All hooks log to stderr with a prefix format:
```
[hook-name] INFO: message
[hook-name] WARN: message
[hook-name] ERROR: message
```

---

## Minimal Configuration Examples

### Safety Hooks Only (Recommended Minimum)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "python3 ./scripts/claude-hooks/dangerous-command-blocker.py"}]
      },
      {
        "matcher": "Read|Edit|Write|Bash",
        "hooks": [{"type": "command", "command": "python3 ./scripts/claude-hooks/sensitive-file-protector.py"}]
      }
    ]
  }
}
```

### Code Quality Hooks Only

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {"type": "command", "command": "python3 ./scripts/claude-hooks/auto-formatter.py"},
          {"type": "command", "command": "python3 ./scripts/claude-hooks/type-checker.py"}
        ]
      }
    ]
  }
}
```

### Notification Hooks Only

```json
{
  "hooks": {
    "Stop": [{"type": "command", "command": "python3 ./scripts/claude-hooks/tts-notify.py stop"}],
    "SubagentStop": [{"type": "command", "command": "python3 ./scripts/claude-hooks/tts-notify.py subagent"}]
  }
}
```
