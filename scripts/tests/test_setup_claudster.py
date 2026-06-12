"""Phase 3 tests: setup_project_ai .claudster scaffold + --vendor gating, and
usage_review .claudster output. Subprocess-based against a tmp project.

Run: python -m pytest scripts/tests/test_setup_claudster.py -q
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
SETUP = SCRIPTS / "setup_project_ai.py"
USAGE = SCRIPTS / "usage_review.py"


def _run(args, cwd=None):
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )


def _make_project(tmp_path):
    # minimal package.json so stack detection + project-facts have something to extract
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "t", "scripts": {"dev": "vite", "test": "vitest run"}}),
        encoding="utf-8",
    )
    return tmp_path


def _run_setup(tmp_path, *extra):
    return _run([str(SETUP), str(tmp_path), "--name", "Test", "--desc", "x", *extra])


def _write_log(path, n=3):
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    lines = []
    for i in range(n):
        ts = (now - timedelta(hours=i + 1)).isoformat(timespec="seconds")
        lines.append(json.dumps({
            "ts": ts, "session": f"s{i}", "input": 1000, "output": 200,
            "cache_write": 0, "cache_read": 500, "est_cost_usd": 0.01,
            "models": ["claude-sonnet-4-6"],
        }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── setup_project_ai: .claudster scaffold ───────────────────────────────────

def test_scaffolds_claudster_tree(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    for sub in ("plans", "handoffs", "agent-docs", "reviews", "prd"):
        assert (tmp_path / ".claudster" / sub).is_dir(), sub
    gi = tmp_path / ".claudster" / ".gitignore"
    assert gi.is_file()
    txt = gi.read_text(encoding="utf-8")
    for pat in ("reviews/*.html", "usage-log.jsonl", ".last-usage-review", "relay.md"):
        assert pat in txt, pat


def test_project_facts_in_claudster(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    assert (tmp_path / ".claudster" / "PROJECT-FACTS.md").is_file()
    assert not (tmp_path / ".claude" / "PROJECT-FACTS.md").exists()


# ── setup_project_ai: --vendor gating ───────────────────────────────────────

def test_no_vendor_by_default(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    assert not (tmp_path / ".claude" / "agents").exists()
    assert not (tmp_path / ".claude" / "commands").exists()


def test_vendor_flag_deploys(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path, "--vendor")
    assert (tmp_path / ".claude" / "agents" / "tester.md").is_file()
    assert (tmp_path / ".claude" / "commands" / "handoff.md").is_file()


def test_settings_and_statusline_still_native(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    assert (tmp_path / ".claude" / "settings.json").is_file()
    assert (tmp_path / ".claude" / "statusline-command.sh").is_file()


# ── usage_review: .claudster output + legacy fallback ───────────────────────

def test_usage_review_stamp_in_claudster(tmp_path):
    _write_log(tmp_path / ".claudster" / "usage-log.jsonl")
    r = _run([str(USAGE), "--cwd", str(tmp_path), "--no-html"])
    assert (tmp_path / ".claudster" / ".last-usage-review").is_file(), r.stdout + r.stderr
    assert not (tmp_path / ".claude" / ".last-usage-review").exists()


def test_usage_review_reads_legacy_log(tmp_path):
    _write_log(tmp_path / ".claude" / "usage-log.jsonl")
    r = _run([str(USAGE), "--cwd", str(tmp_path), "--no-html"])
    assert "No sessions found" not in r.stdout, r.stdout + r.stderr


def test_usage_review_html_in_reviews(tmp_path):
    _write_log(tmp_path / ".claudster" / "usage-log.jsonl")
    _run([str(USAGE), "--cwd", str(tmp_path)])
    assert (tmp_path / ".claudster" / "reviews" / "usage-review.html").is_file()
