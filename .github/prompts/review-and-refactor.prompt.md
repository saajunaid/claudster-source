---
description: 'Review code for quality issues and apply targeted refactoring improvements'
---

# Review and Refactor

Act as a senior software engineer. Review the specified code (or the full project) and apply refactoring improvements while maintaining correctness.

## Instructions

### Step 1: Understand the Standards

Check for project-level coding guidelines in common locations:
- `CONTRIBUTING.md`, `CODING_STANDARDS.md`, or similar docs
- Linter/formatter configs (`.eslintrc`, `pyproject.toml`, `.editorconfig`)
- Existing code patterns and conventions

If coding standards exist, all refactoring must conform to them.

### Step 2: Review the Code

Analyze each file for these issues:

**Readability**
- Unclear variable or function names
- Missing or misleading comments
- Overly complex expressions that could be simplified
- Inconsistent formatting or style

**Maintainability**
- Functions longer than ~40 lines (candidates for extraction)
- Duplicated logic across files
- Deep nesting (> 3 levels) that could be flattened
- Magic numbers or hardcoded strings (extract to constants)

**Best Practices**
- Missing error handling or overly broad exception catches
- Unused imports, variables, or dead code
- Mutable default arguments or other language-specific pitfalls
- Missing type hints or annotations (where the project uses them)

### Step 3: Refactor

Apply improvements while following these rules:

1. **Keep existing file structure** — do not split files unless explicitly asked.
2. **Preserve behavior** — refactoring must not change what the code does.
3. **Run tests after changes** — if the project has tests, verify they still pass.
4. **Make small, reviewable changes** — each refactoring should be easy to understand.

### Step 4: Summarize

After refactoring, provide a summary:

```
## Refactoring Summary

### Changes Made
| File | Change | Reason |
|------|--------|--------|
| ... | ... | ... |

### Tests
- All existing tests: PASS / FAIL
- New issues introduced: None / <list>

### Recommendations
- <any further improvements that were out of scope>
```

## What NOT to Do

- Do not rewrite working code for stylistic preference alone
- Do not add features or change behavior
- Do not remove comments that provide useful context
- Do not introduce new dependencies without asking
