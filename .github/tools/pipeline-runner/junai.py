#!/usr/bin/env python3
"""junai — Unified CLI for the JUNAI agent pipeline and agent management.

Usage:
    junai pipeline <subcommand> [options]
    junai agent    <subcommand> [options]
    junai pool     <subcommand> [options]

Pipeline subcommands:
    status                                     Print current stage, mode, last updated
    init    --project <n> --feature <s>        Initialise a new pipeline from template
            [--type feature|hotfix] [--force]
    mode    --value supervised|assisted|autopilot
                                               Switch pipeline mode
    gate    --name <gate_name>                 Satisfy a supervision gate
    next    [--event <event>]                  Compute next transition (dry-run)
    advance --event <event> [--stage <stage>]  Advance and persist pipeline state
    discover-artefacts [--feature <slug>]      Find existing PRD/ADR/plan artefacts
            [--write-registry]
    fast-track --from-plan <path>              Align state from an approved plan
            [--entry preflight|implement] [--mode supervised|assisted|autopilot]
    run-plan --from-plan <path>                Score, align, and route an approved plan
            [--entry preflight|implement] [--mode supervised|assisted|autopilot]
    resume                                     Print safest next action for paused work
    parse-plan --plan <path>                   Parse numbered implementation phases
    plan-score --plan <path>                   Score plan readiness for automation
    context-guard --plan <path> [--phase <n>]  Estimate static phase context risk
    model-route --stage <stage>                Recommend model for a stage/phase
            [--plan <path>] [--phase <n>]
    dashboard [--output <path>]                Write markdown pipeline dashboard
    halt-info [--reason <text>]                Classify halt reason and recovery commands
    evidence --stage <stage> --status <s>      Write execution evidence bundle
    doctor                                     Diagnose state, artefact, and routing issues
    history                                    Print routing and stage history
    last-handoff                               Print latest routing decision and handoff payload
    transitions                                List all T-01-T-27 transitions as table
    preflight --target-stage <stage>           Run preflight checks before a stage

Agent subcommands:
    make      --name <xyz> [--role executing|advisory]
              Scaffold a new agent from the canonical template
    validate  --name <xyz>
              Audit agent file against required-section checklist (read-only)
    diff      --name <xyz>
              Preview exactly what 'onboard' would inject (read-only)
    onboard   --name <xyz> [--yes]
              Patch missing sections, check registry entry, report summary
    list                                       Table of all agents + compliance status
    inspect   --name <xyz>                     Full detail for one agent
    remove    --name <xyz> [--force]           Deregister agent from agents.registry.json

Pool subcommands:
    version                                    Print current pool SHA
    status   --project <path> [--json]         Summarize managed drift for a project
    diff     --project <path> [--json]         List managed drift entries for a project
    promote  --project <path> [--dry-run]      Promote selected managed project changes into a review branch
    nuggets review --project <path>            Review pending nugget candidates

Run 'junai pipeline --help', 'junai agent --help', or 'junai pool --help' for full option details.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure tools/pipeline-runner is importable regardless of cwd
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_POOL_SYNC_DIR = _HERE.parent / "pool-sync"
if str(_POOL_SYNC_DIR) not in sys.path:
    sys.path.insert(0, str(_POOL_SYNC_DIR))


def _pipeline(argv: list[str]) -> None:
    """Delegate to pipeline_runner.main() with the given argv."""
    import pipeline_runner  # type: ignore[import]

    _backup = sys.argv
    sys.argv = ["junai-pipeline"] + argv
    try:
        pipeline_runner.main()
    finally:
        sys.argv = _backup


def _agent(argv: list[str]) -> None:
    """Delegate to agent_manager.main() with the given argv."""
    import agent_manager  # type: ignore[import]

    _backup = sys.argv
    sys.argv = ["junai-agent"] + argv
    try:
        agent_manager.main()
    finally:
        sys.argv = _backup


def _pool(argv: list[str]) -> None:
    """Delegate to pool_sync.main() with the given argv."""
    import pool_sync  # type: ignore[import]

    raise SystemExit(pool_sync.main(argv))


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__)
        raise SystemExit(0)

    group = sys.argv[1].lower()
    rest = sys.argv[2:]

    if group == "pipeline":
        _pipeline(rest)
    elif group == "agent":
        _agent(rest)
    elif group == "pool":
        _pool(rest)
    else:
        print(f"[junai] Unknown group '{group}'. Expected: pipeline | agent | pool")
        print("        Run 'junai --help' for usage.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
