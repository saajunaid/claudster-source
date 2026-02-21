---
description: "Gather comprehensive context before starting work - understand first, then do"
mode: agent
tools: ['codebase', 'search', 'fetch']
---

# /first-ask - Understand Before You Build

**Do not start implementing until you fully understand the task.**

## Input

User's request: `{{input}}`

---

## Step 1: Iterative Refinement

Your goal is to refine your understanding by asking targeted questions and exploring the codebase. Repeat until no unknowns remain.

### Ask About

| Category | Key Questions |
|----------|--------------|
| **Goal** | What is the overall objective? What problem does this solve? |
| **Users** | Who are the end users? How many? Internal or external? |
| **Scope** | What are the must-haves (MVP) vs nice-to-haves? |
| **Stack** | What technologies are in use? Any constraints? |
| **Patterns** | Are there existing conventions or architecture to follow? |
| **Constraints** | Performance targets? Security requirements? Timeline? |
| **Dependencies** | External APIs, databases, services, existing systems? |
| **Acceptance** | How will we know this is done? What are the success criteria? |

### Explore Proactively

Don't just ask -- investigate:

- **Scan the codebase** for relevant existing code, patterns, and conventions
- **Read config files** (`package.json`, `.env.example`, `pyproject.toml`, etc.)
- **Check existing docs** for architecture decisions or constraints
- **Research** if the task involves unfamiliar libraries or patterns

### Refinement Loop

```
1. Ask specific clarifying questions (not generic ones)
2. Explore the codebase and project structure
3. Summarize your understanding back to the user
4. Ask: "Is there anything I'm missing or got wrong?"
5. Repeat until the user confirms understanding is complete
```

Keep your understanding as simple as it can be -- avoid overcomplicating.

---

## Step 2: Present Your Plan

Once understanding is clear, present a concise plan:

```markdown
## Understanding

{2-3 sentences summarizing what you'll build and why}

## Approach

1. {Step 1 - what you'll do first}
2. {Step 2 - next action}
3. {Step 3 - and so on}

## Key Decisions

- {Any architectural or technical decisions made during clarification}

## Out of Scope

- {What you're explicitly NOT doing}
```

---

## Step 3: Get Confirmation, Then Execute

Wait for the user to confirm the plan, then proceed with implementation.

## Pipeline Boundary (when used with JUNO pipeline)

If `.github/pipeline-state.json` exists, treat this prompt as advisory preparation only:

- Do not provide direct stage-routing handoff prompts.
- Do not instruct stage transitions or gate changes.
- Provide a concise understanding summary + optional troubleshooting brief.
- End with: "Open `@Orchestrator` in a new session to route execution from pipeline state."

---

## Why This Matters

Gathering context upfront:
- Prevents incorrect assumptions
- Ensures appropriate technology choices
- Identifies constraints early
- Aligns implementation with actual needs
- Reduces rework and back-and-forth

## Quick Reference

```
/first-ask                          ← Prompts for task description
/first-ask add customer search      ← Starts refinement for search feature
```
