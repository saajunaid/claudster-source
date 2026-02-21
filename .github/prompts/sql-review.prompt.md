---
description: "Review SQL code for security, performance, correctness, and best practices across all major databases"
mode: agent
tools: ['codebase', 'editFiles', 'search']
---

# /sql-review - SQL Code Review

Perform a thorough SQL code review of the provided code (or selection) focusing on security, performance, maintainability, and database best practices.

## Input

SQL code to review: `{{input}}`

If no SQL provided, scan the workspace for `.sql` files, stored procedures, or inline queries.

---

## Review Categories

### 1. Security Analysis

#### SQL Injection Prevention

```sql
-- BAD: SQL Injection vulnerability
query = "SELECT * FROM users WHERE id = " + userInput;

-- GOOD: Parameterized queries
-- PostgreSQL/MySQL
PREPARE stmt FROM 'SELECT * FROM users WHERE id = ?';
-- SQL Server
EXEC sp_executesql N'SELECT * FROM users WHERE id = @id', N'@id INT', @id = @user_id;
```

#### Access Control
- Principle of Least Privilege: Grant minimum required permissions
- Use database roles instead of direct user permissions
- Review DEFINER vs INVOKER rights on functions/procedures
- Avoid `SELECT *` on tables with sensitive columns

---

### 2. Performance Optimization

#### Common Anti-Patterns

**Functions in WHERE clauses (prevents index usage):**
```sql
-- BAD
SELECT * FROM orders WHERE YEAR(order_date) = 2024;
-- GOOD
SELECT * FROM orders WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01';
```

**N+1 Query Problem:**
```sql
-- BAD: N+1 queries in application code
for user in users:
    orders = query("SELECT * FROM orders WHERE user_id = ?", user.id)
-- GOOD: Single query
SELECT u.*, o.* FROM users u LEFT JOIN orders o ON u.id = o.user_id;
```

**Overuse of DISTINCT (masking join issues):**
```sql
-- BAD
SELECT DISTINCT u.name FROM users u, orders o WHERE u.id = o.user_id;
-- GOOD
SELECT u.name FROM users u INNER JOIN orders o ON u.id = o.user_id GROUP BY u.name;
```

#### Index Strategy
- Missing indexes on WHERE/JOIN/ORDER BY columns
- Over-indexing (unused or redundant indexes)
- Composite index column order
- Covering indexes for frequently queried column sets

#### Join Optimization
- Verify appropriate join types (INNER vs LEFT vs EXISTS)
- Optimize join order for smaller result sets first
- Identify accidental cartesian products (missing join conditions)

---

### 3. Code Quality & Maintainability

#### Naming Conventions
- Stored procedures: `usp_[Action][Entity]`
- User functions: `ufn_[Action]`
- Tables: `[Schema].[PascalCase]`
- Consistent casing across schema

#### Schema Design
- Appropriate normalization level
- Optimal data type choices
- Proper constraints (PK, FK, CHECK, NOT NULL)
- Appropriate default values

---

### 4. Database-Specific Best Practices

| Database | Key Practices |
|----------|--------------|
| **SQL Server** | Use `DATETIME2` over `DATETIME`, `NVARCHAR` for Unicode, `SET NOCOUNT ON`, columnstore for analytics |
| **PostgreSQL** | Use `JSONB` for JSON, `TIMESTAMPTZ` for timestamps, GIN indexes for full-text/JSONB |
| **MySQL** | InnoDB engine, covering indexes, avoid `ENUM` for evolving values |
| **Oracle** | Sequences for IDs, `VARCHAR2` over `VARCHAR`, bind variables |

---

## Review Output Format

### Issue Template

```
## [PRIORITY] [CATEGORY]: Brief Description

**Location**: Table/procedure name
**Issue**: Detailed explanation
**Impact**: Security risk / performance cost / maintenance burden

**Before**:
[problematic SQL]

**After**:
[improved SQL]
```

### Priority Levels

| Icon | Level | When to Use |
|------|-------|-------------|
| RED | Critical | Security vulnerabilities, data integrity risks |
| ORANGE | Issue | Bugs, significant performance problems |
| YELLOW | Suggestion | Improvements, better patterns |
| BLUE | Style | Formatting, naming conventions |

### Summary Scoring

| Category | Score (1-10) |
|----------|-------------|
| Security | SQL injection protection, access controls |
| Performance | Query efficiency, index usage |
| Maintainability | Code quality, documentation |
| Schema Quality | Design patterns, normalization |

**Top 3 Priority Actions**: List the three most impactful fixes.

---

## Review Checklist

### Security
- [ ] All user inputs are parameterized
- [ ] No dynamic SQL with string concatenation
- [ ] Appropriate access controls and permissions
- [ ] Sensitive data is properly protected

### Performance
- [ ] Indexes exist for WHERE/JOIN/ORDER BY columns
- [ ] No unnecessary `SELECT *`
- [ ] JOINs use appropriate types
- [ ] No functions on indexed columns in WHERE clauses
- [ ] Subqueries optimized or converted to JOINs

### Code Quality
- [ ] Consistent naming conventions
- [ ] Proper formatting and indentation
- [ ] Error handling (TRY/CATCH)
- [ ] `SET NOCOUNT ON` in stored procedures
- [ ] Transaction handling where needed

### Schema Design
- [ ] Tables properly normalized
- [ ] Constraints enforce data integrity
- [ ] Foreign key relationships defined
- [ ] Appropriate data types used
