# Changelog

All notable changes to System2 are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
