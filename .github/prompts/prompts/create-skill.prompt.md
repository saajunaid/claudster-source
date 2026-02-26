---
description: "Create a new AI skill (SKILL.md) from scratch or by analyzing repository patterns"
mode: agent
tools: ['codebase', 'editFiles', 'search', 'runCommands']
---

# /create-skill - Create a New Skill

Create or generate a SKILL.md file that teaches the AI agent specialized knowledge, workflows, or tool integrations.

## Input

User's request: `{{input}}`

If `{{input}}` is empty, ask: "What capability should this skill add? Or should I analyze the repo to discover patterns?"

---

## Option A: Create from Description

When the user describes what the skill should do:

1. **Clarify** the skill's purpose, triggers, and target workflows
2. **Read** the skill creator guide at `skills/workflow/skill-creator/SKILL.md` for format and best practices
3. **Create** the skill following the structure below

---

## Option B: Generate from Repository Analysis

When the user wants to extract patterns from the codebase:

### Step 1: Gather Data

```bash
# Recent commits with file changes
git log --oneline -n 200 --name-only --pretty=format:"%H|%s|%ad" --date=short

# Most frequently changed files
git log --oneline -n 200 --name-only | sort | uniq -c | sort -rn | head -20

# Commit message patterns
git log --oneline -n 200 | head -50
```

### Step 2: Detect Patterns

| Pattern Type | What to Look For |
|-------------|-----------------|
| **Commit conventions** | Consistent prefixes (feat:, fix:, chore:) |
| **File co-changes** | Files that always change together |
| **Workflow sequences** | Repeated multi-file change patterns |
| **Architecture** | Folder structure and naming conventions |
| **Testing patterns** | Test locations, naming, framework |

### Step 3: Generate SKILL.md

Create the skill from detected patterns.

---

## Skill Structure

```
skills/{category}/{skill-name}/
├── SKILL.md          (required)
├── scripts/          (optional - executable code)
├── references/       (optional - docs the agent reads)
└── templates/        (optional - starter files)
```

### SKILL.md Format

```markdown
---
name: {skill-name}
description: "{What it does}. Use when {triggers/scenarios}."
category: {coding|testing|workflow|docs}
---

# {Skill Name}

{Brief overview of what this skill provides.}

## When to Use

- {Trigger scenario 1}
- {Trigger scenario 2}

## Prerequisites

- {Required tools or setup}

## Workflows

### {Workflow 1 Name}

1. {Step 1}
2. {Step 2}
3. {Step 3}

## Guidelines

- {Guideline 1}
- {Guideline 2}

## Troubleshooting

| Issue | Solution |
|-------|----------|
| {Problem} | {Fix} |
```

---

## Quality Checklist

- [ ] `name` field matches folder name (lowercase, hyphens only)
- [ ] `description` explains WHAT it does AND WHEN to use it (keyword-rich)
- [ ] Body content is under 500 lines
- [ ] Instructions are for the AI agent, not for humans
- [ ] No content the AI already knows (only add what's project-specific)
- [ ] All referenced scripts are tested and runnable

---

## Quick Reference

```
/create-skill                     ← Interactive skill creation
/create-skill api-patterns        ← Create skill for API patterns
/create-skill --from-repo         ← Analyze repo and generate skill
```

**Full skill creation guide**: `skills/workflow/skill-creator/SKILL.md`
