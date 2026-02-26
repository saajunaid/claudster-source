---
description: "Code review guidelines and checklist"
applyTo: "**/*"
---

# Code Review Guidelines

Structured approach to code review ensuring quality, security, and maintainability.

## Review Principles

1. **Be specific** - Reference exact lines, files, and provide concrete examples
2. **Provide context** - Explain WHY something is an issue and the potential impact
3. **Suggest solutions** - Show corrected code, not just what's wrong
4. **Be constructive** - Focus on improving the code, not criticizing the author
5. **Recognize good practices** - Acknowledge well-written code and smart solutions
6. **Be pragmatic** - Not every suggestion needs immediate implementation

---

## Review Priority (High to Low)

1. **Security** - Vulnerabilities, data exposure, injection risks
2. **Correctness** - Logic errors, edge cases, error handling, breaking changes
3. **Performance** - Inefficiencies, N+1 queries, memory leaks, resource cleanup
4. **Maintainability** - Readability, structure, documentation
5. **Style** - Formatting, naming, conventions

---

## Security Checklist

### Critical (Must Fix Before Merge)

- [ ] No hardcoded secrets, passwords, or API keys
- [ ] All SQL queries use parameterized queries
- [ ] User input is validated and sanitized
- [ ] Authentication required on protected endpoints
- [ ] Authorization checks for resource access
- [ ] No sensitive data logged (passwords, tokens, PII)
- [ ] Error messages don't expose system internals

### Example Findings

```python
# ❌ CRITICAL: SQL Injection
query = f"SELECT * FROM users WHERE id = '{user_id}'"

# ✅ FIXED: Parameterized query
query = "SELECT * FROM users WHERE id = ?"
result = adapter.fetch_dataframe(query, (user_id,))
```

---

## Correctness Checklist

### Error Handling

- [ ] All external calls wrapped in try/except
- [ ] Appropriate exception types caught (not bare `except:`)
- [ ] Error states handled gracefully
- [ ] Cleanup code in `finally` blocks where needed

```python
# ❌ BAD: Bare except
try:
    result = fetch_data()
except:
    pass  # Silent failure

# ✅ GOOD: Specific handling
try:
    result = fetch_data()
except ConnectionError as e:
    logger.error(f"Database connection failed: {e}")
    raise DataFetchError("Unable to fetch data") from e
```

### Edge Cases

- [ ] Empty collections handled
- [ ] Null/None values handled
- [ ] Boundary conditions tested
- [ ] Race conditions considered

```python
# ❌ BAD: No null check
def get_user_name(user: User | None) -> str:
    return user.name

# ✅ GOOD: Null handling
def get_user_name(user: User | None) -> str:
    if user is None:
        return "Unknown"
    return user.name
```

---

## Performance Checklist

### Database

- [ ] No N+1 query patterns
- [ ] Appropriate indexes exist for queries
- [ ] Large datasets use pagination
- [ ] Queries select only needed columns
- [ ] Connection pooling used

```python
# ❌ BAD: N+1 queries
for complaint in complaints:
    customer = fetch_customer(complaint.customer_id)  # Query per iteration

# ✅ GOOD: Batch fetch
customer_ids = [c.customer_id for c in complaints]
customers = fetch_customers(customer_ids)  # Single query
customer_map = {c.id: c for c in customers}
```

### Caching

- [ ] Appropriate caching strategy for data fetches
- [ ] Cache invalidation considered
- [ ] TTL appropriate for data freshness needs

```python
# ✅ GOOD: Cache with TTL
@st.cache_data(ttl=timedelta(minutes=15))
def fetch_dashboard_data():
    return adapter.fetch_dataframe("SELECT * FROM dashboard_metrics")
```

### Resource Management

- [ ] Database connections properly closed/returned to pool
- [ ] File handles closed (use context managers)
- [ ] Large data loaded lazily or paginated
- [ ] No unbounded in-memory collections

```python
# ❌ BAD: Connection leak
conn = get_connection()
result = conn.execute(query)
# conn never closed if exception occurs

# ✅ GOOD: Context manager ensures cleanup
with get_connection() as conn:
    result = conn.execute(query)
```

---

## Code Quality Principles

### KISS (Keep It Simple)
- Simplest solution that works — avoid over-engineering
- No premature optimization — easy to understand > clever code

### DRY (Don't Repeat Yourself)
- Extract common logic into functions/shared utilities
- Avoid copy-paste programming

### YAGNI (You Aren't Gonna Need It)
- Don't build features before they're needed
- Avoid speculative generality — start simple, refactor when needed

### Immutability
```python
# ✅ GOOD: Return new data rather than mutating
updated = {**record, "status": "closed"}

# ❌ BAD: Mutate in place
record["status"] = "closed"  # Harder to trace bugs
```

---

## Maintainability Checklist

### Clean Code

- [ ] Functions/methods under 50 lines
- [ ] Single responsibility principle followed
- [ ] No deeply nested conditionals (max 3 levels)
- [ ] Magic numbers replaced with named constants
- [ ] No code duplication (DRY)
- [ ] No commented-out code or TODO without tickets
- [ ] Code is self-documenting; comments explain "why" not "what"

```python
# ❌ BAD: Magic numbers
if priority > 3:
    escalate()

# ✅ GOOD: Named constants
ESCALATION_THRESHOLD = 3
if priority > ESCALATION_THRESHOLD:
    escalate()
```

### Architecture and Design

- [ ] Clear separation of concerns between layers
- [ ] Dependencies flow in the correct direction (high-level → low-level)
- [ ] Components are loosely coupled and independently testable
- [ ] Related functionality grouped together (high cohesion)
- [ ] Follows established patterns in the codebase

### Type Hints

- [ ] All function parameters typed
- [ ] Return types specified
- [ ] Complex types documented

```python
# ❌ BAD: No types
def process(data, options):
    ...

# ✅ GOOD: Full typing
def process(
    data: pd.DataFrame,
    options: ProcessOptions,
) -> ProcessingResult:
    ...
```

### Comments

- [ ] Comments explain "why", not "what"
- [ ] No obvious comments (e.g., `# increment counter` before `count += 1`)
- [ ] Complex workarounds or non-obvious decisions are documented

```python
# ✅ GOOD: Explain WHY
# Use exponential backoff to avoid overwhelming the API during outages
delay = min(1000 * (2 ** retry_count), 30000)

# ❌ BAD: State the obvious
# Set name to user's name
name = user.name
```

### Documentation

- [ ] Public functions have docstrings
- [ ] Complex logic has inline comments
- [ ] README updated if behavior changed
- [ ] API changes documented

```python
def calculate_sla_compliance(
    complaints: list[Complaint],
    sla_hours: int = 24
) -> float:
    """
    Calculate SLA compliance rate for complaints.
    
    Args:
        complaints: List of complaint records
        sla_hours: Target resolution time in hours
        
    Returns:
        Compliance rate as decimal (0.0 to 1.0)
        
    Example:
        >>> complaints = [...]
        >>> rate = calculate_sla_compliance(complaints, sla_hours=48)
        >>> print(f"{rate:.1%}")  # "85.0%"
    """
```

---

## API Design Standards

### REST Conventions
```
GET    /api/<resource>          # List
GET    /api/<resource>/:id      # Get one
POST   /api/<resource>          # Create
PUT    /api/<resource>/:id      # Full update
PATCH  /api/<resource>/:id      # Partial update
DELETE /api/<resource>/:id      # Delete
```

### Response Format Consistency
- [ ] All endpoints return a consistent response envelope
- [ ] Error responses include actionable messages (not stack traces)
- [ ] Pagination uses `total`, `page`, `per_page` fields

### Input Validation
- [ ] All user input validated at the API boundary (Pydantic, Zod, etc.)
- [ ] Validation errors return structured details, not generic 400s

---

## Code Smell Detection

Watch for these anti-patterns during review:

| Smell | Signs | Action |
|-------|-------|--------|
| Long Function | >50 lines | Extract Method |
| Deep Nesting | >3 indent levels | Guard Clauses / Early Returns |
| Magic Numbers | Hardcoded `3`, `500`, etc. | Named Constants |
| Feature Envy | Method uses another class's data more than its own | Move Method |
| Dead Code | Unused imports, functions, commented-out code | Delete (git has history) |
| Primitive Obsession | Using strings/ints for domain concepts | Value Objects / Enums |

---

## Testing Standards

When reviewing tests or verifying test coverage:

- [ ] Critical paths and new functionality have tests
- [ ] Test names are descriptive (`test_<what>_<condition>_<expected>`)
- [ ] Tests follow Arrange-Act-Assert (AAA) pattern
- [ ] Tests are independent — no shared mutable state between tests
- [ ] Specific assertions used (not generic `assertTrue`)
- [ ] Edge cases covered (nulls, empty collections, boundaries)
- [ ] External dependencies mocked; domain logic tested directly
- [ ] No tests that always pass or are commented out

```python
# ❌ BAD: Vague name, weak assertion
def test_calc():
    assert calculate_sla(data) is not None

# ✅ GOOD: Descriptive name, specific assertion
def test_sla_compliance_returns_zero_when_all_breached():
    complaints = build_complaints(resolved_after_sla=True)
    result = calculate_sla_compliance(complaints, sla_hours=24)
    assert result == 0.0
```

---

## Project-Specific Checklist

### Shared Libraries

- [ ] Using shared libraries for database access (see `project-config.md` → `<SHARED_LIBS>`)
- [ ] Using shared libraries for UI theming (see `project-config.md` → `<SHARED_LIBS>`)
- [ ] Using shared libraries for authentication (see `project-config.md` → `<SHARED_LIBS>`)

### Logging

- [ ] Using `loguru` (not `print` or `logging`)
- [ ] Appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- [ ] No sensitive data in logs

```python
# ❌ BAD
print(f"Processing complaint {complaint_id}")

# ✅ GOOD
from loguru import logger
logger.info(f"Processing complaint {complaint_id}")
```

### Configuration

- [ ] Environment variables via `pydantic-settings`
- [ ] No hardcoded configuration values
- [ ] `.env.example` updated if new vars added

### SQL Server

- [ ] Stored procedures follow `usp_` prefix
- [ ] Table naming follows convention (`[Schema].[TableName]`)
- [ ] Parameters use SQL Server types (`UNIQUEIDENTIFIER`, `NVARCHAR`)

---

## Review Comment Guidelines

### Be Constructive

```markdown
# ❌ BAD
"This code is wrong."

# ✅ GOOD
"This query is vulnerable to SQL injection. Consider using 
parameterized queries with `?` placeholders. Example:
```python
query = 'SELECT * FROM users WHERE id = ?'
result = adapter.fetch_dataframe(query, (user_id,))
```"
```

### Categorize Feedback

Use prefixes to indicate severity:

- `[CRITICAL]` - Must fix before merge (security, data loss)
- `[ISSUE]` - Bug or significant problem
- `[SUGGESTION]` - Improvement, not blocking
- `[NIT]` - Style/formatting, lowest priority
- `[QUESTION]` - Need clarification

### Structured Comment Template

```markdown
**[SEVERITY] Category: Brief title**

Description of the issue or suggestion.

**Why this matters:** Impact or risk if not addressed.

**Suggested fix:**
[code example]

**Reference:** [link to standard or documentation, if applicable]
```

### Example Review Comment

```markdown
[ISSUE] Error Handling: Unhandled None value from database lookup

This function doesn't handle the case when `user` is None,
which can happen when the user isn't found in the database.

**Why this matters:** Will raise AttributeError at runtime,
causing a 500 error for the end user.

**Suggested fix:**
```python
if user is None:
    raise UserNotFoundError(f"User {user_id} not found")
```
```

---

## Approval Criteria

### Ready to Merge

- ✅ No critical security issues
- ✅ No functional bugs
- ✅ Tests pass
- ✅ Code follows project conventions
- ✅ All critical/issue comments addressed

### Needs Changes

- ❌ Security vulnerabilities present
- ❌ Functionality broken
- ❌ Tests failing
- ❌ Critical comments unaddressed

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values. The profile defines `<ORG_NAME>`, `<DB_TYPE>`, `<LOGGING_LIB>`, `<SHARED_LIBS>`, and other project-specific tokens.
