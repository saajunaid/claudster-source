"""Tests for validate_pool.py's privacy denylist — the public-export gate.

validate_pool.py lives at the repo root and is import-safe (its body is behind
`if __name__ == "__main__"`).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("validate_pool", _ROOT / "validate_pool.py")
vp = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = vp
_SPEC.loader.exec_module(vp)  # type: ignore[union-attr]


# ── Track B2 (2026-07-20): internal product codenames must fail-closed ────────

def test_internal_app_codenames_are_flagged():
    for codename in ("appointment-assist", "nps-lens", "rev-sight", "app-sight"):
        hits = vp._scan_text_for_privacy(f"Use `warm-editorial-ui` for {codename} apps.")
        assert hits, f"{codename!r} should be flagged by the privacy scan"


def test_codename_match_is_case_insensitive():
    hits = vp._scan_text_for_privacy("Pair with NPS-LENS for the dashboard.")
    assert hits


def test_internal_tool_names_are_flagged():
    for marker in ("platform-infra", "new-vmie-project"):
        hits = vp._scan_text_for_privacy(f"Run {marker}.ps1 to scaffold the project.")
        assert hits, f"{marker!r} should be flagged by the privacy scan"


def test_bare_vmie_mention_is_not_flagged():
    # "vmie" is also a legitimate, intentional category label for the private-skill
    # opt-in mechanism (setup-project-ai.md's "deploy vmie skills (optional, personal)"
    # step) -- it must stay permitted so that transparent, generic documentation isn't
    # blocked. Only the vmie-prefixed / vmie-hostname shapes and the specific codenames
    # above are denylisted.
    hits = vp._scan_text_for_privacy(
        "`vmie` skills (deploy-local, golden-workflow, windows-deployment) are private "
        "and are not shipped in the public plugin."
    )
    assert hits == []


def test_ordinary_design_routing_prose_is_clean():
    hits = vp._scan_text_for_privacy(
        "Your organization's internal app family (an existing internal tool/dashboard "
        "suite that shares a house design system): load `warm-editorial-ui`."
    )
    assert hits == []


# ── Existing entries stay covered (regression guard on the whole list) ────────

def test_known_internal_hostnames_still_flagged():
    for marker in ("iegbcoppoc02", "ievxcoppoc01", "gitea.internal", "VMIE_BOT_TOKEN"):
        hits = vp._scan_text_for_privacy(f"deploy to {marker}")
        assert hits, f"{marker!r} should still be flagged"
