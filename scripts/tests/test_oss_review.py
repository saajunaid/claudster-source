"""Unit tests for the provider-agnostic cross-review tool (.github/tools/oss_review.py).

No live model calls: `get_diff` and `call_llm` are monkeypatched so the tests exercise the
config resolution, prompt construction, verdict classification, and exit-code mapping in
isolation. This is the TDD backbone for `/claudster:cross-review`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / ".github" / "tools"))

import oss_review  # noqa: E402


def _args(**over) -> argparse.Namespace:
    base = {"range": None, "cwd": ".", "base_url": None, "model": None}
    base.update(over)
    return argparse.Namespace(**base)


# ── resolve_config ──────────────────────────────────────────────────────────

def test_resolve_config_defaults_to_deepseek():
    base, key, model = oss_review.resolve_config(_args(), {"REVIEW_API_KEY": "k"})
    assert base == "https://api.deepseek.com"
    assert model == "deepseek-chat"
    assert key == "k"


def test_resolve_config_missing_key_raises():
    with pytest.raises(oss_review.ConfigError):
        oss_review.resolve_config(_args(), {})


def test_resolve_config_flags_override_env():
    env = {"REVIEW_API_KEY": "k", "REVIEW_BASE_URL": "https://env", "REVIEW_MODEL": "env-model"}
    base, _key, model = oss_review.resolve_config(_args(base_url="https://flag", model="flag-model"), env)
    assert base == "https://flag"
    assert model == "flag-model"


def test_resolve_config_strips_trailing_slash():
    base, _k, _m = oss_review.resolve_config(_args(base_url="https://x/"), {"REVIEW_API_KEY": "k"})
    assert base == "https://x"


# ── build_review_prompt ─────────────────────────────────────────────────────

def test_prompt_carries_range_and_diff_and_verdict_instruction():
    p = oss_review.build_review_prompt("DIFF-BODY", "feat/x", "origin/main..HEAD")
    assert "origin/main..HEAD" in p
    assert "DIFF-BODY" in p
    assert "feat/x" in p
    assert "REVIEW: CLEAN" in p and "REVIEW: BLOCKING" in p


def test_prompt_describes_working_tree_when_no_range():
    p = oss_review.build_review_prompt("D", "main", None)
    assert "working tree" in p.lower()


# ── classify_verdict (fail-closed) ──────────────────────────────────────────

def test_classify_clean():
    assert oss_review.classify_verdict("looks good\nREVIEW: CLEAN") is True


def test_classify_blocking():
    assert oss_review.classify_verdict("bug here\nREVIEW: BLOCKING") is False


def test_classify_blocking_wins_over_clean():
    # Fail-closed: any blocking signal beats a clean one.
    assert oss_review.classify_verdict("REVIEW: CLEAN ... REVIEW: BLOCKING") is False


def test_classify_no_verdict_is_none():
    assert oss_review.classify_verdict("I have opinions but no marker") is None


# ── main: exit-code mapping (get_diff + call_llm stubbed) ───────────────────

def _patch(monkeypatch, *, diff="some diff", review="REVIEW: CLEAN"):
    monkeypatch.setattr(oss_review, "get_diff", lambda rng, cwd: diff)
    monkeypatch.setattr(oss_review, "current_branch", lambda cwd: "test-branch")
    monkeypatch.setattr(oss_review, "call_llm", lambda base, key, model, prompt, **k: review)


def test_main_clean_exits_0(monkeypatch, capsys):
    _patch(monkeypatch, review="all good\nREVIEW: CLEAN")
    assert oss_review.main([], {"REVIEW_API_KEY": "k"}) == oss_review.EXIT_CLEAN
    assert "REVIEW: CLEAN" in capsys.readouterr().out


def test_main_blocking_exits_1(monkeypatch):
    _patch(monkeypatch, review="oops\nREVIEW: BLOCKING")
    assert oss_review.main([], {"REVIEW_API_KEY": "k"}) == oss_review.EXIT_BLOCKING


def test_main_no_verdict_exits_2(monkeypatch):
    _patch(monkeypatch, review="rambled with no marker")
    assert oss_review.main([], {"REVIEW_API_KEY": "k"}) == oss_review.EXIT_ERROR


def test_main_missing_key_exits_3(monkeypatch):
    _patch(monkeypatch)
    assert oss_review.main([], {}) == oss_review.EXIT_CONFIG


def test_main_empty_diff_is_clean(monkeypatch):
    _patch(monkeypatch, diff="   \n")
    assert oss_review.main([], {"REVIEW_API_KEY": "k"}) == oss_review.EXIT_CLEAN


def test_main_git_failure_exits_2(monkeypatch):
    def boom(rng, cwd):
        raise RuntimeError("git diff failed")
    monkeypatch.setattr(oss_review, "get_diff", boom)
    assert oss_review.main([], {"REVIEW_API_KEY": "k"}) == oss_review.EXIT_ERROR


def test_main_endpoint_failure_exits_2(monkeypatch):
    monkeypatch.setattr(oss_review, "get_diff", lambda rng, cwd: "diff")
    monkeypatch.setattr(oss_review, "current_branch", lambda cwd: "b")

    def boom(*a, **k):
        raise RuntimeError("HTTP 500")
    monkeypatch.setattr(oss_review, "call_llm", boom)
    assert oss_review.main([], {"REVIEW_API_KEY": "k"}) == oss_review.EXIT_ERROR
