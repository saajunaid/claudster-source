---
type: analysis
status: current
feature: fable-remediation
creation-agent: claudster
Original Author: Claude Code (dispatched Fable model, claude-fable-5)
Creation Date: 2026-07-20T00:00:00Z
Creating Model: claude-fable-5
---

# Fable adversarial audit — docket, re-run (baseline: `main`)

Read-only adversarial audit by the Fable model (`claude-fable-5`), re-run per
`.claudster/prompts/fable-inspect-docket.md` because the 2026-07-15 audit's full per-finding detail
existed only in the session transcript — only an executive summary survived to disk. This run's full
output is captured here so nothing is lost a second time.

**Scope note (from the audit agent):** the working tree drifted across branches mid-audit
(`feat/ux-correctness` → `feat/cross-review-gate`), but every file cited below was confirmed
byte-identical to `main` via `git diff main -- <file>` (all zero) — findings and line numbers are
anchored to `main` as it stood before the `feat/cross-review-gate` merge (`7f612f4`) landed.

**Already-fixed set NOT re-reported** (per the audit's brief): F1, F2–F6, F11–F13(partial), F17, F25,
F30–F34. Where the agent found one of those *not actually present on the audited `main`*, it says so
explicitly below (see the F25 finding under UI/UX — the fix exists on a branch not yet merged to `main`
at audit time).

## 1. Top 10 (ranked by impact)

1. **`unarchive_task` is not write-serialized** — the F4 op was added to the engine but never added to
   the `@_serialized` set, so it rebuilds `board.json` with no per-repo lock (`engine.py:887-894` vs the
   wrap-loop at `1172-1194`). Confirmed.
2. **No per-project authorization** — any authenticated user can read (and a contributor can write)
   *every* registered project by passing `?project=`; role is a single global rank, not per-board
   (`api.py:733-747, 957-966`). Confirmed.
3. **First-seen Windows users auto-provision as stakeholder with no allowlist/opt-in** — on a
   domain-joined corp proxy, the entire domain silently gains read access to all boards, PRDs, plans,
   reviews, bug detail (`api.py:437-446`). Confirmed. (F20/F21 full detail.)
4. **The Implement lane starts an autonomous code-writing agent with no confirmation** —
   `requires_confirmation:false` for Implement while only Ship is gated; a lead's lane move or
   "Run agent" click immediately spawns branch→implement→commit→test (`config.py:90`;
   `engine.py:105-124,583`; `CardDrawer.tsx:248-262`). Confirmed.
5. **`wip_limits` is dead config** — a first-class per-lane WIP editor in Settings, validated
   server-side, but *nothing* enforces it on any move (`Settings.tsx:152-165`; `api.py:670-672`; no
   check in `engine.move_task:571-586` or the reducer). Confirmed.
6. **Implement runs mutate the shared working tree and can sweep the human's uncommitted WIP into
   agent commits** — `git checkout -B` carries a dirty tree onto the agent branch
   (`runner.py:336-339`); the known-partial F12. Confirmed.
7. **`requires_confirmation` runs count against `max_concurrent_runs` while parked** — unconfirmed
   Ship runs sit `queued` and consume WIP slots, so a few un-actioned Ship drags can wedge the whole
   board's agent capacity (`engine.py:659-664`). Confirmed/Likely.
8. **Stakeholders see a fully-editable card drawer** whose every write (title, description, move,
   archive, delete) 403s — only the Triage block is role-gated (`CardDrawer.tsx:191`; all other
   controls ungated). Confirmed.
9. **Attachment blob store is global and cross-project readable** by any stakeholder who has an id
   (`api.py:1345-1369`; engine `_attachments_dir` is server-wide). Confirmed.
10. **Renaming a lane silently orphans its agent config** — lanes are free-text-renamable, but
    `agent_track.lanes` keys are read-only and not revalidated against the board, so renaming
    "Implement" disables the pipeline lane with no warning (`Settings.tsx:132-144`;
    `api.py:621-627,682-699`). Confirmed.

## 2. Findings by dimension

### Logical / correctness

**[High] Concurrency — `unarchive_task` bypasses the per-repo write lock.** `engine.py:887-894`. Every
other task write is serialized either by an inline `@_serialized` decorator or by the wrap-loop at
`engine.py:1172-1194`. `unarchive_task` (added for F4) is in *neither* — `archive_task` is in the loop,
`unarchive_task` is not, and it carries no inline decorator. Scenario: a card is unarchived while
another request creates a task in the same repo; the two `_commit` calls race the `reduce → write_board`
rebuild with no mutual exclusion, so `board.json` can be clobbered by the loser's stale rebuild until the
next `_load_board` re-reduces. The append-only log stays correct, but the materialized cache violates the
stated "every write op is atomic per repo" contract (`engine.py:139-154`). Fix: add `"unarchive_task"` to
the wrap-loop list. Confidence: **Confirmed**.

**[Medium] `wip_limits` has no enforcement path.** `config.py:103`, `api.py:670-672`,
`Settings.tsx:152-165`. The value is stored, surfaced as an editor, and its keys validated to be real
lanes — but no code consults it. `move_task` (`engine.py:571-586`) and `assign_and_advance` (`853-875`)
never check lane occupancy. Scenario: a lead sets "In Progress = 3", drags a 6th card in, nothing stops
it; they lose trust in the whole config surface. Fix: enforce in `move_task`/`assign_and_advance` (reject
or warn), or delete the editor. Confidence: **Confirmed**.

**[Low] Auto-advance can chain-trigger agent runs.** `runner.py:1398-1404` calls `engine.move_task(...)`
with the default `trigger_agents=True`; F3 only validates that `auto_advance_to` is a *board* lane, not
that it is a non-agent lane. Configuring e.g. `Implement.auto_advance_to = "Ship"` would enqueue a Ship
run on completion (it would then park on confirmation, so impact is bounded). Fix: pass
`trigger_agents=False` on the internal auto-advance move. Confidence: **Confirmed** (latent).

**[Low] Board cache staleness check is lane-only.** `engine.py:296-306` only re-reduces when
`board["lanes"]` differs from config; changes to `done_lane`, `auto_move_on_commit`, or
`status_lane_map` don't invalidate the cached `board.json`. Reducer output doesn't embed those, so
impact is minimal, but a `done_lane` change won't reflect in `subtask.completed` targeting until a
rebuild. Confidence: **Likely**.

### Concurrency & safety landmines

**[High] Implement runs share the developer's working tree (known-partial F12).**
`runner.py:336-339,1285-1295`. The M1 `_worktree_lock` serializes *agent-vs-agent* runs, but nothing
isolates the agent from a human editing the same checkout. `git checkout -B agent/<slug>` carries any
uncommitted human changes onto the agent branch; the agent's per-phase commits can then absorb them, and
the branch/tamper guards (which only check protected-branch advancement and PROJECT-FACTS integrity)
won't notice. Scenario: a dev has local edits, a lead triggers Implement on the same repo, the dev's WIP
lands in an `agent/` commit and the dev's `git status` is quietly rewritten. Fix: require a clean tree
before implement, or a real `git worktree`/clone isolation (the still-open half of F12). Confidence:
**Confirmed**.

**[Medium] Parked confirmation runs wedge the WIP cap.** `engine.py:659-664`. The cap counts
`status in ("queued","running")` — including a `requires_confirmation` run that is queued but
unconfirmed. With the default `max_concurrent_runs:3`, three Ship cards dragged but never confirmed
block *all* further enqueues (the lane trigger drops with OverCapacity, `runner.py:870-871`). The F13
cancel endpoint is the only escape. Fix: exclude unconfirmed runs from the active count, or cap them
separately. Confidence: **Confirmed**.

**[Low] Local startup reconcile reaps all `running` runs.** `runner.py:824-827`.
`reconcile_orphans(startup=True, execution=local)` fails every `queued`/`running` run. If a second
docket process (a stray dev instance) starts against the same repo, its startup pass fails the first
process's genuinely in-flight runs. The file lock protects the write but not this policy decision.
Confidence: **Speculative** (needs two local servers on one repo).

### Pitfalls & footguns

**[High] One click / one drag launches an expensive, code-mutating autonomous run with no confirm.**
`config.py:90` (`Implement… requires_confirmation:false`), `CardDrawer.tsx:248-262` (the "Move to lane"
select), `CardDrawer.tsx:389-398` ("Run agent"). Only Ship is confirmation-gated. A lead who drags a card
to Implement — or picks "Implement" in the drawer's lane select — immediately starts
preflight→implement→commit→tests→review. There is no "this will run an agent" dialog anywhere for
Implement. Fix: gate Implement (and any `kind:implement` lane) behind the same confirmation affordance
as Ship, or a front-end confirm before moving into an agent lane. Confidence: **Confirmed**.

**[Medium] MCP transport and `docket run` CLI bypass the F17 lead gate.** `mcp_server.py:111-112`
(`move_task` → engine default `trigger_agents=True`), `runner.py:876-900` (`_create_run` checks
`enabled` but never role). F17 only closed the *HTTP* lane-drag path (`api.py:1052-1059`). Any local MCP
client or `docket run` invocation can auto-trigger runs regardless of role. This is dev-local, but it
means the "explicit `/run` is lead-only" guarantee is transport-specific. Confidence: **Confirmed**.

**[Low] Fractional-index positions can exhaust float precision.** `engine.py:359-376`. Repeated
insertions between the same two cards halve the gap each time with no rebalancing; ~50 inserts collide.
Fix: periodic renormalization of a lane's positions. Confidence: **Likely**.

### Security & privacy

**[High] No per-project / tenant authorization.** `api.py:733-747` (`_repo` resolves `?project=` with no
ACL), and every read endpoint is `require_stakeholder`, every write `require_contributor` — all
*global*. A stakeholder in team A can `GET /api/board?project=team-B`, read team B's tasks, runs, and
`.claudster/` artifacts (`api.py:1167-1169`); a contributor can create/move/delete cards in any
registered project. Combined with auto-provisioning (below), the blast radius is the whole hub. Fix:
per-project membership/role, or at minimum a project allowlist per user. Confidence: **Confirmed**.

**[High] First-seen NTLM identities auto-provision with no gate (F20/F21 detail).** `api.py:437-446`.
`get_current_user` trusts `X-Remote-User` (loopback + optional shared secret is the only boundary; the
sidecar sends no secret today — `api.py:885-893`, `cli.py:114-124`), and any unknown username is
silently `create_user(..., "stakeholder")`. There is no allowlist, no pending/approval state, no
notification to a lead. On a domain-joined deployment behind the proxy, every employee who opens the URL
becomes a provisioned stakeholder with read access to *all* boards and artifacts. Fix: provision into a
"pending/no-access" state a lead must approve, or an explicit allowlist; log/notify on first-seen.
Confidence: **Confirmed**.

**[Medium] Global attachment store is cross-project readable.** `api.py:1345-1369`; `engine.py:1089-1091`.
Blobs live under `DOCKET_HOME/attachments` keyed by ULID, and `GET /api/attachments/{id}` only checks
`require_stakeholder` and the id format — never that the requester's active project (or any project)
references it. A stakeholder with any attachment id reads it regardless of which board it belongs to.
IDs aren't guessable, but there's no scoping. Fix: verify the attachment is referenced by a task in a
project the user may see. Confidence: **Confirmed**.

**[Medium] Untrusted task text flows into agent prompts.** `runner.py:147-162` (`_PROMPT_TEMPLATE`
embeds title/description), `186-199` (`_implement_prompt`). Any bug-filer (any authenticated user,
including auto-provisioned stakeholders — `create_task` allows `type=bug` for all, `api.py:1016-1028`)
controls description text that is concatenated into a headless coding agent's prompt. F6 hardened only
the *gate verdict* parsing; the implement/PRD body prompt is still injectable ("ignore the plan, do X").
`_guarded_env` keeps the claudster guard on (`runner.py:495-501`), which limits but doesn't eliminate
this. Fix: delimit/fence untrusted fields explicitly and instruct the agent to treat them as data.
Confidence: **Likely/Speculative**.

**[Low] Dev CORS origin is allowed in prod.** `api.py:917-922`.
`allow_origins=[http://localhost:5173]` with `allow_methods/headers=["*"]` is added unconditionally. No
credentials cookie exists post-NTLM, and the header is proxy-injected, so exploitability is low, but
it's needless surface in prod. Confidence: **Confirmed**.

### UI / UX

**[Medium] Stakeholders get a write-shaped card drawer that silently 403s.** `CardDrawer.tsx` — only
the Triage section is gated by `role !== "stakeholder"` (line 191). The title input (224-231),
description (232-241), Move-to-lane / Priority / Type selects (245-289), Archive (145-149), and Delete
(170-177) all render for stakeholders and fail on interaction, surfacing a generic `actionError` (or,
for some paths, throwing `AuthError` which boots them to the not-authorised gate via `client.ts:76`).
Fix: disable/hide mutating controls for read-only roles. Confidence: **Confirmed**.

**[Low] `BugForm` shows the attachment picker to stakeholders whose uploads 403 (F25 not present on the
audited `main`).** `BugForm.tsx` (no role gate on `main` at audit time); the upload endpoint is
`require_contributor` (`api.py:1311-1315`). A stakeholder attaches a screenshot, upload 403s, the
mutation loops on "retry to upload them" (`BugForm.tsx:56-61`) forever. **The F25 fix
(`canAttach = role !== "stakeholder"`, commit `332b0e7`) exists on `feat/ux-correctness` but was not yet
merged to `main` at audit time** — so on the audited baseline this was live; confirm it lands with the
next merge. Fix: merge the F25 gate, or allow stakeholders to attach to bugs they file. Confidence:
**Confirmed** (on the audited `main`).

**[Low] Command Center empty-state copy misleads non-leads.** `CommandCenter.tsx:290` — "Move a card
into an agent lane to kick one off." Post-F17, a contributor's move does *not* kick anything off, and
nothing runs if the track is disabled or no runner is attached. Fix: "A lead runs an agent from a card
in an agent lane." Confidence: **Confirmed**.

**[Low] "Linked plan — move to In Progress to link a plan" only true when `repo_projection` is on.**
`CardDrawer.tsx:364`; the handoff is gated by `repo_projection` (`engine.py:604`). On a board with
projection off (the default, `config.py:110`), the instruction never comes true. Confidence: **Likely**.

### Accessibility

(F30–F34 shipped; only fresh items below.)

**[Low] Emoji/glyph buttons rely on `title`/text with no dedicated label in places.**
`CardDrawer.tsx:178-180` (the `✕` close uses text only), `632` (`📄` is `aria-hidden` but the link text
carries the filename — OK). The drawer close `✕` has no `aria-label` (BugForm's does,
`BugForm.tsx:108`). Minor. Confidence: **Likely**.

**[Low] `window.confirm` for the exec-field save (`Settings.tsx:86-88`)** is a native modal outside the
app's focus model; screen-reader/focus behavior is inconsistent with the custom dialogs the a11y pass
built. Confidence: **Speculative**.

### Workflow & ease-of-use

**[Medium] Renaming a lane orphans its agent behavior with no signal.** `Settings.tsx:132-144`
(free-text lane rename), `api.py:621-627` (`agent_track.lanes` is read-only, not in `_EDITABLE_AGENT`),
`api.py:682-699` (`_validate_merged_config` only checks `auto_advance_to`, and only for lanes still on
the board). Renaming "Implement"→"Build": if the lane holds tasks the patch is rejected
(`api.py:1575-1583`, good), but an *empty* agent lane renames freely and its
`agent_track.lanes["Implement"]` config becomes dead — the pipeline lane silently stops working, with no
way to re-key it from the UI. Fix: validate that configured agent lanes exist on the board (or migrate
the key on rename). Confidence: **Confirmed**.

**[Low] The path "add project → enable agents → run a lane" has a silent dead-end in prod.**
`api.py:494-521` + `CommandCenter.tsx:230-239`: with `DOCKET_RUNNER=0` (prod, `cli.py:130`) and no
worker, agent-enabled boards show runs stuck `queued` with only a small banner. A first-time lead who
enables agents in prod sees nothing happen. The banner helps; a disabled "Run agent" with the reason
inline (`CardDrawer` already does this at `393-394`) is better than the queue-forever path via lane
drag. Confidence: **Likely**.

### Consistency & maintainability

**[Medium] The "every write is serialized" invariant is documented but not uniformly enforced** — see
`unarchive_task` above. The two mechanisms (inline decorator vs. wrap-loop) make it easy to add an op
and forget both. Fix: a single registration point or a test asserting every public write in `engine` is
wrapped. Confidence: **Confirmed**.

**[Low] Thin tests around the newest risky paths.** No test asserts `unarchive_task` serialization;
`wip_limits` has no behavioral test (because there's no behavior). The runner's worktree-contamination
case (dirty tree + implement) isn't covered. Confidence: **Likely** (based on the missing decorator
surviving to `main`).

**[Low] Legacy `hash_password`/`password_hash` column still live** (`auth.py:66-68`,
`auth_store.py:42`) though NTLM never checks a password; the `_NTLM_NO_PASSWORD` sentinel and bcrypt
import linger. Harmless but confusing dead weight. Confidence: **Confirmed**.

## 3. UI/UX quick wins (≤5, cheapest-first)

1. **Gate mutating controls in `CardDrawer` behind `role !== "stakeholder"`** (mirror the existing
   Triage gate) — kills a whole class of silent-403 confusion. `CardDrawer.tsx`.
2. **Add a confirm before moving a card into Implement** (or make Implement
   `requires_confirmation:true`) — the single highest-value footgun fix. `config.py:90` /
   `CardDrawer.tsx:248-262`.
3. **Enforce or remove `wip_limits`** — if you can't wire it this cycle, hide the editor so the UI stops
   promising a rule that doesn't exist. `Settings.tsx:152-165`.
4. **Fix the Command Center empty-state copy** to say a *lead* runs agents. `CommandCenter.tsx:290`.
5. **Merge the F25 BugForm role gate to `main`** — it's already written, just absent from the audited
   baseline (now merged as of the `feat/ux-correctness` merge, if that landed after this audit ran).

## 4. Systemic themes

1. **The authorization model doesn't match the deployment shape.** Roles are a single global rank, yet
   docket is a multi-project hub that auto-provisions every domain user. There is no per-project
   membership and no cross-project isolation for boards, artifacts, or attachments (findings 2, 3, 6, 9).
   For a team-wide rollout this is the structural risk: everyone can see everything the moment they load
   the page.
2. **Config surfaces that aren't wired to behavior.** `wip_limits` (editor, no enforcement) and
   `agent_track.lanes` keys (rename-orphaned, non-editable) are UI promises the engine doesn't keep.
   Each one erodes trust in the whole Settings surface and invites "why didn't my limit work?" tickets.
3. **Safety invariants are asserted in prose but enforced unevenly.** "Every write is serialized"
   (broken by `unarchive_task`), "destructive autonomous runs are confirmed" (true for Ship, false for
   the more destructive Implement), "agent triggers are lead-only" (true for HTTP, false for MCP/CLI).
   The guards are real and thoughtful, but the gaps cluster exactly at the newest features — each new
   op/lane needs to re-earn the invariant, and some don't.
4. **Branch/merge hygiene vs. the audited baseline.** Fixes the team considers "shipped and verified"
   (F25, and the F2–F5/F25 UX pass) lived on feature branches not yet on `main` at audit time; the tree
   even changed branches under this audit. `main` — the stated baseline the wider team would deploy —
   lagged the "fixed" set. Whatever the intended release branch is, it should be made unambiguous,
   because "fixed" and "on main" are not automatically the same thing.
