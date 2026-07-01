# Migration — agent-sandbox → claudster-source (Option A2)

Full plan + phase tracker: `agent-sandbox/.claudster/plans/extract-claudster-to-own-repo.md`.
This file is the concrete **move-list** and the Phase-0 record.

## Phase status
- [x] **Phase 0 — Prep (this repo created; baseline captured).**
- [ ] Phase 1 — Move public source WITH history (`git filter-repo`).
- [ ] Phase 2 — Re-plumb the pipeline; delete the vmie purge (now structurally unnecessary).
- [ ] Phase 3 — Repoint the extension mirrors' pool source.
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

## Remote — CREATED (2026-07-01)
- **`origin` → https://github.com/saajunaid/claudster-source** (GitHub, account `saajunaid`, matches the
  existing `saajunaid/junai` publishing). Created via the GitHub API (no `gh` available); pushed with the
  Git Credential Manager cred already used for junai.
- **Visibility: PRIVATE for now.** Deliberate — the repo is an empty pre-migration skeleton. **Flip to
  public at Phase 4 cutover** (Settings → Danger Zone → Change visibility, or
  `PATCH /repos/saajunaid/claudster-source {"private": false}`), once real source has landed and a publish
  from here is verified against the golden baseline.
- Skeleton pushed: `main` @ `f732e26` (README + .gitignore + this file).
