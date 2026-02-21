---
description: "Performance optimization best practices for backend, database, and frontend"
applyTo: "*"
---

# Performance Optimization Guidelines

## General Principles

1. **Measure first** — Profile before optimizing. Use real data and production-like conditions.
2. **Optimize the common case** — Focus on hot paths and frequently executed code.
3. **Avoid premature optimization** — Write clear, correct code first. Optimize when measurements prove a bottleneck.
4. **Set performance budgets** — Define acceptable latency, throughput, and memory targets before starting.
5. **Optimize at the right level** — Algorithm > architecture > code micro-optimization.

---

## Backend Performance

### Algorithm and Data Structure Selection

- Choose appropriate data structures: `dict`/`set` for O(1) lookups, sorted containers for range queries
- Prefer O(n log n) or better algorithms; avoid O(n²) in hot paths
- Use generators and iterators for large data pipelines to avoid loading everything into memory

### Caching

```python
from functools import lru_cache

# In-memory cache for expensive, repeated computations
@lru_cache(maxsize=256)
def get_exchange_rate(currency_code: str, date: str) -> float:
    """Cached exchange rate lookup — date string ensures daily invalidation."""
    return fetch_rate_from_service(currency_code, date)
```

- Cache at the right granularity (per-request, per-user, global)
- Always set TTL (time-to-live) — stale data causes subtle bugs
- Implement cache invalidation on writes
- Protect against cache stampede with locking or staggered expiry

### Async I/O and Concurrency

```python
import asyncio
import aiohttp

async def fetch_all_endpoints(urls: list[str]) -> list[dict]:
    """Fetch multiple endpoints concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for resp in responses:
            if isinstance(resp, Exception):
                results.append({"error": str(resp)})
            else:
                results.append(await resp.json())
        return results
```

- Use `asyncio` for I/O-bound workloads (HTTP calls, database queries, file I/O)
- Use `multiprocessing` or `concurrent.futures.ProcessPoolExecutor` for CPU-bound work
- Avoid mixing blocking and async code — use `run_in_executor` for legacy blocking calls

### Connection Pooling

```python
from sqlalchemy import create_engine

engine = create_engine(
    connection_string,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections every 30 minutes
)
```

- Always pool database connections — never open/close per query
- Size pools based on expected concurrency, not maximum possible
- Set `pool_recycle` to avoid stale connections from server-side timeouts

### Batch Processing

```python
# ❌ BAD: One insert per record
for record in records:
    db.execute("INSERT INTO results VALUES (?)", (record,))

# ✅ GOOD: Batch insert
BATCH_SIZE = 1000
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i + BATCH_SIZE]
    db.executemany("INSERT INTO results VALUES (?)", batch)
    db.commit()
```

- Batch database writes (INSERT, UPDATE) in chunks of 500-2000 rows
- Batch API calls where the API supports bulk endpoints
- Use bulk copy (e.g., `BULK INSERT`, `pandas.to_sql` with `method='multi'`) for large loads

---

## Python-Specific Tips

### Profiling

```python
# Quick function-level profiling
import cProfile
cProfile.run('my_function()', sort='cumulative')

# Line-level profiling (install line_profiler)
# Decorate with @profile, then run: kernprof -l -v script.py
```

### Use Built-in Data Structures

```python
from collections import defaultdict, Counter, deque

# defaultdict avoids repeated key checks
word_counts = defaultdict(int)
for word in words:
    word_counts[word] += 1

# Counter for frequency analysis
top_items = Counter(items).most_common(10)

# deque for O(1) append/pop from both ends
buffer = deque(maxlen=1000)
```

### Avoid Common Python Pitfalls

```python
# ❌ BAD: String concatenation in loops (O(n²) memory)
result = ""
for line in lines:
    result += line + "\n"

# ✅ GOOD: Join (O(n))
result = "\n".join(lines)

# ❌ BAD: Repeated list search (O(n) per lookup)
if item in large_list:
    ...

# ✅ GOOD: Convert to set for repeated lookups (O(1) per lookup)
large_set = set(large_list)
if item in large_set:
    ...

# ❌ BAD: Loading entire file into memory
data = open("large_file.csv").read()

# ✅ GOOD: Stream with generator
import csv
def read_rows(filepath):
    with open(filepath) as f:
        reader = csv.reader(f)
        for row in reader:
            yield row
```

---

## Database Performance

### Indexing Strategy

```sql
-- Index columns used in WHERE, JOIN, and ORDER BY
CREATE INDEX IX_order_customer ON dbo.orders(customer_id);

-- Composite index matching common query patterns (column order matters)
CREATE INDEX IX_order_status_date
ON dbo.orders(status, created_at DESC)
INCLUDE (customer_id, total_amount);

-- Filtered index for active subset
CREATE INDEX IX_order_open
ON dbo.orders(created_at DESC)
WHERE status IN ('open', 'processing');
```

- Index columns that appear in `WHERE`, `JOIN ON`, and `ORDER BY`
- Put high-selectivity columns first in composite indexes
- Use `INCLUDE` columns to create covering indexes and avoid key lookups
- Use filtered indexes for queries that always filter on a known value
- Don't over-index — each index adds write overhead

### Query Optimization

```sql
-- ✅ Use EXISTS instead of IN for correlated checks
SELECT c.id, c.name
FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);

-- ✅ Avoid functions on indexed columns (non-sargable)
-- BAD:  WHERE YEAR(created_at) = 2025
-- GOOD: WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'

-- ✅ Use JOIN + GROUP BY instead of correlated subqueries
SELECT c.id, COUNT(o.id) AS order_count
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.id;
```

### Avoid the N+1 Query Problem

```python
# ❌ BAD: N+1 — one query per customer
customers = db.execute("SELECT id FROM customers").fetchall()
for c in customers:
    orders = db.execute("SELECT * FROM orders WHERE customer_id = ?", (c.id,))

# ✅ GOOD: Single query with JOIN or batch IN
orders = db.execute("""
    SELECT c.id, c.name, o.order_id, o.total
    FROM customers c
    JOIN orders o ON o.customer_id = c.id
    WHERE c.id IN (?, ?, ?)
""", customer_ids)
```

### Parameterized Queries

Always use parameterized queries — they prevent SQL injection and allow the database to cache execution plans.

```python
# ✅ Parameterized — plan reuse and safe
cursor.execute("SELECT * FROM orders WHERE status = ? AND total > ?", (status, min_total))

# ❌ String formatting — no plan reuse, injection risk
cursor.execute(f"SELECT * FROM orders WHERE status = '{status}'")
```

### Keep Transactions Short

- Do validation and preparation outside the transaction
- Only wrap the minimal atomic unit of work
- Never call external APIs inside a transaction
- Use appropriate isolation levels (READ COMMITTED for most cases)

---

## Caching Strategy

### Cache Hierarchy

| Layer | Scope | TTL | Use Case |
|-------|-------|-----|----------|
| In-process (`lru_cache`, dict) | Single process | Seconds–minutes | Config, lookups, computed values |
| Distributed (Redis, Memcached) | Shared across processes | Minutes–hours | Session data, API responses, query results |
| CDN / HTTP cache | Edge / browser | Hours–days | Static assets, public API responses |

### Cache Invalidation Patterns

```python
# Write-through: update cache on every write
def update_customer(customer_id: str, data: dict):
    db.update("customers", customer_id, data)
    cache.set(f"customer:{customer_id}", data, ttl=3600)

# Cache-aside: invalidate on write, populate on read
def get_customer(customer_id: str) -> dict:
    cached = cache.get(f"customer:{customer_id}")
    if cached:
        return cached
    customer = db.fetch_one("SELECT * FROM customers WHERE id = ?", (customer_id,))
    cache.set(f"customer:{customer_id}", customer, ttl=3600)
    return customer

def update_customer(customer_id: str, data: dict):
    db.update("customers", customer_id, data)
    cache.delete(f"customer:{customer_id}")  # Invalidate
```

### Stampede Protection

When a popular cache key expires, prevent all concurrent requests from hitting the database simultaneously.

```python
import threading

_locks: dict[str, threading.Lock] = {}

def get_with_lock(key: str, fetch_fn, ttl: int = 300):
    value = cache.get(key)
    if value is not None:
        return value

    lock = _locks.setdefault(key, threading.Lock())
    with lock:
        # Double-check after acquiring lock
        value = cache.get(key)
        if value is not None:
            return value
        value = fetch_fn()
        cache.set(key, value, ttl=ttl)
    return value
```

---

## Frontend Performance Basics

### Lazy Loading

- Defer loading of below-the-fold content and non-critical modules
- Use dynamic imports for route-based code splitting
- Lazy-load images with `loading="lazy"` or Intersection Observer

### Minimize DOM Operations

- Batch DOM updates; avoid layout thrashing (read-then-write cycles)
- Use virtual scrolling for long lists (hundreds+ items)
- Debounce or throttle expensive event handlers (scroll, resize, input)

```python
# Debounce example in Streamlit (server-side)
import time

if "last_search_time" not in st.session_state:
    st.session_state.last_search_time = 0

search_term = st.text_input("Search")
now = time.time()

if now - st.session_state.last_search_time > 0.3:  # 300ms debounce
    st.session_state.last_search_time = now
    results = search(search_term)
```

### Compression and Asset Optimization

- Enable gzip/Brotli compression on the server
- Minify JavaScript/CSS for production builds
- Optimize images (WebP, appropriate dimensions, compression)
- Set proper `Cache-Control` headers for static assets

---

## Performance Code Review Checklist

Use this checklist when reviewing code for performance issues:

### Backend
- [ ] No O(n²) or worse algorithms in hot paths
- [ ] Database connections are pooled
- [ ] Expensive computations are cached with appropriate TTL
- [ ] Batch operations used for bulk database writes
- [ ] No N+1 query patterns
- [ ] Async I/O for concurrent external calls
- [ ] Generators used for large data iteration (not loading all into memory)

### Database
- [ ] Queries use indexes (check execution plan for scans)
- [ ] No `SELECT *` in production queries
- [ ] WHERE clauses are sargable (no functions on indexed columns)
- [ ] Parameterized queries used everywhere
- [ ] Transactions are short and focused
- [ ] Pagination implemented for large result sets
- [ ] Appropriate isolation level selected

### Frontend
- [ ] Assets minified and compressed
- [ ] Images optimized and lazy-loaded
- [ ] Expensive event handlers debounced/throttled
- [ ] No unnecessary re-renders or DOM thrashing
- [ ] Code splitting applied for large bundles

### General
- [ ] Performance budgets defined and measured
- [ ] Profiling data supports the optimization (not guessing)
- [ ] Change does not degrade readability for marginal gains
- [ ] Cache invalidation strategy documented
