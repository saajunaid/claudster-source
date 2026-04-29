---
name: golden-plan
context: fork
description: "USE THIS SKILL whenever a user asks for a comprehensive implementation plan, a full-stack build plan, a UI+backend plan, or says 'create a plan for building X' where X spans multiple phases or systems. Also activate when the user says 'plan this project', 'I need a detailed plan', 'build plan', 'implementation plan', or attaches a mockup/wireframe and asks how to build it. Produces a zero-ambiguity, evidence-gated plan with self-contained per-phase prompts, exhaustive data binding tables, per-phase validation checklists, and a global quality gate. Evidence-gated: will not write a single phase until it has verified or asked for required artefacts (mockup, data sample, API contract, scaffold inventory). Dual-mode: generic by default, junai-pipeline only when explicitly requested. Agent-agnostic — any agent with read/search/edit tools can use this skill."
---

# Golden Plan

## When to Use

Activate this skill when the request is for a **comprehensive implementation plan** that involves:

- 8 or more phases across a project
- Full-stack work (backend + frontend or data + UI)
- Complex data binding between a backend and a UI (JSON → React, API → Streamlit, etc.)
- A visual reference (HTML mockup, Figma, screenshot) that must be matched pixel-for-pixel
- Multiple agents executing different phases in sequence

Do NOT use for:
- Simple bug fixes or single-file changes (use `large-task-fidelity.instructions.md` alone)
- Exploratory plans with vague scope (use `brainstorming/SKILL.md` first to harden scope)
- Plans that only touch one system in isolation with no data binding (use `docs/writing-plans/SKILL.md`)

---

## Execution Mode (Required first step)

Before Phase 0, explicitly choose an execution mode:

- **Mode A — `generic` (default):** no junai pipeline assumptions, no orchestrator routing requirements, works with default Copilot/default agents.
- **Mode B — `junai-pipeline` (opt-in):** include orchestrator/stage-routing conventions and pipeline artefact conventions.

If the user does not explicitly request junai pipeline, use `generic`.

---

## Phase 0 — Evidence Gathering (REQUIRED before writing any plan content)

Before writing a single phase, you MUST gather and validate evidence. Do not produce plan output until the evidence gate is satisfied.

Run through the checklist below. For each item, determine its tier:

- **BLOCKER** — Plan cannot proceed without this. Stop and ask the user for it.
- **WARNING** — Plan can proceed but the affected phases will have noted assumptions. Inform the user what you are assuming.
- **OPTIONAL** — Nice to have. Note its absence but proceed.

### Evidence Checklist

#### E1 — Visual Reference
- Does a mockup, wireframe, HTML prototype, or screenshot of the target UI exist?
- If yes: what file/path? Is it frozen (will not change during implementation)?
- **Tier:** BLOCKER for UI-heavy plans. WARNING for backend-only plans.

#### E2 — Live Data Sample
- Is there a real data sample (JSON file, CSV, DB query result) representative of production data?
- Does it reflect the CURRENT schema (not a stale sample)?
- Can field names be read directly from it (avoid field name guessing)?
- **Tier:** BLOCKER for plans with any data binding. WARNING if schema is defined elsewhere (Pydantic DTOs, TypeScript interfaces).

#### E3 — API / Backend Contract
- Are endpoints already defined (routes, method, request params, response shape)?
- Do typed DTOs exist (Pydantic models, TypeScript interfaces)?
- Is the serialization convention documented (camelCase vs snake_case)?
- **Tier:** BLOCKER for full-stack plans. WARNING if backend and frontend are built in the same plan (contract will be defined during planning itself — mark those sections clearly as `[DEFINED IN THIS PLAN]`).

#### E4 — Existing Scaffold Inventory
- What is already built? (List files, packages, installed dependencies.)
- What must NOT be recreated or deleted?
- What needs overhauling vs net-new creation?
- **Tier:** BLOCKER. Without this, the plan will generate conflicting or duplicate code.

#### E5 — Technology Decisions
- Is the tech stack finalised? (Charts library, state management, routing, test runner, animation, etc.)
- Are any decisions still open?
- **Tier:** BLOCKER for phases that depend on the decision. Open decisions must be flagged as `[TECH-DECISION OPEN]` in affected phases.

#### E6 — Scope Boundary
- What is explicitly in v1 vs deferred to a future release?
- Are any data fields known to be empty/missing in v1 (dispatch issues, schema gaps, etc.)?
- **Tier:** WARNING. Missing scope boundary causes unbounded implementations.

#### E7 — Agent / Skill Availability
- Which agents will execute phases? (Or default: `@Implement` for code phases, `@Tester` for test phases.)
- Are the domain skills referenced in phase prompts present on disk? (Verify paths before listing.)
- **Tier:** OPTIONAL. Skill paths that do not exist should be omitted from phase prompts — do not list phantom skills.

#### E8 — Output Destination
- Where should the plan file be saved? (Default: `.github/plans/<feature-slug>.md`)
- Is there a `chain_id` to use? (Format: `FEAT-YYYY-MMDD-{slug}`)
- **Tier:** OPTIONAL. Default path is used if not specified.

---

### Evidence Gate Decision

After running the checklist:

1. **All BLOCKERs satisfied** → Proceed to Phase 1 (Pre-flight Scan).
2. **Any BLOCKER missing** → Load `.github/skills/workflow/asking-questions/SKILL.md` and follow its question structure (numbered questions, multiple-choice options, fast-path `defaults` reply). Do not generate any plan content yet. Example:

   ```
   EVIDENCE GATE — BLOCKED

   Before I can write this plan, I need a few things. Reply with answers
   or `defaults` to accept my assumptions.

   1) Live data sample (E2):
      a) [path/to/sample.json] — I'll read it directly
      b) Point me to the Pydantic DTO / TypeScript interface file instead
      c) Not available yet — assume from field names in the mockup

   2) Existing scaffold location (E4):
      a) [path/to/frontend/] — I'll inventory it
      b) Not built yet — plan will be greenfield
      c) Not sure — use default (greenfield)

   Once these are answered I will produce the full plan.
   ```

3. **WARNINGs present** → Proceed, but note each WARNING at the top of Context & Decisions with an `⚠️ ASSUMPTION:` callout.

---

## Phase 1 — Pre-flight Scan

Before writing any phase content, produce a **pre-flight summary** in this exact format:

```
## Pre-Flight Scan

Phase 0  — Context & Decisions:              reference section, depends on none
Phase 1  — [Name]:                           ~N tasks, depends on [phases or "none"]
Phase 2  — [Name]:                           ~N tasks, depends on [phases]
...
Phase N  — [Name]:                           ~N tasks, depends on [phases]
```

Commit to an expected task count per phase. Do not start writing phase content until this is complete. The pre-flight is your contract with yourself — use it to enforce equal depth across phases.

---

## Phase 2 — Plan Construction

Write the plan to the output file. Follow this template **in full**. Do not omit sections. Do not merge sections. Do not use shorthands.

---

### Plan Template

```markdown
# Plan: [Project Name] — [Sub-title e.g. "React UI Build" or "Backend API + Data Pipeline"]

> **Updated:** YYYY-MM-DD
> **Status:** READY FOR EXECUTION
> **Execution mode:** `generic` <!-- or `junai-pipeline` -->
> **Visual reference:** [path to mockup or "N/A"]
> **Data source:** [path to canonical data sample or "See E3 — API Contract section"]
> **Output destination:** [path where plan is saved]
> **Execution:** Manual — one agent session per phase. See protocol below.

---

## Pre-Flight Scan

[Paste output from Phase 1 — Pre-flight Scan here]

---

## Manual Execution Protocol

Each phase runs in a **separate chat session**. After each phase, return for
validation before starting the next.

- In **`generic` mode**, use normal chat + selected agent(s) directly.
- In **`junai-pipeline` mode**, follow orchestrator routing and stage sequencing.

**Per-phase workflow:**
1. Open a new chat session with the agent named in the phase header
2. Load the skills listed under **Skills to load** — tell the agent:
   "Read these SKILL.md files before starting: [paths]"
3. Attach the files listed under **Files to attach**
4. Also attach this plan file
5. Paste the **Phase Prompt** exactly as written — it is self-contained
6. When the agent finishes, run the commands in the **Validation Checklist**
7. Return to advisory chat, share checklist results + errors. Get a green light before proceeding

**Drift rule:** If a bug or gap is found after Phase N, fix it in the same session before
starting Phase N+1. Never carry debt forward.

**Large-task fidelity:** Agents implementing large phases must follow
`.github/instructions/large-task-fidelity.instructions.md`.

---

## 0. Context & Decisions

### What this plan builds
[2-4 sentences — what the user will have when all phases are complete]

### ⚠️ Assumptions
[List any E-tier WARNINGs from evidence gathering here. If none, write "None — all evidence verified."]

### Technology decisions

| Concern | Decision | Rationale |
|---------|----------|-----------|
| [e.g. Charts library] | [decision] | [one-line reason] |
| ... | ... | ... |

### Data parity assumptions

List every data domain and its v1 availability:

| Domain / Tab | Data availability | Strategy |
|---|---|---|
| [e.g. Executive Overview] | ✅ Real data | Live API |
| [e.g. Geography] | ⚠️ Array always `[]` in v1 | Live API + empty state with explanation |
| [e.g. Modem platform] | ❌ 0% populated | Full empty state (do not build chart) |

### Existing scaffold (do NOT recreate)

| Path | Purpose | Status |
|------|---------|--------|
| [path] | [what it is] | [keep / overhaul / extend] |

### Files to modify (not create)

| File | What changes | Risk of regression |
|------|-------------|-------------------|
| [path] | [description of change] | [low / medium / high — and why] |

### API contract

Only include if the backend exists or is being defined in this plan:

| Endpoint | Method | Params | Response type | Notes |
|----------|--------|--------|---------------|-------|
| `/api/v1/[resource]` | GET | `period: string` | `[TypeName]` | [serialization notes, e.g. camelCase] |
| ... | ... | ... | ... | ... |

---

[Then repeat the following block for EACH PHASE]

## Phase N — [Name]

**Agent:** `@[AgentName]`
**Objective:** [One sentence — what this phase produces. No implementation detail here.]

### Skills to load

Tell the agent to read these SKILL.md files before starting:
[Only list skills whose paths you have VERIFIED exist on disk]
- `.github/skills/[category]/[name]/SKILL.md` — [one-line description]

### Instructions to follow

- `.github/instructions/[name].instructions.md`

### Files to attach

[All files the agent needs as context to execute this phase]
- `[path]`

### Phase Prompt

[SELF-CONTAINED, COPY-PASTE PROMPT — includes all context needed to execute the phase
without reading any other document. Structure:]

```
You are implementing Phase N ([Name]) of the [project name].
Read `[plan file path]` Phase N section in full before making any changes.

PRINCIPLES: [TDD / KISS / YAGNI / DRY / Readability — adjust per phase]

SKILLS TO READ FIRST (load these SKILL.md files):
- [paths]

INSTRUCTIONS TO FOLLOW:
- [paths]

[CRITICAL context the agent needs to NOT make common mistakes — e.g.
"The API already returns camelCase. Do NOT add a key transformation layer."
"client.ts already exists — do NOT recreate it."
"types/nps.ts has all interfaces — import from there, do not re-declare."]

Deliverables (in order):
1. [Specific deliverable — file path + what it exports]
2. [Specific deliverable]
...

When done, run every item in the Validation Checklist and report each result explicitly.
Do not mark done unless all items pass. If any fail, fix and re-verify.
```

### What to build

[For EACH deliverable: write the complete spec with full code/config/values.
NO "similar to above". NO "same as Phase N". NO "...". EVERY deliverable fully spelled out.]

#### N.1 [Deliverable name]

**File:** `[exact path]`

[Full interface/type definitions, implementation spec, code where exact values matter.
If the code is the spec — write the code. Do not describe code, write it.]

#### N.2 [Deliverable name]
[...]

### Validation Checklist — Phase N complete when

[SPECIFIC, VERIFIABLE assertions — not "does it work?" but exact checks:]
- [ ] `npm run build` succeeds (or `python -m pytest` depending on stack)
- [ ] [Specific file] exists and exports [specific symbol]
- [ ] [Specific behavior] renders/returns [specific value]
- [ ] [Known empty state] returns graceful message, no crash
- [ ] Dark mode: [specific component] renders correctly
- [ ] Zero [hardcoded colors / any types / console.log / etc.]

---

[After all phases, include these three mandatory reference sections:]

## Data Binding Reference

Maps every UI component to its exact data source path. All implementing agents must
consult this before wiring any component to data.

### DB-[SECTION] — [Section Name e.g. "App Shell", "Tab 1 — Overview"]

| UI Element / Component | Data path | Type | Notes |
|-----------------------|-----------|------|-------|
| [component] | `[json.field.path]` | `type` | [e.g. camelCase, derived, always [] in v1] |

[Repeat DB-[SECTION] for each logical section / tab / page]

---

## Derived Values Reference

Values computed client-side. NOT present in the raw data. All implementing agents must
derive these — never fetch them as separate API calls.

| Value name | Formula | Used by |
|-----------|---------|---------|
| [e.g. MoM delta] | `currentValue - previousValue` | [component list] |
| [e.g. YTD avg] | `mean(all non-null values in series)` | [component list] |

---

## Quality Gates

Every component across all phases must pass these gates before the plan is considered done:

- [ ] Zero hardcoded colours — always CSS variable tokens or named constants
- [ ] Zero hardcoded data inside components — all data flows from props or hooks
- [ ] TypeScript strict mode — no `any` type anywhere (or Python typing — no untyped params)
- [ ] All empty states render without errors when arrays are `[]` or data is `null`
- [ ] Dark mode: all components render correctly (if applicable)
- [ ] No `console.log` statements in production code
- [ ] No unused imports
- [ ] `npm run build` (or equivalent) produces zero warnings
- [ ] All tests pass
[Add project-specific gate items here]
```

---

## Phase 3 — Self-Sweep (Mandatory Final Step)

After completing the plan document, re-read the **last 40% of the output** before delivering it.

Search for these decay signals:

| Pattern | Example |
|---------|---------|
| `\.{3,}` (ellipsis) | `// ... same for other tabs` |
| `same pattern` | `same pattern as Phase 2` |
| `as above` | `as above for remaining endpoints` |
| `\betc\b\.?` | `deriveYtd, deriveMoM, etc.` |
| `{ ?\.\.\. ?}` | `expect(result).toBe({ ... })` |
| `similar to (Phase\|Step\|Section)` | `similar to Phase 4` |
| `and \d+ more\|and others` | `and 3 more endpoints` |
| `repeat for\|do the same for` | `repeat for remaining products` |

**If any match is found:** Expand it in-place — write the full content that was compressed.
**Do not deliver the plan until zero decay signals remain in the last 40%.**

---

## Mid-Plan Insertion Protocol

When a new phase must be inserted into an **existing plan** (discovered mid-project):

1. **Do NOT renumber** existing phases — renumbering breaks agent prompts that reference phase numbers.
2. **Use a suffix** for inserted phases: Phase 9 → Phase 9A, then 9B if another is added later.
3. **Update the Pre-flight Scan** at the top to include the new phase.
4. **Add a `## Phase 9A` block** with the full structure (Prompt, What to build, Validation Checklist).
5. **Update the Output Destination header** to reflect the new `Updated:` date and status.
6. **Do NOT modify completed phase sections** — treat them as immutable history.

---

## Output Destination

Save the completed plan to:

- `.github/plans/<feature-slug>.md` — default for both modes
- `.github/plans/backlog/<feature-slug>.md` — optional backlog location

If mode is **`junai-pipeline`**, additionally register the artefact in `.github/agent-docs/ARTIFACTS.md` with `status: current`.

**Next step after saving:** Load `.github/skills/workflow/preflight/SKILL.md` and run it against the completed plan before any agent begins implementation. Preflight catches wrong endpoints, stale type names, missing dependencies, and field name mismatches that slipped past plan authorship — far cheaper to fix in the plan than mid-implementation.

---

## Relationship to Other Skills

| Skill | When to use instead |
|-------|-------------------|
| `docs/writing-plans/SKILL.md` | Smaller plans (< 8 phases), TDD micro-task granularity, single developer session |
| `workflow/brainstorming/SKILL.md` | Scope is still vague — use to harden requirements before this skill |
| `workflow/preflight/SKILL.md` | After the plan is written — validates it against the actual codebase before agents start |
| `large-task-fidelity.instructions.md` | Always apply in addition to this skill during plan OUTPUT — not a substitute |
