# Antigravity IDE 1.107.0 — agent-context discovery contract (probed 2026-07-21, not assumed)

Probed from the installed product on the dev workstation: `%USERPROFILE%\AppData\Local\Programs\Antigravity IDE`
(version 1.107.0, VS Code fork, launcher `bin\antigravity-ide.cmd`). Method: literal strings extracted from
`resources\app\out\vs\workbench\workbench.desktop.main.js` (the agent runtime is compiled into the
workbench bundle). Re-probe on version bump — this surface churns.

## What Antigravity reads for agent context

| Surface | Path | Notes |
|---|---|---|
| Project memory | `**/AGENTS.md` (workspace-wide file search) | `InstructionsContextComputer` logs "AGENTS.md files added" — nested AGENTS.md files are picked up too |
| **Skills** | `<workspace folder>/.claude/skills/<name>/SKILL.md` | `findClaudeSkillsInFolder` — **Claude skill format, verbatim**. **FLAT: one directory level**; it iterates the children of `.claude/skills` and requires `SKILL.md` directly inside each — `<category>/<name>/` nesting is NOT discovered |
| Rules | `.agents/rules/*` (primary) or `.agent/rules/*` (alternate) per workspace folder | `localRulesFilePathSegments: [".agents","rules"]`, alternate `[".agent","rules"]` |
| Global memory | `~/.gemini/GEMINI.md` | `globalMemoriesPathSegments` |
| MCP | `.gemini/mcp_config.json` | sits next to the rules config in the same settings object — the Phase-5 junai-mcp seam |

## Implications for the claudster export target
- Reuse the codex bundle's `AGENTS.md` (same template) — Antigravity discovers it natively.
- Skills export to `.claude/skills/` with `flatten_skills: true` (the exporter already does this for the
  Claude plugin bundle). A category-nested tree (codex shape) would be silently invisible.
- No approvals/sandbox/exec contract to probe: Antigravity is an IDE, not a headless CLI — there is no
  `exec`-equivalent to script. (The separate "Gemini CLI"/Agent CLI is NOT installed on this box.)
- Because Antigravity reads the *Claude* skill layout, any repo with skills vendored under
  `.claude/skills/` serves Claude Code (project-level skills) and Antigravity from the SAME directory.

## Validation state
- Layout contract: probed from the shipped workbench bundle (above) — high confidence.
- Live in-IDE confirmation (open a bundle-seeded workspace, verify the agent lists the skills):
  **HUMAN step** — the IDE has no headless probe equivalent to `codex debug prompt-input`.
