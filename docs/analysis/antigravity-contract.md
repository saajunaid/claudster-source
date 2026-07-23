# Antigravity — agent-context discovery contract (probed, not assumed)

> **Two probed surfaces, one divergence.** The **CLI (`agy` v1.1.5, probed 2026-07-23)** — the
> Antigravity 2.0 harness — reads skills from **`.agents/skills/`**; the older **IDE 1.107.0
> (probed 2026-07-21)** read **`.claude/skills/`**. The claudster export target follows the CLI/2.0
> contract (`.agents/skills/`) as of 2026-07-23. Both read `AGENTS.md`.

## CLI `agy` v1.1.5 (Antigravity 2.0 harness) — probed 2026-07-23
Binary: `%LOCALAPPDATA%\agy\bin\agy.exe`. Method: `agy --help` + literal binary strings; auth via
Google OAuth (browser + paste-code; `agy -p` prints the login URL when unauthenticated).

| Surface | Contract |
|---|---|
| Headless run | `agy -p "<prompt>"` (`--print`), `--print-timeout <dur>` (default 5m), `--sandbox`, `--dangerously-skip-permissions`, `--mode accept-edits\|plan`, `--model`, `--effort low\|med\|high`, `--add-dir` |
| Rules/memory | `GEMINI.md`, `AGENTS.md`, `.agents/rules/*.md` (customization root `.agents/`, alt `.agent/`) |
| **Skills** | **`.agents/skills/<name>/SKILL.md`** — flat one level; auto-discovered in the workspace. `skills.json` is only for NON-standard/shared locations (optional) |
| Skill format | SKILL.md **must start** with YAML frontmatter containing `name` + `description` (same rule as codex — the 2026-07-21 fence fix matters here too) |
| Global config | `~/.gemini/config/` (MCP: `~/.gemini/config/mcp_config.json`); CLI settings `~/.gemini/antigravity-cli/settings.json` |
| Plugins | `agy plugin install/list/...`, `.agents/plugins/` |

## IDE 1.107.0 — probed 2026-07-21 (LEGACY skills path)

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
- IDE layout contract: probed from the shipped workbench bundle (above) — high confidence.
- CLI contract: probed from `agy --help` + binary strings (2026-07-23) — high confidence.
- **LIVE-VALIDATED ✅ (2026-07-23, `agy` v1.1.5 headless, bundle-seeded scratch repo):**
  the agent read the bundle's AGENTS.md (correct absolute path, all 6 Laws), discovered the
  bundle's skills from `<workspace>/.agents/skills/`, read a SKILL.md's frontmatter, and executed
  the `git-commit` skill workflow correctly (emitted a conventional commit to the skill's rules).

## Headless scripting gotchas (learned live — cite before wrapping agy)
- **`agy -p` binds to the LAST ACTIVE project, not the cwd.** Without `--new-project` (or
  `--project <id>`) it answered from a previous project's workspace + `~/.agents/skills`.
  Always pass `--new-project` when validating a fresh directory.
- Headless tool calls are **auto-denied** ("a tool required the command permission") — pass
  `--dangerously-skip-permissions` (throwaway dirs only) or add `permissions.allow` rules in
  `~/.gemini/antigravity-cli/settings.json`.
- `--sandbox` **hung to timeout on Windows Server 2019** — avoid it here until re-probed.
- User-level skills at `~/.agents/skills/` are merged into discovery alongside workspace skills;
  builtin skills live under `~/.gemini/antigravity-cli/builtin/skills`.
- Default `--print-timeout` is 5m; real answers took ~1–3m on this box.
