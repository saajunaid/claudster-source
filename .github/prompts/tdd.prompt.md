---
description: 'Start a test-driven development session using the red-green-refactor cycle'
---

# TDD Session

Implement the requested feature or fix using strict test-driven development.

> For the full TDD methodology and patterns, see the skill at `skills/testing/tdd-workflow/SKILL.md`.

## The TDD Cycle

```
RED    →  Write a failing test
GREEN  →  Write minimal code to make it pass
REFACTOR → Improve code while keeping tests green
REPEAT →  Next scenario
```

## Instructions

Follow these steps **in order** — never skip a phase:

### 1. Define the Interface

Define types, function signatures, or API contracts for the feature. Stub implementations with `throw new Error('Not implemented')` or equivalent.

### 2. Write Failing Tests (RED)

Write tests that cover:
- **Happy path** — the expected behavior
- **Edge cases** — empty inputs, nulls, boundary values
- **Error conditions** — invalid arguments, missing data

Run the tests. Confirm they **fail** for the expected reason (not due to syntax errors).

### 3. Implement Minimal Code (GREEN)

Write the simplest code that makes all tests pass. Do not over-engineer. Do not add untested behavior.

Run the tests. Confirm they **pass**.

### 4. Refactor (REFACTOR)

Improve code quality while tests stay green:
- Extract constants and helper functions
- Improve naming and readability
- Remove duplication

Run the tests again. Confirm they still **pass**.

### 5. Check Coverage

Run tests with coverage enabled. If coverage is below 80%, add more test cases and repeat from step 2.

## Rules

- **Tests first** — never write implementation before its test
- **Run tests after every change** — red, green, and refactor phases all end with a test run
- **Minimal code** — only write enough to pass the current tests
- **Small steps** — one test at a time, one behavior at a time
- **Test behavior, not implementation** — tests should not depend on internal details
