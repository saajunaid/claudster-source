# Pipeline Reliability Program

> **Status**: Draft — Discussion document  
> **Scope**: junai agent pipeline system (25 agents, 9 MCP tools, 100+ skills)  
> **Goal**: Systematic hardening of the agentic pipeline to reduce silent failures, vocabulary drift, skill-loading misses, and ambiguity-driven rework

---

## Audit Summary

A full audit of all 9 core pipeline files (orchestrator, plan, anchor, implement, tester, code-reviewer, ARTIFACTS.md, pipeline-state.json, server.py) was conducted against 10 reliability categories. Verdicts:

| # | Category | Verdict | Section |
|---|----------|---------|---------|
| 1 | Artifact Contracts & Versioning | **PARTIALLY EXISTS** | §1 |
| 2 | Pre-flight Checks | **PARTIALLY EXISTS** | §2 |
| 3 | Post-phase Evidence Gates | **EXISTS (Anchor), PARTIAL (others)** | §3 |
| 4 | Ambiguity / Fallback Policy | **MISSING** | §4 |
| 5 | Safety Boundaries | **EXISTS** | §5 |
| 6 | Skill Auto-loading Policy | **PARTIALLY EXISTS** | §6 |
| 7 | Idempotency & Replay | **PARTIALLY EXISTS** | §7 |
| 8 | Vocabulary Normalization | **PARTIALLY EXISTS** | §8 |
| 9 | Observability & Traceability | **PARTIALLY EXISTS** | §9 |
| 10 | Pipeline Regression Testing | **PARTIALLY EXISTS** | §10 |
| 11 | Intent Integrity & Drift Prevention | **MISSING** | §11 |
**Key finding**: The pipeline has strong *prose-level* contracts (every agent has §8/§9, Output Contract tables, safety boundaries) but weak *enforcement* — nothing validates that agents actually produce what their contracts promise. The gap is between "documented expectation" and "verified delivery."

**Critical finding**: Vocabulary normalization (§8) and intent integrity (§11) are different problems that require different solutions. Vocabulary drift = agents using different *words* for the same concept (fixed by GLOSSARY.md). Intent drift = agents reinterpreting the *meaning* of what was designed (requires upstream document propagation + cross-reference verification). Intent drift is the #1 cause of "the agent built the wrong thing" and is NOT addressed by vocabulary fixes alone.

---

## Answers to Pre-Design Questions

### Q1: "I thought we already implemented artifact contracts — DRY check?"

**Yes, partially.** What already exists:
- Every agent has an Output Contract table (`artefact_path`, `required_fields`, `approval_on_completion`, `next_agent`)
- Orchestrator §2 Validate Artefact Contracts checks: file exists, approval header present, required fields non-empty
- ARTIFACTS.md tracks status: `current | superseded | archived | completed`
- `chain_id` (FEAT-YYYY-MMDD-slug) links all artifacts for a feature

**What's missing** (not DRY — genuinely new):
- Contracts are prose, not programmatically enforced (no JSON Schema, no Pydantic validation)
- No artifact-level versioning (plan v1, plan v2 — only `superseded` status)
- Orchestrator's §2 check is instructions-only — the MCP `notify_orchestrator` tool doesn't validate artifact contents
- No cross-agent contract compatibility check (e.g., "does Plan's output schema match what Implement expects as input?")

**Recommendation**: Don't build programmatic enforcement yet. Instead, strengthen the prose contracts with a **canonical field list** in one reference document, and add a lightweight MCP validation step. The current level is adequate for the pipeline's maturity — over-engineering is the real risk here.

### Q3: "Should evidence gates go in Orchestrator or remain in Anchor? How to resolve automatically?"

**Current state**: Anchor has a full 5-phase evidence protocol (baseline capture, pushback check, deliverables proof, regression comparison, evidence bundle). Other agents have lighter verification (Tester reports pass/fail counts, Code Reviewer runs tests optionally, Implement has test-before/after for L tasks only).

The original discussion identified **three layers of missing contractual glue** — Q3 must address all three, not just the evidence tier:

#### Layer 1: Auto Skill Policy (Agent-Level)

Every agent should have **mandatory trigger rules** that auto-load skills based on task signals — not just advisory "Load When Relevant" tables. This is the Frontend Developer detecting React work and auto-loading `react-best-practices/SKILL.md` without being told.

**Current state**: Only Anchor/Data Engineer/SQL Expert have mandatory triggers (for schema-migration). The other 22 agents have advisory-only skill tables.

**Fix**: Each agent gets a `### Mandatory Triggers` section with condition → skill mappings. The agent checks its task description against these conditions on startup and loads matching skills automatically.

#### Layer 2: Structured Phase Metadata (Plan-Level)

The Planner agent should produce **machine-readable phase metadata** for every phase it writes — not just prose instructions. Each phase specifies:

```markdown
## Phase N — {Title}

> **Agent**: `@implement`
> **Skills**: `coding/fastapi-dev/SKILL.md`, `coding/security-review/SKILL.md`
> **Evidence Tier**: `standard` | `anchor`
> **Acceptance Criteria**: [list of verifiable conditions]
```

This is what the Planner agent is currently NOT doing — it writes agent names in prose but doesn't prescribe skills or evidence requirements per phase.

#### Layer 3: Strict Propagation & Enforcement (Orchestrator-Level)

Orchestrator reads the Plan's phase metadata and **propagates it in the handoff payload**:

```json
{
  "handoff_payload": {
    "phase": 2,
    "assigned_agent": "implement",
    "required_skills": [".github/skills/coding/fastapi-dev/SKILL.md"],
    "evidence_tier": "standard",
    "acceptance_criteria": ["API returns 200 for valid input", "Input validation rejects invalid payloads"]
  }
}
```

On the return path, Orchestrator enforces what was prescribed:
- Did the specialist load the required skills? (check `_notes._skills_loaded[]`)
- Does the artifact meet the evidence tier? (Tier 1: artifact exists + fields present. Tier 2: anchor-evidence file with Baseline/Verification/Evidence Bundle sections)
- Are acceptance criteria addressed in the artifact?

**Why not push full evidence into Orchestrator**: Orchestrator is a router and validator, not an executor. It should ask "did you bring proof?" — not generate the proof itself. Evidence *generation* stays in Anchor (Tier 2) or in the specialist agent's validation step (Tier 1).

#### Evidence Tier Definitions

| Tier | Where evidence is generated | What Orchestrator checks on return | When Plan should prescribe it |
|------|------|-----------------|------|
| **Tier 1: Standard** | Specialist agent (tests pass, artifact complete) | Artifact exists, required fields present, approval status set | UI changes, documentation, standard features |
| **Tier 2: Anchor** | Anchor agent (5-phase protocol) | anchor-evidence file exists with `## Baseline`, `## Verification`, `## Evidence Bundle` sections | DB schema changes, security-critical code, infrastructure changes |

#### How It Resolves Automatically

The full chain: **Plan prescribes → Orchestrator propagates → Specialist loads/executes → Orchestrator verifies**

1. Plan writes phase metadata (agent, skills, evidence tier, acceptance criteria)
2. Orchestrator reads the plan, constructs handoff payload with these fields
3. Specialist agent receives handoff, loads required skills, does the work
4. Specialist reports completion via `notify_orchestrator`
5. Orchestrator checks: artifact meets evidence tier + acceptance criteria addressed
6. If checks pass → route to next phase. If not → block and request.

### Q4: "Ambiguity / Fallback Policy — define the best approach"

**Current state**: No defined protocol when an agent encounters ambiguity. Agents improvise — some ask questions, some make assumptions silently, some halt.

**Core principle: Never silently assume.** Even in autopilot, ambiguity should halt and ask — the cost of rework from a wrong assumption always exceeds the cost of a brief pause. Silent assumptions are the #1 cause of "the agent built the wrong thing."

**Recommended approach — Always-Halt Ambiguity Protocol with Choice UI**:

| Severity | All Modes (Supervised / Assisted / Autopilot) | Behavior |
|----------|-----------------------------------------------|----------|
| **Blocking** | HALT + ASK | Present the question with context. Block until user responds. |
| **Significant** | HALT + CHOICES | Present numbered options with pros/cons. User selects. Block until resolved. |
| **Minor** | HALT + CHOICES (with default) | Present options with a recommended default highlighted. User confirms or overrides. |

**Ambiguity classification**:
1. **Blocking** — Cannot proceed without answer, no reasonable default exists (e.g., "which database table?" when two candidates exist, "which API version to target?").
2. **Significant** — Multiple valid approaches, choice affects architecture or behavior (e.g., "REST vs GraphQL?", "pagination vs infinite scroll?").
3. **Minor** — Implementation detail with a reasonable default, but user should be aware of the choice (e.g., "ascending or descending sort default?", "UTC or local timezone for display?").

**Choice Presentation Format** (modeled after VS Code Copilot Planner agent):

When an agent encounters Significant or Minor ambiguity, it presents choices like this:

```markdown
**Decision needed**: {describe the ambiguity}

Context: {why this matters, what it affects}

1. **{Option A}** — {brief description}
   - Pros: {advantages}
   - Cons: {disadvantages}

2. **{Option B}** — {brief description}
   - Pros: {advantages}
   - Cons: {disadvantages}

3. **{Option C}** _(recommended)_ — {brief description}
   - Pros: {advantages}
   - Cons: {disadvantages}

> Select 1, 2, or 3 (or provide a different approach).
```

For Minor ambiguity with a clear default, the agent can use a shorter format:

```markdown
**Quick decision**: {describe the choice}

> Recommended: **{default option}** — {one-line rationale}
> Reply "ok" to accept, or specify an alternative.
```

**Recording**: Every resolved ambiguity is recorded in the artifact's `## Decisions` section:
```
DECISION: {what was decided} — CHOSEN: {option selected} — REASON: {user's rationale or "accepted default"} — SEVERITY: {blocking/significant/minor}
```

**Why always halt (even in autopilot)**: Autopilot means "don't require approval at every gate" — it does NOT mean "make design decisions on the user's behalf." An autopilot pipeline that silently chooses REST over GraphQL has produced output the user may not want. The pause for a choice selection is seconds; the rework from a wrong assumption is an entire pipeline re-run.

### Q9: "Safety boundaries — may be already there, but check"

**Confirmed: Already exists comprehensively.** No new work needed. Verified:
- Read-only mode enforcement (Plan, Code Reviewer, Orchestrator)
- Field ownership per agent in pipeline-state.json
- Secret refusal (hardcoded credential → STOP, suggest .env)
- Agent file patching HARD STOP (Orchestrator won't edit .agent.md)
- Scope restrictions (each agent writes only its own stage's fields) — documented as GAP-I2-c

**One minor gap**: No explicit "do not delete user files" boundary. Agents can theoretically `rm -rf`. This is low-risk (agents follow instructions) but worth adding as a one-line rule in the shared safety section.

### Q10: "Regression tests — should not interfere with code implementation pipeline"

**Current state**: `validate_agents.py` tests file structure + MCP smoke test. Pipeline-runner has `test_orchestrator_gaps.py` for transition logic. No end-to-end orchestration behavior tests.

**Recommended approach — Parallel Test Track**:

```
Code Pipeline:          Intent → PRD → Arch → Plan → Implement → Test → Review → Done
                                                                    ↑
                                                              (code-level tests)

Reliability Tests:      validate_agents.py (pre-publish gate, runs separately)
                        ├── Agent Structure Tests (existing)
                        ├── MCP Smoke Tests (existing)
                        ├── Contract Consistency Tests (new — §1)
                        ├── Vocabulary Consistency Tests (new — §8)
                        └── Routing Logic Tests (new — §10)
```

**Key principle**: Reliability tests run in `validate_agents.py` as a *pre-publish gate*, never inside the code implementation pipeline. They test the pipeline infrastructure (agent definitions, skill references, vocabulary consistency, contract compatibility) — not the user's application code.

**What to test** (additions to `validate_agents.py`):
1. All skill paths in agent files resolve to actual SKILL.md files
2. Output Contract required_fields are consistent across agent handoff chains
3. Vocabulary terms (artifact/artefact, phase/stage, etc.) follow canonical spelling
4. Every agent with read-only mode doesn't have write-capable tool references
5. MCP tool list matches expected count (already exists) + tool parameter smoke tests

---

## The 10 Reliability Workstreams

### §1 — Artifact Contract Registry (Strengthen Existing)

**What exists**: Prose contracts per agent, ARTIFACTS.md registry, Orchestrator §2 validation  
**What to add**:

1. **Canonical Contract Reference** — A single markdown file (`agent-docs/CONTRACT-REFERENCE.md`) that lists every stage's input/output contract in one place. Agents already define these individually; this just centralizes for cross-referencing.

   ```markdown
   ## Plan → Implement Handoff
   
   | Field | Type | Required | Description |
   |-------|------|----------|-------------|
   | chain_id | string | yes | FEAT-YYYY-MMDD-slug |
   | phases[] | array | yes | Ordered implementation phases |
   | phases[].agent | string | yes | Agent name to execute phase |
   | phases[].tasks[] | array | yes | Task list with acceptance criteria |
   | phases[].evidence_tier | enum | no | `standard` or `anchor` (default: standard) |
   | phases[].skills[] | array | no | Skills the assigned agent MUST load |
   ```

2. **Orchestrator Enforcement** — Add to Orchestrator §2: after checking artifact exists and has approval, also verify that `required_fields` from the contract reference are actually present (not just "non-empty" but structurally correct).

3. **Validation test** — In `validate_agents.py`, add a test that parses every agent's Output Contract table and verifies field names are consistent across the handoff chain.

4. **Revision tracking** — When an artifact is reworked (e.g., Implement reworks after Code Reviewer returns `revision-requested`), the agent that produces the replacement must:
   - Set the old ARTIFACTS.md row to `superseded` with `superseded_by: <new artifact path>`
   - Add a new row for the replacement artifact
   - Increment `_notes._revision_count[stage_name]` (new field) so the Orchestrator knows how many rework cycles have occurred

   This is NOT full version numbering (v1, v2, v3) — that was deliberately excluded as over-engineering (see Q1). It IS revision awareness: the pipeline knows "this is the 2nd attempt at the implement stage" which is critical for retry budget enforcement and observability.

**Effort**: Small — one reference doc + one validation test + a few lines in Orchestrator + revision tracking rules  
**Risk if skipped**: Agents silently produce incomplete artifacts; Orchestrator routes forward on an artifact that's missing fields the next agent needs. Rework loops have no audit trail.

---

### §2 — Pre-flight Checks (Extend Existing)

**What exists**: Orchestrator artifact validation, `project-config.md` bootstrap check  
**What to add**:

1. **Orchestrator pre-routing checklist** — Before routing to a specialist, verify:
   - `project-config.md` has a non-empty profile (existing check, just make it blocking)
   - The target agent's required skills exist on disk (new — catches renamed/deleted skills)
   - The handoff payload is well-formed (chain_id present, artifact path resolves)

2. **Planner agent pre-flight** — Before generating a plan, verify:
   - PRD artifact exists and is `current` in ARTIFACTS.md
   - Architecture artifact exists (if architectural work was done)
   - All agents referenced in planned handoffs exist as `.agent.md` files

**Effort**: Small — instructions-only additions to Orchestrator and Plan  
**Risk if skipped**: Agents are routed to work with invalid input; errors surface deep into implementation rather than at the gate

---

### §3 — Evidence Gate Tiers (Formalize Existing)

**What exists**: Anchor's 5-phase evidence protocol, Tester's structured result block, Code Reviewer's evidence-based review

**What to add**:

This workstream implements the three-layer contractual glue described in Q3. The full chain is: **Plan prescribes → Orchestrator propagates → Specialist loads/executes → Orchestrator verifies.**

1. **Tier definition** — Add to the Contract Reference (§1):
   ```
   evidence_tier: standard | anchor
   
   standard: artifact exists + approval set + required_fields present
   anchor: standard + anchor-evidence-*.md exists with Baseline, Verification, Evidence Bundle sections
   ```

2. **Planner agent metadata** — Plan MUST produce structured phase headers with `Agent`, `Skills`, `Evidence Tier`, and `Acceptance Criteria` for every phase. Not just prose — machine-readable metadata that Orchestrator can parse and propagate.

   ```markdown
   ## Phase N — {Title}
   > **Agent**: `@implement`
   > **Skills**: `coding/fastapi-dev/SKILL.md`, `coding/security-review/SKILL.md`
   > **Evidence Tier**: `standard`
   > **Acceptance Criteria**: [list of verifiable conditions]
   ```

   Default evidence tier by work type:
   - Database schema changes → `anchor`
   - Security-critical code → `anchor`
   - Infrastructure/deployment changes → `anchor`
   - UI-only changes → `standard`
   - Documentation → `standard`

3. **Orchestrator propagation** — Orchestrator reads the Plan's phase metadata and constructs the handoff payload with `required_skills`, `evidence_tier`, and `acceptance_criteria`. The specialist receives these in `_notes.handoff_payload` and acts accordingly.

4. **Orchestrator enforcement on return** — After a specialist reports completion:
   - Check the evidence tier that was prescribed for this phase
   - Tier 1 (standard): Verify artifact exists + required fields present + approval set
   - Tier 2 (anchor): Verify `agent-docs/anchor-evidence-*.md` exists with `## Baseline`, `## Verification`, `## Evidence Bundle` sections
   - Check that `_notes._skills_loaded[]` includes the required skills from the handoff
   - If any check fails → block and request, do not advance

5. **Specialist compliance** — Every specialist agent, on receiving a handoff with `required_skills`, loads them as the first action (before task work). On completion, writes `_notes._skills_loaded[]` for Orchestrator to verify.

**Effort**: Medium — Plan template update + Orchestrator §2 enhancement (propagation + return verification) + all specialist agents add skill loading compliance  
**Risk if skipped**: The three-layer chain breaks — Plan prescribes but nobody enforces, skills are missed, high-risk work gets lighter verification

---

### §4 — Ambiguity Resolution Protocol (New)

**What exists**: Nothing explicit  
**What to add**:

**Core principle**: Never silently assume — always halt and ask, all modes. Autopilot means auto-routing, not auto-deciding.

1. **Shared protocol section** — Add to every agent's §8 (next to Partial Completion Protocol):

   ```markdown
   ### Ambiguity Resolution Protocol
   
   When you encounter ambiguity in requirements, inputs, or context:
   
   1. **Classify**: Is this Blocking, Significant, or Minor?
      - Blocking: cannot proceed without answer (data source unknown, conflicting requirements)
      - Significant: multiple valid approaches, choice affects architecture or behavior
      - Minor: implementation detail with a reasonable default, but user should be aware
      
   2. **Always HALT and present choices** (all pipeline modes):
      
      | Severity | Action |
      |----------|--------|
      | Blocking | HALT + ASK — present the question with context, block until user responds |
      | Significant | HALT + CHOICES — present numbered options with pros/cons, user selects |
      | Minor | HALT + CHOICES (with default) — present options with recommended default highlighted, user confirms or overrides |
   
   3. **Choice presentation format**:
      
      For Significant ambiguity:
      > **Decision needed**: {describe the ambiguity}
      > Context: {why this matters}
      > 1. **{Option A}** — {pros/cons}
      > 2. **{Option B}** — {pros/cons}
      > 3. **{Option C}** _(recommended)_ — {pros/cons}
      > Select 1, 2, or 3 (or provide a different approach).
      
      For Minor ambiguity with clear default:
      > **Quick decision**: {describe the choice}
      > Recommended: **{default option}** — {one-line rationale}
      > Reply "ok" to accept, or specify an alternative.
   
   4. **Record**: Write all resolved decisions to your artifact's `## Decisions` section.
      Format: `DECISION: [what] — CHOSEN: [option] — REASON: [rationale] — SEVERITY: [level]`
   ```

2. **Orchestrator check** — After receiving an artifact, review `## Decisions` section. If decisions were made, surface the summary to the user before routing forward (gives a chance to catch any that need revisiting).

**Effort**: Small — template text added to agent §8 sections, one Orchestrator rule  
**Risk if skipped**: Agents silently make different assumptions across phases, leading to inconsistent implementation. In autopilot, wrong assumptions cause full pipeline re-runs.

---

### §5 — Safety Boundaries (Minor Hardening Only)

**What exists**: Comprehensive — read-only modes, field ownership, secret refusal, agent file patching HARD STOP, scope restrictions  
**What to add**:

1. **One-line addition to shared safety section**: "Do not delete files outside your artifact scope without explicit user approval."
2. **No other changes needed** — this category is well-covered.

**Effort**: Trivial  
**Risk if skipped**: Negligible (theoretical only)

---

### §6 — Skill Auto-Loading Policy (Major Gap)

**What exists**: Per-agent skill tables ("Load When Relevant"), one explicit auto-trigger rule (Anchor + schema-migration), _registry.md as human-readable index  
**What to add**:

This is the core architectural gap. The solution has three layers:

#### Layer 1: Agent-Level Skill Policy (Instructions Enhancement)

Each agent already has a skill table. Strengthen it:

```markdown
## Skills and Instructions

### Mandatory Triggers (auto-load when condition matches)
| Condition | Skill | Rationale |
|-----------|-------|-----------|
| Task involves React components | `frontend/react-best-practices/SKILL.md` | Framework-specific patterns |
| Task involves database schema changes | `data/schema-migration/SKILL.md` | Migration safety protocol |
| Task involves API endpoints | `coding/fastapi-dev/SKILL.md` | API standards |

### Advisory Skills (load when relevant)
| Task | Skill |
|------|-------|
| ... | ... |
```

The "Mandatory Triggers" section uses signal words that agents can pattern-match against their task description. This is the same approach used for schema-migration in Anchor/Data Engineer/SQL Expert.

#### Layer 2: Plan-Level Skill Prescription

Planner agent already specifies agent per phase. Extend to include skills:

```markdown
## Phase 2 — Backend API

> **Agent**: `@implement`
> **Skills**: `coding/fastapi-dev/SKILL.md`, `coding/security-review/SKILL.md`
> **Evidence Tier**: standard
```

When the Plan prescribes skills, the assigned agent MUST load them before starting work. This is enforceable through the handoff payload.

#### Layer 3: Orchestrator Propagation

When Orchestrator routes to a specialist, include skill requirements from the plan in `_notes.handoff_payload`:

```json
{
  "handoff_payload": {
    "required_skills": [
      ".github/skills/coding/fastapi-dev/SKILL.md",
      ".github/skills/coding/security-review/SKILL.md"
    ]
  }
}
```

The specialist agent, on receiving a handoff with `required_skills`, loads them as the first action — same as it already reads `project-config.md` today.

#### Validation Test

Add to `validate_agents.py`: verify all skill paths referenced in agent files resolve to actual `SKILL.md` files on disk. This catches renamed or deleted skills.

**Effort**: Medium-Large — all 25 agents need skill table review, Plan template update, Orchestrator handoff extension  
**Risk if skipped**: Agents miss critical skills → produce substandard work → caught late in review → rework

---

### §7 — Idempotency & Single-Stage Replay (Extend Existing)

**What exists**: `pipeline_reset` for full restart, stage drift recovery (§9.2 in Orchestrator), retry counts per stage  
**What to add**:

1. **New MCP tool: `replay_stage`** — Reset a single stage to `not_started` without clearing the entire pipeline. Parameters: `stage_name`, `reason`.

   Constraints:
   - Cannot replay a stage that is a dependency of a completed downstream stage (must replay the chain)
   - Sets `retry_count += 1`
   - Preserves `_notes` for continuity
   - Only available in supervised mode (too risky for autopilot)

2. **Stage snapshot** — Before each stage transition, `notify_orchestrator` writes the previous state to `_notes._stage_history[]` (append-only array). This gives replay context without needing git archaeology.

3. **Input snapshot for outcome consistency** — When Orchestrator constructs a handoff payload for a stage, it also writes a copy to `_notes._stage_inputs[stage_name]`. This is done during handoff construction (same place Orchestrator writes `_notes.handoff_payload` today). On replay, the replayed stage receives the *identical* input snapshot from `_stage_inputs`, not whatever `_notes.handoff_payload` has drifted to since then. This maximizes (but cannot guarantee — LLMs are non-deterministic) consistency between original run and replay.

4. **Replay output comparison** — After replay completes, Orchestrator must compare the new artifact against the original:
   - If downstream stages exist and consumed the original → warn user: "Downstream stages were based on the previous output. Re-run them or review for consistency."
   - If no downstream stages → proceed normally.
   - Write comparison to `_notes._replay_log[]`: `{"stage": "...", "replay_count": N, "changed_fields": ["..."], "downstream_impact": "none|review_needed"}`

**Effort**: Medium — one new MCP tool + notify_orchestrator enhancement + input snapshot logic  
**Risk if skipped**: When a stage produces bad output, the only recovery is full pipeline reset (lose all prior work). Replayed stages may produce inconsistent output with no way to detect the divergence.

---

### §8 — Vocabulary Normalization (Critical Gap)

**What exists**: Stage names are consistent. Most terminology is consistent. Spelling inconsistency (artifact vs artefact). Result status enums differ across agents.

**This is the most common problem in the pipeline today.** The fix is simple but requires discipline:

1. **Create `agent-docs/GLOSSARY.md`** — Single source of truth for all pipeline terminology:

   ```markdown
   # Pipeline Glossary
   
   Canonical terms used across all agents, skills, and pipeline infrastructure.
   When writing agent instructions, skills, or documentation, use ONLY these terms.
   
   ## Core Terms
   
   | Canonical Term | Definition | DO NOT USE |
   |---------------|------------|------------|
   | artefact | Any file produced by an agent as pipeline output | artifact, deliverable, output file |
   | stage | A pipeline phase (intent, prd, architect, plan, implement, tester, review, closed) | phase (in pipeline context), step |
   | phase | A subdivision of work within a Plan (Phase 1, Phase 2...) | stage (in plan context), step |
   | chain_id | Feature tracking ID: FEAT-YYYY-MMDD-slug | feature_id, tracking_id |
   | handoff | Transfer of work from one agent to another via Orchestrator | routing, delegation, dispatch |
   | evidence bundle | Anchor's structured proof-of-work document | proof, verification report |
   | gate | A checkpoint requiring approval before pipeline advances | checkpoint, approval point |
   | HARD STOP | Absolute refusal to proceed (security, out-of-scope, etc.) | halt, block, refuse |
   
   ## Result Statuses (per agent type)
   
   | Agent | Field | Values | Meaning |
   |-------|-------|--------|---------|
   | Tester | tester_result.status | passed, failed | All tests pass / any test fails |
   | Code Reviewer | verdict | approved, revision-requested | Code meets standards / needs changes |
   | Anchor | approval | approved, pending, blocked | Evidence complete / awaiting review / regressions found |
   | Implement | status | complete, partial, blocked | All tasks done / some done / cannot proceed |
   
   ## File Naming
   
   | Pattern | Example | Usage |
   |---------|---------|-------|
   | Agent file | `frontend-developer.agent.md` | Lowercase kebab-case matching name field |
   | Skill file | `.github/skills/{category}/{name}/SKILL.md` | Category folder + name folder + SKILL.md |
   | Plan file | `.github/plans/{feature-slug}.md` | Feature slug from chain_id |
   | Evidence file | `agent-docs/anchor-evidence-{feature}.md` | Per-feature evidence bundle |
   ```

2. **Vocabulary lint in `validate_agents.py`** — Scan all `.agent.md` files for blacklisted terms and flag them:
   - "artifact" (should be "artefact")
   - "phase" when referring to pipeline stages (should be "stage")
   - "step" when referring to plan phases (should be "phase")

3. **Agent instruction update** — Add to every agent's §6 Bootstrap:
   ```
   Read `agent-docs/GLOSSARY.md` for canonical terminology. Use only the terms defined there.
   ```

**Effort**: Small-Medium — one glossary doc + one validation check + one-line addition to 25 agents  
**Risk if skipped**: Vocabulary drift is cumulative — each agent's output becomes slightly harder for the next agent to parse, leading to misinterpretation and rework

---

### §9 — Observability & Traceability (Extend Existing)

**What exists**: `_notes._routing_decision` (latest only), `_notes.latest_result`, per-agent routing summary on startup  
**What to add**:

1. **Routing history** — Add a NEW field `_notes._routing_history[]` as a sibling to the existing `_notes._routing_decision`. Do NOT replace `_routing_decision` — it must remain as a single object because every agent and Orchestrator §1 reads it as `_routing_decision.blocked`, `_routing_decision.to_stage`, etc. The new field is append-only:
   ```json
   {
     "_routing_decision": { "blocked": false, "from_stage": "plan", "to_stage": "implement", ... },
     "_routing_history": [
       {"timestamp": "...", "from": "plan", "to": "implement", "reason": "..."},
       {"timestamp": "...", "from": "implement", "to": "tester", "reason": "..."}
     ]
   }
   ```
   In `notify_orchestrator`: after writing `_routing_decision` (existing behavior), also append the same object to `_routing_history[]`.

   **Rotation policy**: Cap `_routing_history[]` at 50 entries. When full, drop the oldest 10 entries. This prevents unbounded growth in `pipeline-state.json` during long pipeline runs.

2. **Skill loading trace** — Each agent, when loading a skill, appends to `_notes._skills_loaded[]`:
   ```json
   {"agent": "frontend-developer", "skill": "frontend/react-best-practices/SKILL.md", "trigger": "mandatory-react-component"}
   ```
   This is instructions-only (agents write to _notes), no MCP change needed.

   **Graceful fallback for verification**: If an agent forgets to write `_skills_loaded[]`, Orchestrator warns but does NOT block. Blocking on a missing trace field (not a missing skill) would be a false positive — the agent may have loaded the skill correctly but failed to record it. Log the gap and continue.

3. **Session summary** — At stage completion, each agent writes a structured completion record to `_notes.latest_result` (already exists) plus a one-line entry to `_notes._stage_log[]` (new):
   ```json
   {"stage": "implement", "result": "complete", "duration_approx": "1 session", "decisions_count": 2, "skills_loaded": 3, "intent_refs_verified": true}
   ```

4. **Golden Path & Exception Path Design**

   Define what a *healthy* pipeline run looks like vs. a *failing* one, so Orchestrator can detect when it's off-track:

   **Golden Path** (expected sequence for a standard feature):
   ```
   intent → prd → architect → plan → [implement → tester]×N phases → review → closed
   ```
   Each transition produces: artifact at expected path, approval set, required fields present, no unresolved decisions, no blocked stages.

   **Exception Paths** (known failure modes with defined recovery):

   | Exception | Detection | Recovery |
   |-----------|-----------|----------|
   | Stage produces artifact but validation fails | Orchestrator return-path check | Block, request re-work from same agent |
   | Agent halts mid-task (Partial Completion) | Agent reports DONE vs NOT DONE | Resume with fresh session, same stage |
   | Agent drifts from intent (intent verification fails) | §11 Intent Verification Protocol detects divergence | Block, show divergence to user, re-route to same agent with correction |
   | Tester fails after 3 retries | Retry budget exhausted | Route to Debug agent (autopilot) or halt (supervised) |
   | Replay produces different output | §7 replay output comparison | Warn user, flag downstream stages for review |
   | Pipeline state corruption | Stage mismatch in `notify_orchestrator` | §9.2 Stage Drift Recovery protocol |
   | Unrecognized ambiguity (agent doesn't realize it's drifting) | §11 cross-reference mandate catches divergence at next gate | Block, surface to user with source doc vs. artifact comparison |

   **Orchestrator path awareness**: On every routing decision, Orchestrator writes `_notes._current_path: "golden"` or `_notes._current_path: "exception:{type}"`. This is a one-field addition that makes it instantly visible whether the pipeline is on-track or in recovery mode.

**Effort**: Small-Medium — MCP append logic + instructions-only agent additions + golden/exception path definitions  
**Risk if skipped**: When pipeline produces bad output, root-cause analysis requires reading git history of pipeline-state.json — slow and unreliable. No way to distinguish a healthy pipeline from one silently drifting off course.

---

### §10 — Pipeline Regression Testing (Extend validate_agents.py)

**What exists**: `validate_agents.py` with agent structure checks + MCP 9-tool smoke test  
**What to add** (as new test functions in the same file):

1. **Skill Reference Resolution Test**
   - Parse every `.agent.md` file for skill paths
   - Verify each path resolves to an actual `SKILL.md` file
   - Flag broken references

2. **Contract Consistency Test**
   - Parse Output Contract tables from every agent
   - Verify that downstream agents' expected inputs match upstream outputs
   - Flag mismatched field names

3. **Vocabulary Lint Test**
   - Scan all `.agent.md` files for blacklisted terms from GLOSSARY.md
   - Report violations with file, line number, and suggested replacement

4. **Read-Only Agent Tool Audit**
   - For agents declared read-only (Plan, Code Reviewer, Orchestrator), verify their YAML `tools:` list doesn't include write-capable tools
   - Flag violations

5. **Handoff Cross-Reference Test** (already exists, extend)
   - Current: checks if handoff `agent:` names resolve to files
   - Add: check that handoff `prompt:` text mentions the expected artifact path

**Effort**: Medium — 4-5 new test functions in existing file  
**Risk if skipped**: Structural drift accumulates silently between publishes; errors only surface when a user hits a broken pipeline path

---

### §11 — Intent Integrity & Drift Prevention (New — Critical Gap)

**What exists**: GAP-I1 Fidelity Check (checks *coverage* — "did you address every requirement?"). No mechanism to check *fidelity* ("did you interpret each requirement correctly?").

**This is the #1 cause of "the agent built the wrong thing."** Vocabulary normalization (§8) fixes agents using different *words*. Intent integrity fixes agents assigning different *meanings* to the same words.

**The problem in detail**: Architect writes "implement a caching layer for API responses." Plan breaks this into "Phase 3: Implement cache." Implement agent reads "implement cache" and builds an in-memory Python dict — because it never read the Architecture doc that specified Redis and explained why (TTL requirements, multi-process sharing). The task was *covered* (cache exists) but the *intent* was lost (wrong type of cache).

**Root cause**: Agents work from the *immediate* handoff context (Plan task description), not from the *full intent chain* (PRD → Architecture → Plan → task). Each handoff is a lossy compression of the upstream intent.

**Fix — Four mechanisms**:

#### 11a. Intent Chain (upstream documents travel with the task)

Every Plan phase must include an **intent reference** section that links back to the source documents:

```markdown
## Phase 3 — API Caching Layer

> **Agent**: `@implement`
> **Skills**: `coding/caching-patterns/SKILL.md`
> **Evidence Tier**: `standard`
> **Intent References**:
>   - Architecture: `docs/architecture/agentic-adr/ADR-feature.md` §4.2 (Caching Decision)
>   - PRD: `docs/prd/prd.md` NFR-3 (Response time < 200ms under load)
> **Design Intent**: Use Redis as a shared cache layer with 15-min TTL to meet NFR-3. NOT in-memory caching (multi-process requirement from Architecture §4.2).
```

The **Design Intent** field is the Planner agent's one-sentence summary of *what the upstream documents actually mean for this phase*. This is the critical bridge — it forces the Plan to interpret the Architecture explicitly, rather than leaving interpretation to the Implement agent.

Orchestrator propagates `intent_references` and `design_intent` in the handoff payload, same as `required_skills`.

#### 11b. Cross-Reference Mandate (agent verifies interpretation before working)

Every specialist agent, on receiving a phase with `intent_references`, MUST:

1. **Read the referenced documents** (Architecture section, PRD requirement) before starting work
2. **Verify understanding** — write a 2-3 sentence interpretation in the artifact:
   ```markdown
   ## Intent Verification
   **My understanding**: This phase implements a Redis-based API response cache with 
   15-minute TTL, accessed via a shared connection pool. This satisfies NFR-3 (sub-200ms 
   responses) and aligns with Architecture §4.2 (multi-process shared state requirement).
   ```
3. **Flag divergence** — if the agent's interpretation conflicts with the `design_intent` from the Plan, HALT and surface the conflict to the user:
   ```markdown
   **Intent conflict detected**:
   - Plan says: "Redis cache with 15-min TTL"
   - My analysis suggests: "In-memory cache would be simpler and sufficient for single-process deployment"
   - Architecture §4.2 says: "Multi-process requirement mandates shared cache"
   
   > The Architecture document supports the Plan's Redis approach. Proceeding with Redis.
   ```
   If the conflict cannot be resolved from the documents alone → HALT + present choices to user (§4 Ambiguity Protocol).

#### 11c. Intent Verification Gate (Orchestrator checks on return)

When a specialist completes a phase that had `intent_references`:

1. Orchestrator verifies the artifact contains an `## Intent Verification` section
2. If missing → block: "Phase had intent references but artifact has no Intent Verification section. Re-read the source documents and verify your implementation matches the design intent."
3. If present → surface the interpretation to the user for quick confirmation before routing forward (in supervised/assisted mode)

This is lightweight — the Orchestrator doesn't judge whether the interpretation is *correct* (it can't — it's not an executor). It only checks that the specialist *did the verification* and gave the user a chance to catch drift.

#### 11d. Drift Detection Across Phases (cumulative check)

At the end of multi-phase implementation (before routing to Tester), Orchestrator performs a **cumulative intent audit**:

1. Collect all `## Intent Verification` sections from all phase artifacts
2. Collect all `## Decisions` sections from all phase artifacts
3. Present a summary to the user:
   ```markdown
   **Pre-test Intent Summary** (Phases 1–4):
   
   | Phase | Design Intent | Agent Interpretation | Decisions Made |
   |-------|--------------|---------------------|----------------|
   | 1 | Data models per PRD §3 | Models created matching ERD | None |
   | 2 | REST API with auth per Arch §4.1 | FastAPI + JWT auth implemented | Chose RS256 over HS256 (user selected) |
   | 3 | Redis cache per Arch §4.2 | Redis with 15-min TTL | None |
   | 4 | Dashboard per PRD §5 | Streamlit dashboard | Sort order: descending (user confirmed) |
   
   > Review the above. Reply "ok" to proceed to testing, or flag any phase for re-work.
   ```

This is the last chance to catch intent drift before the code is tested and reviewed. It takes seconds to scan and catches the "I didn't realize Phase 3 was supposed to use Redis" problem.

**Hotfix exception**: If `pipeline-state.json` has `"type": "hotfix"`, hotfixes have no PRD or Architecture doc — there are no `intent_references` to verify. Skip §11b (Cross-Reference Mandate) and §11c (Intent Verification Gate) for hotfix pipelines. §11a and §11d are also skipped since the Planner agent is bypassed in hotfix flow.

**Effort**: Medium — Plan template update (intent references + design intent) + all specialist agents add cross-reference mandate + Orchestrator adds intent verification gate + cumulative audit  
**Risk if skipped**: This is THE risk. Without intent integrity, every other reliability improvement (contracts, skills, evidence, vocabulary) can be mechanically perfect and still produce the wrong output. The pipeline passes all gates but delivers something the user didn't ask for.

---

## Implementation Phasing

### Wave 1 — Foundation (Low effort, high impact)

| Item | Workstream | What | Est. Files Changed |
|------|-----------|------|--------------------|
| 1a | §8 Vocabulary | Create `agent-docs/GLOSSARY.md` | 1 new file |
| 1b | §8 Vocabulary | Add glossary reference to all agents' §6 Bootstrap | 25 agents |
| 1c | §4 Ambiguity | Add Ambiguity Resolution Protocol to all agents' §8 | 25 agents |
| 1d | §5 Safety | Add file deletion boundary to shared safety section | 25 agents (one line each) |
| 1e | §10 Testing | Skill reference resolution test in `validate_agents.py` | 1 file |
| 1f | §11 Intent | Add Intent Chain (intent_references + design_intent) to Plan template | 1 agent (plan) |

**Impact**: Fixes the most common problem (vocabulary drift), adds the most missing protocol (ambiguity), starts intent tracking at the Plan level, and adds the first automated pipeline test.

### Wave 2 — Contracts & Enforcement (Medium effort, high impact)

| Item | Workstream | What | Est. Files Changed |
|------|-----------|------|--------------------|
| 2a | §1 Contracts | Create `agent-docs/CONTRACT-REFERENCE.md` | 1 new file |
| 2b | §3 Evidence | Define evidence_tier in Plan template | 1 agent (plan) |
| 2c | §6 Skills | Add Mandatory Triggers table to all agents | 25 agents |
| 2d | §6 Skills | Add required_skills to Plan phase template | 1 agent (plan) |
| 2e | §11 Intent | Add Cross-Reference Mandate to all specialist agents | 20+ agents |
| 2f | §10 Testing | Contract consistency + vocabulary lint tests | 1 file |

**Impact**: Closes the skill-loading gap, formalizes the contract chain, and embeds intent verification at the agent level.

### Wave 3 — Observability & Replay (Medium effort, medium impact)

| Item | Workstream | What | Est. Files Changed |
|------|-----------|------|--------------------|
| 3a | §9 Observability | Routing history (append-only array with rotation) | 1 file (server.py) |
| 3b | §9 Observability | Skill loading trace instructions (graceful — warn, don't block) | 25 agents |
| 3c | §7 Replay | `replay_stage` MCP tool + input snapshot + output comparison | 1 file (server.py) |
| 3c.1 | §10 Testing | Add `replay_stage` to `EXPECTED_MCP_TOOLS` in `validate_agents.py` | 1 file |
| 3c.2 | §7 Replay | Update `pipeline-state.template.json` with new `_notes` fields (see Mock Test M3) | 1 file |
| 3d | §2 Pre-flight | Skill file existence check in Orchestrator | 1 agent |
| 3e | §9 Observability | Golden path / exception path definitions + `_current_path` field | 1 agent (orchestrator) |
| 3f | §10 Testing | Read-only tool audit + handoff cross-reference extension | 1 file |

**Impact**: Makes the pipeline debuggable, adds single-stage recovery with consistency safeguards, and distinguishes healthy runs from drifting ones.

### Wave 4 — Plan-to-Agent Integration (Larger effort, systemic impact)

| Item | Workstream | What | Est. Files Changed |
|------|-----------|------|--------------------|
| 4a | §6 Skills | Orchestrator adds `required_skills[]` + `evidence_tier` to `handoff_payload` via `update_notes` MCP tool during handoff construction (M14 fix: `update_notes` replaces `editFiles` for all `_notes.*` writes) | 1 agent (orchestrator) |
| 4b | §3 Evidence | Orchestrator enforces evidence_tier from plan on return (read from `handoff_payload`, not from Plan artifact — see M17) | 1 agent (orchestrator) |
| 4c | §6 Skills | All specialist agents check `handoff_payload.required_skills` on entry + write `_skills_loaded[]`. **19 agents need NEW handoff_payload reading code; 5 need no-Accepting-Handoffs section created first** (see M15/M16) | 24 agents (all except orchestrator) |
| 4d | §9 Observability | Session summary log entry in §8 completion report. `intent_refs_verified` defaults to `null` until Wave 5 enables intent references (see M19) | 24 agents |

**Impact**: Full plan-to-execution contract: Plan prescribes → Orchestrator propagates → Specialist loads → Evidence verifies. Note: 4a and 5c should be combined as a single Orchestrator handoff extension edit (required_skills + evidence_tier + intent_references + design_intent all go into the same `handoff_payload` construction step).

### Wave 5 — Intent Integrity Enforcement (Medium effort, highest-value impact)

| Item | Workstream | What | Est. Files Changed |
|------|-----------|------|-----------|
| 5a | §11 Intent | Orchestrator intent verification gate: check `## Intent Verification` exists on return — only when `handoff_payload.intent_references` is non-empty (guard against early-pipeline stages — see M21) | 1 agent (orchestrator) |
| 5b | §11 Intent | Orchestrator cumulative intent audit: insert pre-tester conditional in §3 routing — when `_routing_decision.next_stage == 'tester'`, collect all `## Intent Verification` sections and present summary before handoff (see M22 for trigger mechanism) | 1 agent (orchestrator) |
| 5c | §11 Intent | Orchestrator adds `intent_references[]` + `design_intent` to `handoff_payload` via `update_notes` MCP tool — combined with 4a as single handoff extension (M14/M23 fix) | 1 agent (orchestrator) |
| 5d | §11 Intent | Post-Plan specialist agents write `## Intent Verification` section in artifacts — ~12 agents (implement, tester, code-reviewer, security-analyst, debug, anchor, streamlit-dev, frontend-dev, data-engineer, sql-expert, devops, accessibility). PRD/Architect/Plan/KT/Prompt-Engineer/Mermaid/SVG excluded — they run before intent references exist (see M24) | ~12 agents |

**Impact**: Closes the intent drift loop — the #1 cause of "the agent built the wrong thing." Full chain: Plan declares intent → Orchestrator propagates → Specialist verifies interpretation & implements → Orchestrator checks verification exists → cumulative audit before testing. Note: 5b requires a conditional insertion in Orchestrator §3 routing logic ("if next_stage == tester, audit first").

---

## What This Program Does NOT Include

1. **Programmatic schema validation (Pydantic/JSON Schema for artifacts)** — Over-engineering at current scale. Prose contracts with automated lint checks are sufficient.
2. **Runtime agent behavior testing** — Cannot test LLM behavior deterministically. Test the infrastructure (file structure, contracts, vocabulary) instead.
3. **Automated skill discovery/injection** — Too complex for current architecture. Manual skill tables + validation tests catch 90% of issues at 10% of the complexity.
4. **Pipeline state migration tooling** — Not needed yet; `pipeline_version` field exists for future use.
5. **Multi-pipeline concurrency** — Out of scope; current design is single-pipeline-per-workspace.
6. **Deterministic LLM output guarantees** — LLMs are inherently non-deterministic. §7 replay maximizes consistency via input snapshots but cannot guarantee identical output. Accept this as a fundamental constraint.

---

## Known Trade-offs & Gotchas

Issues that the program deliberately introduces or cannot fully resolve. These are accepted trade-offs, not bugs.

| Trade-off | Why it exists | Mitigation |
|-----------|---------------|------------|
| **Always-halt ambiguity breaks autopilot flow** | §4 halts on every ambiguity, even in autopilot. Autopilot is only hands-free for unambiguous work. | Deliberate — the cost of one wrong assumption exceeds the cost of pausing. Autopilot still auto-routes between stages; it just doesn't auto-decide design choices. |
| **Skill loading trace is best-effort** | §9 agent may load a skill but forget to write `_skills_loaded[]`. Orchestrator warns but doesn't block. | Blocking on a missing *trace* (not a missing *skill*) would be a false positive. Logging the gap is sufficient. |
| **Replay may produce different output** | §7 LLMs are non-deterministic. Same input → similar but not identical output. | Input snapshot ensures identical prompts. Output comparison + downstream impact warning catches divergence. User decides whether to accept. |
| **`_routing_history[]` has a size cap** | Capped at 50 entries to prevent `pipeline-state.json` bloat. Old entries are dropped. | For long pipeline runs (5+ features), early routing decisions are lost. Reconstruct from git history if needed. Acceptable trade-off. |
| **Intent verification adds friction** | §11 requires agents to read upstream docs and write `## Intent Verification`. This adds work to every phase. | The friction is the point — forcing agents to verify interpretation before working is cheaper than discovering drift after implementation. |
| **Cumulative intent audit pauses before testing** | §11d adds a user review step between implementation and testing. | Quick scan (seconds). Catches drift that would otherwise require a full pipeline re-run to fix. |

### Potential Race Conditions

| Scenario | Risk | Mitigation |
|----------|------|------------|
| **Concurrent `_notes` writes** | ~~In autopilot, an agent writing `_notes._skills_loaded[]` while `notify_orchestrator` writes `_notes._routing_history[]` could cause a read-modify-write conflict on `pipeline-state.json`.~~ | **RESOLVED**: `update_notes` MCP tool created. Orchestrator §5/§8 updated to route ALL `_notes.*` writes through MCP. The MCP server is now the single authoritative writer for `pipeline-state.json`. Agents call `update_notes({"_skills_loaded": [...]})` instead of `editFiles`. Sequential pipeline execution + single MCP writer eliminates the race. |
| **Plan references stale Architecture doc** | If Architecture doc is updated after Plan is written but before implementation, the Plan's `intent_references` point to outdated sections. | Plan holds `artefact` status `current` — if Architecture is superseded, Orchestrator should detect the mismatch during pre-flight (§2). Add explicit check: "Do the intent_references still point to `current` artifacts?" |
| **Replay resets stage but downstream already consumed original** | §7 `replay_stage` resets a stage. If downstream stages completed based on original output, they're now based on stale data. | §7 dependency-chain constraint prevents replaying upstream without replaying downstream. Output comparison warns about divergence. |
| **GLOSSARY.md and agent vocabulary diverge over time** | Someone edits an agent file and uses the wrong term. No runtime enforcement. | §10 vocabulary lint test catches this at publish time. The gap between edit and publish is accepted — same as any linting approach. |

---

## Success Metrics

After full implementation (all 4 waves), measure:

| Metric | Baseline (estimated) | Target |
|--------|---------------------|--------|
| Skill loading misses per pipeline run | 2-3 | 0 (mandatory triggers + plan prescription catch them) |
| Vocabulary inconsistencies per publish | ~10-15 | 0 (lint gate in validate_agents.py) |
| Silent assumption rework | Unknown (not tracked) | 0 blocking assumptions in autopilot; all documented |
| Broken skill references | Unknown | 0 (pre-publish test catches them) |
| Time to diagnose routing issues | Minutes (git archaeology) | Seconds (routing history array) |
| Pipeline reset frequency | ~1 per complex feature | Reduced via single-stage replay |
| Intent drift incidents per feature | ~1-2 (the #1 pain point) | 0 (intent chain + cross-reference mandate + cumulative audit) |
| Unrecognized ambiguity (agent didn't realize it was drifting) | Unknown | Caught at intent verification gate or cumulative audit |

---

## Mock Test Report — Compatibility Verification

> **Method**: Walked every wave item against the actual pipeline files (25 agents, server.py, validate_agents.py, pipeline-state.template.json, ARTIFACTS.md). Verified structural insertion points, field conflicts, behavioral contradictions, and tool compatibility.
> **Baseline**: All 25 agents pass `validate_agents.py`. MCP smoke test (9 tools) passes.

### Verdicts

| # | Finding | Severity | Wave | Status |
|---|---------|----------|------|--------|
| M1 | `_routing_history` vs `_routing_decision` ambiguity | **FAIL → FIXED** | 3a | §9 text clarified: `_routing_decision` stays as single object; `_routing_history[]` is a NEW sibling field. Original text said "change from single-object to array" which would break every agent reading `_routing_decision.blocked`. |
| M2 | `replay_stage` tool not in `EXPECTED_MCP_TOOLS` | **FAIL** | 3c | Adding a new MCP tool means `EXPECTED_MCP_TOOLS` in `validate_agents.py` must be updated (9 → 10 tools). The smoke test flags unexpected tools: `unexpected = registered - EXPECTED_MCP_TOOLS`. **Action**: Wave 3c must include updating `validate_agents.py` `EXPECTED_MCP_TOOLS` set. |
| M3 | `pipeline-state.template.json` missing new `_notes` fields | **FAIL** | 3-5 | Waves add `_routing_history[]`, `_skills_loaded[]`, `_stage_history[]`, `_stage_inputs{}`, `_replay_log[]`, `_stage_log[]`, `_current_path`, `_revision_count{}`. None exist in template. `pipeline_init` creates states from template — agents appending to missing arrays need fallback. **Action**: Add empty defaults to template OR require agents to use `setdefault()` pattern. Recommend template update — cheaper and safer. |
| M4 | Plan template gets 6 new fields across Waves 1-2 | **WARN** | 1f+2b+2d | Current plan phase has: agent assignment, tasks, deliverables. After Waves 1-2: Agent, Skills, Evidence Tier, Acceptance Criteria, Intent References, Design Intent. Major template restructuring needed — implement 1f, 2b, 2d together as a single Plan template update, not three separate edits. |
| M5 | Hotfix pipeline has no `intent_references` | **WARN → FIXED** | 5 | §11 requires intent_references in every phase, but hotfixes bypass Plan/PRD/Architecture. Added explicit hotfix exception: skip §11b/c/d for `type: hotfix`. |
| M6 | `_notes` unbounded growth (7+ new array fields) | **WARN** | 3-5 | Current `_notes` has 4 keys. After all waves: 11+ keys, several are arrays. Only `_routing_history[]` has a rotation policy (50-cap). **Action**: Apply same 50-cap rotation to `_stage_history[]`, `_replay_log[]`, `_stage_log[]`. `_skills_loaded[]` and `_stage_inputs{}` reset naturally on `pipeline_init`. |
| M7 | §8 is "Completion Reporting Protocol" in 24/25 agents | **WARN** | 1c | Orchestrator §8 is "What You Do NOT Do" (different). Adding "Ambiguity Resolution Protocol" inside §8 works for 24 agents but needs special placement for Orchestrator. **Action**: For Orchestrator, add Ambiguity Protocol to a different section (§8 doesn't contain protocols). |
| M8 | Architect + Implement have no explicit Output Contract fields | **WARN** | 2a | Architect has no formal Output Contract table with `required_fields`. Implement's Output Contract says `src/**` (code committed) with optional impl-notes. CONTRACT-REFERENCE.md (§1/Wave 2a) will need to CREATE contract definitions for these agents, not just centralize existing ones. |
| M9 | Artifact versioning not in any wave | **GAP → FIXED** | 1 | Q1 identified "no artifact-level versioning" but recommended against full v1/v2 numbering. Added revision tracking to §1: agents update ARTIFACTS.md on rework + increment `_notes._revision_count[stage_name]`. Not full versioning — just rework awareness. |
| M10 | `_stage_inputs` snapshot timing ambiguous | **GAP** | 3c | §7 says "when a stage starts, snapshot the handoff payload." But MCP has no `stage_started` event — only `notify_orchestrator` for completion. **Resolution**: Orchestrator writes `_notes._stage_inputs[target_stage]` during handoff construction (§5.1 equivalent). The Orchestrator already writes `handoff_payload` before routing — snapshot is a copy of that payload keyed by stage name. |
| M11 | Cross-Reference Mandate vs context window pressure | **WARN** | 2e | §11b requires agents to read upstream docs (Architecture, PRD sections) before working. Large Architecture docs consume context. The `design_intent` one-liner in Plan is the lightweight bridge — but the mandate says "read the referenced documents." **Mitigation**: Mandate should say: "Read the specific section referenced in `intent_references` (e.g., Architecture §4.2), not the entire document. The `design_intent` field is your summary — the referenced section is your verification source." |
| M12 | Only Anchor has Mandatory Triggers today | **INFO** | 2c | 24 of 25 agents have MT:NO. Wave 2c must create Mandatory Triggers tables for all 24 remaining agents. Large effort but straightforward — condition/skill/rationale mapping per agent based on their domain. |
| M13 | Orchestrator has no Partial Completion Protocol | **INFO** | — | Orchestrator (PCP:NO) and Plan (PCP:NO by name, but has HARD STOP). These are routers/planners, not executors — PCP is less relevant. No action needed. |

### Wave 4 Findings (M14–M20)

| # | Finding | Severity | Wave Item | Details |
|---|---------|----------|-----------|---------|
| M14 | `handoff_payload` written via `editFiles` — split-brain with MCP server | **FAIL → FIXED** | 4a | §5 explicitly permitted `editFiles` for `_notes.*`, but the MCP server also writes `_notes.latest_result` and `_notes._routing_decision` via `notify_orchestrator`. Two concurrent writers to the same JSON file is a split-brain risk. **Root cause**: `editFiles` for `_notes.*` was an inception-era pattern that got codified as "intended" in §5/§8. No MCP tool existed for `_notes.*` writes besides what `notify_orchestrator` handles internally. **Fix applied**: Created `update_notes` MCP tool (server.py). Updated Orchestrator §5 to route `_notes.*` through `update_notes`, removed `_notes.*` from the editFiles MAY list, added `_notes.*` to the MUST-use-MCP table. Updated §8 HARD STOP to cover `_notes.*`. Orchestrator now calls `update_notes({"handoff_payload": {...}})` instead of using `editFiles`. MCP server is now the **single authoritative writer** for `pipeline-state.json`. Tool count: 9 → 10. `validate_agents.py` `EXPECTED_MCP_TOOLS` updated. |
| M15 | Only 6 of 25 agents read `handoff_payload` today | **FAIL** | 4c | 4c says "all agents check `handoff_payload.required_skills` on entry." But today only implement, tester, code-reviewer, plan, anchor, and orchestrator reference `handoff_payload`. The remaining 19 agents have no `handoff_payload` reading code. **Action:** 4c must CREATE the `handoff_payload` reading step in 19 agents, not just add a `required_skills` check. This is a larger effort than stated ("25 agents" understates it — 19 need new sections, 6 need modifications). |
| M16 | 6 agents have no "Accepting Handoffs" section at all | **WARN** | 4c | `anchor`, `data-engineer`, `devops`, `mermaid-diagram-specialist`, `orchestrator`, `ui-ux-designer` have no `## Accepting Handoffs` section. 4c needs to CREATE this section in 6 agents before adding `required_skills` checking logic. Orchestrator is excluded (it's the router, not a specialist), leaving 5 agents needing a new section. |
| M17 | `evidence_tier` has no storage field in pipeline-state | **WARN** | 4b | Orchestrator enforces `evidence_tier` from plan (4b), but `evidence_tier` isn't stored in `pipeline-state.json`. Orchestrator must read it from the Plan artifact each time. If the Plan artifact is modified between stages, the evidence tier could be inconsistent. **Mitigation:** Store `evidence_tier` per stage in `_notes.handoff_payload` (alongside `required_skills`). This makes it immutable for replay (§7). |
| M18 | `_skills_loaded[]` is agent-written but array is Wave 3 infrastructure | **WARN** | 4c+3 | 4c says agents write `_skills_loaded[]` for Orchestrator to verify. But `_skills_loaded[]` is created in the template by Wave 3 (M3). If Wave 4 is implemented without Wave 3, agents append to a non-existent array. **Already covered by Wave 3 prerequisite** — documenting for clarity. |
| M19 | Session summary (4d) isn't in any existing agent section | **WARN** | 4d | 4d adds a "session summary log entry" with `intent_refs_verified` field. This goes in §8 Completion Reporting Protocol. But the current CRP structure across 24 agents is: checklist → commit → update state → output report → HARD STOP. Adding a structured summary log between commit and output is clean. However: `intent_refs_verified` assumes §11 intent references exist (Wave 5). **Action:** Wave 4d depends on Wave 5d unless we make `intent_refs_verified` an optional field that defaults to `null` when no intent references were propagated. |
| M20 | 5 agents call `notify_orchestrator`; 20 don't | **INFO → RESOLVED** | 4d | Only anchor, frontend-developer, implement, orchestrator, and ui-ux-designer call `notify_orchestrator` today. The session summary log (4d) should be part of the completion report output (agent's final message), not an MCP call. For `_skills_loaded[]` writes to `pipeline-state.json`, agents call `update_notes({"_skills_loaded": [...]})` — same MCP tool created for M14 fix. No need to extend `notify_orchestrator` or use `editFiles`. Agents that need `update_notes` get it added to their frontmatter `tools:` list in Wave 4c. |

### Wave 5 Findings (M21–M25)

| # | Finding | Severity | Wave Item | Details |
|---|---------|----------|-----------|---------|
| M21 | Orchestrator §2 has exactly 3 checks; 5a adds a 4th | **WARN** | 5a | Current §2 checks: (1) file exists, (2) YAML `approval: approved`, (3) `required_fields` present. 5a adds: (4) `## Intent Verification` section exists. This is clean — it's additive. But the check only applies when `intent_references` were propagated in the handoff. Must include a guard: "If `handoff_payload.intent_references` is non-empty, check `## Intent Verification` exists. If no intent references were propagated, skip this check." Without the guard, early-pipeline stages (PRD, Architect) that run before intent references exist will be blocked. |
| M22 | Cumulative intent audit (5b) has no trigger event | **FAIL** | 5b | §11d says Orchestrator does a cumulative audit "before routing to Tester." But routing to Tester is determined by `_routing_decision` from the pipeline-runner. Orchestrator reads `_routing_decision` and executes it (§3). There's no "pre-tester hook" — routing is: runner says "next=tester" → Orchestrator routes. **Action:** 5b must insert a conditional check in §3: "If `_routing_decision.next_stage == 'tester'`, perform cumulative intent audit BEFORE presenting the handoff. In supervised mode, present the summary table and wait for user 'ok'. In assisted/autopilot mode, log the summary to `_notes._stage_log[]` and proceed." This is the insertion point — after reading `_routing_decision`, before executing the handoff. |
| M23 | 5c duplicates 4a's payload propagation pattern | **WARN → RESOLVED** | 5c | 5c says "Orchestrator propagates `intent_references` + `design_intent` in handoff payload." This is the same pattern as 4a (`required_skills` in handoff payload). With the M14 fix (`update_notes` MCP tool), both 4a and 5c use the same mechanism: `update_notes({"handoff_payload": {...}})`. **Action:** Combine 4a + 5c into a single Orchestrator handoff extension: `required_skills[]`, `evidence_tier`, `intent_references[]`, and `design_intent` all go into one `update_notes` call during handoff construction. |
| M24 | 20 artifact-producing agents need `## Intent Verification` | **WARN** | 5d | The sub-agent identified 20 agents that produce artifacts (all except orchestrator, mentor, project-manager, janitor, and one borderline). But the `## Intent Verification` section only makes sense for agents that receive `intent_references` — upstream agents (PRD, Architect) won't have them because they run before the Plan creates intent references. **Effective scope:** Only agents that run AFTER the Plan stage need `## Intent Verification`: implement, tester, code-reviewer, security-analyst, debug, anchor, streamlit-developer, frontend-developer, data-engineer, sql-expert, devops, accessibility. That's ~12 agents, not 20+. PRD, Architect, Plan, Knowledge-Transfer, Prompt-Engineer, Mermaid, SVG are excluded. |
| M25 | Wave 5 dependency on Wave 1f + 2e is absolute | **INFO** | 5a-5d | Wave 5 assumes: (1) Plan includes `intent_references` and `design_intent` per phase (Wave 1f), (2) agents have Cross-Reference Mandate (Wave 2e). Without these, there are no intent references to propagate and no mandate to verify. Wave 5 is completely inert without Waves 1-2 foundation. This is already stated but worth re-emphasizing: skipping to Wave 5 is impossible. |

### Wave-by-Wave Compatibility Summary

| Wave | Items | Conflicts Found | Breaking? | Notes |
|------|-------|-----------------|-----------|-------|
| **Wave 1** | 1a-1f | M4 (plan template coordination), M7 (Orchestrator §8 different) | No | All insertion points exist. 1a/1e are new files. 1b/1c/1d are one-line additions to existing sections. 1f is a Plan template extension. |
| **Wave 2** | 2a-2f | M4 (coordinate with 1f), M8 (create missing contracts), M11 (context pressure), M12 (24 agents need MT tables) | No | Largest effort wave. No structural breaks — all changes are additive instructions + one new file. |
| **Wave 3** | 3a-3f | M1 (FIXED), M2 (update EXPECTED_MCP_TOOLS), M3 (update template), M6 (array caps), M10 (snapshot timing) | **M2 and M3 are breaking if missed** | Wave 3 is the riskiest — it modifies server.py (MCP tools) and adds new pipeline-state fields. Must update validate_agents.py and template in the same commit. |
| **Wave 4** | 4a-4d | M3 (template fields), M6 (array caps), M14 (FIXED), M15-M20 (see below) | **M15 is breaking if missed** | Depends on Wave 3 infrastructure. M14 `update_notes` MCP tool already implemented. 19 agents need new entry section (4c). |
| **Wave 5** | 5a-5d | M5 (FIXED), M11 (context pressure), M21-M25 (see below) | **M22 is breaking if missed** | Orchestrator §2 gets new validation logic (5a), cumulative audit has no trigger event (M22), and 20 artifact-producing agents need new output section (5d). |

### Required Template Update (Wave 3 prerequisite, extended for Waves 4-5)

`pipeline-state.template.json` must add these fields to `_notes` before Wave 3 implementation. Fields marked with wave number indicate when they become active:

```json
"_notes": {
  "handoff_payload": null,
  "_routing_decision": null,
  "_hotfix_brief": null,
  "_routing_history": [],
  "_skills_loaded": [],
  "_stage_history": [],
  "_stage_inputs": {},
  "_replay_log": [],
  "_stage_log": [],
  "_current_path": "golden",
  "_revision_count": {},
  "_intent_audit_log": []
}
```

| Field | Wave | Purpose |
|-------|------|---------|
| `_routing_history[]` | 3a | Append-only routing decision log (50-cap) |
| `_skills_loaded[]` | 3b/4c | Skills loaded by current agent (reset per stage) |
| `_stage_history[]` | 3c | Pre-transition state snapshots (50-cap) |
| `_stage_inputs{}` | 3c | Input snapshot per stage for replay (keyed by stage name) |
| `_replay_log[]` | 3c | Replay outcome records (50-cap) |
| `_stage_log[]` | 3e/4d | Session summary entries per stage completion |
| `_current_path` | 3e | `"golden"` or `"exception"` — current execution path |
| `_revision_count{}` | 2a | Rework count per stage (keyed by stage name) |
| `_intent_audit_log[]` | 5b | Cumulative intent verification summaries (pre-tester) |

### Artifact Versioning Assessment

**Q: Is artifact versioning already taken care of?**

**Partially.** Here's the full picture:

| Mechanism | Exists Today | Added by Program | Covers |
|-----------|-------------|-----------------|--------|
| ARTIFACTS.md 4-state status (`current`, `superseded`, `archived`, `completed`) | ✅ Yes | — | Artifact lifecycle tracking |
| `superseded_by` field in ARTIFACTS.md | ✅ Yes (manual) | Formalized in §1 | Replacement chain tracking |
| `chain_id` linking all artifacts for a feature | ✅ Yes | — | Feature-level artifact grouping |
| Explicit version numbers (v1, v2, v3) | ❌ No | ❌ Deliberately excluded | Per-artifact version comparison |
| Revision count per stage (`_revision_count[stage_name]`) | ❌ No | ✅ Added to §1 (Wave 2a) | Rework loop awareness ("this is the 2nd attempt") |
| Contract field consistency validation | ❌ No | ✅ Added to §1 (Wave 2) + §10 | Cross-agent field compatibility |

**Why no version numbers**: The pipeline is sequential — at any point, there's exactly one `current` artifact per stage. When an artifact is reworked, the old one becomes `superseded` and the new one becomes `current`. Version numbers would only help for historical comparison ("what did the plan say in v1 vs v3?"), which is available via git history. Adding a separate versioning system adds complexity without solving a real pipeline problem.

**What the program adds instead**: Revision count (`_revision_count`) tracks HOW MANY TIMES a stage has been reworked, which is what the pipeline actually needs — retry budget enforcement, observability ("implement has been reworked 3 times, something is wrong"), and audit trail.

---

## Next Steps

0. ~~**Infrastructure pre-req**: Create `update_notes` MCP tool, update Orchestrator §5/§8 to route `_notes.*` through MCP, update `validate_agents.py` EXPECTED_MCP_TOOLS (9→10)~~ — **DONE** (M14 fix)
1. Review this document and the Mock Test Report (M1-M25) — identify any items to deprioritize or reorder
2. Approve Wave 1 scope
3. Begin implementation (Wave 1 is primarily documentation + one test function + Plan template — fast to ship)
4. After Wave 1: validate with a real pipeline run before proceeding to Wave 2
5. **Before Wave 3**: Update `pipeline-state.template.json` with new `_notes` fields (see Required Template Update above)
6. **Before Wave 4**: Create `## Accepting Handoffs` section in 5 agents that lack it (anchor, data-engineer, devops, mermaid-diagram-specialist, ui-ux-designer) — see M16
7. **Wave 4+5 optimization**: Combine 4a and 5c into a single Orchestrator handoff extension using `update_notes` MCP tool (all new payload fields in one call) — see M14, M23
8. **Before Wave 5b**: Design the pre-tester conditional hook in Orchestrator §3 routing logic — see M22
