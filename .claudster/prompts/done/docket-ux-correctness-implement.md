# Implement — docket UX & correctness (Fable F2, F3, F4, F5, F25)

You are a senior full-stack engineer. Implement five OPEN docket findings from the Fable audit — the
UX/correctness tail after the reliability/security pass. This is an IMPLEMENTATION task: write the code, test
it (TDD where feasible), verify. Work in `E:\Projects\docket` (backend `src/docket/`, frontend `web/src/`).

Source: `E:\Projects\claudster-source\docs\analysis\fable-audit-docket-2026-07-15.md` (executive layer) and the
status tracker `…\docs\analysis\fable-remediation-status.md` (F2/F3/F4/F5/F25 rows). Read those first. Exact
file:line anchors below were verified against the code on 2026-07-19.

## Ground rules
- **Branch:** create `feat/ux-correctness` off the CURRENT docket `main`. **NEVER push docket `main`** — a push
  to `main` auto-deploys prod via the Gitea pipeline. Feature branch only; hand it back for review/merge.
- **Backend tests:** `.venv\Scripts\python.exe -m pytest tests/ -q` (use the venv python directly; `uv run` may
  fail on a locked `docket.exe` if a docket process is running — if you prefer uv, it's `uv run --extra dev
  pytest -q`). Auth is OFF in the default `TestClient(create_app(repo_path=...))` → the synthetic open-admin
  acts as a lead, so `require_lead`/`require_stakeholder`/`require_contributor` all pass without headers; RBAC
  tests build an ntlm app + header (see `test_api_config.py`, `test_rbac*`).
- **Frontend tests:** `cd web; npx vitest run`. Vitest config is inlined in `web/vite.config.ts` (`jsdom`,
  `globals:false` → import `describe/it/expect/vi` from `"vitest"` explicitly; setup `src/test-setup.ts`).
  Mock role via `vi.mock("../hooks/useAuth", () => ({ useAuth: () => ({ status:"authenticated",
  user:{username:"x"}, role:"stakeholder" }) }))` and API via `vi.mock("../api/client", …)` — see
  `web/src/components/CardDrawer.test.tsx` for the canonical pattern (QueryClientProvider wrapper included).
- **Known flake (NOT your regression):** `tests/test_api.py::test_create_bug_with_fields_via_api` intermittently
  500s under the full suite (Windows subprocess/file timing). Re-run before investigating.
- **Commit per phase**, only the files that phase touches. Flip the matching row in `fable-remediation-status.md`
  (claudster repo) to DONE as each lands. Full suite is ~512 py + ~146 web — keep both green.

---

## Phase 1 — F5: corrupt `events.jsonl` → bare 500 with no escape (Medium-High)
A `json.JSONDecodeError` while replaying the log escapes the OSError handler, so a corrupt events (or board)
file yields FastAPI's bare `500 Internal Server Error` — no file, no offset, and the only escape is deleting
the project.
- **Anchors:** parse sites `store.py:74-85` `read_events` (`json.loads(line)` per line) and `store.py:93-95`
  `read_board`. Propagation: `GET /api/board` (`api.py:930-939`) → `engine.get_board` (`engine.py:400`) →
  `_load_board` (`engine.py:296-306`) → `reduce(read_events(...))` at `engine.py:304`. The only handler is
  `@app.exception_handler(OSError)` `_filesystem_error` (`api.py:921-927`); `JSONDecodeError` subclasses
  `ValueError`, not `OSError`, so it escapes → bare 500.
- **Fix:** wrap the parse in `store.read_events`/`read_board` to raise a domain error (e.g. `engine.CorruptLog`,
  modelled on the existing `TaskNotFound`/`InvalidOperation` domain exceptions the handlers at `api.py:908-914`
  already map) carrying the **file path + line/offset** (`JSONDecodeError` exposes `.lineno`, `.colno`, `.pos`,
  `.msg`). Register a matching `@app.exception_handler` alongside `api.py:921` returning `500` with a
  `detail` that names the file and the byte/line offset (so the operator can find and fix the bad line).
- **TDD (RED first):** write a repo whose `.docket/events.jsonl` has a corrupt line; assert `GET /api/board`
  returns a 500 whose `detail` names `events.jsonl` and the offending line/offset (not a bare 500). No existing
  test covers this — add one near `test_api.py`. A unit test on `read_events` raising the domain error is also
  cheap.
**Commit:** `fix(store+api): surface corrupt events.jsonl with file + offset instead of a bare 500 (F5)`

---

## Phase 2 — F4: archived tasks are unreachable + no unarchive; the "Archived" toggle is dead (High)
`task.archived` is one-way: `/api/board` strips archived tasks (`engine._without_archived`), so the frontend
"Archived" toggle can never receive anything, and there is no unarchive path anywhere (`grep unarchive` = 0).
- **Anchors (backend):** event set `events.py:17` (`EVENT_TYPES`); engine op `engine.py:877-883` `archive_task`
  → `_commit([("task.archived", {"task_id"})])`; API `api.py:1258-1260` `POST /api/tasks/{id}/archive`
  (`require_contributor`); reducer handler `reducer.py:84-89` `_h_task_archived` (sets `archived=True`),
  registered at `reducer.py:396`; strip helpers `_without_archived` (`engine.py:384-388`, used by `get_board`
  `engine.py:400` and `get_tasks` `engine.py:445-448`). Task default `archived:False` at `reducer.py:56`.
- **Anchors (frontend):** dead toggle `BoardToolbar.tsx:134-141` (`spec.include_archived`); filter
  `taskFilter.ts:73-78` + `dnd/dnd.ts:6-8`; URL round-trip `useSearchFilters.ts:37,58`. Archive button on the
  drawer `CardDrawer.tsx:143-149`; two-step confirm precedent `CardDrawer.tsx:56,150-177`; the `act(call)`
  wrapper (`CardDrawer.tsx:69`, mutation 61-68) invalidates `['board']` and surfaces errors. Client helper
  `archiveTask` at `client.ts:298-300`; **no** `unarchiveTask` yet.
- **Fix (backend):** add `task.unarchived` to `EVENT_TYPES`; add `_h_task_unarchived` (mirror archived, set
  `archived=False`, guard `if task is None: return`) registered in `_HANDLERS` (`reducer.py:392-423`); add
  `engine.unarchive_task` (mirror `archive_task`); add `POST /api/tasks/{id}/unarchive` (`require_contributor`,
  mirror `api.py:1258`). Make archived tasks **reachable**: give `get_board`/`get_tasks` a way to INCLUDE
  archived (e.g. `GET /api/board?include_archived=1` → skip `_without_archived`) so the toggle has data. Keep
  the default (no param) stripping archived — don't change the default board payload.
- **Fix (frontend):** wire the "Archived" toggle to request `include_archived` from the board endpoint (thread
  it through `useBoard`/`getBoard`); add an `unarchiveTask` client fn (`POST …/unarchive`) and an **Unarchive**
  button in the `CardDrawer` head-actions, shown only when `task.archived`. Reuse the `act()` wrapper. (Optional
  per the audit's UX-quick-win #2: add a two-step confirm on Archive by cloning the delete-confirm pattern — do
  it only if it doesn't balloon the phase.)
- **TDD:** reducer — `task.unarchived` clears the flag (extend `test_reducer.py:132-137`); engine —
  `unarchive_task` returns ok + flips flag (extend `test_engine.py:184-188`); API — unarchive endpoint flips
  it and `?include_archived=1` returns the archived task while the default omits it (extend `test_api.py:93-98`).
  Web — a `CardDrawer` test that the Unarchive button shows for an archived task and calls `unarchiveTask`.
**Commit:** `feat(engine+api+web): add task.unarchived + include_archived board view + drawer Unarchive (F4)`

---

## Phase 3 — F3: default agent-track config references lanes the board lacks (High)
`AGENT_TRACK_DEFAULT.lanes` keys are `PRD/Plan/Implement/Ship` with `Implement.auto_advance_to = "Validate"`
(`config.py:82-91`), but `DEFAULT_LANES = [Triage, Inbox, Backlog, In Progress, In Review, Done]`
(`config.py:17`). None of the agent lanes (nor `Validate`) exist on a default board, so triggers and
auto-advance silently no-op. Both `auto_advance_to` consumers swallow the resulting `InvalidOperation`
(runner `runner.py:1398-1404`; remote-complete `api.py:1240-1245`), and `_maybe_enqueue_agent_run`
(`engine.py:105-124`) can never fire because the target lane never exists → invisible breakage.
- **Fix:** add lane-consistency validation modelled on the existing checks in `_validate_merged_config`
  (`api.py:662-681`, which already validates `done_lane ∈ lanes` and `wip_limits` keys ∈ lanes). Validate that,
  for the merged config, **every agent_track lane key that is intended to be active exists in `lanes`, and every
  non-null `auto_advance_to` exists in `lanes`.** Decide enforcement with fail-closed-on-write / fail-open-on-read
  discipline: a `PATCH /api/config` (`api.py:1534`) that would leave the agent track enabled while its trigger
  lanes / advance targets are missing must be **rejected** (400 with a clear message naming the missing lanes);
  at load time (`load_config`/`_ensure_agent_track`, `config.py:176-219`) surface a structured warning rather
  than 500 (a dormant default board must still load). Do NOT silently reconcile by mutating the user's lanes.
  Note `agent_track.lanes` is not in the PATCH whitelist (`_EDITABLE_AGENT` `api.py:622-627`), so the practical
  guard is: when `lanes`/`done_lane`/agent-enable change, re-validate agent_track references against the new
  lane set.
- **TDD:** a merged config whose agent track is enabled but whose `auto_advance_to` / trigger lane is absent
  from `lanes` fails `_validate_merged_config`; the default 6-lane board (agent track dormant) still loads and
  validates; a PATCH that removes a lane an active agent trigger depends on is rejected. Config-validation tests
  live in `test_api_config.py`; defaults in `test_config.py:38-107`.
**Commit:** `fix(config+api): validate agent_track lanes/auto_advance_to against board lanes (F3)`

---

## Phase 4 — F2: pipeline preset seeds a card into a lane that doesn't exist yet (Medium)
`applyPipelinePreset()` (`Settings.tsx:92-102`) stages the pipeline lanes into the **local draft only**
(`setDraftKey("lanes", …)` line 93 — persisted only on Save) but immediately calls `createTask(…, {lane:
"Ideas"})` (line 95) against the server, before the "Ideas" lane exists — and swallows the failure with
`.catch(() => {})` (line 100, the only such swallow in `web/src`).
- **Anchors:** button wiring `Settings.tsx:201`; save mutation `save = useMutation({ mutationFn: patchConfig,
  onSuccess … })` `Settings.tsx:40-50`; `onSave()` diff+mutate `Settings.tsx:78-90`; `PIPELINE_LANES`
  (incl. `"Ideas"`) `Settings.tsx:10`; `onError` message precedent `Settings.tsx:49`.
- **Fix:** move the explainer-card `createTask(...)` OUT of `applyPipelinePreset` and INTO the save `onSuccess`
  (`Settings.tsx:42-48`), gated so it only seeds when the pipeline preset was just applied (e.g. a `pendingSeed`
  ref/flag set by `applyPipelinePreset`, consumed + cleared in `onSuccess` after `patchConfig` persisted the
  lanes). Stop swallowing: on card-create failure, surface via `setMsg(...)` (the `onError` pattern), never
  `.catch(()=>{})`.
- **TDD:** a `Settings` web test — applying the preset then saving creates the card only after the config patch
  resolves (assert `patchConfig` called before `createTask`, and `createTask` receives `lane:"Ideas"`); a
  `createTask` rejection surfaces a visible message rather than being swallowed.
**Commit:** `fix(web/settings): seed pipeline explainer card in save onSuccess, surface failures (F2)`

---

## Phase 5 — F25: "Report bug" shows stakeholders an attachment picker that 403s (Medium-High)
`BugForm` shows the screenshot/attachment picker to ALL roles, but `POST /api/tasks/{id}/attachments` is
`require_contributor` (`api.py:1278-1283`), so a stakeholder can create the bug (`POST /api/tasks` is
`require_stakeholder`, `api.py:985`) but every upload 403s — an impossible retry loop (`BugForm.tsx:49-61`).
- **Anchors:** picker JSX `BugForm.tsx:144-171` (`<input type="file" … aria-label="Attach screenshots">`);
  paste/drop handlers `BugForm.tsx:79-86` + form `onPaste` line 104; retry loop `BugForm.tsx:49-61`; misleading
  docstring `BugForm.tsx:9-14`. Role source `useAuth()` (`hooks/useAuth.ts:32`, `role = user?.role`); tiers
  `"stakeholder" | "contributor" | "lead"`. Precedent gating: `Sidebar.tsx:388,465` (`{role === "lead" && …}`).
- **Fix:** in `BugForm.tsx`, `const { role } = useAuth()` (import from `../hooks/useAuth`); wrap the dropzone
  block (144-171) in `{role !== "stakeholder" && (…)}`, and skip the paste-to-attach wiring + `files` machinery
  for stakeholders so no upload is attempted. Correct the docstring (9-14). Bug creation itself stays available
  to every role.
- **TDD:** a `BugForm` web test — with `role:"stakeholder"` the attachment picker is NOT rendered and submitting
  never calls `uploadAttachment`; with `role:"contributor"` the picker IS rendered (mirror `CardDrawer.test.tsx`
  role/API mocks).
**Commit:** `fix(web/bugform): hide attachment picker for stakeholders — no impossible 403 retry loop (F25)`

---

## Verification (before done)
- Full py suite green (mind the known bug-create flake — re-run if it trips) + `npx vitest run` green + web
  build clean (`cd web; npx tsc --noEmit` / `npm run build` if configured).
- F5: hit a hand-corrupted `events.jsonl` and confirm the API `detail` names the file + offset.
- F4: exercise archive → toggle Archived (data appears) → Unarchive → it returns to its lane, end-to-end
  against the dev server.
- Write a short results note into docket `docs/analysis/`.

## Output
A `feat/ux-correctness` branch, one commit per phase, both suites green, results note. Do NOT push `main` —
hand the branch back for review/merge (merging `main` deploys prod). Flag anything left partial (e.g. the
optional Archive-confirm, or F3's enforcement scope if a full default-reconcile proves too invasive).
