#!/usr/bin/env python3
"""Generate manifest.json for System2 update distribution.

Walks known System2 directories, classifies files by platform/scope/validation,
and outputs a deterministic manifest.json to the repo root.

This script is development/release tooling only. It is NOT distributed to users
and is NOT included in the manifest it generates.
"""

import argparse
import json
import sys
from pathlib import Path


# Each rule: (glob_pattern, platform, scope, validation)
FILE_RULES = [
    (".claude/agents/*.md", "claude", "project", "markdown"),
    (".claude/allowlists/*", "claude", "project", "none"),
    (".claude/commands/*.md", "claude", "all", "markdown"),
    (".roo/commands/*.md", "roo", "all", "markdown"),
    ("scripts/claude-hooks/*.py", "claude", "project", "python"),
    ("scripts/claude-hooks/*.regex", "claude", "project", "none"),
    ("roo/system2-pack.yml", "roo", "all", "yaml"),
    ("CLAUDE.md", "claude", "project", "none"),
]

# Explicit singleton files included even if they don't exist yet.
EXPLICIT_FILES = [
    {
        "path": "scripts/update-system2.sh",
        "platform": "all",
        "scope": "project",
        "validation": "shell",
    },
    {
        "path": "scripts/update-system2-yaml.py",
        "platform": "roo",
        "scope": "project",
        "validation": "python",
    },
]

# Files to exclude (dev tooling, not distributed).
EXCLUDE_FILES = {
    "scripts/generate-manifest.py",
}


def derive_description(rel_path: str) -> str:
    """Derive a human-readable description from a file path."""
    p = Path(rel_path)
    stem = p.stem
    suffix = p.suffix

    if rel_path.startswith(".claude/agents/"):
        name = stem.replace("-", " ").replace("_", " ").strip().title()
        return f"{name} agent definition"

    if rel_path.startswith(".claude/allowlists/"):
        name = stem.replace("-", " ").replace("_", " ").strip().title()
        return f"{name} file-access allowlist"

    if rel_path.startswith(".claude/commands/"):
        name = stem.replace("-", " ").replace("_", " ").strip().title()
        return f"{name} slash command (Claude Code)"

    if rel_path.startswith(".roo/commands/"):
        name = stem.replace("-", " ").replace("_", " ").strip().title()
        return f"{name} slash command (Roo Code)"

    if rel_path.startswith("scripts/claude-hooks/"):
        name = stem.replace("-", " ").replace("_", " ").strip().title()
        if suffix == ".py":
            return f"{name} hook script"
        elif suffix == ".regex":
            return f"{name} hook pattern"
        return f"{name} hook file"

    descriptions = {
        "scripts/update-system2.sh": "Update script (self-update target)",
        "scripts/update-system2-yaml.py": "YAML merge helper for Roo Code modes",
        "roo/system2-pack.yml": "Roo Code mode pack (all System2 modes)",
        "CLAUDE.md": "Claude Code project instructions",
    }
    if rel_path in descriptions:
        return descriptions[rel_path]

    name = stem.replace("-", " ").replace("_", " ").strip().title()
    return f"{name} file"


def collect_files(repo_root: Path, check_exists: bool = False) -> list[dict]:
    """Collect all distributable files based on FILE_RULES and EXPLICIT_FILES."""
    files = []
    seen_paths: set[str] = set()

    for pattern, platform, scope, validation in FILE_RULES:
        matched = sorted(repo_root.glob(pattern))
        for filepath in matched:
            rel = str(filepath.relative_to(repo_root))
            if rel in EXCLUDE_FILES or rel in seen_paths:
                continue
            seen_paths.add(rel)
            files.append(
                {
                    "path": rel,
                    "platform": platform,
                    "scope": scope,
                    "validation": validation,
                    "description": derive_description(rel),
                }
            )

    for entry in EXPLICIT_FILES:
        rel = entry["path"]
        if rel in seen_paths or rel in EXCLUDE_FILES:
            continue
        seen_paths.add(rel)
        files.append(
            {
                "path": rel,
                "platform": entry["platform"],
                "scope": entry["scope"],
                "validation": entry["validation"],
                "description": derive_description(rel),
            }
        )

    files.sort(key=lambda f: f["path"])

    if check_exists:
        missing = []
        for f in files:
            if not (repo_root / f["path"]).exists():
                missing.append(f["path"])
        if missing:
            print(
                "ERROR: The following manifest files do not exist on disk:",
                file=sys.stderr,
            )
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
            sys.exit(1)

    return files


def main():
    parser = argparse.ArgumentParser(
        description="Generate manifest.json for System2 update distribution."
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Path to the repository root (default: parent of scripts/ dir)",
    )
    parser.add_argument(
        "--check-exists",
        action="store_true",
        help="Validate that all manifest files exist on disk (for CI use)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for manifest.json (default: <repo-root>/manifest.json)",
    )
    args = parser.parse_args()

    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent

    if not repo_root.is_dir():
        print(f"ERROR: repo root is not a directory: {repo_root}", file=sys.stderr)
        sys.exit(1)

    version_file = repo_root / "VERSION"
    if not version_file.exists():
        print(f"ERROR: VERSION file not found at {version_file}", file=sys.stderr)
        sys.exit(1)
    version = version_file.read_text().strip()
    if not version:
        print("ERROR: VERSION file is empty", file=sys.stderr)
        sys.exit(1)

    files = collect_files(repo_root, check_exists=args.check_exists)

    manifest = {
        "version": version,
        "files": files,
    }

    output_path = Path(args.output) if args.output else repo_root / "manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")

    print(f"Generated {output_path} with {len(files)} files (version {version})")


if __name__ == "__main__":
    main()
