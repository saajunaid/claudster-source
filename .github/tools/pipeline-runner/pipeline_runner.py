from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from guards import evaluate_guard
from schema import CompletionEvent, PipelineState, TransitionResult, parse_pipeline_state, to_state_dict
from transitions import TRANSITIONS, Transition, _REGISTRY_PATH


DEFAULT_STATE_PATH = Path(".github/pipeline-state.json")
ALLOWED_PIPELINE_MODES = {"supervised", "assisted", "autopilot"}
_BASE_SUPERVISION_GATES = {
    "intent_approved",
    "adr_approved",
    "plan_approved",
    "plan_validated",
    "review_approved",
}


def _load_registry_gates() -> set[str]:
    """Union of gate names declared in agents.registry.json transitions."""
    try:
        data = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {t["gate"] for t in data.get("transitions", []) if t.get("gate")}


ALLOWED_SUPERVISION_GATES = _BASE_SUPERVISION_GATES | _load_registry_gates()


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


def _as_workspace_relative(workspace_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_workspace_path(workspace_root: Path, raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return workspace_root / candidate


def _read_frontmatter_file(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not content.startswith("---"):
        return {}
    end_index = content.find("\n---", 3)
    if end_index == -1:
        return {}
    raw = content[3:end_index].strip()
    if not raw:
        return {}
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _frontmatter_approval(path: Path) -> str | None:
    value = _read_frontmatter_file(path).get("approval")
    return str(value).strip().lower() if value is not None else None


def _is_approved(path: Path) -> bool:
    return _frontmatter_approval(path) == "approved"


def _slug_matches(path: Path, feature: str) -> bool:
    feature_slug = feature.strip().lower()
    if not feature_slug:
        return False
    normalized_name = path.stem.lower()
    return feature_slug in normalized_name


def _find_matching_markdown(
    workspace_root: Path,
    feature: str,
    locations: list[str],
    *,
    recursive: bool = False,
    ignore_parts: set[str] | None = None,
) -> list[Path]:
    matches: list[Path] = []
    ignored = ignore_parts or set()
    for raw_location in locations:
        base = workspace_root / raw_location
        if not base.exists():
            continue
        iterator = base.rglob("*.md") if recursive else base.glob("*.md")
        for path in iterator:
            if any(part in ignored for part in path.parts):
                continue
            if _slug_matches(path, feature):
                matches.append(path)
    return sorted(set(matches), key=lambda p: (_is_approved(p) is False, len(p.parts), p.as_posix()))


def _primary_artifact(paths: list[Path]) -> Path | None:
    approved = [path for path in paths if _is_approved(path)]
    if approved:
        return approved[0]
    return paths[0] if paths else None


def _preflight_validates_plan(workspace_root: Path, plan_path: Path) -> tuple[bool, Path | None]:
    candidates = [
        workspace_root / ".github" / "agent-docs" / "preflight-report.md",
        workspace_root / "agent-docs" / "preflight-report.md",
    ]
    expected = _as_workspace_relative(workspace_root, plan_path)
    for candidate in candidates:
        if not candidate.exists():
            continue
        frontmatter = _read_frontmatter_file(candidate)
        result = str(frontmatter.get("result", "")).strip().upper()
        plan = str(frontmatter.get("plan", "")).strip()
        if result == "PASS" and (not plan or plan == expected or Path(plan).name == plan_path.name):
            return True, candidate
    return False, None


def discover_artefacts(workspace_root: Path, feature: str) -> dict[str, Any]:
    """Discover existing pipeline artefacts for a feature slug.

    This is deliberately deterministic so Orchestrator can consume it without
    guessing from prose instructions.
    """
    plan_paths = _find_matching_markdown(
        workspace_root,
        feature,
        [".github/plans", "plans"],
        recursive=False,
        ignore_parts={"backlog"},
    )
    prd_paths = _find_matching_markdown(
        workspace_root,
        feature,
        [".github/agent-docs/prd", "agent-docs/prd"],
    )
    adr_paths = _find_matching_markdown(
        workspace_root,
        feature,
        [
            ".github/agent-docs/architecture",
            "agent-docs/architecture",
            "docs/architecture/agentic-adr",
            "docs/architecture",
        ],
        recursive=True,
    )

    plan = _primary_artifact(plan_paths)
    prd = _primary_artifact(prd_paths)
    adr = _primary_artifact(adr_paths)
    preflight_ok = False
    preflight_report: Path | None = None
    if plan:
        preflight_ok, preflight_report = _preflight_validates_plan(workspace_root, plan)

    if plan and _is_approved(plan) and preflight_ok:
        recommended_entry_stage = "implement"
        reason = "approved plan already has a PASS preflight report"
    elif plan and _is_approved(plan):
        recommended_entry_stage = "preflight"
        reason = "approved plan found; validate before implementation"
    elif prd and _is_approved(prd) and adr and _is_approved(adr):
        recommended_entry_stage = "plan"
        reason = "approved PRD and architecture found; create or refresh plan"
    elif prd and _is_approved(prd):
        recommended_entry_stage = "architect"
        reason = "approved PRD found; architecture is missing or not approved"
    elif adr and _is_approved(adr):
        recommended_entry_stage = "plan"
        reason = "approved architecture found; plan is missing"
    elif adr:
        recommended_entry_stage = "architect"
        reason = "architecture artefact found but it is not approved"
    else:
        recommended_entry_stage = "intent"
        reason = "no approved feature artefacts found"

    def _artifact_payload(paths: list[Path], primary: Path | None) -> dict[str, Any]:
        return {
            "primary": _as_workspace_relative(workspace_root, primary) if primary else None,
            "approved": bool(primary and _is_approved(primary)),
            "candidates": [
                {
                    "path": _as_workspace_relative(workspace_root, path),
                    "approval": _frontmatter_approval(path),
                }
                for path in paths
            ],
        }

    return {
        "ok": True,
        "feature": feature,
        "recommended_entry_stage": recommended_entry_stage,
        "reason": reason,
        "artifacts": {
            "plan": _artifact_payload(plan_paths, plan),
            "prd": _artifact_payload(prd_paths, prd),
            "architecture": _artifact_payload(adr_paths, adr),
            "preflight": {
                "primary": _as_workspace_relative(workspace_root, preflight_report)
                if preflight_report
                else None,
                "passed": preflight_ok,
            },
        },
    }


def _write_artifacts_registry(workspace_root: Path, discovery: dict[str, Any]) -> Path:
    registry_path = workspace_root / ".github" / "agent-docs" / "artifacts.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _now_utc().isoformat(),
        "feature": discovery.get("feature"),
        "recommended_entry_stage": discovery.get("recommended_entry_stage"),
        "artifacts": discovery.get("artifacts", {}),
    }
    registry_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return registry_path


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


def _ensure_notes_dict(state: PipelineState) -> dict[str, Any]:
    if state.notes is None:
        from schema import Notes

        state.notes = Notes()
    return state.notes.model_dump(mode="json", by_alias=True, exclude_none=False)


def _replace_notes_from_dict(state: PipelineState, notes_payload: dict[str, Any]) -> None:
    from schema import Notes

    state.notes = Notes.model_validate(notes_payload)


def _append_note_list(state: PipelineState, key: str, item: dict[str, Any], *, limit: int = 100) -> None:
    notes = _ensure_notes_dict(state)
    values = notes.get(key)
    if not isinstance(values, list):
        values = []
    values.append(item)
    notes[key] = values[-limit:]
    _replace_notes_from_dict(state, notes)


def _set_note_key(state: PipelineState, key: str, value: Any) -> None:
    notes = _ensure_notes_dict(state)
    notes[key] = value
    _replace_notes_from_dict(state, notes)


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
    _append_note_list(
        state,
        "_routing_history",
        {
            "at": _now_utc().isoformat(),
            "stage_completed": event.stage_completed,
            "result_status": event.result_status,
            "artefact_path": event.artefact_path,
            "transition_id": result.transition_id,
            "next_stage": result.next_stage,
            "target_agent": result.target_agent,
            "blocked": result.blocked,
            "blocked_reason": result.blocked_reason,
        },
    )
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
        "progress_line": _format_progress_line(state),
    }


def _count_plan_phases(plan_path: Path) -> int:
    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError:
        return 1
    phase_numbers = {
        int(match.group(1))
        for match in re.finditer(r"(?m)^#{2,4}\s+Phase\s+(\d+)\b", text, flags=re.IGNORECASE)
    }
    return max(phase_numbers) if phase_numbers else 1


def parse_plan_phases(workspace_root: Path, plan_path: Path) -> dict[str, Any]:
    if not plan_path.exists():
        return {"ok": False, "error": f"plan file does not exist: {plan_path}"}
    text = plan_path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"(?m)^(#{2,4})\s+Phase\s+(\d+)\b[^\n]*", text, flags=re.IGNORECASE))
    phases: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        heading = match.group(0).strip()
        phase_number = int(match.group(2))
        agent_match = re.search(r"(?:\*\*)?Agent(?:\*\*)?\s*:?\s*`?@?([A-Za-z0-9_-]+)`?", section, re.IGNORECASE)
        skills = re.findall(r"`([^`]+/SKILL\.md)`", section)
        instructions = re.findall(r"`([^`]+\.instructions\.md)`", section)
        files = re.findall(r"`([^`]+\.[A-Za-z0-9]{1,8})`", section)
        validation_items = [
            line.strip()[2:].strip()
            for line in section.splitlines()
            if line.strip().startswith("- ") and "validation" not in line.lower()
        ][:20]
        phases.append(
            {
                "phase": phase_number,
                "heading": heading.lstrip("#").strip(),
                "agent": agent_match.group(1) if agent_match else None,
                "line_count": len(section.splitlines()),
                "char_count": len(section),
                "skills": sorted(set(skills)),
                "instructions": sorted(set(instructions)),
                "files": sorted(set(files)),
                "validation_items": validation_items,
            }
        )
    return {
        "ok": True,
        "plan": _as_workspace_relative(workspace_root, plan_path),
        "phase_count": len(phases),
        "phases": phases,
    }


def _phase_by_number(parsed: dict[str, Any], phase_number: int | None) -> dict[str, Any] | None:
    phases = parsed.get("phases") or []
    if not phases:
        return None
    if phase_number is None:
        return phases[0]
    return next((phase for phase in phases if phase.get("phase") == phase_number), None)


def context_guard_for_phase(workspace_root: Path, plan_path: Path, phase_number: int | None = None) -> dict[str, Any]:
    parsed = parse_plan_phases(workspace_root, plan_path)
    if not parsed.get("ok"):
        return parsed
    phase = _phase_by_number(parsed, phase_number)
    if phase is None:
        return {"ok": False, "error": f"phase not found: {phase_number}"}
    line_count = int(phase.get("line_count") or 0)
    char_count = int(phase.get("char_count") or 0)
    risk_terms = ["migration", "schema", "security", "auth", "cache", "concurrency", "deploy", "refactor"]
    heading = str(phase.get("heading") or "").lower()
    risk_hits = [term for term in risk_terms if term in heading]
    if line_count > 500 or char_count > 30000:
        status = "red"
        action = "split phase before execution"
    elif line_count > 250 or char_count > 15000 or len(risk_hits) >= 2:
        status = "yellow"
        action = "execute with a narrow scope and stop after the phase"
    else:
        status = "green"
        action = "safe to execute in one focused session"
    return {
        "ok": True,
        "plan": parsed["plan"],
        "phase": phase.get("phase"),
        "status": status,
        "line_count": line_count,
        "char_count": char_count,
        "risk_terms": risk_hits,
        "recommended_action": action,
        "explanation": (
            "This is a conservative static estimate based on phase size and risk words. "
            "It does not inspect the live model context window."
        ),
    }


def score_plan_quality(workspace_root: Path, plan_path: Path) -> dict[str, Any]:
    parsed = parse_plan_phases(workspace_root, plan_path)
    if not parsed.get("ok"):
        return parsed
    text = plan_path.read_text(encoding="utf-8")
    frontmatter = _read_frontmatter_file(plan_path)
    findings: list[dict[str, str]] = []
    score = 100
    if str(frontmatter.get("approval", "")).lower() != "approved":
        score -= 20
        findings.append({"severity": "critical", "message": "plan is not approved"})
    if parsed["phase_count"] == 0:
        score -= 30
        findings.append({"severity": "critical", "message": "no numbered phases found"})
    for phase in parsed["phases"]:
        if not phase.get("agent"):
            score -= 5
            findings.append({"severity": "warning", "message": f"phase {phase['phase']} has no agent assignment"})
        if not phase.get("validation_items"):
            score -= 5
            findings.append({"severity": "warning", "message": f"phase {phase['phase']} has weak validation detail"})
        guard = context_guard_for_phase(workspace_root, plan_path, int(phase["phase"]))
        if guard.get("status") == "red":
            score -= 10
            findings.append({"severity": "warning", "message": f"phase {phase['phase']} is large enough to split"})
    if "## Source Document Traceability" not in text:
        score -= 10
        findings.append({"severity": "warning", "message": "missing Source Document Traceability section"})
    if "## Scope Changes" not in text:
        score -= 5
        findings.append({"severity": "info", "message": "missing Scope Changes declaration"})
    score = max(0, min(100, score))
    if score >= 85:
        readiness = "ready"
    elif score >= 65:
        readiness = "caution"
    else:
        readiness = "not_ready"
    return {
        "ok": True,
        "plan": _as_workspace_relative(workspace_root, plan_path),
        "score": score,
        "readiness": readiness,
        "phase_count": parsed["phase_count"],
        "findings": findings,
    }


def recommend_model_for_work(stage: str, phase: dict[str, Any] | None = None) -> dict[str, Any]:
    text = " ".join(
        str(value)
        for value in [
            stage,
            phase.get("heading") if phase else "",
            " ".join(phase.get("files") or []) if phase else "",
        ]
    ).lower()
    if any(term in text for term in ["security", "auth", "permission", "crypto"]):
        model = "gpt-5.5"
        reason = "security-sensitive work benefits from strongest reasoning"
    elif any(term in text for term in ["migration", "schema", "database", "sql", "deploy", "infra"]):
        model = "gpt-5.4"
        reason = "architecture/infrastructure work benefits from broader reasoning"
    elif stage in {"implement", "anchor", "debug"}:
        model = "gpt-5.3-codex"
        reason = "coding-heavy stage"
    elif stage in {"review", "preflight"}:
        model = "gpt-5.4"
        reason = "validation/review stage"
    else:
        model = "gpt-5.4"
        reason = "general pipeline stage"
    return {"ok": True, "stage": stage, "recommended_model": model, "reason": reason}


def classify_halt_reason(reason: str | None) -> str | None:
    if not reason:
        return None
    lowered = reason.lower()
    if "artefact" in lowered and ("missing" in lowered or "exists" in lowered):
        return "missing_artefact"
    if "approval" in lowered or "approved" in lowered:
        return "approval_missing"
    if "preflight" in lowered:
        return "preflight_failed"
    if "tester" in lowered or "test" in lowered:
        return "test_failed"
    if "ambiguous" in lowered or "ambiguity" in lowered:
        return "ambiguity"
    if "tool" in lowered or "command" in lowered:
        return "tool_error"
    if "context" in lowered:
        return "context_low"
    if "escalation" in lowered:
        return "blocking_escalation"
    return "unknown"


def recovery_commands_for_issue(issue_type: str | None, state: PipelineState | None = None) -> list[str]:
    if issue_type == "approval_missing":
        return ["junai pipeline gate --name <gate_name>"]
    if issue_type == "missing_artefact":
        return ["junai pipeline doctor", "junai pipeline advance --completed-stage <stage> --result-status <status> --artefact-path <path>"]
    if issue_type == "preflight_failed":
        return ["Fix the plan from .github/agent-docs/preflight-report.md", "junai pipeline advance --completed-stage preflight --result-status passed --artefact-path .github/agent-docs/preflight-report.md"]
    if issue_type == "test_failed":
        return ["Route to debug or fix tests", "junai pipeline advance --completed-stage tester --result-status passed"]
    if issue_type == "blocking_escalation":
        return ["Resolve .github/agent-docs/escalations/*.md", "junai pipeline doctor"]
    if state and state.blocked_by:
        return ["junai pipeline doctor"]
    return []


def _new_transition_result_for_handoff(state: PipelineState, stage: str, reason: str) -> dict[str, Any]:
    return {
        "transition_id": "FAST-TRACK",
        "next_stage": stage,
        "target_agent": _target_agent(state, stage),
        "gate_required": None,
        "gate_satisfied": True,
        "blocked": False,
        "blocked_reason": None,
        "pipeline_mode": state.pipeline_mode,
        "handoff_prompt": _build_handoff_prompt(state, stage),
        "computed_at": _now_utc().isoformat(),
        "reason": reason,
    }


def _set_stage_complete(state: PipelineState, stage: str, artefact: str) -> None:
    record = state.stages.setdefault(stage, {})
    record["status"] = "complete"
    record["completed_at"] = _now_utc().isoformat()
    record["artefact"] = artefact


def fast_track_from_plan(
    state: PipelineState,
    workspace_root: Path,
    plan_path: Path,
    entry_stage: str,
    *,
    mode: str | None = None,
) -> dict[str, Any]:
    if entry_stage not in {"preflight", "implement"}:
        return {"ok": False, "error": "entry stage must be 'preflight' or 'implement'"}
    if not plan_path.exists():
        return {"ok": False, "error": f"plan file does not exist: {plan_path}"}
    if not _is_approved(plan_path):
        return {
            "ok": False,
            "error": "plan must have YAML frontmatter with approval: approved",
            "plan": _as_workspace_relative(workspace_root, plan_path),
        }

    if mode:
        requested_mode = mode.strip().lower()
        if requested_mode not in ALLOWED_PIPELINE_MODES:
            return {"ok": False, "error": "invalid pipeline mode"}
        state.pipeline_mode = requested_mode

    plan_rel = _as_workspace_relative(workspace_root, plan_path)
    preflight_ok, preflight_report = _preflight_validates_plan(workspace_root, plan_path)
    if entry_stage == "implement" and not preflight_ok:
        return {
            "ok": False,
            "error": "entry stage 'implement' requires a PASS preflight report for this plan",
            "recommended_entry_stage": "preflight",
            "plan": plan_rel,
        }

    for gate in ("intent_approved", "adr_approved", "plan_approved"):
        setattr(state.supervision_gates, gate, True)
    if entry_stage == "implement":
        setattr(state.supervision_gates, "plan_validated", True)

    # Fast-track is a runner-owned operation, so it may align state directly.
    for stage in ("intent", "prd", "architect", "plan"):
        _set_stage_complete(state, stage, plan_rel)

    if preflight_ok and preflight_report:
        _set_stage_complete(state, "preflight", _as_workspace_relative(workspace_root, preflight_report))
    else:
        preflight_record = state.stages.setdefault("preflight", {})
        preflight_record["status"] = "in_progress" if entry_stage == "preflight" else "not_started"
        preflight_record.setdefault("artefact", None)
        preflight_record.setdefault("completed_at", None)

    total_phases = _count_plan_phases(plan_path)
    implement = state.stages.setdefault("implement", {})
    implement["total_phases"] = max(int(implement.get("total_phases", 1)), total_phases)
    implement.setdefault("current_phase", 0)
    implement.setdefault("retry_count", 0)
    implement.setdefault("max_retries", 3)

    state.current_stage = entry_stage
    state.blocked_by = None
    current = state.stages.setdefault(entry_stage, {})
    current["status"] = "in_progress"

    handoff_payload = {
        "target_agent": _target_agent(state, entry_stage),
        "scope": "all phases" if entry_stage == "implement" else "validate full plan",
        "summary": f"Fast-track from approved plan {plan_rel}",
        "upstream_artefact": plan_rel,
        "coverage_requirements": [],
        "required_tests": [],
        "exit_criteria": "Execute the approved plan phase-by-phase without user approval in autopilot mode.",
    }
    _set_note_key(state, "handoff_payload", handoff_payload)
    _set_note_key(
        state,
        "_routing_decision",
        _new_transition_result_for_handoff(
            state,
            entry_stage,
            f"fast-track from approved plan: {plan_rel}",
        ),
    )
    _append_note_list(
        state,
        "_routing_history",
        {
            "at": _now_utc().isoformat(),
            "transition_id": "FAST-TRACK",
            "next_stage": entry_stage,
            "target_agent": _target_agent(state, entry_stage),
            "artefact_path": plan_rel,
            "blocked": False,
        },
    )

    return {
        "ok": True,
        "entry_stage": entry_stage,
        "pipeline_mode": state.pipeline_mode,
        "plan": plan_rel,
        "total_phases": total_phases,
        "current_stage": state.current_stage,
        "target_agent": _target_agent(state, entry_stage),
        "preflight_report": _as_workspace_relative(workspace_root, preflight_report)
        if preflight_report
        else None,
    }


def _load_or_initialize_state_for_fast_track(
    state_file: Path,
    workspace_root: Path,
    *,
    project: str | None,
    feature: str | None,
) -> PipelineState:
    if state_file.exists():
        return _load_state(state_file)
    if not project or not feature:
        _print_json_error(
            "state file is missing. Provide --project and --feature to initialize before fast-track."
        )
    template_path = workspace_root / ".github" / "pipeline-state.template.json"
    if not template_path.exists():
        _print_json_error(f"template not found: {template_path}")
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    payload["project"] = project
    payload["feature"] = feature
    payload["last_updated"] = _now_utc().isoformat()
    return parse_pipeline_state(payload)


def _stage_artefact_paths(state: PipelineState, stage: str) -> list[str]:
    record = state.stages.get(stage, {})
    raw = record.get("artefact") if isinstance(record, dict) else None
    if not raw:
        return []
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def doctor_payload(state: PipelineState | None, workspace_root: Path, state_file: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    if state is None:
        return {
            "ok": False,
            "errors": [f"state file does not exist: {state_file}"],
            "warnings": [],
            "suggestions": ["Run junai pipeline init --project <name> --feature <slug>"],
        }

    if state.current_stage not in STAGE_TO_AGENT:
        errors.append(f"unknown current_stage: {state.current_stage}")
        suggestions.append("Run junai pipeline init --force or repair current_stage to a registry stage.")

    if state.blocked_by:
        warnings.append(f"pipeline is blocked: {state.blocked_by}")

    if state.notes and state.notes.routing_decision:
        decision = state.notes.routing_decision
        if not isinstance(decision, dict):
            errors.append("_notes._routing_decision is not an object")
        elif decision.get("blocked"):
            warnings.append(f"routing decision is blocked: {decision.get('blocked_reason')}")
        elif decision.get("next_stage") and decision.get("next_stage") != state.current_stage:
            warnings.append(
                "_notes._routing_decision.next_stage differs from current_stage; "
                "rerun junai pipeline next or clear stale routing decision."
            )

    for stage, record in state.stages.items():
        if not isinstance(record, dict):
            continue
        if record.get("status") != "complete":
            continue
        for raw_path in _stage_artefact_paths(state, stage):
            resolved = _resolve_workspace_path(workspace_root, raw_path)
            if not resolved or not resolved.exists():
                errors.append(f"completed stage '{stage}' references missing artefact: {raw_path}")
            elif stage in {"prd", "architect", "plan", "ui_design"} and not _is_approved(resolved):
                errors.append(f"completed stage '{stage}' artefact is not approved: {raw_path}")

    root_agent_docs = workspace_root / "agent-docs"
    if root_agent_docs.exists():
        warnings.append("legacy root agent-docs/ folder exists; canonical path is .github/agent-docs/")
        suggestions.append("Move inter-agent artefacts to .github/agent-docs/ or keep fallback scanning enabled.")

    discovery = discover_artefacts(workspace_root, state.feature)
    if discovery["recommended_entry_stage"] in {"preflight", "implement"}:
        plan = discovery["artifacts"]["plan"]["primary"]
        if plan:
            suggestions.append(f"Existing plan detected: run junai pipeline fast-track --from-plan {plan}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "current_stage": state.current_stage,
        "pipeline_mode": state.pipeline_mode,
        "discovery": discovery,
    }


def _history_payload(state: PipelineState) -> dict[str, Any]:
    notes = state.notes.model_dump(mode="json", by_alias=True) if state.notes else {}
    return {
        "ok": True,
        "routing_history": notes.get("_routing_history") or [],
        "stage_log": notes.get("_stage_log") or [],
        "stage_history": notes.get("_stage_history") or [],
    }


def _last_handoff_payload(state: PipelineState) -> dict[str, Any]:
    notes = state.notes.model_dump(mode="json", by_alias=True) if state.notes else {}
    return {
        "ok": True,
        "current_stage": state.current_stage,
        "routing_decision": notes.get("_routing_decision"),
        "handoff_payload": notes.get("handoff_payload"),
    }


def resume_payload(state: PipelineState | None, workspace_root: Path, state_file: Path) -> dict[str, Any]:
    doctor = doctor_payload(state, workspace_root, state_file)
    if state is None:
        return {"ok": False, "doctor": doctor, "next_action": "initialize pipeline"}
    notes = state.notes.model_dump(mode="json", by_alias=True) if state.notes else {}
    routing = notes.get("_routing_decision")
    handoff = notes.get("handoff_payload")
    if not doctor.get("ok"):
        next_action = "fix doctor errors before routing"
        command = "junai pipeline doctor"
    elif state.blocked_by:
        next_action = "resolve blocked state"
        command = "junai pipeline doctor"
    elif isinstance(routing, dict) and routing.get("next_stage"):
        next_action = f"act as {routing.get('target_agent') or routing.get('next_stage')}"
        command = "junai pipeline last-handoff"
    else:
        next_action = "compute next transition"
        command = "junai pipeline next"
    return {
        "ok": doctor.get("ok", False),
        "current_stage": state.current_stage,
        "pipeline_mode": state.pipeline_mode,
        "next_action": next_action,
        "recommended_command": command,
        "routing_decision": routing,
        "handoff_payload": handoff,
        "doctor": doctor,
    }


def run_plan(
    state: PipelineState,
    workspace_root: Path,
    plan_path: Path,
    *,
    mode: str,
    entry_stage: str,
) -> dict[str, Any]:
    discovery = discover_artefacts(workspace_root, state.feature)
    quality = score_plan_quality(workspace_root, plan_path)
    if not quality.get("ok"):
        return quality
    if quality.get("readiness") == "not_ready":
        return {
            "ok": False,
            "error": "plan quality score is too low for run-plan",
            "quality": quality,
            "discovery": discovery,
        }
    fast_track = fast_track_from_plan(state, workspace_root, plan_path, entry_stage, mode=mode)
    if not fast_track.get("ok"):
        return {"ok": False, "error": fast_track.get("error"), "quality": quality, "discovery": discovery}
    return {
        "ok": True,
        "mode": mode,
        "entry_stage": entry_stage,
        "quality": quality,
        "discovery": discovery,
        "fast_track": fast_track,
        "next_command": "junai pipeline last-handoff",
    }


def write_dashboard(state: PipelineState, workspace_root: Path, output_path: Path) -> dict[str, Any]:
    doctor = doctor_payload(state, workspace_root, workspace_root / ".github" / "pipeline-state.json")
    notes = state.notes.model_dump(mode="json", by_alias=True) if state.notes else {}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Pipeline Dashboard",
        "",
        f"- Project: `{state.project}`",
        f"- Feature: `{state.feature}`",
        f"- Stage: `{state.current_stage}`",
        f"- Mode: `{state.pipeline_mode}`",
        f"- Blocked: `{state.blocked_by or 'no'}`",
        f"- Progress: { _format_progress_line(state) }",
        "",
        "## Gates",
        "",
    ]
    for gate, value in state.supervision_gates.model_dump().items():
        lines.append(f"- `{gate}`: `{value}`")
    lines.extend(["", "## Doctor", ""])
    lines.append(f"- OK: `{doctor.get('ok')}`")
    for issue in doctor.get("errors", []):
        lines.append(f"- Error: {issue}")
    for warning in doctor.get("warnings", []):
        lines.append(f"- Warning: {warning}")
    lines.extend(["", "## Last Handoff", "", "```json"])
    lines.append(json.dumps(notes.get("_routing_decision"), indent=2, ensure_ascii=False))
    lines.extend(["```", "", "## Artefacts", ""])
    for stage, record in state.stages.items():
        if isinstance(record, dict) and record.get("artefact"):
            lines.append(f"- `{stage}`: `{record.get('artefact')}`")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "dashboard": _as_workspace_relative(workspace_root, output_path)}


def write_evidence_bundle(
    state: PipelineState,
    workspace_root: Path,
    *,
    stage: str,
    phase: int | None,
    status: str,
    files: list[str],
    tests: list[str],
    commands: list[str],
    risks: list[str],
) -> dict[str, Any]:
    evidence_dir = workspace_root / ".github" / "agent-docs" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    phase_suffix = f"-phase-{phase}" if phase is not None else ""
    path = evidence_dir / f"{state.feature}-{stage}{phase_suffix}.json"
    payload = {
        "feature": state.feature,
        "stage": stage,
        "phase": phase,
        "status": status,
        "created_at": _now_utc().isoformat(),
        "files": files,
        "tests": tests,
        "commands": commands,
        "risks": risks,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _append_note_list(
        state,
        "_evidence_bundles",
        {"stage": stage, "phase": phase, "status": status, "path": _as_workspace_relative(workspace_root, path)},
    )
    return {"ok": True, "evidence": _as_workspace_relative(workspace_root, path), "payload": payload}


# ── Ordered stage sequence for progress display ──────────────────────────
# _CORE_STAGES: always shown in the progress bar.
# _STAGE_ORDER: full ordered sequence (core + optional) used for skip resolution.
# Optional stages appear in the progress bar only when active (in state.stages).

_CORE_STAGES = [
    "intent", "prd", "architect", "security", "plan",
    "ux_research", "ui_design", "implement", "anchor",
    "tester", "review", "closed",
]

_STAGE_ORDER = [
    "intent", "prd", "architect", "sql_design", "security", "plan",
    "data_engineer", "ux_research", "ui_design", "implement", "anchor",
    "tester", "accessibility", "review", "knowledge_transfer", "devops", "janitor", "closed",
]


def _format_progress_line(state: PipelineState) -> str:
    """Build a visual progress line like: intent ✅ → prd ✅ → [architect] → plan → ...

    Optional stages (sql_design, accessibility, data_engineer, devops, janitor,
    knowledge_transfer) are inserted at their natural position only if they are
    active (in_progress, complete, or skipped) in the current run.
    """
    active_optional = {
        s for s, data in state.stages.items()
        if s not in _CORE_STAGES
        and isinstance(data, dict)
        and data.get("status") in ("in_progress", "complete", "skipped")
    }
    display_stages = [s for s in _STAGE_ORDER if s in _CORE_STAGES or s in active_optional]

    parts: list[str] = []
    for stage in display_stages:
        stage_data = state.stages.get(stage, {})
        status = stage_data.get("status", "not_started") if isinstance(stage_data, dict) else "not_started"
        skipped = status == "skipped"

        if stage == state.current_stage:
            parts.append(f"[{stage}]")
        elif status == "complete":
            parts.append(f"{stage} ✅")
        elif skipped:
            parts.append(f"{stage} ⏭️")
        elif state.blocked_by and stage == state.current_stage:
            parts.append(f"{stage} 🛑")
        else:
            parts.append(stage)
    return "📍 " + " → ".join(parts)


# ── Stage skip logic ─────────────────────────────────────────────────────

# Gates that each stage would satisfy on normal completion.
_STAGE_GATES: dict[str, list[str]] = {
    "intent": ["intent_approved"],
    "architect": ["adr_approved"],
    "plan": ["plan_approved"],
    "review": ["review_approved"],
}

# Stages that must not be skipped (unskippable for pipeline integrity).
_UNSKIPPABLE_STAGES = {"implement", "anchor", "tester", "closed", "BLOCKED"}


def skip_stage(
    state: PipelineState,
    stage_to_skip: str,
    reason: str,
) -> dict[str, Any]:
    """Skip a pipeline stage.  Validates the stage, marks it as skipped,
    auto-satisfies its gates, and advances current_stage to the next
    stage using the default transition path.

    Returns a dict with the result (ok/error + new state info).
    """
    # Validate stage exists
    if stage_to_skip not in STAGE_TO_AGENT:
        return {"ok": False, "error": f"Unknown stage: '{stage_to_skip}'"}

    # Validate it can be skipped
    if stage_to_skip in _UNSKIPPABLE_STAGES:
        return {"ok": False, "error": f"Stage '{stage_to_skip}' cannot be skipped"}

    # Validate it's the current stage or the next expected stage
    if stage_to_skip != state.current_stage:
        return {
            "ok": False,
            "error": (
                f"Can only skip the current stage ('{state.current_stage}'). "
                f"'{stage_to_skip}' is not current."
            ),
        }

    # Validate it's not already complete
    stage_data = state.stages.get(stage_to_skip, {})
    if isinstance(stage_data, dict) and stage_data.get("status") == "complete":
        return {"ok": False, "error": f"Stage '{stage_to_skip}' is already complete"}

    # Mark as skipped
    skipped_data = state.stages.setdefault(stage_to_skip, {})
    skipped_data["status"] = "skipped"
    skipped_data["skipped_at"] = _now_utc().isoformat()
    skipped_data["skipped_reason"] = reason

    # Auto-satisfy any gates this stage would have satisfied
    gates_satisfied: list[str] = []
    for gate in _STAGE_GATES.get(stage_to_skip, []):
        if gate in ALLOWED_SUPERVISION_GATES:
            setattr(state.supervision_gates, gate, True)
            gates_satisfied.append(gate)

    # Advance to next stage using the default ordering.
    _find_next = _find_next_stage_for_skip(state, stage_to_skip)
    if _find_next is None:
        return {
            "ok": False,
            "error": f"Cannot determine next stage after skipping '{stage_to_skip}'",
        }

    state.current_stage = _find_next
    next_stage_data = state.stages.setdefault(_find_next, {})
    if next_stage_data.get("status") in (None, "not_started"):
        next_stage_data["status"] = "in_progress"
    state.blocked_by = None

    return {
        "ok": True,
        "skipped_stage": stage_to_skip,
        "reason": reason,
        "gates_auto_satisfied": gates_satisfied,
        "new_current_stage": state.current_stage,
        "new_target_agent": STAGE_TO_AGENT.get(state.current_stage, "Orchestrator"),
        "progress_line": _format_progress_line(state),
    }


# Optional stages that only activate when a specific feature flag is set.
# _find_next_stage_for_skip skips these when their flag is absent so that a
# plain skip chain mirrors the guard-evaluated path (avoids landing on
# sql_design when sql_design_enabled is not set, for example).
_OPTIONAL_STAGE_FLAGS: dict[str, str] = {
    "sql_design": "sql_design_enabled",
    "data_engineer": "data_track_enabled",
    "accessibility": "a11y_audit_enabled",
    "devops": "deploy_enabled",
    "janitor": "cleanup_enabled",
}


def _find_next_stage_for_skip(state: PipelineState, skipped_stage: str) -> str | None:
    """Determine the next stage after a skip by following the default stage order.

    Optional stages (sql_design, data_engineer, accessibility, devops, janitor)
    are skipped over when their enabling feature flag is not present in state,
    so the skip chain stays on the same conditional path as real routing.
    """
    try:
        idx = _STAGE_ORDER.index(skipped_stage)
    except ValueError:
        return None
    # Walk forward to find the next eligible stage
    for next_stage in _STAGE_ORDER[idx + 1:]:
        stage_data = state.stages.get(next_stage, {})
        status = stage_data.get("status") if isinstance(stage_data, dict) else None
        if status in ("complete", "skipped"):
            continue
        # Skip optional stages whose enabling flag is absent from state extras
        flag = _OPTIONAL_STAGE_FLAGS.get(next_stage)
        if flag and not bool((state.model_extra or {}).get(flag)):
            continue
        return next_stage
    return None


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

    parser_skip = subparsers.add_parser("skip", help="Skip a pipeline stage")
    parser_skip.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_skip.add_argument("--stage", type=str, required=True)
    parser_skip.add_argument("--reason", type=str, required=True)

    parser_preflight = subparsers.add_parser("preflight", help="Run preflight checks")
    parser_preflight.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_preflight.add_argument("--target-stage", type=str, required=True)

    parser_discover = subparsers.add_parser("discover-artefacts", help="Discover existing PRD/ADR/plan artefacts")
    parser_discover.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_discover.add_argument("--feature", type=str, default=None)
    parser_discover.add_argument("--write-registry", action="store_true")

    parser_fast_track = subparsers.add_parser("fast-track", help="Align pipeline state from an approved plan")
    parser_fast_track.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_fast_track.add_argument("--from-plan", type=Path, required=True)
    parser_fast_track.add_argument("--entry", choices=["preflight", "implement"], default="preflight")
    parser_fast_track.add_argument("--mode", choices=sorted(ALLOWED_PIPELINE_MODES), default=None)
    parser_fast_track.add_argument("--project", type=str, default=None)
    parser_fast_track.add_argument("--feature", type=str, default=None)

    parser_doctor = subparsers.add_parser("doctor", help="Diagnose pipeline state and artefact issues")
    parser_doctor.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)

    parser_history = subparsers.add_parser("history", help="Print routing and stage history")
    parser_history.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)

    parser_last_handoff = subparsers.add_parser("last-handoff", help="Print the latest routing decision and handoff payload")
    parser_last_handoff.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)

    parser_resume = subparsers.add_parser("resume", help="Print the safest next action for a paused pipeline")
    parser_resume.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)

    parser_run_plan = subparsers.add_parser("run-plan", help="Score, align, and route from an approved plan")
    parser_run_plan.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_run_plan.add_argument("--from-plan", type=Path, required=True)
    parser_run_plan.add_argument("--entry", choices=["preflight", "implement"], default="preflight")
    parser_run_plan.add_argument("--mode", choices=sorted(ALLOWED_PIPELINE_MODES), default="autopilot")
    parser_run_plan.add_argument("--project", type=str, default=None)
    parser_run_plan.add_argument("--feature", type=str, default=None)

    parser_parse_plan = subparsers.add_parser("parse-plan", help="Parse numbered phases from a plan")
    parser_parse_plan.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_parse_plan.add_argument("--plan", type=Path, required=True)

    parser_dashboard = subparsers.add_parser("dashboard", help="Write a markdown pipeline dashboard report")
    parser_dashboard.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_dashboard.add_argument(
        "--output",
        type=Path,
        default=Path(".github/agent-docs/pipeline-dashboard.md"),
    )

    parser_halt_info = subparsers.add_parser("halt-info", help="Classify a halt reason and print recovery commands")
    parser_halt_info.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_halt_info.add_argument("--reason", type=str, default=None)

    parser_plan_score = subparsers.add_parser("plan-score", help="Score plan readiness for automated execution")
    parser_plan_score.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_plan_score.add_argument("--plan", type=Path, required=True)

    parser_context_guard = subparsers.add_parser("context-guard", help="Estimate phase context risk from static plan size")
    parser_context_guard.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_context_guard.add_argument("--plan", type=Path, required=True)
    parser_context_guard.add_argument("--phase", type=int, default=None)

    parser_model_route = subparsers.add_parser("model-route", help="Recommend a model for a stage or plan phase")
    parser_model_route.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_model_route.add_argument("--stage", type=str, required=True)
    parser_model_route.add_argument("--plan", type=Path, default=None)
    parser_model_route.add_argument("--phase", type=int, default=None)

    parser_evidence = subparsers.add_parser("evidence", help="Write an execution evidence bundle")
    parser_evidence.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser_evidence.add_argument("--stage", type=str, required=True)
    parser_evidence.add_argument("--phase", type=int, default=None)
    parser_evidence.add_argument("--status", type=str, required=True)
    parser_evidence.add_argument("--file", dest="files", action="append", default=[])
    parser_evidence.add_argument("--test", dest="tests", action="append", default=[])
    parser_evidence.add_argument("--command", dest="commands", action="append", default=[])
    parser_evidence.add_argument("--risk", dest="risks", action="append", default=[])

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

    if args.command == "discover-artefacts":
        feature = args.feature
        if feature is None:
            if not state_file.exists():
                _print_json_error("state file is missing and --feature was not provided")
            feature = _load_state(state_file).feature
        discovery = discover_artefacts(workspace_root, feature)
        if args.write_registry:
            registry_path = _write_artifacts_registry(workspace_root, discovery)
            discovery["artifacts_registry"] = _as_workspace_relative(workspace_root, registry_path)
        print(json.dumps(discovery, ensure_ascii=False))
        return

    if args.command == "fast-track":
        state = _load_or_initialize_state_for_fast_track(
            state_file,
            workspace_root,
            project=args.project,
            feature=args.feature,
        )
        plan_path = args.from_plan if args.from_plan.is_absolute() else workspace_root / args.from_plan
        result = fast_track_from_plan(
            state,
            workspace_root,
            plan_path,
            args.entry,
            mode=args.mode,
        )
        if result.get("ok"):
            _save_state(state_file, state)
        print(json.dumps(result, ensure_ascii=False))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "run-plan":
        state = _load_or_initialize_state_for_fast_track(
            state_file,
            workspace_root,
            project=args.project,
            feature=args.feature,
        )
        plan_path = args.from_plan if args.from_plan.is_absolute() else workspace_root / args.from_plan
        result = run_plan(
            state,
            workspace_root,
            plan_path,
            mode=args.mode,
            entry_stage=args.entry,
        )
        if result.get("ok"):
            _save_state(state_file, state)
        print(json.dumps(result, ensure_ascii=False))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "doctor":
        state = _load_state(state_file) if state_file.exists() else None
        result = doctor_payload(state, workspace_root, state_file)
        print(json.dumps(result, ensure_ascii=False))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "resume":
        state = _load_state(state_file) if state_file.exists() else None
        result = resume_payload(state, workspace_root, state_file)
        print(json.dumps(result, ensure_ascii=False))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "parse-plan":
        plan_path = args.plan if args.plan.is_absolute() else workspace_root / args.plan
        result = parse_plan_phases(workspace_root, plan_path)
        print(json.dumps(result, ensure_ascii=False))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "plan-score":
        plan_path = args.plan if args.plan.is_absolute() else workspace_root / args.plan
        result = score_plan_quality(workspace_root, plan_path)
        print(json.dumps(result, ensure_ascii=False))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "context-guard":
        plan_path = args.plan if args.plan.is_absolute() else workspace_root / args.plan
        result = context_guard_for_phase(workspace_root, plan_path, args.phase)
        print(json.dumps(result, ensure_ascii=False))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "model-route":
        phase = None
        if args.plan:
            plan_path = args.plan if args.plan.is_absolute() else workspace_root / args.plan
            parsed = parse_plan_phases(workspace_root, plan_path)
            if not parsed.get("ok"):
                print(json.dumps(parsed, ensure_ascii=False))
                raise SystemExit(1)
            phase = _phase_by_number(parsed, args.phase)
            if args.phase is not None and phase is None:
                print(json.dumps({"ok": False, "error": f"phase not found: {args.phase}"}, ensure_ascii=False))
                raise SystemExit(1)
        print(json.dumps(recommend_model_for_work(args.stage, phase), ensure_ascii=False))
        return

    if args.command == "halt-info":
        state = _load_state(state_file) if state_file.exists() else None
        reason = args.reason or (state.blocked_by if state else None)
        issue_type = classify_halt_reason(reason)
        result = {
            "ok": True,
            "reason": reason,
            "issue_type": issue_type,
            "recovery_commands": recovery_commands_for_issue(issue_type, state),
        }
        print(json.dumps(result, ensure_ascii=False))
        return

    state = _load_state(state_file)

    if args.command == "status":
        print(json.dumps(_status_payload(state), ensure_ascii=False))
        return

    if args.command == "history":
        print(json.dumps(_history_payload(state), ensure_ascii=False))
        return

    if args.command == "last-handoff":
        print(json.dumps(_last_handoff_payload(state), ensure_ascii=False))
        return

    if args.command == "dashboard":
        output_path = args.output if args.output.is_absolute() else workspace_root / args.output
        print(json.dumps(write_dashboard(state, workspace_root, output_path), ensure_ascii=False))
        return

    if args.command == "evidence":
        result = write_evidence_bundle(
            state,
            workspace_root,
            stage=args.stage,
            phase=args.phase,
            status=args.status,
            files=args.files,
            tests=args.tests,
            commands=args.commands,
            risks=args.risks,
        )
        _save_state(state_file, state)
        print(json.dumps(result, ensure_ascii=False))
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
                "ok": True,
                "no_op": True,
                "reason": "idempotency",
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

    if args.command == "skip":
        result = skip_stage(state, args.stage, args.reason)
        if result["ok"]:
            _save_state(state_file, state)
        print(json.dumps(result, ensure_ascii=False))
        if not result["ok"]:
            raise SystemExit(1)
        return


if __name__ == "__main__":
    main()
