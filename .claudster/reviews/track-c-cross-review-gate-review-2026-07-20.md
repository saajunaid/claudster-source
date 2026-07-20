# Independent review — docket `feat/cross-review-gate` (68af5d5), 2026-07-20

Reviewed by a claudster code-reviewer agent before merge (merge to docket `main` = prod deploy).
**Verdict: changes-requested — NOT mergeable.** Tests pass (17/17 in an isolated worktree; the e2e
tests genuinely drive docket's real `Runner.run_now` → subprocess path), fail-closed design is mostly
right, but one fail-open hole was confirmed with a PoC and the gate cannot spawn as documented.

## Blocking

### 1. Fail-open: default branch not named `main`/`master` → silent `REVIEW: CLEAN`
`tools/cross_review_gate.py` `_find_base_ref` tries only `main`/`master`. On a repo whose default
branch is e.g. `develop`, no base resolves → `get_diff` falls back to the working tree → the Implement
lane has already committed, so the tree diff is empty → the empty-diff branch emits:

```
{"is_error": false, "result": "No changes to review.\nREVIEW: CLEAN"}
```

…with the review endpoint **never contacted** (PoC: endpoint pointed at a dead port, still CLEAN).
docket's `_review_verdict` sees final-line CLEAN → run `succeeded` → auto-advance. This is a
docket-supported configuration: `runner._default_branch` (src/docket/runner.py:313) resolves
`origin/HEAD` and handles arbitrary default branches.

**Fix:** resolve the base the way docket does (`git symbolic-ref refs/remotes/origin/HEAD`, then
main/master), and/or parse the `{base_sha}..HEAD` range docket already embeds in the `-p` prompt
(runner.py:208 — the wrapper currently parses `-p` into `args.prompt` and discards it). When no base
resolves AND the tree diff is empty → emit `REVIEW: BLOCKING` ("could not determine review base"),
never CLEAN.

### 2. Install-as-documented never spawns (either platform)
The module docstring (tools/cross_review_gate.py:24-26) and the results note's Install section say to
point `agent_track.review_cmd` at "this script's absolute path". docket's `_spawn_phase` does
`Popen([resolved, "-p", …])`; a bare `.py` fails on Windows (`WinError 193`, PoC on this box — and prod
IS Windows Server) and on POSIX the blob is mode 100644 (no exec bit). Every Implement run would die at
the review phase — fail-closed, but the feature is dead as shipped. The branch's own e2e knows this:
`tests/test_cross_review_gate_e2e.py` `_launcher` builds a `.cmd`/`.sh` shim.

**Fix:** ship/document the launcher shim (or teach the runner to spawn `*.py` via `sys.executable`);
set the exec bit for POSIX.

## Should-fix

- `tools/cross_review_gate.py:216` — read-phase network errors escape the `call_llm` except tuple:
  `ConnectionResetError` (OSError, not URLError) and `http.client.HTTPException`/`IncompleteRead`.
  PoC: `run_review` raises despite its "NEVER raises" contract → traceback, empty stdout → docket falls
  to the **same-vendor** secondary classifier (burns a harness call and the cross-vendor property;
  still gate-closed, so not blocking). Fix: `except Exception` around `call_llm` (or add `OSError` +
  `http.client.HTTPException`).
- `classify_verdict` (:168) — CLEAN matches **anywhere**, not final-line anchored (the F6 lesson).
  A model report quoting `REVIEW: CLEAN` mid-body (this repo's own diffs contain both marker strings
  verbatim) suppresses the appended BLOCKING and routes to the classifier. Fix: mirror docket's
  final-line anchoring; append `REVIEW: BLOCKING` when the final line carries no verdict.
- Test gaps: no endpoint-failure case (connection refused / HTTP 500 — the stub only returns 200)
  although the commit message claims that path is covered; no non-`main`/`master` default-branch case
  (would have caught blocking #1).

## Nits

- `build_review_prompt` (:139) claims "working tree, staged + unstaged" even for merge-base..HEAD diffs.
- Fixed 180s LLM timeout (:175); a `REVIEW_TIMEOUT` env would match the config style.
- Untracked files never appear in either diff form (mostly moot given commit-per-phase).

## Positives

e2e tests drive docket's REAL Runner/subprocess path with the real wrapper; ASCII-safe JSON envelope
sidesteps the cp1252 mojibake trap; no secret is ever printed; the appended BLOCKING line is always
final-line even for multi-line error text.

## Process

Fix on `feat/cross-review-gate` (repo `E:\Projects\docket`), TDD, `uv run --extra dev pytest -q`, then
**re-review** (dispatch a code-reviewer agent on `git diff main...feat/cross-review-gate` against this
report). Merge to `main` (= prod deploy) only with the user's explicit go.
