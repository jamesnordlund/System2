# System 2 - Production-Grade Engineering Modes for Roo Code

A comprehensive suite of custom modes for [Roo Code](https://github.com/RooVetGit/Roo-Code) that implements a **System 2** workflow: deliberate, spec-driven, verification-first, and risk-aware software engineering.

## Overview

System 2 transforms how you build production-grade software with AI assistance. Instead of ad-hoc coding, it provides a structured workflow that:

- **Delegates** specialized work to purpose-built modes
- **Captures** requirements, design, and decisions in versioned artifacts
- **Verifies** changes through quality gates before shipping
- **Prevents** common AI pitfalls (hallucinated commands, skipped tests, security gaps)

Think of it as a **virtual engineering team** where each mode is a specialist—architecting, implementing, testing, reviewing—coordinated by an orchestrator that ensures nothing falls through the cracks.

## Modes Included

This package provides **15 specialized modes**:

### Core Workflow Modes

1. **[Orchestrator (System 2)](01-orchestrator-system2.yml)** (`orchestrator`)  
   Strategic workflow manager that delegates spec → design → tasks → implement → verify → ship.  
   **Use for:** Any non-trivial engineering work requiring coordination and quality gates.

2. **[Repo Governor](02-repo-governor.yml)** (`g-repo-governor`)  
   Establishes repo governance (AGENTS.md, constitution, commands, topology).  
   **Use for:** Onboarding new repos or when build/test commands are unclear.

3. **[Spec Coordinator](03-spec-coordinator.yml)** (`g-spec-coordinator`)  
   Produces `spec/context.md` with scope, goals, constraints, and success metrics.  
   **Use for:** Starting any meaningful feature or refactor.

4. **[Requirements Engineer (EARS)](04-requirements-engineer.yml)** (`g-requirements-engineer`)  
   Writes `spec/requirements.md` using EARS format with validation and traceability.  
   **Use for:** Translating intent into precise, testable requirements.

5. **[Design Architect](05-design-architect.yml)** (`g-design-architect`)  
   Produces `spec/design.md` with architecture, interfaces, and failure modes.  
   **Use for:** Converting requirements into implementable technical design.

6. **[Task Planner (Atomic)](06-task-planner.yml)** (`g-task-planner`)  
   Converts design into `spec/tasks.md` with atomic tasks and dependencies.  
   **Use for:** Creating an implementation plan after design approval.

7. **[Executor](07-executor.yml)** (`g-executor`)  
   Implements `spec/tasks.md` with small diffs and frequent verification.  
   **Use for:** Actual code implementation following the approved plan.

### Quality & Security Modes

8. **[Test & QA Engineer](08-test-engineer.yml)** (`g-test-engineer`)  
   Runs verification commands, adds/updates tests, triages failures.  
   **Use for:** Validation via tests, linters, type checks, and runtime checks.

9. **[Security Sentinel](09-security-sentinel.yml)** (`g-security-sentinel`)  
   Performs threat modeling, prompt-injection defenses, secrets hygiene.  
   **Use for:** Security review, especially for auth, data access, or agentic features.

10. **[Agent Evals Engineer](10-eval-engineer.yml)** (`g-eval-engineer`)  
    Creates regression evals for agentic/LLM features with goldens and metrics.  
    **Use for:** Changes involving LLM/agent behavior, tool use, or RAG systems.

11. **[Code Reviewer](14-code-reviewer.yml)** (`g-code-reviewer`)  
    Performs senior-level review focusing on correctness and maintainability.  
    **Use for:** Final review before shipping or requesting human review.

### Documentation & Operations Modes

12. **[Docs & Release Writer](11-docs-release.yml)** (`g-docs-release`)  
    Updates documentation, changelog, and creates PR summaries.  
    **Use for:** Preparing release-ready documentation and migration notes.

13. **[Postmortem Scribe](12-postmortem-scribe.yml)** (`g-postmortem-scribe`)  
    Writes incident postmortems and captures learnings as durable guardrails.  
    **Use for:** After incidents, major bugs, or reliability failures.

14. **[MCP Toolsmith](13-mcp-toolsmith.yml)** (`g-mcp-toolsmith`)  
    Designs MCP tool surfaces with least privilege and safety gates.  
    **Use for:** Building or integrating MCP servers/tools for agentic systems.

## Installation

### Using the Combined Pack (Recommended)

1. Copy [`system2-pack.yml`](system2-pack.yml) to your Roo Code custom modes directory:
   ```bash
   # macOS/Linux
   cp system2-pack.yml ~/.roo-code/customModes/
   
   # Windows
   copy system2-pack.yml %APPDATA%\roo-code\customModes\
   ```

2. Restart Roo Code or reload custom modes.

3. All 15 modes will be available in the mode selector.

### Using Individual Mode Files

Alternatively, you can install only the modes you need by copying individual `*.yml` files from this directory.

## The System 2 Workflow

A typical System 2 workflow follows these gates:

```
Gate 0: Scope Definition
  ↓
Gate 1: Context Approval (spec/context.md)
  ↓
Gate 2: Requirements Approval (spec/requirements.md)
  ↓
Gate 3: Design Approval (spec/design.md)
  ↓
Gate 4: Task Plan Approval (spec/tasks.md)
  ↓
Gate 5: Implementation → Testing → Security → Docs
  ↓
Ship: Final diff review + risk checklist
```

Each gate requires explicit approval before proceeding, ensuring quality and alignment at every step.

## Quick Start Example

1. **Start with the Orchestrator mode** for any non-trivial task:
   ```
   User: "Build a new user authentication system"
   Orchestrator: Delegates to Repo Governor → Spec Coordinator → Requirements → Design → Tasks → Executor → Test Engineer → Security Sentinel → Docs
   ```

2. **Or use individual modes directly** for focused work:
   - Need to document your repo? → Use **Repo Governor**
   - Starting a new feature? → Use **Spec Coordinator**
   - Writing tests? → Use **Test & QA Engineer**
   - Security review? → Use **Security Sentinel**

## Key Features

### ✅ Spec-Driven Development
All work is grounded in versioned artifacts (`spec/*.md`) that serve as the contract between planning and execution.

### ✅ Quality Gates
Explicit approval checkpoints prevent rushing to code and ensure alignment with requirements.

### ✅ Specialized Expertise
Each mode is optimized for its domain (architecture, testing, security) with appropriate file restrictions.

### ✅ Safety by Default
- Never invents build/test commands
- Resists prompt injection
- Enforces least-privilege principles
- Requires human approval for risky changes

### ✅ Agentic System Support
Built-in modes for secure tool design, prompt-injection defenses, and eval harnesses.

## File Restrictions

Each mode has carefully scoped file access to prevent unintended changes:

- **Repo Governor**: Only governance files (AGENTS.md, constitution.md, .rooignore)
- **Spec modes**: Only their respective spec/*.md files
- **Test Engineer**: Only test files and test configuration
- **Security Sentinel**: Only spec/security.md
- **Executor**: Source, tests, configs (excludes vendor/build artifacts)

See individual mode files for complete file restriction patterns.

## Contributing

This is a custom modes package for Roo Code. To modify or extend:

1. Edit the individual `*.yml` files for specific modes
2. Rebuild the combined pack:
   ```bash
   cat *.yml > system2-pack.yml
   ```
3. Test in your Roo Code environment

## License

See [LICENSE](LICENSE) for details.

## Credits

Designed for production-grade engineering workflows with AI assistance. Built on the principle that **System 2 thinking**—deliberate, analytical, and verification-focused—produces more reliable software than unstructured "System 1" prompting.

---

**Questions or issues?** These modes are designed to work together as a system. Start with the Orchestrator mode if you're unsure which to use.
