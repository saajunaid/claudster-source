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
| 2 | `junai-mcp` ships an unauthenticated shell-exec tool | **OPEN** | *downgraded:* it's stdio/local (footgun, not remote RCE) — still worth gating behind an opt-in flag + arg-array exec |
| 4 | Live credential files in the working tree | **OPEN (human)** | gitignored/untracked → rotate the 3 tokens (your action) |
| — | Exporter silently drops phantom skills / missing sources never fail export | **OPEN** | make export fail-closed |
| — | Copilot→Claude conversion implicitly grants `Bash` to read-only agents | **OPEN** | default read-only |
| — | Redaction misses `-pPASSWORD` / `aws_secret_access_key <k>` shapes | **OPEN** | `dream_capture.redact` |
| — | `session_end` cost model bills GLM/DeepSeek/local as Sonnet | **OPEN** | add the new-provider rates |
| — | Cross-repo fact contamination (`_repo_root` uses launch cwd) | **OPEN** | anchor to the session repo |
| — | `validate_agents` MCP-note hard-fails the build | **OPEN** | separate notes from errors |
| — | No tests around export/validate/sync.ps1 | **OPEN** | add fixtures |
| — | Rebrand half-applied (`agent-sandbox` in deep docs) | **PARTIAL** | front-door + commands done (274bc16); `agent-workflow-design-reference.md` (63 refs), diagrams, test fixtures remain — cosmetic |

## docket
> **Merged to docket `main` + deploying (2026-07-17, `096cbb3`):** F1, F17, F12-partial, and the full
> F30–F34 accessibility set were integrated (clean auto-merge; web build + 143 web tests + 496 py tests
> green) and pushed to `main` — the Gitea pipeline re-gates on tests, then deploys prod.

| # | Finding | Status | Where |
|---|---------|--------|-------|
| F1 | `requires_confirmation` a no-op → Ship-drag auto-deploys prod | **DONE** | backend enforce (06b7cdc) + lead-only confirm UI (1e59da1) |
| F17 | Contributor lane-drag auto-triggers runs (bypasses lead gate) | **DONE** | a76a5e9 |
| F30–F34 | Accessibility (no keyboard DnD, non-dialog drawers, focus, contrast, no live region) | **DONE** | `feat/a11y` 710f89d…4f21dfa; 138 web tests + keyboard Playwright walkthrough |
| F12 | Implement hijacks the human's working tree | **PARTIAL** | crash-leftover guard self-heal shipped (e8a369b); **full worktree isolation OPEN** (needs live Implement run — design + subtleties in the plan) |
| F11 | Cross-process ID race on `.docket/` (in-memory locks only) | **OPEN** | on-disk lock around commit+allocate |
| F6 | Gate verdicts substring-matched over the whole transcript (spoofable via task text) | **OPEN** | anchor to the final line; treat marker-anywhere as None |
| F13 | Stuck runs wedge the WIP cap (reconcile only at startup) | **OPEN** | periodic reconcile + a lead cancel/fail endpoint |
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
