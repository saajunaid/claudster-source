# Porting claudster to a new coding harness — the repeatable recipe

claudster is one canonical toolbox (`.github/` source) with per-harness export shapes
(`.github/runtime-targets.json`, built by `export_runtime_resources.py`). Adding a harness is **not a
project — it is this 5-step loop**, done twice already (codex, antigravity). Budget: hours, not days.

## The mental model (read once)
The toolbox has two layers that port very differently:
- **Knowledge layer** — skills, instructions, prompts, agent briefs. Plain markdown → ships to EVERY
  harness. This is ~90% of the value.
- **Execution layer** — hooks, slash commands, subagents. Claude Code native. Do NOT reimplement it per
  harness; the only portable execution surface is **MCP** (opt-in, later).

Never fork the toolbox. One source, many export shapes.

## The 5-step loop

### 1. Probe the discovery contract — never trust memory or docs alone
Question to answer: *where does this harness look for (a) project memory/conventions, (b) skills, and in
what format, (c) MCP config?* Harness loading paths churn per-version — probe the INSTALLED product:
- CLI harness: `<tool> --help` on every relevant subcommand; then extract literal path strings from the
  binary: `grep -aoE '[ -~]{0,60}skills[ -~]{0,40}' <binary>` (same for `AGENTS.md`, `SKILL.md`,
  frontmatter error messages).
- IDE harness (VS Code forks): grep the workbench bundle —
  `resources/app/out/vs/workbench/workbench.desktop.main.js` — for the same strings.
- Start from the AGENTS.md assumption (it is the de-facto cross-harness convention) but **verify it**.

Record verbatim findings in `docs/analysis/<harness>-contract.md` with the probed version number.
Worked examples: `codex-cli-contract.md`, `antigravity-contract.md`.

### 2. Add an export target to `.github/runtime-targets.json`
Copy the closest existing target and adjust destinations to the probed paths. Available knobs:
`workspace_root`, `files` (single files, e.g. the AGENTS.md template from
`claude-harness/claude-md/agents.md.tmpl`), `copies` with `included_skills` rosters,
`flatten_skills: true` when the harness wants a flat `<name>/SKILL.md` layout (antigravity), nested
category layout otherwise (codex). The exporter is fail-closed: a roster naming a nonexistent skill
fails the build — that is a feature.

### 3. Export and shape-check offline
`python export_runtime_resources.py --profile <harness> --report` → errors must be none. Then verify the
layout matches the probed contract mechanically (count `SKILL.md` files at the expected depth; confirm
the memory file landed at the probed filename).

### 4. Live-validate with the cheapest real probe the harness offers
- codex: `codex debug prompt-input` from a bundle-seeded repo renders the exact model-visible prompt
  with NO model call and NO auth — assert the memory content and the skill roster appear in it. Then
  (with auth) one real `codex exec` executing a skill workflow.
- IDE harnesses: open a bundle-seeded workspace and ask the agent what conventions/skills it sees
  (human step — record the result in the contract doc).
- If a probe contradicts step 1, fix the target AND the contract doc, re-export, re-probe.

### 5. Record and close the loop
Update the contract doc's "Validation state", flip the plan row, commit
(`feat(export): <harness> target — probed and validated`). Distribution to real projects is
`claudster-init --target <harness>` (see `scripts/claudster_init.py`).

## Known harness map (as probed — re-verify on version bumps)

| Harness | Memory file | Skills path + shape | Probed |
|---|---|---|---|
| Claude Code | CLAUDE.md | plugin marketplace (or project `.claude/skills/`, flat) | production reference |
| GitHub Copilot | copilot-instructions.md | `.github/skills/` nested | production reference |
| Codex CLI 0.137 | AGENTS.md (CLAUDE.md fallback) | `.codex/skills/` nested OK | 2026-07-21 |
| Antigravity 1.107 | AGENTS.md (workspace-wide) | `.claude/skills/` **flat** | 2026-07-21 |
| opencode / others | AGENTS.md (convention) | **unprobed — run this loop** | — |

Note the convergence: AGENTS.md + Claude-format SKILL.md are becoming the interop surface — Antigravity
literally reads `.claude/skills/`. Expect (but verify) new harnesses to follow.

## The over-complication traps (do not)
- No per-harness forks of skill content — fix the pool, re-export.
- No reimplementing hooks/subagents outside Claude Code.
- No bespoke integration projects for harness #3+ — if this loop doesn't cover it, extend THIS doc.
