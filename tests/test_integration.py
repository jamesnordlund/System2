"""Integration tests for update-system2.sh using a real HTTP mock server.

These tests exercise the full update pipeline: version check, manifest fetch,
file download, validation, backup, copy, logging, and summary output.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "update-system2.sh"
YAML_HELPER = REPO_ROOT / "scripts" / "update-system2-yaml.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mock_server import start_server


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_upstream(tmp_path):
    """Create a mock upstream directory with System2 files."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()

    # VERSION
    (upstream / "VERSION").write_text("0.2.0")

    # Agent file
    agents_dir = upstream / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "test-agent.md").write_text(
        "---\nname: test-agent\ndescription: Test agent\n---\n\nYou are a test agent.\n"
    )

    # CLAUDE.md (no frontmatter — validated as "none" in real manifest)
    (upstream / "CLAUDE.md").write_text("# Test Claude Instructions\n")

    # Update script
    scripts_dir = upstream / "scripts"
    scripts_dir.mkdir()
    shutil.copy(str(SCRIPT), str(scripts_dir / "update-system2.sh"))
    shutil.copy(str(YAML_HELPER), str(scripts_dir / "update-system2-yaml.py"))

    # Roo pack
    roo_dir = upstream / "roo"
    roo_dir.mkdir()
    roo_pack = {
        "customModes": [
            {
                "slug": "orchestrator",
                "name": "Orchestrator (System 2)",
                "description": "Updated orchestrator",
                "roleDefinition": "New role",
                "whenToUse": "Always",
                "customInstructions": "New instructions",
                "groups": [],
            },
            {
                "slug": "g-executor",
                "name": "Executor",
                "description": "Updated executor",
                "roleDefinition": "New role",
                "whenToUse": "For implementation",
                "customInstructions": "New instructions",
                "groups": ["read", "edit"],
            },
        ]
    }
    with open(roo_dir / "system2-pack.yml", "w") as f:
        yaml.dump(roo_pack, f, default_flow_style=False)

    # manifest.json
    manifest = {
        "version": "0.2.0",
        "files": [
            {
                "path": ".claude/agents/test-agent.md",
                "platform": "claude",
                "scope": "project",
                "validation": "markdown",
                "description": "Test agent",
            },
            {
                "path": "CLAUDE.md",
                "platform": "claude",
                "scope": "project",
                "validation": "none",
                "description": "Claude instructions",
            },
            {
                "path": "scripts/update-system2.sh",
                "platform": "all",
                "scope": "project",
                "validation": "shell",
                "description": "Update script",
            },
            {
                "path": "scripts/update-system2-yaml.py",
                "platform": "all",
                "scope": "project",
                "validation": "python",
                "description": "YAML helper",
            },
            {
                "path": "roo/system2-pack.yml",
                "platform": "roo",
                "scope": "all",
                "validation": "yaml",
                "description": "Roo mode pack",
            },
        ],
    }
    (upstream / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return upstream


@pytest.fixture
def project_dir(tmp_path):
    """Create a mock project directory with System2 installed."""
    project = tmp_path / "project"
    project.mkdir()

    # Copy scripts
    scripts = project / "scripts"
    scripts.mkdir()
    shutil.copy(str(SCRIPT), str(scripts / "update-system2.sh"))
    shutil.copy(str(YAML_HELPER), str(scripts / "update-system2-yaml.py"))
    os.chmod(str(scripts / "update-system2.sh"), 0o755)

    # Create .claude/agents
    agents = project / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "test-agent.md").write_text(
        "---\nname: test-agent\ndescription: Old agent\n---\n\nOld content.\n"
    )

    # CLAUDE.md
    (project / "CLAUDE.md").write_text("# Old Claude Instructions\n")

    # Version marker
    (project / ".system2-version").write_text("0.1.0")

    return project


@pytest.fixture
def server(mock_upstream):
    """Start mock HTTP server."""
    srv, base_url = start_server(mock_upstream)
    yield base_url
    srv.shutdown()


def _run_update(project_dir, server_url, *extra_args):
    """Run the update script against the mock server."""
    env = os.environ.copy()
    env["HOME"] = str(project_dir.parent / "fakehome")
    os.makedirs(env["HOME"], exist_ok=True)

    # Ensure venv python3 is in PATH so PyYAML is available for validation
    venv_bin = REPO_ROOT / ".venv" / "bin"
    if venv_bin.exists():
        env["PATH"] = str(venv_bin) + ":" + env.get("PATH", "")

    script = str(project_dir / "scripts" / "update-system2.sh")

    result = subprocess.run(
        ["bash", script, "--repo-url", server_url, "--scope", "project"] + list(extra_args),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result


# ── Tests ────────────────────────────────────────────────────────────────────


class TestFullUpdate:
    def test_claude_code_project_update(self, project_dir, server):
        result = _run_update(project_dir, server)
        combined = result.stdout + result.stderr

        assert result.returncode == 0, f"Update failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "Update available: 0.1.0 -> 0.2.0" in combined

        # Agent file should be updated
        agent = (project_dir / ".claude" / "agents" / "test-agent.md").read_text()
        assert "Test agent" in agent  # New description

        # Version marker should be updated
        assert (project_dir / ".system2-version").read_text().strip() == "0.2.0"

        # Log should exist
        assert (project_dir / ".system2-update.log").exists()
        log = (project_dir / ".system2-update.log").read_text()
        assert "outcome: success" in log
        assert "new_version: 0.2.0" in log

        # Backup should exist
        backup_dir = project_dir / ".system2-backup"
        assert backup_dir.exists()

    def test_already_up_to_date(self, project_dir, server):
        (project_dir / ".system2-version").write_text("0.2.0")
        result = _run_update(project_dir, server)
        combined = result.stdout + result.stderr

        assert result.returncode == 0
        assert "Already up to date" in combined

    def test_dry_run_no_changes(self, project_dir, server):
        old_agent = (project_dir / ".claude" / "agents" / "test-agent.md").read_text()
        result = _run_update(project_dir, server, "--dry-run")
        combined = result.stdout + result.stderr

        assert result.returncode == 0
        assert "DRY RUN" in combined
        assert "No files were modified" in combined

        # File should NOT be changed
        assert (project_dir / ".claude" / "agents" / "test-agent.md").read_text() == old_agent
        # Version should NOT be updated
        assert (project_dir / ".system2-version").read_text().strip() == "0.1.0"

    def test_force_update_despite_matching_version(self, project_dir, server):
        (project_dir / ".system2-version").write_text("0.2.0")
        result = _run_update(project_dir, server, "--force")
        combined = result.stdout + result.stderr

        assert result.returncode == 0
        assert "Already up to date" not in combined

    def test_first_time_install_no_version_file(self, project_dir, server):
        (project_dir / ".system2-version").unlink()
        result = _run_update(project_dir, server)
        combined = result.stdout + result.stderr

        assert result.returncode == 0
        assert "Update available: unknown -> 0.2.0" in combined
        assert (project_dir / ".system2-version").read_text().strip() == "0.2.0"

    def test_backup_preserves_original(self, project_dir, server):
        original = (project_dir / ".claude" / "agents" / "test-agent.md").read_text()
        result = _run_update(project_dir, server)
        assert result.returncode == 0

        # Find backup
        backup_dir = project_dir / ".system2-backup"
        backups = list(backup_dir.iterdir())
        assert len(backups) == 1

        backed_up = (backups[0] / ".claude" / "agents" / "test-agent.md").read_text()
        assert backed_up == original

    def test_self_update_notice(self, project_dir, server):
        result = _run_update(project_dir, server)
        combined = result.stdout + result.stderr

        assert result.returncode == 0
        assert "update command itself was updated" in combined


class TestNetworkFailures:
    def test_download_failure_aborts(self, mock_upstream, project_dir):
        """When a file download fails, the update should abort without modifying files."""
        srv, base_url = start_server(mock_upstream, fail_paths={"test-agent.md"})
        try:
            result = _run_update(project_dir, base_url)
            assert result.returncode != 0

            # Original file should be unchanged
            agent = (project_dir / ".claude" / "agents" / "test-agent.md").read_text()
            assert "Old agent" in agent  # Still the old content

            # Version should not be updated
            assert (project_dir / ".system2-version").read_text().strip() == "0.1.0"
        finally:
            srv.shutdown()


class TestValidationFailure:
    """REQ-042, REQ-023: Validation failure aborts update, no files modified."""

    def test_invalid_yaml_aborts_update(self, mock_upstream, project_dir):
        """When a downloaded YAML file fails validation, the update aborts."""
        # Corrupt the roo pack to be invalid YAML
        roo_pack = mock_upstream / "roo" / "system2-pack.yml"
        roo_pack.write_text("this is not valid yaml: [\nunclosed bracket")

        # Ensure roo platform is detected so the pack file is actually downloaded
        (project_dir / ".roomodes").write_text("{}")

        srv, base_url = start_server(mock_upstream)
        try:
            result = _run_update(project_dir, base_url)
            combined = result.stdout + result.stderr

            assert result.returncode != 0, (
                f"Expected non-zero exit for invalid YAML\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )

            # Version should NOT be updated
            assert (project_dir / ".system2-version").read_text().strip() == "0.1.0"
        finally:
            srv.shutdown()

    def test_invalid_markdown_aborts_update(self, mock_upstream, project_dir):
        """When a downloaded markdown file fails frontmatter validation, the update aborts."""
        # Corrupt the agent markdown to have no frontmatter
        agent = mock_upstream / ".claude" / "agents" / "test-agent.md"
        agent.write_text("No frontmatter here, just text.")

        srv, base_url = start_server(mock_upstream)
        try:
            result = _run_update(project_dir, base_url)
            combined = result.stdout + result.stderr

            assert result.returncode != 0, (
                f"Expected non-zero exit for invalid markdown\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )

            # Original agent should be unchanged
            original_agent = (project_dir / ".claude" / "agents" / "test-agent.md").read_text()
            assert "Old agent" in original_agent
        finally:
            srv.shutdown()


class TestLogEntryCompleteness:
    """REQ-054: Log entry must contain all required fields."""

    def test_log_contains_all_required_fields(self, project_dir, server):
        result = _run_update(project_dir, server)
        assert result.returncode == 0

        log = (project_dir / ".system2-update.log").read_text()

        # Required fields per REQ-054
        assert "outcome: success" in log
        assert "previous_version: 0.1.0" in log
        assert "new_version: 0.2.0" in log
        assert "scope: project" in log
        assert "files_added:" in log or "files_modified:" in log
        assert "--- UPDATE" in log


class TestIdempotency:
    def test_double_update(self, project_dir, server):
        """Running update twice — second time should be 'already up to date'."""
        result1 = _run_update(project_dir, server)
        assert result1.returncode == 0

        result2 = _run_update(project_dir, server)
        combined2 = result2.stdout + result2.stderr
        assert result2.returncode == 0
        assert "Already up to date" in combined2
