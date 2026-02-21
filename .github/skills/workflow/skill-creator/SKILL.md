---
name: skill-creator
description: Guide for creating effective skills. Use when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
source: anthropics/skills
license: Apache-2.0
---

# Skill Creator

Skills are modular packages that extend Claude's capabilities by providing specialized knowledge, workflows, and tools.

## Core Principles

### Concise is Key
The context window is a shared resource. Only add context Claude doesn't already have. Challenge each piece: "Does Claude really need this?"

### Anatomy of a Skill

```
skill-name/
â”œâ”€â”€ SKILL.md (required)
â”‚   â”œâ”€â”€ YAML frontmatter (name, description)
â”‚   â””â”€â”€ Markdown instructions
â””â”€â”€ Bundled Resources (optional)
    â”œâ”€â”€ scripts/      - Executable code
    â”œâ”€â”€ references/   - Documentation
    â””â”€â”€ assets/       - Templates, images
```

### SKILL.md Format

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Instructions for Claude when this skill is active]

## Examples
- Example usage 1
- Example usage 2

## Guidelines
- Guideline 1
- Guideline 2
```

### Frontmatter Field Requirements

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | **Yes** | 1-64 chars, lowercase letters/numbers/hyphens only, must match folder name |
| `description` | **Yes** | 1-1024 chars, must describe WHAT it does AND WHEN to use it |
| `category` | No | Organizational grouping (coding, testing, workflow, docs) |
| `license` | No | License name or reference to bundled LICENSE.txt |
| `source` | No | Attribution for adapted skills |

### Description Best Practices

**CRITICAL**: The `description` is the PRIMARY mechanism for automatic skill discovery. Include:

1. **WHAT** the skill does (capabilities)
2. **WHEN** to use it (triggers, scenarios, keywords)
3. **Keywords** users might mention in prompts

```yaml
# ✅ GOOD: Keyword-rich, explains WHAT and WHEN
description: 'Toolkit for testing local web applications using Playwright. Use when asked to verify frontend functionality, debug UI behavior, capture browser screenshots, or view browser console logs.'

# ❌ BAD: Too vague for discovery
description: 'Web testing helpers'
```

### Recommended Body Sections

| Section | Purpose |
|---------|---------|
| `# Title` | Brief overview |
| `## When to Use` | Reinforces description triggers |
| `## Prerequisites` | Required tools, dependencies |
| `## Step-by-Step Workflows` | Numbered steps for tasks |
| `## Troubleshooting` | Common issues and solutions |
| `## References` | Links to bundled docs |

## Skill Creation Process

### Step 1: Understand with Examples
Gather concrete examples of how the skill will be used. Ask:
- "What functionality should this skill support?"
- "What would a user say that should trigger this skill?"

### Step 2: Plan Reusable Contents
Analyze examples to identify:
- **Scripts**: Code that gets rewritten repeatedly
- **References**: Documentation Claude needs to reference
- **Assets**: Templates, images for output

### Step 3: Initialize
Create the skill directory structure with SKILL.md and resource folders.

**Optional resource directories:**

| Folder | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/` | Executable code (Python, Bash, JS) | Automation that performs operations |
| `references/` | Documentation agent reads | API references, schemas, guides |
| `assets/` | Static files used AS-IS | Images, fonts, templates |
| `templates/` | Starter code agent modifies | Scaffolds to extend |

### Step 4: Implement
- Start with reusable resources (scripts, references, assets)
- Write clear SKILL.md with proper frontmatter
- Test scripts by actually running them

### Step 5: Iterate
Use the skill on real tasks, notice struggles, improve.

## Progressive Disclosure

Keep SKILL.md under 500 lines. Split content:

```markdown
# PDF Processing

## Quick start
[code example]

## Advanced features
- **Form filling**: See [FORMS.md](FORMS.md)
- **API reference**: See [REFERENCE.md](REFERENCE.md)
```

## What NOT to Include

- README.md
- INSTALLATION_GUIDE.md
- CHANGELOG.md
- User-facing documentation

Skills are for AI agents, not humans.

## Validation Checklist

- [ ] Folder name is lowercase with hyphens
- [ ] `name` field matches folder name exactly
- [ ] `description` is 10-1024 characters, explains WHAT and WHEN
- [ ] Body content is under 500 lines
- [ ] Bundled assets are under 5MB each
- [ ] All scripts are tested and runnable

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Skill not discovered | Improve description with more keywords and triggers |
| Name validation fails | Ensure lowercase, no consecutive hyphens, matches folder |
| Description too short | Add capabilities, triggers, and keywords |
| Assets not found | Use relative paths from skill root |
