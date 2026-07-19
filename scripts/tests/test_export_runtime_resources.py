"""Fail-closed tests for export_runtime_resources.py.

The runtime exporter previously folded two real defects into skip counters and
still exited 0:
  * a target roster naming a skill that doesn't exist (the `codex` target named
    5 phantom frontend skills) — the bundle silently shipped fewer skills;
  * a declared copy/file `source` that doesn't exist on disk.
And Copilot→Claude agent conversion defaulted a no-mapped-tools agent to include
``Bash`` — implicitly granting shell to what should be a read-only agent.

These tests pin the fail-closed behaviour. The module lives at the repo root, so
it is loaded by path.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]  # scripts/tests -> scripts -> repo root
_SPEC = importlib.util.spec_from_file_location(
    "export_runtime_resources", _ROOT / "export_runtime_resources.py"
)
export = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = export  # dataclass introspection needs the module registered
_SPEC.loader.exec_module(export)  # type: ignore[union-attr]


# ── Copilot→Claude tool conversion: never implicitly grant Bash ───────────────

def test_default_tools_are_read_only_no_bash():
    # No copilot tools mapped → default must be read-only, never shell.
    result = export.convert_tools_to_claude_format([])
    assert "Bash" not in result
    assert result == "Read, Grep, Glob"


def test_unmapped_tools_default_read_only():
    # 'problems'/'changes' map to [] in TOOL_MAP → still read-only.
    result = export.convert_tools_to_claude_format(["problems", "changes"])
    assert "Bash" not in result


def test_explicit_execute_still_grants_bash():
    # An agent that explicitly declares 'execute' keeps Bash — only the implicit
    # default is tightened.
    result = export.convert_tools_to_claude_format(["read", "execute"])
    assert "Bash" in result


# ── Skill-roster validation: phantom skills must be flagged ───────────────────

def _make_skill_tree(root: Path, layout: dict[str, list[str]]) -> Path:
    skills = root / "skills"
    for category, names in layout.items():
        for name in names:
            d = skills / category / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    return skills


def test_validate_skill_roster_flags_phantom_skill(tmp_path):
    skills = _make_skill_tree(tmp_path, {"frontend": ["mockup"]})
    roster = {"frontend": {"mockup", "warm-new"}}
    problems = export._validate_skill_roster(skills, roster)
    assert any("warm-new" in p for p in problems)
    assert not any("mockup" in p for p in problems)


def test_validate_skill_roster_flags_phantom_category(tmp_path):
    skills = _make_skill_tree(tmp_path, {"frontend": ["mockup"]})
    roster = {"nope": {"anything"}}
    problems = export._validate_skill_roster(skills, roster)
    assert any("nope" in p for p in problems)


def test_validate_skill_roster_clean(tmp_path):
    skills = _make_skill_tree(tmp_path, {"frontend": ["mockup", "css-architecture"]})
    roster = {"frontend": {"mockup", "css-architecture"}}
    assert export._validate_skill_roster(skills, roster) == []


# ── ExportStats carries hard errors ───────────────────────────────────────────

def test_export_stats_has_errors_field():
    stats = export.ExportStats(profile="t")
    assert stats.errors == []


# ── Integration: a phantom roster / missing source fails main() (exit 1) ───────

def _write_manifest(tmp_path: Path, roster: dict, *, extra_files: list | None = None) -> Path:
    canonical = tmp_path / "canonical"
    _make_skill_tree(canonical, {"frontend": ["mockup"]})
    manifest = {
        "canonical_root": str(canonical),
        "output_root": str(tmp_path / "out"),
        "exclusions": {},
        "targets": [
            {
                "name": "demo",
                "workspace_root": ".",
                "copies": [{"source": "skills", "destination": "skills", "included_skills": roster}],
                "files": extra_files or [],
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _run_main(monkeypatch, manifest_path: Path) -> int:
    monkeypatch.setattr(
        sys, "argv", ["export_runtime_resources.py", "--manifest", str(manifest_path), "--report"]
    )
    return export.main()


def test_main_fails_on_phantom_skill(monkeypatch, tmp_path):
    manifest = _write_manifest(tmp_path, {"frontend": ["mockup", "ghost-skill"]})
    assert _run_main(monkeypatch, manifest) == 1


def test_main_passes_on_clean_roster(monkeypatch, tmp_path):
    manifest = _write_manifest(tmp_path, {"frontend": ["mockup"]})
    assert _run_main(monkeypatch, manifest) == 0


def test_main_fails_on_missing_source(monkeypatch, tmp_path):
    manifest = _write_manifest(
        tmp_path,
        {"frontend": ["mockup"]},
        extra_files=[{"source": "does-not-exist.md", "destination": "x.md"}],
    )
    assert _run_main(monkeypatch, manifest) == 1


# ── Regression: the real manifest's rosters have no phantom skills ────────────

def test_real_manifest_rosters_are_clean():
    """After the codex roster is corrected, no shipped target names a phantom skill."""
    manifest = json.loads((_ROOT / ".github" / "runtime-targets.json").read_text(encoding="utf-8"))
    skills_root = _ROOT / ".github" / "skills"
    for target in manifest["targets"]:
        for copy_spec in target.get("copies", []):
            roster = copy_spec.get("included_skills")
            if not roster:
                continue
            roster_sets = {cat: set(names) for cat, names in roster.items()}
            problems = export._validate_skill_roster(skills_root, roster_sets)
            assert problems == [], f"{target['name']}: {problems}"
