#!/usr/bin/env python3
"""junai — Unified CLI for the JUNAI agent pipeline and agent management.

Usage:
    junai pipeline <subcommand> [options]
    junai agent    <subcommand> [options]

Pipeline subcommands:
    status                                     Print current stage, mode, last updated
    init    --project <n> --feature <s>        Initialise a new pipeline from template
            [--type feature|hotfix] [--force]
    mode    --value supervised|auto            Switch pipeline mode
    gate    --name <gate_name>                 Satisfy a supervision gate
    next    [--event <event>]                  Compute next transition (dry-run)
    advance --event <event> [--stage <stage>]  Advance and persist pipeline state
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

Run 'junai pipeline --help' or 'junai agent --help' for full option details.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure tools/pipeline-runner is importable regardless of cwd
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


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
    else:
        print(f"[junai] Unknown group '{group}'. Expected: pipeline | agent")
        print("        Run 'junai --help' for usage.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
