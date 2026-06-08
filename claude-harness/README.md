# claude-harness — canonical Claude Code / agent-agnostic harness

Source of truth for the Claude Code development harness. The `setup-project-ai` generator
(`scripts/setup_project_ai.py` + `setup-project-ai` skill) deploys and customizes these into any
project, producing a working, TDD-first, context-rot-resistant dev environment.

Proven end-to-end in the Phase 0 spike (`E:\Projects\_harness-spike`); see that repo's
`.github/agent-docs/PHASE-0-LEARNINGS.md`.

## Layout
```
claude-harness/
├── agents/            10 lean subagents (own context, report back) — deployed to .claude/agents/
│   ├── tester.md · code-reviewer.md · preflight.md          (Phase 0 trio)
│   ├── security-analyst.md · codebase-audit.md · debug.md   (Phase 2)
│   ├── anchor.md · knowledge-transfer.md                    (Phase 2)
│   └── data-engineer.md · sql-expert.md                     (Phase 2)
├── commands/          slash commands — deployed to .claude/commands/
│   ├── feature-plan.md · tdd.md · prd.md · handoff.md · setup-project-ai.md
├── claude-md/         CLAUDE.md fragment library — composed into the project's CLAUDE.md hierarchy
│   ├── root.md.tmpl       universal root (identity placeholders + harness + laws)
│   ├── agents.md.tmpl     AGENTS.md mirror (Codex / agent-agnostic)
│   ├── backend-python.md  → src/CLAUDE.md   (when Python backend detected)
│   ├── backend-fastapi.md → appended to src/CLAUDE.md (when FastAPI detected)
│   ├── frontend-react.md  → frontend/CLAUDE.md (when React/Vite detected)
│   └── tests-pytest.md    → tests/CLAUDE.md  (when pytest detected)
├── settings.template.json base .claude/settings.json
├── model-aliases.json     logical model tier → concrete model (portability seam — see below)
└── stack-map.json         stack-detection signals → which fragments/commands/subagents apply
```

## Skills: two-plugin tiering (lean context)
Claude Code loads every enabled plugin's skill descriptions into **every** session, so a large flat
skill set is a standing context tax. claudster splits skills across two plugins in one marketplace:

- **`claudster`** (this plugin) — agents, commands, loop hooks, and a **core** set (~38) of
  high-frequency dev skills. Always enabled; modest always-on cost.
- **`claudster-extras`** — the **long tail** (cloud, data, the rest of frontend/coding, media,
  productivity). **Disabled by default**; enable only when you need it:
  ```
  claude plugin install claudster-extras@claudster   # one-time
  claude plugin enable  claudster-extras             # when you need the breadth
  claude plugin disable claudster-extras             # back to lean
  ```
  While disabled it costs **zero** always-on context. (Plugin skills must live flat at
  `skills/<name>/SKILL.md` to be discovered — the build flattens the pool's category layout.)

Office skills (`pdf`/`docx`/`pptx`/`xlsx`) are Anthropic's proprietary document-skills and are **not**
shipped here — install Anthropic's document-skills (or keep them in `~/.claude/skills/`).

## Running on local / non-Anthropic models (portability seam)
The harness is **model-portable by design** — it's markdown interpreted by a CLI, not code bound to a
provider. The one Anthropic-specific detail is each subagent's `model: opus|sonnet|haiku` frontmatter.
Treat that as a **logical tier**, resolved through `model-aliases.json`, not a hard model ID.

To run under a gateway (the local-LLM fallback path):
1. Stand up a **LiteLLM** proxy in front of your models (local GPU via Ollama/vLLM, or any provider).
2. Point Claude Code at it: `ANTHROPIC_BASE_URL=<proxy>`, `ANTHROPIC_AUTH_TOKEN=<gateway/virtual key>`,
   optionally `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` to populate the model picker. (Codex uses
   the equivalent OpenAI base-URL seam.)
3. Override the tiers in `model-aliases.json` — e.g. keep `opus` remote for planning/verification, map
   `sonnet`/`haiku` to a **local coder model** (`local_fallback_example` shows the planner=remote /
   coder=local split). This is the intended future shape: Opus plans, a local model codes.

Caveats (don't hide them): a gateway is a server someone must run — subscription users gain nothing from
it and should leave it off (default). Claude Code sends `anthropic-beta` headers some non-Anthropic
backends reject (400). Keep the seam **optional, default-off**, same posture as the pipeline MCP.

## Design rules (learned in Phase 0)
- **Deterministic vs generative split.** Mechanical steps (placeholder substitution, venv/deps,
  frontend test harness, file deploy) are pure Python — they must not vary. CLAUDE.md *curation*
  (enriching fragments with project-specific facts from STACK.md/code) is the skill's AI step.
- **Idempotent.** Re-running never destroys user edits: existing CLAUDE.md/settings are merged or
  left, harness files are refreshed only with `--force`.
- **Agent-agnostic core.** CLAUDE.md ↔ AGENTS.md are mirrors; subagents/commands/skills are plain
  markdown Codex can also read.
