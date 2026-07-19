# Fable audit — remediation status tracker

Living status of every Fable finding (from `fable-audit-claudster-2026-07-15.md` and
`fable-audit-docket-2026-07-15.md`). **DONE** = fixed + tested + committed. **PARTIAL** = the accessible/
worst part is fixed, a slice remains. **OPEN** = not started. **WON'T-FIX / N/A** = deliberate.
Updated 2026-07-17.

## claudster
| # | Finding | Status | Where |
|---|---------|--------|-------|
| 1 | Internal deploy runbook (`iegbcoppoc02`/`gitea.internal`/`VMIE_BOT_TOKEN`) in the public `claude-extras` bundle | **DONE** | genericized `deploy-local` + windows-deployment + devops-agent + enterprise-recipe (84f662f, 4d5536c); **republished** & verified clean via `git grep` on the mirror |
| 3 | Privacy gate can't catch the leak (denylist only `vmie-`) | **DONE** | broadened `validate_pool` PRIVACY_SUBSTRINGS (4d5536c) |
| 5 | Dream Memory hitCount inflation (80-char head collision) | **DONE** | full-command fp (42c1e1f) |
| 6 | Guard POSIX-only — misses `Remove-Item -Recurse -Force`/`rmdir /s` | **DONE** | 889d563 |
| 7 | Guard misses force-push via `+refspec` | **DONE** | 889d563 |
| 8 | `sync.ps1` push-failure reported as success | **DONE** | `$LASTEXITCODE` checks (a58d29e) |
| 9 | Guide's `/claudster:cross-review` doesn't resolve | **DONE** | added core command (dccc4cd) |
| 10 | Personal paths + credential-incident handoff in public files | **DONE** | genericized guide + copilot-instructions + commands (84f662f, 274bc16); removed handoff + `.archive/pipeline` (4d5536c, ac25092) |
| 2 | `junai-mcp` ships an unauthenticated shell-exec tool | **DONE** | `run_command` gated: opt-in `JUNAI_ENABLE_RUN_COMMAND` (off by default) + arg-array `create_subprocess_exec` (no shell → no `;`/`&&`/`\|` chaining) + executable allowlist (`JUNAI_RUN_COMMAND_ALLOWLIST` override). Applied to canonical pool copy `.github/tools/mcp-server/server.py` **and** the PyPI mirror `src/junai_mcp/server.py` (byte-identical); 10 RED-first gate tests |
| 4 | Live credential files in the working tree | **OPEN (human)** | gitignored/untracked → rotate the 3 tokens (your action) |
| — | Exporter silently drops phantom skills / missing sources never fail export | **DONE** | `export_runtime_resources.py` fail-closed: `_validate_skill_roster` + `ExportStats.errors` → `main()` returns 1 on any phantom skill or missing declared source. Removed the 5 stale `codex`/frontend phantoms from `runtime-targets.json`; canonical export still exits 0 (verified) |
| — | Copilot→Claude conversion implicitly grants `Bash` to read-only agents | **DONE** | `convert_tools_to_claude_format` no-mapped-tools default tightened to `[Read, Grep, Glob]` (was `+Bash`); explicit `execute` still maps to Bash |
| — | Redaction misses `-pPASSWORD` / `aws_secret_access_key <k>` shapes | **DONE** | `dream_capture.redact` gained `_MYSQL_PW` (mysql-family `-pVALUE` glued), `_CURL_USERPASS` (`curl -u user:pass`), `_AWS_CRED` (space-separated `aws_secret_access_key <k>`); all command-scoped so `cp -pr`/`python -u`/`docker -p 8080:80` survive. 8 new TDD cases incl. false-positive guards |
| — | `session_end` cost model bills GLM/DeepSeek/local as Sonnet | **OPEN** | add the new-provider rates |
| — | Cross-repo fact contamination (`_repo_root` uses launch cwd) | **OPEN** | anchor to the session repo |
| — | `validate_agents` MCP-note hard-fails the build | **OPEN** | separate notes from errors |
| — | No tests around export/validate/sync.ps1 | **PARTIAL** | export now covered — `scripts/tests/test_export_runtime_resources.py` (11 tests: fail-closed, roster validation, read-only default, real-manifest regression); validate/sync.ps1 still uncovered |
| — | Rebrand half-applied (`agent-sandbox` in deep docs) | **PARTIAL** | front-door + commands done (274bc16); `agent-workflow-design-reference.md` (63 refs), diagrams, test fixtures remain — cosmetic |

## docket
> **Deployed to prod (2026-07-17, `096cbb3`):** F1, F17, F12-partial + the full F30–F34 accessibility set
> — clean auto-merge, web build + 143 web + 496 py green; Gitea `deploy` **success**.
>
> **Deployed to prod (2026-07-17, `855d41c`):** F6, F11, F13 — independently re-verified before merge
> (512 py + 146 web + tsc/vite clean); Gitea `python_tests` → `web_checks` → `deploy` all **success**.
> Review follow-up: two stale lock-path comments corrected (`0a81586`) — the F11 file lock lives at
> `DOCKET_HOME/runtime/locks/<sha256>.lock`, deliberately NOT inside `.docket/` (attach-repo renames it
> on Windows).

| # | Finding | Status | Where |
|---|---------|--------|-------|
| F1 | `requires_confirmation` a no-op → Ship-drag auto-deploys prod | **DONE** | backend enforce (06b7cdc) + lead-only confirm UI (1e59da1) |
| F17 | Contributor lane-drag auto-triggers runs (bypasses lead gate) | **DONE** | a76a5e9 |
| F30–F34 | Accessibility (no keyboard DnD, non-dialog drawers, focus, contrast, no live region) | **DONE** | `feat/a11y` 710f89d…4f21dfa; 138 web tests + keyboard Playwright walkthrough |
| F12 | Implement hijacks the human's working tree | **PARTIAL** | crash-leftover guard self-heal shipped (e8a369b); **full worktree isolation OPEN** (needs live Implement run — design + subtleties in the plan) |
| F11 | Cross-process ID race on `.docket/` (in-memory locks only) | **DONE** | `feat/reliability` — reentrant `_RepoLock` (in-memory RLock + msvcrt/fcntl file lock under `DOCKET_HOME/runtime/locks/`) around `@_serialized`; deterministic cross-process mutex + 4-process id-race tests (7d1b66d) |
| F6 | Gate verdicts substring-matched over the whole transcript (spoofable via task text) | **DONE** | `feat/reliability` — positive verdict anchored to the final non-empty line (`_final_line`); blocking still matches anywhere (fail-closed); RED-first injection tests (9347583) |
| F13 | Stuck runs wedge the WIP cap (reconcile only at startup) | **DONE** | `feat/reliability` — periodic reconcile task in the FastAPI lifespan (liveness-aware: heartbeat for remote, `_active` set for local) + lead-only `POST …/runs/{rid}/cancel` + two-step Command Center "Cancel run" button (139d2db) |
| F5 | Corrupt `events.jsonl` → bare 500, no escape | **OPEN** | catch decode error, name the file/offset |
| F4 | Archived tasks unreachable + no unarchive; dead toggle | **OPEN** | add `task.unarchived` + endpoint |
| F2 | Pipeline-preset seeds a card into a lane that doesn't exist yet | **OPEN** | create in save `onSuccess` |
| F3 | Default agent-lane config references lanes the board lacks | **OPEN** | validate `agent_track.lanes`/`auto_advance_to` vs `lanes` |
| F25 | "Report bug" promises stakeholders uploads that 403 | **OPEN** | hide the picker for stakeholders |
| F20/F21 | NTLM trust rests on loopback; first-seen users auto-provision | **OPEN** | prefer `DOCKET_PROXY_SECRET`; opt-in provisioning |
| F7–F10, F14–F16, F18–F19, F22–F24, F26–F29, F35–F39 | (assorted correctness/UX/maint — see the full audit) | **OPEN** | `fable-audit-docket-2026-07-15.md` |

**Recommended next docket pass (highest value of the OPEN set):** F6 (security — verdict spoofing),
F11 (data integrity — ID race), F13 (reliability — stuck runs). A prompt for these can be written like
`.claudster/prompts/docket-accessibility-implement.md`.
