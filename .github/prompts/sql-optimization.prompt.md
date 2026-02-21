---
description: 'Analyze and optimize SQL queries for performance across any database engine'
---

# SQL Performance Optimization

Analyze the provided SQL queries (or project SQL code) and optimize them for performance. Apply universal techniques that work across MySQL, PostgreSQL, SQL Server, Oracle, and other SQL databases.

## Instructions

1. Identify the target database engine if possible (ask if unclear).
2. For each query or pattern found, analyze and optimize using the areas below.
3. Show **before** (problematic) and **after** (optimized) versions with explanations.
4. Suggest index changes where applicable.

## Optimization Areas

### Query Structure
- Replace `SELECT *` with explicit column lists
- Convert correlated subqueries to JOINs or window functions
- Use `EXISTS` instead of `IN` for subqueries when appropriate
- Filter early in `WHERE` clauses to reduce row processing
- Avoid functions on indexed columns in `WHERE` (breaks index usage)

### JOIN Optimization
- Use `INNER JOIN` instead of `LEFT JOIN` when NULLs aren't needed
- Move filter conditions into `JOIN ... ON` when logically correct
- Order JOINs from smallest to largest result set where the optimizer benefits

### Index Strategy
- Suggest composite indexes matching query filter + sort order
- Recommend covering indexes for frequently-run queries
- Flag over-indexing risks (impacts write performance)
- Consider partial indexes for filtered subsets

### Pagination
- Replace large-offset `LIMIT/OFFSET` with cursor-based pagination
- Use keyset pagination (`WHERE id > last_seen_id ORDER BY id LIMIT N`)

### Aggregation and Batching
- Combine multiple `COUNT` queries into a single conditional aggregation
- Replace row-by-row inserts with batch `INSERT ... VALUES`
- Use temporary tables for complex multi-step calculations

### Anti-Patterns to Flag
- `SELECT *` in production queries
- Functions wrapping indexed columns in `WHERE`
- N+1 query patterns in application code
- Missing `LIMIT` on unbounded queries
- `OR` conditions that prevent index usage (suggest `UNION ALL`)

## Output Format

For each optimization, provide:

```
### Issue: <brief description>
**Severity**: High | Medium | Low
**Before**: <original SQL>
**After**: <optimized SQL>
**Why**: <explanation of the performance improvement>
**Index suggestion** (if any): <CREATE INDEX statement>
```

## Optimization Checklist

After reviewing all queries, summarize:

- [ ] No `SELECT *` in production queries
- [ ] JOINs use appropriate types and order
- [ ] WHERE clauses are index-friendly
- [ ] Pagination uses cursor-based approach for large sets
- [ ] Batch operations used for bulk inserts/updates
- [ ] Indexes match query patterns without over-indexing
- [ ] Execution plans reviewed for remaining bottlenecks
