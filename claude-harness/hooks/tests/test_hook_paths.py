"""Subprocess tests for claudster hook path resolution (.claudster + legacy fallback).

The hooks run top-level code and call sys.exit() on import, so they CANNOT be
imported — each test invokes the hook as a subprocess with a crafted stdin payload
and a tmp_path cwd, then asserts on stdout / written files.

Run: python -m pytest claude-harness/hooks/tests/test_hook_paths.py -q
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent
INJECT = HOOKS_DIR / "inject_relay.py"
SESSION_END = HOOKS_DIR / "session_end.py"


def _run(script: Path, cwd: Path, stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=str(cwd),
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",  # hooks reconfigure stdout to utf-8; decode to match (Windows default is cp1252)
        timeout=30,
    )


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)


# ── inject_relay: relay resolution ──────────────────────────────────────────

def test_inject_reads_new_relay(tmp_path):
    (tmp_path / ".claudster").mkdir()
    (tmp_path / ".claudster" / "relay.md").write_text("# Relay — NEW", encoding="utf-8")
    r = _run(INJECT, tmp_path, "{}")
    assert "# Relay — NEW" in r.stdout


def test_inject_falls_back_to_legacy_root_relay(tmp_path):
    (tmp_path / "relay.md").write_text("# Relay — LEGACY", encoding="utf-8")
    r = _run(INJECT, tmp_path, "{}")
    assert "# Relay — LEGACY" in r.stdout


def test_inject_prefers_new_over_legacy(tmp_path):
    (tmp_path / ".claudster").mkdir()
    (tmp_path / ".claudster" / "relay.md").write_text("RELAY-NEW-CONTENT", encoding="utf-8")
    (tmp_path / "relay.md").write_text("RELAY-OLD-CONTENT", encoding="utf-8")
    r = _run(INJECT, tmp_path, "{}")
    assert "RELAY-NEW-CONTENT" in r.stdout
    assert "RELAY-OLD-CONTENT" not in r.stdout


# ── inject_relay: usage-review nudge stamp (new + legacy fallback) ───────────

def test_inject_nudge_reads_new_stamp(tmp_path):
    (tmp_path / ".claudster").mkdir()
    (tmp_path / ".claudster" / ".last-usage-review").write_text(_iso_days_ago(10), encoding="utf-8")
    r = _run(INJECT, tmp_path, "{}")
    assert "[USAGE-REVIEW]" in r.stdout


def test_inject_nudge_reads_legacy_stamp(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / ".last-usage-review").write_text(_iso_days_ago(10), encoding="utf-8")
    r = _run(INJECT, tmp_path, "{}")
    assert "[USAGE-REVIEW]" in r.stdout


# ── inject_relay: DOC-MAP reference-index pointer (Phase 4) ─────────────────

def test_inject_emits_docmap_pointer_when_present(tmp_path):
    (tmp_path / ".claudster" / "kb").mkdir(parents=True)
    (tmp_path / ".claudster" / "kb" / "DOC-MAP.md").write_text("# Doc map", encoding="utf-8")
    r = _run(INJECT, tmp_path, "{}")
    assert "DOC-MAP" in r.stdout
    assert ".claudster/kb/DOC-MAP.md" in r.stdout


def test_inject_no_docmap_pointer_when_absent(tmp_path):
    r = _run(INJECT, tmp_path, "{}")
    assert "DOC-MAP" not in r.stdout


def test_inject_docmap_pointer_anchors_to_repo_root_in_subdir(tmp_path):
    """The pointer fires for a session launched from a subfolder (root-anchored)."""
    _git_init(tmp_path)
    (tmp_path / ".claudster" / "kb").mkdir(parents=True)
    (tmp_path / ".claudster" / "kb" / "DOC-MAP.md").write_text("# Doc map", encoding="utf-8")
    sub = tmp_path / "src"
    sub.mkdir()
    r = _run(INJECT, sub, "{}")
    assert "DOC-MAP" in r.stdout


# ── session_end: usage-log write → .claudster, never .claude ────────────────

def test_session_end_writes_new_usage_log(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"message": {"model": "claude-sonnet-4-6",
                                "usage": {"input_tokens": 10, "output_tokens": 5}}}) + "\n",
        encoding="utf-8",
    )
    payload = json.dumps({"transcript_path": str(transcript), "session_id": "t"})
    _run(SESSION_END, tmp_path, payload)
    new_log = tmp_path / ".claudster" / "usage-log.jsonl"
    old_log = tmp_path / ".claude" / "usage-log.jsonl"
    assert new_log.is_file()
    lines = [l for l in new_log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    assert not old_log.exists()


# ── repo-root anchoring: state lands at the git root, never the launch subdir ──

def test_session_end_anchors_log_to_repo_root(tmp_path):
    """A session launched from a subfolder must append to the repo-root log,
    not scatter a .claudster/ into the subfolder (the rev-sight bug)."""
    _git_init(tmp_path)
    sub = tmp_path / "frontend"
    sub.mkdir()
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps({"message": {"model": "claude-sonnet-4-6",
                                "usage": {"input_tokens": 10, "output_tokens": 5}}}) + "\n",
        encoding="utf-8",
    )
    payload = json.dumps({"transcript_path": str(transcript), "session_id": "t"})
    _run(SESSION_END, sub, payload)  # launched from the subdir
    assert (tmp_path / ".claudster" / "usage-log.jsonl").is_file(), "log must land at repo root"
    assert not (sub / ".claudster").exists(), "must NOT scatter .claudster into the subdir"


def test_inject_reads_relay_from_repo_root_in_subdir(tmp_path):
    """relay.md at the repo root is found even when the session runs from a subfolder."""
    _git_init(tmp_path)
    (tmp_path / ".claudster").mkdir()
    (tmp_path / ".claudster" / "relay.md").write_text("# Relay — ROOT-ANCHORED", encoding="utf-8")
    sub = tmp_path / "src"
    sub.mkdir()
    r = _run(INJECT, sub, "{}")  # launched from the subdir
    assert "# Relay — ROOT-ANCHORED" in r.stdout
