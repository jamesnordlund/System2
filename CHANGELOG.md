# Changelog

All notable changes to System2 are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Update audit log written to `.system2-update.log`.
- Safety and quality hooks in `scripts/claude-hooks/`: dangerous-command-blocker, sensitive-file-protector, auto-formatter, type-checker, tts-notify, validate-file-paths.
- 13 Claude Code subagent definitions in `.claude/agents/` with file-access allowlists.
- 14 Roo Code mode definitions in `roo/system2-pack.yml`.
- Orchestrator instructions in `CLAUDE.md` with session bootstrap, gate workflow, and post-execution agent chaining.
- Platform-specific documentation: `README-CLAUDE.md`, `README-ROO.md`.
