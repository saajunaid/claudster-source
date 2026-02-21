---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md`

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For the implementing agent:** Follow this plan task-by-task, executing each step sequentially.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

```markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
```

## Remember
- Exact file paths always
- Complete code in plan (not "add validation")
- Exact commands with expected output
- Reference relevant skills with @ syntax
- DRY, YAGNI, TDD, frequent commits
- **Every phase MUST end with a numbered exit gate task** (e.g., "Task N.X: Exit Gate") that includes pass/fail checks, commit message format, and an explicit "STOP — do not proceed to next phase" instruction
- **Every phase/step must specify the executing agent and include a ready-to-use prompt with `═══ PROMPT START` / `═══ PROMPT END` markers**
- **Use 4-backtick fences (`` ```` ``) for the outer prompt block** so nested code blocks render correctly
- **After writing all phases, run the Cross-Reference Audit against ALL source documents**

## Cross-Reference Audit

**Run this AFTER all phases are written, BEFORE finalizing the plan.**

Walk through every FR, NFR, risk, and design decision from ALL input documents. For each, verify it maps to a specific, actionable plan step. Output a traceability matrix:

```markdown
## Source Document Traceability

| Requirement | Source | Plan Phase/Step | Status |
|-------------|--------|-----------------|--------|
| FR-101 | PRD §3.1 | Phase 1, Step 2 | ✅ Covered |
| NFR-208 | PRD §4.2 | Phase 5, Step 1 | ✅ Covered |
| Risk-003 | Arch §9 | Phase 3, Step 3 | ✅ Covered |
| ALT-002 | Arch §7.4 | N/A | ⚠️ Out of Scope — rationale: deferred to v2 |
```

**Rules:**
- A requirement without a plan step → add a step or mark "Out of Scope" with rationale
- A cited section reference (§N) → verify the section number matches the actual document
- Zero-tolerance: no unmapped requirements in a finalized plan

## Agent & Prompt Assignment

**Every phase/step MUST include a ready-to-use prompt block.** This is non-negotiable because plans are executed across multiple sessions by different agents.

### Prompt Block Template

> **CRITICAL**: Use 4-backtick fences (` ```` `) for the outer prompt block so nested code blocks (yaml, python, etc.) inside the prompt render correctly. Add `═══ PROMPT START` and `═══ PROMPT END` markers so users can clearly see where to copy from/to.

```markdown
### Ready-to-Use Prompt (Phase N — Step M)

> **How to use:** Copy the prompt block below (between ═══ START and ═══ END markers) into a new chat session. **Include all code blocks** — they're context for the agent, not for you to apply manually.
> **Agent:** `@{agent-name}` (see `.github/agents/{agent-name}.agent.md`)
> **Skills to load:** `.github/skills/{skill-path}/SKILL.md`
> **Instructions (auto-applied):** `{instruction1}.instructions.md`, `{instruction2}.instructions.md`
> **Project config:** `.github/project-config.md` (profile: `{profile}`)

> ═══ PROMPT START — Copy everything between START and END into a new chat ═══

\`\`\`\`
{One-sentence task description}

**Agent context:** You are the `@{agent-name}` agent. Load `.github/project-config.md` before starting.

**Read these files FIRST (in order):**
1. `.github/plans/{plan-file}.md` — **THIS PLAN** — read "Phase N — Step M"
2. {Architecture/PRD doc} — {specific sections}
3. {Target file(s)} — current state

**What to do:**
- {Actionable instruction 1}
- {Actionable instruction 2}

**Acceptance criteria:**
- {Testable criterion 1}
- {Testable criterion 2}

**Scope boundary:**
- Exit gate: Task N.X (the last task in this phase)
- Do NOT proceed to Phase N+1 after the exit gate passes
- Do NOT offer additional work beyond the exit gate tasks
- Commit with: `feat({feature}): Phase N — {description}` and STOP
\`\`\`\`

> ═══ PROMPT END ═══════════════════════════════════════════════════════════
```

### Agent Selection Guide

| Task Type | Agent | Agent File |
|-----------|-------|------------|
| Models, services, logic | `@implement` | `implement.agent.md` |
| Streamlit UI, components | `@streamlit-developer` | `streamlit-developer.agent.md` |
| Tests, fixtures | `@tester` | `tester.agent.md` |
| SQL queries, schema | `@sql-expert` | `sql-expert.agent.md` |
| Docs, README | `@docs` | `docs.agent.md` |
| Code review | `@code-review` | `code-review.agent.md` |

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `.github/plans/<filename>.md`. Two execution options:**

**1. This session** — I implement each task sequentially, reviewing between tasks

**2. Separate session** — Open a new session with the `@implement` agent and provide the plan path

**Which approach?"**

**If separate session chosen:**
- Guide them to open new session
- Reference the `@implement` agent (`.github/agents/implement.agent.md`)
- Provide the plan file path for the implementing agent to read
