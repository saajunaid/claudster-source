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

## After the deterministic step — deploy vmie skills

If the harness source (`claude-harness/skills/vmie/`) exists in agent-sandbox, also copy the
vmie skill set into `.github/skills/vmie/` in this project so deploy-local, golden-workflow,
and windows-deployment are available locally:

```powershell
$harness = "e:\Projects\agent-sandbox\claude-harness\skills\vmie"
$dest = ".github\skills\vmie"
if (Test-Path $harness) {
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item "$harness\*" $dest -Recurse -Force
    Write-Host "vmie skills deployed to $dest"
}
```

Do not commit the vmie skills to the project repo — they are private harness resources.
