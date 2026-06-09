---
type: reference
description: "Documents the VS Code / Copilot coding-agent tool capabilities available to junai agents: what each tool does, its limitations, and which agents have it."
Last Updated: 2025-01-01
---

# Tool Capability Manifest

This document describes the tool capabilities that junai agents can declare in their frontmatter `tools:` list. It is the authoritative reference for skill authors, agent authors, and the browser-first instruction file.

---

## Tool Reference

### `read`
Read files from the workspace. Always available.

### `search`
Search the workspace by text, regex, or semantic query. Always available.

### `edit`
Create and edit files in the workspace. Always available.

### `execute`
Run terminal commands. Always available to agents that declare it.

### `problems`
Access VS Code Problems panel (compile errors, lint errors). Runtime: VS Code Copilot only.

### `testFailure`
Access test failure output from the VS Code Test Explorer. Runtime: VS Code Copilot only.

### `changes`
Access the VS Code Source Control diff view (staged/unstaged changes). Runtime: VS Code Copilot only.

### `web`
VS Code integrated browser panel. Provides synchronous in-process browser actions:
- Navigate to a URL
- Click elements by CSS selector or ARIA label
- Read visible DOM text and computed state
- Take screenshots
- Fill form inputs

**Limits:**
- Only acts on the currently-open browser panel; cannot spawn new browser instances
- No network interception or request mocking
- No cross-origin iframe access beyond what the browser allows
- No multi-page automation flows (redirect chains require multiple tool calls)
- Not available in Claude coding agent, Codex agent, or non-VS-Code runtimes

**Fallback when `web` is unavailable or fails:** Load `.github/skills/workflow/playwright/SKILL.md` (if present) or `.github/skills/webapp/webapp-testing/SKILL.md` and use Playwright instead. See `.github/instructions/browser-first.instructions.md`.

### `github/*`
GitHub integration tools (search issues/PRs, read repo metadata). Runtime: VS Code Copilot with GitHub extension.

### `junai-mcp/*`
junai MCP server tools (9 tools: artefact management, pipeline-state, registry queries, etc.). Requires `uv run` MCP server running. See `.github/tools/mcp-server/server.py`.

### `context7/*`
Context7 MCP — library documentation lookup. Requires Context7 MCP server.

---

## Agent → Tool Matrix

| Agent | `web` | `problems` | `testFailure` | `changes` | `junai-mcp/*` | `context7/*` | `github/*` |
|-------|-------|-----------|--------------|----------|--------------|-------------|-----------|
| Implement | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Frontend Developer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Tester | ✅ | ✅ | ✅ | — | ✅ | ✅ | — |
| Streamlit Developer | ✅ | ✅ | — | — | — | ✅ | — |
| DevOps | ✅ | — | — | — | — | — | ✅ |
| UX Designer | ✅ | — | — | — | — | — | — |
| Accessibility | ✅ | — | — | — | — | — | — |
| Data Engineer | — | ✅ | — | — | — | ✅ | — |
| SQL Expert | — | ✅ | — | — | — | ✅ | — |
| Debug | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Anchor | — | ✅ | ✅ | — | ✅ | — | — |

*`—` means the agent's `tools:` frontmatter does not include this capability.*

---

## Runtime Support Matrix

| Tool | VS Code Copilot | Claude coding agent | Codex agent |
|------|----------------|--------------------|--------------------|
| `read` | ✅ | ✅ | ✅ |
| `search` | ✅ | ✅ | ✅ |
| `edit` | ✅ | ✅ | ✅ |
| `execute` | ✅ | ✅ | ✅ |
| `problems` | ✅ | ❌ | ❌ |
| `testFailure` | ✅ | ❌ | ❌ |
| `changes` | ✅ | ❌ | ❌ |
| `web` | ✅ | ❌ | ❌ |
| `github/*` | ✅ | ❌ | ❌ |
| `junai-mcp/*` | ✅ (if server running) | ✅ (if configured) | ✅ (if configured) |
| `context7/*` | ✅ (if server running) | ✅ (if configured) | ✅ (if configured) |

---

## Notes for Skill Authors

- Skills that use browser inspection (`web`) should include a "**Web tool not available?**" fallback block pointing to a Playwright alternative.
- Skills that reference `problems` or `testFailure` should note "VS Code only" if those tools are critical to the workflow.
- Do NOT assume `web` is available unless the agent explicitly declares it in `tools:`.
