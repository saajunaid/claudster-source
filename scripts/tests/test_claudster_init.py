"""Tests for scripts/claudster_init.py — the one-command toolbox installer for non-Claude harnesses.

Contract under test (toolbox-portability plan, Phase 4):
  • install a target bundle from a local source (--from) into a project dir;
  • source layouts supported: <src>/bundles/<target> (published junai repo shape) and
    <src>/dist/runtime-resources/<target> (claudster-source checkout shape);
  • idempotent — re-running with no changes reports up-to-date and touches nothing;
  • upstream changes propagate on re-run;
  • files the USER modified after install are never overwritten without --force
    (detected via the sha256 manifest written at install time);
  • a pre-existing file the installer never wrote (e.g. the user's own AGENTS.md) is a
    conflict, not a silent overwrite;
  • unknown target fails with an actionable message listing available bundles;
  • tarball sources (the GitHub codeload shape) extract to the same result.

No network in tests: the GitHub path is exercised via a local .tar.gz fixture.
"""

import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claudster_init as ci  # noqa: E402


# ── fixtures ─────────────────────────────────────────────────────────────────

def _make_bundle(root: Path, target: str = "codex") -> Path:
    """Create a minimal published-repo-shaped source: <root>/bundles/<target>/…"""
    b = root / "bundles" / target
    (b / ".codex" / "skills" / "git-commit").mkdir(parents=True)
    (b / "AGENTS.md").write_text("# AGENTS\nThe Laws.\n", encoding="utf-8")
    (b / ".codex" / "skills" / "git-commit" / "SKILL.md").write_text(
        "---\nname: git-commit\ndescription: d\n---\nbody\n", encoding="utf-8"
    )
    return root


@pytest.fixture()
def src(tmp_path: Path) -> Path:
    return _make_bundle(tmp_path / "src")


@pytest.fixture()
def dest(tmp_path: Path) -> Path:
    d = tmp_path / "proj"
    d.mkdir()
    return d


def _run(*argv: str) -> int:
    return ci.main(list(argv))


# ── target resolution ────────────────────────────────────────────────────────

def test_unknown_target_fails_and_lists_available(src, dest, capsys):
    rc = _run("--target", "nope", "--from", str(src), "--dest", str(dest))
    assert rc == 2
    out = capsys.readouterr()
    assert "codex" in out.err or "codex" in out.out  # lists what IS available


def test_source_checkout_shape_dist_runtime_resources(tmp_path, dest):
    src = tmp_path / "checkout"
    b = src / "dist" / "runtime-resources" / "codex"
    b.mkdir(parents=True)
    (b / "AGENTS.md").write_text("x", encoding="utf-8")
    assert _run("--target", "codex", "--from", str(src), "--dest", str(dest)) == 0
    assert (dest / "AGENTS.md").read_text(encoding="utf-8") == "x"


# ── install + idempotence ────────────────────────────────────────────────────

def test_fresh_install_copies_all_files_and_writes_manifest(src, dest):
    assert _run("--target", "codex", "--from", str(src), "--dest", str(dest)) == 0
    assert (dest / "AGENTS.md").exists()
    assert (dest / ".codex" / "skills" / "git-commit" / "SKILL.md").exists()
    manifest = json.loads((dest / ci.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["target"] == "codex"
    assert "AGENTS.md" in manifest["files"]


def test_rerun_with_no_changes_is_noop(src, dest, capsys):
    _run("--target", "codex", "--from", str(src), "--dest", str(dest))
    before = (dest / "AGENTS.md").stat().st_mtime_ns
    assert _run("--target", "codex", "--from", str(src), "--dest", str(dest)) == 0
    assert (dest / "AGENTS.md").stat().st_mtime_ns == before
    assert "up to date" in capsys.readouterr().out.lower()


def test_upstream_change_propagates_on_rerun(src, dest):
    _run("--target", "codex", "--from", str(src), "--dest", str(dest))
    (src / "bundles" / "codex" / "AGENTS.md").write_text("# v2\n", encoding="utf-8")
    assert _run("--target", "codex", "--from", str(src), "--dest", str(dest)) == 0
    assert (dest / "AGENTS.md").read_text(encoding="utf-8") == "# v2\n"


# ── local-modification protection ────────────────────────────────────────────

def test_user_modified_file_is_not_overwritten(src, dest, capsys):
    _run("--target", "codex", "--from", str(src), "--dest", str(dest))
    (dest / "AGENTS.md").write_text("MY LOCAL EDITS\n", encoding="utf-8")
    (src / "bundles" / "codex" / "AGENTS.md").write_text("# v2\n", encoding="utf-8")
    rc = _run("--target", "codex", "--from", str(src), "--dest", str(dest))
    assert rc == 1  # conflict reported
    assert (dest / "AGENTS.md").read_text(encoding="utf-8") == "MY LOCAL EDITS\n"
    assert "AGENTS.md" in capsys.readouterr().out


def test_force_overwrites_user_modifications(src, dest):
    _run("--target", "codex", "--from", str(src), "--dest", str(dest))
    (dest / "AGENTS.md").write_text("MY LOCAL EDITS\n", encoding="utf-8")
    (src / "bundles" / "codex" / "AGENTS.md").write_text("# v2\n", encoding="utf-8")
    assert _run("--target", "codex", "--from", str(src), "--dest", str(dest), "--force") == 0
    assert (dest / "AGENTS.md").read_text(encoding="utf-8") == "# v2\n"


def test_preexisting_unmanaged_file_is_a_conflict_not_silently_replaced(src, dest):
    (dest / "AGENTS.md").write_text("the user's own file\n", encoding="utf-8")
    rc = _run("--target", "codex", "--from", str(src), "--dest", str(dest))
    assert rc == 1
    assert (dest / "AGENTS.md").read_text(encoding="utf-8") == "the user's own file\n"
    # the rest of the bundle still installed
    assert (dest / ".codex" / "skills" / "git-commit" / "SKILL.md").exists()


def test_preexisting_identical_file_is_adopted(src, dest):
    (dest / "AGENTS.md").write_text("# AGENTS\nThe Laws.\n", encoding="utf-8")
    assert _run("--target", "codex", "--from", str(src), "--dest", str(dest)) == 0


# ── tarball source (GitHub codeload shape) ───────────────────────────────────

def test_tarball_source_installs_like_a_directory(tmp_path, src, dest):
    # codeload tarballs wrap everything in a single "<repo>-<ref>/" top dir
    tgz = tmp_path / "repo.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        for p in sorted((src / "bundles").rglob("*")):
            if p.is_file():
                tf.add(p, arcname="junai-main/bundles/" + p.relative_to(src / "bundles").as_posix())
    assert _run("--target", "codex", "--from", str(tgz), "--dest", str(dest)) == 0
    assert (dest / "AGENTS.md").exists()
    assert (dest / ".codex" / "skills" / "git-commit" / "SKILL.md").exists()
