# Project Instructions

> This file is yours. The junai extension manages only the `<!-- junai:start -->` … `<!-- junai:end -->`
> section below; everything else is never read, modified, or deleted by the extension.
>
> junai system documentation (25 agents, pipeline flow, MCP tools, routing conventions) is
> automatically provided by `.github/instructions/junai-system.instructions.md`.

---

## Project Overview

**agent-sandbox** is the authoring and source-of-truth repository for the **junai agent pipeline system**. Not a deployed application — this is where all 25 agent definitions, skills, prompts, and tooling are authored, tested, and published via the junai VS Code extension (`junai-labs.junai`).

Everything in `.github/` here is the **pool source** that gets bundled into the extension and deployed into any project that installs it.

```
agent-sandbox/
├── .github/
│   ├── agents/              ← 25 agent definition files (*.agent.md)
│   ├── skills/              ← Reusable skill bundles (domain knowledge packs)
│   ├── prompts/             ← Reusable prompt files
│   ├── instructions/        ← Coding convention files (*.instructions.md)
│   ├── tools/
│   │   └── mcp-server/
│   │       └── server.py    ← FastMCP server (9 tools, PEP 723 uv runtime)
│   ├── agent-docs/
│   │   ├── ARTIFACTS.md     ← Artefact registry (inter-agent working files)
│   │   └── *.md             ← Pipeline schema docs, artefact templates
│   ├── plans/               ← Implementation plans produced by the Plan agent
│   ├── handoffs/            ← Agent-to-agent handoff templates
│   ├── diagrams/            ← Architecture and workflow reference diagrams
│   ├── pipeline-state.json  ← Live pipeline state (gates, routing, artefacts)
│   └── project-config.md   ← Project-specific token definitions
├── validate_agents.py       ← Pre-publish gate: checks 25 agents + MCP smoke test
├── sync.ps1                 ← junai-pull / junai-push sync functions
└── project-config.md        ← Workspace-level config
```

> **agent-sandbox has no git remote.** All commits are local only. Changes are pushed downstream via the publish workflow described below.

---

## The Three-Repo System

```
agent-sandbox  (local only — authoring source)
    │
    ├──▶  E:\Projects\junai-vscode   (VS Code extension — github.com/saajunaid/junai-vscode)
    │         bundle-pool.js copies .github/ → pool/ before every publish
    │
    └──▶  E:\Projects\junai          (public pool mirror — github.com/saajunaid/junai)
              sync.ps1 junai-push copies .github/ folders and git pushes
```

- **agent-sandbox** is where you author all changes
- **junai-vscode** is what marketplace users install; it bundles the pool and deploys it into workspaces
- **junai** is the public-facing mirror of the pool for users who want to browse or fork agent definitions directly

---

## The 25 Agents

Each agent is defined in `.github/agents/<name>.agent.md`. Full model assignments, key roles, pipeline flow, MCP tools, and routing conventions are in `.github/instructions/junai-system.instructions.md` (auto-loaded by VS Code Copilot via `applyTo: "**"`).


---

## Architecture Notes

**Three-repo system:**
```
agent-sandbox  (local only, no remote — authoring source of truth)
    │
    ├──▶  E:\Projects\junai-vscode   (VS Code extension — github.com/saajunaid/junai-vscode)
    │         bundle-pool.js copies .github/ → pool/ before every publish
    │
    └──▶  E:\Projects\junai          (public pool mirror — github.com/saajunaid/junai)
              sync.ps1 junai-push copies .github/ folders and git pushes
```

- **agent-sandbox** — author all changes here; no remote; local commits only
- **junai-vscode** — marketplace extension; bundles and deploys the pool
- **junai** — public-facing mirror for users to browse/fork agent definitions

**Pool deployment:** Everything in `.github/` is copied verbatim into user workspaces by `bundle-pool.js` on install. `pipeline-state.json` and `project-config.md` are USER_OWNED and never overwritten by pool updates. `copilot-instructions.md` is no longer bundled — the extension manages only a sentinel-delimited `<!-- junai:start -->` section programmatically (v0.6.2+).

**MCP server runtime:** `server.py` uses `uv run` (PEP 723 inline deps) — no local `.venv` install needed. `stdin=asyncio.subprocess.DEVNULL` on all subprocess spawns prevents stdio pipe inheritance deadlock (critical fix v0.4.9).

---

## Team / Project Conventions

**Pre-publish gate:** Always run `validate_agents.py` before publishing. Checks all 25 agents (required frontmatter, `§8`/`§9` sections, Partial Completion Protocol) + MCP smoke test (9 tools via JSON-RPC).

**Publish workflow:**
```powershell
# 1. Validate (agent-sandbox)
python validate_agents.py

# 2. Commit agent-sandbox (local only)
git add .github/; git commit -m "feat: ..."

# 3. Publish extension (junai-vscode)
cd E:\Projects\junai-vscode
# edit package.json version
git add package.json; git commit -m "chore: bump version to X.Y.Z"
$env:VSCE_PAT = (Get-Content "vscode.pat" -Raw).Trim()
npm run publish   # bundle-pool + tsc + vsce publish
git push

# 4. Sync pool mirror (junai)
cd E:\Projects\junai
git add .github/agents .github/skills .github/prompts .github/instructions .github/diagrams .github/tools
git commit -m "feat: sync pool from agent-sandbox - YYYY-MM-DD"
git push
```

**`npm run publish` internals:** `bundle-pool.js` wipes `pool/`, copies `.github/` folders, skips `vmie` skill, guards against `dir/dir` nesting, writes `POOL_VERSION`. Then `tsc` compiles, then `vsce publish`.

**Do NOT:**
- Add application code here — infrastructure/tooling only
- Commit secrets or PAT tokens (`.vscode.pat` is gitignored)
- Run `git push` from agent-sandbox (no remote)
- Edit `E:\Projects\junai-vscode\pool\` directly (wiped on every `npm run publish`)
- Skip `validate_agents.py` before publishing

---

## Institutional Knowledge

- PowerShell `git push` exits code 1 even on success (stderr quirk) — not an error; check GitHub to confirm push landed
- `copilot-instructions.md` managed-section pattern since v0.6.2 — extension manages only a `<!-- junai:start -->` sentinel block; user content outside markers is never touched. Replaced the v0.5.7 USER_OWNED approach. junai system docs live in `junai-system.instructions.md`.
- `uv run` replaces `.venv` path in `mcp.json` (introduced v0.5.5) — no local Python install needed for MCP
- `bundle-pool.js` `dir/dir` nesting guard introduced v0.5.2 — `cmdUpdate` auto-heals legacy nesting on activation
- Agent file naming: lowercase kebab-case matching the `name` frontmatter field exactly
- `validate_agents.py` `KNOWN_MODELS` allowlist must be updated whenever a new model is introduced
