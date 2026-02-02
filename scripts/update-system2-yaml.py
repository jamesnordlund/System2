#!/usr/bin/env python3
"""YAML merge helper for System2 Roo Code mode updates.

Provides two subcommands:
  merge    - Merge incoming System2 modes into an existing Roo Code YAML file,
             preserving non-System2 modes.
  validate - Validate that a file is well-formed YAML or Markdown with frontmatter.

The System2 slug list is derived dynamically from the incoming pack file,
not hardcoded. The incoming pack is the single source of truth for which
slugs are "System2 slugs."
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install with: pip3 install pyyaml",
        file=sys.stderr,
    )
    sys.exit(4)


def extract_slugs_from_pack(pack_data: dict) -> set[str]:
    """Extract all mode slugs from an incoming System2 pack."""
    modes = pack_data.get("customModes", [])
    if not isinstance(modes, list):
        return set()
    return {m["slug"] for m in modes if isinstance(m, dict) and "slug" in m}


def merge_modes(existing_path: str, incoming_path: str, output_path: str) -> dict:
    """Merge incoming System2 modes into existing YAML, preserving non-System2 modes.

    Returns a dict with merge statistics: {added, replaced, preserved, removed_slugs}.
    """
    # Read incoming pack
    incoming_data = _load_yaml(incoming_path)
    if incoming_data is None:
        print(f"ERROR: Failed to parse incoming pack: {incoming_path}", file=sys.stderr)
        sys.exit(3)

    incoming_modes = incoming_data.get("customModes", [])
    if not isinstance(incoming_modes, list):
        print(
            f"ERROR: Incoming pack has no valid 'customModes' list: {incoming_path}",
            file=sys.stderr,
        )
        sys.exit(3)

    system2_slugs = extract_slugs_from_pack(incoming_data)
    if not system2_slugs:
        print(
            f"ERROR: Incoming pack contains no modes with slugs: {incoming_path}",
            file=sys.stderr,
        )
        sys.exit(3)

    # Read existing file (may be empty or missing)
    existing_data = _load_yaml(existing_path)
    if existing_data is None:
        existing_data = {"customModes": []}

    existing_modes = existing_data.get("customModes", [])
    if not isinstance(existing_modes, list):
        existing_modes = []

    # Separate non-System2 modes (preserve) from System2 modes (replace)
    preserved_modes = [
        m for m in existing_modes
        if isinstance(m, dict) and m.get("slug") not in system2_slugs
    ]
    replaced_slugs = {
        m.get("slug") for m in existing_modes
        if isinstance(m, dict) and m.get("slug") in system2_slugs
    }

    # Build merged output: preserved non-System2 modes + all incoming modes
    merged_modes = preserved_modes + incoming_modes

    output_data = dict(existing_data)
    output_data["customModes"] = merged_modes

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(
            output_data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

    # Validate round-trip
    check = _load_yaml(output_path)
    if check is None or "customModes" not in check:
        print(f"ERROR: Output file failed round-trip validation: {output_path}", file=sys.stderr)
        sys.exit(3)

    stats = {
        "added": len(system2_slugs - replaced_slugs),
        "replaced": len(replaced_slugs),
        "preserved": len(preserved_modes),
    }
    return stats


def validate_file(file_path: str, file_type: str) -> bool:
    """Validate a file based on its type. Returns True if valid."""
    p = Path(file_path)
    if not p.exists():
        print(f"ERROR: File does not exist: {file_path}", file=sys.stderr)
        return False

    content = p.read_text(encoding="utf-8")

    if file_type == "yaml":
        try:
            data = yaml.safe_load(content)
            if data is None:
                print(f"ERROR: YAML file is empty: {file_path}", file=sys.stderr)
                return False
            return True
        except yaml.YAMLError as e:
            print(f"ERROR: Invalid YAML in {file_path}: {e}", file=sys.stderr)
            return False

    elif file_type == "markdown":
        lines = content.split("\n")
        if len(lines) < 3:
            print(f"ERROR: Markdown file too short for frontmatter: {file_path}", file=sys.stderr)
            return False
        if lines[0].strip() != "---":
            print(f"ERROR: Markdown file missing frontmatter opening '---': {file_path}", file=sys.stderr)
            return False
        # Find closing ---
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return True
        print(f"ERROR: Markdown file missing frontmatter closing '---': {file_path}", file=sys.stderr)
        return False

    elif file_type == "json":
        import json
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {file_path}: {e}", file=sys.stderr)
            return False

    elif file_type == "shell":
        first_line = content.split("\n")[0] if content else ""
        if "#!/bin/bash" in first_line or "#!/usr/bin/env bash" in first_line:
            return True
        print(f"ERROR: Shell script missing bash shebang: {file_path}", file=sys.stderr)
        return False

    elif file_type == "python":
        first_line = content.split("\n")[0] if content else ""
        if "python" in first_line or content.strip():
            return True
        print(f"ERROR: Python file appears empty: {file_path}", file=sys.stderr)
        return False

    else:
        # Unknown type, pass
        return True


def _load_yaml(path: str) -> dict | None:
    """Safely load a YAML file. Returns None if file doesn't exist or is invalid."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        content = p.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            return None
        return data
    except yaml.YAMLError:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="YAML merge helper for System2 Roo Code mode updates."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # merge subcommand
    merge_parser = subparsers.add_parser(
        "merge", help="Merge incoming System2 modes into existing YAML"
    )
    merge_parser.add_argument(
        "--existing", required=True, help="Path to existing YAML file (.roomodes or custom_modes.yaml)"
    )
    merge_parser.add_argument(
        "--incoming", required=True, help="Path to incoming system2-pack.yml"
    )
    merge_parser.add_argument(
        "--output", required=True, help="Path for merged output file"
    )

    # validate subcommand
    validate_parser = subparsers.add_parser(
        "validate", help="Validate file format"
    )
    validate_parser.add_argument(
        "--file", required=True, help="Path to file to validate"
    )
    validate_parser.add_argument(
        "--type",
        required=True,
        choices=["yaml", "markdown", "json", "shell", "python"],
        help="Expected file type",
    )

    args = parser.parse_args()

    if args.command == "merge":
        stats = merge_modes(args.existing, args.incoming, args.output)
        print(
            f"Merge complete: {stats['replaced']} replaced, "
            f"{stats['added']} added, {stats['preserved']} non-System2 preserved"
        )
    elif args.command == "validate":
        if validate_file(args.file, args.type):
            print(f"VALID: {args.file} ({args.type})")
            sys.exit(0)
        else:
            sys.exit(3)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
