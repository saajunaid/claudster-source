from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import FastMCP


def _detect_workspace_root() -> Path:
    """Find workspace root by searching upward from cwd for .github dir, or use env var."""
    if "JUNAI_WORKSPACE_ROOT" in os.environ:
        return Path(os.environ["JUNAI_WORKSPACE_ROOT"]).resolve()
    current = Path.cwd()
    for directory in [current, *current.parents]:
        if (directory / ".github").is_dir():
            return directory
    return current


WORKSPACE_ROOT = _detect_workspace_root()
DEFAULT_PIPELINE_STATE = WORKSPACE_ROOT / ".github" / "pipeline-state.json"
PIPELINE_STATE_PATH = Path(
    os.getenv("PIPELINE_STATE_PATH", str(DEFAULT_PIPELINE_STATE))
)
ALLOWED_PIPELINE_MODES = {"supervised", "assisted", "autopilot"}
ALLOWED_SUPERVISION_GATES = {
    "intent_approved",
    "adr_approved",
    "plan_approved",
    "review_approved",
}

# ── Direct import of pipeline-runner (eliminates subprocess + AV scan) ────────
_RUNNER_DIR = WORKSPACE_ROOT / ".github" / "tools" / "pipeline-runner"
_RUNNER_AVAILABLE = False
_pr: Any = None        # pipeline_runner module
_schema: Any = None    # schema module

if _RUNNER_DIR.exists() and str(_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNNER_DIR))
try:
    import pipeline_runner as _pr          # type: ignore[import]
    import schema as _schema               # type: ignore[import]
    _RUNNER_AVAILABLE = True
except Exception:  # noqa: BLE001
    pass  # Falls back to subprocess if import fails
# ─────────────────────────────────────────────────────────────────────────────


def _to_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_pipeline_state() -> dict[str, Any]:
    if not PIPELINE_STATE_PATH.exists():
        raise FileNotFoundError(
            f"Pipeline state not found at {PIPELINE_STATE_PATH}. "
            "Create .github/pipeline-state.json first."
        )
    return json.loads(PIPELINE_STATE_PATH.read_text(encoding="utf-8"))


def _save_pipeline_state(state: dict[str, Any]) -> None:
    state["last_updated"] = _to_iso_utc()
    PIPELINE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PIPELINE_STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


async def _run_pipeline_runner(
    completed_stage: str,
    result_status: str,
    artefact_path: str | None,
) -> dict[str, Any]:
    """Advance pipeline state. Uses direct in-process call when pipeline-runner
    is importable (no subprocess, no AV scan). Falls back to subprocess otherwise."""
    if _RUNNER_AVAILABLE:
        try:
            state = _pr._load_state(PIPELINE_STATE_PATH)
            event = _schema.CompletionEvent(
                stage_completed=completed_stage,
                result_status=result_status,
                artefact_path=artefact_path,
            )
            result = _pr.compute_next_transition(state, event, WORKSPACE_ROOT)
            state = _pr._advance_state(state, event, result)
            _pr._save_state(PIPELINE_STATE_PATH, state)
            return json.loads(result.model_dump_json(exclude_none=False))
        except Exception as exc:
            return {
                "blocked": True,
                "reason": f"pipeline-runner error: {exc}",
            }

    # ── Subprocess fallback (used only if import failed at startup) ───────────
    runner_path = WORKSPACE_ROOT / ".github" / "tools" / "pipeline-runner" / "pipeline_runner.py"
    if not runner_path.exists():
        return {
            "blocked": True,
            "reason": "pipeline-runner not found at .github/tools/pipeline-runner/pipeline_runner.py",
        }
    command = [
        sys.executable, str(runner_path), "advance",
        "--state-file", str(PIPELINE_STATE_PATH),
        "--completed-stage", completed_stage,
        "--result-status", result_status,
    ]
    if artefact_path:
        command.extend(["--artefact-path", artefact_path])
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(WORKSPACE_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {"blocked": True, "reason": "pipeline-runner subprocess timed out after 120s."}
    except Exception as exc:
        return {"blocked": True, "reason": f"failed to launch pipeline runner: {exc}"}
    if proc.returncode != 0:
        return {
            "blocked": True, "reason": "pipeline-runner advance failed",
            "stderr": stderr_bytes.decode("utf-8", errors="replace").strip(),
            "stdout": stdout_bytes.decode("utf-8", errors="replace").strip(),
        }
    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    if not stdout:
        return {"blocked": True, "reason": "pipeline-runner returned no output"}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"blocked": True, "reason": "pipeline-runner output is not valid JSON", "stdout": stdout}
    # ─────────────────────────────────────────────────────────────────────────


def _path_contains_hint(path: Path, hint: str) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if not hint.strip():
        return True
    lower_hint = hint.lower()
    content = path.read_text(encoding="utf-8", errors="ignore").lower()
    tokens = [token for token in lower_hint.replace("`", " ").split() if len(token) > 2]
    if not tokens:
        return True
    return any(token in content for token in tokens)


def _attempt_path_correction(file_value: str) -> Path | None:
    candidate = WORKSPACE_ROOT / file_value
    if candidate.exists():
        return candidate

    filename = Path(file_value).name
    if not filename:
        return None

    matches = list(WORKSPACE_ROOT.rglob(filename))
    if not matches:
        return None
    return matches[0]


mcp = FastMCP("junai-mcp")


def _get_progress_line(state: dict[str, Any]) -> str | None:
    """Generate a visual progress line from raw state dict.
    Uses pipeline-runner in-process if available, otherwise builds a simple one."""
    if _RUNNER_AVAILABLE:
        try:
            pstate = _pr._load_state(PIPELINE_STATE_PATH)
            return _pr._format_progress_line(pstate)
        except Exception:
            pass
    # Simple fallback
    current = state.get("current_stage", "?")
    return f"📍 Current stage: {current}"


@mcp.tool()
async def notify_orchestrator(
    stage_completed: str,
    result_status: str,
    artefact_path: str | None = None,
    result_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record stage completion and ask pipeline-runner for deterministic next transition."""
    state = _load_pipeline_state()
    current_stage = state.get("current_stage")
    if current_stage and current_stage != stage_completed:
        return {
            "blocked": True,
            "reason": (
                "stage mismatch: "
                f"state current_stage={current_stage}, stage_completed={stage_completed}"
            ),
        }

    stages = state.setdefault("stages", {})
    stage_record = stages.setdefault(stage_completed, {})
    stage_record["status"] = "complete"
    stage_record["completed_at"] = _to_iso_utc()
    if artefact_path:
        stage_record["artefact"] = artefact_path

    notes = state.setdefault("_notes", {})
    notes["latest_result"] = {
        "stage_completed": stage_completed,
        "result_status": result_status,
        "artefact_path": artefact_path,
        "result_payload": result_payload,
        "received_at": _to_iso_utc(),
    }

    _save_pipeline_state(state)

    routing_decision = await _run_pipeline_runner(
        completed_stage=stage_completed,
        result_status=result_status,
        artefact_path=artefact_path,
    )

    refreshed_state = _load_pipeline_state()
    refreshed_notes = refreshed_state.setdefault("_notes", {})
    refreshed_notes["_routing_decision"] = routing_decision
    _save_pipeline_state(refreshed_state)

    return routing_decision


@mcp.tool()
async def validate_deferred_paths(
    deferred_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate deferred item file paths and attempt path correction where possible."""
    validated: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    corrections: list[dict[str, Any]] = []

    for item in deferred_items:
        file_value = str(item.get("file", "")).strip()
        detail = str(item.get("detail", "")).strip()

        if not file_value:
            unverified.append({
                **item,
                "verified": False,
                "reason": "missing file path",
            })
            continue

        candidate = WORKSPACE_ROOT / file_value
        if candidate.exists() and _path_contains_hint(candidate, detail):
            validated.append({
                **item,
                "verified": True,
            })
            continue

        corrected = _attempt_path_correction(file_value)
        if corrected and _path_contains_hint(corrected, detail):
            relative_corrected = corrected.relative_to(WORKSPACE_ROOT).as_posix()
            corrected_item = {
                **item,
                "file": relative_corrected,
                "verified": True,
            }
            validated.append(corrected_item)
            corrections.append({
                "original_file": file_value,
                "corrected_file": relative_corrected,
                "id": item.get("id"),
            })
            continue

        reason = "file not found"
        if candidate.exists():
            reason = "file found but detail hint did not match"
        unverified.append({
            **item,
            "verified": False,
            "reason": reason,
        })

    return {
        "validated": validated,
        "unverified": unverified,
        "corrections": corrections,
    }


@mcp.tool()
async def get_pipeline_status() -> dict[str, Any]:
    """Return current pipeline status and best-effort next transition summary."""
    state = _load_pipeline_state()
    notes = state.get("_notes") or {}

    stages_summary: dict[str, Any] = {}
    for stage_name, stage_info in (state.get("stages") or {}).items():
        if isinstance(stage_info, dict):
            stages_summary[stage_name] = {
                "status": stage_info.get("status"),
                "artefact": stage_info.get("artefact"),
                "completed_at": stage_info.get("completed_at"),
            }

    return {
        "project": state.get("project"),
        "feature": state.get("feature"),
        "current_stage": state.get("current_stage"),
        "pipeline_mode": state.get("pipeline_mode", "supervised"),
        "stages_summary": stages_summary,
        "blocked_by": state.get("blocked_by"),
        "next_transition": notes.get("_routing_decision"),
        "progress_line": _get_progress_line(state),
        "state_file": str(PIPELINE_STATE_PATH),
    }


@mcp.tool()
async def skip_stage(stage_to_skip: str, reason: str) -> dict[str, Any]:
    """Skip the current pipeline stage and advance to the next one.

    Use when a stage is not needed for this task (e.g. skipping security
    review for a docs-only change, or skipping prd for a small bug fix).
    Only the current stage can be skipped. Gates that the skipped stage
    would have satisfied are auto-approved.

    Returns the result including new current_stage and progress_line.
    """
    if not _RUNNER_AVAILABLE:
        # Subprocess fallback
        runner_path = WORKSPACE_ROOT / ".github" / "tools" / "pipeline-runner" / "pipeline_runner.py"
        if not runner_path.exists():
            return {"ok": False, "error": "pipeline-runner not found"}
        command = [
            sys.executable, str(runner_path), "skip",
            "--state-file", str(PIPELINE_STATE_PATH),
            "--stage", stage_to_skip,
            "--reason", reason,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(WORKSPACE_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=30.0
            )
        except (asyncio.TimeoutError, Exception) as exc:
            return {"ok": False, "error": f"subprocess error: {exc}"}
        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"ok": False, "error": stdout or stderr_bytes.decode()}

    # In-process path (preferred)
    try:
        pstate = _pr._load_state(PIPELINE_STATE_PATH)
        result = _pr.skip_stage(pstate, stage_to_skip, reason)
        if result.get("ok"):
            _pr._save_state(PIPELINE_STATE_PATH, pstate)
        return result
    except Exception as exc:
        return {"ok": False, "error": f"skip_stage error: {exc}"}


@mcp.tool()
async def set_pipeline_mode(mode: str) -> dict[str, Any]:
    """Set the pipeline mode to supervised, assisted, or autopilot."""
    requested_mode = mode.strip().lower()
    if requested_mode not in ALLOWED_PIPELINE_MODES:
        return {
            "success": False,
            "reason": "invalid mode. expected one of: supervised, assisted, autopilot",
        }

    state = _load_pipeline_state()
    state["pipeline_mode"] = requested_mode
    _save_pipeline_state(state)
    return {
        "success": True,
        "pipeline_mode": requested_mode,
    }


@mcp.tool()
async def satisfy_gate(gate_name: str) -> dict[str, Any]:
    """Set a supervision gate to satisfied (true)."""
    gate = gate_name.strip()
    if gate not in ALLOWED_SUPERVISION_GATES:
        return {
            "success": False,
            "reason": f"unknown supervision gate: {gate}",
        }

    state = _load_pipeline_state()
    supervision_gates = state.setdefault("supervision_gates", {})
    supervision_gates[gate] = True
    _save_pipeline_state(state)
    return {
        "success": True,
        "supervision_gate": gate,
        "satisfied": True,
    }


@mcp.tool()
async def pipeline_init(
    project: str,
    feature: str,
    type: str = "feature",
    confirm: bool = False,
    _bypass_active_check: bool = False,
) -> dict[str, Any]:
    """Initialise a new pipeline state file from the template.

    Requires confirm=True to proceed — this prevents accidental invocation
    mid-run. Use when starting a brand-new feature or hotfix pipeline.

    If a pipeline-state.json already exists, it will be overwritten.

    _bypass_active_check is an internal flag used by pipeline_reset to skip
    the active-pipeline guard. Do not set this from user-facing calls.
    """
    if not confirm:
        return {
            "success": False,
            "reason": (
                "confirm must be True to initialise a new pipeline. "
                "This will overwrite any existing pipeline-state.json. "
                "Set confirm=True only when the user has explicitly requested a new pipeline."
            ),
        }

    # Guard: refuse to overwrite an active (non-closed) pipeline unless bypass is set.
    if not _bypass_active_check and PIPELINE_STATE_PATH.exists():
        try:
            existing = json.loads(PIPELINE_STATE_PATH.read_text(encoding="utf-8"))
            existing_stage = existing.get("current_stage", "")
            if existing_stage and existing_stage != "closed":
                return {
                    "success": False,
                    "reason": "active_pipeline_detected",
                    "message": (
                        "A pipeline is already active and not closed. "
                        "Use pipeline_reset to intentionally restart, "
                        "or close the current pipeline first."
                    ),
                    "current_pipeline": {
                        "project": existing.get("project"),
                        "feature": existing.get("feature"),
                        "current_stage": existing_stage,
                        "pipeline_mode": existing.get("pipeline_mode", "supervised"),
                        "last_updated": existing.get("last_updated"),
                    },
                }
        except (json.JSONDecodeError, OSError):
            pass  # Corrupt/unreadable state — allow init to overwrite

    allowed_types = {"feature", "hotfix"}
    pipeline_type = type.strip().lower()
    if pipeline_type not in allowed_types:
        return {
            "success": False,
            "reason": f"invalid type '{type}'. expected one of: feature, hotfix",
        }

    template_path = WORKSPACE_ROOT / ".github" / "pipeline-state.template.json"
    if not template_path.exists():
        return {
            "success": False,
            "reason": f"pipeline-state.template.json not found at {template_path}",
        }

    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
        template["project"] = project.strip()
        template["feature"] = feature.strip()
        template["pipeline_mode"] = template.get("pipeline_mode") or "supervised"
        template["type"] = pipeline_type
        template["last_updated"] = _to_iso_utc()
        PIPELINE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PIPELINE_STATE_PATH.write_text(
            json.dumps(template, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        return {
            "success": False,
            "reason": f"pipeline init failed: {exc}",
        }

    return {
        "success": True,
        "project": project.strip(),
        "feature": feature.strip(),
        "type": pipeline_type,
        "state_file": str(PIPELINE_STATE_PATH),
        "message": (
            f"Pipeline initialised for '{project.strip()}' / '{feature.strip()}' "
            f"({pipeline_type}). pipeline_mode is supervised by default. "
            "Use set_pipeline_mode to switch to assisted or autopilot if desired."
        ),
    }


@mcp.tool()
async def pipeline_reset(
    project: str,
    feature: str,
    type: str = "feature",
    confirm: bool = False,
) -> dict[str, Any]:
    """Reset the current pipeline state and start a new pipeline run.

    Identical to pipeline_init but semantically signals resetting an
    existing pipeline rather than creating a fresh one. Requires confirm=True.
    Use when a pipeline has closed and the user wants to start the next feature,
    or when explicitly restarting a failed/stale pipeline.
    """
    if not confirm:
        return {
            "success": False,
            "reason": (
                "confirm must be True to reset the pipeline. "
                "This will overwrite the existing pipeline-state.json. "
                "Set confirm=True only when the user has explicitly requested a reset."
            ),
        }

    # Delegate to pipeline_init with confirm already validated.
    # _bypass_active_check=True: pipeline_reset is explicit user intent to restart —
    # the active-pipeline guard does not apply here.
    return await pipeline_init(
        project=project,
        feature=feature,
        type=type,
        confirm=True,
        _bypass_active_check=True,
    )


@mcp.tool()
async def run_command(
    command: str,
    timeout: int = 60,
    max_output_chars: int = 20000,
) -> dict[str, Any]:
    """Execute a shell command in the workspace root and return stdout, stderr, exit code.

    Use this for running tests (pytest, playwright), linters (black, ruff),
    formatters, build steps, or any other shell command the pipeline needs to
    execute hands-free. Agents should prefer this over asking the user to run
    commands manually in a terminal.

    Args:
        command: Shell command to run (e.g. ".venv/Scripts/pytest tests/ -v").
                 Executed in the workspace root directory with shell=True.
        timeout: Seconds before the process is killed. Default 60s. Increase for
                 long test suites, Playwright runs, or slow build steps.
        max_output_chars: Truncate combined output to this many characters to
                          avoid flooding the context window. Default 20000.
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(WORKSPACE_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=float(timeout)
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return {
                "success": False,
                "exit_code": -1,
                "command": command,
                "reason": f"Command timed out after {timeout}s",
                "output": "",
                "truncated": False,
                "cwd": str(WORKSPACE_ROOT),
            }

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        combined = (stdout + ("\n" + stderr if stderr.strip() else "")).strip()

        truncated = False
        if len(combined) > max_output_chars:
            combined = combined[:max_output_chars] + "\n[...output truncated]"
            truncated = True

        return {
            "success": process.returncode == 0,
            "exit_code": process.returncode,
            "command": command,
            "output": combined,
            "truncated": truncated,
            "cwd": str(WORKSPACE_ROOT),
        }

    except Exception as exc:
        return {
            "success": False,
            "exit_code": -1,
            "command": command,
            "reason": str(exc),
            "output": "",
            "truncated": False,
            "cwd": str(WORKSPACE_ROOT),
        }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
