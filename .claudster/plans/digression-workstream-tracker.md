---
type: plan
status: shipped
feature: digression-workstream-tracker
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-08T00:00:00Z
Creating Model: claude-opus-4-8
---

# Digression workstream tracker — never lose the original task after a detour

## Problem (recurring, felt in real sessions)

When a session **digresses** from its original task into a related-but-different one — a design
decision, a sub-feature, or a blocker that must be fixed first — the original task is easy to lose. The
user then has to *remember and re-state* it, and there is no mechanism that says "you were on X, at
phase Y — resume?".

**Concrete motivating session (2026-07):** the primary task was the **uni-sight (UCIP)** plan. It
digressed, in sequence, into: a **Windows-auth sidecar**, then **app resilience / never-blank**, then a
multi-phase **data-driven RBAC pilot** on serve-sight. At *every* digression the user asked, verbatim,
"is UCIP still tracked?" — the anxiety of a dropped thread is real and repeated. We handled it **by hand**
in `.claudster/relay.md` (marking UCIP the "primary destination" while each digression logged a "return
to Phase 2" pointer), which worked but relied on the agent remembering to maintain it.

## Desired behavior

Claudster should, without the user re-stating anything:
1. **Record the original task + its status** (active plan path, phase, resume pointer) when work digresses.
2. **Surface it** — e.g. at SessionStart: "Active: <current>. Parked: <original> at phase Y."
3. **Resume it** — offer to pop back to the parked task when the digression completes, with its exact
   resume point.

## Design sketch (a "workstream stack" on the existing relay mechanism)

- **State:** a small stack persisted in `.claudster/` — either a structured `## Workstream stack` section
  in `relay.md`, or `.claudster/workstreams.jsonl` (append-only, one entry per push/pop). Each frame:
  `{ plan, phase, resumePointer, pushedAt, reason }`.
- **`/digress [reason]`** — push the current workstream (from the active plan + relay) onto the stack and
  start the new task. (Or auto-detect: a session starts a *different* `.claudster/plans/*` while another is
  mid-flight → prompt to push.)
- **`/resume`** — pop the top frame; report "you were on <plan> at <phase> — continue?" and rehydrate the
  relay's Next-step from it.
- **SessionStart hook** — inject the stack summary alongside the relay (this is the anti-context-rot win).
- Reuses the relay's existing "primary destination" idea, just formalized so the agent can't forget it.

## Decisions (resolved 2026-07-10 — reviewed with the user)
1. **Per-repo stack, cross-repo-aware frames.** The stack lives in the repo where the *original* task
   lives (`.claudster/workstreams.json`); each frame may carry an optional `repo` field pointing at
   another repo's plan (covers the UCIP case, where digressions spanned repos). No global state — keeps
   claudster's everything-is-repo-scoped model intact.
2. **Explicit `/digress` + `/resume` only; the hook nudges, never auto-pushes.** Auto-detection produces
   false positives (a quick look at another plan ≠ a digression). Instead: the SessionStart injection
   shows the stack, and the handoff/relay skills gain one line of guidance — "starting a different plan
   while relay.md shows another mid-flight? suggest `/digress` to the user."
3. **Sibling file, not folded into relay.md.** `relay.md` is prose and is *rewritten* by `/handoff`; a
   structured stack inside it would be mangled. `.claudster/workstreams.json` is the state;
   `inject_relay.py` (the existing SessionStart hook) reads it and prepends one line per parked frame:
   `⛏ Parked: <plan> @ <phase> — "<reason>" (pushed <date>). /resume to pop.`

## State file schema (the contract everything below shares)
`.claudster/workstreams.json` — a JSON object, not JSONL (the stack is small; whole-file atomic rewrite):
```json
{
  "version": 1,
  "stack": [
    {
      "plan": ".claudster/plans/ucip.md",
      "phase": "Phase 2 — ingestion",
      "resumePointer": "next: wire the parser to the staging table (see plan Tracker row 2)",
      "reason": "blocked on the Windows-auth sidecar",
      "repo": null,
      "pushedAt": "2026-07-10T14:00:00Z"
    }
  ]
}
```
Rules: `stack` is LIFO (last element = most recently parked). `repo: null` means "this repo"; otherwise an
absolute path to the repo whose plan is referenced (cross-repo case). All fields strings except `repo`
(string|null). Unknown fields are preserved on rewrite (forward compatibility).

## Improvements (added 2026-07-11, during execution)
1. **Per-frame fail-open access.** The hook reads every frame field with `.get(...)` + a default, so a
   frame missing `phase`/`reason`/`repo` degrades to `?`/empty rather than raising — a partially-written
   stack must never break SessionStart (same bar as the Dream-Memory block right below it in the hook).
2. **`/digress` idempotency guard.** If the top-of-stack frame is already the plan being parked, `/digress`
   UPDATES that frame in place (refresh `phase`/`resumePointer`/`reason`/`pushedAt`) instead of pushing a
   duplicate. Prevents a stack of identical frames when a session digresses twice from the same plan.
3. **Deterministic ordering test.** Phase 1 asserts the parked line is emitted BEFORE the `=== relay.md ===`
   marker (index comparison), not merely that both strings are present — the "surface it first" guarantee.

## Phases

### Phase 1 — Hook injection (TDD) ✅ 10296d9
**Touches:** `claude-harness/hooks/inject_relay.py`, `claude-harness/hooks/tests/test_hook_paths.py`
(CORRECTED 2026-07-11: there is NO `*relay*` test file — the inject_relay hook is tested in
`test_hook_paths.py`. The hooks run top-level code and `sys.exit()` on import, so they CANNOT be imported:
every test invokes the hook as a subprocess via the module's `_run(script, cwd, stdin)` helper with a
tmp_path cwd, then asserts on stdout. Follow that exact fixture style — add the new tests under a
`# ── inject_relay: workstream stack ──` banner alongside the existing `inject_*` tests.)
**Implement:** in the hook, after locating the repo's `.claudster/` (reuse however it finds `relay.md`):
read `workstreams.json`; if absent, unparseable, `version != 1`, or `stack` empty → inject nothing extra
(and NEVER raise — wrap in try/except; a broken stack file must not break session start). Else prepend,
BEFORE the relay content, one line per frame top-of-stack first:
`⛏ Parked workstream: <plan> @ <phase> — "<reason>" (since <pushedAt date part>). Run /resume to pop.`
Multiple frames: list all, deepest last, and add a final line `(<N> parked total)` when N > 1.
**TDD (write RED first):** `test_injects_parked_frame_line` (stack of 1 → line present before relay text);
`test_multiple_frames_listed_lifo`; `test_absent_file_injects_nothing`;
`test_malformed_json_is_silently_ignored` (file containing `{oops`); `test_empty_stack_injects_nothing`;
`test_cross_repo_frame_shows_repo_path` (frame with `repo` set → the path appears in the line).
**Exit gate:** `python -m pytest claude-harness/hooks/tests -q` all pass; full suite green.
**Commit:** `feat(hooks): inject parked-workstream stack at SessionStart`

### Phase 2 — `/digress` and `/resume` commands ✅ dbeb79a
**Touches:** `claude-harness/commands/digress.md` (new), `claude-harness/commands/resume.md` (new).
Frontmatter style: copy `claude-harness/commands/handoff.md` (description + argument-hint).
**`digress.md`** (`argument-hint: [reason for the detour]`) instructs the agent to:
1. Identify the CURRENT workstream: the active plan = the `.claudster/plans/*.md` this session has been
   executing (else the plan named in relay.md's Next-step; else ask the user which plan to park — the ONLY
   permitted question). Read its `## Tracker` (or phase headings) for the current phase.
2. Write a one-line `resumePointer`: the next concrete action (from the Tracker/relay Next-step).
3. Read `.claudster/workstreams.json` (create `{"version":1,"stack":[]}` if absent). If the top-of-stack
   frame's `plan` already equals the plan being parked → UPDATE it in place (refresh phase/resumePointer/
   reason/pushedAt) rather than pushing a duplicate (improvement #2); else APPEND the frame (schema above;
   `pushedAt` = now, ISO-8601; `reason` = `$ARGUMENTS` or a self-derived one-liner). Write the whole file back.
4. Confirm to the user: "Parked: <plan> @ <phase>. Now switching to: <the new task>." Then continue with
   whatever the user asked.
**`resume.md`** (no args) instructs the agent to:
1. Read the stack; if absent/empty say "Nothing is parked." and stop.
2. POP the last frame (rewrite the file without it), then restate: plan, phase, resumePointer — and update
   `relay.md`'s "## Next step" section to match the popped frame (edit in place, preserving the rest).
3. Ask nothing; begin executing the resumePointer.
**Exit gate:** both commands exist; `validate_pool.py` OK; register them wherever `implement.md` was
registered (mirror commit `b9461d5`'s registry edit if one exists — check `git show b9461d5 --stat`).
**Commit:** `feat(commands): /claudster:digress + /claudster:resume — the workstream stack`

### Phase 3 — Guidance + convention test ✅ 0677817
**Touches:** `claude-harness/commands/handoff.md` (one sentence: if the session is abandoning a mid-flight
plan for another, suggest `/digress` first), `scripts/tests/test_headless_convention.py` OR a new
`scripts/tests/test_workstream_commands.py`: assert `digress.md` mentions the schema fields
(`resumePointer`, `pushedAt`), `resume.md` handles the empty-stack case explicitly (the words "Nothing is
parked"), and both files never instruct a destructive git action (grep: no `git checkout`, `git reset`).
**Exit gate:** suite green.
**Commit:** `test+docs: digression guidance in handoff; convention tests for the stack commands`

### Phase 4 — Ship ✅ (this commit)
`validate_pool.py` + full suite + bare `junai-push` (never `-Publish`); append a dated section to
`docs/analysis/IMPL-STATUS.md`. NOTE (2026-07-11): local work committed; the `junai-push` publish step is
held for explicit user confirmation (plugin-only change → prefer `-NoPublish` to avoid an unnecessary
MCP/VS Code republish).
**Commit:** `docs: digression workstream tracker shipped`

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\digression-workstream-tracker.md fully, then execute it
autonomously in E:\Projects\claudster-source. Rules: the Decisions section is settled — do not redesign;
TDD (Phase 1 RED tests first); after each phase run the full suite
(python -m pytest -q --import-mode=importlib) + validate_pool.py; commit per phase with the plan's commit
message, committing ONLY files your phase touched; update this plan's phase headings with ✅ + commit hash.
Bare junai-push in Phase 4 is allowed. Never ask a question the plan answers; the single permitted
interactive question is the one digress.md itself defines (ambiguous active plan).
```

## Provenance
Requested by the user during the 2026-07 UCIP session; earlier captured only in the assistant's private
project memory (`digression-workstream-tracker`) — this file records it **in the claudster repo** so it
is discoverable and actionable.
