from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

from schema import CompletionEvent, PipelineState


GuardFunction = Callable[[PipelineState, CompletionEvent, Path], tuple[bool, str | None]]

_SECURITY_SEVERITIES = {"security-nit", "security", "critical", "high"}


def _stage_record(state: PipelineState, stage_name: str) -> dict:
    stage = state.stages.get(stage_name)
    if isinstance(stage, dict):
        return stage
    return {}


def _resolve_workspace_path(workspace_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return workspace_root / candidate


def _iter_artefact_paths(value: str | None) -> list[str]:
    if value is None:
        return []
    if "," in value:
        return [part.strip() for part in value.split(",") if part.strip()]
    stripped = value.strip()
    return [stripped] if stripped else []


def _read_frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}

    end_index = content.find("\n---", 3)
    if end_index == -1:
        return {}

    frontmatter_raw = content[3:end_index].strip()
    if not frontmatter_raw:
        return {}

    parsed = yaml.safe_load(frontmatter_raw)
    if isinstance(parsed, dict):
        return parsed
    return {}


def artefact_exists(
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    record = _stage_record(state, event.stage_completed)
    artefact_path = event.artefact_path or record.get("artefact")
    paths = _iter_artefact_paths(artefact_path)
    if not paths:
        return False, f"No artefact path found for stage '{event.stage_completed}'"

    for path_str in paths:
        if _resolve_workspace_path(workspace_root, path_str).exists():
            return True, None

    return False, f"No artefact file exists for stage '{event.stage_completed}'"


def artefact_approved(
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    record = _stage_record(state, event.stage_completed)
    artefact_path = event.artefact_path or record.get("artefact")
    paths = _iter_artefact_paths(artefact_path)
    if not paths:
        return False, f"No artefact available to validate approval for '{event.stage_completed}'"

    for path_str in paths:
        path = _resolve_workspace_path(workspace_root, path_str)
        if not path.exists() or not path.is_file():
            continue
        try:
            frontmatter = _read_frontmatter(path)
        except (OSError, yaml.YAMLError) as exc:
            return False, f"Failed parsing frontmatter in {path}: {exc}"
        if str(frontmatter.get("approval", "")).strip().lower() == "approved":
            return True, None

    return False, "Artefact approval is not 'approved'"


def all_phases_done(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    implement = _stage_record(state, "implement")
    current_phase = int(implement.get("current_phase", 0))
    total_phases = int(implement.get("total_phases", 1))
    if current_phase >= total_phases:
        return True, None
    return False, f"Implementation phases not complete ({current_phase}/{total_phases})"


def more_phases_remain(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    implement = _stage_record(state, "implement")
    current_phase = int(implement.get("current_phase", 0))
    total_phases = int(implement.get("total_phases", 1))
    if current_phase < total_phases:
        return True, None
    return False, "No remaining implementation phases"


def retry_budget_remaining(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    tester = _stage_record(state, "tester")
    retry_count = int(tester.get("retry_count", 0))
    max_retries = int(tester.get("max_retries", 3))
    if retry_count < max_retries:
        return True, None
    return False, "Tester retry budget exhausted"


def retry_budget_exhausted(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    tester = _stage_record(state, "tester")
    retry_count = int(tester.get("retry_count", 0))
    max_retries = int(tester.get("max_retries", 3))
    if retry_count >= max_retries:
        return True, None
    return False, "Tester retry budget remains"


def has_security_deferrals(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    has_security = any(
        str(item.severity).strip().lower() in _SECURITY_SEVERITIES for item in state.deferred
    )
    if has_security:
        return True, None
    return False, "No security deferrals found"


def no_security_deferrals(
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    result, _ = has_security_deferrals(state, event, workspace_root)
    if result:
        return False, "Security deferrals still present"
    return True, None


def no_security_deferrals_pending(
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    return no_security_deferrals(state, event, workspace_root)


def has_deferred_items(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    if state.deferred:
        return True, None
    return False, "No deferred items available for re-entry"


def coverage_requirements_present(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    payload = state.notes.handoff_payload if state.notes else None
    if payload is None:
        return False, "handoff_payload is missing"

    if payload.upstream_artefact and not payload.coverage_requirements:
        return False, "coverage_requirements is required when upstream_artefact is set"

    for item in payload.coverage_requirements:
        if not isinstance(item, str) or not item.strip():
            return False, "coverage_requirements entries must be non-empty strings"

    return True, None


def no_blocking_escalations(
    _state: PipelineState,
    _event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    escalations_dir = workspace_root / "agent-docs" / "escalations"
    if not escalations_dir.exists():
        return True, None

    for path in escalations_dir.rglob("*.md"):
        try:
            frontmatter = _read_frontmatter(path)
        except (OSError, yaml.YAMLError):
            continue
        if str(frontmatter.get("severity", "")).strip().lower() == "blocking":
            return False, f"Blocking escalation present: {path.relative_to(workspace_root).as_posix()}"

    return True, None


def parallel_security_enabled(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    notes = state.notes.model_dump(by_alias=True) if state.notes else {}
    parallel = notes.get("parallel_groups") or {}
    enabled = bool(parallel)
    if enabled:
        return True, None
    return False, "Parallel security branch not enabled"


def parallel_not_enabled(
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    result, _ = parallel_security_enabled(state, event, workspace_root)
    if result:
        return False, "Parallel security branch requires dedicated join handling"
    return True, None


def parallel_security_join_ready(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    architect = _stage_record(state, "architect")
    if str(architect.get("status", "")) == "complete":
        return True, None
    return False, "Architect stage must be complete before joining to plan"


def ui_track_enabled(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    notes = state.notes.model_dump(by_alias=True) if state.notes else {}
    ui_track = notes.get("ui_track")
    if bool(ui_track):
        return True, None
    return False, "UI track not enabled"


def ui_track_not_enabled(
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    result, _ = ui_track_enabled(state, event, workspace_root)
    if result:
        return False, "UI track enabled; plan should route through ux_research"
    return True, None


def review_retry_budget_remaining(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    review = _stage_record(state, "review")
    retry_count = int(review.get("retry_count", 0))
    max_retries = int(review.get("max_retries", 3))
    if retry_count < max_retries:
        return True, None
    return False, "Review retry budget exhausted"


def review_retry_budget_exhausted(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    review = _stage_record(state, "review")
    retry_count = int(review.get("retry_count", 0))
    max_retries = int(review.get("max_retries", 3))
    if retry_count >= max_retries:
        return True, None
    return False, "Review retry budget remains"


def pipeline_mode_autopilot(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    if (state.pipeline_mode or "").strip().lower() == "autopilot":
        return True, None
    return False, "pipeline_mode is not autopilot"


def pipeline_mode_assisted(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    if (state.pipeline_mode or "").strip().lower() == "assisted":
        return True, None
    return False, "pipeline_mode is not assisted"


def pipeline_mode_supervised(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    if state.pipeline_mode == "supervised":
        return True, None
    return False, "pipeline_mode is not supervised"


def blocked_cleared(
    state: PipelineState,
    _event: CompletionEvent,
    _workspace_root: Path,
) -> tuple[bool, str | None]:
    if state.blocked_by:
        return False, "blocked_by is still set"
    return True, None


GUARD_REGISTRY: dict[str, GuardFunction] = {
    "artefact_exists": artefact_exists,
    "artefact_approved": artefact_approved,
    "all_phases_done": all_phases_done,
    "more_phases_remain": more_phases_remain,
    "retry_budget_remaining": retry_budget_remaining,
    "retry_budget_exhausted": retry_budget_exhausted,
    "review_retry_budget_remaining": review_retry_budget_remaining,
    "review_retry_budget_exhausted": review_retry_budget_exhausted,
    "has_security_deferrals": has_security_deferrals,
    "no_security_deferrals": no_security_deferrals,
    "no_security_deferrals_pending": no_security_deferrals_pending,
    "has_deferred_items": has_deferred_items,
    "coverage_requirements_present": coverage_requirements_present,
    "no_blocking_escalations": no_blocking_escalations,
    "parallel_security_enabled": parallel_security_enabled,
    "parallel_not_enabled": parallel_not_enabled,
    "parallel_security_join_ready": parallel_security_join_ready,
    "ui_track_enabled": ui_track_enabled,
    "ui_track_not_enabled": ui_track_not_enabled,
    "pipeline_mode_supervised": pipeline_mode_supervised,
    "pipeline_mode_assisted": pipeline_mode_assisted,
    "pipeline_mode_autopilot": pipeline_mode_autopilot,
    "blocked_cleared": blocked_cleared,
}


def evaluate_guard(
    guard_name: str,
    state: PipelineState,
    event: CompletionEvent,
    workspace_root: Path,
) -> tuple[bool, str | None]:
    guard = GUARD_REGISTRY.get(guard_name)
    if guard is None:
        return False, f"Unknown guard '{guard_name}'"
    return guard(state, event, workspace_root)
