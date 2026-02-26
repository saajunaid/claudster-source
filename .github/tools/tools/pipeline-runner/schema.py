from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


StageStatus = Literal["not_started", "in_progress", "complete", "blocked"]
PipelineMode = Literal["supervised", "assisted", "autopilot"]


class StageState(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: StageStatus = "not_started"
    artefact: str | None = None
    completed_at: datetime | None = None


class ImplementStageState(StageState):
    current_phase: int = 0
    total_phases: int = 1
    retry_count: int = 0
    max_retries: int = 3


class TesterStageState(StageState):
    retry_count: int = 0
    max_retries: int = 3


class ReviewStageState(StageState):
    retry_count: int = 0
    max_retries: int = 3


class SupervisionGates(BaseModel):
    model_config = ConfigDict(extra="allow")

    intent_approved: bool = False
    adr_approved: bool = False
    plan_approved: bool = False
    review_approved: bool = False


class DeferredItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    file: str
    detail: str
    severity: str


class HandoffPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    target_agent: str | None = None
    scope: str | None = None
    summary: str | None = None
    required_tests: list[str] = Field(default_factory=list)
    exit_criteria: str | None = None
    upstream_artefact: str | None = None
    coverage_requirements: list[str] = Field(default_factory=list)


class Notes(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        protected_namespaces=(),
        extra="allow",
    )

    handoff_payload: HandoffPayload | None = None
    routing_decision: dict[str, Any] | None = Field(
        default=None,
        alias="_routing_decision",
    )
    hotfix_brief: dict[str, Any] | None = Field(
        default=None,
        alias="_hotfix_brief",
    )


class PipelineState(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        protected_namespaces=(),
        extra="allow",
    )

    project: str
    feature: str
    pipeline_version: str = "1.0"
    pipeline_mode: str = "supervised"  # PipelineMode: supervised | assisted | autopilot
    type: str | None = None
    current_stage: str
    stages: dict[str, dict[str, Any]]
    supervision_gates: SupervisionGates = Field(default_factory=SupervisionGates)
    deferred: list[DeferredItem] = Field(default_factory=list)
    blocked_by: str | None = None
    last_updated: datetime | None = None
    notes: Notes | None = Field(default=None, alias="_notes")


class CompletionEvent(BaseModel):
    stage_completed: str
    result_status: str
    artefact_path: str | None = None
    result_payload: dict[str, Any] | None = None


class TransitionResult(BaseModel):
    transition_id: str | None = None
    next_stage: str | None = None
    target_agent: str | None = None
    gate_required: str | None = None
    gate_satisfied: bool = True
    blocked: bool = False
    blocked_reason: str | None = None
    pipeline_mode: str = "supervised"  # PipelineMode: supervised | assisted | autopilot
    handoff_prompt: str | None = None
    computed_at: datetime | None = None


def parse_pipeline_state(raw_state: dict[str, Any]) -> PipelineState:
    return PipelineState.model_validate(raw_state)


def to_state_dict(state: PipelineState) -> dict[str, Any]:
    return state.model_dump(mode="json", exclude_none=False, by_alias=True)


PipelineState.model_rebuild()
