from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNNER_PATH = REPO_ROOT / ".github" / "tools" / "pipeline-runner" / "pipeline_runner.py"
TEMPLATE_PATH = REPO_ROOT / ".github" / "pipeline-state.template.json"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER_PATH), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_state(state_file: Path, *, feature: str = "alpha-plan") -> None:
    payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    payload["project"] = "claudster-source"
    payload["feature"] = feature
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_approved_plan(workspace: Path, feature: str = "alpha-plan") -> Path:
    plan = workspace / ".github" / "plans" / f"{feature}.md"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(
        "---\n"
        "type: plan\n"
        "status: current\n"
        "approval: approved\n"
        "---\n"
        "# Plan\n\n"
        "## Phase 1 - Foundation\n\n"
        "Agent: `implement`\n\n"
        "- Update `.github/tools/pipeline-runner/pipeline_runner.py`\n"
        "- Run pytest for pipeline runner\n\n"
        "## Phase 2 - Tests\n\n"
        "Agent: `tester`\n\n"
        "- Run regression tests\n"
        "- Verify evidence bundle\n\n"
        "## Source Document Traceability\n\n"
        "- Grounded in CI and pipeline docs\n\n"
        "## Scope Changes\n\n"
        "- None\n",
        encoding="utf-8",
    )
    return plan


def test_discover_artefacts_finds_approved_plan_and_writes_registry(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    _write_approved_plan(workspace)

    result = _run_cli(
        "discover-artefacts",
        "--state-file",
        str(state_file),
        "--write-registry",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["recommended_entry_stage"] == "preflight"
    assert payload["artifacts"]["plan"]["primary"] == ".github/plans/alpha-plan.md"
    registry_path = workspace / payload["artifacts_registry"]
    assert registry_path.exists()


def test_fast_track_from_plan_sets_preflight_handoff_and_autopilot(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    plan = _write_approved_plan(workspace)

    result = _run_cli(
        "fast-track",
        "--state-file",
        str(state_file),
        "--from-plan",
        str(plan),
        "--entry",
        "preflight",
        "--mode",
        "autopilot",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["entry_stage"] == "preflight"
    assert payload["pipeline_mode"] == "autopilot"
    assert payload["total_phases"] == 2

    state = _load_json(state_file)
    assert state["current_stage"] == "preflight"
    assert state["pipeline_mode"] == "autopilot"
    assert state["supervision_gates"]["intent_approved"] is True
    assert state["supervision_gates"]["adr_approved"] is True
    assert state["supervision_gates"]["plan_approved"] is True
    assert state["stages"]["plan"]["artefact"] == ".github/plans/alpha-plan.md"
    assert state["stages"]["implement"]["total_phases"] == 2
    assert state["_notes"]["_routing_decision"]["next_stage"] == "preflight"
    assert state["_notes"]["handoff_payload"]["upstream_artefact"] == ".github/plans/alpha-plan.md"


def test_fast_track_to_implement_requires_passed_preflight(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    plan = _write_approved_plan(workspace)

    result = _run_cli(
        "fast-track",
        "--state-file",
        str(state_file),
        "--from-plan",
        str(plan),
        "--entry",
        "implement",
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["recommended_entry_stage"] == "preflight"


def test_doctor_reports_legacy_agent_docs_warning(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    (workspace / "agent-docs").mkdir()

    result = _run_cli("doctor", "--state-file", str(state_file))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert any("legacy root agent-docs" in item for item in payload["warnings"])


def test_advance_duplicate_completion_is_clean_noop(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    state = _load_json(state_file)
    state["stages"]["intent"]["status"] = "complete"
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    result = _run_cli(
        "advance",
        "--state-file",
        str(state_file),
        "--completed-stage",
        "intent",
        "--result-status",
        "complete",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["no_op"] is True


def test_history_and_last_handoff_commands_return_json(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    plan = _write_approved_plan(workspace)
    fast_track = _run_cli(
        "fast-track",
        "--state-file",
        str(state_file),
        "--from-plan",
        str(plan),
    )
    assert fast_track.returncode == 0

    history = _run_cli("history", "--state-file", str(state_file))
    last_handoff = _run_cli("last-handoff", "--state-file", str(state_file))

    assert history.returncode == 0
    assert last_handoff.returncode == 0
    assert json.loads(history.stdout)["routing_history"]
    assert json.loads(last_handoff.stdout)["routing_decision"]["next_stage"] == "preflight"


def test_parse_plan_context_guard_plan_score_and_model_route(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    plan = _write_approved_plan(workspace)

    parsed = _run_cli("parse-plan", "--state-file", str(state_file), "--plan", str(plan))
    guard = _run_cli("context-guard", "--state-file", str(state_file), "--plan", str(plan), "--phase", "1")
    score = _run_cli("plan-score", "--state-file", str(state_file), "--plan", str(plan))
    route = _run_cli(
        "model-route",
        "--state-file",
        str(state_file),
        "--stage",
        "implement",
        "--plan",
        str(plan),
        "--phase",
        "1",
    )

    assert parsed.returncode == 0
    assert json.loads(parsed.stdout)["phase_count"] == 2
    assert guard.returncode == 0
    assert json.loads(guard.stdout)["status"] == "green"
    assert "static estimate" in json.loads(guard.stdout)["explanation"]
    assert score.returncode == 0
    assert json.loads(score.stdout)["readiness"] == "ready"
    assert route.returncode == 0
    assert json.loads(route.stdout)["recommended_model"] == "gpt-5.3-codex"


def test_run_plan_resume_dashboard_halt_info_and_evidence(tmp_path: Path) -> None:
    workspace = tmp_path
    state_file = workspace / ".github" / "pipeline-state.json"
    _seed_state(state_file)
    plan = _write_approved_plan(workspace)

    run_plan = _run_cli(
        "run-plan",
        "--state-file",
        str(state_file),
        "--from-plan",
        str(plan),
        "--entry",
        "preflight",
        "--mode",
        "autopilot",
    )
    assert run_plan.returncode == 0
    run_payload = json.loads(run_plan.stdout)
    assert run_payload["ok"] is True
    assert run_payload["quality"]["readiness"] == "ready"

    resume = _run_cli("resume", "--state-file", str(state_file))
    assert resume.returncode == 0
    assert json.loads(resume.stdout)["recommended_command"] == "junai pipeline last-handoff"

    dashboard = _run_cli("dashboard", "--state-file", str(state_file))
    assert dashboard.returncode == 0
    dashboard_path = workspace / json.loads(dashboard.stdout)["dashboard"]
    assert dashboard_path.exists()
    assert "# Pipeline Dashboard" in dashboard_path.read_text(encoding="utf-8")

    halt = _run_cli("halt-info", "--state-file", str(state_file), "--reason", "preflight failed on plan")
    assert halt.returncode == 0
    assert json.loads(halt.stdout)["issue_type"] == "preflight_failed"

    evidence = _run_cli(
        "evidence",
        "--state-file",
        str(state_file),
        "--stage",
        "implement",
        "--phase",
        "1",
        "--status",
        "passed",
        "--file",
        ".github/tools/pipeline-runner/pipeline_runner.py",
        "--test",
        "pytest .github/tools/pipeline-runner/tests",
        "--command",
        "junai pipeline plan-score --plan .github/plans/alpha-plan.md",
        "--risk",
        "none",
    )
    assert evidence.returncode == 0
    evidence_payload = json.loads(evidence.stdout)
    evidence_path = workspace / evidence_payload["evidence"]
    assert evidence_path.exists()
    state = _load_json(state_file)
    assert state["_notes"]["_evidence_bundles"][0]["path"] == evidence_payload["evidence"]
