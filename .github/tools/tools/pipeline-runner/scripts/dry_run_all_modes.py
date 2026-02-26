"""
Dry-run walkthrough of all 3 pipeline modes across the full stage sequence.

Simulates the happy-path journey in each mode, showing exactly how gates and
routing behave per mode. Nothing is written to disk — pure in-memory
computation against the real runner logic.

Run from the pipeline-runner directory:
    python scripts/dry_run_all_modes.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

# Make sure the runner package is importable from this script's location
RUNNER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNNER_DIR))

from pipeline_runner import compute_next_transition
from schema import CompletionEvent, PipelineState, parse_pipeline_state

MODES = ["supervised", "assisted", "autopilot"]

# ─── Approved artefact content ─────────────────────────────────────────────────
# artefact_approved guard requires YAML frontmatter with `approval: approved`
APPROVED_MD = "---\napproval: approved\n---\n\nmock artefact content\n"
PLAIN_MD    = "mock artefact content\n"  # no approval frontmatter

# ─── Happy path definition ─────────────────────────────────────────────────────
# (from_stage, event, artefact_file, needs_approved_frontmatter, gate_name)
# tester uses "passed"; review uses "approved" — matching Transition event strings
HAPPY_PATH: list[tuple[str, str, str, bool, str | None]] = [
    ("intent",      "complete",  "intent.md",  False,  "intent_approved"),
    ("prd",         "complete",  "prd.md",     True,   None),
    ("architect",   "complete",  "adr.md",     True,   "adr_approved"),
    ("plan",        "complete",  "plan.md",    True,   "plan_approved"),
    ("implement",   "complete",  "impl.md",    False,  None),
    ("tester",      "passed",    "test.md",    False,  None),
    ("review",      "approved",  "review.md",  True,   "review_approved"),
]

# ─── State factory ─────────────────────────────────────────────────────────────
def _make_state(
    current_stage: str,
    mode: str,
    artefact_file: str | None,
    gates: dict[str, bool],
) -> PipelineState:
    base: dict[str, Any] = {
        "project": "dry-run",
        "feature": "mock-pipeline",
        "pipeline_version": "1.0",
        "pipeline_mode": mode,
        "type": None,
        "current_stage": current_stage,
        "stages": {
            "intent":      {"status": "in_progress", "artefact": None, "completed_at": None},
            "prd":         {"status": "not_started",  "artefact": None, "completed_at": None},
            "architect":   {"status": "not_started",  "artefact": None, "completed_at": None},
            "security":    {"status": "not_started",  "artefact": None, "completed_at": None},
            "plan":        {"status": "not_started",  "artefact": None, "completed_at": None},
            "ux_research": {"status": "not_started",  "artefact": None, "completed_at": None},
            "ui_design":   {"status": "not_started",  "artefact": None, "completed_at": None},
            "implement":   {
                "status": "in_progress", "artefact": None, "completed_at": None,
                "current_phase": 1, "total_phases": 1,  # phase 1/1 — all phases done
                "retry_count": 0, "max_retries": 3,
            },
            "tester":  {"status": "not_started", "artefact": None, "completed_at": None,
                        "retry_count": 0, "max_retries": 3},
            "review":  {"status": "not_started", "artefact": None, "completed_at": None,
                        "retry_count": 0, "max_retries": 3},
            "debug":   {"status": "not_started", "artefact": None, "completed_at": None},
            "closed":  {"status": "not_started", "artefact": None, "completed_at": None},
        },
        "supervision_gates": {
            "intent_approved": gates.get("intent_approved", False),
            "adr_approved":    gates.get("adr_approved",    False),
            "plan_approved":   gates.get("plan_approved",   False),
            "review_approved": gates.get("review_approved", False),
        },
        "deferred": [],
        "blocked_by": None,
        "last_updated": None,
        "_notes": {"handoff_payload": None, "_routing_decision": None, "_hotfix_brief": None},
    }
    if artefact_file:
        base["stages"][current_stage]["artefact"] = artefact_file
    return parse_pipeline_state(base)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _autopilot_auto_satisfies(gate: str | None) -> bool:
    """True if autopilot auto-satisfies this gate (all gates except intent_approved)."""
    return gate is not None and gate != "intent_approved"


def _section(title: str) -> None:
    print(f"\n  ┌─ {title}")


def _hr() -> None:
    print(f"  {'─' * 76}")


# ─── Main dry run ──────────────────────────────────────────────────────────────
def run_dry_run() -> None:
    print()
    print("=" * 80)
    print("  PIPELINE DRY RUN — ALL 3 MODES  (nothing written to disk)")
    print("  Tests happy-path routing + gate behaviour at every guarded transition")
    print("=" * 80)

    all_ok = True
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Pre-create all artefact files — approved and plain variants
        artefact_files: dict[str, Path] = {}
        for stage, _, artefact_file, needs_approval, _ in HAPPY_PATH:
            path = workspace / artefact_file
            path.write_text(APPROVED_MD if needs_approval else PLAIN_MD, encoding="utf-8")
            artefact_files[stage] = path

        for mode in MODES:
            _section(f"MODE: {mode.upper()}")
            _hr()
            print(f"  {'Stage':<13} {'Event':<10} {'Gate':<18} {'T-ID':<6} {'satisfied':<11} {'→ next':<14} Status")
            _hr()

            for stage, event_status, artefact_file, _, gate in HAPPY_PATH:
                # For each gated transition, run two sub-cases:
                #   A) gate NOT set  → for supervised/assisted: must block on gate
                #                    → for autopilot (non-intent): gate auto-satisfied
                #   B) gate SET      → must pass and route forward
                # For ungated transitions run once.
                sub_cases: list[tuple[dict[str, bool], str]] = (
                    [({}, "gate=N"), ({gate: True}, "gate=Y")]
                    if gate else
                    [({}, "")]
                )

                for gates_dict, sub_label in sub_cases:
                    state = _make_state(stage, mode, artefact_file, gates_dict)
                    event = CompletionEvent(stage_completed=stage, result_status=event_status)

                    try:
                        result = compute_next_transition(state, event, workspace)
                    except Exception as exc:
                        tag = f"[{sub_label}]" if sub_label else ""
                        print(f"  {stage:<13} {event_status:<10} {(gate or '—'):<18} ERR    EXCEPTION   —              ✗ {exc}")
                        failures.append(f"{mode}/{stage}{tag}: EXCEPTION {exc}")
                        all_ok = False
                        continue

                    actual_sat   = result.gate_satisfied
                    actual_tid   = result.transition_id or "—"
                    actual_next  = result.next_stage or "—"
                    actual_block = result.blocked

                    # ── Expected outcomes ──────────────────────────────────
                    if gate is None:
                        # No gate: expect transition to fire and not block
                        ok = not actual_block and actual_tid != "—"
                        status = "✓" if ok else f"✗ blocked={actual_block} tid={actual_tid}"
                    elif _autopilot_auto_satisfies(gate) and mode == "autopilot":
                        # autopilot + non-intent gate: always auto-satisfied regardless of gates_dict
                        ok = (actual_sat is True) and not actual_block
                        status = "✓" if ok else f"✗ expected auto-satisfied, got sat={actual_sat} blocked={actual_block}"
                    elif not gates_dict:
                        # supervised/assisted, gate NOT set: must hold (gate_satisfied=False, not blocked outright)
                        # intent_approved in autopilot also goes here
                        ok = (actual_sat is False) and (actual_tid != "—")
                        status = "✓" if ok else f"✗ expected sat=False+routed, got sat={actual_sat} tid={actual_tid} blocked={actual_block}"
                    else:
                        # gate IS set: must pass (gate_satisfied=True) and route forward
                        ok = (actual_sat is True) and not actual_block and actual_next != "—"
                        status = "✓" if ok else f"✗ expected sat=True+routed, got sat={actual_sat} next={actual_next}"

                    if not ok:
                        all_ok = False
                        tag = f"[{sub_label}]" if sub_label else ""
                        failures.append(f"{mode}/{stage}{tag}: {status}")

                    gate_col = f"{gate or '—'}"
                    if sub_label:
                        gate_col = f"{gate} {sub_label}"
                    sat_str = f"{actual_sat}" if gate else "—"

                    print(
                        f"  {stage:<13} {event_status:<10} {gate_col:<18} "
                        f"{actual_tid:<6} {sat_str:<11} {actual_next:<14} {status}"
                    )

            _hr()

    print()
    print("=" * 80)
    if all_ok:
        print("  ✓  ALL CHECKS PASSED — pipeline routes correctly in all 3 modes")
        print()
        print("  Gate behaviour summary:")
        print("    supervised  — gates block in all 4 guarded transitions (requires manual approval)")
        print("    assisted    — identical gate behaviour to supervised at runner level")
        print("                  (assisted vs supervised difference is orchestrator-level only:")
        print("                   supervised presents a button; assisted auto-invokes next agent)")
        print("    autopilot   — intent_approved always requires manual approval")
        print("                  adr_approved / plan_approved / review_approved auto-satisfied")
    else:
        print("  FAILURES:")
        for f in failures:
            print(f"    ✗ {f}")
    print("=" * 80)
    print()

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    run_dry_run()
