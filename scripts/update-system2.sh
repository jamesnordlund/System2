#!/usr/bin/env bash
# update-system2.sh — Update System2 agent/mode definitions from upstream.
#
# Usage: bash scripts/update-system2.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run          Show what would change without applying
#   --scope <value>    Override scope detection: project, global, or both
#   --force            Skip version check, re-download all files
#   --repo-url <url>   Override upstream repo URL
#   --branch <branch>  Override upstream branch (default: main)
#   --help             Show usage
#
# EXIT CODES:
#   0  Success (or already up to date)
#   1  General error
#   2  Network failure
#   3  Validation failure
#   4  Missing dependency

set -euo pipefail

# ─── Configuration ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_REPO_URL="https://github.com/jamesnordlund/System2"
DEFAULT_BRANCH="main"

REPO_URL="${DEFAULT_REPO_URL}"
BRANCH="${DEFAULT_BRANCH}"
DRY_RUN=false
FORCE=false
SCOPE_OVERRIDE=""

CURL_TIMEOUT=30
LOCK_FILE=""
TEMP_DIR=""

# Global arrays for copy tracking (initialized empty)
COPY_ADDED=()
COPY_MODIFIED=()
COPY_FAILED=()

# ─── Cleanup ────────────────────────────────────────────────────────────────
cleanup() {
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
    if [[ -n "$LOCK_FILE" && -f "$LOCK_FILE" ]]; then
        rm -f "$LOCK_FILE"
    fi
}
trap cleanup EXIT

# ─── Logging helpers ────────────────────────────────────────────────────────
info()  { echo "[update-system2] $*"; }
warn()  { echo "[update-system2] WARNING: $*" >&2; }
error() { echo "[update-system2] ERROR: $*" >&2; }

# ─── Usage ──────────────────────────────────────────────────────────────────
usage() {
    cat <<'EOF'
Usage: bash scripts/update-system2.sh [OPTIONS]

Update System2 agent/mode definitions from the upstream repository.

OPTIONS:
  --dry-run          Show what would change without applying
  --scope <value>    Override scope detection: project, global, or both
  --force            Skip version check, re-download all files
  --repo-url <url>   Override upstream GitHub repo URL
  --branch <branch>  Override upstream branch (default: main)
  --help             Show this help message

EXIT CODES:
  0  Success (or already up to date)
  1  General error
  2  Network failure
  3  Validation failure
  4  Missing dependency (e.g., python3 for YAML merge)
EOF
}

# ─── Argument parsing ───────────────────────────────────────────────────────
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --scope)
                if [[ -z "${2:-}" ]]; then
                    error "--scope requires a value: project, global, or both"
                    exit 1
                fi
                case "$2" in
                    project|global|both)
                        SCOPE_OVERRIDE="$2"
                        ;;
                    *)
                        error "Invalid scope: $2 (must be project, global, or both)"
                        exit 1
                        ;;
                esac
                shift 2
                ;;
            --repo-url)
                if [[ -z "${2:-}" ]]; then
                    error "--repo-url requires a value"
                    exit 1
                fi
                # Warn if non-HTTPS (allow localhost/127.0.0.1 for testing)
                if [[ "$2" != https://* && "$2" != http://localhost* && "$2" != http://127.0.0.1* ]]; then
                    warn "Non-HTTPS repo URL detected: $2"
                    warn "Downloads will not be encrypted. Use HTTPS in production."
                fi
                REPO_URL="$2"
                shift 2
                ;;
            --branch)
                if [[ -z "${2:-}" ]]; then
                    error "--branch requires a value"
                    exit 1
                fi
                BRANCH="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# ─── Raw URL construction ──────────────────────────────────────────────────
raw_url() {
    local path="$1"
    # If repo URL is not a GitHub URL, use it directly (for testing / custom hosting)
    if [[ "$REPO_URL" != *"github.com"* ]]; then
        echo "${REPO_URL%/}/${BRANCH}/${path}"
        return
    fi
    # Convert github.com URL to raw.githubusercontent.com URL
    local repo_url="$REPO_URL"
    repo_url="${repo_url#https://github.com/}"
    repo_url="${repo_url%.git}"
    echo "https://raw.githubusercontent.com/${repo_url}/${BRANCH}/${path}"
}

# ─── Network fetch ──────────────────────────────────────────────────────────
fetch_file() {
    local url="$1"
    local output="$2"
    local description="${3:-file}"

    # Ensure parent directory exists
    mkdir -p "$(dirname "$output")"

    if ! curl --fail --silent --show-error --max-time "$CURL_TIMEOUT" \
         --proto '=https' --location -o "$output" "$url"; then
        error "Failed to download $description from: $url"
        return 1
    fi
}

# ─── Lock file ──────────────────────────────────────────────────────────────
acquire_lock() {
    LOCK_FILE="${INSTALL_ROOT}/.system2-update.lock"

    if [[ -f "$LOCK_FILE" ]]; then
        local lock_age
        if [[ "$(uname)" == "Darwin" ]]; then
            lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_FILE") ))
        else
            lock_age=$(( $(date +%s) - $(stat -c %Y "$LOCK_FILE") ))
        fi

        if (( lock_age < 600 )); then
            error "Another update appears to be in progress (lock file is ${lock_age}s old)."
            error "If this is stale, remove: $LOCK_FILE"
            exit 1
        else
            warn "Removing stale lock file (${lock_age}s old)"
            rm -f "$LOCK_FILE"
        fi
    fi

    echo "$$" > "$LOCK_FILE"
}

# ─── Version check ──────────────────────────────────────────────────────────
check_version() {
    local version_url
    version_url="$(raw_url "VERSION")"

    local upstream_version
    if ! upstream_version=$(curl --fail --silent --show-error --max-time "$CURL_TIMEOUT" "$version_url"); then
        warn "Could not fetch upstream VERSION file from: $version_url"
        if [[ "$FORCE" == true ]]; then
            info "Proceeding with --force (version check skipped)"
            echo "unknown"
            return 0
        else
            error "Use --force to skip version check and proceed anyway."
            exit 2
        fi
    fi

    upstream_version="$(echo "$upstream_version" | tr -d '[:space:]')"

    local local_version="unknown"
    local version_file="${INSTALL_ROOT}/.system2-version"
    if [[ -f "$version_file" ]]; then
        local_version="$(cat "$version_file" | tr -d '[:space:]')"
    fi

    if [[ "$FORCE" != true && "$upstream_version" == "$local_version" ]]; then
        info "Already up to date (version $local_version)" >&2
        # Exit subshell with empty stdout — main detects this
        exit 0
    fi

    info "Update available: $local_version -> $upstream_version" >&2
    echo "$upstream_version"
}

# ─── Manifest fetch and parse ───────────────────────────────────────────────
fetch_manifest() {
    local manifest_url
    manifest_url="$(raw_url "manifest.json")"

    local manifest_file="${TEMP_DIR}/manifest.json"
    if ! fetch_file "$manifest_url" "$manifest_file" "manifest.json"; then
        exit 2
    fi

    # Parse manifest using python3
    if ! command -v python3 &>/dev/null; then
        error "python3 is required to parse manifest.json"
        exit 4
    fi

    MANIFEST_FILE="$manifest_file" python3 -c '
import json, os, sys
try:
    data = json.load(open(os.environ["MANIFEST_FILE"]))
    assert "files" in data, "Missing files key"
    for f in data["files"]:
        print(f["path"] + "|" + f["platform"] + "|" + f["scope"] + "|" + f["validation"] + "|" + f.get("description", ""))
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
'
}

# ─── Scope detection ────────────────────────────────────────────────────────
detect_scope() {
    local has_project=false
    local has_global=false

    # Claude Code project-level
    if [[ -d "${INSTALL_ROOT}/.claude/agents" ]]; then
        has_project=true
    fi

    # Roo Code project-level
    if [[ -f "${INSTALL_ROOT}/.roomodes" ]]; then
        has_project=true
    fi

    # Claude Code user-level
    if [[ -d "$HOME/.claude/agents" ]]; then
        has_global=true
    fi

    # Roo Code global-level (macOS)
    local roo_global_config=""
    roo_global_config="$(find_roo_global_config)"
    if [[ -n "$roo_global_config" ]]; then
        has_global=true
    fi

    if [[ -n "$SCOPE_OVERRIDE" ]]; then
        echo "$SCOPE_OVERRIDE"
        return
    fi

    if [[ "$has_project" == true && "$has_global" == true ]]; then
        echo "both"
    elif [[ "$has_project" == true ]]; then
        echo "project"
    elif [[ "$has_global" == true ]]; then
        echo "global"
    else
        # No existing installation detected — default to project
        echo "project"
    fi
}

# ─── Roo Code global config discovery ──────────────────────────────────────
find_roo_global_config() {
    # Check environment variable override first
    if [[ -n "${ROO_GLOBAL_CONFIG:-}" && -f "$ROO_GLOBAL_CONFIG" ]]; then
        echo "$ROO_GLOBAL_CONFIG"
        return
    fi

    # macOS path
    local mac_path="$HOME/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/custom_modes.yaml"
    if [[ -f "$mac_path" ]]; then
        echo "$mac_path"
        return
    fi

    # Linux path
    local linux_path="$HOME/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/custom_modes.yaml"
    if [[ -f "$linux_path" ]]; then
        echo "$linux_path"
        return
    fi

    # Not found
    echo ""
}

# ─── Path validation ───────────────────────────────────────────────────────
validate_manifest_path() {
    local path="$1"

    # Reject absolute paths
    if [[ "$path" == /* ]]; then
        error "Manifest contains absolute path (rejected): $path"
        return 1
    fi

    # Reject path traversal
    if [[ "$path" == *".."* ]]; then
        error "Manifest contains path traversal (rejected): $path"
        return 1
    fi

    # Validate characters: only alphanumeric, dots, hyphens, underscores, slashes
    if ! echo "$path" | grep -qE '^[a-zA-Z0-9._/-]+$'; then
        error "Manifest contains invalid characters in path (rejected): $path"
        return 1
    fi

    return 0
}

# ─── Allowed write paths check ──────────────────────────────────────────────
check_write_allowed() {
    local dest_path="$1"
    local abs_path
    # Resolve to absolute path
    local parent_dir
    parent_dir="$(dirname "$dest_path")"
    if [[ -d "$parent_dir" ]]; then
        abs_path="$(cd "$parent_dir" && pwd)/$(basename "$dest_path")"
    elif [[ "$dest_path" == /* ]]; then
        # Already absolute, parent just doesn't exist yet
        abs_path="$dest_path"
    else
        # Relative path, resolve against INSTALL_ROOT
        abs_path="${INSTALL_ROOT}/${dest_path}"
    fi

    local allowed_prefixes=(
        "${INSTALL_ROOT}/.claude/"
        "${INSTALL_ROOT}/.roo/"
        "${INSTALL_ROOT}/scripts/"
        "${INSTALL_ROOT}/CLAUDE.md"
        "${INSTALL_ROOT}/.roomodes"
        "${INSTALL_ROOT}/.system2-version"
        "${INSTALL_ROOT}/.system2-update.log"
        "${INSTALL_ROOT}/.system2-backup/"
        "${INSTALL_ROOT}/roo/"
        "$HOME/.claude/"
        "$HOME/.roo/"
        "$HOME/.system2-version"
        "$HOME/.system2-update.log"
        "$HOME/.system2-backup/"
    )

    # Add Roo global config path if known
    local roo_global
    roo_global="$(find_roo_global_config)"
    if [[ -n "$roo_global" ]]; then
        allowed_prefixes+=("$(dirname "$roo_global")/")
    fi

    for prefix in "${allowed_prefixes[@]}"; do
        if [[ "$abs_path" == "$prefix"* || "$abs_path" == "$prefix" ]]; then
            return 0
        fi
    done

    error "Write to path not allowed: $dest_path (resolved: $abs_path)"
    return 1
}

# ─── Content validation ─────────────────────────────────────────────────────
validate_downloaded_files() {
    local temp_dir="$1"
    shift
    # Remaining args: "path|validation" pairs
    local failed=false

    for entry in "$@"; do
        local path="${entry%%|*}"
        local validation="${entry##*|}"
        local file="${temp_dir}/${path}"

        if [[ ! -f "$file" ]]; then
            continue
        fi

        case "$validation" in
            yaml|markdown|json)
                if ! python3 "${SCRIPT_DIR}/update-system2-yaml.py" validate \
                    --file "$file" --type "$validation"; then
                    failed=true
                fi
                ;;
            shell)
                local first_line
                first_line="$(head -1 "$file")"
                if [[ "$first_line" != *"#!/bin/bash"* && "$first_line" != *"#!/usr/bin/env bash"* ]]; then
                    error "Shell script missing bash shebang: $path"
                    failed=true
                fi
                ;;
            python)
                # Just check it's non-empty
                if [[ ! -s "$file" ]]; then
                    error "Python file is empty: $path"
                    failed=true
                fi
                ;;
            none|*)
                # No validation needed
                ;;
        esac
    done

    if [[ "$failed" == true ]]; then
        error "Content validation failed. Update aborted."
        exit 3
    fi
}

# ─── Backup ─────────────────────────────────────────────────────────────────
create_backup() {
    local backup_root="$1"
    shift
    # Remaining args: files to back up (absolute paths)

    local timestamp
    timestamp="$(date -u +%Y-%m-%dT%H%M%S)"
    local backup_dir="${backup_root}/.system2-backup/${timestamp}"

    mkdir -p "$backup_dir"

    for file in "$@"; do
        if [[ -f "$file" ]]; then
            local rel_path="${file#"$backup_root"/}"
            local backup_file="${backup_dir}/${rel_path}"
            mkdir -p "$(dirname "$backup_file")"
            cp "$file" "$backup_file"
        fi
    done

    info "Backup created at: $backup_dir" >&2
    echo "$backup_dir"
}

# ─── File copy ──────────────────────────────────────────────────────────────
copy_files() {
    local temp_dir="$1"
    local dest_root="$2"
    shift 2
    # Remaining args: relative paths to copy

    local files_added=()
    local files_modified=()
    local files_failed=()

    for rel_path in "$@"; do
        local src="${temp_dir}/${rel_path}"
        local dest="${dest_root}/${rel_path}"

        if [[ ! -f "$src" ]]; then
            continue
        fi

        # Check write is allowed
        if ! check_write_allowed "$dest"; then
            files_failed+=("$rel_path")
            continue
        fi

        # Track add vs modify
        if [[ -f "$dest" ]]; then
            files_modified+=("$rel_path")
        else
            files_added+=("$rel_path")
        fi

        mkdir -p "$(dirname "$dest")"
        if ! cp "$src" "$dest"; then
            error "Failed to copy: $rel_path"
            files_failed+=("$rel_path")
        fi
    done

    # Report results
    if [[ ${#files_failed[@]} -gt 0 ]]; then
        error "Some files failed to copy:"
        for f in ${files_failed[@]+"${files_failed[@]}"}; do
            error "  - $f"
        done
        error "Backup was preserved for manual recovery."
    fi

    # Return stats via global arrays (use ${arr[@]+...} for bash 3.2 set -u compat)
    COPY_ADDED=(${files_added[@]+"${files_added[@]}"})
    COPY_MODIFIED=(${files_modified[@]+"${files_modified[@]}"})
    COPY_FAILED=(${files_failed[@]+"${files_failed[@]}"})
}

# ─── Log entry ──────────────────────────────────────────────────────────────
write_log() {
    local log_file="$1"
    local outcome="$2"
    local prev_version="$3"
    local new_version="$4"
    local scope="$5"
    shift 5
    # Remaining: added files, then "---", then modified files

    cat >> "$log_file" <<EOF
--- UPDATE $(date -u +%Y-%m-%dT%H:%M:%SZ) ---
outcome: $outcome
previous_version: $prev_version
new_version: $new_version
scope: $scope
EOF

    if [[ ${#COPY_ADDED[@]} -gt 0 ]]; then
        echo "files_added:" >> "$log_file"
        for f in ${COPY_ADDED[@]+"${COPY_ADDED[@]}"}; do
            echo "  - $f" >> "$log_file"
        done
    else
        echo "files_added: (none)" >> "$log_file"
    fi

    if [[ ${#COPY_MODIFIED[@]} -gt 0 ]]; then
        echo "files_modified:" >> "$log_file"
        for f in ${COPY_MODIFIED[@]+"${COPY_MODIFIED[@]}"}; do
            echo "  - $f" >> "$log_file"
        done
    else
        echo "files_modified: (none)" >> "$log_file"
    fi

    if [[ ${#COPY_FAILED[@]} -gt 0 ]]; then
        echo "errors:" >> "$log_file"
        for f in ${COPY_FAILED[@]+"${COPY_FAILED[@]}"}; do
            echo "  - failed to copy: $f" >> "$log_file"
        done
    else
        echo "errors: (none)" >> "$log_file"
    fi
    echo "---" >> "$log_file"
    echo "" >> "$log_file"
}

# ─── Change summary ────────────────────────────────────────────────────────
print_summary() {
    local prev_version="$1"
    local new_version="$2"
    local backup_dir="$3"

    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  System2 Update Complete"
    echo "═══════════════════════════════════════════════════════"
    echo "  Version: $prev_version -> $new_version"
    echo ""

    if [[ ${#COPY_ADDED[@]} -gt 0 ]]; then
        echo "  Added (${#COPY_ADDED[@]}):"
        for f in ${COPY_ADDED[@]+"${COPY_ADDED[@]}"}; do
            echo "    + $f"
        done
    fi

    if [[ ${#COPY_MODIFIED[@]} -gt 0 ]]; then
        echo "  Modified (${#COPY_MODIFIED[@]}):"
        for f in ${COPY_MODIFIED[@]+"${COPY_MODIFIED[@]}"}; do
            echo "    ~ $f"
        done
    fi

    if [[ ${#COPY_ADDED[@]} -eq 0 && ${#COPY_MODIFIED[@]} -eq 0 ]]; then
        echo "  No file changes."
    fi

    echo ""
    echo "  Backup: $backup_dir"

    # Self-update notice
    local self_updated=false
    for f in ${COPY_MODIFIED[@]+"${COPY_MODIFIED[@]}"} ${COPY_ADDED[@]+"${COPY_ADDED[@]}"}; do
        if [[ "$f" == "scripts/update-system2.sh" || "$f" == *"/commands/update-system2.md" ]]; then
            self_updated=true
            break
        fi
    done

    if [[ "$self_updated" == true ]]; then
        echo ""
        echo "  NOTE: The update command itself was updated."
        echo "  Changes take effect on next invocation."
    fi

    echo "═══════════════════════════════════════════════════════"
    echo ""
}

# ─── Roo Code YAML merge ───────────────────────────────────────────────────
merge_roo_modes() {
    local existing_path="$1"
    local incoming_pack="$2"
    local output_path="$3"

    if ! command -v python3 &>/dev/null; then
        error "python3 is required for Roo Code mode updates (YAML merge)"
        exit 4
    fi

    info "Merging Roo Code modes: $existing_path"
    if ! python3 "${SCRIPT_DIR}/update-system2-yaml.py" merge \
        --existing "$existing_path" \
        --incoming "$incoming_pack" \
        --output "$output_path"; then
        error "YAML merge failed for: $existing_path"
        exit 3
    fi
}

# ─── Main ───────────────────────────────────────────────────────────────────
main() {
    parse_args "$@"

    info "System2 Update"
    info "Repository: $REPO_URL (branch: $BRANCH)"

    # Acquire lock
    acquire_lock

    # Version check
    local new_version
    new_version="$(check_version)" || exit $?
    # check_version exits with 0 when already up to date (printing message via info)
    # but $() runs in subshell so exit only terminates the subshell.
    # Detect the "already up to date" case by checking if new_version is empty.
    if [[ -z "$new_version" ]]; then
        exit 0
    fi

    local local_version="unknown"
    if [[ -f "${INSTALL_ROOT}/.system2-version" ]]; then
        local_version="$(cat "${INSTALL_ROOT}/.system2-version" | tr -d '[:space:]')"
    fi

    # Create temp directory
    TEMP_DIR="$(mktemp -d)" || {
        error "Failed to create temporary directory"
        exit 1
    }

    # Fetch and parse manifest
    info "Fetching manifest..."
    local manifest_entries
    manifest_entries="$(fetch_manifest)" || exit $?

    # Detect scope
    local scope
    scope="$(detect_scope)"
    info "Detected scope: $scope"

    # Detect active platforms based on installed targets
    local has_claude=false
    local has_roo=false
    if [[ -d "${INSTALL_ROOT}/.claude/agents" || -d "$HOME/.claude/agents" ]]; then
        has_claude=true
    fi
    if [[ -f "${INSTALL_ROOT}/.roomodes" || -n "$(find_roo_global_config)" ]]; then
        has_roo=true
    fi
    # If neither detected, default to both (fresh install)
    if [[ "$has_claude" == false && "$has_roo" == false ]]; then
        has_claude=true
        has_roo=true
    fi

    # Filter manifest by scope and platform, download files
    info "Downloading files..."
    local files_to_copy=()
    local validation_entries=()

    while IFS='|' read -r path platform file_scope validation description; do
        # Skip files not matching active platform
        if [[ "$platform" != "all" ]]; then
            if [[ "$platform" == "claude" && "$has_claude" == false ]]; then
                continue
            fi
            if [[ "$platform" == "roo" && "$has_roo" == false ]]; then
                continue
            fi
        fi

        # Skip files not matching scope
        if [[ "$file_scope" != "all" ]]; then
            case "$scope" in
                project)
                    [[ "$file_scope" != "project" ]] && continue
                    ;;
                global)
                    [[ "$file_scope" != "global" ]] && continue
                    ;;
                both)
                    # Include all scopes
                    ;;
            esac
        fi

        # Validate path
        if ! validate_manifest_path "$path"; then
            exit 3
        fi

        # Download
        local url
        url="$(raw_url "$path")"
        local dest="${TEMP_DIR}/${path}"

        if ! fetch_file "$url" "$dest" "$description"; then
            error "Download failed. Update aborted. No files were modified."
            exit 2
        fi

        files_to_copy+=("$path")
        validation_entries+=("${path}|${validation}")

    done <<< "$manifest_entries"

    # Validate downloaded files
    info "Validating downloaded files..."
    validate_downloaded_files "$TEMP_DIR" ${validation_entries[@]+"${validation_entries[@]}"}

    # Handle Roo Code YAML merge if applicable
    local roo_pack_downloaded=false
    for f in ${files_to_copy[@]+"${files_to_copy[@]}"}; do
        if [[ "$f" == "roo/system2-pack.yml" ]]; then
            roo_pack_downloaded=true
            break
        fi
    done

    if [[ "$roo_pack_downloaded" == true ]]; then
        local incoming_pack="${TEMP_DIR}/roo/system2-pack.yml"

        # Project-level merge (.roomodes)
        if [[ "$scope" == "project" || "$scope" == "both" ]]; then
            if [[ -f "${INSTALL_ROOT}/.roomodes" ]]; then
                merge_roo_modes "${INSTALL_ROOT}/.roomodes" "$incoming_pack" "${TEMP_DIR}/.roomodes"
                # Replace pack in files_to_copy with merged .roomodes
                files_to_copy+=(".roomodes")
            fi
        fi

        # Global-level merge (custom_modes.yaml)
        if [[ "$scope" == "global" || "$scope" == "both" ]]; then
            local roo_global
            roo_global="$(find_roo_global_config)"
            if [[ -n "$roo_global" ]]; then
                local merged_global="${TEMP_DIR}/roo_global_merged.yaml"
                merge_roo_modes "$roo_global" "$incoming_pack" "$merged_global"
                # This file needs special handling — copy to the global config path
            fi
        fi
    fi

    # Dry-run: show what would change and exit
    if [[ "$DRY_RUN" == true ]]; then
        echo ""
        echo "DRY RUN: would update the following files:"
        for f in ${files_to_copy[@]+"${files_to_copy[@]}"}; do
            local dest="${INSTALL_ROOT}/${f}"
            if [[ -f "$dest" ]]; then
                echo "  ~ $f (modify)"
            else
                echo "  + $f (add)"
            fi
        done
        echo ""
        echo "No files were modified."
        exit 0
    fi

    # Create backup
    local files_to_backup=()
    for f in ${files_to_copy[@]+"${files_to_copy[@]}"}; do
        local existing="${INSTALL_ROOT}/${f}"
        if [[ -f "$existing" ]]; then
            files_to_backup+=("$existing")
        fi
    done

    local backup_dir=""
    if [[ ${#files_to_backup[@]} -gt 0 ]]; then
        backup_dir="$(create_backup "$INSTALL_ROOT" ${files_to_backup[@]+"${files_to_backup[@]}"})"
    else
        backup_dir="(no backup needed — all files are new)"
    fi

    # Copy files
    info "Applying update..."
    COPY_ADDED=()
    COPY_MODIFIED=()
    COPY_FAILED=()
    copy_files "$TEMP_DIR" "$INSTALL_ROOT" ${files_to_copy[@]+"${files_to_copy[@]}"}

    # Handle Roo global config separately if merged
    if [[ "$roo_pack_downloaded" == true && ("$scope" == "global" || "$scope" == "both") ]]; then
        local roo_global
        roo_global="$(find_roo_global_config)"
        if [[ -n "$roo_global" && -f "${TEMP_DIR}/roo_global_merged.yaml" ]]; then
            # Backup global config
            if [[ -f "$roo_global" ]]; then
                local global_backup_dir="${HOME}/.system2-backup/$(date -u +%Y-%m-%dT%H%M%S)"
                mkdir -p "$global_backup_dir"
                cp "$roo_global" "${global_backup_dir}/custom_modes.yaml"
                info "Global config backed up to: $global_backup_dir"
            fi
            if ! check_write_allowed "$roo_global"; then
                error "Roo global config path failed write allowlist check: $roo_global"
                exit 1
            fi
            cp "${TEMP_DIR}/roo_global_merged.yaml" "$roo_global"
            COPY_MODIFIED+=("(global) custom_modes.yaml")
            info "Roo Code global config updated. A VS Code window reload may be required."
        fi
    fi

    # Determine outcome based on copy results
    local outcome="success"
    if [[ ${#COPY_FAILED[@]} -gt 0 ]]; then
        outcome="partial_failure"
    fi

    # Only write version marker on full success — partial failure should
    # allow the next run to retry without --force
    if [[ "$outcome" == "success" ]]; then
        echo "$new_version" > "${INSTALL_ROOT}/.system2-version"
    fi

    # Write log
    write_log "${INSTALL_ROOT}/.system2-update.log" "$outcome" \
        "$local_version" "$new_version" "$scope"

    # Print summary
    print_summary "$local_version" "$new_version" "$backup_dir"

    if [[ ${#COPY_FAILED[@]} -gt 0 ]]; then
        error "Some files failed to copy. Check errors above."
        error "To restore from backup: cp -r ${backup_dir}/* ${INSTALL_ROOT}/"
        exit 1
    fi
}

main "$@"
