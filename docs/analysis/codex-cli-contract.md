# Codex CLI 0.137.0 — headless + discovery contract (probed 2026-07-21, not assumed)

Probed live on the dev workstation (`codex-cli 0.137.0`, npm install, Windows). Sources: `codex --help`,
`codex exec --help`, `codex doctor`, `codex features list`, and literal strings extracted from the
shipped binary (`@openai/codex-win32-x64 … bin/codex.exe`). Every claudster codex integration cites
THIS file; re-probe on version bump (0.145.0 already available).

## Auth state (this box)
`codex doctor` → "auth is configured" (mode `chatgpt`, tokens in `%USERPROFILE%\.codex\auth.json`),
**BUT a live `codex exec` failed with "refresh token was revoked"** — doctor checks token *presence*,
not validity. **HUMAN: `codex logout && codex login` before any model-call validation.**
(Also: WebSocket to chatgpt.com fails on this network; HTTPS fallback reachable.)

## Non-interactive execution
```
codex exec [OPTIONS] [PROMPT]        # aliases: codex e
```
Verbatim-confirmed flags (from `codex exec --help`):

| Need | Flag |
|---|---|
| working dir | `-C, --cd <DIR>` (plus `--add-dir <DIR>` for extra writable roots) |
| approvals | **NONE — `exec` has no `-a/--ask-for-approval`** (live-verified: "unexpected argument"; that flag is interactive-only). Headless behavior is governed by `--sandbox` alone |
| model | `-m, --model <MODEL>` |
| sandbox | `-s, --sandbox <read-only\|workspace-write\|danger-full-access>` |
| JSON events | `--json` (JSONL on stdout) |
| **last message** | `-o, --output-last-message <FILE>` — **preferred parse target** |
| structured output | `--output-schema <FILE>` (JSON Schema for the final response) |
| outside a git repo | `--skip-git-repo-check` |
| no session persistence | `--ephemeral` |
| ignore user config | `--ignore-user-config` (auth still via `CODEX_HOME`) |
| config override | `-c key=value` (dotted TOML paths) |

Read-only review shape: `codex exec -s read-only -o out.txt "<prompt>"`.
`codex review` / `codex exec review` also exist as a first-class non-interactive code review.

## Project-context discovery (what an exported bundle must look like)
- **AGENTS.md** — read as project memory. Binary also references `CLAUDE.md` alongside `AGENTS.md`
  (fallback chain), and a `child_agents_md` feature (off) for nested files.
- **Skills — project root: `.codex/skills/`** (binary: "for repos this is usually `.codex/skills`").
  User-level: `$CODEX_HOME/skills` i.e. `~/.codex/skills` (several flags default there).
  **NOT `.agents/skills/`** — in 0.137 `.agents/` is only the *plugins marketplace* root
  (`.agents/plugins/marketplace.json`). The pre-probe claudster export target guessed `.agents/skills/`
  → **wrong, fixed 2026-07-21**.
- **Skill format: `SKILL.md` with YAML frontmatter, VALIDATED**:
  - `name` and `description` required non-empty; `disable-model-invocation` must be false if present.
  - **Unexpected frontmatter keys are rejected** ("Unexpected key(s) in SKILL.md frontmatter:
    {unexpected}. Allowed properties are: {allowed}" — full allowed set not extractable statically).
  - Risk for claudster: pool skills carry `context:`, `source:`, `license:`, `version:` keys.
    **Live-probe result: harmless.** The strict key validator belongs to codex's skill *installer*;
    the *loader* tolerates extra keys. But the file MUST start with `---` on line 1 — two pool skills
    wrapped in a stray ```` ```skill ```` fence were silently skipped until fixed (2026-07-21).
  - Skill metadata is truncated to a "skills context budget" — long descriptions get cut.

## Live validation (2026-07-21, offline half — `codex debug prompt-input` from a bundle-seeded repo)
`codex debug prompt-input` renders the exact model-visible prompt WITHOUT a model call (no auth needed) —
use it as the standard bundle smoke test. Results against the exported claudster bundle:
- AGENTS.md content injected verbatim (The Laws present).
- Skills roots resolved: `r0` = `<project>/.codex/skills` (our bundle), `r1/r2` = `~/.codex/skills`,
  `r3` = system skills. Nested `<category>/<name>/SKILL.md` layout IS discovered.
- **94/94 bundle skills visible** in the skills instructions block (after the fence fix; was 93/94).
- Remaining (blocked on re-login): one real `codex exec` executing a skill workflow end-to-end.
- **Config: project `.codex/config.toml` supported** (project must be trusted) layered under
  `~/.codex/config.toml`. `[[skills.config]]` blocks can disable individual skills by path.
- **Plugins/marketplaces** exist (`codex plugin add/list/marketplace`, `.agents/plugins/marketplace.json`,
  feature `plugins` stable) — a possible future distribution channel; out of scope for the bundle.
- **MCP:** `codex mcp add <name> -- <command>`, `[[mcp_servers]]` in config.toml — the Phase-5 junai-mcp
  seam. Features `apps`/`multi_agent`/`hooks` are stable in 0.137.

## Exit/parse guidance for wrappers
Prefer `-o <file>` for the final message (stdout `--json` is an event stream, not a single document).
Treat a missing/empty last-message file as failure (fail-closed).

## Version-churn warning
0.145.0 is already published; skills/plugins surface is under active development (many `under
development` feature flags). Re-run this probe (help + binary strings + one live smoke) before
trusting the contract on a new version.
