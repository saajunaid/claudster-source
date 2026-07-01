# Migration — agent-sandbox → claudster-source (Option A2)

Full plan + phase tracker: `agent-sandbox/.claudster/plans/extract-claudster-to-own-repo.md`.
This file is the concrete **move-list** and the Phase-0 record.

## Phase status
- [x] **Phase 0 — Prep (this repo created; baseline captured).**
- [x] **Phase 1 — Public source moved WITH history (2026-07-01).** 327→246 commits; 842 files. Fail-closed
  keep-list (only named public paths). **Privacy: 3 filter-repo passes** — the third caught the proprietary
  `[redacted proprietary file]` + old `vm-ppt`/`golden-workflow`/`vmie` skills surviving at *historical*
  paths (`.github/skills/docs/vm-ppt/`, `.github/skills/skills/vmie/`, `.github/skills/devops/golden-workflow/`)
  that the current-location exclusion missed. Verified: zero private-skill paths/objects in all history;
  largest blobs are legit public assets; no tags pushed.
- [x] **Phase 2 — Build/validate standalone + privacy made structural (2026-07-01).**
  - **Build parity proven**: `export --profile claude --profile claude-extras` from this repo is
    content-identical to the golden baseline (all 521 files; the only delta is uniform CRLF vs
    agent-sandbox's accidental mixed EOL — an improvement). ⇒ Phase 4's gate is *content*-identical
    (EOL-agnostic), not literally byte-identical.
  - **Private gating removed** (proven no-op via before/after export diff, 783 files identical):
    dropped the `exclusions` block (`skills`/`private_roots`/`private_paths`) + codex
    `include_private:["vmie"]` + codex's stale `vmie` skill category from `runtime-targets.json`;
    neutralised the vmie purge in `sync.ps1` (`$PRIVATE_ROOT_FOLDERS`/`$PRIVATE_SKILL_CATEGORIES` → `@()`,
    parses clean). Privacy is now structural — nothing private exists to gate.
  - **validate_pool green** (`--include-dist`, 1215 files) after dropping the dead hardcoded mirror paths;
    139 skills (= 141 − the 2 private vmie skills). Migrated **215-test** suite passes from this repo.
  - Deferred to Phase 3 (mirror-push machinery, not runnable until mirrors are repointed): `sync.ps1`
    path constants (`$REPO_ROOT`/`$EXT_REPOS_ROOT`/key files), the version-bump dance, `bundle-pool.js`.
    Minor stale item: `pool.manifest.yml` still classifies `plans`/`pipeline-state.json` (dropped) as
    owned — harmless (classification, not disk); clean up alongside the pipeline re-plumb.
- [x] **Phase 3 — Extension-mirror repoint verified (2026-07-01).** Key finding: **no mirror edits
  needed.** `sync.ps1` sets `$env:JUNAI_SOURCE = $ProjectRoot` before running each extension's
  `bundle-pool.js`, and all mirror paths derive from `$PSScriptRoot` — so running the pipeline *from*
  claudster-source automatically sources the pool from claudster-source. Empirically proven: ran
  junai-vscode's `bundle-pool.js` with `JUNAI_SOURCE=claudster-source` → bundled 732 files, **139 skills,
  zero vmie/golden-workflow/vm-ppt**, bundled skill files match claudster-source. Added `vscode-extensions/`
  to `.gitignore` (mirrors placed here at cutover, never tracked). The **physical relocation of the 4 mirror
  working copies + their keys** (`pypimcp.key`, `vscode.pat`, `ptarmigan.pat`) under
  `claudster-source/vscode-extensions/` is the Phase 4 cutover step.
- [ ] Phase 4 — Cutover: place mirrors+keys under claudster-source; run junai-push; verify content-identical.
- [ ] Phase 4 — Cutover publish; verify byte-identical to the golden baseline.
- [ ] Phase 5 — Decommission agent-sandbox; stand up the private repo.

## Golden baseline (captured 2026-07-01, agent-sandbox @ 9c8b847)
Location: `E:\Projects\_archive\claudster-phase0-baseline\`
- `versions.txt` — claudster 1.3.11 · claudster-extras 1.3.1 · junai-mcp 0.2.22 · VS Code ext 1.2.33
- `plugin-tree-manifest.sha256` — content hashes of the 521 generated plugin files (claude/ + claude-extras/)
- Rollback: `E:\Projects\_archive\agent-sandbox-full-20260701.bundle` (git bundle --all, verified)

After migration, regenerate the plugin tree from THIS repo and diff its content-hash manifest against the
baseline. Zero diff = the extraction preserved the published artifact exactly.

## MOVE HERE (public source → claudster-source)
From `agent-sandbox`, preserving history where practical:
- `.github/skills/**` — **except `skills/vmie/`** (proprietary)
- `.github/agents/`, `.github/prompts/`, `.github/instructions/`, `.github/tools/`, `.github/recipes/`,
  `.github/diagrams/`, `.github/agent-docs/`, `.github/handoffs/`
  — **except** `prompts/junai-ship.prompt.md` (local-only) and `.github/plans/` (private)
- `.github/runtime-targets.json` (the build manifest)
- `.github/tools/mcp-server/server.py` (MCP server logic) + the MCP package skeleton (decide: own it here)
- `claude-harness/**` (the only claudster-exclusive authoring source) — drop the unused `skills/vmie` if present
- `scripts/setup_project_ai.py`, `scripts/usage_review.py`, `scripts/tests/**`
- Build machinery: `sync.ps1`, `export_runtime_resources.py`, `validate_pool.py`, `validate_agents.py`
- `.env.example`, `CHANGELOG` handling (currently in the junai mirror — decide a single home)

## LEAVE BEHIND (private → new private repo in Phase 5; never public)
- `vmie/` (root) and `.github/skills/vmie/` (proprietary: golden-workflow, vm-ppt, incidents)
- `.github/plans/` (internal), `prompts/junai-ship.prompt.md` (local-only)
- `docket/`, `.docket/` (untracked experiments), appointment-assist material
- `.claudster/` working state (plans/handoffs/relay/usage) — the migration plan itself lives here for now
- All secrets/keys: `.env`, `*.pat`, `pypimcp.key`, `.mcpregistry_*`, `github-pat.md`
- **Open item:** the `codex` lane in `runtime-targets.json` does `include_private: ["vmie"]` — it cannot
  come here with vmie; resolve in Phase 2 (keep with the private repo, or drop the lane).

## DEFERRED (excluded by Phase 1's fail-closed keep-list — decide before Phase 4 / going public)
Missing a public file is recoverable (add a commit); leaking a private one is not — so these were left out
and need an explicit call:
- `claudster/` handbook (`CLAUDSTER.md`, `NORTH-STAR.md`, `claude-structure.jpg`) — internal state-of-record;
  review before publishing to a public repo.
- `docs/` — content unreviewed for public exposure.
- `.github/workflows/` — CI (claudster-source will likely define its own).
- `.github/pipeline-state.json` + `pipeline-state.template.json`, `.github/diagrams.zip`,
  `scripts/extract_nuggets.ps1`, root `project-config.md` — unclear if pool-required; add back if Phase 4
  build needs them.
- **MCP package skeleton** (`pyproject.toml`, `src/junai_mcp/`) currently lives in the `junai` mirror, not
  agent-sandbox — Phase 2 decides whether claudster-source owns it (only the MCP *server logic*,
  `.github/tools/mcp-server/server.py`, came across in Phase 1).

## Remote — CREATED (2026-07-01)
- **`origin` → https://github.com/saajunaid/claudster-source** (GitHub, account `saajunaid`, matches the
  existing `saajunaid/junai` publishing). Created via the GitHub API (no `gh` available); pushed with the
  Git Credential Manager cred already used for junai.
- **Visibility: PRIVATE for now.** Deliberate — the repo is an empty pre-migration skeleton. **Flip to
  public at Phase 4 cutover** (Settings → Danger Zone → Change visibility, or
  `PATCH /repos/saajunaid/claudster-source {"private": false}`), once real source has landed and a publish
  from here is verified against the golden baseline.
- Skeleton pushed: `main` @ `f732e26` (README + .gitignore + this file).
