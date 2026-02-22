from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

PIPELINE_RUNNER_DIR = Path(__file__).resolve().parents[1]
if str(PIPELINE_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_RUNNER_DIR))

from schema import PipelineState, parse_pipeline_state


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def make_state(workspace_root: Path):
    def _factory(
        current_stage: str,
        *,
        pipeline_type: str | None = None,
        pipeline_mode: str = "supervised",
        stage_overrides: dict[str, dict[str, Any]] | None = None,
        supervision_overrides: dict[str, bool] | None = None,
        deferred: list[dict[str, Any]] | None = None,
        blocked_by: str | None = None,
        notes: dict[str, Any] | None = None,
    ) -> PipelineState:
        stage_overrides = stage_overrides or {}
        supervision_overrides = supervision_overrides or {}

        base = {
            "project": "agent-sandbox",
            "feature": "deterministic-routing",
            "pipeline_version": "1.0",
            "pipeline_mode": pipeline_mode,
            "type": pipeline_type,
            "current_stage": current_stage,
            "stages": {
                "intent": {"status": "not_started", "artefact": None, "completed_at": None},
                "prd": {"status": "not_started", "artefact": None, "completed_at": None},
                "architect": {"status": "not_started", "artefact": None, "completed_at": None},
                "security": {"status": "not_started", "artefact": None, "completed_at": None},
                "plan": {"status": "not_started", "artefact": None, "completed_at": None},
                "ux_research": {"status": "not_started", "artefact": None, "completed_at": None},
                "ui_design": {"status": "not_started", "artefact": None, "completed_at": None},
                "implement": {
                    "status": "not_started",
                    "artefact": None,
                    "completed_at": None,
                    "current_phase": 0,
                    "total_phases": 1,
                    "retry_count": 0,
                    "max_retries": 3,
                },
                "tester": {
                    "status": "not_started",
                    "artefact": None,
                    "completed_at": None,
                    "retry_count": 0,
                    "max_retries": 3,
                },
                "review": {
                    "status": "not_started",
                    "artefact": None,
                    "completed_at": None,
                    "retry_count": 0,
                    "max_retries": 3,
                },
                "debug": {"status": "not_started", "artefact": None, "completed_at": None},
                "closed": {"status": "not_started", "artefact": None, "completed_at": None},
            },
            "supervision_gates": {
                "intent_approved": False,
                "adr_approved": False,
                "plan_approved": False,
                "review_approved": False,
                **supervision_overrides,
            },
            "deferred": deferred or [],
            "blocked_by": blocked_by,
            "last_updated": None,
            "_notes": notes or {"handoff_payload": None, "_routing_decision": None, "_hotfix_brief": None},
        }

        for stage_name, values in stage_overrides.items():
            base["stages"].setdefault(stage_name, {}).update(values)

        return parse_pipeline_state(base)

    return _factory
