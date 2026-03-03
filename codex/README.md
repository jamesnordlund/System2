# System2 for Codex

This directory is the Codex runtime port of System2.

## What it provides

- `templates/AGENTS.md`: Codex orchestrator template (System2 gate workflow)
- `skills/init/SKILL.md`: `system2-init` skill to bootstrap `AGENTS.md`
- `runtime/agent-registry.json`: role map from System2 agents to Codex sub-agent types
- `tools/validate_paths.py`: allowlist validator for write-restricted roles
- `config.toml.example`: optional Codex feature/profile baseline
- `install.sh`: local installer (marketplace alternative)

## Install

```bash
./codex/install.sh
```

Dry run:

```bash
./codex/install.sh --dry-run
```

Custom Codex home:

```bash
./codex/install.sh --codex-home /path/to/.codex
```

## Use

1. Install enables multi-agent mode automatically by running:

```bash
codex features enable multi_agent
```

2. In your target project, ask Codex to use `system2-init`.
3. Follow the generated `AGENTS.md` gate workflow.
