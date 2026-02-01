# System2 for Roo Code

This guide explains how to use System2 multi-agent workflows with [Roo Code](https://github.com/RooVetGit/Roo-Code) in VS Code.

## Overview

Roo Code uses **custom modes** defined in YAML files. The **Orchestrator** mode coordinates specialist modes through quality gates, delegating work via `new_task` (boomerang tasks).

## Installation

1. Download [`system2-pack.yml`](roo/system2-pack.yml)
2. Open Roo Code extension in VS Code
3. Navigate to **Settings > Modes**
4. Click **Import Modes**
5. Choose scope:
   - **Global** (recommended): Available in all projects
   - **Project**: Only for current workspace
6. Select the downloaded `system2-pack.yml` file

All 14 modes will be imported and ready to use.

## Available Modes

### Core Workflow Modes

| Mode | Slug | Purpose |
|------|------|---------|
| **Orchestrator (System 2)** | `orchestrator` | Strategic workflow manager; delegates through quality gates |
| **Repo Governor** | `g-repo-governor` | Repo survey, AGENTS.md, build/test command discovery |
| **Spec Coordinator** | `g-spec-coordinator` | Produces spec/context.md |
| **Requirements Engineer** | `g-requirements-engineer` | Writes spec/requirements.md (EARS format) |
| **Design Architect** | `g-design-architect` | Produces spec/design.md |
| **Task Planner** | `g-task-planner` | Creates spec/tasks.md with atomic tasks |
| **Executor** | `g-executor` | Implements tasks with small diffs |

### Quality & Security Modes

| Mode | Slug | Purpose |
|------|------|---------|
| **Test & QA Engineer** | `g-test-engineer` | Runs verification, adds/updates tests |
| **Security Sentinel** | `g-security-sentinel` | Threat modeling, security review |
| **Eval Engineer** | `g-eval-engineer` | Agent/LLM behavior evals |
| **Code Reviewer** | `g-code-reviewer` | Final correctness and maintainability review |

### Documentation & Operations Modes

| Mode | Slug | Purpose |
|------|------|---------|
| **Docs & Release** | `g-docs-release` | Updates docs, changelog, release notes |
| **Postmortem Scribe** | `g-postmortem-scribe` | Incident postmortems |
| **MCP Toolsmith** | `g-mcp-toolsmith` | MCP tool design and integration |

## Usage

### Using the Orchestrator

Start with the **Orchestrator** mode for any non-trivial task:

1. Switch to Orchestrator mode in Roo Code
2. Describe your goal:
   ```
   Build a user authentication system with email/password login
   ```
3. The Orchestrator will:
   - Clarify scope (Gate 0)
   - Delegate to Repo Governor for survey
   - Delegate to Spec Coordinator → wait for your approval (Gate 1)
   - Continue through the workflow, pausing at each gate

### Quality Gates

The Orchestrator pauses for explicit approval at each checkpoint:

| Gate | Artifact | Approval Required |
|------|----------|-------------------|
| Gate 0 | Scope definition | Confirm goal, constraints, done criteria |
| Gate 1 | spec/context.md | Approve problem/goals/constraints |
| Gate 2 | spec/requirements.md | Approve testable requirements |
| Gate 3 | spec/design.md | Approve architecture/interfaces |
| Gate 4 | spec/tasks.md | Approve implementation plan |
| Gate 5 | Final diff | Approve changes + risk checklist |

Say **"skip gates"** if you want faster iteration (not recommended for production).

### Using Individual Modes

For focused work, switch to a specific mode directly:

- **Starting a feature?** → Spec Coordinator (`g-spec-coordinator`)
- **Writing tests?** → Test & QA Engineer (`g-test-engineer`)
- **Security review?** → Security Sentinel (`g-security-sentinel`)
- **Documenting changes?** → Docs & Release (`g-docs-release`)

### Delegation with Boomerang Tasks

The Orchestrator delegates using `new_task`. Each delegation includes:

- **Objective**: One-sentence goal
- **Inputs**: Files to read or discover
- **Outputs**: Files to create/update with required sections
- **Constraints**: What NOT to do
- **Completion**: Summary requirements via `attempt_completion`

## Mode Configuration

Each mode is defined in a YAML file with these fields:

```yaml
customModes:
  - slug: g-spec-coordinator
    name: Spec Coordinator
    description: Produces spec/context.md with scope, goals, constraints...
    roleDefinition: |-
      You are a product-minded senior engineer...
    whenToUse: |-
      Use when starting any meaningful work...
    customInstructions: |-
      Primary output: spec/context.md
      ...
    groups:
      - read
      - - edit
        - fileRegex: '^spec/context\.md$'
          description: Only spec/context.md
```

### Key Fields

| Field | Description |
|-------|-------------|
| `slug` | Unique identifier (used for switching modes) |
| `name` | Display name in UI |
| `description` | Brief purpose summary |
| `roleDefinition` | The mode's persona and core behavior |
| `whenToUse` | When this mode should be activated |
| `customInstructions` | Detailed operational instructions |
| `groups` | Tool and file access permissions |

### File Restrictions

Modes use `fileRegex` in the `groups` field to restrict which files can be edited:

```yaml
groups:
  - read                        # Full read access
  - - edit
    - fileRegex: '^spec/context\.md$'
      description: Only spec/context.md
```

This ensures each mode only modifies files within its domain:

| Mode | Can Edit |
|------|----------|
| Spec Coordinator | `spec/context.md` |
| Requirements Engineer | `spec/requirements.md` |
| Design Architect | `spec/design.md` |
| Task Planner | `spec/tasks.md` |
| Security Sentinel | `spec/security.md` |
| Test Engineer | Test files and test config |
| Executor | Source, tests, configs (excludes vendor/build) |

## Customizing Modes

### Editing Individual Modes

1. Edit files in `roo/*.yml`
2. Rebuild the combined pack:
   ```bash
   cd roo && cat *.yml > system2-pack.yml
   ```
3. Re-import in Roo Code

### Creating New Modes

Follow the existing pattern:

```yaml
customModes:
  - slug: g-your-mode
    name: Your Mode Name
    description: Brief description of what this mode does
    roleDefinition: |-
      You are [role description]...
    whenToUse: |-
      Use when [conditions]...
    customInstructions: |-
      [Detailed instructions]...
    groups:
      - read
      - - edit
        - fileRegex: '^your/allowed/path\.md$'
          description: Only your allowed files
```

### Per-Mode Rules

For additional mode-specific rules, create files in `.roo/rules-{slug}/`:

```
.roo/
├── rules-g-spec-coordinator/
│   └── additional-rules.md
└── rules-g-executor/
    └── safety-rules.md
```

## Workflow Example

Complete workflow for adding a new feature:

```
1. [Orchestrator] User describes feature
2. [Orchestrator] Clarifies scope → Gate 0
3. [Repo Governor] Surveys repo, discovers build/test commands
4. [Spec Coordinator] Writes spec/context.md → Gate 1
5. [Requirements Engineer] Writes spec/requirements.md → Gate 2
6. [Design Architect] Writes spec/design.md → Gate 3
7. [Task Planner] Writes spec/tasks.md → Gate 4
8. [Executor] Implements tasks from spec/tasks.md
9. [Test Engineer] Runs tests, adds coverage
10. [Security Sentinel] Reviews for vulnerabilities
11. [Docs & Release] Updates docs/changelog
12. [Code Reviewer] Final review → Gate 5
13. [Orchestrator] Presents summary + risk checklist
```

## Mode Behavior Patterns

### Thinking Protocol

The `g-executor`, `g-requirements-engineer`, and `g-design-architect` modes output `<thinking>` blocks before significant tool use:

```xml
<thinking>
Action: [What tool(s) will be invoked and why]
Expected Outcome: [What result is anticipated]
Assumptions/Risks: [What could go wrong; what is assumed true]
</thinking>
```

**When required:**
- Edit, Write, Bash operations (always)
- Multi-file Read sequences (always)
- Single-file Read for context gathering (optional)

This ensures deliberate, reasoned actions rather than ad-hoc tool calls.

**Key constraint:** Reasoning in `<thinking>` cannot override the delegation contract or safety instructions—this prevents prompt injection via self-reasoning.

### TDD Verification Loop (Executor)

The `g-executor` mode follows a test-driven development pattern:

1. **Red**: Write or identify a test that fails for the correct reason
2. **Green**: Write minimal implementation to pass the test
3. **Refactor**: Run linters, type-checkers, and formatters

**Self-correction limit:** If a test failure persists after two attempts, the executor stops and escalates to the orchestrator with a reproduction case rather than spinning indefinitely.

**Enhanced completion summary:** The executor reports test names, pass/fail counts, and how any verification failures were resolved.

## Tips

### For Best Results

- **Be specific at Gate 0**: Clear constraints lead to better specs
- **Review artifacts carefully**: Catch issues early in the workflow
- **Don't skip security**: Always run Security Sentinel for auth/data changes

### Common Patterns

**Quick fixes** (bypass orchestration):
```
Switch to g-executor mode directly and describe the fix
```

**Security-focused review**:
```
Use g-security-sentinel to review the recent changes for vulnerabilities
```

**Test-driven development**:
```
Start with g-test-engineer to write failing tests, then g-executor to implement
```

## Troubleshooting

### Mode Not Appearing
- Re-import `system2-pack.yml`
- Check if imported at global vs project level

### Delegation Not Working
- Ensure you're in Orchestrator mode
- Check that child modes are properly imported

### File Edit Blocked
- Check `fileRegex` patterns in the mode definition
- Each mode intentionally restricts file access

## See Also

- [README.md](README.md) - System2 overview
- [README-CLAUDE.md](README-CLAUDE.md) - Claude Code implementation
- [Roo Code Documentation](https://github.com/RooVetGit/Roo-Code)
