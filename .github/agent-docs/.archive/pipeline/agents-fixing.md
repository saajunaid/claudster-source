# Agent Pool — Fix Instructions

**Date**: 2026-02-26
**Workspace**: `E:\Projects\agent-sandbox\.github\agents`
**Verified against**: actual agent files (grep-checked, not assumed)

Apply all fixes below to the junai agent pool. Read the Pipeline Context section fully before making any edits — it explains conscious design decisions so you do not accidentally undo intentional patterns.

---

## Before You Start — Read These Files

- `E:\Projects\agent-sandbox\.github\agents\anchor.agent.md` — primary target for most fixes
- `E:\Projects\agent-sandbox\.github\agents\orchestrator.agent.md` — pipeline source of truth
- `E:\Projects\agent-sandbox\.github\agents\code-reviewer.agent.md` — canonical reference for §9 Deferred Items template

---

## Pipeline Context — Conscious Design Decisions

**1. `next_agent` is a routing hint, not direct execution.**
The Orchestrator orchestrates all stage transitions by reading pipeline-state.json. `next_agent` in an Output Contract is a suggested default the Orchestrator may or may not follow depending on pipeline mode (supervised/assisted/autopilot) and approval gates. This is intentional — agents do not route to each other directly. The fix needed is NOT removing next_agent but making it conditional so the Orchestrator picks up the right signal.

**2. Universal Agent Protocols (§1–9) were added progressively via GAP fixes.**
GAP-001 through GAP-016 were applied over multiple sessions. Lightweight agents (accessibility, mentor, mermaid-diagram-specialist, project-manager, prompt-engineer, svg-diagram) predate the §8 Completion Reporting rollout. They are intentionally non-code-pipeline agents but still need §8 for consistency.

**3. Deferred Items Protocol (§9) was introduced as GAP-016.**
It was only propagated to agents updated at that time: `anchor` and `code-reviewer`. Orchestrator covers the same ground via its Pipeline Close Protocol (§10) — do not add §9 to orchestrator. All other 22 agents need §9 added. The canonical template is in `anchor.agent.md §9`.

**4. `validate_deferred_paths` is an Orchestrator-level tool (GAP-016 Pipeline Close).**
It is fully documented in `orchestrator.agent.md` only. It appears in the `tools:` list of `anchor.agent.md` and `implement.agent.md` as a copy-paste artifact — never documented in their bodies. Fix: add body-text instructions for both agents on when and how to call it.

**5. Model assignments are task-type-driven — not uniform across the pool.**
- `GPT-5.3-Codex` is correct for pure code-generation agents: `implement`, `streamlit-developer`, `frontend-developer`, `data-engineer`, `sql-expert`, `tester`, `janitor`, `devops`. Do NOT migrate these — Codex is the right choice for code output.
- `Claude Sonnet 4.6` is correct for reasoning-primary agents currently wrong on Codex: `code-reviewer` (judgment about code quality / security / intent) and `debug` (causality reasoning is 80% of the work; fix is secondary).
- `Claude Opus 4.6` is correct for highest-stakes judgment agents: `orchestrator`, `architect`, `plan`, `prd`, `anchor`, `security-analyst`. These do strategic reasoning, risk classification, and structured proof work where Opus depth is warranted.
- `Gemini 3.1 Pro` stays on `mermaid-diagram-specialist`, `svg-diagram`, `ui-ux-designer` — visual/diagram generation.
- **Only 3 model changes in this session**: anchor → Claude Opus 4.6, code-reviewer → Claude Sonnet 4.6, debug → Claude Sonnet 4.6.

**6. The §6 / §6.1 numbering structure is deliberate — do not change it.**
Every agent uses `### 6. Bootstrap Check` → `### 6.1 Routing Summary (Pipeline Awareness)` → `### 7.`. This is a consistent shared pattern across the entire pool, not a numbering bug. Do not modify it in any agent.

**7. Tester does NOT have a Deferred Items Protocol.**
A prior assessment incorrectly claimed it did. Verified: only `anchor.agent.md` and `code-reviewer.agent.md` have §9. Tester does not. The target count after Fix 7 is 23 agents with §9 (all 24 minus orchestrator).

---

## Verified Current State (grep-confirmed)

| What | Count | Details |
|------|-------|---------|
| Total agents | 24 | — |
| Have §8 Completion Reporting | 18 | — |
| Missing §8 | 6 | accessibility, mentor, mermaid-diagram-specialist, project-manager, prompt-engineer, svg-diagram |
| Have §9 Deferred Items | 2 | anchor, code-reviewer |
| Missing §9 | 22 | all others except orchestrator |
| Hardcoded `next_agent` | 7 agents | architect→plan, plan→implement, prd→architect, janitor→code-reviewer, devops→done, ux-designer→ui-ux-designer, anchor→tester |
| Model errors | 3 | anchor (Codex→Opus), code-reviewer (Codex→Sonnet), debug (Codex→Sonnet) |

> **Note**: `ui-ux-designer` DOES have §8 — do NOT modify it.

---

## Fixes to Apply

### Fix 1 — Correct model on 3 agents _(do this first — lowest risk, single-line changes)_

**`anchor.agent.md`**: `model: GPT-5.3-Codex` → `model: Claude Opus 4.6`
Anchor is reserved for highest-stakes work (security, hotfixes, DB migrations). 80% of its work is reasoning and judgment, not code generation. Opus depth is warranted. This is a deliberate exception — do not apply Opus to other agents.

**`code-reviewer.agent.md`**: `model: GPT-5.3-Codex` → `model: Claude Sonnet 4.6`
Code review is judgment, not generation. Codex produces code — it does not inherently reason about whether code is correct, secure, or aligned with intent.

**`debug.agent.md`**: `model: GPT-5.3-Codex` → `model: Claude Sonnet 4.6`
Causality reasoning (Phase 1–2) is 80% of debug work. The fix (Phase 3) is secondary. Codex is optimised for the minority part.

Leave all other Codex agents unchanged: `implement`, `streamlit-developer`, `frontend-developer`, `data-engineer`, `sql-expert`, `tester`, `janitor`, `devops`.

---

### Fix 2 — Anchor: Add rollback protocol to Phase 4
After the "fix them before proceeding" instruction in Phase 4 (Verify Against Baseline), add a **Rollback Protocol** sub-section:

- If regressions cannot be resolved after 2 fix attempts: stop, do not proceed
- For DB migrations: document the down-migration command in the Evidence Bundle before Phase 3 begins; if Phase 4 fails, execute the down-migration and record the revert in the Evidence Bundle
- For hotfixes: restore previous file state via git revert; document the revert hash in the Evidence Bundle
- In all cases: escalate to Orchestrator with `status: blocked` and reason

---

### Fix 3 — Anchor: Add DB schema baseline to Phase 1
Phase 1 (Capture Baseline) captures test/lint/import baselines. Add a **DB Schema Baseline** step:

- If the task involves any DB migration or schema change: run the schema inspection command and save output as part of the baseline snapshot
- Reference the schema baseline in the Evidence Bundle §Baseline section
- If schema cannot be captured, escalate before proceeding — do not run DB migrations without a baseline

---

### Fix 4 — Anchor: Add security-analyst to handoffs block
In the front matter handoffs block, add after the Debug entry:

```yaml
  - label: Security Review
    agent: Security Analyst
    prompt: Review the implementation above for security vulnerabilities, auth flows, and data exposure risks.
    send: false
```

---

### Fix 5 — Anchor: Make next_agent conditional in Output Contract
Replace the unconditional `next_agent: tester` with conditional routing logic:

- If task involved security-sensitive changes (auth, crypto, PII, session): `next_agent: security-analyst`
- Otherwise (standard hotfix, migration, refactor): `next_agent: tester`

Add a note below the table: "Orchestrator reads `task_type` and `security_sensitive` fields from the Evidence Bundle to determine the correct route."

---

### Fix 6 — Anchor + Implement: Document validate_deferred_paths in agent body
Both anchor.agent.md and implement.agent.md list `junai-mcp/validate_deferred_paths` in their tools: front matter but never instruct the agent to call it.

For **Anchor**: In §9 Deferred Items Protocol, after the YAML block, add:
"After completing the Evidence Bundle, call `validate_deferred_paths` to verify all deferred items are logged in pipeline-state.json before handing off to the Orchestrator."

For **Implement**: Add the same instruction in its deferred/completion section. If Implement has no §9 yet (it won't until Fix 7), add the validate_deferred_paths call instruction within the new §9 block added for Implement in Fix 7.

---

### Fix 7 — Add §9 Deferred Items Protocol to 22 agents

The following 22 agents are missing §9. Verify each file before editing:

`accessibility`, `architect`, `data-engineer`, `debug`, `devops`, `frontend-developer`, `implement`, `janitor`, `mentor`, `mermaid-diagram-specialist`, `plan`, `prd`, `project-manager`, `prompt-engineer`, `security-analyst`, `sql-expert`, `streamlit-developer`, `svg-diagram`, `tester`, `ui-ux-designer`, `ux-designer`

**Skip `orchestrator`** — its Pipeline Close Protocol (§10) is the equivalent mechanism.

Use this canonical template from `anchor.agent.md §9`:

```
### 9. Deferred Items Protocol

Any issues out-of-scope for this task but worth tracking:

```yaml
deferred:
  - id: DEF-001
    title: <short title>
    file: <relative file path>
    detail: <one or two sentences>
    severity: security-nit | code-quality | performance | ux
```
```

Insert after §8, before `## Output Contract` in each agent.

---

### Fix 8 — Add §8 Completion Reporting Protocol to 6 agents

The following 6 agents are missing §8:
`accessibility`, `mentor`, `mermaid-diagram-specialist`, `project-manager`, `prompt-engineer`, `svg-diagram`

Use the §8 block from any compliant agent (e.g. `implement.agent.md` or `tester.agent.md`) as the template. The heading must match exactly:

```
### 8. Completion Reporting Protocol (MANDATORY — GAP-001/002/004/008/009/010)
```

Insert between `### 7. Context Priority Order` and `## Output Contract` in each of the 6 agents.

---

### Fix 9 — Anchor: Scale Phase 1 timeout to task size
In Phase 1 where pytest timeout is set, replace flat `--timeout=120` with size-graduated values referencing the Phase 0 size classification:

- S tasks: `--timeout=60`
- M tasks: `--timeout=120`
- L tasks: `--timeout=300`

---

## Execution Order

Work in this sequence to minimise conflict risk:

1. **Fix 1** — 3 model lines (lowest risk, do first)
2. **Fix 3 + Fix 2** — Anchor Phase 1 DB baseline, Phase 4 rollback
3. **Fix 4 + Fix 5** — Anchor front matter handoff + Output Contract routing
4. **Fix 9** — Anchor Phase 1 timeout scaling
5. **Fix 8** — §8 to the 6 agents missing it
6. **Fix 7** — §9 sweep across 22 agents (largest change — do last)
7. **Fix 6** — `validate_deferred_paths` body docs in Anchor + Implement (after §9 is in place)

> If context fills up before completing Fix 7, stop after Fix 6 and handle Fix 7 in a follow-up prompt targeting only the remaining agents.

---

## Verification Commands

Run after all fixes are complete:

```powershell
cd "E:\Projects\agent-sandbox\.github\agents"

# Should return exactly 8 — the Codex agents staying on Codex
# If anchor, code-reviewer, or debug appear here that is an error
Select-String -Path "*.md" -Pattern "GPT-5.3-Codex" -SimpleMatch | Select-Object Filename, Line

# Should return 24 filenames
Select-String -Path "*.md" -Pattern "Completion Reporting Protocol" -SimpleMatch | Select-Object Filename | Sort-Object Filename

# Should return 23 filenames (all except orchestrator)
Select-String -Path "*.md" -Pattern "Deferred Items Protocol" -SimpleMatch | Select-Object Filename | Sort-Object Filename

# Confirm the 3 model corrections
Get-ChildItem *.md | ForEach-Object {
    $line = Get-Content $_.FullName | Select-String "model:" | Select-Object -First 1
    if ($line) { "$($_.Name): $($line.Line.Trim())" }
}
```

**Expected results:**
- GPT-5.3-Codex: 8 hits — implement, streamlit-developer, frontend-developer, data-engineer, sql-expert, tester, janitor, devops only
- §8: 24 files
- §9: 23 files (all except orchestrator)
- anchor → `Claude Opus 4.6`, code-reviewer → `Claude Sonnet 4.6`, debug → `Claude Sonnet 4.6`

---

## Hard Constraints — Do Not Violate

- Do NOT change the `model:` on any agent other than anchor, code-reviewer, debug
- Do NOT modify the `### 6. Bootstrap Check` / `### 6.1 Routing Summary` numbering — it is consistent across all agents by design
- Do NOT add §9 to `orchestrator.agent.md` — Pipeline Close Protocol (§10) is its equivalent
- Do NOT remove `next_agent` from any Output Contract — make it conditional, not absent
- Do NOT modify `ui-ux-designer.agent.md` — it already has §8 and is correct on model
- Do NOT add or remove any tools from any agent other than the specified `validate_deferred_paths` documentation in Anchor and Implement
- Do NOT change any other content beyond the specified fixes — if it is not mentioned in the fixes, it should be left as-is
- Do NOT add or modify any handoff entries in any agent other than the specified Security Analyst entry in Anchor
- Do NOT change any file names or paths — only the content within the specified agent markdown files
