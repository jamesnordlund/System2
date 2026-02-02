"""Tests for scripts/generate-manifest.py -- manifest generation logic.

Covers REQ-063, REQ-064: The manifest.json must list all distributable files
with correct metadata (path, platform, scope, validation, description).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "generate-manifest.py"

# Import the module under test
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import importlib

gen_manifest = importlib.import_module("generate-manifest")


# ---- Unit tests for derive_description ----


class TestDeriveDescription:
    def test_agent_file(self):
        desc = gen_manifest.derive_description(".claude/agents/spec-coordinator.md")
        assert "agent definition" in desc.lower()
        assert "Spec Coordinator" in desc

    def test_allowlist_file(self):
        desc = gen_manifest.derive_description(".claude/allowlists/edit-allow.txt")
        assert "allowlist" in desc.lower()

    def test_claude_command(self):
        desc = gen_manifest.derive_description(".claude/commands/update-system2.md")
        assert "slash command" in desc.lower()
        assert "Claude Code" in desc

    def test_roo_command(self):
        desc = gen_manifest.derive_description(".roo/commands/update-system2.md")
        assert "slash command" in desc.lower()
        assert "Roo Code" in desc

    def test_hook_script(self):
        desc = gen_manifest.derive_description("scripts/claude-hooks/pre-commit.py")
        assert "hook script" in desc.lower()

    def test_hook_regex(self):
        desc = gen_manifest.derive_description("scripts/claude-hooks/allow-pattern.regex")
        assert "hook pattern" in desc.lower()

    def test_known_explicit_file(self):
        desc = gen_manifest.derive_description("scripts/update-system2.sh")
        assert "Update script" in desc

    def test_unknown_file_fallback(self):
        desc = gen_manifest.derive_description("some/unknown/file.txt")
        # Should still produce something reasonable
        assert "File" in desc


# ---- Unit tests for collect_files ----


class TestCollectFiles:
    def test_collects_from_repo_root(self):
        """collect_files against the real repo root should find files."""
        files = gen_manifest.collect_files(REPO_ROOT, check_exists=False)
        paths = [f["path"] for f in files]

        # The update script is always included (explicit file)
        assert "scripts/update-system2.sh" in paths
        assert "scripts/update-system2-yaml.py" in paths

        # generate-manifest.py should be EXCLUDED
        assert "scripts/generate-manifest.py" not in paths

    def test_excludes_dev_tooling(self):
        files = gen_manifest.collect_files(REPO_ROOT, check_exists=False)
        paths = {f["path"] for f in files}
        for excluded in gen_manifest.EXCLUDE_FILES:
            assert excluded not in paths

    def test_no_duplicates(self):
        files = gen_manifest.collect_files(REPO_ROOT, check_exists=False)
        paths = [f["path"] for f in files]
        assert len(paths) == len(set(paths)), "Duplicate paths in manifest"

    def test_files_are_sorted(self):
        files = gen_manifest.collect_files(REPO_ROOT, check_exists=False)
        paths = [f["path"] for f in files]
        assert paths == sorted(paths)

    def test_required_fields_present(self):
        files = gen_manifest.collect_files(REPO_ROOT, check_exists=False)
        for f in files:
            assert "path" in f
            assert "platform" in f
            assert "scope" in f
            assert "validation" in f
            assert "description" in f

    def test_check_exists_with_missing_file(self, tmp_path):
        """When check_exists=True and files are missing, sys.exit(1) is called."""
        # Create a minimal repo structure with VERSION but no actual files
        (tmp_path / "VERSION").write_text("0.1.0")
        # No agent files etc. exist, but the EXPLICIT_FILES entries will be listed
        with pytest.raises(SystemExit) as exc_info:
            gen_manifest.collect_files(tmp_path, check_exists=True)
        assert exc_info.value.code == 1

    def test_collect_from_synthetic_repo(self, tmp_path):
        """Build a minimal repo structure and verify collection."""
        (tmp_path / "VERSION").write_text("1.0.0")

        # Create files matching FILE_RULES
        agents = tmp_path / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "test-agent.md").write_text("---\nname: test\n---\n")

        commands = tmp_path / ".claude" / "commands"
        commands.mkdir(parents=True)
        (commands / "update-system2.md").write_text("---\n---\nContent")

        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "update-system2.sh").write_text("#!/usr/bin/env bash\n")
        (scripts / "update-system2-yaml.py").write_text("print('hello')\n")

        files = gen_manifest.collect_files(tmp_path, check_exists=False)
        paths = [f["path"] for f in files]

        assert ".claude/agents/test-agent.md" in paths
        assert ".claude/commands/update-system2.md" in paths
        assert "scripts/update-system2.sh" in paths
        assert "scripts/update-system2-yaml.py" in paths


# ---- CLI tests ----


class TestGenerateManifestCLI:
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT)] + list(args),
            capture_output=True,
            text=True,
        )

    def test_generates_manifest_for_real_repo(self, tmp_path):
        output_file = tmp_path / "manifest.json"
        result = self._run(
            "--repo-root", str(REPO_ROOT),
            "--output", str(output_file),
        )
        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert output_file.exists()

        data = json.loads(output_file.read_text())
        assert "version" in data
        assert "files" in data
        assert isinstance(data["files"], list)
        assert len(data["files"]) > 0

    def test_version_in_manifest_matches_version_file(self, tmp_path):
        output_file = tmp_path / "manifest.json"
        result = self._run(
            "--repo-root", str(REPO_ROOT),
            "--output", str(output_file),
        )
        assert result.returncode == 0

        data = json.loads(output_file.read_text())
        expected_version = (REPO_ROOT / "VERSION").read_text().strip()
        assert data["version"] == expected_version

    def test_missing_version_file_exits_1(self, tmp_path):
        """Repo without VERSION file should fail."""
        result = self._run("--repo-root", str(tmp_path))
        assert result.returncode == 1
        assert "VERSION" in result.stderr

    def test_empty_version_file_exits_1(self, tmp_path):
        (tmp_path / "VERSION").write_text("")
        result = self._run("--repo-root", str(tmp_path))
        assert result.returncode == 1
        assert "empty" in result.stderr.lower()

    def test_check_exists_flag_with_valid_repo(self, tmp_path):
        """--check-exists with a real repo should pass (all files exist)."""
        output_file = tmp_path / "manifest.json"
        result = self._run(
            "--repo-root", str(REPO_ROOT),
            "--output", str(output_file),
            "--check-exists",
        )
        assert result.returncode == 0

    def test_invalid_repo_root(self, tmp_path):
        result = self._run("--repo-root", str(tmp_path / "nonexistent"))
        assert result.returncode == 1

    def test_output_is_valid_json(self, tmp_path):
        output_file = tmp_path / "manifest.json"
        self._run("--repo-root", str(REPO_ROOT), "--output", str(output_file))
        content = output_file.read_text()
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_manifest_file_entries_have_required_keys(self, tmp_path):
        output_file = tmp_path / "manifest.json"
        self._run("--repo-root", str(REPO_ROOT), "--output", str(output_file))
        data = json.loads(output_file.read_text())
        for entry in data["files"]:
            assert "path" in entry
            assert "platform" in entry
            assert "scope" in entry
            assert "validation" in entry
            assert "description" in entry
