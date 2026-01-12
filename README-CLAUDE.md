# System2 for Claude Code

This guide explains how to use System2 multi-agent workflows with the [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code).

## Overview

Claude Code uses **subagents** defined as Markdown files with YAML frontmatter. The main conversation acts as the **orchestrator**, delegating specialist work to purpose-built subagents in `.claude/agents/`.

## Installation

1. Copy this repository (or just the `.claude/` directory) into your project root
2. Copy `CLAUDE.md` to your project root to enable orchestrator behavior
3. Copy `scripts/claude-hooks/` for file validation hooks

```
your-project/
├── .claude/
│   ├── agents/           # Subagent definitions
│   └── allowlists/       # File restriction patterns
├── scripts/
│   └── claude-hooks/     # Validation scripts
└── CLAUDE.md             # Orchestrator instructions
```

## Available Subagents

| Subagent | Description | Tools |
|----------|-------------|-------|
| `repo-governor` | Repo survey and governance bootstrap | Read, Edit, Write, Grep, Glob, Bash |
| `spec-coordinator` | Drafts spec/context.md | Read, Edit, Write, Grep, Glob |
| `requirements-engineer` | Writes spec/requirements.md (EARS format) | Read, Edit, Write, Grep, Glob |
| `design-architect` | Produces spec/design.md | Read, Edit, Write, Grep, Glob |
| `task-planner` | Creates spec/tasks.md | Read, Edit, Write, Grep, Glob |
| `executor` | Implements tasks with small diffs | Read, Edit, Write, Grep, Glob, Bash |
| `test-engineer` | Runs verification, updates tests | Read, Edit, Write, Grep, Glob, Bash |
| `security-sentinel` | Security review and threat modeling | Read, Edit, Write, Grep, Glob, Bash |
| `eval-engineer` | Agent/LLM behavior evals | Read, Edit, Write, Grep, Glob, Bash |
| `docs-release` | Updates docs, changelog, release notes | Read, Edit, Write, Grep, Glob |
| `code-reviewer` | Final review for correctness | Read, Grep, Glob, Bash |
| `postmortem-scribe` | Incident postmortems | Read, Edit, Write, Grep, Glob |
| `mcp-toolsmith` | MCP tool design | Read, Edit, Write, Grep, Glob, Bash |

## Usage

### Basic Workflow

With `CLAUDE.md` in place, Claude Code acts as the orchestrator. For non-trivial work, it will guide you through the quality gates:

```
You: Build a user authentication system

Claude: I'll coordinate this through the System2 workflow.

Gate 0 (Scope): Let me clarify a few things...
- What authentication methods? (email/password, OAuth, etc.)
- Any existing auth infrastructure?
- Definition of done?

[After clarification]

I'll delegate to the spec-coordinator to draft spec/context.md...
```

### Explicit Delegation

You can invoke subagents directly:

```
You: Use the spec-coordinator to draft the context for a new caching feature

You: Use the test-engineer to run verification and fix any failing tests

You: Use the security-sentinel to review the authentication changes
```

### Gate Workflow

The orchestrator pauses for approval at each gate:

1. **Gate 0**: Confirm scope, constraints, definition of done
2. **Gate 1**: Approve `spec/context.md`
3. **Gate 2**: Approve `spec/requirements.md`
4. **Gate 3**: Approve `spec/design.md`
5. **Gate 4**: Approve `spec/tasks.md`
6. **Gate 5**: Approve final diff and risk checklist

Say "skip gates" if you want to move faster (not recommended for production work).

## Subagent Configuration

Each subagent is a Markdown file in `.claude/agents/`:

```markdown
---
name: spec-coordinator
description: Drafts spec/context.md with scope, goals, constraints, and open questions. Use proactively at the start of meaningful work.
tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
hooks:
  PreToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/validate-file-paths.py .claude/allowlists/spec-context.regex"
---
You are a product-minded senior engineer...
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase letters and hyphens |
| `description` | Yes | When Claude should delegate to this subagent |
| `tools` | No | Allowlist of tools; inherits all if omitted |
| `disallowedTools` | No | Denylist applied to inherited tools |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit` (default: `sonnet`) |
| `permissionMode` | No | `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan` |
| `hooks` | No | Lifecycle hooks for validation |

### File Restrictions via Hooks

Unlike Roo Code's `fileRegex`, Claude Code uses hooks for file restrictions. Each subagent can have a `PreToolUse` hook that validates file paths against a regex pattern:

```yaml
hooks:
  PreToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "python3 ./scripts/claude-hooks/validate-file-paths.py .claude/allowlists/spec-context.regex"
```

The allowlist files in `.claude/allowlists/` contain regex patterns:

```
# .claude/allowlists/spec-context.regex
^spec/context\.md$
```

## Safety and Quality Hooks

System2 includes reusable hooks for safety, code quality, and notifications. These are located in `scripts/claude-hooks/`.

### Available Hooks

| Hook | Event | Purpose |
|------|-------|---------|
| `dangerous-command-blocker.py` | PreToolUse (Bash) | Blocks `rm -rf /`, `sudo rm -rf`, `chmod 777`, `git reset --hard`, force push to main/master, `DROP TABLE`, `DELETE` without WHERE |
| `sensitive-file-protector.py` | PreToolUse (Read/Edit/Write/Bash) | Blocks access to `.env`, `~/.ssh/`, `~/.aws/`, `~/.gnupg/`, credential files |
| `auto-formatter.py` | PostToolUse (Edit/Write) | Runs prettier/black/gofmt on modified files |
| `type-checker.py` | PostToolUse (Edit/Write) | Runs tsc/mypy on modified TypeScript/Python files |
| `tts-notify.py` | Stop/SubagentStop | Announces task completion via TTS (macOS/Windows/Linux) |
| `validate-file-paths.py` | PreToolUse (Edit/Write) | Restricts file writes to allowlisted paths |

### Enabling Hooks

Add hooks to agent frontmatter in `.claude/agents/*.md`:

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
---
```

Or add to `.claude/settings.json` for global hooks:

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

### Hook Behavior

**PreToolUse hooks** run before tool execution and can block operations:
- Exit 0: Allow the operation
- Exit 2: Block with JSON reason on stdout (`{"decision": "block", "reason": "..."}`)
- Exit 1: Error (blocks implicitly)

**PostToolUse hooks** run after tool completion and are informational only (always exit 0).

**Stop/SubagentStop hooks** run when tasks complete (always exit 0).

### Custom Allowlists and Patterns

The dangerous command blocker and sensitive file protector support optional pattern files:

```bash
# Allow specific commands that would otherwise be blocked
python3 ./scripts/claude-hooks/dangerous-command-blocker.py .claude/hooks/dangerous-commands-allowlist.regex

# Add custom sensitive file patterns
python3 ./scripts/claude-hooks/sensitive-file-protector.py .claude/hooks/sensitive-patterns.regex
```

Pattern files use one regex per line (lines starting with `#` are comments).

### Debugging Hooks

Set `CLAUDE_HOOK_DEBUG=1` for verbose output:

```bash
export CLAUDE_HOOK_DEBUG=1
```

See `scripts/claude-hooks/README.md` for detailed documentation.

## Programmatic Usage

### CLI with Custom Agents

Pass session-only agent definitions via `--agents`:

```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```

### Agent Priority Order

When duplicates exist:
1. `--agents` CLI flag (session only)
2. `.claude/agents/` (project)
3. `~/.claude/agents/` (user)
4. Plugin `agents/` directory

## Managing Subagents

Use the `/agents` command in Claude Code to:
- Create new subagents
- Edit existing subagents
- Choose project vs user scope
- Preview subagent configurations

## Background vs Foreground Execution

- **Foreground** (default): Blocking; full tool access
- **Background**: Concurrent; auto-denies permissions; no MCP tools

Use background runs for high-volume tasks like test suites or log processing.

## Context and Resuming

- Each subagent runs in its own context window
- Transcripts stored in `~/.claude/projects/{project}/{sessionId}/subagents/`
- Resume a prior subagent by asking Claude to continue its work

## Tips

### Delegation Contract

When delegating (either as orchestrator or manually), include:
- **Objective**: One-sentence goal
- **Inputs**: Files to read or discover
- **Outputs**: Files to create/update
- **Constraints**: What not to do
- **Completion summary**: What to report back

### Customizing Subagents

To modify behavior:
1. Edit the appropriate `.claude/agents/*.md` file
2. Adjust the system prompt (body of the Markdown file)
3. Update `tools` or `hooks` as needed
4. Update corresponding `.claude/allowlists/*.regex` if file restrictions change

### Skipping the Full Workflow

For simple tasks, bypass the orchestrator:
```
You: (without CLAUDE.md or with explicit instruction)
Just add a helper function to utils.py that formats dates.
```

## Troubleshooting

### Subagent Not Found
- Ensure the agent file exists in `.claude/agents/`
- Check that `name` field matches what you're requesting

### File Edit Blocked
- Check the allowlist regex in `.claude/allowlists/`
- Ensure `scripts/claude-hooks/validate-file-paths.py` is executable

### Too Many Approval Prompts
- Use `permissionMode: acceptEdits` for trusted operations
- Consider `dontAsk` for fully automated pipelines (use with caution)

## See Also

- [NEW-README.md](NEW-README.md) - System2 overview
- [README-ROO.md](README-ROO.md) - Roo Code implementation
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
