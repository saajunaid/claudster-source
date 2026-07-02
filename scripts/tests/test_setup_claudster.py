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
    for pat in ("reviews/*.html", "usage-log.jsonl", ".last-usage-review", "relay.md", "memory.jsonl"):
        assert pat in txt, pat


def test_scaffolds_config_toml_example(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    cfg = tmp_path / ".claudster" / "config.toml.example"
    assert cfg.is_file()
    txt = cfg.read_text(encoding="utf-8")
    assert "[guard]" in txt and "allow" in txt          # guard escape hatch
    assert "[doc_coverage]" in txt and "[dream_memory]" in txt  # all three live sections documented
    # The real config.toml is NOT written — only the example (user opts in by copying).
    assert not (tmp_path / ".claudster" / "config.toml").exists()


def test_scaffold_keeps_existing_config_example(tmp_path):
    _make_project(tmp_path)
    cfg = tmp_path / ".claudster" / "config.toml.example"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("# hand-edited — keep me\n", encoding="utf-8")
    _run_setup(tmp_path)
    assert cfg.read_text(encoding="utf-8") == "# hand-edited — keep me\n"  # never clobbered


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


# ── setup_project_ai: doc-coverage discipline (Phase 2) ─────────────────────

def test_setup_emits_doc_map(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    dm = tmp_path / ".claudster" / "kb" / "DOC-MAP.md"
    assert dm.is_file()
    # the scaffold must point at the discipline checker so the link survives setup
    assert "check_doc_coverage.py" in dm.read_text(encoding="utf-8")


def test_setup_copies_checker(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    checker = tmp_path / "scripts" / "check_doc_coverage.py"
    assert checker.is_file()
    assert "def run(" in checker.read_text(encoding="utf-8")
    # The shared config reader must ride along, or the checker's [doc_coverage] override is inert.
    assert (tmp_path / "scripts" / "claudster_config.py").is_file()


def test_setup_emits_page_guide_only_with_frontend(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    assert not (tmp_path / "UI_PAGE_GUIDE.md").exists()  # no frontend/ → no page guide
    (tmp_path / "frontend").mkdir()
    _run_setup(tmp_path)
    assert (tmp_path / "UI_PAGE_GUIDE.md").is_file()  # frontend/ present → stub emitted


def test_root_claude_md_points_to_doc_map(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    cm = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert ".claudster/kb/DOC-MAP.md" in cm


def test_doc_map_not_clobbered_on_resetup(tmp_path):
    _make_project(tmp_path)
    _run_setup(tmp_path)
    dm = tmp_path / ".claudster" / "kb" / "DOC-MAP.md"
    dm.write_text("# EDITED — keep me", encoding="utf-8")
    _run_setup(tmp_path)  # no --force → idempotent, must not clobber
    assert dm.read_text(encoding="utf-8") == "# EDITED — keep me"


def test_doc_map_prelinks_discovered_docs(tmp_path):
    """A fresh scaffold pre-links the repo's real docs (README, docs/…) instead of an empty placeholder."""
    _make_project(tmp_path)
    (tmp_path / "README.md").write_text("# T\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "arch.md").write_text("# Arch\n", encoding="utf-8")
    _run_setup(tmp_path)
    dm = (tmp_path / ".claudster" / "kb" / "DOC-MAP.md").read_text(encoding="utf-8")
    assert "(../../README.md)" in dm       # link written relative to .claudster/kb/
    assert "(../../docs/arch.md)" in dm
    # every pre-linked target exists on disk, so the checker stays gate-clean
    checker = tmp_path / "scripts" / "check_doc_coverage.py"
    r = _run([str(checker), "--check"], cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_ships_checker():
    """The make-or-break: the bundled `claude` plugin must carry the checker at plugin/scripts/."""
    manifest = json.loads(
        (SCRIPTS.parent / ".github" / "runtime-targets.json").read_text(encoding="utf-8")
    )
    claude = next(t for t in manifest["targets"] if t["name"] == "claude")
    dests = [f["destination"] for f in claude.get("files", [])]
    assert "scripts/check_doc_coverage.py" in dests


# ── setup_project_ai: pre-push gate wiring (Phase 3) ────────────────────────

def _load_setup_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("spa_for_test", SETUP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pre_push_gate_runs_doc_coverage():
    """The gate must invoke the checker in --check mode (blocks on hard invariants)."""
    hook = _load_setup_module().PRE_PUSH_HOOK
    assert "check_doc_coverage.py --check" in hook
    # guarded so it auto-skips when the checker isn't present (older repos) or python is missing
    assert 'scripts/check_doc_coverage.py' in hook
    assert "command -v python" in hook
