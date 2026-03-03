# Migration Guide: Claude-Only to Dual Runtime (Claude + Codex)

This guide migrates an existing System2 Claude plugin deployment to dual runtime support while preserving current Claude behavior.

## Goal

- Keep Claude plugin workflows unchanged.
- Add Codex runtime in parallel.
- Standardize spec artifacts and gate behavior across both runtimes.

## Prerequisites

- Existing System2 Claude installation is working.
- Codex CLI is installed and authenticated.
- Access to `~/.codex` on target machines.

## Migration Steps

### 1) Baseline the current Claude setup

In a Claude-driven repo:

- Confirm plugin status with `/plugin list`.
- Confirm `CLAUDE.md` exists and gate flow is active.
- Confirm `spec/context.md`, `spec/requirements.md`, `spec/design.md`, `spec/tasks.md` conventions are in use.

### 2) Install Codex runtime pack

From the System2 repo root:

```bash
./codex/install.sh
```

What this does:

- Installs runtime assets to `$CODEX_HOME/skills/system2`.
- Enables Codex multi-agent mode (`codex features enable multi_agent`).

### 3) Bootstrap project orchestration for Codex

In the target project session with Codex:

- Ask Codex to run `system2-init`.
- This creates `AGENTS.md` (Codex orchestrator instructions).
- If `AGENTS.md` already exists, run `system2-init --force` only after review.

### 4) Validate dual-runtime consistency

In one pilot repository, run one small feature through both orchestrators:

- Claude path: `CLAUDE.md` gate flow.
- Codex path: `AGENTS.md` gate flow.

Acceptance criteria:

- Both paths produce/consume the same `spec/*` artifacts.
- Gate progression and approvals are equivalent.
- Final outputs (tests/docs/risk summary) are comparable in quality.

### 5) Roll out team defaults

- Keep Claude plugin install instructions for Claude users.
- Add Codex install instructions (`./codex/install.sh`) for Codex users.
- Standardize review policy: Gate 5 approval is required regardless of runtime.

## Operational Model

- `CLAUDE.md`: Claude orchestrator contract.
- `AGENTS.md`: Codex orchestrator contract.
- `spec/*`: shared source of truth across both runtimes.

This avoids runtime lock-in while preserving one delivery process.

## Risk Controls

- Keep Claude runtime unchanged during migration.
- Add Codex runtime incrementally (pilot first).
- Use allowlist validation for write-restricted roles:

```bash
python3 codex/tools/validate_paths.py plugin/allowlists/spec-context.regex spec/context.md
```

- Require explicit gate approvals in both runtimes.

## Rollback

If Codex rollout causes friction:

- Keep using Claude plugin path only.
- Retain Codex assets installed under `~/.codex/skills/system2` for later retry.
- No Claude plugin rollback is required because Claude files are unchanged by Codex install.

## Recommended Adoption Sequence

1. Pilot in one repo with one squad.
2. Validate delivery metrics over 1-2 sprints.
3. Expand to additional repos with the same dual-runtime playbook.
