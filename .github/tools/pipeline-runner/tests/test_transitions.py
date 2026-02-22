from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_runner import compute_next_transition
from schema import CompletionEvent
from transitions import TRANSITIONS


def _write_frontmatter(path: Path, approval: str = "approved") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\napproval: {approval}\n---\nbody\n", encoding="utf-8")


def test_transition_table_contains_t01_through_t27() -> None:
    ids = {transition.id for transition in TRANSITIONS}
    expected = {f"T-{number:02d}" for number in range(1, 28)}
    assert expected.issubset(ids)


@pytest.mark.parametrize(
    ("stage", "event", "artefact_name", "gate", "expected"),
    [
        ("intent", "complete", "intent.md", "intent_approved", "T-01"),
        ("prd", "complete", "prd.md", None, "T-02"),
        ("architect", "complete", "adr.md", "adr_approved", "T-03"),
        ("plan", "complete", "plan.md", "plan_approved", "T-04"),
    ],
)
def test_main_path_early_transitions(
    make_state,
    workspace_root: Path,
    stage: str,
    event: str,
    artefact_name: str,
    gate: str | None,
    expected: str,
) -> None:
    artefact = workspace_root / artefact_name
    _write_frontmatter(artefact)

    gates = {}
    if gate:
        gates[gate] = True

    state = make_state(
        stage,
        stage_overrides={stage: {"artefact": artefact_name}},
        supervision_overrides=gates,
    )
    transition = compute_next_transition(
        state,
        CompletionEvent(stage_completed=stage, result_status=event),
        workspace_root,
    )
    assert transition.transition_id == expected
    assert transition.blocked is False


def test_t05_implement_to_tester_when_all_phases_done(make_state, workspace_root: Path) -> None:
    state = make_state(
        "implement",
        stage_overrides={"implement": {"current_phase": 3, "total_phases": 3}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="implement", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-05"
    assert result.next_stage == "tester"


def test_t06_tester_to_review_on_passed(make_state, workspace_root: Path) -> None:
    state = make_state("tester")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="passed"),
        workspace_root,
    )
    assert result.transition_id == "T-06"
    assert result.next_stage == "review"


def test_t07_review_to_closed_on_approved(make_state, workspace_root: Path) -> None:
    state = make_state("review", supervision_overrides={"review_approved": True})
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="review", result_status="approved"),
        workspace_root,
    )
    assert result.transition_id == "T-07"
    assert result.next_stage == "closed"


def test_t08_architect_to_security_when_parallel_enabled(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "adr.md"
    _write_frontmatter(artefact)
    state = make_state(
        "architect",
        stage_overrides={"architect": {"artefact": "adr.md"}},
        notes={
            "handoff_payload": None,
            "parallel_groups": {"arch_security": {"stages": ["architect", "security"]}},
        },
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="architect", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-08"
    assert result.next_stage == "security"


def test_t09_security_to_plan_when_join_ready(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "security.md"
    _write_frontmatter(artefact)
    state = make_state(
        "security",
        stage_overrides={
            "security": {"artefact": "security.md"},
            "architect": {"status": "complete"},
        },
        supervision_overrides={"adr_approved": True},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="security", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-09"
    assert result.next_stage == "plan"


def test_t10_plan_to_ux_research_when_ui_track_enabled(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "plan.md"
    _write_frontmatter(artefact)
    state = make_state(
        "plan",
        stage_overrides={"plan": {"artefact": "plan.md"}},
        notes={"handoff_payload": None, "ui_track": True},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="plan", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-10"
    assert result.next_stage == "ux_research"


def test_t11_ux_research_to_ui_design(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "ux.md"
    artefact.write_text("research", encoding="utf-8")
    state = make_state(
        "ux_research",
        stage_overrides={"ux_research": {"artefact": "ux.md"}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="ux_research", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-11"


def test_t12_ui_design_to_implement(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "ui.md"
    _write_frontmatter(artefact)
    state = make_state(
        "ui_design",
        stage_overrides={"ui_design": {"artefact": "ui.md"}},
        supervision_overrides={"plan_approved": True},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="ui_design", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-12"
    assert result.next_stage == "implement"


def test_t13_implement_loop_when_more_phases_remain(make_state, workspace_root: Path) -> None:
    state = make_state(
        "implement",
        stage_overrides={"implement": {"current_phase": 1, "total_phases": 3}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="implement", result_status="phase_complete"),
        workspace_root,
    )
    assert result.transition_id == "T-13"
    assert result.next_stage == "implement"


def test_t13_final_phase_does_not_loop(make_state, workspace_root: Path) -> None:
    state = make_state(
        "implement",
        stage_overrides={"implement": {"current_phase": 3, "total_phases": 3}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="implement", result_status="phase_complete"),
        workspace_root,
    )
    assert result.blocked is True


def test_t14_retry_within_budget(make_state, workspace_root: Path) -> None:
    state = make_state("tester", stage_overrides={"tester": {"retry_count": 1, "max_retries": 3}})
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="failed"),
        workspace_root,
    )
    assert result.transition_id == "T-14"
    assert result.next_stage == "implement"


def test_t15_retry_exhausted_blocks(make_state, workspace_root: Path) -> None:
    state = make_state("tester", stage_overrides={"tester": {"retry_count": 3, "max_retries": 3}})
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="failed"),
        workspace_root,
    )
    assert result.transition_id == "T-15"
    assert result.next_stage == "BLOCKED"


def test_t16_review_revision_requested_returns_implement(make_state, workspace_root: Path) -> None:
    state = make_state("review")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="review", result_status="revision-requested"),
        workspace_root,
    )
    assert result.transition_id == "T-16"


def test_t17_hotfix_intake_unknown_to_debug(make_state, workspace_root: Path) -> None:
    state = make_state("intake", pipeline_type="hotfix")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intake", result_status="hotfix_unknown"),
        workspace_root,
    )
    assert result.transition_id == "T-17"
    assert result.next_stage == "debug"


def test_t18_hotfix_intake_known_to_implement(make_state, workspace_root: Path) -> None:
    state = make_state("intake", pipeline_type="hotfix")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intake", result_status="hotfix_known"),
        workspace_root,
    )
    assert result.transition_id == "T-18"
    assert result.next_stage == "implement"


def test_t19_hotfix_debug_to_implement(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "debug.md"
    artefact.write_text("debug", encoding="utf-8")
    state = make_state(
        "debug",
        pipeline_type="hotfix",
        stage_overrides={"debug": {"artefact": "debug.md"}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="debug", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-19"


def test_t20_hotfix_implement_to_tester_without_phase_check(make_state, workspace_root: Path) -> None:
    state = make_state(
        "implement",
        pipeline_type="hotfix",
        stage_overrides={"implement": {"current_phase": 0, "total_phases": 9}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="implement", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-20"


def test_t21_hotfix_tester_to_review_for_security_deferrals(make_state, workspace_root: Path) -> None:
    state = make_state(
        "tester",
        pipeline_type="hotfix",
        deferred=[
            {
                "id": "D-1",
                "title": "auth header",
                "file": "app.py",
                "detail": "secure this",
                "severity": "security",
            }
        ],
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="passed"),
        workspace_root,
    )
    assert result.transition_id == "T-21"
    assert result.next_stage == "review"


def test_t22_hotfix_tester_to_closed_when_no_security_deferrals(make_state, workspace_root: Path) -> None:
    state = make_state(
        "tester",
        pipeline_type="hotfix",
        deferred=[
            {
                "id": "D-2",
                "title": "style",
                "file": "app.py",
                "detail": "style change",
                "severity": "nit",
            }
        ],
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="passed"),
        workspace_root,
    )
    assert result.transition_id == "T-22"
    assert result.next_stage == "closed"


def test_t23_closed_reentry_with_deferred_items(make_state, workspace_root: Path) -> None:
    state = make_state(
        "closed",
        deferred=[
            {
                "id": "D-3",
                "title": "follow-up",
                "file": "x.py",
                "detail": "later",
                "severity": "low",
            }
        ],
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="closed", result_status="deferred_reentry"),
        workspace_root,
    )
    assert result.transition_id == "T-23"


def test_t23_closed_reentry_without_deferred_items_blocks(make_state, workspace_root: Path) -> None:
    state = make_state("closed")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="closed", result_status="deferred_reentry"),
        workspace_root,
    )
    assert result.blocked is True


def test_pipeline_mode_auto_normalises_to_assisted_no_auto_gate(make_state, workspace_root: Path) -> None:
    """'auto' is a deprecated alias for 'assisted'. Gates are NOT auto-satisfied."""
    artefact = workspace_root / "intent.md"
    artefact.write_text("intent", encoding="utf-8")
    state = make_state(
        "intent",
        pipeline_mode="auto",
        stage_overrides={"intent": {"artefact": "intent.md"}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-01"
    assert result.gate_satisfied is False  # 'auto' normalised to 'assisted'; requires explicit approval


def test_pipeline_mode_autopilot_does_not_auto_satisfy_intent_approved(make_state, workspace_root: Path) -> None:
    """autopilot mode never auto-satisfies 'intent_approved' — always requires human."""
    artefact = workspace_root / "intent.md"
    artefact.write_text("intent", encoding="utf-8")
    state = make_state(
        "intent",
        pipeline_mode="autopilot",
        stage_overrides={"intent": {"artefact": "intent.md"}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-01"
    assert result.gate_satisfied is False  # intent_approved is the one gate that autopilot doesn't bypass


def test_pipeline_mode_supervised_requires_gate_true(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "intent.md"
    artefact.write_text("intent", encoding="utf-8")
    state = make_state(
        "intent",
        pipeline_mode="supervised",
        stage_overrides={"intent": {"artefact": "intent.md"}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-01"
    assert result.gate_satisfied is False


def test_pipeline_mode_supervised_gate_true_when_enabled(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "intent.md"
    artefact.write_text("intent", encoding="utf-8")
    state = make_state(
        "intent",
        pipeline_mode="supervised",
        stage_overrides={"intent": {"artefact": "intent.md"}},
        supervision_overrides={"intent_approved": True},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert result.gate_satisfied is True


def test_t26_blocks_when_blocking_escalation_exists(make_state, workspace_root: Path) -> None:
    escalations = workspace_root / "agent-docs" / "escalations"
    escalations.mkdir(parents=True)
    (escalations / "blocking.md").write_text("---\nseverity: blocking\n---\n", encoding="utf-8")

    state = make_state("tester")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="passed"),
        workspace_root,
    )
    assert result.transition_id == "T-26"
    assert result.blocked is True


def test_t27_unblocks_when_blocked_by_cleared(make_state, workspace_root: Path) -> None:
    state = make_state("BLOCKED", blocked_by=None)
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="implement", result_status="recovered"),
        workspace_root,
    )
    assert result.transition_id == "T-27"
    assert result.next_stage == "implement"


def test_t27_stays_blocked_if_blocked_by_present(make_state, workspace_root: Path) -> None:
    state = make_state("BLOCKED", blocked_by="waiting for approval")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="implement", result_status="recovered"),
        workspace_root,
    )
    assert result.blocked is True


def test_unknown_stage_event_blocks(make_state, workspace_root: Path) -> None:
    state = make_state("janitor")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="janitor", result_status="complete"),
        workspace_root,
    )
    assert result.blocked is True


def test_invalid_event_blocks(make_state, workspace_root: Path) -> None:
    state = make_state("tester")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="done"),
        workspace_root,
    )
    assert result.blocked is True


def test_duplicate_completion_like_status_blocks(make_state, workspace_root: Path) -> None:
    state = make_state("review")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="review", result_status="complete"),
        workspace_root,
    )
    assert result.blocked is True


def test_guard_failure_missing_artefact_blocks(make_state, workspace_root: Path) -> None:
    state = make_state("intent")
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert result.blocked is True


def test_guard_failure_missing_approval_blocks(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "prd.md"
    _write_frontmatter(artefact, approval="pending")
    state = make_state("prd", stage_overrides={"prd": {"artefact": "prd.md"}})
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="prd", result_status="complete"),
        workspace_root,
    )
    assert result.blocked is True


def test_guard_failure_gate_not_satisfied_still_returns_transition(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "intent.md"
    artefact.write_text("ok", encoding="utf-8")
    state = make_state("intent", stage_overrides={"intent": {"artefact": "intent.md"}})
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="intent", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-01"
    assert result.gate_satisfied is False


def test_guard_failure_parallel_not_supported_path(make_state, workspace_root: Path) -> None:
    artefact = workspace_root / "adr.md"
    _write_frontmatter(artefact)
    state = make_state(
        "architect",
        stage_overrides={"architect": {"artefact": "adr.md"}},
        notes={"handoff_payload": None, "parallel_groups": {"group": {"stages": ["architect"]}}},
    )
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="architect", result_status="complete"),
        workspace_root,
    )
    assert result.transition_id == "T-08"


def test_guard_failure_retry_budget_remaining_mismatch(make_state, workspace_root: Path) -> None:
    state = make_state("tester", stage_overrides={"tester": {"retry_count": 5, "max_retries": 5}})
    result = compute_next_transition(
        state,
        CompletionEvent(stage_completed="tester", result_status="failed"),
        workspace_root,
    )
    assert result.transition_id == "T-15"
