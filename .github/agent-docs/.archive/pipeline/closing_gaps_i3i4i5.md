# Closing Prompts — GAP-I3, GAP-I4, GAP-I5

> Give each prompt to `@implement` in the sandbox workspace (`E:\Projects\agent-sandbox`).
> Run them in order: I3 → I4 → I5.
> Each ends with a commit. Run all 3 before merging to Customer360.

---

## GAP-I3 — Orchestrator proactive mode recommendation

**What to fix:** The orchestrator's §9 Intake Protocol currently classifies the scenario and routes, but says nothing about which pipeline mode to use. Users are left to figure it out themselves. Add a mode recommendation to every intake response.

**File to change:** `.github/agents/orchestrator.agent.md`

**Exact change — §9 Intake Protocol table:**

Replace the existing table:

```markdown
| Scenario | Entry stage | Auto-approved gates |
```

with an expanded table that adds a `Recommended mode` column and a `Mode rationale` column:

```markdown
| Scenario | Entry stage | Auto-approved gates | Recommended mode | Rationale |
```

Use these values for each row:

| Scenario | Recommended mode | Rationale |
|---|---|---|
| "I have an idea / new feature" | supervised | Unknown scope; gates protect against scope drift |
| "I have a PRD, need architecture" | supervised | Architecture decisions benefit from human review gates |
| "I have a plan, need implementation" | supervised | Multi-phase work; human oversight per phase |
| "Bug/hotfix — known root cause" | either | Safe: scope locked. Auto fine if confident, supervised if uncertain |
| "Bug/hotfix — unknown root cause" | supervised | Debug output may need human interpretation before implement |
| "Deferred items from pipeline-state.json" | auto | Scope pre-locked from previous run; low re-entry risk |

After the table, add this instruction block:

```markdown
**Mode recommendation output (required):**
After classifying the scenario, output this line before any routing action:

> **Recommended mode: `<supervised|auto>`** — <one-sentence rationale>
> To switch: say *"Switch pipeline to supervised mode"* or *"Switch pipeline to auto mode"*

Do not change `pipeline_mode` in `pipeline-state.json` yourself. Only the user switches mode via MCP tool or CLI. You recommend; they decide.
```

**Constraints:**
- Do not change any other section
- Do not modify the gate auto-approval logic
- Do not change §3.1 Pipeline Mode section

**Commit message:**
```
feat(orchestrator): GAP-I3 — add proactive mode recommendation to §9 Intake Protocol
```

---

## GAP-I4 — Pipeline halt notification and recovery protocol

**What to fix:** When the pipeline halts (blocked state, failed guards, gate unsatisfied, retry exhausted), the orchestrator has no structured protocol for: (1) explaining the block clearly to the user, (2) guiding recovery step-by-step, (3) resuming after the issue is fixed. Add §13 covering all 5 halt scenarios.

**File to change:** `.github/agents/orchestrator.agent.md`

**Exact change — add §13 after §12 Hotfix Mini-Pipeline:**

```markdown
---

### 13. Pipeline Halt & Recovery Protocol (GAP-I4)

When the pipeline-runner returns `blocked: true` or `pipeline-state.json` shows `blocked_by` is set, **STOP all routing** and surface the issue to the user immediately.

**Halt output format (always use this):**
```
⛔ Pipeline halted.
Reason: <blocked_by value from pipeline-state.json>
Stage: <current_stage>
Recovery path: see below
```

**Recovery paths by cause:**

| Cause | What to show user | Recovery action |
|---|---|---|
| Missing artefact (guard: `artefact_exists` failed) | "The artefact for stage `<stage>` does not exist at `<path>`." | User fixes the artefact → say *"Artefact is ready, resume pipeline"* → re-run `notify_orchestrator` |
| Artefact not approved (guard: `artefact_approved` failed) | "The artefact at `<path>` does not have `approval: approved` in its YAML header." | User adds approval header → say *"Artefact approved, resume pipeline"* |
| Gate unsatisfied | "Gate `<gate_name>` must be satisfied before advancing." | Review the gate content → say *"Approve <gate_name>"* → orchestrator calls `satisfy_gate` MCP tool |
| Tester retry budget exhausted (T-15) | "Tester has failed `<retry_count>` times (max: `<max_retries>`). Pipeline blocked." | User reviews failures → say *"Route to debug agent"* → orchestrator manually advances to debug stage |
| Blocking escalation exists | "A blocking escalation exists in `agent-docs/escalations/`. Pipeline cannot advance." | User resolves escalation → updates severity to `resolved` → say *"Escalation resolved, unblock pipeline"* → orchestrator clears `blocked_by` and re-runs runner |

**After user resolves the issue:**
1. Re-read `pipeline-state.json`
2. Clear `blocked_by: null`
3. Re-run `notify_orchestrator` or `pipeline-runner next` to recompute transition
4. If transition is now valid, proceed with routing (supervised button or auto invoke per `pipeline_mode`)
5. Commit updated `pipeline-state.json`

**Important:** All resumption must go through `@Orchestrator`. Agents must never self-resume.
```

**Constraints:**
- Do not modify §11 Tester Retry Loop or §12 Hotfix Mini-Pipeline
- §13 is additive only
- Keep the halt output format exactly as specified (user-facing text)

**Commit message:**
```
feat(orchestrator): GAP-I4 — add §13 Pipeline Halt & Recovery Protocol
```

---

## GAP-I5 — Mixed-intent decomposition

**What to fix:** When a user provides a message containing multiple pipeline items (e.g. "fix this bug, add this feature, update the DB schema, and fix the UI"), the orchestrator currently takes the first recognisable item and starts a pipeline for it. The rest is ignored. Required: parse all items, classify each, queue them, confirm with user before starting.

**File to change:** `.github/agents/orchestrator.agent.md`

**Exact change — replace §9 Intake Protocol with the expanded version below:**

Keep the existing table and gate logic intact. Add a **"Multi-item intake"** block at the end of §9, after the single-item table:

```markdown
### 9.1 Multi-Item Intake (GAP-I5)

If the user's message contains **more than one distinct work item**, do NOT start a pipeline immediately.

**Step 1 — Parse and classify every item:**

| Item | Classification | Reason |
|---|---|---|
| Bug / defect / broken behaviour | `hotfix` | Time-sensitive; fast-track pipeline |
| New feature / new capability | `feature` | Full pipeline required |
| UI fix / visual regression | `hotfix` (if post-close) or `feature` (if new design) | Depends on whether pipeline is open |
| DB change / schema / new table | `feature` | Design + plan required |
| Config change / infra tweak | `ad-hoc` | No pipeline — call devops/sql-expert directly |
| SQL query / data exploration | `ad-hoc` | No pipeline — call sql-expert or data-engineer directly |
| Refactor / tech debt | `feature` | Needs plan and review |

**Step 2 — Present the decomposed list to the user:**

```
I found N pipeline items in your request:

1. [hotfix] <item summary> → hotfix pipeline, starts at: implement|debug
2. [feature] <item summary> → feature pipeline, starts at: intent
3. [ad-hoc] <item summary> → no pipeline; I will call @<agent> directly

Suggested order: hotfixes first, then features.
Ad-hoc items I can handle now in parallel if you wish.

Shall I start with item 1?
```

**Step 3 — Wait for user confirmation before starting ANY pipeline.**

**Step 4 — Run one pipeline at a time.** Do not start item 2 until item 1 reaches `closed`.

**Step 5 — Ad-hoc items:** Handle ad-hoc items without pipeline init. Route directly to the appropriate specialist agent (sql-expert, devops, data-engineer, janitor) for that item only. Do not create or modify `pipeline-state.json` for ad-hoc work.

**What counts as "more than one distinct work item":**
- Two or more items that would each result in a separate commit
- Items that touch different codebases, services, or schemas
- A mix of hotfix + feature + ad-hoc in a single message

**What does NOT need decomposition:**
- A single hotfix with multiple DEF IDs (same pipeline, list in `_hotfix_brief`)
- A single feature with multiple phases (same pipeline, tracked in `current_phase`/`total_phases`)
```

**Constraints:**
- Do not remove or change the existing §9 single-item intake table
- §9.1 is additive — it activates only when multiple items are detected
- The existing gate auto-approval logic remains unchanged
- Do not modify any other section

**Commit message:**
```
feat(orchestrator): GAP-I5 — add §9.1 multi-item intake decomposition protocol
```
