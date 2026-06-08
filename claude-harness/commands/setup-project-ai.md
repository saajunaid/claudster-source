---
description: Install or refresh the Claude Code dev harness in this project (CLAUDE.md hierarchy, subagents, commands, settings, AGENTS.md)
argument-hint: [--force] [project description]
---

# /setup-project-ai — install the harness

Set up (or refresh) the agent-agnostic development harness for this project. Follow the
`setup-project-ai` skill end-to-end: run the deterministic generator, resolve any reported
placeholders, enrich the generated CLAUDE.md hierarchy with project-specific facts, ensure the test
env, and smoke-test.

Context / args: **$ARGUMENTS**

Load and follow `.github/skills/workflow/setup-project-ai/SKILL.md`. Do not hand-roll the steps —
the deterministic parts must go through `scripts/setup_project_ai.py` so they don't vary.
