---
description: "Run the golden-nuggets knowledge-capture workflow by loading the authoritative workflow skill"
mode: agent
tools: ['codebase', 'editFiles', 'search']
---

# /golden-nuggets

Load `.github/skills/workflow/golden-nuggets/SKILL.md` first and follow it as the source of truth.

## What to do

1. Detect whether this is pipeline, independent, or CI-capture context.
2. Follow the skill's extraction, routing, write, and verification rules exactly.
3. Treat live instruction, runbook, or managed hub updates as the primary output outside CI mode.
4. Write the session log only after live writes are verified.
5. In CI-capture mode, write only `.github/agent-docs/nuggets-inbox.md`, then rely on `junai pool nuggets review --project <path>` for later human triage.

## Rules

- Do not duplicate the skill rules in this prompt.
- Do not let CI capture mode write live instruction files.
- Do not auto-promote raw candidates from the inbox.
- Preserve independent `/golden-nuggets` usage by treating this prompt as a thin wrapper around the skill.
