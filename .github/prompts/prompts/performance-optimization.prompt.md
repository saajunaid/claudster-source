---
description: "Optimize code, queries, or systems for better performance with a structured profiling and analysis approach"
---

# Performance Optimization Prompt

Use this prompt when you need to optimize code for better performance.

## Context Template

```
I need to optimize [FUNCTION/MODULE/QUERY] for better performance.

## Current Situation
- Current performance: [e.g., 5 seconds response time]
- Target performance: [e.g., < 500ms response time]
- Volume: [e.g., 10,000 records, 100 concurrent users]

## Constraints
- Cannot change: [e.g., database schema, external API]
- Must maintain: [e.g., existing API contract]
- Budget: [e.g., no additional infrastructure]

## What I've Tried
- [List previous optimization attempts]

## Code/Query to Optimize
[Paste the code or query]
```

## Example: SQL Query Optimization

```
I need to optimize this SQL query for better performance.

## Current Situation
- Current performance: 12 seconds
- Target performance: < 1 second
- Volume: 500,000 records, queried 50 times/hour

## Constraints
- Cannot add new indexes (DBA approval required for production)
- Must return same result set

## What I've Tried
- Added WHERE clause filters
- Reduced SELECT columns

## Query to Optimize
SELECT c.customer_id, c.name, 
       COUNT(o.order_id) as order_count,
       SUM(o.total) as total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.created_at > '2024-01-01'
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC
```

## Analysis Framework

When optimizing, ask for:

### 1. Profiling
- Where is time being spent?
- What are the bottlenecks?
- Memory usage patterns?

### 2. Algorithm Analysis
- Time complexity (O notation)?
- Can we reduce iterations?
- Are there more efficient algorithms?

### 3. Database Optimization
- Query execution plan analysis
- Index recommendations
- Query restructuring

### 4. Caching Opportunities
- What data is static or slowly changing?
- What queries are repeated?
- Where can we add memoization?

### 5. Parallelization
- Can work be distributed?
- Are there independent operations?
- Would async help?

## Project-Specific Optimizations

### Streamlit Performance
```python
# Use caching for expensive operations
@st.cache_data(ttl=3600)
def load_data():
    return expensive_query()

# Use session state for persistent data
if 'data' not in st.session_state:
    st.session_state.data = load_data()
```

### SQL Server Optimization
```sql
-- Use TOP to limit results
SELECT TOP 100 ...

-- Avoid SELECT *
SELECT specific_columns ...

-- Use EXISTS instead of IN for subqueries
WHERE EXISTS (SELECT 1 FROM ...)
```

### Python Performance
```python
# Use list comprehensions
items = [x.process() for x in data]

# Use generators for large datasets
def process_large_file(file):
    for line in file:
        yield process_line(line)

# Use appropriate data structures
seen = set()  # O(1) lookup vs list O(n)
```

## Expected Output

When the AI analyzes your performance issue, it should produce:

```markdown
## Performance Analysis: [Component Name]

### Current Performance
- Metric: [e.g., 12s query time]
- Bottleneck: [where time is spent]

### Root Cause
[Explanation of why it's slow -- e.g., "Full table scan on 500K rows due to
missing index on created_at column, plus implicit type conversion on customer_id"]

### Recommended Optimizations (Priority Order)

#### 1. [Highest Impact Change]
- **Impact**: [e.g., 12s -> 0.8s (93% improvement)]
- **Effort**: [Low/Medium/High]
- **Before**:
  ```sql
  SELECT * FROM orders WHERE YEAR(created_at) = 2026
  ```
- **After**:
  ```sql
  SELECT order_id, customer_name, status
  FROM orders
  WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'
  ```
- **Why**: Allows index seek instead of table scan

#### 2. [Second Optimization]
...

### Verification
- Run the optimized version and measure: [specific test command]
- Expected result: [target metric]
```
