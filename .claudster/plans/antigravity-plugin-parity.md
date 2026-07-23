---
type: plan
status: draft
feature: antigravity-plugin-parity
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-23T00:00:00Z
Creating Model: claude-fable-5
---

# Antigravity plugin parity — same claudster experience in agy as in Claude Code

## Goal
One claudster, two first-class homes. In Antigravity (`agy`) that means: install once at user
level, update centrally (like the Claude Code marketplace), same rules hierarchy, same skills,
and the portable slice of hooks/commands/agents — all packaged from the SAME canonical source by
the SAME exporter. No fork, ever.

## Context (probed facts — cite, don't re-derive)
- `docs/analysis/antigravity-contract.md` — agy v1.1.5 contract + headless gotchas (LIVE-validated
  2026-07-23: AGENTS.md + `.agents/skills/` + skill execution all work via the bundle).
- agy HAS a plugin system: `agy plugin install <plugin@marketplace> | validate | link | import`,
  manifests are `plugin.json` (+ `import_manifest.json` internally), marketplaces at
  `.agents/plugins/marketplace.json`. Binary contains NO `.claude/` paths — `plugin import claude`
  targets something else (probably Claude Desktop extensions); found nothing on this box.
- agy also has: hooks (`~/.agents/hooks/hooks.json` + `scripts/` exist on this box — a live
  example to read), custom agents (`agy agents` — empty list today), `--agent`, MCP via
  `~/.gemini/config/mcp_config.json`, settings at `~/.gemini/antigravity-cli/settings.json`.
- Claude Code `CLAUDE.md` supports `@path` imports — the mechanism for single-sourcing rules.
- Non-portable by nature (accept, don't chase): Claude Code statusline, permission modes,
  slash-command UX. agy's TUI has its own equivalents.

## Phases

### Phase 0 — Single-source the rules: AGENTS.md canonical, CLAUDE.md = shim
**Goal:** repo + subfolder rules written ONCE, read natively by both harnesses.
**Design:** `AGENTS.md` holds the content (root and subfolders); each sibling `CLAUDE.md` becomes
`@AGENTS.md` + optional Claude-only addenda. NO symlinks (Windows privilege + git fragility).
**Touches:** `scripts/setup_project_ai.py` + `claude-harness/claude-md/root.md.tmpl` (+ area
fragments): generate the AGENTS.md/CLAUDE.md-shim pair instead of CLAUDE.md-only; migration mode
for existing repos (`--migrate-rules`: move CLAUDE.md content → AGENTS.md, leave shim; refuse on
conflict). TDD.
**Exit gate:** in a scratch repo: Claude Code resolves the shim (probe: ask what the Laws are);
`agy -p --new-project` reads root AND one subfolder AGENTS.md. Existing-repo migration tested on a
copy of docket (not committed there).
**Commit:** `feat(setup): AGENTS.md-canonical rules with CLAUDE.md @import shims`

### Phase 1 — Probe the agy plugin + hooks + agents contract
**Goal:** pin `plugin.json` schema, marketplace.json format, hooks.json schema, custom-agent format.
**Method (per the porting guide — probe, never assume):**
- Read the LIVE example on this box: `~/.agents/hooks/hooks.json` + `scripts/`.
- Scaffold a minimal plugin and iterate against `agy plugin validate <path>` until green — the
  validator IS the schema oracle. Binary strings + official docs (antigravity.google/docs/cli) fill gaps.
- Probe `agy plugin link <mp> <target>` and `.agents/plugins/marketplace.json` shape.
- Probe custom agents: where agent definitions live so `agy agents` lists them; map 2-3 claudster
  agent briefs (code-reviewer, preflight) as candidates.
**Exit gate:** `docs/analysis/antigravity-plugin-contract.md` with verbatim schemas + a hello-world
plugin that installs, lists, enables, and its skill fires in a session.
**Commit:** `docs(analysis): agy plugin/hooks/agents contract — probed`

### Phase 2 — Exporter target `antigravity-plugin`
**Goal:** package claudster (skills + rules templates + mapped extras) in agy plugin layout with a
generated `plugin.json`, from the same pool. Reuse the bundle roster; version from the claudster
manifest (same bump flow).
**Exit gate:** `agy plugin validate dist/runtime-resources/antigravity-plugin` green; local
`agy plugin install` → skills fire in a scratch session; `validate_pool` extended to lint the new
bundle. Full suite green.
**Commit:** `feat(export): antigravity-plugin target — claudster as an agy plugin`

### Phase 3 — Distribution + updates (the "user-level once" experience)
**Goal:** install once, update centrally — parity with the Claude marketplace.
**Implement:** publish the plugin bundle + a `marketplace.json` into the junai GitHub repo (extend
`sync.ps1` junai-push — ALSO close the deferred `bundles/<target>/` publish from the
toolbox-portability plan here, one wiring pass); document `agy plugin install claudster@<marketplace>`
+ update flow in README "Installing outside Claude Code".
**Exit gate:** on this box, install claudster into agy FROM GitHub, run a skill; `claudster-init`
GitHub mode also works now (bundles published). Leak-free `git grep` gate before the mirror push.
**Commit:** `feat(dist): claudster agy plugin published — install-once from GitHub`

### Phase 4 — Deeper parity: hooks, agents, MCP
**Goal:** port the portable execution-layer slice.
- Map SessionStart-relay + guard-style hooks onto agy's hooks.json semantics where equivalents
  exist (probed in Phase 1); skip what has no equivalent — record a parity table in the guide.
- Ship 2-3 claudster agents as agy custom agents if Phase 1 proved the format.
- junai-mcp into `~/.gemini/config/mcp_config.json` (+ codex `[[mcp_servers]]`) — this absorbs
  toolbox-portability Phase 5.
**Exit gate:** parity table in `docs/guide/porting-to-a-harness.md`; one hook + one agent + one MCP
tool demonstrably working in agy.
**Commit:** `feat(agy): hooks/agents/MCP parity slice`

## Non-goals
- No second claudster codebase; no hand-maintained agy copies of skills.
- No chasing statusline/permission-mode/slash-UX parity — harness-native, accept difference.
- No dependence on `agy plugin import claude` (targets something else; our exporter is the bridge).

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\antigravity-plugin-parity.md fully, then execute
autonomously in E:\Projects\claudster-source. Probe-first discipline: every agy format claim comes
from agy plugin validate / live files / binary strings — never memory; cite
docs/analysis/antigravity-contract.md gotchas (--new-project, permission auto-deny, no --sandbox).
TDD for all code; full suite (python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q
--import-mode=importlib) + python validate_pool.py per phase; commit per phase; update this plan's
phases with ✅ + hash. Phase 3's mirror push needs the leak-free git grep gate. agy is authenticated
on this box; if a live agy step fails on auth, mark blocked-on-human and continue.
```
