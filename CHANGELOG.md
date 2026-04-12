# Changelog

All notable changes to System2 are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-04-11

### Fixed

- `repo-governor` agent template for `.claude/settings.json` now uses correct `Read(pattern)`/`Edit(pattern)` syntax for `permissions.deny` rules. Bare glob patterns were silently ignored or produced warnings at startup.

## [0.4.0] - 2026-04-11

Anti-additive bias and simplification pass across agents, hooks, and evals to reduce generated slop.

### Added

- Simplification step in post-execution workflow: `code-reviewer` runs in a new simplification mode when diffs exceed 50 lines or touch more than 2 files, identifying removable abstractions, wrappers, comments, and dead code.
- Slop catalog integration: `code-reviewer` reads `.claude/slop-catalog.md` for project-specific anti-patterns and suggests new entries; `executor` treats catalog entries as local convention.
- Write-lease lifecycle in orchestrator: per-task file path constraints written to `.task-lease.regex` before execution, enforced by `validate-file-paths.py`, cleaned up after completion.
- Change budget reporting: `change-budget-reporter.py` SubagentStop hook reads `.task-budget.json` and reports surface-area metrics (files changed, symbols added, lines delta).
- Module boundary enforcement: `boundary-check.py` PreToolUse hook validates imports against `spec/module-boundaries.json`.
- Boundary artifact outputs for `design-architect`: emits `spec/interfaces.json` (public exports per module) and `spec/module-boundaries.json` (allowed/forbidden import paths) alongside `spec/design.md`.
- Anti-slop sequence eval suite (`evals/fixtures/anti-slop-sequence/`): 4-task progressive coding sequence with golden files testing whether the executor avoids unnecessary abstractions across sequential changes.
- `EVAL-SEC-004` eval validating all allowlist `.regex` files contain compilable patterns.
- Stale task-lease/budget file cleanup during session bootstrap.

### Changed

- `executor`: added anti-additive bias rules (prefer deletion over addition, justify every new symbol, removal pass after green tests), assumptions-first protocol for non-trivial tasks.
- `code-reviewer`: expanded review checklist with minimality and adaptation cost criteria; surface-area delta reporting; future-change probe now covers two requirements instead of one.
- `design-architect`: new required sections in `spec/design.md` — "Simplicity Budget" (caps on new modules/interfaces, mandatory do-nothing alternative) and "Rejected Abstractions".
- `spec-coordinator`: new required section "Minimal Change Intent" in `spec/context.md`.
- `task-planner`: tasks now include `change_budget` (max files, max new symbols, interface policy) and `write_lease` (file path regex patterns) fields.
- Delegation contract in orchestrator CLAUDE.md: added "Non-goals" and "Change shape" fields.
- Hook utilities (`_hook_utils.py`): trimmed verbose docstrings, removed unused `check_command_exists`, `get_tool_input()` now returns None on parse failure.
- `dangerous-command-blocker.py`, `sensitive-file-protector.py`, `auto-formatter.py`, `type-checker.py`, `tts-notify.py`, `validate-file-paths.py`: reduced to minimal implementations, removed narrative docstrings and dead code.

### Removed

- `dangerous-commands-allowlist.regex` and `sensitive-patterns.regex` — patterns now embedded directly in their respective hooks.
- `example-hooks-config.md` — removed in favor of `HOOKS.md`.
- Unused helper functions and verbose docstring boilerplate across all hooks.

## [0.3.0] - 2026-03-15

Add a bounded corrective path for non-local regressions while preserving the existing fast path for routine implementation.

### Added

- Maintenance / Regression Loop in `CLAUDE.md` with local-vs-non-local failure classification, regression ledger recording, amendment-vs-invalidation routing, and a 3-cycle corrective iteration cap.
- Corrective mode for `requirements-engineer` — bimodal operation (baseline for initial spec work, corrective for post-verification failure analysis) producing bounded requirement deltas with design-impact classification.
- Maintenance execution rules and citation authority for `executor` — scope discipline during corrective cycles, with temporary REQ ID citation from corrective packets.
- Structured verification summary for `test-engineer` — baseline/regressed/flaky/changed-file breakdown required in completion output, plus a test mutation policy with edit classification and assertion-weakening guards.
- Future-change probe for `code-reviewer` — assesses whether each diff makes plausible next changes easier, neutral, or harder, and identifies new rigidities.
- Maintenance evals for `eval-engineer` — sequential change-sequence authoring with metrics for regression-free completion, diff size growth, interface churn, and corrective cycle count.
- `spec/regression-ledger.md` as a formal artifact with `allowlists/regression-ledger.regex` and tracked in `agent_allowlist_bindings.json` as an unbound allowlist.
- `spec/regression-ledger.md` listed in `design-architect` inputs for context when refreshing design after corrective requirements.
- `EVAL-SEC-004` — validates all allowlist `.regex` files contain compilable regex patterns.
- `Maintenance / Regression Loop` added to `template_sections.json` required headings.

### Changed

- `requirements-engineer` description and inputs updated to reflect bimodal operation.
- `test-engineer` completion summary now requires the structured verification summary.
- `allowlist_inventory.json` expected count updated from 12 to 13.
- `skills/init/SKILL.md` template synced with updated `CLAUDE.md`.

## [0.2.0] - 2026-02-16

Remove Roo Code support and convert to Claude Code plugin with marketplace distribution.

### Added

- Plugin manifest (`.claude-plugin/plugin.json`) declaring name, version, author, and description.
- Marketplace manifest (`.claude-plugin/marketplace.json`) for distribution via `/plugin marketplace`.
- `/system2:init` skill that writes the orchestrator CLAUDE.md into the consuming project.

### Changed

- All System2 files relocated from `.claude/` to plugin-standard directories (`agents/`, `hooks/`, `allowlists/`, `skills/`).
- Agent frontmatter hook paths migrated from `$CLAUDE_PROJECT_DIR/.claude/hooks/` to `${CLAUDE_PLUGIN_ROOT}/hooks/` (and likewise for allowlists).
- `README.md` rewritten for plugin installation workflow; manual copy instructions removed.
- `CLAUDE.md` updated to remove `.claude/agents/` path references.
- Consolidated `README.md` and `README-CLAUDE.md` into a single README.

### Removed (BREAKING)

- **Installation method changed from manual file copy to the Claude Code plugin system.** Users must reinstall via `/plugin marketplace add` and `/plugin install`.
- **Roo Code platform support has been fully removed.** Roo Code users should pin to the `v0.1.0` tag for continued support, or maintain a fork.
- 14 Roo Code mode definition files (`roo/01-orchestrator-system2.yml` through `roo/14-code-reviewer.yml`).
- `roo/system2-pack.yml` -- combined Roo Code mode pack.
- `.roo/commands/update-system2.md` -- Roo Code slash command.
- `README-ROO.md` -- Roo Code documentation.
- `README-CLAUDE.md` -- consolidated into `README.md`.
- `manifest.json` -- declarative file list for the update script.
- `.system2/` directory -- update infrastructure (backup, lock, log, version cache).
- `scripts/` directory -- `update-system2.sh`, `generate-manifest.py`, `update-system2-yaml.py`, and Claude hook scripts (moved to `hooks/`).
- `tests/` directory -- shell and Python test suites for removed infrastructure.
- `/update-system2` slash command (replaced by native plugin update mechanism).

## [0.1.0] - 2026-02-01

### Added

- `/update-system2` slash command for both Claude Code and Roo Code platforms.
- `scripts/update-system2.sh` -- manifest-driven update script with backup, validation, lock file, and self-update detection.
  - Flags: `--dry-run`, `--force`, `--scope project|global|both`, `--repo-url <url>`, `--branch <branch>`.
  - Exit codes: 0 (success/up-to-date), 1 (general error), 2 (network failure), 3 (validation failure), 4 (missing dependency).
- `scripts/update-system2-yaml.py` -- YAML merge helper for Roo Code mode updates. Preserves non-System2 custom modes during merge.
- `manifest.json` -- declarative file list with platform, scope, and validation metadata consumed by the update script.
- `VERSION` file (0.1.0) used for upstream version comparison.
- Timestamped backups in `.system2-backup/` before any file overwrites.
- Update audit log written to `.system2/update.log`.
- Safety and quality hooks in `scripts/claude-hooks/`: dangerous-command-blocker, sensitive-file-protector, auto-formatter, type-checker, tts-notify, validate-file-paths.
- 13 Claude Code subagent definitions in `.claude/agents/` with file-access allowlists.
- 14 Roo Code mode definitions in `roo/system2-pack.yml`.
- Orchestrator instructions in `CLAUDE.md` with session bootstrap, gate workflow, and post-execution agent chaining.
- Platform-specific documentation: `README-CLAUDE.md`, `README-ROO.md`.
