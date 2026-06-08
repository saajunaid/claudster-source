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

Load and follow the `setup-project-ai` skill. Do not hand-roll the steps — the deterministic parts
must go through the bundled generator so they don't vary. Resolve its path per the skill's Step 1:
- Plugin install: `${CLAUDE_PLUGIN_ROOT}/scripts/setup_project_ai.py`
- agent-sandbox checkout: `scripts/setup_project_ai.py`

## After the deterministic step — deploy vmie skills (optional, personal)

`vmie` skills (deploy-local, golden-workflow, windows-deployment) are **private** and are not shipped
in the public plugin. This step is for a local harness author who keeps a vmie source on disk; it is a
no-op for everyone else. Point `CLAUDSTER_HARNESS_SRC` at your harness root (the folder containing
`skills/vmie/`) and run:

```powershell
$src = if ($env:CLAUDSTER_HARNESS_SRC) { Join-Path $env:CLAUDSTER_HARNESS_SRC "skills\vmie" } else { $null }
$dest = ".github\skills\vmie"
if ($src -and (Test-Path $src)) {
    New-Item -ItemType Directory -Force $dest | Out-Null
    Copy-Item "$src\*" $dest -Recurse -Force
    Write-Host "vmie skills deployed to $dest"
} else {
    Write-Host "vmie source not found (set CLAUDSTER_HARNESS_SRC) — skipping; public installs have no vmie."
}
```

Do not commit the vmie skills to the project repo — they are private harness resources.
