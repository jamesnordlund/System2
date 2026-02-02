#!/usr/bin/env bats
# Tests for scripts/update-system2.sh

SCRIPT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="${SCRIPT_DIR}/scripts/update-system2.sh"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"

# ── Setup / Teardown ────────────────────────────────────────────────────────

setup() {
    TEST_TEMP="$(mktemp -d)"

    # Ensure venv python3 is available so PyYAML works
    SAVED_PATH="$PATH"
    if [[ -x "$VENV_PYTHON" ]]; then
        export PATH="$(dirname "$VENV_PYTHON"):$PATH"
    fi
    export HOME="$TEST_TEMP/fakehome"
    mkdir -p "$HOME"

    # Create a fake project directory
    PROJECT_DIR="$TEST_TEMP/project"
    mkdir -p "$PROJECT_DIR/scripts"
    mkdir -p "$PROJECT_DIR/.claude/agents"

    # Copy the script under test
    cp "$SCRIPT" "$PROJECT_DIR/scripts/update-system2.sh"
    chmod +x "$PROJECT_DIR/scripts/update-system2.sh"

    # Copy the YAML helper
    cp "$SCRIPT_DIR/scripts/update-system2-yaml.py" "$PROJECT_DIR/scripts/update-system2-yaml.py"

    # Create mock upstream files in a directory we'll serve or reference
    MOCK_UPSTREAM="$TEST_TEMP/upstream"
    mkdir -p "$MOCK_UPSTREAM"

    # VERSION
    echo "0.2.0" > "$MOCK_UPSTREAM/VERSION"

    # manifest.json
    cat > "$MOCK_UPSTREAM/manifest.json" <<'MANIFEST'
{
  "version": "0.2.0",
  "files": [
    {
      "path": ".claude/agents/test-agent.md",
      "platform": "claude",
      "scope": "project",
      "validation": "markdown",
      "description": "Test agent"
    },
    {
      "path": "scripts/update-system2.sh",
      "platform": "all",
      "scope": "project",
      "validation": "shell",
      "description": "Update script"
    }
  ]
}
MANIFEST

    # Mock agent file
    mkdir -p "$MOCK_UPSTREAM/.claude/agents"
    cat > "$MOCK_UPSTREAM/.claude/agents/test-agent.md" <<'AGENT'
---
name: test-agent
description: A test agent
---

You are a test agent.
AGENT

    # Mock update script (copies itself)
    mkdir -p "$MOCK_UPSTREAM/scripts"
    cp "$SCRIPT" "$MOCK_UPSTREAM/scripts/update-system2.sh"
}

teardown() {
    rm -rf "$TEST_TEMP"
}

# ── Helper: create a mock curl ──────────────────────────────────────────────

# Replace curl with a function that serves from MOCK_UPSTREAM
setup_mock_curl() {
    # Create a mock curl script
    cat > "$TEST_TEMP/mock-curl" <<MOCKCURL
#!/usr/bin/env bash
# Mock curl that serves files from MOCK_UPSTREAM
OUTPUT=""
URL=""
while [[ \$# -gt 0 ]]; do
    case "\$1" in
        -o) OUTPUT="\$2"; shift 2 ;;
        --fail|--silent|--show-error|--location) shift ;;
        --max-time) shift 2 ;;
        *) URL="\$1"; shift ;;
    esac
done

# Extract the path from the URL (everything after the first /main/)
REL_PATH="\${URL#*://*/main/}"

LOCAL_FILE="${MOCK_UPSTREAM}/\${REL_PATH}"

if [[ -f "\$LOCAL_FILE" ]]; then
    if [[ -n "\$OUTPUT" ]]; then
        mkdir -p "\$(dirname "\$OUTPUT")"
        cp "\$LOCAL_FILE" "\$OUTPUT"
    else
        cat "\$LOCAL_FILE"
    fi
    exit 0
else
    echo "curl: (22) The requested URL returned error: 404" >&2
    exit 22
fi
MOCKCURL
    chmod +x "$TEST_TEMP/mock-curl"

    # Copy mock as "curl" and prepend to PATH
    cp "$TEST_TEMP/mock-curl" "$TEST_TEMP/curl"
    chmod +x "$TEST_TEMP/curl"
    export PATH="$TEST_TEMP:$PATH"
}

# ── Arg parsing tests ───────────────────────────────────────────────────────

@test "--help exits 0 and prints usage" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
    [[ "$output" == *"--dry-run"* ]]
}

@test "-h also prints usage" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage"* ]]
}

@test "unknown flag exits 1" {
    run bash "$SCRIPT" --unknown-flag
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option"* ]]
}

@test "--scope without value exits 1" {
    run bash "$SCRIPT" --scope
    [ "$status" -eq 1 ]
    [[ "$output" == *"requires a value"* ]]
}

@test "--scope invalid value exits 1" {
    run bash "$SCRIPT" --scope invalid
    [ "$status" -eq 1 ]
    [[ "$output" == *"Invalid scope"* ]]
}

@test "--scope project is accepted" {
    # This will fail at network stage, but arg parsing should succeed
    setup_mock_curl
    # Set local version to match to trigger "already up to date"
    echo "0.2.0" > "$PROJECT_DIR/.system2-version"
    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    # Should exit 0 (already up to date) — proving --scope was parsed
    [ "$status" -eq 0 ]
    [[ "$output" == *"Already up to date"* ]]
}

# ── Version check tests ────────────────────────────────────────────────────

@test "matching version prints 'Already up to date' and exits 0" {
    setup_mock_curl
    echo "0.2.0" > "$PROJECT_DIR/.system2-version"
    run bash "$PROJECT_DIR/scripts/update-system2.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Already up to date"* ]]
}

@test "different version proceeds with update" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"
    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]
    [[ "$output" == *"Update available: 0.1.0 -> 0.2.0"* ]]
}

@test "missing .system2-version treats as 'unknown' and proceeds" {
    setup_mock_curl
    # Don't create .system2-version
    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]
    [[ "$output" == *"Update available: unknown -> 0.2.0"* ]]
}

@test "--force skips version check" {
    setup_mock_curl
    echo "0.2.0" > "$PROJECT_DIR/.system2-version"
    run bash "$PROJECT_DIR/scripts/update-system2.sh" --force --scope project
    [ "$status" -eq 0 ]
    # Should NOT say "Already up to date"
    [[ "$output" != *"Already up to date"* ]]
}

# ── Network failure tests ──────────────────────────────────────────────────

@test "network failure on VERSION exits 2 without --force" {
    # Use a curl that always fails
    cat > "$TEST_TEMP/curl" <<'FAILCURL'
#!/usr/bin/env bash
echo "curl: (28) Connection timed out" >&2
exit 28
FAILCURL
    chmod +x "$TEST_TEMP/curl"
    export PATH="$TEST_TEMP:$PATH"

    run bash "$PROJECT_DIR/scripts/update-system2.sh"
    [ "$status" -eq 2 ]
    [[ "$output" == *"--force"* ]]
}

@test "network failure on VERSION with --force proceeds" {
    # curl fails for VERSION but succeeds for manifest
    local call_count=0
    cat > "$TEST_TEMP/curl" <<PARTIALCURL
#!/usr/bin/env bash
# First call (VERSION) fails, subsequent calls serve from mock
URL=""
OUTPUT=""
while [[ \$# -gt 0 ]]; do
    case "\$1" in
        -o) OUTPUT="\$2"; shift 2 ;;
        --fail|--silent|--show-error|--location) shift ;;
        --max-time) shift 2 ;;
        *) URL="\$1"; shift ;;
    esac
done

if [[ "\$URL" == *"VERSION" ]]; then
    echo "curl: (28) timeout" >&2
    exit 28
fi

REL_PATH="\${URL#*://*/main/}"
LOCAL_FILE="${MOCK_UPSTREAM}/\${REL_PATH}"

if [[ -f "\$LOCAL_FILE" ]]; then
    if [[ -n "\$OUTPUT" ]]; then
        mkdir -p "\$(dirname "\$OUTPUT")"
        cp "\$LOCAL_FILE" "\$OUTPUT"
    else
        cat "\$LOCAL_FILE"
    fi
    exit 0
else
    exit 22
fi
PARTIALCURL
    chmod +x "$TEST_TEMP/curl"
    export PATH="$TEST_TEMP:$PATH"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --force --scope project
    [ "$status" -eq 0 ]
    [[ "$output" == *"version check skipped"* ]]
}

# ── Dry-run tests ──────────────────────────────────────────────────────────

@test "--dry-run shows changes but modifies nothing" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --dry-run --scope project
    [ "$status" -eq 0 ]
    [[ "$output" == *"DRY RUN"* ]]
    [[ "$output" == *"No files were modified"* ]]

    # Version file should NOT be updated
    [ "$(cat "$PROJECT_DIR/.system2-version")" = "0.1.0" ]
}

# ── Backup tests ──────────────────────────────────────────────────────────

@test "backup is created before overwriting files" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    # Create existing file that will be overwritten
    mkdir -p "$PROJECT_DIR/.claude/agents"
    echo "old content" > "$PROJECT_DIR/.claude/agents/test-agent.md"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]

    # Backup directory should exist
    [ -d "$PROJECT_DIR/.system2-backup" ]

    # Find backup dir (timestamped)
    local backup_dir
    backup_dir=$(ls -d "$PROJECT_DIR/.system2-backup"/*/ 2>/dev/null | head -1)
    [ -n "$backup_dir" ]

    # Original file should be backed up
    [ -f "${backup_dir}.claude/agents/test-agent.md" ]
    [ "$(cat "${backup_dir}.claude/agents/test-agent.md")" = "old content" ]
}

# ── Path validation tests ──────────────────────────────────────────────────

@test "path traversal in manifest is rejected" {
    setup_mock_curl
    # Modify manifest to include a path traversal
    cat > "$MOCK_UPSTREAM/manifest.json" <<'BADMANIFEST'
{
  "version": "0.2.0",
  "files": [
    {
      "path": "../etc/passwd",
      "platform": "all",
      "scope": "project",
      "validation": "none",
      "description": "Malicious file"
    }
  ]
}
BADMANIFEST
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 3 ]
    [[ "$output" == *"path traversal"* ]]
}

@test "absolute path in manifest is rejected" {
    setup_mock_curl
    cat > "$MOCK_UPSTREAM/manifest.json" <<'BADMANIFEST'
{
  "version": "0.2.0",
  "files": [
    {
      "path": "/etc/passwd",
      "platform": "all",
      "scope": "project",
      "validation": "none",
      "description": "Malicious file"
    }
  ]
}
BADMANIFEST
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 3 ]
    [[ "$output" == *"absolute path"* ]]
}

# ── Lock file tests ──────────────────────────────────────────────────────

@test "fresh lock file blocks concurrent update" {
    setup_mock_curl
    # Create a fresh lock file (less than 600 seconds old)
    echo "99999" > "$PROJECT_DIR/.system2-update.lock"

    run bash "$PROJECT_DIR/scripts/update-system2.sh"
    [ "$status" -eq 1 ]
    [[ "$output" == *"Another update"* ]]
}

# ── Self-update notice ──────────────────────────────────────────────────────

@test "self-update notice when update-system2.sh is modified" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]
    [[ "$output" == *"update command itself was updated"* ]]
}

# ── Log entry tests ─────────────────────────────────────────────────────────

@test "log entry is written after successful update" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]

    [ -f "$PROJECT_DIR/.system2-update.log" ]
    grep -q "outcome: success" "$PROJECT_DIR/.system2-update.log"
    grep -q "new_version: 0.2.0" "$PROJECT_DIR/.system2-update.log"
}

# ── Version marker tests ───────────────────────────────────────────────────

@test "version marker is updated after successful update" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]

    [ "$(cat "$PROJECT_DIR/.system2-version")" = "0.2.0" ]
}

# ── Idempotency ────────────────────────────────────────────────────────────

@test "running update twice - second time reports already up to date" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    # First run
    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]

    # Second run (version now matches)
    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]
    [[ "$output" == *"Already up to date"* ]]
}

# ── Static safety checks ────────────────────────────────────────────────────

@test "no eval on fetched content in script" {
    # Check that there's no 'eval' used to process fetched content
    # (eval for internal purposes like variable expansion is OK, eval on curl output is not)
    run grep -n 'eval.*curl\|eval.*\$.*fetch\|eval.*downloaded' "$SCRIPT"
    [ "$status" -eq 1 ]  # grep returns 1 when no matches (which is what we want)
}

@test "no pipe-to-shell on fetched content" {
    run grep -nE 'curl.*\|\s*(bash|sh|python)' "$SCRIPT"
    [ "$status" -eq 1 ]  # No matches expected
}

@test "all curl calls use HTTPS" {
    # Find all curl calls that reference a URL variable and ensure they resolve to https
    # The raw_url function builds https:// URLs, so we verify that function
    run grep -c 'https://raw.githubusercontent.com' "$SCRIPT"
    [ "$status" -eq 0 ]
    [ "$output" -ge 1 ]
}

@test "script passes bash -n syntax check" {
    run bash -n "$SCRIPT"
    [ "$status" -eq 0 ]
}

# ── Manifest path validation (additional) ───────────────────────────────────

@test "manifest path with special characters is rejected" {
    setup_mock_curl
    cat > "$MOCK_UPSTREAM/manifest.json" <<'BADMANIFEST'
{
  "version": "0.2.0",
  "files": [
    {
      "path": ".claude/agents/test agent (copy).md",
      "platform": "all",
      "scope": "project",
      "validation": "none",
      "description": "File with spaces and parens"
    }
  ]
}
BADMANIFEST
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 3 ]
    [[ "$output" == *"invalid characters"* ]]
}

# ── Log entry completeness (REQ-054) ──────────────────────────────────────

@test "log entry contains all required fields" {
    setup_mock_curl
    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    [ "$status" -eq 0 ]

    [ -f "$PROJECT_DIR/.system2-update.log" ]
    grep -q "outcome: success" "$PROJECT_DIR/.system2-update.log"
    grep -q "previous_version: 0.1.0" "$PROJECT_DIR/.system2-update.log"
    grep -q "new_version: 0.2.0" "$PROJECT_DIR/.system2-update.log"
    grep -q "scope: project" "$PROJECT_DIR/.system2-update.log"
    grep -q "files_added:\|files_modified:" "$PROJECT_DIR/.system2-update.log"
}

# ── --repo-url and --branch args ───────────────────────────────────────────

@test "--repo-url without value exits 1" {
    run bash "$SCRIPT" --repo-url
    [ "$status" -eq 1 ]
    [[ "$output" == *"requires a value"* ]]
}

@test "--branch without value exits 1" {
    run bash "$SCRIPT" --branch
    [ "$status" -eq 1 ]
    [[ "$output" == *"requires a value"* ]]
}

# ── write_log error reporting (S2 coverage) ─────────────────────────────────

@test "log entry contains error details when a file copy is rejected by write allowlist" {
    setup_mock_curl

    # Craft a manifest with one valid file and one file outside the allowed write paths.
    # "notallowed/bad.txt" passes validate_manifest_path but fails check_write_allowed.
    cat > "$MOCK_UPSTREAM/manifest.json" <<'MANIFEST'
{
  "version": "0.2.0",
  "files": [
    {
      "path": ".claude/agents/test-agent.md",
      "platform": "claude",
      "scope": "project",
      "validation": "markdown",
      "description": "Test agent"
    },
    {
      "path": "notallowed/bad.txt",
      "platform": "all",
      "scope": "project",
      "validation": "none",
      "description": "File outside allowed paths"
    }
  ]
}
MANIFEST

    # Create the upstream file so download succeeds (failure happens at copy stage)
    mkdir -p "$MOCK_UPSTREAM/notallowed"
    echo "should not land" > "$MOCK_UPSTREAM/notallowed/bad.txt"

    echo "0.1.0" > "$PROJECT_DIR/.system2-version"

    run bash "$PROJECT_DIR/scripts/update-system2.sh" --scope project
    # Script exits 1 because COPY_FAILED is non-empty
    [ "$status" -eq 1 ]

    # The log file must exist and contain the error entry for the rejected file
    [ -f "$PROJECT_DIR/.system2-update.log" ]
    grep -q "errors:" "$PROJECT_DIR/.system2-update.log"
    grep -q "failed to copy: notallowed/bad.txt" "$PROJECT_DIR/.system2-update.log"

    # The log must NOT say "errors: (none)" since there was a real failure
    ! grep -q "errors: (none)" "$PROJECT_DIR/.system2-update.log"
}
