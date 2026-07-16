# Fable audit — docket (2026-07-15)

Read-only adversarial audit by Fable (`claude-fable-5`) of `E:\Projects\docket` @ `af231cc`, run from
`.claudster/prompts/fable-inspect-docket.md`. Findings are the reviewer's; verify before acting.

## Top 10 (ranked)
1. **`requires_confirmation` is a no-op** — a card dragged into Ship immediately runs `/claudster:ship` (which pushes; push-to-main auto-deploys prod). Flag stored + shown, never enforced. (Critical)
2. **Implement runs mutate the developer's real working tree** — `git checkout -B` on the shared tree can sweep uncommitted WIP into agent commits; a crash leaves the branch switched + pre-commit guard installed. (High)
3. **Cross-process write race on `.docket/`** — engine uses `threading.RLock` only; shipped hooks/CLI write from a second process → duplicate `DKT-N` ids / clobbered `board.json`. (High)
4. **Contributor lane-drag auto-triggers agent runs, bypassing the lead-only gate** — `/move` is contributor-tier and fires `_maybe_enqueue_agent_run` unconditionally where a local runner is attached. (High)
5. **Gate verdicts string-matched over the whole transcript** — echoed `REVIEW: CLEAN` / injected task text can flip a fail-closed gate open. (High)
6. **Stuck runs wedge the WIP cap with no runtime recovery** — reconcile only at process startup; a dead worker holds `running` (and the cap) until restart. (High)
7. **Archived tasks are unreachable and unrestorable** — no unarchive op; `/api/board` strips archived; the "Archived" toggle can never show anything. (High)
8. **Corrupt `events.jsonl` 500s the board** — `json.JSONDecodeError` escapes the OSError handler; only escape is removing the project. (Medium-High)
9. **Kanban DnD has no keyboard path** — only `PointerSensor`; cards are click-only `<article>`s; drawer is a non-modal div. WCAG 2.2 AA 2.1.1 fails. (High)
10. **"Report bug" lies to stakeholders** — UI promises screenshot uploads to all roles; attachments are contributor-gated server-side →永 impossible-retry loop. (Medium-High)

## Systemic themes
1. **Single-process assumptions in a multi-process product** — engine/registry/locks are in-memory `threading` locks, but hooks/CLI/worker all write `.docket/` from other processes. On-disk lock around commit+allocate is the structural fix.
2. **Guardrails declared but not enforced end-to-end** — `requires_confirmation` (stored-but-ignored), lead-only run gate (ungated lane-move), fail-closed verdict (substring-matched over attacker-influenced text). One threat model: "who/what can start or pass an autonomous, code-writing, prod-deploying run."
3. **Best-effort-everything hides failure** — pervasive `except Exception: log & continue` is right for durability, wrong for observability; users see nothing happen. Pair every swallowed failure with a user-visible signal.
4. **Autonomy without isolation or accessibility** — Implement mutates the human's real tree; the board is mouse-only with non-dialog overlays. A git-worktree sandbox + a keyboard/dialog layer are the two structural investments.

## UI/UX quick wins
1. Hide the BugForm attachment picker for stakeholders (kills the impossible retry loop).
2. Confirm Archive (reuse the two-step delete pattern) until unarchive exists.
3. Render the API `detail` on board-load error + an inline "Remove project" (instead of "Is docket serve running?").
4. Move the pipeline-preset card creation into save `onSuccess`; stop `.catch(()=>{})`.
5. Add a "this runs `<command>` on the server" line + tooltip auto-triggering lanes.

_Full per-finding detail (F1–F39 with file:line, failure scenarios, fixes, confidence) is in the audit
transcript; the above is the executive layer. Positives noted by the reviewer: artifact path guards, the
visual-iframe `sandbox=""`+CSP, attachment sniff/re-encode, `prefers-reduced-motion`, 404-not-403 on ids._
