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


# ── setup_project_ai: legacy relocation (Phase 4) ───────────────────────────

def test_relocates_legacy_state(tmp_path):
    _make_project(tmp_path)
    (tmp_path / "relay.md").write_text("# legacy relay", encoding="utf-8")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "usage-log.jsonl").write_text('{"ts":"x"}\n', encoding="utf-8")
    (tmp_path / ".claude" / ".last-usage-review").write_text("2026-06-01T00:00:00+00:00", encoding="utf-8")
    (tmp_path / ".claude" / "PROJECT-FACTS.md").write_text("# old facts", encoding="utf-8")
    (tmp_path / ".claude" / "relay").mkdir()
    (tmp_path / ".claude" / "relay" / "feat-x.md").write_text("# branch relay", encoding="utf-8")

    _run_setup(tmp_path)

    assert (tmp_path / ".claudster" / "relay.md").is_file()
    assert (tmp_path / ".claudster" / "usage-log.jsonl").is_file()
    assert (tmp_path / ".claudster" / ".last-usage-review").is_file()
    assert (tmp_path / ".claudster" / "PROJECT-FACTS.md").is_file()
    assert (tmp_path / ".claudster" / "relay" / "feat-x.md").is_file()
    # legacy copies removed
    assert not (tmp_path / "relay.md").exists()
    assert not (tmp_path / ".claude" / "usage-log.jsonl").exists()
    assert not (tmp_path / ".claude" / ".last-usage-review").exists()
    assert not (tmp_path / ".claude" / "PROJECT-FACTS.md").exists()
    assert not (tmp_path / ".claude" / "relay").exists()


def test_relocation_idempotent(tmp_path):
    _make_project(tmp_path)
    (tmp_path / "relay.md").write_text("# legacy relay", encoding="utf-8")
    _run_setup(tmp_path)
    relay_new = tmp_path / ".claudster" / "relay.md"
    assert relay_new.is_file()
    content = relay_new.read_text(encoding="utf-8")
    r2 = _run_setup(tmp_path)  # second run: legacy source gone → no-op, no error
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert relay_new.read_text(encoding="utf-8") == content


def test_relocation_never_clobbers(tmp_path):
    _make_project(tmp_path)
    (tmp_path / ".claudster").mkdir()
    (tmp_path / ".claudster" / "relay.md").write_text("KEEP", encoding="utf-8")
    (tmp_path / "relay.md").write_text("OLD", encoding="utf-8")
    _run_setup(tmp_path)
    assert (tmp_path / ".claudster" / "relay.md").read_text(encoding="utf-8") == "KEEP"
    assert (tmp_path / "relay.md").read_text(encoding="utf-8") == "OLD"  # legacy left in place


def test_relocates_github_plans_for_normal_project(tmp_path):
    _make_project(tmp_path)
    (tmp_path / ".github" / "plans").mkdir(parents=True)
    (tmp_path / ".github" / "plans" / "a.md").write_text("# plan a", encoding="utf-8")
    (tmp_path / ".github" / "plans" / "b.md").write_text("# plan b", encoding="utf-8")
    _run_setup(tmp_path)
    assert (tmp_path / ".claudster" / "plans" / "a.md").is_file()
    assert (tmp_path / ".claudster" / "plans" / "b.md").is_file()
    assert not (tmp_path / ".github" / "plans" / "a.md").exists()
    assert not (tmp_path / ".github" / "plans" / "b.md").exists()


def test_keeps_github_plans_for_authoring_source(tmp_path):
    _make_project(tmp_path)
    (tmp_path / "claude-harness").mkdir()  # sentinel: this target IS the claudster authoring repo
    (tmp_path / ".github" / "plans").mkdir(parents=True)
    (tmp_path / ".github" / "plans" / "a.md").write_text("# pool plan", encoding="utf-8")
    _run_setup(tmp_path)
    assert (tmp_path / ".github" / "plans" / "a.md").is_file()  # left in place (pool-synced)
    assert not (tmp_path / ".claudster" / "plans" / "a.md").exists()
