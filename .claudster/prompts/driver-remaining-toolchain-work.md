# Driver — finish the claudster + docket hardening backlog

You are the **driver** for the remaining work on this two-repo toolchain. Don't treat this as one isolated
task: you own a backlog and work it down, checking in with the user at the decision points flagged below.

## Orient first (read these, in this order — do NOT skip)
1. `.claudster/relay.md` — where the last session stopped, validation state, open blockers.
2. `docs/analysis/fable-remediation-status.md` — **the driver list**: every audit finding with
   DONE / PARTIAL / OPEN. Your queue comes from here.
3. `.claudster/plans/oss-model-lanes-and-public-readiness.md` — the strategic plan: **Track 0** (audit
   hardening, active) and the **un-started Tracks A / B / C**.
4. `docs/analysis/fable-audit-claudster-2026-07-15.md` — the detail behind each claudster row.
5. `docs/guide/start-here.md` — what claudster and docket are and how they relate (the toolchain map).
6. `README.md` `## Publishing` — `junai-push` semantics + the `dist/` Windows-ACL landmine.

## The big picture (why this exists)
- **claudster** (`E:\Projects\claudster-source`) is a Claude Code harness/plugin (skills, subagents,
  commands, hooks) published to a **public** marketplace mirror. **docket** (`E:\Projects\docket`) is an
  event-sourced board + autonomous agent pipeline that drives claudster's slash-commands.
- Two adversarial **Fable audits** (2026-07-15) found ~59 issues. **Every critical/high is now closed and
  deployed**: the public-bundle infra leak (closed + republished), the guard/sync/memory P1 fixes, and
  docket's F1/F17/F12-partial/F6/F11/F13 + the F30–F34 accessibility set (both merged to docket `main`
  and live in prod).
- **What's left is the medium/low tail** (~19 OPEN rows) plus the plan's un-started Tracks A/B/C. Goal:
  work that tail down, keeping claudster genuinely publish-safe and docket safe for the wider team.

## Your queue (in order)

### 1. NOW — claudster mediums pass (implement DIRECTLY; no spec needed)
Work the OPEN **claudster** rows in the tracker. Suggested order (detail in the audit):
1. **Gate the `junai-mcp` shell-exec tool** — `vscode-extensions/junai/src/junai_mcp/server.py` (`run_command`,
   ~line 800) runs any string via `create_subprocess_shell` (`shell=True`), no allowlist, and ships on PyPI.
   It's **stdio/local** (a footgun, not remote RCE — don't overstate it). Put it behind an opt-in env flag,
   use arg-array exec (no `shell=True`), add an allowlist.
2. **Exporter fail-closed** — `export_runtime_resources.py`: a target roster naming a skill that doesn't exist,
   and `missing_source`, currently fold into counters with exit 0 (the `codex` target names ~5 phantom skills).
   Make them FAIL. Also: Copilot→Claude conversion defaults an agent with no mapped tools to include `Bash` —
   never implicitly grant shell; default read-only.
3. **Redaction shapes** — `claude-harness/scripts/dream_capture.py` `redact` misses `-pPASSWORD`,
   `aws_secret_access_key <k>`, `curl -u user:pass`.
4. **Cost model** — `claude-harness/hooks/session_end.py` only knows opus/sonnet/haiku, so GLM/DeepSeek/local
   bill as Sonnet.
5. **Cross-repo fact contamination** — `_repo_root` resolves from the launch cwd, so docket facts land in
   claudster's Dream Memory store. Anchor to the session's repo.
6. **`validate_agents.py`** — an MCP "note" is appended to `errors` and `:813` exits 1 on any error, so adding
   an MCP tool hard-fails the build. Separate notes from errors.
Then: the cosmetic rebrand tail (`agent-workflow-design-reference.md` has ~63 `agent-sandbox` refs, plus
diagrams/test fixtures) — low value; do it only if the others are done.

### 2. NEXT — docket F2/F3/F4/F5/F25
Write an implementation spec at `.claudster/prompts/docket-ux-correctness-implement.md`, modelled on the two
existing ones (`docket-accessibility-implement.md`, `docket-reliability-security-implement.md`) — same shape:
branch off docket `main`, TDD phases, exact files, acceptance, verification, per-phase commits. Covers:
F2 (pipeline preset seeds a card into a lane that doesn't exist yet), F3 (default agent-lane config references
lanes the board lacks), F4 (archived tasks unreachable — no unarchive; dead "Archived" toggle), F5 (corrupt
`events.jsonl` → bare 500 with no escape), F25 ("Report bug" promises stakeholders uploads that 403).
**Ask the user** whether they want you to run it or hand it to a separate session.

### 3. THEN — the strategic plan (ask the user before starting each)
- **Track A** — model-switching as a real claudster feature (cross-platform `claude-oss`/`claude-glm`
  launchers + `/claudster:use-model` + non-hardcoded key resolution). Design is settled in the plan.
- **Track B** — claudster public-readiness. **BLOCKED on a human decision: the LICENSE choice**
  (recommendation: MIT). Ask for it before starting B1.
- **Track C** — point docket's Implement review gate at `oss_review.py` for cross-vendor review.
- **F12 full worktree isolation** (docket) — deferred: it needs a **LIVE Implement run** to verify; the
  correctness subtleties (uncommitted `.claudster/` plan artifacts aren't in a fresh worktree) are recorded
  in the plan. Don't attempt it blind.

## Operating rules (these matter)
- **TDD**: RED test first, then the fix. After **every** claudster fix run BOTH:
  `python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q --import-mode=importlib` (currently
  **303 passed, 1 skipped**) and `python validate_pool.py` (must stay OK).
- **Commit per fix**, only the files that fix touches, and **flip that row to DONE in
  `docs/analysis/fable-remediation-status.md`** — the tracker must never drift from reality.
- **Privacy is a publish gate**: the pool ships publicly. No internal hosts/org identifiers/personal paths in
  `.github/` or `claude-harness/`. `validate_pool.py`'s content-based denylist enforces it — **extend the
  denylist rather than allowlisting a real leak**.
- **`.claudster/` is the artifacts home** — plans/prd/kb/prompts/reviews live there; never the repo root or
  `.github/` (that's the published pool).
- **Publishing**: bare `junai-push` = mirror sync + version bump, **no publish**; `-Publish` publishes
  MCP/VS Code; `-NoPublish` is a deprecated no-op. The `dist/` dir can be Administrator-owned → a
  non-elevated push fails on `ensure_clean_dir` **and then silently syncs stale content**. If that happens,
  ask the user to run (elevated): `Remove-Item -Recurse -Force 'E:\Projects\claudster-source\dist'` then
  `. .\sync.ps1; junai-push`.
- **docket: NEVER push `main`** — it auto-deploys prod. Feature branches only; hand them back for review.
- **Known docket flake** (NOT a regression): `tests/test_api.py::test_create_bug_with_fields_via_api`
  intermittently 500s under the full suite (Windows subprocess/file timing). Re-run before investigating.
- Be honest in reports: if something is partial, unverified, or you skipped it, say so plainly.

## Start here
Read the docs above, confirm the tracker's OPEN claudster rows against the code, then begin item 1
(gate the `junai-mcp` shell tool) TDD-first. Tell the user what you found and what you're doing before the
first edit, and check in at each decision point flagged above.
