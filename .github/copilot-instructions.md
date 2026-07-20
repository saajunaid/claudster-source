# Project Instructions

> This file is yours. The tooling manages only the `junai:start` … `junai:end` section
> below; everything else is never read, modified, or deleted automatically.
>
> System documentation (agents, pipeline flow, MCP tools, routing conventions) is
> automatically provided by `.github/instructions/junai-system.instructions.md`.

---

## Project Overview

**claudster-source** is the authoring and source-of-truth repository for the **claudster** harness — the
agent definitions, skills, prompts, hooks, and tooling that ship as a Claude Code plugin (and are exported
to other AI CLIs). Everything under `.github/` is the **canonical source**; runtime-specific resources for
Claude, Copilot, Codex, and the subset lanes are generated from it during packaging.

```
claudster-source/
├── .github/
│   ├── agents/              ← agent definition files (*.agent.md)
│   ├── skills/              ← reusable skill bundles (domain knowledge packs)
│   ├── prompts/             ← reusable prompt files
│   ├── instructions/        ← coding convention files (*.instructions.md)
│   ├── tools/               ← pool tooling (pool-sync, pool-validator, oss_review.py, …)
│   ├── agent-docs/          ← pipeline schema docs, runbooks, artefact templates
│   ├── recipes/             ← delivery recipes
│   ├── diagrams/            ← architecture and workflow reference diagrams
│   └── runtime-targets.json ← export contract (which resources go to which runtime)
├── claude-harness/          ← the plugin's commands, hooks, subagents, and scripts
├── validate_agents.py       ← pre-publish gate: agent frontmatter + MCP smoke test
├── validate_pool.py         ← pre-publish gate: registry, gates, privacy scan, prompts, skill drift
├── export_runtime_resources.py ← builds dist/runtime-resources/ exports from canonical `.github/`
└── sync.ps1                 ← junai-pull / junai-push sync + publish functions
```

> **claudster-source has a git origin remote.** Commit and push here as normal. The distributable pool is
> then synced to its marketplace mirror by `sync.ps1`'s `junai-push` (a separate remote — see below).

---

## Distribution

The canonical `.github/` pool is exported and distributed to several lanes (paths are per-machine; resolve
them from your own checkout, never hardcode a personal path):

- **claude / claude-extras** — the Claude Code plugin pair (core always-on + the long-tail skill library).
- **codex / copilot** — exports for other AI CLIs (`AGENTS.md` mirrors `CLAUDE.md`).
- **subset lanes** (e.g. ptarmigan, liffey) — trimmed pool profiles, some marketplace-published, some
  internal VSIX-only.

`export_runtime_resources.py` reads `.github/runtime-targets.json` and emits build artefacts under
`dist/runtime-resources/`. **Treat `dist/` as generated output, not source of truth.**

---

## Team / Project Conventions

**Pre-publish gate:** always run the validators before publishing.
- `validate_agents.py` — agent frontmatter (required sections, Partial Completion Protocol) + MCP smoke test.
- `validate_pool.py` — registry/transition consistency, gate consistency, **privacy scan**, prompt
  frontmatter, skill-registry drift, golden-plan structure. Default scope is `.github/`; add `--include-dist`
  after an export to audit the built bundles, and `--include-external` to audit the mirrors.

**Publish workflow (from claudster-source):**
```powershell
# 1. Validate + test
python validate_pool.py
python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q --import-mode=importlib

# 2. Commit source (has a remote — push as normal)
git add .github/ claude-harness/; git commit -m "feat: ..."; git push

# 3. Sync the pool to its mirror (bumps the plugin version; NO marketplace publish by default)
. .\sync.ps1
junai-push               # mirror sync only
junai-push -Publish      # also publish MCP (PyPI) + VS Code extension — deliberate, content-diff gated
```

**Privacy is a publish gate, not an afterthought:** the pool ships publicly, so no internal hosts,
credentials, org identifiers, or personal filesystem paths belong in `.github/`. `validate_pool.py`'s
privacy scan enforces this; add new internal markers to its denylist rather than allowlisting a real leak.

## Institutional Knowledge

- Canonical-source rule: author AI resources only in `.github/` (and `claude-harness/`); treat exports under
  `dist/` and the runtime mirrors as generated targets, never hand-edited sources.
- Agent file naming: lowercase kebab-case matching the `name` frontmatter field exactly.
- `validate_agents.py` `KNOWN_MODELS` allowlist must be updated whenever a new model is introduced.

Apply the fidelity rules below whenever a task produces a **large, structured, multi-phase output** —
specifically: 4+ phases in a session, 50+ expected output lines, or multiple reference docs as constraints.

**Rule 1 — Pre-Flight Scan:** Before writing any task line, produce a `Phase N — [Name]: ~N tasks expected`
summary for ALL phases first. Do not start the main output until the pre-flight is complete.

**Rule 2 — Named Output File:** Write deliverables to a named file. Include `OUTPUT DESTINATION: <relative
path>` in the prompt. Chat output is secondary.

**Rule 3 — Path Gate:** Before writing any `CREATE`/`UPDATE`/`CONFIGURE` line, verify the file path exists in
the project directory spec. If not found: write `NOTE — [path] not found in directory spec, confirm before
creating`.

**Rule 4 — No Abbreviation:** Never use "similar to Phase X", "as above", "same pattern", "follow approach in
Phase N", "etc." in task descriptions. Every task line must be written in full.

**Rule 5 — Phase Boundary Re-Anchor:** After completing each phase section, re-read the fidelity constraints
before starting the next phase.

**Rule 6 — Equal Depth:** Late phases (final 2–3) must have the same number of task lines as their deliverable
count warrants. Do not summarise late phases.

**Rule 7 — Open Question Flagging:** Flag tasks blocked by open questions with `[OQ-N BLOCKER]` inline. Do not
silently skip or assume resolution.

**Rule 8 — Post-Generation Self-Sweep (Mandatory):** After completing any large structured output, scan the
last 40% for decay signals: `...`, `same pattern`, `as above`, `{ ... }`, `similar to Phase N`, `repeat for`,
`and N more`. Expand every match in-place before delivering.

<!-- junai:start -->

## Agent Pipeline

> System documentation (agents, pipeline flow, MCP tools, routing conventions) is automatically provided by
> `.github/instructions/junai-system.instructions.md`.
>
> Project-specific config: `.github/project-config.md` | Pipeline state: `.github/pipeline-state.json`
>
> Start with `@Orchestrator` in Copilot Chat.

## Recipe-Driven Delivery

When working on **data-to-UI tasks** (new features, dashboards, data integrations — not bug fixes, refactors,
or docs-only work):

1. Read `.github/project-config.md` — check if a `recipe` field is set in Step 1
2. If set, read `.github/recipes/{recipe}.recipe.md`
3. Follow the recipe's **Delivery Pipeline** as your mandatory phase sequence
4. Load the recipe's **Mandatory Skills** for each phase you work on
5. Apply the recipe's **Cross-Skill Conventions** (naming chains, directory structure, chart styling)

If no recipe is set, work normally using your built-in expertise and any skills loaded via other mechanisms.

<!-- junai:end -->
