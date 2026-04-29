# Context Handoff: junai Ecosystem — Publish Automation & v0.4.x Hardening

**Date**: 2026-02-26
**Status**: Near Complete (one manual step outstanding)
**Session Type**: Full session closeout — carry all context forward

---

## What Was Being Done

This session completed a multi-phase pipeline hardening and publish automation effort for the **junai agent ecosystem**. Work included: skip_stage MCP tool, Anchor adversarial review agent, cross-artifact drift protection, cross-repo README sync, full decoupling of publish tooling from `Customer360`'s `.venv`, key-file-based credential automation, a security incident remediation (PAT leaked in VSIX), and first successful publish of both the PyPI MCP package (`junai-mcp 0.2.0`) and VS Code extension (`junai-labs.junai v0.4.3`).

---

## Repo Map

| Repo | Path | Remote | Role |
|------|------|--------|------|
| `junai` | `E:\Projects\agent-sandbox\vscode-extensions\junai` | GitHub `saajunaid/junai` | Pool template + PyPI source + sync.ps1 |
| `junai-vscode` | `E:\Projects\agent-sandbox\vscode-extensions\junai-vscode` | GitHub `saajunaid/junai-vscode` | VS Code extension (VSIX + marketplace) |
| `agent-sandbox` | `E:\Projects\agent-sandbox` | local only (no remote) | Active development + pool bundle source |
| `Customer360` | `E:\Projects\Customer360` | GitHub | Working project (gitignores agents/skills) |

---

## Current State

### Completed ✅

- **skip_stage MCP tool** — agents can skip pipeline stages via `mcp_junai_skip_stage`; state written to `pipeline-state.json`
- **progress_line** — `get_pipeline_status` now returns current stage context
- **Anchor agent** (`anchor.agent.md`) — adversarial review agent added to pool; cross-artifact drift protection
- **24-agent pool** — all 4 repos synced; agent-sandbox is the canonical source
- **9 MCP tools** — `skip_stage` added; all READMEs updated
- **junai local `.venv`** — `E:\Projects\agent-sandbox\vscode-extensions\junai\.venv` bootstrapped with Python 3.14 (`C:/Users/jshaik/.local/bin/python3.14.exe`), contains `build` + `twine 6.2.0`; Customer360 venv dependency eliminated
- **Key file automation** (`junai-release` in `sync.ps1`):
  - Reads `E:\Projects\agent-sandbox\vscode-extensions\junai\pypimcp.key` → sets `TWINE_USERNAME=__token__`, `TWINE_PASSWORD`
  - Reads `E:\Projects\agent-sandbox\vscode-extensions\junai-vscode\vscode.pat` → sets `VSCE_PAT`
  - Both files gitignored (`*.key`, `*.pat`) AND vscodeignored
- **`junai-push` auto-publish** — default behaviour when key files exist; `-NoPublish` to skip
- **Security fix** — `vscode.pat` was accidentally bundled in v0.4.0 VSIX; PAT rotated, `*.pat`/`*.key` added to `.vscodeignore`, clean v0.4.1 published
- **PyPI published** — `junai-mcp 0.2.0` at https://pypi.org/project/junai-mcp/0.2.0/
- **Marketplace published** — `junai-labs.junai v0.4.3` at https://marketplace.visualstudio.com/items?itemName=junai-labs.junai
- **All READMEs synced** — junai, junai-vscode, agent-sandbox, Customer360 MCP README all reflect 24 agents / 9 tools

### Pending ⚠️

- **Delete v0.4.0 from marketplace** — v0.4.0 VSIX contained the exposed PAT in its file tree (`.pat` was not yet in `.vscodeignore`). Must be deleted **manually**:
  1. Go to https://marketplace.visualstudio.com/manage/publishers/junai-labs
  2. Click junai → **Hub** tab
  3. Find v0.4.0 → "..." menu → **Delete version**
  - ⚠️ Do NOT run `vsce unpublish junai-labs.junai` — that deletes the **entire extension**, not just one version

### Not Started (Backlog)

- Fully autonomous PM pipeline (PM agent orchestrates Intent→PRD→Architect→Plan→Implement→Review without manual gates) — noted as future goal

---

## Files Changed This Session

| File | Action | Purpose |
|------|--------|---------|
| `E:\Projects\agent-sandbox\vscode-extensions\junai\sync.ps1` | MODIFY | Added `junai-release`, `-NoPublish`/auto-publish, local venv publish, `$JUNAI_VSCODE`/`$PYPI_KEY_FILE`/`$VSCE_PAT_FILE` globals |
| `E:\Projects\agent-sandbox\vscode-extensions\junai\.gitignore` | MODIFY | Added `pypimcp.key`, `*.key` |
| `E:\Projects\agent-sandbox\vscode-extensions\junai\README.md` | MODIFY | 24 agents, 9 tools, junai-release command, correct model tiers, What's Coming updated |
| `E:\Projects\agent-sandbox\vscode-extensions\junai\.venv\` | CREATE | Bootstrapped Python 3.14 venv with build + twine |
| `E:\Projects\agent-sandbox\vscode-extensions\junai-vscode\package.json` | MODIFY | v0.4.3, updated description, `npx vsce` for publish/package |
| `E:\Projects\agent-sandbox\vscode-extensions\junai-vscode\.gitignore` | MODIFY | Added `vscode.pat`, `*.pat` |
| `E:\Projects\agent-sandbox\vscode-extensions\junai-vscode\.vscodeignore` | MODIFY | Added `*.pat`, `*.key` (security fix) |
| `E:\Projects\agent-sandbox\vscode-extensions\junai-vscode\README.md` | MODIFY | 24 agents, 9 tools, Anchor row, skip_stage row |
| `E:\Projects\agent-sandbox\.github\tools\mcp-server\README.md` | MODIFY | Full 9-tool listing |
| `E:\Projects\Customer360\.github\tools\mcp-server\README.md` | MODIFY | Full 9-tool listing (canonical source) |

---

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| PyPI token storage in `pypimcp.key` | Gitignored plain-text file avoids env var fragility; must include `pypi-` prefix |
| `junai-push` auto-publishes by default | Reduces friction for normal releases; `-NoPublish` for sync-only |
| `.vscodeignore` must include `*.pat`, `*.key` | Prevents credential files from being bundled into VSIX |
| agent-sandbox has no git remote | Intentional — it's a local staging environment; pool is synced via `bundle-pool.js` to junai-vscode |
| v0.4.0 left on marketplace (not `vsce unpublish`) | `vsce unpublish` deletes the whole extension; need manual version delete at hub |

---

## Blockers / Issues

- **v0.4.0 marketplace deletion** — this is the only remaining action; requires browser login to marketplace hub (see steps above)
- No failing tests; no build errors; all CI is push-based (no dedicated pipeline)

---

## Commit Log (last session)

**junai** (latest: `69ad243`):
```
69ad243 docs: sync MCP server README to pool — 9 tools, skip_stage, progress_line
69c94a6 docs: update README for v0.2.0 (24 agents, 9 MCP tools, junai-release, skip_stage, Anchor, drift protection)
998731a docs: sync MCP tool docs and release workflow
663f591 feat: auto-publish on junai-push when keys exist
82a35f6 feat: add keyfile-based release automation
9a94878 chore: decouple MCP publish from external venv
```

**junai-vscode** (latest: `3a85876`):
```
3a85876 chore: bump to v0.4.3 — updated marketplace README and description
3fe8fbc docs: update README + description for v0.4.1 (24 agents, 9 MCP tools, skip_stage, Anchor, drift protection)
2675813 fix: exclude *.pat *.key from VSIX + bump to v0.4.1
3aed7d8 chore: ignore local vscode PAT file
d9ebcb4 chore: use npx vsce for publish/package
f69ceb6 feat: v0.4.0 — skip_stage, progress line, 22 agent routing, anchor-review, drift fixes
```

**agent-sandbox** (latest: `f3eae3e`, local only):
```
f3eae3e docs: update MCP server README — 9 tools, skip_stage, progress_line
fa3932a feat(pipeline): skip_stage, progress line, drift fix, UX hardening
```

---

## Release Status

| Artifact | Version | Status |
|----------|---------|--------|
| PyPI `junai-mcp` | 0.2.0 | ✅ Published |
| VS Code `junai-labs.junai` | 0.4.3 | ✅ Published (current, clean) |
| VS Code `junai-labs.junai` | 0.4.0 | ⚠️ Published (contains exposed PAT — delete manually) |

---

## Normal Release Workflow (going forward)

```powershell
# Full release (both PyPI + extension) — auto when keys exist
junai-push

# Skip publish (sync only)
junai-push -NoPublish

# PyPI only (bump version manually in pyproject.toml first)
junai-release -SkipExtension -McpVersion "0.2.1"

# Extension only
junai-release -SkipMcp
```

Key files (do not commit, gitignored):
- `E:\Projects\agent-sandbox\vscode-extensions\junai\pypimcp.key` — PyPI token (must start with `pypi-`)
- `E:\Projects\agent-sandbox\vscode-extensions\junai-vscode\vscode.pat` — Azure DevOps PAT

---

## Continuation Instructions

### Immediate Next Step
Delete v0.4.0 from the VS Code marketplace:
1. https://marketplace.visualstudio.com/manage/publishers/junai-labs
2. junai → Hub tab → v0.4.0 → "..." → Delete version

### After That — New Work
This handoff document is the entry point for the next session. The agent-sandbox workspace is the right place for agent/skill development. Normal workflow:
- Edit agents/skills in `E:\Projects\agent-sandbox\.github\`
- `junai-push` from junai to sync + publish

### Files to Read First in New Session
1. This file: `.github/handoffs/2026-02-26-junai-ecosystem-publish-automation.md`
2. `E:\Projects\agent-sandbox\vscode-extensions\junai\sync.ps1` — full command reference
3. `E:\Projects\agent-sandbox\.github\tools\mcp-server\README.md` — MCP tool reference

---

## Continuation Prompt (paste this in the new chat)

```
I'm opening a fresh session to continue work on the junai agent ecosystem.

Please read this handoff document first:
E:\Projects\agent-sandbox\.github\handoffs\2026-02-26-junai-ecosystem-publish-automation.md

## Quick context

- 4-repo ecosystem: junai (pool/PyPI), junai-vscode (extension), agent-sandbox (dev sandbox), Customer360 (working project)
- Just shipped: junai-mcp 0.2.0 (PyPI), junai-labs.junai v0.4.3 (VS Code marketplace), 24-agent pool, 9 MCP tools, skip_stage, Anchor adversarial review, drift protection
- Key automation: `junai-push` auto-publishes when key files exist; `junai-release` for selective publish
- One outstanding manual action: delete v0.4.0 from marketplace hub (contains accidentally-exposed PAT from before .vscodeignore fix)

## Workspace
Open: E:\Projects\agent-sandbox

## What I want to work on next
[DESCRIBE YOUR NEXT TASK HERE]
```
