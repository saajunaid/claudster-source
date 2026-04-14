# Project Instructions

> This file is yours. The junai extension manages only the `<!-- junai:start -->` … `<!-- junai:end -->`
> section below; everything else is never read, modified, or deleted by the extension.
>
> junai system documentation (25 agents, pipeline flow, MCP tools, routing conventions) is
> automatically provided by `.github/instructions/junai-system.instructions.md`.

---

## Project Overview

**agent-sandbox** is the authoring and source-of-truth repository for the **junai agent pipeline system**. Not a deployed application — this is where all 25 agent definitions, skills, prompts, and tooling are authored, tested, and compiled into runtime-specific project resources via the junai VS Code extension (`junai-labs.junai`).

Everything in `.github/` here is the **canonical source**. Runtime-specific resources for Copilot, Claude, and Codex are exported from that source into project-local folders during packaging.

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
│   ├── plans/               ← Implementation plans produced by the Planner agent
│   ├── handoffs/            ← Agent-to-agent handoff templates
│   ├── diagrams/            ← Architecture and workflow reference diagrams
│   ├── pipeline-state.json  ← Live pipeline state (gates, routing, artefacts)
│   └── project-config.md   ← Project-specific token definitions
├── validate_agents.py       ← Pre-publish gate: checks 25 agents + MCP smoke test
├── export_runtime_resources.py ← Builds project-local `.github/`, `.claude/`, `.codex/` exports from canonical `.github/`
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
    │         packaging builds runtime-specific project-local exports
    │
    └──▶  E:\Projects\junai          (public pool mirror — github.com/saajunaid/junai)
              sync.ps1 junai-push copies canonical `.github/` source and git pushes
```

- **agent-sandbox** is where you author all changes
- **junai-vscode** is what marketplace users install; it compiles canonical resources into runtime-native project folders in workspaces
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
    │         package step builds `.github/`, `.claude/`, `.codex/` project-local exports
    │
    └──▶  E:\Projects\junai          (public pool mirror — github.com/saajunaid/junai)
              sync.ps1 junai-push copies canonical `.github/` folders and git pushes
```

- **agent-sandbox** — author all changes here; no remote; local commits only
- **junai-vscode** — marketplace extension; bundles and deploys the pool
- **junai** — public-facing mirror for users to browse/fork agent definitions

**Runtime export architecture:** `.github/` is the only authoring source. Packaging builds project-local runtime folders per workspace: Copilot reads `.github/`, Claude reads `.claude/`, Codex reads `.codex/`. User-level deployment is intentionally unsupported by default to avoid duplicate loading and context bloat. `pipeline-state.json` and `project-config.md` are USER_OWNED and never overwritten by pool updates. `copilot-instructions.md` is no longer bundled wholesale — the extension manages only a sentinel-delimited `<!-- junai:start -->` section programmatically (v0.6.2+).

**Export contract:** `export_runtime_resources.py` reads `.github/runtime-targets.json` and emits build artefacts under `dist/runtime-resources/` for packaging. Treat `dist/` as generated output, not source of truth.

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

# 3. Build runtime exports (agent-sandbox)
python export_runtime_resources.py

# 4. Publish extension (junai-vscode)
cd E:\Projects\junai-vscode
# edit package.json version
git add package.json; git commit -m "chore: bump version to X.Y.Z"
$env:VSCE_PAT = (Get-Content "vscode.pat" -Raw).Trim()
npm run publish   # package runtime exports + tsc + vsce publish
git push

# 5. Sync pool mirror (junai)
cd E:\Projects\junai
git add .github/agents .github/skills .github/prompts .github/instructions .github/diagrams .github/tools
git commit -m "feat: sync pool from agent-sandbox - YYYY-MM-DD"
git push
```

**Packaging internals:** packaging reads canonical `.github/`, builds runtime-specific project-local exports for Copilot/Claude/Codex, skips excluded assets like `vmie`, writes version metadata, then publishes. The extension should never write equivalent resources into user-level folders.

**Do NOT:**


## Institutional Knowledge

- `copilot-instructions.md` managed-section pattern since v0.6.2 — extension manages only a `<!-- junai:start -->` sentinel block; user content outside markers is never touched. Replaced the v0.5.7 USER_OWNED approach. junai system docs live in `junai-system.instructions.md`.
- Response discipline rules (no preamble, no closing summaries, dense confirmations) are enforced globally via `.github/instructions/terse-responses.instructions.md` (`applyTo: "**"`). Shipped to all runtimes via the `instructions` copy in `runtime-targets.json`.
- Canonical-source rule: author AI resources only in `.github/`; treat `.claude/` and `.codex/` as generated runtime targets, never hand-edited sources.
- Project-local-only rule: the extension ships runtime folders into each workspace and does not populate user-level instruction folders by default.
- `uv run` replaces `.venv` path in `mcp.json` (introduced v0.5.5) — no local Python install needed for MCP

Apply these rules whenever a task produces a **large, structured, multi-phase output** — specifically:
- 4 or more phases in a single session
- 50 or more expected output lines
- Multiple reference documents attached as constraints

**Rule 1 — Pre-Flight Scan:** Before writing any task line, produce a `Phase N — [Name]: ~N tasks expected` summary for ALL phases first. Do not start the main output until the pre-flight is complete.

**Rule 2 — Named Output File:** Write deliverables to a named file. Include `OUTPUT DESTINATION: <relative path>` in the prompt. Chat output is secondary.

**Rule 3 — Path Gate:** Before writing any `CREATE`/`UPDATE`/`CONFIGURE` line, verify the file path exists in the project directory spec. If not found: write `NOTE — [path] not found in directory spec, confirm before creating`.

**Rule 4 — No Abbreviation:** Never use "similar to Phase X", "as above", "same pattern", "follow approach in Phase N", "etc." in task descriptions. Every task line must be written in full.

**Rule 5 — Phase Boundary Re-Anchor:** After completing each phase section, re-read the fidelity constraints before starting the next phase.

**Rule 6 — Equal Depth:** Late phases (final 2–3) must have the same number of task lines as their deliverable count warrants. Do not summarise late phases.

**Rule 7 — Open Question Flagging:** Flag tasks blocked by open questions with `[OQ-N BLOCKER]` inline. Do not silently skip or assume resolution.

**Rule 8 — Post-Generation Self-Sweep (Mandatory):** After completing any large structured output, scan the last 40% for decay signals: `...`, `same pattern`, `as above`, `{ ... }`, `similar to Phase N`, `repeat for`, `and N more`. Expand every match in-place before delivering.
- `bundle-pool.js` `dir/dir` nesting guard introduced v0.5.2 — `cmdUpdate` auto-heals legacy nesting on activation
- Agent file naming: lowercase kebab-case matching the `name` frontmatter field exactly
- `validate_agents.py` `KNOWN_MODELS` allowlist must be updated whenever a new model is introduced
