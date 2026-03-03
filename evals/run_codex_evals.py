#!/usr/bin/env python3
"""
System2 Codex Runtime Eval Harness

Structural assertions for the Codex runtime port.
Uses only Python 3.8+ standard library.

Usage:
    python3 evals/run_codex_evals.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
GOLDENS_DIR = SCRIPT_DIR / "goldens"


class EvalResult:
    def __init__(self, eval_id: str, description: str, passed: bool, message: str = ""):
        self.eval_id = eval_id
        self.description = description
        self.passed = passed
        self.message = message

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        msg = f"  [{status}] {self.eval_id}: {self.description}"
        if not self.passed and self.message:
            msg += f"\n         {self.message}"
        return msg


RESULTS: List[EvalResult] = []


def record(eval_id: str, description: str, passed: bool, message: str = "") -> None:
    RESULTS.append(EvalResult(eval_id, description, passed, message))


def load_json(rel_path: str) -> Dict:
    path = REPO_ROOT / rel_path
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def read_file(rel_path: str) -> str:
    path = REPO_ROOT / rel_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def eval_man_001() -> None:
    golden = load_json("evals/goldens/codex_manifest_schema.json")
    errors: List[str] = []
    manifest_path = golden["manifest_path"]
    manifest_full = REPO_ROOT / manifest_path
    if not manifest_full.is_file():
        errors.append(f"Missing manifest: {manifest_path}")
    else:
        try:
            manifest = load_json(manifest_path)
        except json.JSONDecodeError as exc:
            manifest = {}
            errors.append(f"Invalid JSON in {manifest_path}: {exc}")

        for key, expected in golden["required_fields"].items():
            actual = manifest.get(key)
            if actual != expected:
                errors.append(f"{key}: expected {expected!r}, got {actual!r}")

        entrypoints = manifest.get("entrypoints", {})
        if not isinstance(entrypoints, dict):
            errors.append("entrypoints must be an object")
            entrypoints = {}

        for key in golden["required_entrypoints"]:
            if key not in entrypoints:
                errors.append(f"entrypoints missing key: {key}")
                continue
            path = entrypoints[key]
            full = (REPO_ROOT / "codex" / Path(path).as_posix().replace("./", "", 1))
            if not full.exists():
                errors.append(f"entrypoint path missing for {key}: {path}")

    record(
        "EVAL-CODEX-MAN-001",
        "codex/manifest.json has required fields and entrypoint files",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_runtime_001() -> None:
    registry = load_json("codex/runtime/agent-registry.json")
    delegation = load_json("evals/goldens/delegation_map.json")
    expected = set(delegation["delegation_order"])
    actual = {agent["name"] for agent in registry.get("agents", [])}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    record(
        "EVAL-CODEX-RT-001",
        "Codex agent registry includes exactly the System2 delegation roles",
        not missing and not extra and len(actual) == 13,
        f"missing={missing}, extra={extra}, count={len(actual)}" if missing or extra or len(actual) != 13 else "",
    )


def eval_runtime_002() -> None:
    registry = load_json("codex/runtime/agent-registry.json")
    bindings = load_json("evals/goldens/agent_allowlist_bindings.json")
    expected_bindings = bindings["bindings"]
    errors: List[str] = []

    for agent in registry.get("agents", []):
        name = agent.get("name")
        source = agent.get("source_prompt")
        if not source or not (REPO_ROOT / source).is_file():
            errors.append(f"{name}: missing source prompt file {source!r}")

        allowlist = agent.get("write_allowlist")
        if name in expected_bindings:
            expected_allowlist = f"plugin/allowlists/{expected_bindings[name]}"
            if allowlist != expected_allowlist:
                errors.append(
                    f"{name}: expected write_allowlist {expected_allowlist!r}, got {allowlist!r}"
                )
            elif not (REPO_ROOT / allowlist).is_file():
                errors.append(f"{name}: allowlist file does not exist: {allowlist}")
        else:
            if allowlist:
                errors.append(f"{name}: should not define write_allowlist, got {allowlist!r}")

    record(
        "EVAL-CODEX-RT-002",
        "Registry source prompts and allowlist bindings are valid",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_tpl_001() -> None:
    golden = load_json("evals/goldens/codex_template_sections.json")
    content = read_file("codex/templates/AGENTS.md")
    missing = [heading for heading in golden["required_headings"] if heading not in content]
    record(
        "EVAL-CODEX-TPL-001",
        "codex/templates/AGENTS.md includes required sections",
        len(missing) == 0,
        f"Missing headings: {missing}" if missing else "",
    )


def eval_tpl_002() -> None:
    skill = read_file("codex/skills/init/SKILL.md")
    template = read_file("codex/templates/AGENTS.md").strip()
    errors: List[str] = []
    begin = "---BEGIN TEMPLATE---"
    end = "---END TEMPLATE---"

    b = skill.find(begin)
    e = skill.find(end)
    if b < 0 or e < 0 or e < b:
        errors.append("Skill template markers missing or malformed")
    else:
        embedded = skill[b + len(begin):e].strip()
        if embedded != template:
            errors.append("Embedded template in codex skill does not match codex/templates/AGENTS.md")

    record(
        "EVAL-CODEX-TPL-002",
        "codex init skill template matches codex/templates/AGENTS.md",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_inst_001() -> None:
    errors: List[str] = []
    install_script = REPO_ROOT / "codex" / "install.sh"
    if not install_script.is_file():
        errors.append("codex/install.sh does not exist")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "bash",
                str(install_script),
                "--dry-run",
                "--codex-home",
                tmpdir,
            ]
            proc = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                errors.append(f"dry-run exit code {proc.returncode}")
            if "[dry-run]" not in proc.stdout:
                errors.append("dry-run output missing '[dry-run]' markers")
            if "codex features enable multi_agent" not in proc.stdout:
                errors.append("installer dry-run missing multi_agent enable command")
            expected_target = Path(tmpdir) / "skills" / "system2"
            if expected_target.exists():
                errors.append("dry-run created target directory but should not")

    record(
        "EVAL-CODEX-INS-001",
        "codex/install.sh supports non-mutating --dry-run install",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_tool_001() -> None:
    errors: List[str] = []
    validator = REPO_ROOT / "codex" / "tools" / "validate_paths.py"
    allowlist = REPO_ROOT / "plugin" / "allowlists" / "spec-context.regex"
    if not validator.is_file():
        errors.append("codex/tools/validate_paths.py missing")
    else:
        allow_cmd = [
            "python3",
            str(validator),
            str(allowlist),
            "spec/context.md",
        ]
        deny_cmd = [
            "python3",
            str(validator),
            str(allowlist),
            "README.md",
        ]
        allow_proc = subprocess.run(allow_cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        deny_proc = subprocess.run(deny_cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if allow_proc.returncode != 0:
            errors.append(f"allow case failed with exit {allow_proc.returncode}")
        if deny_proc.returncode != 2:
            errors.append(f"deny case expected exit 2, got {deny_proc.returncode}")

    record(
        "EVAL-CODEX-TOL-001",
        "codex/tools/validate_paths.py allows allowed paths and blocks disallowed paths",
        len(errors) == 0,
        "; ".join(errors) if errors else "",
    )


def eval_doc_001() -> None:
    golden = load_json("evals/goldens/codex_required_readme_patterns.json")
    readme = read_file("README.md")
    missing: List[str] = []
    for rule in golden["must_contain"]:
        pattern = rule["pattern"]
        if pattern not in readme:
            missing.append(f"{rule['id']}: {pattern!r}")
    record(
        "EVAL-CODEX-DOC-001",
        "README includes Codex runtime installation guidance",
        len(missing) == 0,
        "; ".join(missing) if missing else "",
    )


ALL_EVALS = [
    eval_man_001,
    eval_runtime_001,
    eval_runtime_002,
    eval_tpl_001,
    eval_tpl_002,
    eval_inst_001,
    eval_tool_001,
    eval_doc_001,
]


def main() -> int:
    start = time.time()
    print("=" * 70)
    print("System2 Codex Runtime Eval Suite")
    print(f"Repo root: {REPO_ROOT}")
    print("=" * 70)

    for eval_fn in ALL_EVALS:
        try:
            eval_fn()
        except Exception as exc:
            record(
                eval_fn.__name__,
                f"EXCEPTION in {eval_fn.__name__}",
                False,
                str(exc),
            )

    passed = sum(1 for r in RESULTS if r.passed)
    failed = sum(1 for r in RESULTS if not r.passed)

    print()
    for result in RESULTS:
        print(result)

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {len(RESULTS)} total")
    print(f"Elapsed: {time.time() - start:.2f}s")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
