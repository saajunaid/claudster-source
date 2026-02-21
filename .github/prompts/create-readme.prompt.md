---
description: "Generate a comprehensive, well-structured README.md for a project"
mode: agent
tools: ['codebase', 'editFiles', 'search', 'fetch']
---

# /create-readme - Generate Project README

**You must review the project and create a README.md immediately.**

## Input

User's request: `{{input}}`

If `{{input}}` is empty, scan the workspace to infer project details automatically.

---

## Step 1: Review the Project

Before writing, understand the project thoroughly:

1. **Read key files**: `package.json`, `pyproject.toml`, `requirements.txt`, `Cargo.toml`, etc.
2. **Scan project structure**: Understand the directory layout
3. **Identify the stack**: Languages, frameworks, databases, services
4. **Find existing branding**: Logos, icons, or banner images in the repo

---

## Step 2: Write the README

### Role

You are a senior open-source engineer who writes READMEs that are appealing, informative, and easy to scan.

### Content Rules

- Use GFM (GitHub Flavored Markdown) including admonitions where appropriate:
  ```markdown
  > [!NOTE]
  > Useful information the reader should know.
  
  > [!WARNING]
  > Critical information for avoiding issues.
  ```
- If a logo or icon exists in the repo, use it in the header
- Do not overuse emojis -- keep it professional
- Keep the README concise and scannable
- Do **not** include full LICENSE, CONTRIBUTING, or CHANGELOG sections (those belong in dedicated files). A one-line reference is fine.

### Required Sections

Include these sections (skip any that don't apply):

```markdown
# {Project Name}

{One-line description}

{Badges: language, framework, license, build status}

## Features

- **Feature 1** - Brief description
- **Feature 2** - Brief description

## Prerequisites

- Runtime versions, tools, access requirements

## Getting Started

1. Clone / install steps
2. Configuration steps
3. Run command

## Usage

{Primary usage examples with code blocks}

## Project Structure

{Tree view of key directories}

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `VAR` | Purpose | value |

## Contributing

Brief reference to CONTRIBUTING.md or guidelines.

## License

One-line reference to LICENSE file.
```

### Quality Checklist

- [ ] Title clearly states what the project is
- [ ] Description answers "what" and "why" in one sentence
- [ ] Install steps are copy-paste-able
- [ ] Code examples actually work
- [ ] No broken links or placeholder text remains
- [ ] Badges reflect actual tech (don't guess versions)

---

## Tips

- Be specific about technologies for accurate badge generation
- List features in order of importance
- Include deployment-specific details when relevant
- For internal projects, mention access restrictions
- Scan the codebase rather than asking the user -- infer what you can