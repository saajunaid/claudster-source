description: "Large-task execution discipline — pre-flight scan, path gate, anti-drift rules, and equal-depth enforcement for multi-phase planning and implementation sessions"
applyTo: ".github/agents/*.agent.md, .github/instructions/*.md, .github/plans/*.md"

# Large-Task Fidelity Instructions

Apply these rules whenever a task produces a **large, structured, multi-phase output** — specifically:
- 4 or more phases in a single session
- 50 or more expected output lines
- Multiple reference documents attached as constraints

These are *execution discipline* rules, not requirements-gathering rules. They are orthogonal to `plan-mode.instructions.md` (which handles discovery and clarification before implementation begins). Apply both when a session moves from planning into large-scale output generation.

---

## Trigger Conditions

Activate when the task involves:
- A complete project plan across many phases
- A large implementation spanning multiple files and layers
- Any output where fidelity to attached reference documents is critical
- Any output where the end of the document must match the quality of the beginning

---

## Rule 1 — Pre-Flight Scan (Required Before Any Output)

Before writing any task line, phase section, or implementation block, produce a **pre-flight summary** in this format:

```
Phase N — [Name]: ~N tasks expected, depends on [phase numbers or "none"]
```

Produce all phases first. Do not start the main output until the pre-flight is complete.

**Why:** Forces a full scope read before output commitment. Prevents depth decay on later phases because the agent has already committed to an expected task count per phase.

---

## Rule 2 — Named Output File

When producing a planning artefact or task list, write it to a named file — not just as chat output.

- Include the output file path in the prompt: `OUTPUT DESTINATION: <relative path>`
- The file is the deliverable. Chat output is secondary.
- If the session produces a task list, the file name should clearly identify it (e.g. `master-task-list.md`, `phase-3-plan.md`).

**Why:** Chat output can be silently truncated or lost. A named file gives the human a verifiable, reviewable artefact.

---

## Rule 3 — Path Gate

Before writing any `CREATE`, `UPDATE`, or `CONFIGURE` line that references a file path:

1. Verify the path appears verbatim in the project's directory structure document (e.g. `§15` of a blueprint)
2. If the path is NOT listed there: write a `NOTE — [path] not found in directory spec, confirm before creating` instead of inventing it

**Why:** Agents under context load invent plausible-sounding paths. The path gate forces a source-of-truth check per line rather than per session.

---

## Rule 4 — No Abbreviation

Never use these shorthands in structured output:
- "similar to Phase X"
- "as above"
- "same pattern"
- "follow the approach in Phase N"
- "etc." in a task description
- "..." to indicate continuation

Every task line must be written in full, regardless of similarity to earlier lines.

**Why:** Abbreviation is a fidelity collapse signal. It tells the implementer to infer details — which is exactly where intent drift enters.

---

## Rule 5 — Phase Boundary Re-Anchor

After completing each phase section, explicitly re-read the fidelity constraints before starting the next phase.

In practice: treat the constraints block as a checklist you tick mentally after each phase, not once at the start.

**Why:** Attention to constraints degrades over long outputs. Re-anchoring at each boundary keeps constraint awareness fresh through Phase 8 and 9, not just Phase 1.

---

## Rule 6 — Equal Depth

Late phases (the final 2–3 phases of any plan) must receive the same number of task lines as their deliverable count warrants.

- Do not summarise late phases
- Do not merge late-phase deliverables into single lines
- If you notice a phase is getting thinner than earlier phases, stop and expand it before continuing

**Why:** Output quality predictably tapers. Equal depth is an explicit override of that default.

---

## Rule 7 — Open Question Flagging

If the reference documents contain open questions (e.g. §7.8 OQ-1 through OQ-5) that affect specific tasks:

- Flag each affected task with `[OQ-N BLOCKER]` inline
- Do not silently assume a resolution
- Do not skip the task — stub it and flag

**Why:** Blocked items are often the most critical. Silent omission causes implementers to discover blockers mid-build.

---

## Rule 8 — Post-Generation Self-Sweep (Mandatory Final Step)

After completing any large structured output (plan, implementation sequence, test suite, migration set, report), run a self-sweep for output decay patterns before declaring the work complete.

**Scan the last 40% of your output for these decay signals:**

| Signal | Regex pattern | Example |
|--------|--------------|---------|
| Ellipsis placeholders | `\.{3,}` | `// ... similar tests for each function` |
| Same-pattern shortcuts | `same pattern` | `same pattern × 3 rows` |
| As-above references | `as above` | `as above for remaining endpoints` |
| Etc. in task lines | `\betc\b\.?` | `deriveDeltas, deriveYtd, etc.` |
| Pseudo-code bodies | `\{ ?\.\.\. ?\}` | `expect(result).toBe({ ... })` |
| Phase/step cross-refs | `similar to (Phase\|Step\|Section)` | `similar to Phase 2` |
| Collapsed lists | `and \d+ more\|and others\|and the rest` | `and 3 more` |
| Implied continuation | `repeat for\|do the same for` | `repeat for remaining products` |

**Execution:**

1. After writing the output, re-read the last 40% of the document
2. Search for each decay signal above
3. If ANY match is found: **stop and expand the shortcut in-place** — write the full content that was compressed
4. If you cannot expand (context lost): flag with `[DECAY: needs expansion]` and include in your completion summary
5. Do NOT deliver output containing unexpanded decay markers as a completed artefact

**Why:** Output decay is the most common fidelity failure in large outputs. These patterns are mechanically detectable. A self-sweep takes seconds and prevents hours of downstream rework. The decay signals above were empirically identified from real agent outputs that passed semantic review but failed structural completeness.

---

## Anti-Pattern Summary

| Anti-pattern | Symptom | Correct behaviour |
|---|---|---|
| Depth decay | Phase 8 has 3 lines, Phase 1 has 20 | Equal depth rule — expand before continuing |
| Path invention | `src/utils/helpers.py` not in directory spec | Path gate — write NOTE instead |
| Abbreviation collapse | "follows same pattern as above" | No abbreviation — write full line |
| Constraint fade | Phase 7 uses f-string SQL | Re-anchor — constraints apply to every phase |
| Chat-only output | Deliverable only in response, no file | Named output file — write to disk |
| Scope blindness | Agent starts writing before reading all phases | Pre-flight scan — summarise all phases first |
| Output decay | `...`, `same pattern`, `as above`, `{ ... }` in later sections | Self-sweep — expand every shortcut before delivering |

---

## Quick Reference (Paste into Any Large-Task Prompt)

```
EXECUTION FIDELITY RULES — apply from first line to last:
1. PRE-FLIGHT: Produce a ~N-tasks-expected summary for every phase before writing any task.
2. OUTPUT FILE: Write the deliverable to <file path> — do not treat chat as the output.
3. PATH GATE: Verify each file path exists in the reference structure doc before writing it.
   If not found, write NOTE — [path] not in directory spec, confirm before creating.
4. NO ABBREVIATION: Write every task line in full — no "as above", "same pattern", or "etc."
5. RE-ANCHOR: After each phase, re-read the fidelity constraints before starting the next.
6. EQUAL DEPTH: Final phases must be as thorough as Phase 1 — do not summarise late phases.
7. FLAG BLOCKERS: Mark open-question-dependent tasks with [OQ-N BLOCKER] inline.
8. SELF-SWEEP: After completing output, scan the last 40% for decay signals ("...",
   "same pattern", "as above", "etc.", "{ ... }", "similar to Phase N").
   Expand every match in-place. Do not deliver output with unexpanded shortcuts.
```
