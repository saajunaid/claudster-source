---
description: 'Analyze test coverage gaps and generate tests to reach 80%+ coverage'
---

# Test Coverage Improvement

Analyze the project's test coverage, identify gaps, and generate tests to bring coverage above 80%.

## Instructions

### Step 1: Run Coverage Analysis

Run tests with coverage reporting using the project's test framework:

```bash
# JavaScript/TypeScript
npm test -- --coverage

# Python
pytest --cov --cov-report=term-missing

# Or the project's equivalent command
```

### Step 2: Identify Gaps

Review the coverage report and find:
- Files below 80% line coverage
- Untested functions or methods
- Uncovered branches (if/else paths, error handlers, edge cases)

Prioritize by impact:
1. **Critical business logic** with low coverage
2. **Error handling paths** that are never tested
3. **Utility functions** used across the codebase
4. **Edge cases** — null, empty, boundary values

### Step 3: Generate Tests

For each under-covered file, write tests targeting the gaps:

- **Unit tests** for individual functions (happy path + error cases)
- **Integration tests** for API endpoints or service interactions
- **Edge case tests** for boundary conditions

Follow the project's existing test conventions (file naming, structure, assertions, mocking patterns).

### Step 4: Verify

Run coverage again and confirm improvement. Repeat steps 2-3 if still below target.

### Step 5: Report

Show before/after metrics:

```
## Coverage Report

| File | Before | After | Change |
|------|--------|-------|--------|
| src/service.ts | 45% | 87% | +42% |
| src/utils.ts | 60% | 95% | +35% |

Overall: 52% → 83% (+31%)
```

## Focus Areas

- Happy path scenarios
- Error handling and exception paths
- Edge cases: null, undefined, empty strings, empty arrays
- Boundary conditions: zero, negative, max values
- Async error paths and timeout handling
