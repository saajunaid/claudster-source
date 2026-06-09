# junai — Pipeline & Distribution Backlog

> Living backlog for all outstanding work on the junai framework and distribution.
> All items are scoped with: where to execute, which session, and the prime prompt to use.
> Update status as items complete.

---

## Status Legend

| Symbol | Meaning |
|---|---|
| ✅ Done | Complete and synced to all repos |
| 🔄 In Progress | Active work |
| ⏳ Next | Ready to start — no blockers |
| 🔲 Backlog | Planned but not yet started |
| 🗂 Deferred | Intentionally parked |

---

## Step 1 — AutoMode Pipeline Test: Chat Widget Icon Rebrand

**Status:** ✅ Done (feature: `change-chatwidgeticon`, pipeline completed 2026-02-22 in *assisted* mode)
**Where:** Customer360 VS Code window  
**Session:** New chat session (don't carry over planning context)  
**Scope:** Replace Chat Widget header icon with `src/assets/info-center-animated.svg`

**Pre-session terminal (reset state for new pipeline):**
```powershell
cd E:\Projects\Customer360
# Either via chat: "Start a new pipeline for feature: chat-widget-icon-rebrand"
# Or via terminal:
python .github/tools/pipeline-runner/pipeline_runner.py init --project customer360 --feature chat-widget-icon-rebrand --type feature
```

**Prime prompt to `@Orchestrator`:**
```
Read .github/pipeline-state.json and .github/project-config.md.

New feature:
Replace the Cyber bot icon in the Chat Widget header with the app logo.
- Current icon: cyber bot SVG (Chat Widget header)
- Replacement: src/assets/info-center-animated.svg
- Scope: Chat Widget header only, no other UI changes

I want to run this in auto mode. Recommend the right pipeline mode before we start.
```

**What was done:** Pipeline ran in assisted mode (was called auto at the time). Test file path resolved (`tests/test_juno_vibo_iframe.py`, not root). Pipeline closed successfully through all stages including static analysis.

**What the test validated:**
- `pipeline_init` / `pipeline_reset` MCP tools
- `notify_orchestrator` stage completion routing
- `satisfy_gate` gate approval
- Tester retry loop
- `Return to Orchestrator` handoff button
- Static test execution via `run_command` (no server needed)

---

## Step 2 — Troubleshoot AutoMode Issues (if any)

**Status:** ✅ Done — one issue found and resolved: test file was at `tests/test_juno_vibo_iframe.py`, not project root as tester assumed. Static analysis test confirmed (no server needed). All edge cases resolved.  
**Where:** Customer360 session (same as Step 1)

**If session breaks mid-pipeline, prime prompt for recovery:**
```
Read .github/pipeline-state.json. The pipeline was running in auto mode for
feature "chat-widget-icon-rebrand". Resume from current_stage. Do not re-run
completed stages. Orchestrator §9.2 drift resync applies if stage is uncertain.
```

---

## Step 3 — README.md for Strangers ✅ Done

**Status:** ✅ Done (`d2055a4` junai, `7f45dcd` Customer360)  
**Where:** junai repo directly (README.md is not a pool file)  
**What was done:** Full README rewrite — Path A (template), Path B (junai-pull), venv setup, 8 MCP tools table (`run_command` added), chat-first pipeline commands, agents overview, 3-mode explanation (supervised / assisted / autopilot)  
**Line count:** ~160 lines (under 200 target)

---

## Step 4 — TBD.md Template Repository + Init Steps ✅ Done

**Status:** ✅ Done (this session)  
**Where:** Customer360, current session  
**What was done:**
- Added §3a Path A (GitHub template) and §3b Path B (junai-pull) with correct steps
- Updated §3c venv with combined pip install command
- Updated §3d to show 7 tools (was 5), chat-first init, CLI as alternative
- Removed stale "CLI-only" note — `pipeline_init` is now an MCP tool

---

## Step 5 — Relocate `tools/` to `.github/tools/` (IDE-Agnostic Cleanup)

**Status:** ✅ Done — completed 2026-02-22 (agent-sandbox `a03d93b`)
**Result:** All 123 tests pass. `tools/` lives at `.github/tools/` across all 3 repos.

**What this involves:**
- Move `tools/` to `.github/tools/` in agent-sandbox
- Update `server.py`: `WORKSPACE_ROOT / "tools"` → `WORKSPACE_ROOT / ".github" / "tools"`
- Update `sync.ps1`: copy from/to `.github/tools/` instead of `tools/`
- Update all CLI examples in README.md and TBD.md
- Update `.vscode/mcp.json` path references
- Run test suite to verify

**Why:** `.github/` is a git-standard folder understood by all IDEs (VS Code, Cursor, Windsurf, JetBrains). Putting `tools/` inside makes junai fully IDE-agnostic and reduces the deploy footprint to a single folder.

**Prime prompt:**
```
Read .github/project-config.md and tools/ directory structure.

Task: Move tools/ into .github/tools/ for IDE-agnostic deployment.

Files to update: tools/mcp-server/server.py (WORKSPACE_ROOT path),
sync.ps1 (all 4 functions), .vscode/mcp.json, README.md CLI examples,
.github/pipeline/TBD.md CLI examples.

Run the full test suite after moving. Commit when tests pass.
```

---

## Step 5-VS — Build VS Code Extension

**Status:** ✅ Done — published to VS Code Marketplace 2026-02-22; latest v0.1.2  
**Where:** Done outside pipeline (direct scaffolding session)  
**Extension ID:** `junai-labs.junai` · Publisher: `junai-labs`  
**Marketplace:** https://marketplace.visualstudio.com/items?itemName=junai-labs.junai  
**GitHub:** https://github.com/saajunaid/junai-vscode  
**What shipped:**
- v0.0.1: 3 commands (`junai: Initialize Agent Pipeline`, `junai: Show Pipeline Status`, `junai: Set Pipeline Mode`), 587 pool files bundled, animated SVG + PNG icon
- v0.0.2: auto-writes `.vscode/mcp.json` with `uvx junai-mcp` entry on init
- v0.0.3: renamed to `junai — Agentic Pipeline`, keyword-optimised description, 12 keywords
- v0.0.4: new orbital pipeline icon (dark background, ring, glowing nodes, arrowhead arcs)
- v0.0.5: fixed marketplace README (user-facing); welcome prompt on activation; `mcpServers` contribution + AI/Chat categories; full pool rebundle (606 files)
- v0.0.6: SEO — renamed to `junai - AI Agent Pipeline`; keyword-optimised keywords for marketplace search ranking
- v0.0.7: `galleryBanner` dark theme; `qna` link; removed `icon.gif` dead weight from VSIX
- v0.0.8: added `junai: Remove from this project` command; stripped `diagrams/` from pool
- v0.0.9: fixed stale pool content (bundle-pool now clears pool/ before copy); diagrams confirmed absent from VSIX
- v0.1.0: added `junai: Update Agent Pool` command — merges latest agents/skills/prompts over existing files, skips `pipeline-state.json` and `project-config.md` (user-owned). Creates a retention loop: staying installed means future pool improvements land automatically; uninstalled users are frozen on their downloaded version
- v0.1.1: fixed `contributes.mcpServerDefinitionProviders` (was wrong `mcpServers` key); added `agent-docs/`, `plans/README.md`, `handoffs/README.md` to pool (from clean agent-sandbox source); engines bumped to `^1.101.0`; security: confirmed pool sources from agent-sandbox only (Customer360 plans contained client data)
- v0.1.2: new icon (`iconfinal_icon128.png`, 128×128, 17KB)

**Pre-session:**
```powershell
python .github/tools/pipeline-runner/pipeline_runner.py init --project junai --feature vscode-extension --type feature
```

**Prime prompt to `@Orchestrator`:**
```
Read .github/pipeline-state.json and .github/project-config.md.

New feature: Build a VS Code Marketplace extension for junai.

Goal: Single command "junai: Scaffold pipeline" — copies .github/ (agents, skills,
prompts, instructions, diagrams, tools) into the currently open workspace. Equivalent
to junai-pull but requires no PowerShell and no cloned junai repo.

Target users: developers who find junai on the VS Code Marketplace and want zero-friction
setup. Should work on Windows, Mac, and Linux.

Prerequisites:
- .github/tools/ relocation (Step 5) should be complete so the extension deploys a single folder
- vsce publisher account needed before marketplace publish step

Start in supervised mode. Begin at intent stage.
```

**Pre-publish checklist (record in TBD.md §20 when building):**
- [ ] `package.json` extension manifest
- [ ] Activation event + command contribution
- [ ] File copy logic (cross-platform: Windows, Mac, Linux)
- [ ] `vsce package` build step
- [ ] Publisher account at https://marketplace.visualstudio.com/manage
- [ ] README and icon for Marketplace listing

---

## Step 6-MCP — MCP Server Publication

**Status:** ✅ Done — published to `registry.modelcontextprotocol.io` 2026-02-22  
**Where:** junai repo (done outside pipeline — direct package publish session)  
**PyPI:** https://pypi.org/project/junai-mcp/0.1.1/  
**Registry name:** `io.github.saajunaid/junai-mcp` version 0.1.1  
**Depends on:** Step 5-VS (extension first — MCP registry is smaller audience, do after)

**What was done:**
- Created Python package `junai-mcp` with `src/junai_mcp/server.py` (fixed WORKSPACE_ROOT portability + runner path `.github/` prefix)
- Created `pyproject.toml` (setuptools.build_meta, v0.1.1), `server.json` (77-char description ✅)
- Added `<!-- mcp-name: io.github.saajunaid/junai-mcp -->` to README.md for ownership verification
- Uploaded `junai_mcp-0.1.1` to PyPI via twine
- Downloaded `mcp-publisher v1.4.1`, ran `login github` + `publish` → ✓ Successfully published
- Ownership proof in PKG-INFO line 24 confirmed before publish

**Pre-session:**
```powershell
python .github/tools/pipeline-runner/pipeline_runner.py init --project junai --feature mcp-server-publication --type feature
```

**Prime prompt to `@Orchestrator`:**
```
Read .github/pipeline-state.json.

New feature: Publish the junai MCP server to the VS Code MCP server registry.

The MCP server is at `.github/tools/mcp-server/server.py`. It exposes 8 tools: pipeline_init, pipeline_reset, notify_orchestrator,
validate_deferred_paths, get_pipeline_status, set_pipeline_mode, satisfy_gate, run_command.

Goal: List it in the VS Code MCP registry so users can add it to .vscode/mcp.json with
a single entry. The correct registry is https://registry.modelcontextprotocol.io (not
https://github.com/microsoft/vscode-mcp-servers — that is stale/incorrect).

Start in supervised mode. Begin at intent stage.
```

---

## Step 7 — Update README + TBD for VS Code Extension and MCP

**Status:** ✅ Done — README Distribution ✅; TBD §20 (VS Code Extension) ✅; TBD §21 (MCP Server) ✅. All three committed to Customer360.  
**Where:** junai (README), Customer360 (TBD.md) — can be one session  
**Session:** New chat session in junai workspace

**Prime prompt:**
```
Read README.md. Also read E:\Projects\Customer360\.github\pipeline\TBD.md.

Two tasks:
1. Add a "Distribution" section to README.md:
   (a) VS Code Marketplace extension — install command, what it deploys
   (b) MCP Server registry listing — how to add to .vscode/mcp.json
2. Add §20 to TBD.md: "VS Code Extension" — installation, what it deploys, when to use vs junai-pull
   Add §21 to TBD.md: "MCP Server Publication" — registry entry format, manual .vscode/mcp.json setup

Commit README in junai. Commit TBD.md in Customer360, then sync to junai.
```

---

## Step 8 — Write Full User Guide (USERGUIDE.md)

**Status:** ✅ Done — `USERGUIDE.md` written and pushed to `saajunaid/junai` (`60a8704`). All 21 sections covered, validated against agents.registry.json, server.py, and pool file counts.  
**Where:** junai workspace  
**Session:** New dedicated session — large writing task

**Prime prompt:**
```
Read .github/pipeline/TBD.md in E:\Projects\Customer360 in full (all 21 sections).
Also read README.md in this workspace.

Write USERGUIDE.md in this repo based on TBD.md §1–§21.
Validate every claim before writing — check actual files in agents/, skills/, tools/.
Do not fabricate tool names, command syntax, or file paths.

Audience: stranger who found junai on GitHub. Has VS Code and GitHub Copilot.
Tone: clear, direct, no marketing fluff.

Commit when complete.
```

---

## Step 9 — Self-Contained Binary / Installer (Future)

**Status:** 🗂 Deferred  
**Why deferred:** The one remaining terminal step (venv creation) could be eliminated by shipping a self-contained executable (PyInstaller bundle) that bootstraps the venv automatically. Not worth the build complexity until the core framework is widely adopted.

**When to revisit:** After VS Code Extension ships. If users complain about the venv step in the extension, build a bundled version.

**Options when ready:**
- PyInstaller: bundle `pipeline_runner.py` + `server.py` as a single `.exe` / Unix binary
- VS Code Extension can execute the binary directly (no Python on PATH required)
- MCP server can be packaged as an npm package with node bindings

---

## Step 10 — LinkedIn Post + Distribution

**Status:** ⏳ Next (can do after README is ready — Step 3 ✅)  
**Where:** No VS Code needed  
**Session:** N/A

**Action plan (from publish.md):**

1. **GitHub topics** (5 min): go to `https://github.com/saajunaid/junai` → Settings → About → add topics:
   `copilot`, `ai-agents`, `vscode`, `llm`, `prompt-engineering`, `github-copilot`, `state-machine`, `python`, `developer-tools`

2. **Export pipeline poster to PNG**: open `diagrams/junai-pipeline-poster.svg` in browser → screenshot or save as PNG for LinkedIn image

3. **LinkedIn post** (copy from publish.md Phase 1):
   > I kept watching AI agents hallucinate the wrong next step in a pipeline.
   > So I replaced LLM-inferred routing with a Python state machine.
   > Result: a deterministic 9-stage agent pipeline inside VS Code Copilot — git-blameable, auditable, no hallucinated routing.
   > Open source. Just `.agent.md` files + a state machine.
   > [link to https://github.com/saajunaid/junai]
   Attach pipeline poster PNG. Post Tuesday–Thursday 8–10am.

4. **Dev.to article** (follow-up week): see publish.md Phase 3 for outline

5. **Hacker News Show HN**: wait for ~50 GitHub stars first

---

## Pre-VS Code Extension Checklist

Before starting Step 5-VS, confirm these are all done:

- [x] tools/ deployed by junai-pull (done `d59099e`)
- [x] pipeline_init and pipeline_reset MCP tools (done `91cbb16`)
- [x] README.md rewritten for strangers (done this session)
- [x] TBD.md §3 updated with correct paths and 7-tool count (done this session)
- [ ] tools/ relocated to .github/tools/ (Step 5 — do first)
- [ ] .vscode/mcp.json verified present in junai repo (check before extension build)
- [x] vsce publisher account created at https://marketplace.visualstudio.com/manage (`junai-labs`)

---

## Sync Approach (always follow this order)

```
agent-sandbox  →  Customer360  →  junai-push  →  GitHub (origin/main)
```

- Code changes: agent-sandbox first
- Pool files (.github/): robocopy agent-sandbox → Customer360, then junai-push
- Root files (sync.ps1, tools/, README.md): manual copy agent-sandbox → Customer360, then junai-push
- README.md exception: lives only in junai (not a pool file), edit there directly
- PIPELINE-GAPS.md, TBD.md, PIPELINE-BACKLOG.md: Customer360 only (project docs, not synced to junai)

---

## Step 11 — Refresh Pipeline Documentation & Diagrams

**Status:** ✅ Done (2026-02-23)  
**Where:** Customer360 + agent-sandbox + junai  
**Commits:** Customer360 `fb5b100` · agent-sandbox `281d5f3` · junai `d72f513` (pushed)

**Completed:**
- `advisory-hub-mode.svg` — Card C regenerated: "Supervisor vs Auto Mode" → "Pipeline Modes" with supervised / assisted / autopilot descriptions
- `agent-pipeline-poster.svg` — Pattern F label updated: "F. Supervisor Mode (AdvisoryHub)" → "F. AdvisoryHub Mode"; note updated to "works in any pipeline mode"
- `pipeline-entry-guide.svg` — scanned, no stale mode text found, no changes needed
- Cascaded both updated SVGs → agent-sandbox and junai; junai pushed to origin

### 11a. PIPELINE-ENTRY-GUIDE.md (Customer360 only)
**Assessment:** Keep — it documents 8 pipeline entry scenarios (A–H) with exact prompts; useful pre-reading before USERGUIDE.md.  
**What needs updating:**
- Add pipeline mode note near the top (supervised / assisted / autopilot)
- Scenario A prime prompt still references `I want to run this in auto mode` indirectly — sanitise
- Review gate names and stage references for accuracy against current `agents.registry.json`

### 11b. pipeline-flowchart.md (Customer360 only)
**Status:** ✅ Already updated (2026-02-22) — `MODE_A` changed from "auto" to "assisted / autopilot"

### 11c. svg-poster-brief.md (Customer360 only)
**Status:** ✅ Already updated (2026-02-22) — Panel C mode description updated for 3-mode system

### 11d. .github/diagrams/ SVG files — REGENERATION NEEDED
All SVG files must be reviewed and regenerated where stale. Key files:
- `advisory-hub-mode.svg` — still has **"Supervisor vs Auto Mode"** (line 67) and **"Auto Mode (future)"** (line 71) — **must regenerate**
- `pipeline-entry-guide.svg` — review for stale mode/stage text
- `agent-pipeline-poster.svg` — review for stale mode/stage text

**Cascade:** Regenerated SVGs must be copied to agent-sandbox and junai `.github/diagrams/`

**Prime prompt to `@svg-diagram` agent:**
```
Read .github/pipeline/svg-poster-brief.md for the full design spec.
Also inspect .github/diagrams/advisory-hub-mode.svg — it has stale text:
  line 67: "Supervisor vs Auto Mode"
  line 71: "Auto Mode (future) — fully autonomous pipeline"

Update both text labels to reflect the 3-mode system (supervised / assisted / autopilot).
Then review pipeline-entry-guide.svg and agent-pipeline-poster.svg for any stale
"auto mode" or "supervised vs auto" language and apply the same correction.

Save updated SVGs in .github/diagrams/. Commit when done.
```

**After diagrams update:**
1. Cascade `.github/diagrams/` from Customer360 to agent-sandbox and junai
2. Commit all 3 repos

---

## Step 12 — IDE-Agnostic Multi-IDE Support

**Status:** 🔲 Backlog  
**Where:** agent-sandbox (core changes) → cascade to junai → junai-vscode (extension updates)  
**Session:** New dedicated session — do not combine with other pipeline work  
**Scope:** Make junai work as an AI agent pipeline framework across VS Code, Cursor, Claude Code, and Codex — without changing the core pipeline state machine or MCP server.

---

### What's Already Agnostic (don't touch)

| Component | Why it's already portable |
|---|---|
| `pipeline-state.json` | Plain JSON — any tool reads it |
| `.github/tools/pipeline-runner/` | Pure Python CLI, no IDE dependency |
| `.github/tools/mcp-server/server.py` | MCP is a universal protocol — VS Code, Cursor, Claude Code, Windsurf all support it |
| Agent instruction body (markdown text) | Reusable as-is across all IDEs |
| `.github/` folder placement | Git-standard — all IDEs recognise it |

**Do not refactor these.** The portability work is purely an adapter layer on top.

---

### What Needs an Adapter Per IDE

| Component | VS Code (current) | Cursor | Claude Code | Codex |
|---|---|---|---|---|
| Agent definition files | `.github/agents/*.agent.md` (frontmatter: `name`, `tools`, `handoffs`, `model`) | `.cursor/rules/*.mdc` | `CLAUDE.md` + `claude.json` project config | `AGENTS.md` |
| MCP server registration | `.vscode/mcp.json` | `.cursor/mcp.json` | Project-level config file | N/A (no MCP yet) |
| Autopilot watcher | `junai-vscode` extension (`workbench.action.chat.open<AgentName>` + `steerWithMessage`) | No VS Code API — needs standalone CLI watcher | `claude --print` CLI invocation | `codex` CLI invocation |

---

### Recommended Architecture

Introduce a generator command:

```
junai ide setup --target cursor
junai ide setup --target claude-code
junai ide setup --target vscode      # already default, no-op
```

Each invocation:
1. Reads `.github/agents/*.agent.md` pool (single source of truth — never duplicated)
2. Emits IDE-specific agent configs into the appropriate folder
3. Writes the MCP config for that IDE if one does not already exist
4. Leaves `pipeline-state.json`, pipeline-runner, and MCP server completely untouched

A companion watcher script (`junai-watch.py`) handles autopilot invocation for non-VS Code IDEs by polling `pipeline-state.json` and invoking agents via their respective CLI.

---

### Implementation Phases

**Phase 1 — Cursor adapter (lowest effort, highest ROI)**
- `.cursor/rules/` generator: strip VS Code frontmatter, emit `.mdc` format per agent
- `.cursor/mcp.json` generator (structurally identical to `.vscode/mcp.json` — swap variable names)
- Standalone `junai-watch.py` poller: reads `_routing_decision`, invokes agent via Cursor CLI or clipboard fallback
- Test: run a full pipeline in Cursor with generated configs

**Phase 2 — Claude Code adapter**
- `CLAUDE.md` generator: top-level instruction file referencing the agent pool for Claude Code project context
- `claude.json` project config (if applicable per version)
- `junai-watch.py` extended: `claude --print "<prompt>"` invocation path

**Phase 3 — Codex adapter**
- `AGENTS.md` generator (OpenAI Codex format)
- MCP support TBD — Codex MCP is not stable as of Feb 2026; defer until GA

---

### Caveats and Things to Watch Out For

**1. Agent frontmatter is VS Code Copilot-specific — do not try to make it universal**  
The `name:`, `tools:`, `handoffs:`, `model:` fields are parsed by the Copilot extension only. Cursor uses `.mdc` with different keys. Claude Code ignores frontmatter entirely. The generator must *translate*, not *share*. The body of each `.agent.md` is what is reusable.

**2. `handoffs:` have no direct equivalent in Cursor or Claude Code**  
VS Code Copilot renders handoffs as clickable UI buttons. No other IDE has this concept. The generator should emit a plain-text "Handoff shortcuts" section at the bottom of each generated file listing the same targets as copy-paste prompts — or the autopilot watcher handles transitions programmatically.

**3. `junai-watch.py` is not as seamless as the VS Code extension**  
The extension hooks into VS Code internal APIs for zero-click autopilot. A CLI watcher requires a terminal to stay running and uses clipboard-paste or CLI invocation — more friction. Document this clearly as "semi-autopilot" for non-VS Code targets.

**4. Don't overwrite VS Code files when setting up another IDE**  
`junai ide setup --target cursor` must not touch `.vscode/mcp.json` or `.github/agents/`. Adapters are additive-only. Add a `--dry-run` flag to preview generated files before writing.

**5. MCP server path in generated configs must be robust — not hardcoded**  
VS Code uses `${workspaceFolder}`; Cursor uses `${workspaceRoot}`. The generator must resolve these correctly per target. Never hardcode absolute paths into generated configs.

**6. Generated IDE config files are NOT pool files**  
`.cursor/`, `CLAUDE.md`, `AGENTS.md` are generated locally per project. They are **not** synced through the agent-sandbox → junai cascade. Only the generator script itself lives in the pool. Each developer runs `junai ide setup` in their own workspace.

**7. Test matrix is large — tackle one IDE per session**  
Ship Cursor adapter first (most adopted, most similar to VS Code). Validate a full pipeline end-to-end before starting Claude Code. Do not combine Phase 1 and Phase 2 in the same session.

**8. `steerWithMessage` and `open<AgentName>` are VS Code private APIs — do not leak them**  
The autopilot watcher in `junai-vscode` uses `workbench.action.chat.open<AgentName>` and `workbench.action.chat.steerWithMessage`, both locked behind `enabledApiProposals`. These have no equivalent in other IDEs. The standalone `junai-watch.py` must never attempt to call VS Code internal commands.

---

### Prime Prompt (when ready to start — Phase 1 Cursor)

```
Read .github/pipeline-state.json and .github/project-config.md.
Also read .github/pipeline/PIPELINE-BACKLOG.md Step 12 for full design context.

New feature: IDE-agnostic adapter layer — Phase 1 (Cursor).

Goal: Add a `junai ide setup --target cursor` CLI command that:
1. Reads .github/agents/*.agent.md pool files
2. Generates .cursor/rules/<agent-name>.mdc for each agent
   (translate VS Code frontmatter to Cursor .mdc format; keep instruction body unchanged)
3. Generates .cursor/mcp.json from .vscode/mcp.json
   (swap ${workspaceFolder} → ${workspaceRoot}; do not modify .vscode/mcp.json)

Also create .github/tools/junai-watch.py: a standalone poller that checks
pipeline-state.json every 2s, detects a non-None _routing_decision.target_agent,
and invokes the target via `cursor --agent "<name>" "<prompt>"` with clipboard fallback.

Constraints:
- Do not touch .github/agents/, .vscode/mcp.json, pipeline-state.json, or the MCP server
- Generator is additive only — never overwrites unless --force is passed
- Add --dry-run flag that prints what would be generated without writing
```
