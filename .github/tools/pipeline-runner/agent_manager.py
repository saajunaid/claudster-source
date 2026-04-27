#!/usr/bin/env python3
"""agent_manager — Agent lifecycle management for the JUNAI pipeline.

Commands:
    make      --name <xyz> [--role executing|advisory]
    validate  --name <xyz>
    diff      --name <xyz>
    onboard   --name <xyz> [--yes]
    list
    inspect   --name <xyz>
    remove    --name <xyz> [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (resolved relative to this file's location so they work from anywhere)
# ---------------------------------------------------------------------------
_TOOL_DIR = Path(__file__).resolve().parent        # .github/tools/pipeline-runner/
_REPO_ROOT = _TOOL_DIR.parent.parent.parent        # workspace root (agent-sandbox/)
_AGENTS_DIR = _REPO_ROOT / ".github" / "agents"
_REGISTRY = _TOOL_DIR / "agents.registry.json"

# ---------------------------------------------------------------------------
# Required-section definitions
#   Each entry: (key, description, test_fn(lines: list[str]) -> bool)
# ---------------------------------------------------------------------------

def _has_frontmatter(lines: list[str]) -> bool:
    """YAML front-matter block present (--- ... ---)."""
    if not lines or lines[0].rstrip() != "---":
        return False
    return any(l.rstrip() == "---" for l in lines[1:])


def _has_name(lines: list[str]) -> bool:
    return any(re.match(r"^name:\s*\S", l) for l in lines)


def _has_description(lines: list[str]) -> bool:
    return any(re.match(r"^description:\s*\S", l) for l in lines)


def _has_mcp_tools(lines: list[str]) -> bool:
    """tools field has at least one junai-mcp/ tool reference."""
    tool_line = next((l for l in lines if l.strip().startswith("tools:")), None)
    return tool_line is not None and "junai-mcp/" in tool_line


def _has_handoff_return(lines: list[str]) -> bool:
    """Front-matter contains a 'Return to Orchestrator' handoff entry."""
    return any("Return to Orchestrator" in l for l in lines)


def _has_section_8(lines: list[str]) -> bool:
    """A Completion Reporting Protocol heading exists (any section number)."""
    return any(re.search(r"#+\s+\d+\.\s+Completion Reporting Protocol", l) for l in lines)


def _has_hard_stop(lines: list[str]) -> bool:
    """HARD STOP language present (§8 gate)."""
    return any("HARD STOP" in l for l in lines)


def _has_scope_restriction(lines: list[str]) -> bool:
    """GAP-I2-c scope restriction block present."""
    return any("Scope restriction" in l and "GAP-I2-c" in l for l in lines)


def _has_pipeline_state_ref(lines: list[str]) -> bool:
    """pipeline-state.json is referenced somewhere."""
    return any("pipeline-state.json" in l for l in lines)


def _has_junai_advance(lines: list[str]) -> bool:
    """junai pipeline advance (or pipeline advance) command referenced."""
    return any(re.search(r"junai pipeline advance|pipeline advance", l) for l in lines)


REQUIRED_SECTIONS: list[tuple[str, str, object]] = [
    ("frontmatter",       "YAML front-matter block (--- … ---)",           _has_frontmatter),
    ("name",              "name: field in front-matter",                    _has_name),
    ("description",       "description: field in front-matter",            _has_description),
    ("mcp_tools",         "tools: has junai-mcp/ references",              _has_mcp_tools),
    ("handoff_return",    "Return to Orchestrator handoff in front-matter", _has_handoff_return),
    ("section_8",         "§8 Completion Reporting Protocol heading",       _has_section_8),
    ("hard_stop",         "HARD STOP language in §8",                       _has_hard_stop),
    ("scope_restriction", "GAP-I2-c scope restriction block",               _has_scope_restriction),
    ("pipeline_state",    "pipeline-state.json reference",                  _has_pipeline_state_ref),
    ("junai_advance",     "junai pipeline advance command in §8",           _has_junai_advance),
]

# ---------------------------------------------------------------------------
# Template for `junai agent make`
# ---------------------------------------------------------------------------
EXECUTING_TEMPLATE = '''\
---
name: {ClassName}
description: >
  TODO: One-sentence description of what this executing agent does.
tools:
  - vscode/readFile
  - vscode/writeFile
  - vscode/runInTerminal
  - junai-mcp/get_pipeline_status
  - junai-mcp/notify_orchestrator
  - junai-mcp/satisfy_gate
  - junai-mcp/set_pipeline_mode
  - junai-mcp/validate_deferred_paths
model: claude-sonnet-4-5
handoffs:
  - label: Return to Orchestrator
    agent: Orchestrator
    prompt: >-
      Stage complete. Read pipeline-state.json and _routing_decision, then route to
      the next stage as determined by the transition table.
    send: false
---

# {ClassName}

> **Pipeline role:** Executing agent — owns stage `{stage_name}`
> **Trigger:** Orchestrator hands off when `current_stage == "{stage_name}"`

---

## 1. Intake

1. Read `/pipeline/pipeline-state.json`.
2. Read `handoff_payload` from the Orchestrator message.
3. Confirm `current_stage == "{stage_name}"` — abort if mismatch.

---

## 2. Context Load
<!-- TODO: list files/docs this agent must read before starting work -->

---

## 3. Work Instructions
<!-- TODO: numbered steps for the actual work this agent performs -->

---

## 4. Output Contract
<!-- TODO: list all expected artefacts (files, outputs) -->

---

## 5. Quality Gates
<!-- TODO: acceptance criteria the agent must verify before reporting complete -->

---

## 6. Error Handling
<!-- TODO: what to do on failure / how to surface blockers to Orchestrator -->

---

## 7. Artefact Logging
<!-- TODO: list artefact paths that must be recorded in pipeline-state.json -->

---

## 8. Completion Reporting Protocol

1. Verify all §5 quality gates pass.
2. Update `pipeline-state.json`:
   - Set `stages.{stage_name}.status = "complete"`
   - Set `stages.{stage_name}.completed_at` to ISO-8601 timestamp
   - Set `stages.{stage_name}.artefact` to primary output path

> **Scope restriction (GAP-I2-c):** Only write your own stage\'s `status`,
> `completed_at`, and `artefact` fields.  Never write `current_stage`,
> `_notes._routing_decision`, or `supervision_gates` — those belong exclusively
> to Orchestrator and pipeline-runner.

3. Run `junai pipeline advance --event {stage_name}_complete` in terminal.
4. Commit all changed files with message matching the Output Contract.

**HARD STOP — Do NOT click "Return to Orchestrator" until:**
- [ ] All quality gates in §5 pass.
- [ ] `stages.{stage_name}.status` is `"complete"` in pipeline-state.json.
- [ ] `junai pipeline advance` returned success (status 200 / no error).
- [ ] All artefacts committed to git.
'''

ADVISORY_TEMPLATE = '''\
---
name: {ClassName}
description: >
  TODO: One-sentence description of what this advisory agent does.
tools:
  - vscode/readFile
  - vscode/runInTerminal
model: claude-sonnet-4-5
handoffs:
  - label: Return to Orchestrator
    agent: Orchestrator
    prompt: >-
      Advisory review complete. Read my report and decide whether to proceed or
      block the pipeline, then update pipeline-state.json accordingly.
    send: false
---

# {ClassName} (Advisory)

> **Pipeline role:** Advisory agent — produces a non-binding review report
> **Trigger:** Orchestrator invokes at the appropriate review checkpoint

---

## 1. Intake

1. Read the file(s) or artefacts specified in the Orchestrator handoff payload.
2. Do NOT modify `pipeline-state.json` — advisory agents are read-only.

---

## 2. Scope
<!-- TODO: describe exactly what this agent reviews -->

---

## 3. Review Checklist
<!-- TODO: ordered list of items to evaluate -->

---

## 4. Report Format

Produce a Markdown report with:
- **Summary:** pass / fail / needs-work verdict
- **Findings:** numbered list of issues
- **Recommendations:** actionable next steps

---

## 5. Completion

1. Present the report in chat.
2. Do NOT run `junai pipeline advance` — advisory agents never advance the pipeline.
3. Click "Return to Orchestrator" so it can decide the next step.

**HARD STOP — Do NOT advance the pipeline from an advisory agent.**
'''

# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _load_registry() -> dict:
    if _REGISTRY.exists():
        return json.loads(_REGISTRY.read_text(encoding="utf-8"))
    return {}


def _save_registry(data: dict) -> None:
    _REGISTRY.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _agent_file(name: str) -> Path:
    """Return expected path for <name>.agent.md."""
    return _AGENTS_DIR / f"{name}.agent.md"


def _read_lines(name: str) -> list[str]:
    p = _agent_file(name)
    if not p.exists():
        raise FileNotFoundError(f"Agent file not found: {p}")
    return p.read_text(encoding="utf-8").splitlines()


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

def _run_checks(lines: list[str]) -> list[dict]:
    """Return list of {key, description, passed} for each required section."""
    results = []
    for key, desc, test_fn in REQUIRED_SECTIONS:
        results.append({"key": key, "description": desc, "passed": bool(test_fn(lines))})
    return results


def _print_check_table(name: str, checks: list[dict]) -> None:
    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    print(f"\nAgent: {name}  ({passed}/{total} checks pass)\n")
    print(f"  {'CHECK':<22}  {'STATUS':<8}  DESCRIPTION")
    print(f"  {'-'*22}  {'-'*8}  {'-'*42}")
    for c in checks:
        status = "  PASS  " if c["passed"] else "  FAIL  "
        print(f"  {c['key']:<22}  {status}  {c['description']}")
    print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_make(args: argparse.Namespace) -> None:
    name = args.name
    role = args.role  # "executing" | "advisory"
    target = _agent_file(name)

    if target.exists() and not args.force:
        print(f"[make] '{target}' already exists. Use --force to overwrite.")
        raise SystemExit(1)

    class_name = "".join(w.capitalize() for w in re.split(r"[-_\s]+", name))
    stage_name = name.lower().replace("-", "_").replace(" ", "_")

    tmpl = EXECUTING_TEMPLATE if role == "executing" else ADVISORY_TEMPLATE
    content = tmpl.format(ClassName=class_name, stage_name=stage_name)

    _AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"[make] Created {target}")
    print(f"       Role: {role}")
    print(f"       Next: edit the TODO sections, then run 'junai agent validate --name {name}'")


def cmd_validate(args: argparse.Namespace) -> None:
    try:
        lines = _read_lines(args.name)
    except FileNotFoundError as exc:
        print(f"[validate] {exc}")
        raise SystemExit(1)

    checks = _run_checks(lines)
    _print_check_table(args.name, checks)

    reg = _load_registry()
    stages = reg.get("stages", {})
    if args.name not in stages:
        print(f"  WARNING  Agent '{args.name}' is NOT registered in agents.registry.json\n")

    if not all(c["passed"] for c in checks):
        raise SystemExit(2)


def cmd_diff(args: argparse.Namespace) -> None:
    """Show what 'onboard' would inject — dry-run."""
    try:
        lines = _read_lines(args.name)
    except FileNotFoundError as exc:
        print(f"[diff] {exc}")
        raise SystemExit(1)

    checks = _run_checks(lines)
    failing = [c for c in checks if not c["passed"]]

    if not failing:
        print(f"[diff] '{args.name}' already passes all checks — nothing to inject.")
        return

    print(f"[diff] Patches 'onboard' would apply to '{args.name}':\n")
    for c in failing:
        print(f"  MISSING  {c['key']:<22}  {c['description']}")

    print()

    # Show concrete text snippets for injectable checks
    injectable_hints = {
        "scope_restriction": (
            "\n> **Scope restriction (GAP-I2-c):** Only write your own stage's `status`,\n"
            "> `completed_at`, and `artefact` fields.  Never write `current_stage`,\n"
            "> `_notes._routing_decision`, or `supervision_gates` — those belong exclusively\n"
            "> to Orchestrator and pipeline-runner.\n"
        ),
        "hard_stop": (
            "\n**HARD STOP — Do NOT click \"Return to Orchestrator\" until:**\n"
            "- [ ] All quality gates pass.\n"
            "- [ ] `stages.<stage>.status` is `\"complete\"` in pipeline-state.json.\n"
            "- [ ] `junai pipeline advance` returned success.\n"
            "- [ ] All artefacts committed to git.\n"
        ),
        "junai_advance": (
            "\n3. Run `junai pipeline advance --event <stage>_complete` in terminal.\n"
        ),
        "section_8": (
            "\n## 8. Completion Reporting Protocol\n\n"
            "1. Verify all quality gates pass.\n"
            "2. Update `pipeline-state.json` …\n"
        ),
    }
    for c in failing:
        hint = injectable_hints.get(c["key"])
        if hint:
            print(f"--- Would inject for '{c['key']}': ---")
            print(hint)

    reg = _load_registry()
    stages = reg.get("stages", {})
    if args.name not in stages:
        print(f"  INFO  'onboard' would also warn: '{args.name}' not in agents.registry.json")
        print("        (registry entry must be added manually — onboard does not modify it)\n")


def cmd_onboard(args: argparse.Namespace) -> None:
    try:
        lines = _read_lines(args.name)
    except FileNotFoundError as exc:
        print(f"[onboard] {exc}")
        raise SystemExit(1)

    checks = _run_checks(lines)
    failing = [c for c in checks if not c["passed"]]

    if not failing:
        print(f"[onboard] '{args.name}' already passes all checks. Nothing to do.")
        return

    # Only auto-patch items that are safe to append without context
    auto_patchable = {"scope_restriction", "hard_stop"}
    patchable = [c for c in failing if c["key"] in auto_patchable]
    manual_only = [c for c in failing if c["key"] not in auto_patchable]

    print(f"[onboard] Agent: {args.name}")
    if patchable:
        print(f"  Will auto-patch ({len(patchable)} items):")
        for c in patchable:
            print(f"    + {c['key']:<22} {c['description']}")
    if manual_only:
        print(f"  Requires manual editing ({len(manual_only)} items):")
        for c in manual_only:
            print(f"    ! {c['key']:<22} {c['description']}")

    reg = _load_registry()
    stages = reg.get("stages", {})
    if args.name not in stages:
        print(f"\n  WARNING  '{args.name}' is NOT in agents.registry.json")
        print("           Add the stage entry manually — onboard does not modify the registry.\n")

    if not args.yes and patchable:
        answer = input("  Apply the auto-patches listed above? [y/N] ").strip().lower()
        if answer != "y":
            print("[onboard] Aborted. No changes made.")
            return

    if patchable:
        content = "\n".join(lines)
        for c in patchable:
            if c["key"] == "scope_restriction":
                inject = (
                    "\n> **Scope restriction (GAP-I2-c):** Only write your own stage's `status`,\n"
                    "> `completed_at`, and `artefact` fields.  Never write `current_stage`,\n"
                    "> `_notes._routing_decision`, or `supervision_gates` — those belong exclusively\n"
                    "> to Orchestrator and pipeline-runner.\n"
                )
                # Inject after the first "Update pipeline-state.json" line in §8
                content = re.sub(
                    r"(Update `pipeline-state\.json`[^\n]*\n)",
                    r"\1" + inject,
                    content,
                    count=1,
                )
            elif c["key"] == "hard_stop":
                inject = (
                    "\n**HARD STOP — Do NOT click \"Return to Orchestrator\" until:**\n"
                    "- [ ] All quality gates pass.\n"
                    "- [ ] `stages.<stage>.status` is `\"complete\"` in pipeline-state.json.\n"
                    "- [ ] `junai pipeline advance` returned success.\n"
                    "- [ ] All artefacts committed to git.\n"
                )
                content += inject

        _agent_file(args.name).write_text(content, encoding="utf-8")
        print(f"[onboard] '{args.name}' patched and saved.")

    if manual_only:
        print(f"\n[onboard] {len(manual_only)} item(s) require manual attention — "
              "re-run 'validate' after editing.")
        raise SystemExit(2)
    else:
        print(f"[onboard] '{args.name}' onboarding complete.")


def cmd_list(_args: argparse.Namespace) -> None:
    reg = _load_registry()
    reg_stages = set(reg.get("stages", {}).keys())

    agent_files = sorted(_AGENTS_DIR.glob("*.agent.md"))
    if not agent_files:
        print(f"[list] No agent files found in {_AGENTS_DIR}")
        return

    header = f"  {'AGENT':<32}  {'REGISTERED':<12}  {'§8':<6}  {'HARD STOP':<10}  {'I2-c':<6}  ROLE"
    print(f"\n{header}")
    print(f"  {'-'*32}  {'-'*12}  {'-'*6}  {'-'*10}  {'-'*6}  ----")

    for f in agent_files:
        name = f.stem.replace(".agent", "")
        lines = f.read_text(encoding="utf-8").splitlines()
        checks_map = {c["key"]: c["passed"] for c in _run_checks(lines)}

        registered = "YES" if name in reg_stages else "NO "
        has_s8     = "YES" if checks_map.get("section_8")         else "NO "
        has_hs     = "YES" if checks_map.get("hard_stop")         else "NO "
        has_i2c    = "YES" if checks_map.get("scope_restriction") else "NO "

        # Infer role from template markers
        role = "advisory" if "advisory" in " ".join(lines[:20]).lower() else "executing"

        print(f"  {name:<32}  {registered:<12}  {has_s8:<6}  {has_hs:<10}  {has_i2c:<6}  {role}")

    print()


def cmd_inspect(args: argparse.Namespace) -> None:
    try:
        lines = _read_lines(args.name)
    except FileNotFoundError as exc:
        print(f"[inspect] {exc}")
        raise SystemExit(1)

    reg = _load_registry()
    stage_entry = reg.get("stages", {}).get(args.name)

    print(f"\n=== Agent: {args.name} ===")
    print(f"File: {_agent_file(args.name)}")

    if stage_entry:
        print(f"\nRegistry entry:")
        print(json.dumps(stage_entry, indent=4))
    else:
        print(f"\nRegistry: NOT REGISTERED in agents.registry.json")

    # Parse name/description from frontmatter
    for l in lines:
        if re.match(r"^name:\s*\S", l):
            print(f"\nname:        {l.split(':', 1)[1].strip()}")
        if re.match(r"^description:\s*\S", l):
            print(f"description: {l.split(':', 1)[1].strip()}")
        if re.match(r"^model:\s*\S", l):
            print(f"model:       {l.split(':', 1)[1].strip()}")

    # Handoffs
    in_handoffs = False
    handoffs: list[str] = []
    for l in lines:
        if re.match(r"^handoffs:", l):
            in_handoffs = True
            continue
        if in_handoffs:
            if l.startswith("---") or (l and not l.startswith(" ") and not l.startswith("-")):
                break
            if re.search(r"label:", l):
                handoffs.append(l.strip())
    if handoffs:
        print("\nHandoffs:")
        for h in handoffs:
            print(f"  {h}")

    print("\nCompliance checks:")
    checks = _run_checks(lines)
    _print_check_table(args.name, checks)

    # Show headings (##)
    headings = [l for l in lines if re.match(r"^#{1,3} ", l)]
    if headings:
        print("Sections:")
        for h in headings[:20]:
            print(f"  {h}")
    print()


def cmd_remove(args: argparse.Namespace) -> None:
    reg = _load_registry()
    stages = reg.get("stages", {})

    if args.name not in stages:
        print(f"[remove] '{args.name}' is not registered in agents.registry.json. Nothing to do.")
        return

    if not args.force:
        answer = input(f"[remove] Remove '{args.name}' from registry? [y/N] ").strip().lower()
        if answer != "y":
            print("[remove] Aborted.")
            return

    del stages[args.name]
    reg["stages"] = stages
    _save_registry(reg)
    print(f"[remove] '{args.name}' removed from {_REGISTRY}")
    print(f"         NOTE: The agent file itself is untouched — delete it manually if needed.")


# ---------------------------------------------------------------------------
# Argument parser + main
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="junai-agent",
        description="JUNAI agent lifecycle manager",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # make
    p_make = sub.add_parser("make", help="Scaffold a new agent from template")
    p_make.add_argument("--name", required=True, help="Agent name (kebab-case)")
    p_make.add_argument("--role", choices=["executing", "advisory"], default="executing")
    p_make.add_argument("--force", action="store_true", help="Overwrite if file exists")

    # validate
    p_val = sub.add_parser("validate", help="Audit agent against required-section checklist")
    p_val.add_argument("--name", required=True)

    # diff
    p_diff = sub.add_parser("diff", help="Preview what onboard would inject (dry-run)")
    p_diff.add_argument("--name", required=True)

    # onboard
    p_onboard = sub.add_parser("onboard", help="Patch missing sections in an agent file")
    p_onboard.add_argument("--name", required=True)
    p_onboard.add_argument("--yes",  action="store_true", help="Skip confirmation prompt")

    # list
    sub.add_parser("list", help="Table of all agents with compliance status")

    # inspect
    p_inspect = sub.add_parser("inspect", help="Full detail for one agent")
    p_inspect.add_argument("--name", required=True)

    # remove
    p_remove = sub.add_parser("remove", help="Deregister agent from agents.registry.json")
    p_remove.add_argument("--name", required=True)
    p_remove.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    dispatch = {
        "make":     cmd_make,
        "validate": cmd_validate,
        "diff":     cmd_diff,
        "onboard":  cmd_onboard,
        "list":     cmd_list,
        "inspect":  cmd_inspect,
        "remove":   cmd_remove,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
