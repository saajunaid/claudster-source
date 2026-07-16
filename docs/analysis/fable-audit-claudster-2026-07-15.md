# Fable audit — claudster (2026-07-15)

Read-only adversarial audit by Fable (`claude-fable-5`) of `E:\Projects\claudster-source`, run from
`.claudster/prompts/fable-inspect-claudster.md`. Findings are the reviewer's; the **Verification notes** at
the bottom are the main thread's own checks (some correct an over/under-statement).

## Top 10 (ranked)
1. **Internal deploy runbook ships in the public `claudster-extras` bundle** — `deploy-local/SKILL.md` (prod host `iegbcoppoc02`, `gitea.internal`, `VMIE_BOT_TOKEN`, `Invoke-Command -ComputerName iegbcoppoc02`) present in `dist/runtime-resources/claude-extras/…`. (Critical — **confirmed**)
2. **MCP server ships a shell-exec tool** — `junai_mcp/server.py:800` `run_command` via `create_subprocess_shell` (`shell=True`), no allowlist, on PyPI as `junai-mcp`. (**stdio/local**, so a footgun to gate — NOT remote RCE; see notes)
3. **The privacy claim is unenforceable** — `validate_pool.py:101` denylists only `vmie-`; misses `iegbcoppoc`, `gitea.internal`, `jshaik`, `VMIE_BOT_TOKEN`. `sync.ps1` purges only the `vmie` skill *category*, but `deploy-local` lives in `devops/`. (High)
4. **Live credential files in the working tree** — `pypimcp.key` (PyPI token), `vscode.pat`, `ptarmigan.pat`. (**gitignored/untracked** — not an active leak; rotate + relocate anyway.)
5. **Dream Memory inflates noise into "lessons"** — `_HEAD_LEN=80` truncates command keys → fingerprint collision → inflated `hitCount`; the live store shows 5 facts at hitCount 13–17, all 80-char keys, dominating SessionStart. (High)
6. **Guard is POSIX-only for catastrophic delete** — `guard.py:98` allows `Remove-Item -Recurse -Force C:\`, `rmdir /s /q`, `shutil.rmtree('/')` on a Windows-primary box. (High)
7. **Guard misses force-push via refspec** — `git push origin +main` bypasses the `--force` matcher. (High)
8. **`git push` failure treated as success** — `sync.ps1:1297-1300` pipes to `Out-Null` with no `$LASTEXITCODE` check, then sets `MirrorChanged=$true`. (High)
9. **The guide's headline `/claudster:cross-review` command doesn't exist** — it's a *skill* in `claudster-extras` (off by default); no `commands/cross-review.md`. First thing a new user tries fails. (High)
10. **Personal paths + an unresolved credential-incident handoff in public files** — `providers-and-keys.md:30` (`C:\Users\jshaik\…`), `.github/handoffs/2026-02-26-…md` (a PAT leak with a still-pending "delete v0.4.0 from marketplace"). (High)

## Other notable findings
- Exporter silently drops nonexistent skills (codex target names 5 phantom skills), missing sources never fail export, Copilot→Claude conversion implicitly grants `Bash` to read-only agents (`export_runtime_resources.py`).
- Redaction misses `-pPASSWORD` / `aws_secret_access_key <k>` / `curl -u u:p` shapes (`dream_capture.py`).
- Cross-repo fact contamination — `claudster-source` store holds docket facts (`_repo_root` uses launch `getcwd()`).
- session_end cost model only knows opus/sonnet/haiku → GLM/DeepSeek/local bill as Sonnet.
- The junai→claudster rebrand is half-applied (`junai-push` verbs, `copilot-instructions.md` says "no git remote", phantom agents in the model table, stale IMPL-STATUS).
- No tests around export/validate/publish/sync.ps1 — the most dangerous code is the least tested.

## Systemic themes
1. **"Privacy is structural" was assumed, not enforced.** Every control keys on the `vmie` category / `vmie-` string; internal content *outside* that shape (deploy-local, devops agent, enterprise recipe, personal paths) ships or is tracked publicly. Fix: content-based denylist (org identifiers + hosts + usernames); forbid allowlisting live infra.
2. **Fail-open copied into places that need fail-closed.** Correct for hooks; wrong for the export/publish path (silent skips, un-checked push, a dead leak-gate).
3. **The rebrand is half-applied** → dead references, phantom commands, a git-remote contradiction that breaks onboarding.
4. **The most dangerous code is the least tested.**

## Verification notes (main thread, 2026-07-15)
- **#1 confirmed:** `grep` found `iegbcoppoc02`/`gitea.internal`/`VMIE_BOT_TOKEN` in `dist/runtime-resources/claude-extras/plugin-extras/skills/{deploy-local/SKILL.md,_registry.md}`.
- **#4 calibrated:** all three credential files exist but are **gitignored and untracked** (not committed/pushed). Real tokens on disk → rotate + move to a secret store, but not an active git leak.
- **#2 calibrated DOWN:** `server.py` uses `FastMCP` + `mcp.run()` = **stdio transport** (local, user-launched). The shell tool is the same trust level as the user's own agent — a footgun worth gating (opt-in flag, arg-array exec, allowlist), **not** remotely exploitable RCE.
- Everything else above is the reviewer's, not yet independently verified.
