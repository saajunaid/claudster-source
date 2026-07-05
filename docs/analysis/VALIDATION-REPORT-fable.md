# Independent validation report (Fable 5) — 2026-07-05

Independent zero-quota audit of the claudster × docket agentic pipeline on branch
`feat/agentic-pipeline` in both repos. Every suite was re-run from scratch (fakes only — no live
`claude -p`, no agent spawn); the high-risk code paths were read and adversarially probed with throwaway
scripts. No source, config, or test was changed. This report is the only file written.

## Verdict
- **tests:** CONCERNS — docket green (374 pytest + build + 67 vitest); claudster is **3 failed / 246
  passed as it actually runs on this machine**, green (249) only once the ambient guard kill-switch is
  unset. The suite is not hermetic.
- **correctness:** PASS — reducer/engine/runner match their commit messages; determinism + layering hold.
- **robustness:** CONCERNS — a hard crash can wedge a run in `running` forever (cap deadlock); the CLI
  `run` path bypasses the opt-in flag; the refine loop ends on a substring match.
- **security:** PASS — the artifact guards resisted every bypass I threw at them; `sandbox=""` blocks the
  real threat (script execution). One low residual (no CSP → external-resource beacon).
- **status-honesty:** CONCERNS — headline test numbers are stale/optimistic, "never stuck in running" is
  overstated, and a cross-repo contradiction (Tailwind CDN vs sandbox) ships unacknowledged.
- **A8-design:** CONCERNS — the locked invariants have at least one real hole (test-command tampering)
  and one enforcement-timing gap (branch guard), and they lean on a guard that has a global kill switch.

## Test numbers (observed)
- **docket** `.venv\Scripts\python -m pytest tests/ -q` → **374 passed, 1 warning** (97 s).
- **docket web** `npm run build` → **OK** (tsc + vite; 835 kB chunk, pre-existing >500 kB warning only).
- **docket web** `npx vitest run` → **67 passed** (8 files).
- **claudster** `C:\Python\python -m pytest scripts/tests claude-harness/hooks/tests -q`
  **as-invoked in this session → 3 failed, 246 passed.** The 3 failures are all in
  `claude-harness/hooks/tests/test_guard.py` (`test_deny_emits_permission_decision`,
  `test_ask_emits_permission_decision`, `TestKillSwitch::test_guard_disabled_helper`). With
  `CLAUDSTER_GUARD_DISABLED` removed from the environment: **249 passed, 0 failed** (and `test_guard.py`
  alone → 45 passed). Root cause is finding #2 below — not a product regression, but a real
  discrepancy vs the claimed all-green.
- **claudster** `validate_pool.py` (default) → **All pool checks passed**; `--profile claude` → **passed**
  (hook imports resolve; the Dream-Memory packaging fix is present).

Discrepancy vs IMPL-STATUS: it reports the claudster suite as **242/244/249 passed** and docket as
**374** with everything green. docket matches. The claudster suite does **not** pass as the repo is
actually run on this machine (kill-switch active) — 3 fail. IMPL-STATUS never mentions the guard tests
being non-hermetic.

## Findings
Most severe first.

### 1. (Medium) A run orphaned in `running` deadlocks the whole agent track — no crash recovery
`runner.py:365` `_execute` is double-wrapped so any *in-process* exception routes to `fail_agent_run`.
But between `engine.start_agent_run` (status→`running`, `runner.py:381`) and the terminal
complete/fail, a hard stop of the docket process (OS kill, power loss, `serve` restart) leaves the run
permanently `running` — no event ever fails it, and there is **no startup reconciliation** (grep for
`reconcile`/`orphan`/`running` in `runner.py` finds nothing; `start()` at `runner.py:212` only spins the
worker + registers the trigger).
**Failure scenario:** `max_concurrent_runs` defaults to 1 (`config.py:31`). The cap check in
`engine.queue_agent_run` (`engine.py:533`) counts `status in ("queued","running")`. One orphaned
`running` run ⇒ `active(1) >= cap(1)` ⇒ **every** future enqueue raises `OverCapacity` and every
lane-move auto-run is silently dropped (`runner._on_lane_trigger` swallows it, `runner.py:244`). The
track is wedged until a human hand-edits `events.jsonl`. IMPL-STATUS's "a run never gets stuck in
`running`" is only true for exceptions, not process death.
**Fix:** on `Runner.start()`, scan the board for `status=="running"` (or `queued`) runs with no live
worker and `fail_agent_run(error="orphaned by restart")` them before draining the queue. Cheap, and it
restores the cap.

### 2. (Medium) Guard tests are non-hermetic — they inherit `CLAUDSTER_GUARD_DISABLED` from the ambient env
`claude-harness/hooks/tests/test_guard.py:206,268` and the deny test assert the guard emits a
decision / that `guard_disabled(tmp)` is `False`, but they never `monkeypatch.delenv("CLAUDSTER_GUARD_
DISABLED")`. The kill switch added in `9882a17` (`guard.py:195`) reads the process env first, so on any
machine where the switch is set globally — which is exactly this user's setup
(`~/.claude/settings.json` sets `"CLAUDSTER_GUARD_DISABLED": "1"`) — three tests fail. The falsy-value
test passes only because it sets `"0"` explicitly.
**Failure scenario:** the standard command in the validation prompt (`pytest scripts/tests
claude-harness/hooks/tests -q`) reports **3 failed** for the very user who shipped the kill switch, while
CI on a clean env reports green — a latent, environment-dependent red.
**Fix:** add `monkeypatch.delenv("CLAUDSTER_GUARD_DISABLED", raising=False)` to the enable-path guard
tests (or an autouse fixture that clears it for the whole `test_guard.py` module except the explicit
kill-switch cases).

### 3. (Low–Medium) The `docket run` CLI path bypasses the `agent_track.enabled` opt-in
The stated invariant is "with `agent_track.enabled=false`, ZERO agent effects." That holds for the two
paths with a test: lane-move triggers (`engine._maybe_enqueue_agent_run` checks `enabled`,
`engine.py:110`) and `POST /api/tasks/{id}/run` (`api.py:691`). But `cli.py:91-105` `docket run` →
`Runner.run_now` → `_create_run` (`runner.py:249`) only checks that the lane has a *command*, never
`agent.get("enabled")`. `queue_agent_run`/`enqueue`/`run_now` are likewise unguarded.
**Failure scenario:** a repo with the track configured but `enabled=false`; `docket run DKT-7 --lane PRD`
spawns a real headless `claude -p` — an agent effect while the track is "off." The opt-in test
(`test_runner.py:211`) only exercises `move_task`, so it misses this.
**Fix:** gate `run_now`/`_create_run` (or the CLI `run` handler) on `enabled`, matching the API, OR
document that the CLI is an explicit-intent override and adjust the invariant wording. It's explicit user
action, hence lower severity — but it contradicts the invariant as written.

### 4. (Medium) Visual-companion guidance (Tailwind browser CDN) contradicts docket's `sandbox=""` iframe
`prd.md:46` and `feature-plan.md:35` tell the headless agent it may style the visual with "the Tailwind
CSS **browser** CDN." The Tailwind browser CDN is a `<script src="https://cdn.tailwindcss.com">` that
generates styles at runtime. docket renders the companion in `VisualView.tsx:32` with `sandbox=""`
(**no** `allow-scripts`), so that script never executes and the visual renders **unstyled**. The two
halves were built in separate sessions and the guidance was never reconciled with the sandbox.
**Failure scenario:** an agent follows the (equally-blessed) Tailwind-CDN branch → the human opens the
visual in the drawer and sees raw, unstyled HTML; looks like a rendering bug. Only the inline-`<style>`
branch works.
**Fix:** drop the Tailwind-CDN option from both commands — require inline `<style>` (self-contained,
sandbox-safe, and consistent with the "no external asset" rule already stated on the same line).

### 5. (Low) Refine loop terminates on a substring match in human annotation text
`runner.py:329` ends the multi-turn refine when `"ended" in text.lower()`. Any human annotation that
merely contains the word — "the header ended too abruptly", "the list ended early" — is misread as
session-end and stops the loop after one revise.
**Failure scenario:** a reviewer's legitimate note containing "ended" cuts refinement short; no error,
just a silently truncated loop. (Termination is otherwise sound: bounded `refine_max_rounds=20` +
per-poll timeout, so it can't infinite-loop, and it runs on its own thread so it never blocks the run
worker — those parts check out.)
**Fix:** detect end from a structured lavish signal (exit status / explicit end marker) rather than a
substring of free-text feedback.

### 6. (Low) No CSP on the sandboxed visual iframe — external resources still load
`sandbox=""` correctly blocks scripts/forms/popups/same-origin, so agent-generated HTML **cannot**
execute JS or exfiltrate via script — the primary threat is handled well (verified: this is why the
Tailwind *script* CDN is inert). But `sandbox=""` does not stop passive resource loads, and there is no
`csp` attribute on the iframe, so an `<img src="http://attacker/beacon">` or `<link rel=stylesheet
href=external>` in the companion still fires a request when the drawer opens.
**Failure scenario:** negligible for a self-authored PRD (no secrets to leak), but it does leak "this
artifact was viewed, from this IP, at this time" to an arbitrary host the agent chose to embed.
**Fix (optional):** add `csp="default-src 'none'; style-src 'unsafe-inline'"` to the iframe, or strip
external `src`/`href` at read time. Low priority.

## Status-honesty check
- **"Both suites green / 242(244/249) passed."** Not as the repo runs on this machine — the claudster
  suite is **3 failed, 246 passed** with the guard kill-switch active (finding #2). Green (249) only with
  the env var unset. IMPL-STATUS presents unconditional green.
- **"a run never gets stuck in `running`" / "EVERY failure path routes to `fail_agent_run`."** True for
  in-process exceptions; **false for process death** — no reconciliation exists (finding #1). Overstated.
- **Opt-in "zero agent effects when disabled."** True for moves and the API; the **CLI `run` path is not
  gated** and has no test (finding #3). The claim is broader than what's enforced/tested.
- **Visual companion "shipped + proven live."** The claudster guidance still recommends a Tailwind CDN
  path that docket's sandbox silently breaks (finding #4); the "proven" run presumably used inline
  `<style>`. The contradiction is unmentioned.
- **Accurate claims I confirmed:** the two live-caught fixes are genuinely in place — `config.py:48-51`
  uses `/claudster:*` namespaced commands (no bare `/prd` anywhere), and `runner.py:406` / `:347` resolve
  the exe via `shutil.which(raw_cmd) or raw_cmd` before spawn; no bare `claude` Popen remains. Layering is
  clean — only `engine._commit` calls `store.append_event` (grep-confirmed); the runner calls engine ops
  only. Determinism (`reduce(read_events())==board.json`) and the cap-atomicity fix (the check now lives
  **inside** the serialized `queue_agent_run`, `engine.py:533-537`) are real. The harness adapter seam is
  clean (Claude not hardcoded; Gemini/Codex stubs raise loudly). These match their commit messages.

## A8 design assessment
The locked invariants (no-implement-on-default-branch, runner-runs-tests-itself, fail-if-untested,
mandatory preflight + code-review gates) are the right shape, but I found holes an autonomous implement
could slip through:

1. **Test-command tampering (real hole).** D2 says the runner independently re-runs the suite, with the
   command sourced from `.claudster/PROJECT-FACTS.md` (fallback `agent_track.test_command`). PROJECT-FACTS
   lives **in the repo the implement session is editing**. A session (buggy or adversarial) can rewrite
   the test command to `exit 0` / `pytest -k __none__`, and since the runner reads it **after** the
   session, the "independent" gate runs the neutered command and reports green. Fix: snapshot the test
   command **before** spawning, and fail the run if the diff touches PROJECT-FACTS.md (or the config key).
2. **Branch guard is checked once, at the wrong time (enforcement gap).** "Refuse to implement on the
   default branch" defends the *spawn* moment. But the session has git + `acceptEdits`; nothing stops it
   from `git checkout main && git commit` mid-run. A start-of-run check is not a guarantee. Fix: enforce
   at commit time (a pre-commit hook that refuses the default branch) or verify post-run that every new
   commit landed on `agent/<slug>`, not just that the branch existed at launch.
3. **The guard it leans on has a global kill switch — and it's currently ON.** The A8 defense-in-depth
   story assumes claudster's PreToolUse guard backstops a runaway `acceptEdits` session. But `9882a17`
   added `CLAUDSTER_GUARD_DISABLED`, and this environment sets it to `1` globally
   (`~/.claude/settings.json`). An autonomous implement launched here runs with the guard **fully
   bypassed**. Fix: have the runner refuse to start an Implement run when the kill switch is set (or
   force-clear it for the child), and treat the guard as non-optional for autonomous code-writing.
4. **Internal contradiction in the doc itself.** The LOCKED section (lines 15-26) makes preflight
   **mandatory / must-PASS-before-any-code**; the older "Risks / guards" bullet (lines 124-125) says v1
   "can bypass `fast_track`… preflight becomes an optional pre-step." A builder could implement either.
   Reconcile the text before A8.2 is built.
5. **Code-review gate is advisory and LLM-based.** "Blocking findings ⇒ does not auto-advance; surface
   for the human" — but the code stays committed on the branch, and a run that "succeeded but didn't
   advance" reads as success. Give it a distinct terminal state (e.g. `needs_review`) so a human can't
   mistake a review-blocked run for a clean one, and remember the reviewer is itself a model (not a hard
   guarantee).

Net: the machinery-over-trust intent is sound, but #1 and #3 are ways an autonomous implement reaches
"Validate" (or worse, touches main) without the intended safety actually holding. Address those before
A8 writes code unattended.

## What I could NOT verify (author-claimed, not re-verified — no quota spent)
- **Any live headless behaviour.** The never-ask robustness of `prd.md`/`feature-plan.md` on a bare title
  is a *content lint only* (`test_headless_convention.py` checks wording, not model behaviour). Reading
  the `## Headless mode` sections, the wording is genuinely strong — "NEVER ask", "a bare title is
  sufficient", "asking is ALWAYS wrong here", "invent a reasonable interpretation… state it as an
  assumption" — about as unambiguous as prose enforcement gets. But whether a real `claude -p` obeys it
  on a 3-word card is **author-claimed** (IMPL-STATUS says it was proven via `--plugin-dir`); I did not
  spend quota to re-prove it.
- **B1/B2 live smokes, the real `docket run` E2E, the on-screen A4/A5 UI demos, the S0 lavish spike, and
  real-lavish refine.** All are IMPL-STATUS reviewer claims from live sessions. I re-verified the *code
  paths* behind them (fakes + static review) but not the live runs.
- **Real Windows CTRL_BREAK timeout-kill against a genuine long-running `claude -p`.** Exercised only via
  `fake_claude hang`; the real-process kill is author-claimed.
- **The publish/`junai-push` gating** (opt-in `-Publish`, SHA256 content-diff). Verified by reading
  Track 0 code + `validate_pool` passing; not executed (hard rule).

VALIDATION COMPLETE → docs/analysis/VALIDATION-REPORT-fable.md
