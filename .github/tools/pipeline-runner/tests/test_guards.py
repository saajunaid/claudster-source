from __future__ import annotations

from pathlib import Path

from guards import evaluate_guard
from schema import CompletionEvent


def _write_frontmatter(path: Path, approval: str = "approved") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\napproval: {approval}\n---\ncontent\n", encoding="utf-8")


def test_artefact_exists_true(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "doc.md"
    artefact.write_text("ok", encoding="utf-8")
    state = make_state("intent", stage_overrides={"intent": {"artefact": "doc.md"}})
    ok, reason = evaluate_guard(
        "artefact_exists",
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert ok is True
    assert reason is None


def test_artefact_exists_false(make_state, workspace_root: Path) -> None:
    state = make_state("intent")
    ok, reason = evaluate_guard(
        "artefact_exists",
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert ok is False
    assert reason is not None


def test_artefact_approved_true(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "approved.md"
    _write_frontmatter(artefact, "approved")
    state = make_state("prd", stage_overrides={"prd": {"artefact": "approved.md"}})
    ok, _ = evaluate_guard(
        "artefact_approved",
        state,
        CompletionEvent(stage_completed="prd", result_status="complete"),
        workspace_root,
    )
    assert ok is True


def test_artefact_approved_false(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "pending.md"
    _write_frontmatter(artefact, "pending")
    state = make_state("prd", stage_overrides={"prd": {"artefact": "pending.md"}})
    ok, _ = evaluate_guard(
        "artefact_approved",
        state,
        CompletionEvent(stage_completed="prd", result_status="complete"),
        workspace_root,
    )
    assert ok is False


def test_phase_guards(make_state, workspace_root: Path) -> None:
    state = make_state("implement", stage_overrides={"implement": {"current_phase": 1, "total_phases": 2}})
    more_ok, _ = evaluate_guard(
        "more_phases_remain",
        state,
        CompletionEvent(stage_completed="implement", result_status="phase_complete"),
        workspace_root,
    )
    all_ok, _ = evaluate_guard(
        "all_phases_done",
        state,
        CompletionEvent(stage_completed="implement", result_status="complete"),
        workspace_root,
    )
    assert more_ok is True
    assert all_ok is False


def test_retry_guards(make_state, workspace_root: Path) -> None:
    state = make_state("tester", stage_overrides={"tester": {"retry_count": 2, "max_retries": 2}})
    remain_ok, _ = evaluate_guard(
        "retry_budget_remaining",
        state,
        CompletionEvent(stage_completed="tester", result_status="failed"),
        workspace_root,
    )
    exhausted_ok, _ = evaluate_guard(
        "retry_budget_exhausted",
        state,
        CompletionEvent(stage_completed="tester", result_status="failed"),
        workspace_root,
    )
    assert remain_ok is False
    assert exhausted_ok is True


def test_security_deferral_guards(make_state, workspace_root: Path) -> None:
    state = make_state(
        "tester",
        deferred=[
            {
                "id": "S-1",
                "title": "security",
                "file": "a.py",
                "detail": "fix",
                "severity": "security",
            }
        ],
    )
    has_ok, _ = evaluate_guard(
        "has_security_deferrals",
        state,
        CompletionEvent(stage_completed="tester", result_status="passed"),
        workspace_root,
    )
    none_ok, _ = evaluate_guard(
        "no_security_deferrals",
        state,
        CompletionEvent(stage_completed="tester", result_status="passed"),
        workspace_root,
    )
    assert has_ok is True
    assert none_ok is False


def test_has_deferred_items_guard(make_state, workspace_root: Path) -> None:
    state = make_state(
        "closed",
        deferred=[{"id": "D1", "title": "x", "file": "x", "detail": "x", "severity": "low"}],
    )
    ok, _ = evaluate_guard(
        "has_deferred_items",
        state,
        CompletionEvent(stage_completed="closed", result_status="deferred_reentry"),
        workspace_root,
    )
    assert ok is True


def test_coverage_requirements_present_guard(make_state, workspace_root: Path) -> None:
    state = make_state(
        "plan",
        notes={
            "handoff_payload": {
                "upstream_artefact": "docs/plan.md",
                "coverage_requirements": ["FR-1", "NFR-2"],
            }
        },
    )
    ok, _ = evaluate_guard(
        "coverage_requirements_present",
        state,
        CompletionEvent(stage_completed="plan", result_status="complete"),
        workspace_root,
    )
    assert ok is True


def test_no_blocking_escalations_guard_false(make_state, workspace_root: Path) -> None:
    path = workspace_root / "agent-docs" / "escalations"
    path.mkdir(parents=True)
    (path / "block.md").write_text("---\nseverity: blocking\n---\n", encoding="utf-8")
    state = make_state("tester")
    ok, _ = evaluate_guard(
        "no_blocking_escalations",
        state,
        CompletionEvent(stage_completed="tester", result_status="passed"),
        workspace_root,
    )
    assert ok is False


def test_pipeline_mode_guards(make_state, workspace_root: Path) -> None:
    auto_state = make_state("intent", pipeline_mode="auto")
    supervised_state = make_state("intent", pipeline_mode="supervised")

    auto_ok, _ = evaluate_guard(
        "pipeline_mode_auto",
        auto_state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    supervised_ok, _ = evaluate_guard(
        "pipeline_mode_supervised",
        supervised_state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert auto_ok is True
    assert supervised_ok is True


def test_unknown_guard_returns_false(make_state, workspace_root: Path) -> None:
    state = make_state("intent")
    ok, reason = evaluate_guard(
        "does_not_exist",
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert ok is False
    assert "Unknown guard" in (reason or "")
