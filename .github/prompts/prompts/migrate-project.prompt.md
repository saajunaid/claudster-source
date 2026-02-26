---
description: "Migrate an existing project to use AI development resources (agents, skills, instructions, prompts)"
---

# Migrate Project Prompt

## Copy-Paste Template

```
Migrate my existing project at [PROJECT_PATH] to use the AI development framework.

Project details:
- Language/framework: [e.g., Python/Streamlit, Node.js/React]
- Has existing tests: [yes/no]
- Has Git repo: [yes/no]
- Current state: [working/partial/legacy]

I want a [minimal/full] migration:
- Minimal: Add AI resources (agents, instructions, skills, prompts) only
- Full: Add AI resources + documentation + IDE settings

After migration, analyze the codebase and suggest improvements.
```

## Purpose

Complete guide for migrating an existing project to the AI Agentic Development Framework. Use this when you have a project you want to integrate with AI development resources.

## When to Use

- You have an existing project without AI resources
- You want to add AI assistance to a legacy project
- You're onboarding a project into the framework

## Quick Migration Commands

### Minimal Migration (Add AI Resources Only)

```powershell
# Navigate to your project scripts folder
cd <path-to-project-scripts>

# Migrate your project
.\migrate-project.ps1 -ProjectPath "<path-to-your-project>"
```

### Full Migration (Add AI Resources + Docs + VS Code Settings)

```powershell
cd <path-to-project-scripts>
.\migrate-project.ps1 -ProjectPath "<path-to-your-project>" -Full
```

## What Gets Added

### Minimal Migration

| Resource | Count | Purpose |
|----------|-------|---------|
| `agents/` | 18 | AI personas for different tasks |
| `instructions/` | 13 | Coding guidelines by file type |
| `skills/` | 9 | Reusable AI capabilities |
| `prompts/` | 9 | Common prompt templates |
| `sync-ai-resources.ps1` | 1 | Update script |

### Full Migration (Additional)

| Resource | Purpose |
|----------|---------|
| `.vscode/settings.json` | VS Code configuration |
| `docs/developer-handbook.md` | AI resource usage guide |
| `docs/user-guide.md` | Project lifecycle guide |

## Migration Workflow

### Phase 1: Pre-Migration Assessment

Before migrating, understand your project:

```
Questions to answer:
1. Does the project have a requirements.txt or pyproject.toml?
2. Is there a src/ folder structure?
3. Are there existing tests?
4. Is there a Git repository?
5. What's the current state (working, partial, legacy)?
```

### Phase 2: Run Migration

```powershell
cd <path-to-project-scripts>
.\migrate-project.ps1 -ProjectPath "<path-to-your-project>" -Full
```

The script will:
1. Check if `` already exists
2. Copy all AI resources
3. Add sync script
4. Analyze project structure
5. Provide recommendations

### Phase 3: Post-Migration Analysis

After migration, use AI agents to analyze your code. In Cursor you can use @agent names; in other IDEs, paste the agent's instructions and then the prompt:

```
# Code quality review → Use Code Reviewer agent: "Analyze the codebase for quality issues and best practices"
# Architecture review → Use Architect agent: "Review the current architecture and suggest improvements"
# Security audit → Use Security Analyst agent: "Check for security vulnerabilities"
# Test coverage → Use Tester agent: "Identify areas lacking test coverage and generate tests"
# Documentation → Use a documentation-focused agent or skill to review and suggest improvements
```

### Phase 4: Optional Restructuring

If you want to align with project conventions:

```
Use the Project Manager agent: "Help me restructure this project to match project standards"
```

## Comparison: New vs Migrated Project

| Aspect | New Project | Migrated Project |
|--------|-------------|------------------|
| Structure | Framework standard | Existing (preserved) |
| AI Resources | ✅ Included | ✅ Added |
| Dependencies | requirements.txt template | Existing preserved |
| Configuration | .env.example template | Existing preserved |
| Boilerplate | app.py, config.py, etc. | None added |

## Post-Migration Checklist

After migration, verify:

- [ ] `` folder exists with all resources
- [ ] `sync-ai-resources.ps1` is in project root
- [ ] Your IDE has access to agents (Cursor: @agent names; others: load agent markdown as context)
- [ ] Instructions apply to relevant file types
- [ ] Project still runs normally

## Updating AI Resources

When the framework is updated, sync your project:

```powershell
cd <path-to-your-project>
.\sync-ai-resources.ps1
```

## Troubleshooting

### Agents Not Working After Migration

```powershell
# Verify AI resources folder exists (use your IDE's path, e.g. .cursor or .github)
Get-ChildItem .cursor -Name   # or: Get-ChildItem .github -Name

# If missing, re-run migration
cd <path-to-project-scripts>
.\migrate-project.ps1 -ProjectPath "<path-to-your-project>"
```

### Conflicts with Existing AI Resources Folder

The migration script will ask before overwriting. Options:

1. **Overwrite**: Replace existing with latest resources
2. **Cancel**: Keep existing, manually merge
3. **Backup first**: 
   ```powershell
   Rename-Item .cursor .cursor-backup   # or your IDE's folder name
   # Then run migration
   ```

### Project Structure Recommendations

If you want to restructure (optional):

```
Recommended structure:
├──          # AI resources (added by migration)
├── .vscode/           # VS Code settings
├── docs/
│   ├── prd/prd.md     # Product requirements
│   └── *.md           # Other documentation
├── src/
│   ├── app.py         # Entry point
│   ├── config.py      # Configuration
│   ├── models/        # Data models
│   ├── services/      # Business logic
│   └── utils/         # Utilities
├── tests/
├── data/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Related Resources

| Resource | Purpose |
|----------|---------|
| `@project-manager` | Interactive migration guidance |
| `/project-setup` | New project creation guide |
| `developer-handbook.md` | Complete AI resource reference |
| `user-guide.md` | Full project lifecycle |
