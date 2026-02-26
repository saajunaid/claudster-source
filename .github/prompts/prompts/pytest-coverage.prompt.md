---
description: 'Analyze pytest coverage and add tests to reach full code coverage'
---

# Pytest Coverage Improvement

Run pytest with coverage analysis and iteratively add tests until all lines are covered.

## Instructions

### Step 1: Generate Coverage Report

Run pytest with annotated coverage output:

```bash
pytest --cov --cov-report=annotate:cov_annotate
```

To scope to a specific module:

```bash
pytest --cov=<module_name> --cov-report=annotate:cov_annotate
```

To run specific test files:

```bash
pytest tests/test_<module>.py --cov=<module_name> --cov-report=annotate:cov_annotate
```

### Step 2: Identify Uncovered Lines

Open the `cov_annotate/` directory. Each source file has a corresponding annotated file:
- Lines starting with `!` (exclamation mark) are **not covered** by tests.
- Files with 100% coverage can be skipped.

### Step 3: Add Missing Tests

For each file with less than 100% coverage:

1. Open the annotated file and identify all `!`-marked lines.
2. Determine what test cases would exercise those code paths:
   - **Conditional branches** (if/elif/else)
   - **Exception handlers** (try/except)
   - **Edge cases** (empty inputs, None values, boundary conditions)
   - **Error paths** (invalid arguments, missing data)
3. Write focused tests that specifically target the uncovered lines.
4. Follow existing test conventions in the project (fixtures, naming, structure).

### Step 4: Verify and Iterate

Re-run the coverage command after adding tests. Repeat steps 2-3 until all lines are covered.

### Step 5: Clean Up

After reaching target coverage:
- Remove the `cov_annotate/` directory (or add it to `.gitignore`)
- Ensure all new tests pass independently: `pytest tests/ -v`

## Tips

- Prefer testing **behavior** over implementation details.
- Use `pytest.raises()` to cover exception paths.
- Use `@pytest.mark.parametrize` to cover multiple branches concisely.
- Mock external dependencies (database, APIs) to test error-handling paths.
- If a line is genuinely unreachable, mark it with `# pragma: no cover`.
