# junai — Publish & Distribution Plan

> Meta-plan for making junai discoverable and adopted. Not part of the pipeline framework itself.

---

## Phase 1 — LinkedIn Post (immediate)

**Goal:** First public signal, build initial GitHub stars.

**Post format:** Image + text post (NOT article — posts get more reach)

**Suggested copy:**
> I kept watching AI agents hallucinate the wrong next step in a pipeline.
>
> So I replaced LLM-inferred routing with a Python state machine.
>
> Result: a deterministic 9-stage agent pipeline inside VS Code Copilot — git-blameable, auditable, no hallucinated routing.
>
> → Intent → PRD → Architect → Plan → Implement → Test → Review → Close
>
> Open source. Just `.agent.md` files + a state machine. Drop it into any project.
>
> [link to https://github.com/saajunaid/junai]

**Attach:** `diagrams/junai-pipeline-poster.svg` converted to PNG/JPG (LinkedIn renders image posts higher than link previews).

**Best posting time:** Tuesday–Thursday, 8–10am local time.

**Hashtags:** `#GitHubCopilot` `#AIAgents` `#VSCode` `#BuildInPublic` `#DeveloperTools` `#LLM` `#Python`

---

## Phase 2 — GitHub Discoverability

**Goal:** Searchable via GitHub Topics.

**Actions:**
- Go to `https://github.com/saajunaid/junai` → About (gear icon)
- Add topics: `copilot`, `ai-agents`, `vscode`, `llm`, `prompt-engineering`, `devops`, `state-machine`, `github-copilot`, `python`, `developer-tools`
- Add a one-liner description: "Deterministic 9-stage agent pipeline for VS Code + GitHub Copilot"
- Confirm "Template repository" is checked (done ✅)

---

## Phase 3 — Dev.to Article

**Goal:** SEO long-tail, indexes within days, drives sustained GitHub traffic.

**Title options:**
- "Why I replaced LLM-inferred routing with a Python state machine in my Copilot agent pipeline"
- "Building a deterministic AI agent pipeline in VS Code — no framework, just .md files and a state machine"

**Article outline (write from TBD.md §1–§4):**
1. The problem: agents hallucinate routing decisions
2. The solution: a transition table that owns all routing logic
3. How it works: 9 stages, pipeline-state.json, MCP tools
4. How to use it: template repo → `project-config.md` → `@Orchestrator`
5. GitHub link + call to action

**Cross-post to LinkedIn** as a shared article link (gets less reach than native post, but builds credibility).

---

## Phase 4 — Hacker News Show HN

**Goal:** Credibility + spike in GitHub stars.

**Threshold before posting:** ~50 GitHub stars (HN community responds better when there's existing signal).

**Post format:**
> Show HN: junai – deterministic agent pipeline for VS Code Copilot (github.com/saajunaid/junai)

**Comment prep:** Be ready to answer:
- "How is this different from LangChain/LangGraph?"
- "Why not just use a workflow engine?"
- "Does this work without Copilot Pro?"

---

## Phase 5 — Awesome Lists

Submit to these lists (open a PR on each):
- [ ] `awesome-copilot` (search GitHub)
- [ ] `awesome-ai-agents`
- [ ] `awesome-vscode`

---

## Phase 6 — VS Code Extension (future)

**Goal:** One-click install from the VS Code Marketplace.

**What it would do:** "Scaffold junai pipeline" command → installs `.github/` into the open workspace, same as `junai-pull` but without PowerShell.

**Effort:** ~1 sprint. Needs a `package.json` extension manifest and a single command contribution.

---

## Phase 7 — MCP Registry (future)

List the 5 MCP tools (`notify_orchestrator`, `validate_deferred_paths`, `get_pipeline_status`, `set_pipeline_mode`, `satisfy_gate`) in the VS Code MCP server registry.

This surfaces junai to any MCP-compatible client, not just GitHub Copilot.

---

## Status Tracker

| Phase | Status | Notes |
|---|---|---|
| Template repository enabled | ✅ Done | `saajunaid/junai` is now a GitHub template |
| LinkedIn post | ⏳ Pending | Draft copy above — needs pipeline poster as PNG |
| GitHub topics | ⏳ Pending | Manual step in GitHub UI |
| Dev.to article | ⏳ Pending | Write from TBD.md outline |
| Hacker News | ⏳ Pending | Wait for ~50 stars first |
| Awesome list PRs | ⏳ Pending | After HN / LinkedIn |
| VS Code extension | 🔲 Backlog | Future sprint |
| MCP registry | 🔲 Backlog | Future sprint |
