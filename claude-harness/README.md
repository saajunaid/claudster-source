# claude-harness — canonical Claude Code / agent-agnostic harness

Source of truth for the Claude Code development harness. The `setup-project-ai` generator
(`scripts/setup_project_ai.py` + `setup-project-ai` skill) deploys and customizes these into any
project, producing a working, TDD-first, context-rot-resistant dev environment.

Proven end-to-end in the Phase 0 spike (`E:\Projects\_harness-spike`); see that repo's
`.github/agent-docs/PHASE-0-LEARNINGS.md`.

## Layout
```
claude-harness/
├── agents/            lean subagents (own context, report back) — deployed to .claude/agents/
│   ├── tester.md
│   ├── code-reviewer.md
│   └── preflight.md
├── commands/          slash commands — deployed to .claude/commands/
│   ├── feature-plan.md
│   ├── tdd.md
│   ├── prd.md
│   ├── handoff.md
│   └── relay.md
├── claude-md/         CLAUDE.md fragment library — composed into the project's CLAUDE.md hierarchy
│   ├── root.md.tmpl       universal root (identity placeholders + harness + laws)
│   ├── agents.md.tmpl     AGENTS.md mirror (Codex / agent-agnostic)
│   ├── backend-python.md  → src/CLAUDE.md   (when Python backend detected)
│   ├── backend-fastapi.md → appended to src/CLAUDE.md (when FastAPI detected)
│   ├── frontend-react.md  → frontend/CLAUDE.md (when React/Vite detected)
│   └── tests-pytest.md    → tests/CLAUDE.md  (when pytest detected)
├── settings.template.json base .claude/settings.json
└── stack-map.json         stack-detection signals → which fragments/commands/subagents apply
```

## Design rules (learned in Phase 0)
- **Deterministic vs generative split.** Mechanical steps (placeholder substitution, venv/deps,
  frontend test harness, file deploy) are pure Python — they must not vary. CLAUDE.md *curation*
  (enriching fragments with project-specific facts from STACK.md/code) is the skill's AI step.
- **Idempotent.** Re-running never destroys user edits: existing CLAUDE.md/settings are merged or
  left, harness files are refreshed only with `--force`.
- **Agent-agnostic core.** CLAUDE.md ↔ AGENTS.md are mirrors; subagents/commands/skills are plain
  markdown Codex can also read.
