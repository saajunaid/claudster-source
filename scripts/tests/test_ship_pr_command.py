"""Content-lint the /ship-pr command (the reviewed lane, half 1).

/ship-pr is the mechanics-only half of the reviewed lane: push a feature branch, open a PR,
monitor its CI, STOP at green. It must never merge and never deploy — that is /ship-merge's
deliberately separate door (merge == deploy on the Gitea/NSSM repos). This is a content lint —
it does NOT prove model behavior; it prevents the safety-critical wording (no-merge, backup
ref before force-push, scope-guard pre-check) from being quietly removed from the command text.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CMD = _REPO / "claude-harness" / "commands" / "ship-pr.md"


def _text() -> str:
    return _CMD.read_text(encoding="utf-8")


def test_ship_pr_command_exists() -> None:
    assert _CMD.is_file(), "claude-harness/commands/ship-pr.md must exist"


def test_frontmatter_contract() -> None:
    text = _text()
    assert text.startswith("---"), "ship-pr.md must start with YAML frontmatter"
    head = text.split("---", 2)[1]
    assert "description:" in head, "frontmatter must carry a description"
    assert "argument-hint:" in head, "frontmatter must carry an argument-hint"


def test_enumerates_all_three_lanes() -> None:
    lower = _text().lower()
    assert "gitea" in lower, "must describe the Gitea lane"
    assert "github" in lower, "must describe the GitHub lane"
    assert "local-only" in lower, "must describe the local-only lane"


def test_local_only_lane_refuses_and_points_at_ship() -> None:
    lower = _text().lower()
    # There is no PR concept without a forge — refuse early, don't fabricate a flow.
    assert "refuse" in lower, "local-only lane must REFUSE, not improvise"
    assert "/ship" in _text(), "the refusal must point the user at /ship"


def test_refuses_on_default_branch() -> None:
    lower = _text().lower()
    assert "default branch" in lower, "must handle the on-default-branch case"
    assert "stop" in lower, "on the default branch it must stop (a PR is branch->main)"


def test_preflight_before_pr() -> None:
    lower = _text().lower()
    assert "preflight" in lower, "must run local gates before opening a PR"
    assert "ruff check" in lower, "preflight must mirror CI's lint gate"
    assert "never open a pr over red preflight" in lower or "red preflight" in lower, \
        "must forbid opening a PR over red preflight"


def test_scope_guard_precheck() -> None:
    lower = _text().lower()
    assert "scope-guard" in lower or "scope guard" in lower, \
        "must pre-check a scope-guard workflow's rule BEFORE creating the PR"
    assert "before" in lower and "offending" in lower, \
        "the pre-check must refuse early with the specific offending files"


def test_force_push_safety() -> None:
    text = _text()
    assert "--force-with-lease" in text, "any force-push must be --force-with-lease"
    assert "backup/" in text, "must snapshot a backup/<branch>-preship ref before a rewrite"
    assert "preship" in text, "the backup ref is named backup/<branch>-preship"


def test_rebase_only_when_behind() -> None:
    lower = _text().lower()
    assert "rebase" in lower, "must offer rebase-safe currency"
    assert "behind" in lower, "rebase only when the branch is behind the default branch"


def test_pr_creation_is_idempotent() -> None:
    lower = _text().lower()
    assert "already exists" in lower, \
        "if a PR for the branch already exists, update/report it — never error"


def test_monitors_ci_and_stops_at_green() -> None:
    lower = _text().lower()
    assert "monitor" in lower, "must monitor the PR's CI"
    assert "stop at green" in lower or "stops at green" in lower, \
        "must STOP at green and report mergeability"
    assert "mergeable" in lower, "the report must state mergeable-or-blocked"


def test_never_merges_never_deploys() -> None:
    text = _text()
    lower = text.lower()
    # The whole point of the split: /ship-pr produces a reviewable artifact and stops.
    assert "never merge" in lower, "must state it NEVER merges"
    assert "never deploy" in lower or "never deploys" in lower, "must state it never deploys"
    assert "gh pr merge" not in lower, "must not contain a merge action"
    assert "/ship-merge" in text, "must hand off to /ship-merge for the merge"


def test_references_lane_skills() -> None:
    lower = _text().lower()
    assert "deploy-local" in lower, "Gitea CI monitoring reuses the deploy-local skill"
    assert "gh-cli" in lower or "gh run" in lower, "GitHub monitoring reuses the gh-cli skill"


def test_safety_invariants_present() -> None:
    lower = _text().lower()
    assert "git add -a" in lower, "must forbid blind git add -A"
    assert "workflow file" in lower, "must forbid editing workflow files to pass a gate"
