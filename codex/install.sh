#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --codex-home)
      CODEX_HOME="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: ./codex/install.sh [--dry-run] [--codex-home <path>]" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOT="$CODEX_HOME/skills/system2"

run_or_echo() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    eval "$@"
  fi
}

echo "Installing System2 Codex runtime"
echo "Source: $SCRIPT_DIR"
echo "Target: $TARGET_ROOT"

run_or_echo "mkdir -p \"$TARGET_ROOT/skills/init\" \"$TARGET_ROOT/runtime\" \"$TARGET_ROOT/templates\" \"$TARGET_ROOT/tools\""
run_or_echo "cp \"$SCRIPT_DIR/manifest.json\" \"$TARGET_ROOT/manifest.json\""
run_or_echo "cp \"$SCRIPT_DIR/config.toml.example\" \"$TARGET_ROOT/config.toml.example\""
run_or_echo "cp \"$SCRIPT_DIR/runtime/agent-registry.json\" \"$TARGET_ROOT/runtime/agent-registry.json\""
run_or_echo "cp \"$SCRIPT_DIR/templates/AGENTS.md\" \"$TARGET_ROOT/templates/AGENTS.md\""
run_or_echo "cp \"$SCRIPT_DIR/skills/init/SKILL.md\" \"$TARGET_ROOT/skills/init/SKILL.md\""
run_or_echo "cp \"$SCRIPT_DIR/tools/validate_paths.py\" \"$TARGET_ROOT/tools/validate_paths.py\""
run_or_echo "chmod +x \"$TARGET_ROOT/tools/validate_paths.py\""
run_or_echo "CODEX_HOME=\"$CODEX_HOME\" codex features enable multi_agent"

echo
echo "Install complete."
echo "Next steps:"
echo "1) In your project, run the skill by prompting: use system2-init"
echo "2) Review the generated AGENTS.md and start at Gate 0 scope definition"
