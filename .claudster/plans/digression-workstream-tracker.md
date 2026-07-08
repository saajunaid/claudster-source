---
type: plan
status: proposed
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

## Open questions
- One stack per repo, or global across repos? (This session's digressions spanned platform-infra +
  serve-sight while UCIP lived in uni-sight — cross-repo.)
- Auto-push heuristics vs. explicit `/digress` only (avoid false positives).
- Interaction with existing `relay.md` (fold the stack into it, or a sibling file the SessionStart hook
  reads first).

## Provenance
Requested by the user during the 2026-07 UCIP session; earlier captured only in the assistant's private
project memory (`digression-workstream-tracker`) — this file records it **in the claudster repo** so it
is discoverable and actionable.
