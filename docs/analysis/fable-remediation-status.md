# Fable audit — remediation status tracker

**This is the single source of truth** for the two Fable audits (2026-07-15) of claudster + docket and
everything done since. Living status of every finding (from `fable-audit-claudster-2026-07-15.md` and
`fable-audit-docket-2026-07-15.md`) plus the strategic Tracks A/B/C that grew out of the same effort.
**DONE** = fixed + tested + committed. **PARTIAL** = the worst part is fixed, a slice remains.
**OPEN** = not started. Updated 2026-07-20.

## Documents map — what drives what

| Purpose | Document |
|---|---|
| **This tracker** — per-finding DONE/OPEN status | `docs/analysis/fable-remediation-status.md` (you are here) |
| **Driver prompt for the remaining backlog** — hand to a fresh session to continue | `.claudster/prompts/driver-remaining-toolchain-work.md` (update its "queue" section — items 1–3 are now done; the remaining queue is below) |
| Strategic plan (Track 0 hardening + Tracks A/B/C) | `.claudster/plans/oss-model-lanes-and-public-readiness.md` |
| Audit executive summaries (Top-10 + themes only) | `docs/analysis/fable-audit-{claudster,docket}-2026-07-15.md` |
| Track B privacy sweep + docket team-usability report | `docs/analysis/PUBLIC-READINESS.md` |
| Implementation specs used for the docket passes | `.claudster/prompts/done/docket-{accessibility,reliability-security,ux-correctness}-implement.md` |

> ⚠ **Known gap:** the full per-finding detail (file:line, failure scenario, fix, confidence) for the
> docket audit's F1–F39 existed only in the audit session transcript — only the executive layer was saved
> to disk. Everything fixed so far had its detail re-derived in the implementation specs. The remaining
> ~18 medium/low docket findings (F7–F10, F14–F16, F18–F19, F22–F24, F26–F29, F35–F39) are **numbers
> without saved descriptions**; closing them requires re-running a scoped Fable inspection on docket
> (reuse `.claudster/prompts/fable-inspect-docket.md`, excluding the fixed areas) to regenerate the tail.

## Scoreboard (2026-07-20)

- **All Critical/High findings in both repos: CLOSED and deployed.**
- claudster: 17 findings DONE (test-coverage + rebrand tails closed 2026-07-20), 1 OPEN (human: token
  rotation + marketplace v0.4.0 deletion), 1 OPEN new (pipeline-runner suite broken, pre-existing).
- docket: 14 findings DONE (incl. all of F30–F34 a11y), 1 PARTIAL (F12 worktree isolation), ~20 OPEN
  (F20/F21 + the untracked medium/low tail).
- Tracks: **A DONE** (shipped 2026-07-19) · **B B1/B2/B3 DONE, B4 awaits the user** · **C
  code-complete but NOT mergeable** — branch `feat/cross-review-gate` pushed 2026-07-20; independent
  review returned **changes-requested with 2 blocking issues**: (1) fail-open — a repo whose default
  branch isn't `main`/`master` yields an empty diff → `REVIEW: CLEAN` with the endpoint never called
  (PoC-confirmed; docket itself supports arbitrary default branches via `origin/HEAD`); (2) the
  install doc points `review_cmd` at the bare `.py`, which cannot spawn (Windows `WinError 193`;
  no POSIX exec bit) — needs the launcher shim the e2e tests already use. Plus should-fixes:
  uncaught read-phase socket errors, and `classify_verdict` matching CLEAN anywhere instead of
  final-line (the F6 lesson). Fix on the branch before merge.

## claudster
| # | Finding | Status | Where |
|---|---------|--------|-------|
| 1 | Internal deploy runbook (`iegbcoppoc02`/`gitea.internal`/`VMIE_BOT_TOKEN`) in the public `claude-extras` bundle | **DONE** | genericized `deploy-local` + windows-deployment + devops-agent + enterprise-recipe (84f662f, 4d5536c); **republished** & verified clean via `git grep` on the mirror |
| 3 | Privacy gate can't catch the leak (denylist only `vmie-`) | **DONE** | broadened `validate_pool` PRIVACY_SUBSTRINGS (4d5536c); extended again in Track B2 with 6 codename/tool patterns + tests (29784d2) |
| 5 | Dream Memory hitCount inflation (80-char head collision) | **DONE** | full-command fp (42c1e1f) |
| 6 | Guard POSIX-only — misses `Remove-Item -Recurse -Force`/`rmdir /s` | **DONE** | 889d563 |
| 7 | Guard misses force-push via `+refspec` | **DONE** | 889d563 |
| 8 | `sync.ps1` push-failure reported as success | **DONE** | `$LASTEXITCODE` checks (a58d29e) |
| 9 | Guide's `/claudster:cross-review` doesn't resolve | **DONE** | added core command (dccc4cd) |
| 10 | Personal paths + credential-incident handoff in public files | **DONE** | genericized guide + copilot-instructions + commands (84f662f, 274bc16); removed handoff + `.archive/pipeline` (4d5536c, ac25092) |
| 2 | `junai-mcp` ships an unauthenticated shell-exec tool | **DONE** | `run_command` gated: opt-in `JUNAI_ENABLE_RUN_COMMAND` (off by default) + arg-array `create_subprocess_exec` (no shell → no `;`/`&&`/`\|` chaining) + executable allowlist (`JUNAI_RUN_COMMAND_ALLOWLIST` override). Applied to canonical pool copy `.github/tools/mcp-server/server.py` **and** the PyPI mirror `src/junai_mcp/server.py` (byte-identical); 10 RED-first gate tests |
| 4 | Live credential files in the working tree | **OPEN (human)** | gitignored/untracked → rotate the 3 tokens (`pypimcp.key`, `vscode.pat`, `ptarmigan.pat`) + delete VS Code `junai-labs.junai` v0.4.0 at the marketplace hub (bundled a since-rotated PAT) |
| — | Exporter silently drops phantom skills / missing sources never fail export | **DONE** | `export_runtime_resources.py` fail-closed: `_validate_skill_roster` + `ExportStats.errors` → `main()` returns 1 on any phantom skill or missing declared source. Removed the 5 stale `codex`/frontend phantoms from `runtime-targets.json`; canonical export still exits 0 (verified) |
| — | Copilot→Claude conversion implicitly grants `Bash` to read-only agents | **DONE** | `convert_tools_to_claude_format` no-mapped-tools default tightened to `[Read, Grep, Glob]` (was `+Bash`); explicit `execute` still maps to Bash |
| — | Redaction misses `-pPASSWORD` / `aws_secret_access_key <k>` shapes | **DONE** | `dream_capture.redact` gained `_MYSQL_PW` (mysql-family `-pVALUE` glued), `_CURL_USERPASS` (`curl -u user:pass`), `_AWS_CRED` (space-separated `aws_secret_access_key <k>`); all command-scoped so `cp -pr`/`python -u`/`docker -p 8080:80` survive. 8 new TDD cases incl. false-positive guards |
| — | `session_end` cost model bills GLM/DeepSeek/local as Sonnet | **DONE** | `PRICING_PER_MTOK` + `_tier` gained glm/deepseek/qwen/kimi tiers and a `local` (zero-cost) tier for ollama/self-hosted; unknown hosted still falls back to sonnet. Subprocess TDD asserts OSS < sonnet and local == 0 |
| — | Cross-repo fact contamination (`_repo_root` uses launch cwd) | **DONE** | both state-anchoring hooks now use the payload `cwd` (session repo), not the hook process's launch cwd: `session_end.py` (Dream Memory store + usage log) and `inject_relay.py` (relay/usage resolution). Mirrors guard.py's `data.get("cwd") or os.getcwd()`. 2 TDD cases (session cwd wins over process cwd) |
| — | `validate_agents` MCP-note hard-fails the build | **DONE** | `smoke_test_mcp_server` now returns `(errors, notes)`; new `_diff_mcp_tools` routes extra/new tools and skips to NOTES (printed `[NOTE]`), only genuine failures to errors. Exit keys on `mcp_errors` only, so adding an MCP tool no longer fails the build. 4 TDD cases |
| — | No tests around export/validate/sync.ps1 | **DONE** | export (11 tests) + `validate_pool` privacy regression tests (29784d2) + `scripts/tests/test_sync_ps1.py` (8 tests, 2026-07-20: pwsh syntax-parse, BOM/ASCII encoding lock, every-`git push`-checks-`$LASTEXITCODE`, entry points, opt-in publish, privacy markers). The RED run exposed **4 push sites still reporting success on failure** (profile export, `junai-revert` source + 2 cascade pushes) — all fixed |
| — | Rebrand half-applied (`agent-sandbox` in deep docs) | **DONE** | 2026-07-20 sweep: `sync.ps1` (13), orchestrator agent, `setup_project_ai`/`usage_review`/`agent_manager`, pipeline-runner test fixtures, both drawio diagrams, RECIPE-RUNBOOK → `claudster-source`; historical mentions in `validate_pool.py`/`runtime-targets.json` → "predecessor repo". (`agent-workflow-design-reference.md` was already clean — the "63 refs" were in gitignored mirror copies.) Historical analysis docs (`pass1-foundations.md`) deliberately untouched |
| — | pipeline-runner test suite broken — `.github/pipeline-state.template.json` missing → 17 of 138 tests fail (pre-existing; found 2026-07-20; not in the standard gate so unnoticed) | **OPEN** | decide keep-vs-retire: the Copilot-era pipeline-runner is superseded by docket's pipeline; either restore the template or retire the tool + tests |

## docket
> **Deployed to prod (2026-07-17, `096cbb3`):** F1, F17, F12-partial + the full F30–F34 accessibility set
> — clean auto-merge, web build + 143 web + 496 py green; Gitea `deploy` **success**.
>
> **Deployed to prod (2026-07-17, `855d41c`):** F6, F11, F13 — independently re-verified before merge
> (512 py + 146 web + tsc/vite clean); Gitea `python_tests` → `web_checks` → `deploy` all **success**.
> Review follow-up: two stale lock-path comments corrected (`0a81586`) — the F11 file lock lives at
> `DOCKET_HOME/runtime/locks/<sha256>.lock`, deliberately NOT inside `.docket/` (attach-repo renames it
> on Windows).
>
> **On docket `main`, awaiting deploy confirmation (2026-07-19, merged via `feat/ux-correctness`):**
> F2, F3, F4, F5, F25 (commits `673e51f…332b0e7`; results note
> `E:\Projects\docket\docs\analysis\ux-correctness-F2-F3-F4-F5-F25-results.md`).

| # | Finding | Status | Where |
|---|---------|--------|-------|
| F1 | `requires_confirmation` a no-op → Ship-drag auto-deploys prod | **DONE** | backend enforce (06b7cdc) + lead-only confirm UI (1e59da1) |
| F17 | Contributor lane-drag auto-triggers runs (bypasses lead gate) | **DONE** | a76a5e9 |
| F30–F34 | Accessibility (no keyboard DnD, non-dialog drawers, focus, contrast, no live region) | **DONE** | `feat/a11y` 710f89d…4f21dfa; 138 web tests + keyboard Playwright walkthrough |
| F12 | Implement hijacks the human's working tree | **PARTIAL** | crash-leftover guard self-heal shipped (e8a369b); **full worktree isolation OPEN** (needs live Implement run — design + subtleties in the plan's Track 0 §F12) |
| F11 | Cross-process ID race on `.docket/` (in-memory locks only) | **DONE** | `feat/reliability` — reentrant `_RepoLock` (in-memory RLock + msvcrt/fcntl file lock under `DOCKET_HOME/runtime/locks/`) around `@_serialized`; deterministic cross-process mutex + 4-process id-race tests (7d1b66d) |
| F6 | Gate verdicts substring-matched over the whole transcript (spoofable via task text) | **DONE** | `feat/reliability` — positive verdict anchored to the final non-empty line (`_final_line`); blocking still matches anywhere (fail-closed); RED-first injection tests (9347583) |
| F13 | Stuck runs wedge the WIP cap (reconcile only at startup) | **DONE** | `feat/reliability` — periodic reconcile task in the FastAPI lifespan (liveness-aware: heartbeat for remote, `_active` set for local) + lead-only `POST …/runs/{rid}/cancel` + two-step Command Center "Cancel run" button (139d2db) |
| F5 | Corrupt `events.jsonl` → bare 500, no escape | **DONE** | `feat/ux-correctness` — `store.read_events`/`read_board` raise domain `CorruptLog` (file + line/offset); engine re-exports, api handler returns 500 with that detail. Unit + endpoint TDD (673e51f) |
| F4 | Archived tasks unreachable + no unarchive; dead toggle | **DONE** | `feat/ux-correctness` — `task.unarchived` event + reducer handler, `engine.unarchive_task`, `POST /api/tasks/{id}/unarchive`, `GET /api/board?include_archived=1`; web: `useBoard(includeArchived)` + drawer Unarchive button. TDD reducer/engine/api + CardDrawer (d9b2265) |
| F2 | Pipeline-preset seeds a card into a lane that doesn't exist yet | **DONE** | `feat/ux-correctness` — `applyPipelinePreset` only stages lanes + arms a `pendingSeed` ref; the explainer card is created in the save `onSuccess` (after lanes persist), with seed failures surfaced not swallowed. Settings web TDD (75fcbda) |
| F3 | Default agent-lane config references lanes the board lacks | **DONE** | `feat/ux-correctness` — `_validate_merged_config` rejects a config where an agent-track lane present on the board auto-advances to a missing lane. Dormant agent lanes not checked, so the default agent-disabled board stays valid. TDD (8802888) |
| F25 | "Report bug" promises stakeholders uploads that 403 | **DONE** | `feat/ux-correctness` — `BugForm` reads `useAuth().role`; attachment picker + paste-to-attach render only for contributor+. Bug creation stays open to all roles. Web TDD (332b0e7) |
| F20/F21 | NTLM trust rests on loopback; first-seen users auto-provision | **OPEN** | prefer `DOCKET_PROXY_SECRET`; opt-in provisioning. Note the tension recorded in `PUBLIC-READINESS.md` B3: this same mechanism is what makes zero-setup teammate onboarding work — the fix must keep that (e.g. secret + provisioning default-on but toggleable) |
| F7–F10, F14–F16, F18–F19, F22–F24, F26–F29, F35–F39 | assorted medium/low correctness/UX/maintainability (~18 findings) | **OPEN — descriptions not on disk** | detail existed only in the audit transcript (see the Known gap note above). Recoverable hints from the exec summary's "UI/UX quick wins": render the API `detail` on board-load error + inline "Remove project"; a "this runs `<command>` on the server" line/tooltip on auto-triggering lanes. To work this tail: re-run a scoped `fable-inspect-docket.md` audit excluding the fixed areas, save the FULL findings this time, then spec + implement |

## Tracks A/B/C (the strategic plan, same document family)

| Track | Status | Evidence |
|---|---|---|
| **A — model-switching as a claudster feature** | **DONE** (2026-07-19) | `oss_model.py` resolver (bc4c907), `claude-oss` launchers, `/claudster:use-model` + setup install (aa62ffc), shipped `junai-push` (dc3de43) |
| **B — claudster public-readiness** | **B1/B2/B3 DONE (2026-07-20); B4 OPEN (human)** | LICENSE (MIT) + public README (386b6d6); privacy sweep — 12 findings genericized/excluded + scanner hardening (29784d2, `PUBLIC-READINESS.md`); docket team-usability verified with 2 doc fixes (5616cdb). **B4 = the user decides whether/where to publish** |
| **C — cross-vendor review gate in the pipeline** | **code-complete; review = changes-requested (2 blocking)** | docket branch `feat/cross-review-gate` pushed 2026-07-20; results `E:\Projects\docket\docs\analysis\track-c-cross-review-gate-results.md`. Blocking: non-`main`/`master` default branch fail-opens to CLEAN; bare-`.py` `review_cmd` never spawns (WinError 193 / no exec bit). **Full review: `.claudster/reviews/track-c-cross-review-gate-review-2026-07-20.md`.** Fix on the branch, re-review, then merge (= prod deploy) with the user's go |

## Remaining work — the definitive queue

Work these from this tracker; per-item detail lives where each row points.

**Human-only (no code):**
1. Rotate the 3 tokens (`pypimcp.key`, `vscode.pat`, `ptarmigan.pat`) — claudster #4.
2. Delete VS Code `junai-labs.junai` v0.4.0 at the marketplace hub (browser-only).
3. Track B4 — decide whether/where to publish claudster publicly.

**docket (feature branches only — NEVER push docket `main`, it deploys prod):**
4. Fix the 2 blocking review findings on `feat/cross-review-gate` (+ the should-fixes: broaden the
   `call_llm` except tuple, final-line-anchor `classify_verdict`, add endpoint-failure +
   non-`main`-default-branch tests), re-review, then merge with the user's explicit go (= prod deploy).
5. F20/F21 — `DOCKET_PROXY_SECRET` + opt-in auto-provisioning (keep zero-setup onboarding viable).
6. The medium/low tail (~18 findings) — **first regenerate the findings** (scoped re-audit via
   `.claudster/prompts/fable-inspect-docket.md`, persist the full detail), then spec via a
   `docket-*-implement.md` prompt and implement.
7. F12 full worktree isolation — design + correctness subtleties in
   `.claudster/plans/oss-model-lanes-and-public-readiness.md` Track 0; needs a LIVE Implement run to verify.

**claudster:**
8. pipeline-runner suite: 17 pre-existing failures (missing `.github/pipeline-state.template.json`) —
   decide keep-vs-retire (superseded by docket's pipeline), then restore the template or retire the tool.

_(Closed 2026-07-20: sync.ps1 test coverage — which also exposed and fixed 4 more unchecked pushes —
and the `agent-sandbox` rebrand tail.)_
