from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent / "agents.registry.json"


@dataclass(frozen=True)
class Transition:
    id: str
    from_stage: str
    to_stage: str
    event: str
    guards: list[str]
    gate: str | None
    hotfix_only: bool = False
    priority: int = 0


def _load_transitions(registry_path: Path = _REGISTRY_PATH) -> list[Transition]:
    """Load all pipeline transitions from agents.registry.json.

    This is the single source of truth. To add a new pipeline-integrated agent,
    add entries to agents.registry.json — no Python changes required.
    """
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return [
        Transition(
            id=t["id"],
            from_stage=t["from_stage"],
            to_stage=t["to_stage"],
            event=t["event"],
            guards=t.get("guards", []),
            gate=t.get("gate"),
            hotfix_only=t.get("hotfix_only", False),
            priority=t.get("priority", 0),
        )
        for t in data["transitions"]
    ]


# Loaded at import time so all existing imports continue to work unchanged.
TRANSITIONS: list[Transition] = _load_transitions()

_LEGACY_INLINE_TRANSITIONS: list[Transition] = [
    Transition("T-01", "intent", "prd", "complete", ["artefact_exists"], "intent_approved"),
    Transition(
        "T-02",
        "prd",
        "architect",
        "complete",
        ["artefact_exists", "artefact_approved"],
        None,
    ),
    Transition(
        "T-03",
        "architect",
        "plan",
        "complete",
        ["artefact_exists", "artefact_approved", "parallel_not_enabled"],
        "adr_approved",
    ),
    Transition(
        "T-04",
        "plan",
        "implement",
        "complete",
        ["artefact_exists", "artefact_approved", "ui_track_not_enabled"],
        "plan_approved",
    ),
    Transition("T-05", "implement", "tester", "complete", ["all_phases_done"], None),
    Transition("T-06", "tester", "review", "passed", [], None),
    Transition(
        "T-07",
        "review",
        "closed",
        "approved",
        ["no_security_deferrals_pending"],
        "review_approved",
    ),
    Transition(
        "T-08",
        "architect",
        "security",
        "complete",
        ["artefact_exists", "artefact_approved", "parallel_security_enabled"],
        None,
        priority=10,
    ),
    Transition(
        "T-09",
        "security",
        "plan",
        "complete",
        ["artefact_exists", "artefact_approved", "parallel_security_join_ready"],
        "adr_approved",
    ),
    Transition(
        "T-10",
        "plan",
        "ux_research",
        "complete",
        ["artefact_exists", "artefact_approved", "ui_track_enabled"],
        None,
        priority=10,
    ),
    Transition("T-11", "ux_research", "ui_design", "complete", ["artefact_exists"], None),
    Transition(
        "T-12",
        "ui_design",
        "implement",
        "complete",
        ["artefact_exists", "artefact_approved"],
        "plan_approved",
    ),
    Transition(
        "T-13",
        "implement",
        "implement",
        "phase_complete",
        ["more_phases_remain"],
        None,
        priority=15,
    ),
    Transition(
        "T-14",
        "tester",
        "implement",
        "failed",
        ["retry_budget_remaining"],
        None,
        priority=10,
    ),
    Transition(
        "T-15",
        "tester",
        "BLOCKED",
        "failed",
        ["retry_budget_exhausted"],
        None,
        priority=5,
    ),
    Transition("T-16", "review", "implement", "revision-requested", [], None, priority=10),
    Transition("T-17", "intake", "debug", "hotfix_unknown", [], None, hotfix_only=True),
    Transition(
        "T-18",
        "intake",
        "implement",
        "hotfix_known",
        [],
        None,
        hotfix_only=True,
        priority=10,
    ),
    Transition(
        "T-19",
        "debug",
        "implement",
        "complete",
        ["artefact_exists"],
        None,
        hotfix_only=True,
    ),
    Transition("T-20", "implement", "tester", "complete", [], None, hotfix_only=True, priority=5),
    Transition(
        "T-21",
        "tester",
        "review",
        "passed",
        ["has_security_deferrals"],
        None,
        hotfix_only=True,
        priority=10,
    ),
    Transition(
        "T-22",
        "tester",
        "closed",
        "passed",
        ["no_security_deferrals"],
        None,
        hotfix_only=True,
        priority=5,
    ),
    Transition(
        "T-23",
        "closed",
        "implement",
        "deferred_reentry",
        ["has_deferred_items"],
        None,
    ),
    Transition("T-24", "*", "*", "*", ["pipeline_mode_auto"], None, priority=-10),
    Transition("T-25", "*", "*", "*", ["pipeline_mode_supervised"], None, priority=-10),
    Transition("T-26", "*", "BLOCKED", "*", ["no_blocking_escalations"], None, priority=-100),
    Transition("T-27", "BLOCKED", "*", "recovered", ["blocked_cleared"], None, priority=10),
]
# NOTE: _LEGACY_INLINE_TRANSITIONS is kept only as a reference/fallback.
# TRANSITIONS (above) is authoritative and loaded from agents.registry.json.
