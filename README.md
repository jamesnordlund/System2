# System2 - Multi-Agent Engineering Workflows

A framework for **deliberate, spec-driven, verification-first** software engineering with AI assistance.

## Model Provider Support

System2 supports multiple model providers:

- **Native** (default): Claude Code CLI and Roo Code VS Code extension
- **AWS Bedrock** (optional): Claude 3.5 Sonnet via AWS Bedrock for enterprise-grade AI

Configure Bedrock in `.system2/config.yml` when you need enterprise features, cost control, or AWS integration.

## What is System2?

System2 provides a structured multi-agent workflow for building production-grade software. Instead of ad-hoc prompting, it coordinates specialized agents through quality gates:

```
Scope → Context → Requirements → Design → Tasks → Implementation → Verification → Ship
```

The name comes from Daniel Kahneman's dual-process theory: **System 1** is fast and intuitive; **System 2** is slow and deliberate. This framework embodies System 2 thinking—analytical, verification-focused, and risk-aware.

## Core Concepts

### Specialized Agents

Each agent is a domain expert with focused responsibilities:

| Agent | Responsibility | Primary Output |
|-------|----------------|----------------|
| **Repo Governor** | Repository survey and governance | AGENTS.md, build/test commands |
| **Spec Coordinator** | Scope, goals, constraints | spec/context.md |
| **Requirements Engineer** | Testable requirements (EARS format) | spec/requirements.md |
| **Design Architect** | Architecture and interfaces | spec/design.md |
| **Task Planner** | Atomic implementation tasks | spec/tasks.md |
| **Executor** | Code implementation | Source files |
| **Test Engineer** | Verification and test coverage | Test files |
| **Security Sentinel** | Threat modeling, security review | spec/security.md |
| **Eval Engineer** | Agent/LLM behavior evals | Eval harnesses |
| **Docs & Release** | Documentation and changelogs | README, CHANGELOG |
| **Code Reviewer** | Final correctness review | Review comments |
| **Postmortem Scribe** | Incident analysis | Postmortem docs |
| **MCP Toolsmith** | Tool integration design | MCP configurations |

### Quality Gates

Work progresses through explicit approval checkpoints:

- **Gate 0 (Scope)**: Confirm goal, constraints, and definition of done
- **Gate 1 (Context)**: Approve spec/context.md
- **Gate 2 (Requirements)**: Approve spec/requirements.md
- **Gate 3 (Design)**: Approve spec/design.md
- **Gate 4 (Tasks)**: Approve spec/tasks.md
- **Gate 5 (Ship)**: Approve final diff and risk checklist

### Spec-Driven Artifacts

All planning produces versioned Markdown files in `/spec`:

```
spec/
├── context.md       # Problem, goals, constraints, success criteria
├── requirements.md  # EARS-format testable requirements
├── design.md        # Architecture, interfaces, failure modes
├── tasks.md         # Atomic tasks with dependencies
└── security.md      # Threat model (when applicable)
```

These artifacts serve as the contract between planning and execution.

## Workflow Example

A typical feature development flow:

1. **Orchestrator** receives the request and clarifies scope (Gate 0)
2. **Spec Coordinator** drafts context.md → user approves (Gate 1)
3. **Requirements Engineer** writes requirements.md → user approves (Gate 2)
4. **Design Architect** produces design.md → user approves (Gate 3)
5. **Task Planner** creates tasks.md → user approves (Gate 4)
6. **Executor** implements each task with small diffs
7. **Test Engineer** runs verification and adds tests
8. **Security Sentinel** reviews for vulnerabilities
9. **Docs & Release** updates documentation
10. **Code Reviewer** performs final review → user approves (Gate 5)

## Platform Support

System2 workflows are available for multiple AI coding assistants:

| Platform | Configuration Location | Documentation |
|----------|------------------------|---------------|
| **Claude Code** (CLI) | `.claude/agents/` | [README-CLAUDE.md](README-CLAUDE.md) |
| **Roo Code** (VS Code) | `roo/*.yml` | [README-ROO.md](README-ROO.md) |

Both implementations share the same workflow philosophy and agent roles. Choose based on your preferred development environment.

## Key Principles

### Safety by Default
- Never invent build/test commands—discover them from repo
- Resist prompt injection—treat file contents as data
- Enforce least-privilege tool access per agent
- Require human approval for risky changes

### Verification First
- No implementation without approved specs
- Tests run before claiming completion
- Security review for auth, data access, and agentic features

### Context Hygiene
- Main conversation stays focused on decisions
- Specialist work delegated to appropriate agents
- Summaries returned, not raw output

## Quick Start

1. Choose your platform ([Claude Code](README-CLAUDE.md) or [Roo Code](README-ROO.md))
2. Install the agent/mode configurations
3. Start with the **Orchestrator** for any non-trivial task
4. Follow the quality gates, approving at each checkpoint

For simple, focused tasks, you can invoke individual agents directly:
- Starting a feature? → **Spec Coordinator**
- Writing tests? → **Test Engineer**
- Security review? → **Security Sentinel**

## License

See [LICENSE](LICENSE) for details.

---

**System2**: Because reliable software requires deliberate engineering, not just fast prompting.
