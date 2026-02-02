"""Tests for scripts/update-system2-yaml.py — YAML merge helper."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "update-system2-yaml.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# ── Helpers ──────────────────────────────────────────────────────────────────

# Import the module under test directly for unit tests
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import importlib

update_yaml = importlib.import_module("update-system2-yaml")


def _merge(existing_path, incoming_path, output_path):
    """Wrapper around merge_modes."""
    return update_yaml.merge_modes(str(existing_path), str(incoming_path), str(output_path))


def _load(path):
    with open(path) as f:
        return yaml.safe_load(f)


def _slugs(data):
    return [m["slug"] for m in data.get("customModes", [])]


# ── Merge tests ──────────────────────────────────────────────────────────────


class TestMergeReplaces:
    """Test that System2 modes are replaced and non-System2 modes are preserved."""

    def test_merge_replaces_system2_modes(self, tmp_path):
        output = tmp_path / "merged.yaml"
        stats = _merge(FIXTURES / "existing_mixed.yaml", FIXTURES / "incoming_pack.yml", output)

        data = _load(output)
        slugs = _slugs(data)

        # System2 modes from incoming should be present
        assert "orchestrator" in slugs
        assert "g-spec-coordinator" in slugs
        assert "g-executor" in slugs

        # Non-System2 modes should be preserved
        assert "my-custom-mode" in slugs
        assert "another-custom" in slugs

        # The orchestrator should have the new description
        orch = next(m for m in data["customModes"] if m["slug"] == "orchestrator")
        assert orch["description"] == "Updated orchestrator definition"

        assert stats["replaced"] == 2  # orchestrator, g-spec-coordinator
        assert stats["added"] == 1  # g-executor
        assert stats["preserved"] == 2  # my-custom-mode, another-custom

    def test_merge_adds_new_modes(self, tmp_path):
        output = tmp_path / "merged.yaml"
        _merge(FIXTURES / "existing_system2_only.yaml", FIXTURES / "incoming_pack.yml", output)

        data = _load(output)
        slugs = _slugs(data)

        assert "g-executor" in slugs  # New mode from incoming

    def test_merge_preserves_non_system2(self, tmp_path):
        output = tmp_path / "merged.yaml"
        _merge(FIXTURES / "existing_non_system2_only.yaml", FIXTURES / "incoming_pack.yml", output)

        data = _load(output)
        slugs = _slugs(data)

        # Non-System2 should come first (preserved order), then incoming
        assert "my-custom-mode" in slugs
        assert "another-custom" in slugs
        assert "orchestrator" in slugs

    def test_merge_preserves_non_system2_content(self, tmp_path):
        output = tmp_path / "merged.yaml"
        _merge(FIXTURES / "existing_mixed.yaml", FIXTURES / "incoming_pack.yml", output)

        data = _load(output)
        custom = next(m for m in data["customModes"] if m["slug"] == "my-custom-mode")

        # Content should be unchanged
        assert custom["description"] == "A user-defined mode that should be preserved"
        assert custom["roleDefinition"] == "Custom role"


class TestMergeEdgeCases:
    """Edge cases for merge logic."""

    def test_merge_empty_existing(self, tmp_path):
        output = tmp_path / "merged.yaml"
        stats = _merge(FIXTURES / "existing_empty.yaml", FIXTURES / "incoming_pack.yml", output)

        data = _load(output)
        slugs = _slugs(data)

        assert len(slugs) == 3  # All from incoming
        assert stats["replaced"] == 0
        assert stats["added"] == 3
        assert stats["preserved"] == 0

    def test_merge_no_existing_file(self, tmp_path):
        output = tmp_path / "merged.yaml"
        nonexistent = tmp_path / "does_not_exist.yaml"
        stats = _merge(nonexistent, FIXTURES / "incoming_pack.yml", output)

        data = _load(output)
        assert len(data["customModes"]) == 3

    def test_merge_malformed_incoming_aborts(self, tmp_path):
        output = tmp_path / "merged.yaml"
        with pytest.raises(SystemExit) as exc_info:
            _merge(FIXTURES / "existing_mixed.yaml", FIXTURES / "incoming_pack_malformed.yml", output)
        assert exc_info.value.code == 3

    def test_merge_empty_incoming_aborts(self, tmp_path):
        output = tmp_path / "merged.yaml"
        with pytest.raises(SystemExit) as exc_info:
            _merge(FIXTURES / "existing_mixed.yaml", FIXTURES / "incoming_pack_empty.yml", output)
        assert exc_info.value.code == 3

    def test_merge_output_is_valid_yaml(self, tmp_path):
        output = tmp_path / "merged.yaml"
        _merge(FIXTURES / "existing_mixed.yaml", FIXTURES / "incoming_pack.yml", output)

        # Round-trip: load and verify structure
        data = _load(output)
        assert isinstance(data, dict)
        assert "customModes" in data
        assert isinstance(data["customModes"], list)
        for mode in data["customModes"]:
            assert isinstance(mode, dict)
            assert "slug" in mode

    def test_merge_idempotent(self, tmp_path):
        output1 = tmp_path / "merged1.yaml"
        output2 = tmp_path / "merged2.yaml"

        _merge(FIXTURES / "existing_mixed.yaml", FIXTURES / "incoming_pack.yml", output1)
        _merge(output1, FIXTURES / "incoming_pack.yml", output2)

        data1 = _load(output1)
        data2 = _load(output2)

        assert _slugs(data1) == _slugs(data2)
        assert len(data1["customModes"]) == len(data2["customModes"])


class TestSlugDerivation:
    """Verify slugs are extracted from the incoming pack, not hardcoded."""

    def test_slug_derivation_from_incoming(self):
        incoming_data = _load(FIXTURES / "incoming_pack.yml")
        slugs = update_yaml.extract_slugs_from_pack(incoming_data)

        assert slugs == {"orchestrator", "g-spec-coordinator", "g-executor"}

    def test_slug_derivation_custom_pack(self, tmp_path):
        """A pack with non-standard slugs should still work."""
        custom_pack = tmp_path / "custom.yml"
        with open(custom_pack, "w") as f:
            yaml.dump({
                "customModes": [
                    {"slug": "x-custom-one", "name": "Custom One"},
                    {"slug": "x-custom-two", "name": "Custom Two"},
                ]
            }, f)

        output = tmp_path / "merged.yaml"
        stats = _merge(FIXTURES / "existing_mixed.yaml", custom_pack, output)

        data = _load(output)
        slugs = _slugs(data)

        # All original modes should be preserved (none match incoming slugs)
        assert "orchestrator" in slugs
        assert "g-spec-coordinator" in slugs
        assert "my-custom-mode" in slugs
        assert "another-custom" in slugs
        # Plus the new custom modes
        assert "x-custom-one" in slugs
        assert "x-custom-two" in slugs

        assert stats["preserved"] == 4
        assert stats["added"] == 2
        assert stats["replaced"] == 0


# ── Validate tests ───────────────────────────────────────────────────────────


class TestValidate:
    def test_validate_yaml_valid(self):
        assert update_yaml.validate_file(str(FIXTURES / "existing_mixed.yaml"), "yaml") is True

    def test_validate_yaml_invalid(self):
        assert update_yaml.validate_file(str(FIXTURES / "incoming_pack_malformed.yml"), "yaml") is False

    def test_validate_yaml_empty_file(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        assert update_yaml.validate_file(str(empty), "yaml") is False

    def test_validate_markdown_valid(self):
        assert update_yaml.validate_file(str(FIXTURES / "valid_markdown.md"), "markdown") is True

    def test_validate_markdown_invalid(self):
        assert update_yaml.validate_file(str(FIXTURES / "invalid_markdown.md"), "markdown") is False

    def test_validate_markdown_no_closing(self, tmp_path):
        md = tmp_path / "no_close.md"
        md.write_text("---\nname: test\nno closing fence\n")
        assert update_yaml.validate_file(str(md), "markdown") is False

    def test_validate_json_valid(self, tmp_path):
        jf = tmp_path / "test.json"
        jf.write_text(json.dumps({"key": "value"}))
        assert update_yaml.validate_file(str(jf), "json") is True

    def test_validate_json_invalid(self, tmp_path):
        jf = tmp_path / "bad.json"
        jf.write_text("{broken json")
        assert update_yaml.validate_file(str(jf), "json") is False

    def test_validate_shell_valid(self, tmp_path):
        sh = tmp_path / "test.sh"
        sh.write_text("#!/usr/bin/env bash\necho hello\n")
        assert update_yaml.validate_file(str(sh), "shell") is True

    def test_validate_shell_invalid(self, tmp_path):
        sh = tmp_path / "bad.sh"
        sh.write_text("echo hello\n")
        assert update_yaml.validate_file(str(sh), "shell") is False

    def test_validate_python_valid(self, tmp_path):
        py = tmp_path / "test.py"
        py.write_text("print('hello')\n")
        assert update_yaml.validate_file(str(py), "python") is True

    def test_validate_nonexistent_file(self, tmp_path):
        assert update_yaml.validate_file(str(tmp_path / "nope.txt"), "yaml") is False


# ── CLI integration tests ────────────────────────────────────────────────────


class TestCLI:
    """Test the script via subprocess to verify CLI interface."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT)] + list(args),
            capture_output=True,
            text=True,
        )

    def test_help(self):
        result = self._run("--help")
        assert result.returncode == 0
        assert "merge" in result.stdout or "YAML" in result.stdout

    def test_merge_cli(self, tmp_path):
        output = tmp_path / "merged.yaml"
        result = self._run(
            "merge",
            "--existing", str(FIXTURES / "existing_mixed.yaml"),
            "--incoming", str(FIXTURES / "incoming_pack.yml"),
            "--output", str(output),
        )
        assert result.returncode == 0
        assert "Merge complete" in result.stdout
        assert output.exists()

    def test_validate_cli_valid(self):
        result = self._run(
            "validate",
            "--file", str(FIXTURES / "existing_mixed.yaml"),
            "--type", "yaml",
        )
        assert result.returncode == 0
        assert "VALID" in result.stdout

    def test_validate_cli_invalid(self):
        result = self._run(
            "validate",
            "--file", str(FIXTURES / "incoming_pack_malformed.yml"),
            "--type", "yaml",
        )
        assert result.returncode == 3

    def test_no_command(self):
        result = self._run()
        assert result.returncode == 1


# ── Additional edge-case tests ─────────────────────────────────────────────


class TestExtractSlugsEdgeCases:
    """Edge cases for extract_slugs_from_pack (REQ-060 traceability)."""

    def test_customModes_not_a_list(self):
        """When customModes is a string or dict instead of list, return empty set."""
        assert update_yaml.extract_slugs_from_pack({"customModes": "not-a-list"}) == set()

    def test_customModes_missing(self):
        """When customModes key is absent, return empty set."""
        assert update_yaml.extract_slugs_from_pack({"other": "data"}) == set()

    def test_modes_without_slug_key(self):
        """Modes missing slug key should be skipped."""
        data = {"customModes": [{"name": "no-slug"}, {"slug": "has-slug", "name": "ok"}]}
        slugs = update_yaml.extract_slugs_from_pack(data)
        assert slugs == {"has-slug"}

    def test_modes_with_non_dict_entries(self):
        """Non-dict entries in customModes should be skipped gracefully."""
        data = {"customModes": ["a-string", 42, {"slug": "valid", "name": "ok"}]}
        slugs = update_yaml.extract_slugs_from_pack(data)
        assert slugs == {"valid"}


class TestLoadYamlEdgeCases:
    """Edge cases for _load_yaml helper."""

    def test_load_yaml_returns_none_for_invalid(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("this: is: not: [valid yaml")
        assert update_yaml._load_yaml(str(bad)) is None

    def test_load_yaml_returns_none_for_list(self, tmp_path):
        """YAML that parses to a list (not dict) should return None."""
        lst = tmp_path / "list.yaml"
        lst.write_text("- item1\n- item2\n")
        assert update_yaml._load_yaml(str(lst)) is None

    def test_load_yaml_returns_none_for_nonexistent(self, tmp_path):
        assert update_yaml._load_yaml(str(tmp_path / "nope.yaml")) is None


class TestValidateAdditional:
    """Additional validation edge cases."""

    def test_validate_shell_with_bin_bash_shebang(self, tmp_path):
        """#!/bin/bash (without env) should also be valid (REQ-025)."""
        sh = tmp_path / "test.sh"
        sh.write_text("#!/bin/bash\necho hello\n")
        assert update_yaml.validate_file(str(sh), "shell") is True

    def test_validate_unknown_type_passes(self, tmp_path):
        """Unknown file type should pass validation (returns True)."""
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert update_yaml.validate_file(str(f), "unknown_type") is True

    def test_validate_markdown_exactly_three_lines(self, tmp_path):
        """Minimal valid markdown with frontmatter: just opening, content, closing."""
        md = tmp_path / "minimal.md"
        md.write_text("---\nname: test\n---\n")
        assert update_yaml.validate_file(str(md), "markdown") is True

    def test_validate_markdown_too_short(self, tmp_path):
        """Markdown with only 2 lines cannot have valid frontmatter."""
        md = tmp_path / "short.md"
        md.write_text("---\nname: test")
        assert update_yaml.validate_file(str(md), "markdown") is False

    def test_validate_python_with_shebang(self, tmp_path):
        """Python file with shebang should be valid."""
        py = tmp_path / "test.py"
        py.write_text("#!/usr/bin/env python3\nprint('hello')\n")
        assert update_yaml.validate_file(str(py), "python") is True
