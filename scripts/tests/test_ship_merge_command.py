"""Content-lint the /ship-merge command (the reviewed lane, half 2).

/ship-merge is the deliberate second door: merge an already-green, already-reviewed PR,
watch the deploy the merge triggers, validate prod, and clean up the branch ONLY after the
deploy is confirmed green. On these repos merge == deploy, so the human-confirm gate and the
green-precondition wording are safety-critical. This is a content lint — it does NOT prove
model behavior; it prevents those guarantees from being quietly removed from the command text.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CMD = _REPO / "claude-harness" / "commands" / "ship-merge.md"


def _text() -> str:
    return _CMD.read_text(encoding="utf-8")


def test_ship_merge_command_exists() -> None:
    assert _CMD.is_file(), "claude-harness/commands/ship-merge.md must exist"


def test_frontmatter_contract() -> None:
    text = _text()
    assert text.startswith("---"), "ship-merge.md must start with YAML frontmatter"
    head = text.split("---", 2)[1]
    assert "description:" in head, "frontmatter must carry a description"
    assert "argument-hint:" in head, "frontmatter must carry an argument-hint"


def test_enumerates_lanes_and_refuses_local_only() -> None:
    lower = _text().lower()
    assert "gitea" in lower and "github" in lower, "must describe both forge lanes"
    assert "local-only" in lower, "must name the local-only lane"
    assert "refuse" in lower, "local-only lane (no PR concept) must REFUSE, not improvise"


def test_green_and_mergeable_precondition() -> None:
    lower = _text().lower()
    # Refuse unless the PR is green + mergeable + reviewed per the repo's rules.
    assert "green" in lower and "mergeable" in lower, \
        "must require green checks AND mergeability before merging"
    assert "required" in lower and "review" in lower, \
        "must honor the repo's required-reviewer rules"
    assert "conflict" in lower, "must refuse on merge conflicts"
    assert "missing" in lower or "exactly what" in lower, \
        "on refusal it must report exactly what is missing"


def test_explicit_human_confirm_deploy_warning() -> None:
    text = _text()
    lower = text.lower()
    # The one irreversible, outward-facing step: merging deploys prod.
    assert "DEPLOY" in text, "the confirm prompt must state the merge will DEPLOY"
    assert "confirm" in lower, "must require explicit human confirmation"
    assert "does not carry over" in lower or "not carry over" in lower, \
        "approval must not carry over to a future run"


def test_merge_strategy_detected_not_assumed() -> None:
    lower = _text().lower()
    assert "squash" in lower and "merge-commit" in lower.replace("merge commit", "merge-commit"), \
        "must name the strategy options"
    assert "don't assume" in lower or "never assume" in lower or "detect" in lower, \
        "merge strategy comes from repo settings/CLAUDE.md, not assumption"


def test_monitors_deploy_and_validates() -> None:
    lower = _text().lower()
    assert "monitor" in lower, "must monitor the deploy the merge triggers"
    assert "deploy_prod" in lower or "deploy job" in lower, "must watch the deploy job"
    assert "health" in lower, "post-deploy validation must check health"
    assert "sha" in lower, "post-deploy validation must match the deployed SHA to the merge"


def test_branch_cleanup_only_after_green() -> None:
    lower = _text().lower()
    assert "cleanup" in lower or "clean up" in lower, "must clean up the branch"
    assert "only after" in lower, "cleanup happens ONLY AFTER a confirmed-green deploy"
    assert "skip cleanup" in lower, \
        "if deploy validation failed, cleanup is SKIPPED — never delete a branch that may need re-work"
    assert "backup/" in lower, "must also drop the backup/<branch>-preship ref created by /ship-pr"


def test_never_creates_the_pr_it_merges() -> None:
    text = _text()
    lower = text.lower()
    # The anti-pattern: create-and-merge in one shot recreates review-with-no-pause.
    assert "/ship-pr" in text, "must reference /ship-pr as the door that creates the PR"
    assert "gh pr create" not in lower, "must not contain a PR-creation action"


def test_references_lane_skills() -> None:
    lower = _text().lower()
    assert "deploy-local" in lower, "Gitea deploy monitoring reuses the deploy-local skill"
    assert "gh-cli" in lower or "gh pr" in lower, "GitHub lane reuses the gh-cli skill"
