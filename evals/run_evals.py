#!/usr/bin/env python3
"""
System2 v0.2.0 Plugin Migration Eval Harness

Deterministic structural assertions verifying the plugin conversion.
Uses only Python 3.8+ standard library. No external dependencies.

Usage:
    python3 evals/run_evals.py

Exit codes:
    0 - All evals pass
    1 - One or more evals fail
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve repo root relative to this script's location
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
GOLDENS_DIR = SCRIPT_DIR / "goldens"
PLUGIN_DIR = "plugin"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_golden(name: str) -> dict:
    """Load a golden JSON file from evals/goldens/."""
    path = GOLDENS_DIR / name
    with open(path) as f:
        return json.load(f)


def read_file(rel_path: str) -> str:
    """Read a file relative to repo root. Returns content or empty string if missing."""
    full = REPO_ROOT / rel_path
    if full.is_file():
        return full.read_text(encoding="utf-8", errors="replace")
    return ""


def list_files(rel_dir: str, suffix: str = "") -> List[str]:
    """List filenames in a directory relative to repo root, optionally filtered by suffix."""
    full = REPO_ROOT / rel_dir
    if not full.is_dir():
        return []
    files = [f.name for f in full.iterdir() if f.is_file()]
    if suffix:
        files = [f for f in files if f.endswith(suffix)]
    return sorted(files)


def dir_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).is_dir()


def file_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).is_file()


def grep_dir(rel_dir: str, pattern: str, file_suffix: str = "") -> List[Tuple[str, int, str]]:
    """Search files in a directory for a regex pattern. Returns list of (filename, lineno, line)."""
    results = []
    compiled = re.compile(pattern)
    full = REPO_ROOT / rel_dir
    if not full.is_dir():
        return results
    for fpath in sorted(full.rglob("*")):
        if not fpath.is_file():
            continue
        if file_suffix and not fpath.name.endswith(file_suffix):
            continue
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            if compiled.search(line):
                results.append((str(fpath.relative_to(REPO_ROOT)), i, line.strip()))
    return results


def grep_file(rel_path: str, pattern: str) -> List[Tuple[int, str]]:
    """Search a single file for a regex pattern. Returns list of (lineno, line)."""
    results = []
    content = read_file(rel_path)
    if not content:
        return results
    compiled = re.compile(pattern)
    for i, line in enumerate(content.splitlines(), 1):
        if compiled.search(line):
            results.append((i, line.strip()))
    return results


def extract_frontmatter(content: str) -> Optional[str]:
    """Extract YAML frontmatter from a Markdown file (content between first two --- lines)."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end < 0:
        return None
    return "\n".join(lines[1:end])


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

class EvalResult:
    def __init__(self, eval_id: str, description: str, passed: bool, message: str = ""):
        self.eval_id = eval_id
        self.description = description
        self.passed = passed
        self.message = message

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        msg = f"  [{status}] {self.eval_id}: {self.description}"
        if not self.passed and self.message:
            msg += f"\n         {self.message}"
        return msg


results: List[EvalResult] = []


def record(eval_id: str, description: str, passed: bool, message: str = ""):
    results.append(EvalResult(eval_id, description, passed, message))


# ---------------------------------------------------------------------------
# Eval implementations
# ---------------------------------------------------------------------------

def eval_path_001():
    """EVAL-PATH-001: Zero CLAUDE_PROJECT_DIR occurrences in agents/"""
    hits = grep_dir(f"{PLUGIN_DIR}/agents", r"CLAUDE_PROJECT_DIR")
    record(
        "EVAL-PATH-001",
        "Zero CLAUDE_PROJECT_DIR occurrences in agents/",
        len(hits) == 0,
        f"Found {len(hits)} occurrence(s): {hits[:3]}" if hits else "",
    )


def eval_path_002():
    """EVAL-PATH-002: Zero .claude/hooks or .claude/allowlists paths in agents/"""
    hits = grep_dir(f"{PLUGIN_DIR}/agents", r"\.claude/(hooks|allowlists)")
    record(
        "EVAL-PATH-002",
        "Zero .claude/(hooks|allowlists) paths in agents/",
        len(hits) == 0,
        f"Found {len(hits)} occurrence(s): {hits[:3]}" if hits else "",
    )


def eval_path_003():
    """EVAL-PATH-003: All hook commands use CLAUDE_PLUGIN_ROOT/hooks/"""
    golden = load_golden("agent_inventory.json")
    missing = []
    for filename in golden["agents"]:
        content = read_file(f"{PLUGIN_DIR}/agents/{filename}")
        fm = extract_frontmatter(content)
        if fm is None:
            missing.append(f"{filename}: no frontmatter")
            continue
        # Every agent has at least one hook referencing hooks/
        if "CLAUDE_PLUGIN_ROOT" not in fm:
            # code-reviewer still references hooks via CLAUDE_PLUGIN_ROOT
            missing.append(f"{filename}: no CLAUDE_PLUGIN_ROOT in frontmatter")
        elif 'CLAUDE_PLUGIN_ROOT}/hooks/' not in fm:
            missing.append(f"{filename}: CLAUDE_PLUGIN_ROOT present but no /hooks/ path")
    record(
        "EVAL-PATH-003",
        "All agent hook commands use CLAUDE_PLUGIN_ROOT/hooks/",
        len(missing) == 0,
        "; ".join(missing) if missing else "",
    )


def eval_path_004():
    """EVAL-PATH-004: All allowlist args use CLAUDE_PLUGIN_ROOT/allowlists/"""
    golden = load_golden("agent_allowlist_bindings.json")
    missing = []
    for agent_name, allowlist_file in golden["bindings"].items():
        filename = f"{agent_name}.md"
        content = read_file(f"{PLUGIN_DIR}/agents/{filename}")
        fm = extract_frontmatter(content)
        if fm is None:
            missing.append(f"{filename}: no frontmatter")
            continue
        expected_fragment = f"CLAUDE_PLUGIN_ROOT}}/allowlists/{allowlist_file}"
        if expected_fragment not in fm:
            missing.append(f"{filename}: expected allowlist ref to {allowlist_file}")
    # Agents without allowlist should NOT have allowlist references
    for agent_name in golden["agents_without_allowlist"]:
        filename = f"{agent_name}.md"
        content = read_file(f"{PLUGIN_DIR}/agents/{filename}")
        fm = extract_frontmatter(content) or ""
        if "allowlists/" in fm:
            missing.append(f"{filename}: should not reference allowlists/ but does")
    record(
        "EVAL-PATH-004",
        "All allowlist args use CLAUDE_PLUGIN_ROOT/allowlists/ with correct file",
        len(missing) == 0,
        "; ".join(missing) if missing else "",
    )


def eval_path_005():
    """EVAL-PATH-005: Hook command quoting follows expected pattern"""
    # Pattern: '...  "${CLAUDE_PLUGIN_ROOT}/hooks/...'  (double quote around variable+path)
    golden = load_golden("agent_inventory.json")
    bad_quoting = []
    pattern = re.compile(r'"?\$\{?CLAUDE_PLUGIN_ROOT\}?[^"]*"')
    expected_pattern = re.compile(r'"\$\{CLAUDE_PLUGIN_ROOT\}/(?:hooks|allowlists)/[^"]*"')
    for filename in golden["agents"]:
        content = read_file(f"{PLUGIN_DIR}/agents/{filename}")
        fm = extract_frontmatter(content)
        if fm is None:
            continue
        for line in fm.splitlines():
            if "CLAUDE_PLUGIN_ROOT" in line and "command:" in line:
                # Check that the variable is properly wrapped in braces and double-quoted
                if "${CLAUDE_PLUGIN_ROOT}" not in line:
                    bad_quoting.append(f"{filename}: missing braces in CLAUDE_PLUGIN_ROOT")
                elif not expected_pattern.search(line):
                    bad_quoting.append(f"{filename}: unexpected quoting: {line.strip()}")
    record(
        "EVAL-PATH-005",
        'Hook command quoting uses "${CLAUDE_PLUGIN_ROOT}/..." pattern',
        len(bad_quoting) == 0,
        "; ".join(bad_quoting[:5]) if bad_quoting else "",
    )


def eval_inv_001():
    """EVAL-INV-001: Exactly 13 named agent .md files in agents/"""
    golden = load_golden("agent_inventory.json")
    expected = set(golden["agents"].keys())
    actual = set(list_files(f"{PLUGIN_DIR}/agents", ".md"))
    missing = expected - actual
    extra = actual - expected
    record(
        "EVAL-INV-001",
        f"Exactly {golden['expected_count']} agent .md files in agents/",
        missing == set() and extra == set() and len(actual) == golden["expected_count"],
        f"missing={sorted(missing)}, extra={sorted(extra)}, count={len(actual)}"
        if missing or extra or len(actual) != golden["expected_count"]
        else "",
    )


def eval_inv_002():
    """EVAL-INV-002: Zero .md files in .claude/agents/"""
    stale = list_files(".claude/agents", ".md")
    record(
        "EVAL-INV-002",
        "Zero .md files in .claude/agents/",
        len(stale) == 0,
        f"Found {len(stale)} stale file(s): {stale}" if stale else "",
    )


def eval_inv_003():
    """EVAL-INV-003: Correct hook file counts in hooks/"""
    golden = load_golden("hook_inventory.json")
    actual_py = set(list_files(f"{PLUGIN_DIR}/hooks", ".py"))
    actual_regex = set(list_files(f"{PLUGIN_DIR}/hooks", ".regex"))
    expected_py = set(golden["python_files"])
    expected_regex = set(golden["regex_files"])
    missing_py = expected_py - actual_py
    extra_py = actual_py - expected_py
    missing_regex = expected_regex - actual_regex
    extra_regex = actual_regex - expected_regex
    ok = (
        len(actual_py) == golden["expected_py_count"]
        and len(actual_regex) == golden["expected_regex_count"]
        and not missing_py
        and not missing_regex
    )
    msg_parts = []
    if missing_py:
        msg_parts.append(f"missing py: {sorted(missing_py)}")
    if extra_py:
        msg_parts.append(f"extra py: {sorted(extra_py)}")
    if missing_regex:
        msg_parts.append(f"missing regex: {sorted(missing_regex)}")
    if extra_regex:
        msg_parts.append(f"extra regex: {sorted(extra_regex)}")
    record(
        "EVAL-INV-003",
        f"{golden['expected_py_count']} .py and {golden['expected_regex_count']} .regex files in hooks/",
        ok,
        "; ".join(msg_parts) if msg_parts else "",
    )


def eval_inv_004():
    """EVAL-INV-004: Correct allowlist file count in allowlists/"""
    golden = load_golden("allowlist_inventory.json")
    actual = set(list_files(f"{PLUGIN_DIR}/allowlists", ".regex"))
    expected = set(golden["files"])
    missing = expected - actual
    extra = actual - expected
    record(
        "EVAL-INV-004",
        f"Exactly {golden['expected_count']} .regex files in allowlists/",
        len(actual) == golden["expected_count"] and not missing,
        f"missing={sorted(missing)}, extra={sorted(extra)}, count={len(actual)}"
        if missing or extra or len(actual) != golden["expected_count"]
        else "",
    )


def eval_inv_005():
    """EVAL-INV-005: hooks/hooks.json does NOT exist"""
    exists = file_exists(f"{PLUGIN_DIR}/hooks/hooks.json")
    record(
        "EVAL-INV-005",
        "plugin/hooks/hooks.json does NOT exist",
        not exists,
        "plugin/hooks/hooks.json exists but should not" if exists else "",
    )


def eval_man_001():
    """EVAL-MAN-001: plugin.json valid JSON with correct fields"""
    golden = load_golden("manifest_schemas.json")
    path = golden["plugin_json"]["path"]
    errors = []
    content = read_file(path)
    if not content:
        errors.append(f"{path} does not exist or is empty")
    else:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"{path} is not valid JSON: {e}")
            data = None
        if data is not None:
            for field in golden["plugin_json"]["required_field_names"]:
                if field not in data:
                    errors.append(f"missing field: {field}")
            for field, expected in golden["plugin_json"]["required_fields"].items():
                # Support dotted keys for nested access (e.g. "author.name")
                parts = field.split(".")
                actual = data
                for part in parts:
                    actual = actual.get(part) if isinstance(actual, dict) else None
                if actual != expected:
                    errors.append(f"{field}: expected {expected!r}, got {actual!r}")
    record(
        "EVAL-MAN-001",
        "plugin.json valid JSON with correct fields",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_man_002():
    """EVAL-MAN-002: marketplace.json valid JSON with correct fields"""
    golden = load_golden("manifest_schemas.json")
    path = golden["marketplace_json"]["path"]
    errors = []
    content = read_file(path)
    if not content:
        errors.append(f"{path} does not exist or is empty")
    else:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"{path} is not valid JSON: {e}")
            data = None
        if data is not None:
            for field in golden["marketplace_json"]["required_field_names"]:
                if field not in data:
                    errors.append(f"missing field: {field}")
            for field, expected in golden["marketplace_json"]["required_fields"].items():
                actual = data.get(field)
                if actual != expected:
                    errors.append(f"{field}: expected {expected!r}, got {actual!r}")
            plugins = data.get("plugins", [])
            if not plugins:
                errors.append("plugins array is empty")
            elif plugins[0].get("source") != golden["marketplace_json"]["plugins_first_entry"]["source"]:
                errors.append(
                    f"plugins[0].source: expected {golden['marketplace_json']['plugins_first_entry']['source']!r}, "
                    f"got {plugins[0].get('source')!r}"
                )
    record(
        "EVAL-MAN-002",
        "marketplace.json valid JSON with correct fields",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_man_003():
    """EVAL-MAN-003: VERSION file matches plugin.json version"""
    golden = load_golden("manifest_schemas.json")
    version_content = read_file("VERSION").strip()
    plugin_content = read_file(golden["plugin_json"]["path"])
    errors = []
    if version_content != golden["version_file"]["expected_content"]:
        errors.append(f"VERSION: expected {golden['version_file']['expected_content']!r}, got {version_content!r}")
    try:
        plugin_data = json.loads(plugin_content) if plugin_content else {}
        plugin_version = plugin_data.get("version", "")
    except json.JSONDecodeError:
        plugin_version = ""
        errors.append("plugin.json is not valid JSON")
    if version_content != plugin_version:
        errors.append(f"VERSION ({version_content!r}) != plugin.json version ({plugin_version!r})")
    record(
        "EVAL-MAN-003",
        "VERSION file matches plugin.json version",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_tpl_001():
    """EVAL-TPL-001: skills/init/SKILL.md template content matches CLAUDE.md"""
    init_content = read_file(f"{PLUGIN_DIR}/skills/init/SKILL.md")
    claude_content = read_file("CLAUDE.md").strip()
    errors = []
    if not init_content:
        errors.append("skills/init/SKILL.md does not exist or is empty")
    elif not claude_content:
        errors.append("CLAUDE.md does not exist or is empty")
    else:
        # Extract template between markers
        begin_marker = "---BEGIN TEMPLATE---"
        end_marker = "---END TEMPLATE---"
        begin_idx = init_content.find(begin_marker)
        end_idx = init_content.find(end_marker)
        if begin_idx < 0:
            errors.append(f"skills/init/SKILL.md missing '{begin_marker}' marker")
        elif end_idx < 0:
            errors.append(f"skills/init/SKILL.md missing '{end_marker}' marker")
        else:
            template = init_content[begin_idx + len(begin_marker):end_idx].strip()
            if template != claude_content:
                # Find first difference for diagnostics
                t_lines = template.splitlines()
                c_lines = claude_content.splitlines()
                for i, (t, c) in enumerate(zip(t_lines, c_lines)):
                    if t != c:
                        errors.append(
                            f"First diff at line {i+1}: "
                            f"template={t[:80]!r}... vs CLAUDE.md={c[:80]!r}..."
                        )
                        break
                else:
                    if len(t_lines) != len(c_lines):
                        errors.append(
                            f"Line count mismatch: template={len(t_lines)}, CLAUDE.md={len(c_lines)}"
                        )
    record(
        "EVAL-TPL-001",
        "skills/init/SKILL.md template == CLAUDE.md content",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_tpl_002():
    """EVAL-TPL-002: No .claude/agents/ path in CLAUDE.md or template"""
    errors = []
    for path in ["CLAUDE.md", f"{PLUGIN_DIR}/skills/init/SKILL.md"]:
        hits = grep_file(path, r"\.claude/agents/")
        if hits:
            errors.append(f"{path}: {len(hits)} occurrence(s) at line(s) {[h[0] for h in hits]}")
    record(
        "EVAL-TPL-002",
        "No .claude/agents/ path in CLAUDE.md or init template",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_tpl_003():
    """EVAL-TPL-003: Template contains all required section headings"""
    golden = load_golden("template_sections.json")
    content = read_file(f"{PLUGIN_DIR}/skills/init/SKILL.md")
    missing = []
    for heading in golden["required_headings"]:
        if heading not in content:
            missing.append(heading)
    record(
        "EVAL-TPL-003",
        "Template contains all required section headings",
        len(missing) == 0,
        f"Missing headings: {missing}" if missing else "",
    )


def eval_orc_001():
    """EVAL-ORC-001: Delegation map names match agent filenames"""
    golden = load_golden("delegation_map.json")
    agent_files = list_files(f"{PLUGIN_DIR}/agents", ".md")
    agent_names_from_files = sorted(f.replace(".md", "") for f in agent_files)
    delegation_names = sorted(golden["delegation_order"])
    missing_in_files = set(delegation_names) - set(agent_names_from_files)
    missing_in_map = set(agent_names_from_files) - set(delegation_names)
    errors = []
    if missing_in_files:
        errors.append(f"In delegation map but no file: {sorted(missing_in_files)}")
    if missing_in_map:
        errors.append(f"File exists but not in delegation map: {sorted(missing_in_map)}")
    record(
        "EVAL-ORC-001",
        "Delegation map names match agent filenames",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_orc_002():
    """EVAL-ORC-002: Agent frontmatter name: field matches filename"""
    golden = load_golden("agent_inventory.json")
    errors = []
    for filename, expected_name in golden["agents"].items():
        content = read_file(f"{PLUGIN_DIR}/agents/{filename}")
        fm = extract_frontmatter(content)
        if fm is None:
            errors.append(f"{filename}: no frontmatter found")
            continue
        # Find name: field
        name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        if not name_match:
            errors.append(f"{filename}: no 'name:' field in frontmatter")
        else:
            actual_name = name_match.group(1).strip()
            if actual_name != expected_name:
                errors.append(f"{filename}: name={actual_name!r}, expected={expected_name!r}")
    record(
        "EVAL-ORC-002",
        "Agent frontmatter name: matches filename",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_orc_003():
    """EVAL-ORC-003: Agent allowlist bindings match design spec"""
    golden = load_golden("agent_allowlist_bindings.json")
    errors = []
    for agent_name, expected_allowlist in golden["bindings"].items():
        filename = f"{agent_name}.md"
        content = read_file(f"{PLUGIN_DIR}/agents/{filename}")
        fm = extract_frontmatter(content)
        if fm is None:
            errors.append(f"{filename}: no frontmatter")
            continue
        # Look for the allowlist reference
        pattern = r"allowlists/(\S+\.regex)"
        matches = re.findall(pattern, fm)
        # Remove trailing quote marks from matches
        matches = [m.rstrip('"\'') for m in matches]
        if expected_allowlist not in matches:
            errors.append(
                f"{agent_name}: expected allowlist {expected_allowlist!r}, found {matches}"
            )
    record(
        "EVAL-ORC-003",
        "Agent allowlist bindings match design spec",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_cln_001():
    """EVAL-CLN-001: Deleted infrastructure files do not exist"""
    must_not_exist = [
        ("manifest.json", "file"),
        (".system2", "dir"),
        (".claude/commands/update-system2.md", "file"),
        ("scripts", "dir"),
        ("tests", "dir"),
    ]
    still_exist = []
    for path, kind in must_not_exist:
        if kind == "file" and file_exists(path):
            still_exist.append(path)
        elif kind == "dir" and dir_exists(path):
            still_exist.append(path + "/")
    record(
        "EVAL-CLN-001",
        "Deleted infrastructure files/dirs do not exist",
        len(still_exist) == 0,
        f"Still exist: {still_exist}" if still_exist else "",
    )


def eval_cln_002():
    """EVAL-CLN-002: No .system2/ entries in .gitignore"""
    hits = grep_file(".gitignore", r"\.system2/")
    record(
        "EVAL-CLN-002",
        "No .system2/ entries in .gitignore",
        len(hits) == 0,
        f"Found {len(hits)} .system2/ entries" if hits else "",
    )


def eval_cln_003():
    """EVAL-CLN-003: spec*/ pattern in .gitignore"""
    hits = grep_file(".gitignore", r"spec\*/")
    record(
        "EVAL-CLN-003",
        "spec*/ pattern preserved in .gitignore",
        len(hits) > 0,
        "spec*/ pattern not found in .gitignore" if not hits else "",
    )


def eval_doc_001():
    """EVAL-DOC-001: README has required patterns, no prohibited patterns"""
    golden = load_golden("required_readme_patterns.json")
    errors = []
    readme = read_file("README.md")
    if not readme:
        errors.append("README.md does not exist or is empty")
    else:
        for rule in golden["must_contain"]:
            pattern = rule["pattern"]
            is_regex = rule.get("is_regex", False)
            if is_regex:
                if not re.search(pattern, readme):
                    errors.append(f"must_contain: {rule['id']} -- pattern {pattern!r} not found")
            else:
                if pattern not in readme:
                    errors.append(f"must_contain: {rule['id']} -- {pattern!r} not found")
        for rule in golden["must_not_contain"]:
            pattern = rule["pattern"]
            is_regex = rule.get("is_regex", False)
            if is_regex:
                if re.search(pattern, readme):
                    errors.append(f"must_not_contain: {rule['id']} -- pattern {pattern!r} found")
            else:
                if pattern in readme:
                    errors.append(f"must_not_contain: {rule['id']} -- {pattern!r} found")
    record(
        "EVAL-DOC-001",
        "README has required patterns, no prohibited patterns",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_doc_002():
    """EVAL-DOC-002: No REQ- IDs in implementation files"""
    golden = load_golden("prohibited_patterns.json")
    errors = []
    for rule in golden["rules"]:
        if not rule["id"].startswith("no-req-ids"):
            continue
        scope = rule["scope"]
        pattern = rule["pattern"]
        exclude_files = set(rule.get("exclude_files", []))
        if scope.endswith("/"):
            hits = grep_dir(scope.rstrip("/"), pattern)
            # Filter out excluded files
            if exclude_files:
                hits = [h for h in hits if h[0] not in exclude_files]
        else:
            if scope in exclude_files:
                continue
            hits = grep_file(scope, pattern)
        if hits:
            if isinstance(hits[0], tuple) and len(hits[0]) == 3:
                locations = [f"{h[0]}:{h[1]}" for h in hits[:3]]
            else:
                locations = [f"line {h[0]}" for h in hits[:3]]
            errors.append(f"{rule['id']} in {scope}: {len(hits)} hit(s) at {locations}")
    record(
        "EVAL-DOC-002",
        "No REQ- IDs in implementation files",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_sec_001():
    """EVAL-SEC-001: No non-stdlib imports in hook scripts"""
    stdlib_modules = {
        "sys", "os", "re", "json", "shutil", "subprocess", "argparse",
        "typing", "__future__", "_hook_utils", "pathlib", "importlib",
        "importlib.util", "textwrap", "collections", "functools",
        "io", "string", "hashlib", "time", "datetime", "copy",
        "traceback", "contextlib", "abc", "enum", "dataclasses",
        "shlex", "glob", "fnmatch", "signal", "struct", "tempfile",
        "unittest", "logging", "inspect", "ast", "token", "tokenize",
    }
    errors = []
    hook_dir = REPO_ROOT / PLUGIN_DIR / "hooks"
    if hook_dir.is_dir():
        for fpath in sorted(hook_dir.glob("*.py")):
            lines = fpath.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    # Parse the module name
                    if stripped.startswith("from "):
                        module = stripped.split()[1].split(".")[0]
                    else:
                        module = stripped.split()[1].split(".")[0].rstrip(",")
                    if module not in stdlib_modules:
                        errors.append(f"{fpath.name}:{i}: non-stdlib import: {stripped}")
    record(
        "EVAL-SEC-001",
        "No non-stdlib imports in hook scripts",
        len(errors) == 0,
        "; ".join(errors[:5]) if errors else "",
    )


def eval_sec_002():
    """EVAL-SEC-002: No network calls in hook scripts"""
    network_patterns = [
        r"\brequests\.",
        r"\burllib\.",
        r"\bhttp\.client",
        r"\bhttp\.server",
        r"\bsocket\.",
        r"\bhttpx\.",
        r"\baiohttp\.",
    ]
    combined = "|".join(network_patterns)
    hits = grep_dir(f"{PLUGIN_DIR}/hooks", combined, file_suffix=".py")
    record(
        "EVAL-SEC-002",
        "No network calls in hook scripts",
        len(hits) == 0,
        f"Found network call patterns: {hits[:3]}" if hits else "",
    )


def eval_sec_003():
    """EVAL-SEC-003: Safety instruction present in CLAUDE.md and template"""
    errors = []
    for path in ["CLAUDE.md", f"{PLUGIN_DIR}/skills/init/SKILL.md"]:
        content = read_file(path)
        if "untrusted input" not in content:
            errors.append(f"{path}: 'untrusted input' safety instruction not found")
    record(
        "EVAL-SEC-003",
        "Safety instruction present in CLAUDE.md and template",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_EVALS = [
    # Path migration
    eval_path_001,
    eval_path_002,
    eval_path_003,
    eval_path_004,
    eval_path_005,
    # File inventory
    eval_inv_001,
    eval_inv_002,
    eval_inv_003,
    eval_inv_004,
    eval_inv_005,
    # Manifests
    eval_man_001,
    eval_man_002,
    eval_man_003,
    # Template
    eval_tpl_001,
    eval_tpl_002,
    eval_tpl_003,
    # Orchestrator consistency
    eval_orc_001,
    eval_orc_002,
    eval_orc_003,
    # Cleanup
    eval_cln_001,
    eval_cln_002,
    eval_cln_003,
    # Documentation
    eval_doc_001,
    eval_doc_002,
    # Security
    eval_sec_001,
    eval_sec_002,
    eval_sec_003,
]


def main():
    start = time.time()

    print("=" * 70)
    print("System2 v0.2.0 Plugin Migration Eval Suite")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Goldens:   {GOLDENS_DIR}")
    print("=" * 70)
    print()

    for eval_fn in ALL_EVALS:
        try:
            eval_fn()
        except Exception as e:
            record(
                eval_fn.__doc__.split(":")[0] if eval_fn.__doc__ else eval_fn.__name__,
                f"EXCEPTION in {eval_fn.__name__}",
                False,
                str(e),
            )

    elapsed = time.time() - start

    # Group results by category
    categories = {
        "PATH": "Path Migration",
        "INV": "File Inventory",
        "MAN": "Manifests",
        "TPL": "Template Consistency",
        "ORC": "Orchestrator Consistency",
        "CLN": "Cleanup",
        "DOC": "Documentation",
        "SEC": "Security",
    }

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for prefix, label in categories.items():
        group = [r for r in results if f"-{prefix}-" in r.eval_id]
        if group:
            print(f"--- {label} ---")
            for r in group:
                print(r)
            print()

    # Ungrouped (if any)
    grouped_ids = set()
    for prefix in categories:
        for r in results:
            if f"-{prefix}-" in r.eval_id:
                grouped_ids.add(r.eval_id)
    ungrouped = [r for r in results if r.eval_id not in grouped_ids]
    if ungrouped:
        print("--- Other ---")
        for r in ungrouped:
            print(r)
        print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {len(results)} total")
    print(f"Elapsed: {elapsed:.2f}s")
    print("=" * 70)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
