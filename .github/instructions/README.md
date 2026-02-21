# Instructions

This folder contains coding instructions and guidelines that AI assistants apply automatically based on file types.

## What are Instructions?

Instructions are context-specific guidelines that tell AI assistants how to write code for specific languages, frameworks, or situations. They're automatically applied based on file patterns.

## Available Instructions

### Language & Framework Instructions

| File | Applies To | Purpose |
|------|------------|---------|
| [python.instructions.md](python.instructions.md) | `**/*.py` | Python coding standards |
| [sql.instructions.md](sql.instructions.md) | `**/*.sql` | SQL Server guidelines |
| [streamlit.instructions.md](streamlit.instructions.md) | `**/app.py, **/pages/*.py` | Streamlit patterns |
| [fastapi.instructions.md](fastapi.instructions.md) | `**/api/**/*.py` | FastAPI patterns |
| [frontend.instructions.md](frontend.instructions.md) | `**/*.html, **/*.css` | Frontend styling, brand guidelines |
| [mcp-server.instructions.md](mcp-server.instructions.md) | `**/mcp-servers/**/*.py` | MCP server development |

### DevOps & Infrastructure Instructions

| File | Applies To | Purpose |
|------|------------|---------|
| [docker.instructions.md](docker.instructions.md) | `**/Dockerfile, **/docker-compose*.yml` | Docker best practices |
| [github-actions.instructions.md](github-actions.instructions.md) | `.github/workflows/*.yml` | CI/CD pipeline patterns |

### Testing & Quality Instructions

| File | Applies To | Purpose |
|------|------------|---------|
| [testing.instructions.md](testing.instructions.md) | `**/tests/**/*.py` | Testing patterns |
| [code-review.instructions.md](code-review.instructions.md) | `**/*` | Code review guidelines |
| [playwright.instructions.md](playwright.instructions.md) | `**/tests/**/*.ts, **/*.spec.ts` | E2E testing with Playwright |

### Security & Accessibility Instructions

| File | Applies To | Purpose |
|------|------------|---------|
| [security.instructions.md](security.instructions.md) | `**/*` | Security best practices |
| [accessibility.instructions.md](accessibility.instructions.md) | `**/*.html, **/*.py` | WCAG 2.2 compliance |

## How Instructions Work

Each instruction file has a YAML frontmatter:

```yaml
---
description: "What this instruction covers"
applyTo: "**/*.py"  # Glob pattern for matching files
---
```

When you open or create a file matching the pattern, the AI assistant automatically considers these guidelines.

## Project-Specific Adaptations

All instructions are tailored for the project's environment:
- Python 3.11+ syntax and features
- SQL Server database
- Brand integration
- Air-gapped production considerations
- Shared library usage (`<SHARED_LIBS>` shared libraries)

## Using Instructions

Instructions are **IDE-agnostic**. Use them in any tool that accepts file-based or pasted context:

| IDE / Tool | How to use |
|------------|------------|
| **GitHub Copilot** | Instructions in `copilot-instructions.md` or project-level instructions; merge or link to these files. |
| **Cursor** | Add to `.cursorrules` or reference in chat; path-based rules can use the `applyTo` globs. |
| **VS Code (other extensions)** | Include in system/context via extension settings, or paste the relevant instruction when working on matching file types. |
| **Claude / other chat** | Paste or attach the instruction file when editing code that matches the `applyTo` pattern (e.g. Python → `python.instructions.md`). |

After sync, files live under `instructions/`. All paths are relative, so just place the AI resources folder wherever your IDE expects it (e.g. `.cursor/`, `.github/`).

## Portability & Precedence

When moving AI resources between projects or machines, use this model:

1. **Pool (portable default):** Keep shared behavior in `.github/agents/`, `.github/skills/`, `.github/prompts/`, `.github/instructions/`, `.github/diagrams/`.
2. **Project overlay (local):** Keep project-specific constraints in each project's `copilot-instructions.md`.
3. **Sync direction:** Use `junai-push` to publish pool updates from a project to `junai`; use `junai-pull` to bring latest pool into another project.
4. **Important:** `junai-pull`/`junai-push` do **not** sync project-local files like `copilot-instructions.md` or `.github/pipeline/*` unless your sync script is extended.
5. **Recommendation:** Put global guardrails (e.g., AdvisoryHub boundaries) in synced `instructions/` and `prompts/`, then mirror minimal project-specific wording in local `copilot-instructions.md`.
6. **First run on new machine:** clone/open project → load `sync.ps1` → run `junai-pull` → verify expected prompt/instruction files are present.

## Adding New Instructions

1. Create a new `.instructions.md` file
2. Add YAML frontmatter with `description` and `applyTo`
3. Write clear, actionable guidelines
4. Include code examples for best practices
