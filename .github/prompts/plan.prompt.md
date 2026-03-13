---
description: "Create a phased execution plan for multi-session work"
mode: agent
tools: ['codebase', 'editFiles', 'search']
---

# /plan - Create Phased Execution Plan

**You must create a phased plan document immediately.**

## Input

User's request: `{{input}}`

If `{{input}}` is empty, ask: "What feature or task do you need a phased plan for?"

---

## Step 1: Analyze Scope

Quickly assess the work:

1. **Read relevant files** to understand current state
2. **Identify components** that need creation/modification
3. **Estimate complexity** - is this truly multi-session work?

```
If work can be completed in ONE session (< 1 hour):
  → Tell user: "This is single-session work. Proceeding directly."
  → Do the work instead of creating a plan.

If work requires MULTIPLE sessions:
  → Continue to Step 2.
```

---

## Step 1b: Requirements & Constraints

Before designing phases, capture key requirements and constraints that shape the plan:

```
- REQ-001: [Functional requirement]
- SEC-001: [Security requirement]
- CON-001: [Constraint - tech, time, infrastructure]
- PAT-001: [Pattern to follow from existing codebase]
```

This ensures nothing is missed during phase design.

---

## Step 2: Design Phases

Break work into **independently completable phases**:

### Phase Sizing Rules

| Phase Size | Guideline |
|------------|-----------|
| Too small | Combined into previous phase |
| Ideal | 30-60 minutes work, clear completion point |
| Too large | Split into sub-phases |

### Phase Types (Common Patterns)

```
Foundation Phase:  Data models, adapters, configuration
Core Phase:        Business logic, services, main functionality  
UI Phase:          Pages, components, styling
Integration Phase: Connecting pieces, end-to-end testing
Polish Phase:      Error handling, edge cases, documentation
```

### Each Phase MUST Have

- [ ] Clear deliverables (what gets created/changed)
- [ ] Testable outcome (how to verify completion)
- [ ] No dangling dependencies (works standalone)
- [ ] **Agent assignment** (which agent executes this phase)
- [ ] **Required skills** (which `.github/skills/*/SKILL.md` the agent must load)
- [ ] **Evidence tier** (`standard` or `anchor` — determines verification depth)
- [ ] **Intent references** (links to specific Architecture/PRD sections this phase implements)
- [ ] **Design intent** (one-sentence summary of what upstream documents mean for this phase)
- [ ] **Ready-to-use prompt** (self-contained prompt with `═══ PROMPT START` / `═══ PROMPT END` markers)

### Documentation Considerations

For significant features, include documentation deliverables in your plan:

| If Adding... | Include Deliverable |
|--------------|---------------------|
| New public APIs | API_REFERENCE.md update |
| New architecture/flow | Architecture diagram |
| New env variables | `.env.example` update |
| Breaking changes | CHANGELOG.md entry |
| Visible feature | README.md update |

You can include docs in a Polish Phase, or add doc tasks as deliverables within the relevant phase (e.g., "Update architecture diagram" after creating new data flow).

---

## Step 2b: Cross-Reference Audit (MANDATORY)

**After designing all phases, before writing the plan document**, systematically verify that every requirement from input documents is covered.

### Process

1. **List every requirement** from ALL input documents:
   - FRs (functional requirements) from PRD
   - NFRs (non-functional requirements) from PRD
   - Risks and mitigations from architecture doc
   - Design decisions and constraints from architecture doc
   - Patterns and rules from instruction files

2. **For each requirement**, find its matching plan phase/step:
   - Does a specific phase/step address it?
   - Is there enough detail for an engineer to implement it?
   - Is there a testable acceptance criterion?

3. **For any unmatched requirement**:
   - **Add a new phase/step** to cover it, OR
   - **Mark explicitly as "Out of Scope"** with rationale

4. **Verify all section references** (§N citations):
   - Open the cited document
   - Confirm the section number, heading, and content match
   - Fix any incorrect references

5. **Include a Traceability Matrix** in the plan (see template in Step 3)

> **Why this step exists**: The Plan agent has historically acknowledged requirements during analysis (Step 1b) but failed to create actionable plan steps for them. This audit catches those gaps before implementation begins.

---

## Step 3: Create Plan Document

Create file at: `plans/{feature-name}.md`

Use this template:

```markdown
# {Feature Name} - Phased Execution Plan

**Created**: {date}
**Status**: Phase 1 of N | Planned / In Progress / Completed / On Hold
**Estimated Sessions**: {N}

## Overview

{2-3 sentence description of what we're building}

## Current State

{Brief description of relevant existing code/state}

## Phases

### Phase 1: {Name} ⏳
**Goal**: {One sentence}
**Agent**: `@{agent-name}` (see `.github/agents/{agent-name}.agent.md`)
**Required Skills**: `{.github/skills/relevant-skill/SKILL.md}` (skills the agent MUST load for this phase)
**Evidence Tier**: `standard` | `anchor` (standard = artefact exists + fields present; anchor = full 5-phase evidence protocol)
**Intent References**:
  - Architecture: `{path-to-ADR}` §{section} ({decision title})
  - PRD: `{path-to-PRD}` {requirement ID} ({requirement summary})
**Design Intent**: {One-sentence summary of what upstream documents mean for THIS phase — forces explicit interpretation}
**Deliverables**:
- [ ] {File or component 1}
- [ ] {File or component 2}

**Verification**: {How to test this phase is complete}

**Key Details**:
```
{Any specific implementation notes, patterns to follow, etc.}
```

#### Ready-to-Use Prompt (Phase 1)

> **How to use:** Copy the prompt block below (between ═══ START and ═══ END markers) into a new chat session. **Include all code blocks** — they're context for the agent, not for you to apply manually.
> **Agent:** `@{agent-name}` (see `.github/agents/{agent-name}.agent.md`)
> **Skills to load:** `.github/skills/{skill-path}/SKILL.md`
> **Instructions (auto-applied):** `{relevant}.instructions.md`
> **Project config:** `.github/project-config.md` (profile: `{profile}`)

> ═══ PROMPT START — Copy everything between START and END into a new chat ═══

\`\`\`\`
{One-sentence task description}

**Agent context:** You are the `@{agent-name}` agent. Load `.github/project-config.md` before starting.

**Read these files FIRST (in order):**
1. `plans/{feature-name}.md` — **THIS PLAN** — read "Phase 1"
2. {Source docs with specific sections}
3. {Target files — current state}

**What to do:**
- {Actionable instruction 1}
- {Actionable instruction 2}

**Acceptance criteria:**
- {Testable criterion 1}
- {Testable criterion 2}
\`\`\`\`

> ═══ PROMPT END ═══════════════════════════════════════════════════════════

---

### Phase 2: {Name} 🔲
**Goal**: {One sentence}
**Agent**: `@{agent-name}`
**Deliverables**:
- [ ] {File or component}

**Verification**: {How to test}

#### Ready-to-Use Prompt (Phase 2)
> {Same structure as Phase 1 prompt block — with ═══ START / END markers}

---

### Phase 3: {Name} 🔲
...

---

## Alternatives Considered

| ID | Approach | Why Not Chosen |
|----|----------|----------------|
| ALT-001 | {Alternative approach} | {Rationale} |

## Affected Files

| ID | File Path | Action |
|----|-----------|--------|
| FILE-001 | {path} | Create / Modify / Delete |

## Dependencies

| External Dependency | Status | Notes |
|---------------------|--------|-------|
| {e.g., Database access} | ✅ Ready | |

## Risks

| Risk | Mitigation |
|------|------------|
| {Risk} | {How to handle} |

## Source Document Traceability (MANDATORY)

> This matrix proves every requirement from input documents is covered in the plan.
> Generated by the Cross-Reference Audit (Step 2b).

| Requirement | Source | Plan Phase/Step | Status |
|-------------|--------|-----------------|--------|
| FR-001 | PRD §X.Y | Phase N, Step M | ✅ Covered |
| NFR-001 | PRD §X.Y | Phase N, Step M (criterion: ...) | ✅ Covered |
| Risk-001 | Arch §X | Phase N, Step M (mitigation: ...) | ✅ Covered |
| {Requirement} | {Source} | N/A | ⚠️ Out of Scope — rationale: {why} |

> **Rule**: Every FR, NFR, risk, and design decision from input documents MUST appear in this table.
> Items without a plan step must have an explicit "Out of Scope" rationale.

## Continuation Prompts

**To start Phase 1:**
> Read `plans/{feature-name}.md` and implement Phase 1. Mark deliverables complete as you finish them.

**To continue Phase N:**
> Read `plans/{feature-name}.md` and implement Phase {N}. Previous phases are complete.
```

> 💡 **Note**: Use `- [ ]` checkbox format for deliverables so progress can be tracked. In Cursor, the Implement agent can update the plan as work progresses; in other IDEs, you or the AI can update checkboxes when completing each item.

---

## Step 4: Output Summary

After creating the plan document, output:

```
## ✅ Plan Created

**Location**: `plans/{feature-name}.md`
**Phases**: {N} phases, estimated {N} sessions

### Phase Overview
1. {Phase 1 name} - {brief description}
2. {Phase 2 name} - {brief description}
...

### To Begin Implementation

Start a new chat with:
> Read `plans/{feature-name}.md` and implement Phase 1.

In Cursor you can hand off to the Implement agent; in other IDEs, paste: "Read the plan at `plans/<feature-name>.md` and implement Phase 1."

The implement agent will automatically update your plan doc as work progresses.
```

---

## Quick Reference

```
/plan                     ← Prompts for what to plan
/plan add search feature  ← Creates plan for search feature
/plan refactor services   ← Creates plan for refactoring
```

**Output location**: `plans/{feature-name}.md`

**This prompt creates the plan. Implementation happens in subsequent sessions.**

---

## Example: Completed Plan

Here's what a filled-in plan looks like:

```markdown
# Customer Search Feature - Phased Execution Plan

**Created**: 2026-02-09
**Status**: Phase 1 of 3
**Estimated Sessions**: 3

## Overview

Add a customer search page with filters (name, status, date range),
pagination, and drill-down to customer detail. Requires backend API
endpoint and Streamlit UI.

## Current State

The app has Home and Analytics pages. No search functionality exists.
Database has `customers` and `orders` tables with indexes on `customer_id`.

## Phases

### Phase 1: Backend API + Data Layer
**Goal**: Create search endpoint with filtering and pagination
**Agent**: `@implement` (see `.github/agents/implement.agent.md`)
**Deliverables**:
- [x] `src/models/search.py` - SearchRequest/SearchResponse Pydantic models
- [x] `src/repositories/customer_repo.py` - parameterized search query
- [x] `src/services/search_service.py` - search with caching
- [x] `tests/test_search_service.py` - unit tests

> **Note:** This is a *worked example* — adjust paths to match your project structure.

**Verification**: `pytest tests/test_search_service.py` passes

#### Ready-to-Use Prompt (Phase 1)

> **How to use:** Copy the prompt block below (between ═══ START and ═══ END markers) into a new chat session. **Include all code blocks** — they're context for the agent, not for you to apply manually.
> **Agent:** `@implement` (see `.github/agents/implement.agent.md`)
> **Skills to load:** `.github/skills/frontend/streamlit-dev/SKILL.md`
> **Instructions (auto-applied):** `python.instructions.md`, `sql.instructions.md`
> **Project config:** `.github/project-config.md`

> ═══ PROMPT START — Copy everything between START and END into a new chat ═══

\`\`\`\`
Create the search backend: Pydantic models, repository with parameterized query, service with caching, and unit tests.

**Read these files FIRST:**
1. `plans/customer-search.md` — **THIS PLAN** — read "Phase 1"
2. `src/services/data_ingestion/database_adapter.py` — existing DB adapter
3. `src/ingestion_config/queries.yaml` — existing query patterns

**What to do:**
- Create `src/models/search.py` with SearchRequest (filters) and SearchResponse (paginated results)
- Create `src/repositories/customer_repo.py` with parameterized search query
- Create `src/services/search_service.py` with @st.cache_data(ttl=300)
- Create `tests/test_search_service.py` with tests for empty results, pagination, and filters

**Acceptance criteria:**
- `pytest tests/test_search_service.py -v` → all pass
- No SQL injection (parameterized queries only)
\`\`\`\`

> ═══ PROMPT END ═══════════════════════════════════════════════════════════

---

### Phase 2: Search UI Page
**Goal**: Build Streamlit search page with filters and results table
**Agent**: `@streamlit-developer` (see `.github/agents/streamlit-developer.agent.md`)
**Deliverables**:
- [ ] `src/pages/Search.py` - search page with filter sidebar
- [ ] `src/components/search_filters.py` - reusable filter component
- [ ] `src/components/customer_table.py` - paginated results table

**Verification**: Navigate to Search page, enter a name, see results

---

### Phase 3: Polish + Detail View
**Goal**: Add customer detail drill-down and error handling
**Agent**: `@streamlit-developer`
**Deliverables**:
- [ ] `src/pages/CustomerDetail.py` - detail view
- [ ] Error states and empty state handling
- [ ] Loading spinners and performance optimization

**Verification**: Full flow: search -> select customer -> see details

---

## Source Document Traceability

| Requirement | Source | Plan Phase/Step | Status |
|-------------|--------|-----------------|--------|
| Search by name | PRD §2.1 | Phase 1, Step 1 + Phase 2 | ✅ Covered |
| Pagination | PRD §2.3 | Phase 1 (backend) + Phase 2 (UI) | ✅ Covered |
| Customer drill-down | PRD §2.4 | Phase 3 | ✅ Covered |
| Error handling | NFR §3.1 | Phase 3 | ✅ Covered |
```
