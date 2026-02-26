---
description: 'Perform a thorough code review checking security, quality, and best practices'
---

# Code Review

Perform a comprehensive review of the specified code changes (or uncommitted changes). Check for security issues, code quality, and adherence to best practices.

## Instructions

### Step 1: Identify Changes

Determine the scope of review:
- If reviewing uncommitted work: check `git diff` for changed files
- If reviewing specific files: use the files provided by the user
- If reviewing a PR: examine all changed files in the pull request

### Step 2: Review Each File

Check every changed file against these categories:

**Security (CRITICAL)**
- Hardcoded credentials, API keys, or tokens
- SQL injection vulnerabilities (unsanitized input in queries)
- XSS vulnerabilities (unescaped user input in output)
- Missing input validation on user-facing endpoints
- Path traversal risks in file operations
- Insecure dependency usage

**Code Quality (HIGH)**
- Functions exceeding ~50 lines (candidates for extraction)
- Files exceeding ~800 lines (candidates for splitting)
- Nesting depth greater than 4 levels
- Missing error handling or bare exception catches
- Leftover `console.log` / `print` / `debugger` statements
- Unresolved `TODO` or `FIXME` comments

**Best Practices (MEDIUM)**
- Mutation where immutable patterns are preferred
- Missing tests for new or changed functionality
- Missing documentation for public APIs
- Accessibility issues in UI code (missing labels, alt text, ARIA)
- Inconsistent naming or style relative to the rest of the codebase

### Step 3: Produce the Report

For each issue found, report:

```
### <Issue Title>
**Severity**: CRITICAL | HIGH | MEDIUM | LOW
**File**: <path>:<line>
**Issue**: <description of the problem>
**Fix**: <suggested fix or code change>
```

### Step 4: Summary

End with an overall assessment:

```
## Review Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |

**Verdict**: APPROVE / REQUEST CHANGES / BLOCK

Blocking issues: <list any CRITICAL or HIGH issues that must be fixed>
```

## Rules

- **Never approve code with CRITICAL security issues.**
- Flag HIGH issues as "must fix before merge."
- MEDIUM and LOW issues can be noted as suggestions.
- If no issues are found, still confirm the review was thorough.
