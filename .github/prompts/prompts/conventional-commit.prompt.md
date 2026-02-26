---
description: "Generate and execute conventional commit messages following the Conventional Commits spec"
mode: agent
tools: ['codebase', 'runCommands']
---

# /commit - Conventional Commit

Generate and optionally execute a conventional commit for staged or unstaged changes.

## Automated Workflow

When invoked, follow these steps:

1. Run `git status` to review changed files
2. Run `git diff --cached` (or `git diff` if nothing staged) to inspect changes
3. Analyze the changes and construct a commit message using the format below
4. Present the commit message to the user for confirmation
5. Execute: `git commit -m "<message>"`

---

## Commit Message Format

```markdown

## Conventional Commits Format

<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

## Types (required)

| Type | Description | Example |
|------|-------------|---------|
| feat | New feature | `feat: add user authentication` |
| fix | Bug fix | `fix: resolve login timeout issue` |
| docs | Documentation only | `docs: update API reference` |
| style | Formatting, no code change | `style: fix indentation in models.py` |
| refactor | Code change, no feature/fix | `refactor: simplify database queries` |
| perf | Performance improvement | `perf: optimize image loading` |
| test | Adding/fixing tests | `test: add unit tests for auth module` |
| build | Build system changes | `build: update requirements.txt` |
| ci | CI configuration | `ci: add GitHub Actions workflow` |
| chore | Other maintenance | `chore: update .gitignore` |
| revert | Revert previous commit | `revert: revert "feat: add feature"` |

## Scopes (optional)

Indicate the section of codebase:
- `feat(api)`: Feature in API module
- `fix(ui)`: Fix in UI module
- `docs(readme)`: Documentation in README

Common scopes (adapt to your project):
- `api` - Backend/API layer
- `ui` - Frontend/UI layer
- `db` - Database/SQL
- `auth` - Authentication
- `config` - Configuration
- `lib` - Shared libraries

## Breaking Changes

Use `!` or `BREAKING CHANGE:` footer:
```
feat(api)!: change authentication flow

BREAKING CHANGE: JWT tokens now expire after 1 hour
```

## Examples

### Simple Feature
```
feat(ui): add network dashboard page

- Add metrics display with 4 KPI cards
- Implement date range filter
- Add traffic chart visualization
```

### Bug Fix
```
fix(api): resolve database connection timeout

Connection pool was not being reused between requests.
Added connection pool singleton to maintain connections.

Fixes #123
```

### Breaking Change
```
feat(api)!: require authentication for all endpoints

All API endpoints now require valid JWT token.
Anonymous access has been removed.

BREAKING CHANGE: All API clients must include 
Authorization header with valid JWT token.

Migration guide: docs/migration/auth-v2.md
```

### Documentation
```
docs: add installation instructions for Windows

- Add Windows-specific setup steps
- Include SQL Server Express installation
- Add Ollama Windows installation guide
```

### Refactoring
```
refactor(db): simplify query builder

- Remove deprecated query methods
- Consolidate duplicate code
- Improve type hints
```

## Guidelines

1. **Subject Line**
   - Use imperative mood ("add" not "added")
   - Lowercase first letter
   - No period at end
   - Max 50 characters

2. **Body**
   - Explain what and why (not how)
   - Wrap at 72 characters
   - Use bullet points for multiple changes

3. **Footer**
   - Reference issues: `Fixes #123`, `Closes #456`
   - Note breaking changes
   - Add co-authors: `Co-authored-by: Name <email>`

```

## Usage Examples

### Example 1: Feature Addition

**Input (Changes):**
```diff
+ Added new user settings page
+ Users can update profile information
+ Added email notification preferences
```

**Output:**
```
feat(ui): add user settings page

- Add profile information editing
- Add email notification preferences
- Integrate with existing auth system
```

### Example 2: Bug Fix

**Input (Changes):**
```diff
- Fixed issue where login fails after session timeout
- Updated token refresh logic
```

**Output:**
```
fix(auth): handle session timeout gracefully

Token refresh was not triggered on 401 responses.
Added automatic token refresh and retry logic.

Fixes #247
```

### Example 3: Multiple Changes

**Input (Changes):**
```diff
- Refactored database module
- Added connection pooling
- Improved query performance
- Updated tests
```

**Output:**
```
perf(db): implement connection pooling

- Add connection pool with configurable size
- Reuse connections across requests
- Reduce connection overhead by 60%

Tests updated to use pooled connections.
```

## Integration with Git

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/commit-msg

# Validate commit message format
if ! head -1 "$1" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?(!)?: .{1,50}$"; then
    echo "Invalid commit message format."
    echo "Expected: <type>[scope]: <description>"
    exit 1
fi
```

### Git Alias
```bash
# Add to ~/.gitconfig
[alias]
    cm = "!f() { git commit -m \"$1: $2\"; }; f"
    feat = "!f() { git commit -m \"feat: $1\"; }; f"
    fix = "!f() { git commit -m \"fix: $1\"; }; f"
```

## Quick Reference

```
/commit              ← Auto-detect changes and generate commit
/commit fix login    ← Hint: it's a fix related to login
```
