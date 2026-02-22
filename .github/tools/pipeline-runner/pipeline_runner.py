from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guards import evaluate_guard
from schema import CompletionEvent, PipelineState, TransitionResult, parse_pipeline_state, to_state_dict
from transitions import TRANSITIONS, Transition, _REGISTRY_PATH


DEFAULT_STATE_PATH = Path(".github/pipeline-state.json")
ALLOWED_PIPELINE_MODES = {"supervised", "assisted", "autopilot"}
ALLOWED_SUPERVISION_GATES = {
    "intent_approved",
    "adr_approved",
    "plan_approved",
    "review_approved",
}


def _load_stage_map(registry_path: Path = _REGISTRY_PATH) -> dict[str, str]:
    """Load stage-to-agent display-name map from agents.registry.json."""
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return {stage: info["agent"] for stage, info in data["stages"].items()}


# Loaded at import time — add new stages in agents.registry.json only.
STAGE_TO_AGENT: dict[str, str] = _load_stage_map()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _workspace_root(state_file: Path) -> Path:
    return state_file.resolve().parents[1]


def _load_state(state_file: Path) -> PipelineState:
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    return parse_pipeline_state(payload)


def _deep_merge_preserve_unknown(existing: Any, updated: Any) -> Any:
    if isinstance(existing, dict) and isinstance(updated, dict):
        merged = dict(existing)
        for key, value in updated.items():
            merged[key] = _deep_merge_preserve_unknown(existing.get(key), value)
        return merged
    return updated


def _save_state(state_file: Path, state: PipelineState) -> None:
    state.last_updated = _now_utc()
    updated_payload = to_state_dict(state)
    if state_file.exists():
        existing_payload = json.loads(state_file.read_text(encoding="utf-8"))
        updated_payload = _deep_merge_preserve_unknown(existing_payload, updated_payload)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(updated_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _print_json_error(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    raise SystemExit(code)


def _sorted_transitions() -> list[Transition]:
    return sorted(TRANSITIONS, key=lambda item: item.priority, reverse=True)


def _is_hotfix(state: PipelineState) -> bool:
    return (state.type or "").strip().lower() == "hotfix"


def _matches_transition(state: PipelineState, event: CompletionEvent, transition: Transition) -> bool:
    if transition.id in {"T-24", "T-25", "T-26", "T-27"}:
        return False
    if transition.from_stage != state.current_stage:
        return False
    if transition.event != event.result_status:
        return False

    if transition.hotfix_only and not _is_hotfix(state):
        return False

    if not transition.hotfix_only and _is_hotfix(state):
        non_hotfix_ids = {"T-13", "T-14", "T-15", "T-16"}
        if transition.id not in non_hotfix_ids:
            return False

    return True


def _effective_mode(mode: str | None) -> str:
    return (mode or "supervised").strip().lower()


def _gate_satisfied(state: PipelineState, gate_name: str | None) -> bool:
    if gate_name is None:
        return True
    mode = _effective_mode(state.pipeline_mode)
    if mode == "autopilot":
        # intent_approved always requires explicit human approval in every mode
        if gate_name == "intent_approved":
            gates = state.supervision_gates.model_dump()
            return bool(gates.get(gate_name, False))
        # all other gates are auto-satisfied by Orchestrator in autopilot
        return True
    # supervised and assisted: check actual gate state
    gates = state.supervision_gates.model_dump()
    return bool(gates.get(gate_name, False))


def _target_agent(state: PipelineState, next_stage: str | None) -> str | None:
    if next_stage is None:
        return None
    if next_stage == "implement" and state.notes and state.notes.handoff_payload:
        if state.notes.handoff_payload.target_agent:
            return state.notes.handoff_payload.target_agent
    return STAGE_TO_AGENT.get(next_stage, "Orchestrator")


def _build_handoff_prompt(state: PipelineState, next_stage: str | None) -> str | None:
    if next_stage is None:
        return None
    return (
        f"The pipeline is routing to stage '{next_stage}'. "
        "Read .github/pipeline-state.json first and follow your completion protocol."
    )


def compute_next_transition(
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> TransitionResult:
    escalation_ok, escalation_reason = evaluate_guard(
        "no_blocking_escalations",
        state,
        event,
        workspace_root,
    )
    if not escalation_ok:
        return TransitionResult(
            transition_id="T-26",
            next_stage="BLOCKED",
            blocked=True,
            blocked_reason=escalation_reason,
            pipeline_mode=state.pipeline_mode,
            computed_at=_now_utc(),
        )

    if state.current_stage == "BLOCKED":
        recovered, recovered_reason = evaluate_guard("blocked_cleared", state, event, workspace_root)
        if recovered:
            previous_stage = event.stage_completed
            return TransitionResult(
                transition_id="T-27",
                next_stage=previous_stage,
                target_agent=_target_agent(state, previous_stage),
                pipeline_mode=state.pipeline_mode,
                handoff_prompt=_build_handoff_prompt(state, previous_stage),
                computed_at=_now_utc(),
            )
        return TransitionResult(
            transition_id="T-26",
            next_stage="BLOCKED",
            blocked=True,
            blocked_reason=recovered_reason or "Blocked state unresolved",
            pipeline_mode=state.pipeline_mode,
            computed_at=_now_utc(),
        )

    candidates = [
        transition
        for transition in _sorted_transitions()
        if _matches_transition(state, event, transition)
    ]
    if not candidates:
        return TransitionResult(
            blocked=True,
            blocked_reason=(
                f"No transition matched stage='{state.current_stage}' "
                f"event='{event.result_status}'"
            ),
            pipeline_mode=state.pipeline_mode,
            computed_at=_now_utc(),
        )

    for transition in candidates:
        guard_failures: list[str] = []
        for guard_name in transition.guards:
            ok, reason = evaluate_guard(guard_name, state, event, workspace_root)
            if not ok:
                guard_failures.append(reason or f"Guard '{guard_name}' failed")
        if guard_failures:
            continue

        gate_ok = _gate_satisfied(state, transition.gate)
        return TransitionResult(
            transition_id=transition.id,
            next_stage=transition.to_stage,
            target_agent=_target_agent(state, transition.to_stage),
            gate_required=transition.gate,
            gate_satisfied=gate_ok,
            blocked=False,
            blocked_reason=None,
            pipeline_mode=state.pipeline_mode,
            handoff_prompt=_build_handoff_prompt(state, transition.to_stage),
            computed_at=_now_utc(),
        )

    return TransitionResult(
        blocked=True,
        blocked_reason=(
            f"All candidate transitions failed guards for stage='{state.current_stage}' "
            f"event='{event.result_status}'"
        ),
        pipeline_mode=state.pipeline_mode,
        computed_at=_now_utc(),
    )


def _default_event_for_state(state: PipelineState) -> CompletionEvent:
    status_map = {
        "review": "approved",
        "tester": "passed",
        "implement": "complete",
    }
    result_status = status_map.get(state.current_stage, "complete")
    return CompletionEvent(stage_completed=state.current_stage, result_status=result_status)


def _build_result_payload(raw_payload: str | None) -> dict[str, Any] | None:
    if raw_payload is None:
        return None
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("result-payload must be a JSON object")
    return payload


def _preflight_checks(state: PipelineState, workspace_root: Path, target_stage: str) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if target_stage == "tester":
        guard_ok, reason = evaluate_guard(
            "coverage_requirements_present",
            state,
            CompletionEvent(stage_completed=state.current_stage, result_status="complete"),
            workspace_root,
        )
        if not guard_ok:
            errors.append(reason or "coverage_requirements_present check failed")

        payload = state.notes.handoff_payload if state.notes else None
        if payload and payload.upstream_artefact:
            upstream_path = _resolve_upstream_path(workspace_root, payload.upstream_artefact)
            if not upstream_path.exists():
                warnings.append(
                    f"upstream_artefact does not exist: {payload.upstream_artefact}"
                )

    return {
        "ok": not errors,
        "target_stage": target_stage,
        "errors": errors,
        "warnings": warnings,
    }


def _resolve_upstream_path(workspace_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return workspace_root / path


def _increment_retries(state: PipelineState, event: CompletionEvent) -> None:
    if event.stage_completed == "tester" and event.result_status == "failed":
        tester = state.stages.get("tester", {})
        retry_count = int(tester.get("retry_count", 0))
        tester["retry_count"] = retry_count + 1
    elif event.stage_completed == "review" and event.result_status == "revision-requested":
        review = state.stages.get("review", {})
        retry_count = int(review.get("retry_count", 0))
        review["retry_count"] = retry_count + 1


def _advance_state(state: PipelineState, event: CompletionEvent, result: TransitionResult) -> PipelineState:
    current_stage_data = state.stages.setdefault(event.stage_completed, {})
    current_stage_data["status"] = "complete"
    current_stage_data["completed_at"] = _now_utc().isoformat()
    if event.artefact_path:
        current_stage_data["artefact"] = event.artefact_path

    _increment_retries(state, event)

    if result.blocked:
        state.current_stage = "BLOCKED"
        state.blocked_by = result.blocked_reason
    elif result.next_stage:
        state.current_stage = result.next_stage
        state.blocked_by = None
        next_stage_data = state.stages.setdefault(result.next_stage, {})
        if next_stage_data.get("status") == "not_started":
            next_stage_data["status"] = "in_progress"

    if state.notes is None:
        from schema import Notes

        state.notes = Notes()
    state.notes.routing_decision = result.model_dump(mode="json", exclude_none=False)
    return state


def _status_payload(state: PipelineState) -> dict[str, Any]:
    return {
        "project": state.project,
        "feature": state.feature,
        "current_stage": state.current_stage,
        "pipeline_mode": state.pipeline_mode,
        "blocked_by": state.blocked_by,
        "stages": state.stages,
        "last_updated": state.last_updated.isoformat() if state.last_updated else None,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic pipeline state runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_next = subparsers.add_parser("next", help="Compute next transition without writing state")
    parser_next.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_next.add_argument("--completed-stage", type=str, default=None)
    parser_next.add_argument("--result-status", type=str, default=None)
    parser_next.add_argument("--artefact-path", type=str, default=None)

    parser_advance = subparsers.add_parser("advance", help="Advance and persist routing decision")
    parser_advance.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_advance.add_argument("--completed-stage", type=str, required=True)
    parser_advance.add_argument("--result-status", type=str, required=True)
    parser_advance.add_argument("--artefact-path", type=str, default=None)
    parser_advance.add_argument("--result-payload", type=str, default=None)

    parser_preflight = subparsers.add_parser("preflight", help="Run preflight checks")
    parser_preflight.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_preflight.add_argument("--target-stage", type=str, required=True)

    parser_status = subparsers.add_parser("status", help="Print current status")
    parser_status.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)

    parser_mode = subparsers.add_parser("mode", help="Set pipeline mode")
    parser_mode.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_mode.add_argument("--value", type=str, required=True)

    parser_gate = subparsers.add_parser("gate", help="Satisfy a supervision gate")
    parser_gate.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_gate.add_argument("--name", type=str, required=True)

    parser_init = subparsers.add_parser("init", help="Initialize state file from template")
    parser_init.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_init.add_argument("--project", type=str, required=True)
    parser_init.add_argument("--feature", type=str, required=True)
    parser_init.add_argument("--type", type=str, default=None)
    parser_init.add_argument("--force", action="store_true")

    parser_transitions = subparsers.add_parser("transitions", help="Print transitions from registry")
    parser_transitions.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)

    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    state_file = args.state_file
    workspace_root = _workspace_root(state_file)

    if args.command == "transitions":
        registry = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        transitions = registry.get("transitions", [])
        print(json.dumps(transitions, ensure_ascii=False))
        return

    if args.command == "init":
        if state_file.exists() and not args.force:
            _print_json_error(
                f"state file already exists: {state_file}. Use --force to overwrite."
            )

        template_path = workspace_root / ".github" / "pipeline-state.template.json"
        if not template_path.exists():
            _print_json_error(f"template not found: {template_path}")

        template = json.loads(template_path.read_text(encoding="utf-8"))
        template["project"] = args.project
        template["feature"] = args.feature
        template["pipeline_mode"] = template.get("pipeline_mode") or "supervised"
        template["type"] = args.type
        template["last_updated"] = _now_utc().isoformat()

        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps(template, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "project": args.project,
                    "feature": args.feature,
                    "type": args.type,
                    "state_file": str(state_file),
                },
                ensure_ascii=False,
            )
        )
        return

    state = _load_state(state_file)

    if args.command == "status":
        print(json.dumps(_status_payload(state), ensure_ascii=False))
        return

    if args.command == "mode":
        requested_mode = args.value.strip().lower()
        if requested_mode not in ALLOWED_PIPELINE_MODES:
            _print_json_error(
                "invalid pipeline mode. expected one of: supervised, assisted, autopilot"
            )
        state.pipeline_mode = requested_mode
        _save_state(state_file, state)
        print(json.dumps({"ok": True, "pipeline_mode": requested_mode}, ensure_ascii=False))
        return

    if args.command == "gate":
        gate_name = args.name.strip()
        if gate_name not in ALLOWED_SUPERVISION_GATES:
            _print_json_error(f"unknown supervision gate: {gate_name}")
        setattr(state.supervision_gates, gate_name, True)
        _save_state(state_file, state)
        print(
            json.dumps(
                {
                    "ok": True,
                    "supervision_gate": gate_name,
                    "satisfied": True,
                },
                ensure_ascii=False,
            )
        )
        return

    if args.command == "preflight":
        preflight_result = _preflight_checks(state, workspace_root, args.target_stage)
        print(json.dumps(preflight_result, ensure_ascii=False))
        if not preflight_result["ok"]:
            raise SystemExit(2)
        return

    if args.command == "next":
        if args.completed_stage and args.result_status:
            event = CompletionEvent(
                stage_completed=args.completed_stage,
                result_status=args.result_status,
                artefact_path=args.artefact_path,
            )
        else:
            event = _default_event_for_state(state)
        next_result: TransitionResult = compute_next_transition(state, event, workspace_root)
        print(next_result.model_dump_json(exclude_none=False))
        if next_result.blocked:
            raise SystemExit(1)
        return

    if args.command == "advance":
        # GAP-I2-b: idempotency guard — if the stage being completed is already
        # marked complete, this is a duplicate call; warn and no-op to prevent
        # double-advancing the pipeline by two steps.
        _already_done = state.stages.get(args.completed_stage, {}).get("status") == "complete"
        if _already_done:
            print(json.dumps({
                "ok": False,
                "warning": "idempotency",
                "message": (
                    f"Stage '{args.completed_stage}' is already marked complete"
                    " — advance is a no-op. State unchanged."
                ),
                "current_stage": state.current_stage,
            }, ensure_ascii=False))
            return
        event = CompletionEvent(
            stage_completed=args.completed_stage,
            result_status=args.result_status,
            artefact_path=args.artefact_path,
            result_payload=_build_result_payload(args.result_payload),
        )
        advance_result: TransitionResult = compute_next_transition(state, event, workspace_root)
        state = _advance_state(state, event, advance_result)
        _save_state(state_file, state)
        print(advance_result.model_dump_json(exclude_none=False))
        if advance_result.blocked:
            raise SystemExit(1)
        return


if __name__ == "__main__":
    main()
