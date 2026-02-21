---
description: 'Run a comprehensive verification pass — build, lint, type-check, and test'
---

# Verify

Run all project verification checks and produce a pass/fail report.

> For the full verification methodology, see the skill at `skills/workflow/verification-loop/SKILL.md`.

## Instructions

Execute the following checks **in order**. Stop on critical failures.

### 1. Build Check
- Run the project's build command.
- If the build fails, report the errors and **stop** — nothing else matters until the build is fixed.

### 2. Type Check
- Run the type checker (e.g., `tsc --noEmit`, `mypy`, `pyright`).
- Report all errors with file and line number.

### 3. Lint Check
- Run the project's linter (e.g., `eslint`, `ruff`, `flake8`).
- Report warnings and errors.

### 4. Test Suite
- Run all tests with coverage enabled.
- Report pass/fail counts and coverage percentage.

### 5. Debug Artifact Audit
- Search source files (not test files) for `console.log`, `print()`, or `debugger` statements.
- Report locations so they can be removed before commit.

### 6. Git Status
- Show uncommitted changes and files modified since last commit.

## Output Format

Produce a concise verification report:

```
VERIFICATION: PASS / FAIL

Build:    OK / FAIL
Types:    OK / N errors
Lint:     OK / N issues
Tests:    X/Y passed, Z% coverage
Logs:     OK / N debug statements found

Ready for PR: YES / NO
```

If any check fails, list the issues with suggested fixes below the summary.

## Modes

You can scope the verification:
- **quick** — build + type-check only
- **full** — all checks (default)
- **pre-commit** — build, types, lint, debug audit
- **pre-pr** — all checks plus a search for hardcoded secrets or credentials
