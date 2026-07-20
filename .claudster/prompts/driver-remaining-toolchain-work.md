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

## Your queue (in order) — updated 2026-07-20

> Completed since this prompt was first written: the entire claudster mediums pass, docket F2/F3/F4/F5/F25
> (merged via `feat/ux-correctness`), Track A (shipped), Track B B1/B2/B3, and Track C (branch
> `feat/cross-review-gate`, unmerged). Details in the tracker. The remaining queue:

### 1. NOW — push + review + merge docket `feat/cross-review-gate`
Track C's output sits on that docket branch, not pushed. Push the branch, hand it back for review; merge to
docket `main` only with the user's go-ahead (main auto-deploys prod).

### 2. NEXT — docket F20/F21 (auth hardening)
NTLM trust rests on loopback; first-seen users auto-provision. Prefer a `DOCKET_PROXY_SECRET` shared header +
an opt-in/toggleable provisioning gate — but preserve the zero-setup teammate onboarding that B3 verified
(see the tension note in `docs/analysis/PUBLIC-READINESS.md` §B3). Spec first (a `docket-*-implement.md`
prompt, modelled on the existing three), then implement on a feature branch.

### 3. THEN — regenerate + work the docket medium/low tail (~18 findings)
F7–F10, F14–F16, F18–F19, F22–F24, F26–F29, F35–F39 have **no saved descriptions** (transcript-only).
Re-run a scoped audit via `.claudster/prompts/fable-inspect-docket.md` excluding the already-fixed areas,
**persist the full per-finding detail to `docs/analysis/` this time**, update the tracker, then spec +
implement the worthwhile ones.

### 4. WHEN THE USER SCHEDULES IT — F12 full worktree isolation (docket)
Deferred: it needs a **LIVE Implement run** to verify; the correctness subtleties (uncommitted `.claudster/`
plan artifacts aren't in a fresh worktree) are recorded in the plan's Track 0. Don't attempt it blind.

### 5. LOW-VALUE tail (only if the above are done)
`sync.ps1` test coverage; the cosmetic rebrand tail (`agent-workflow-design-reference.md` ~63
`agent-sandbox` refs, diagrams, test fixtures).

### HUMAN actions (remind the user; not yours to do)
Rotate the 3 tokens (`pypimcp.key`, `vscode.pat`, `ptarmigan.pat`); delete VS Code `junai-labs.junai`
v0.4.0 at the marketplace hub; decide Track B4 (whether/where to publish claudster).

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
