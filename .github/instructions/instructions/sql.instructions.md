---
description: "SQL Server coding conventions and guidelines"
applyTo: "**/*.sql"
---

# SQL Server Standards

## Query Externalization (CRITICAL)

**All SQL queries that fetch data from the database MUST be externalized to the query config file path defined in `project-config.md`.**

Do NOT:
- Write inline SQL in Python code
- Perform aggregations (COUNT, SUM, GROUP BY) in Python when database can do it
- Fetch all rows and filter in memory

```yaml
# ✅ CORRECT: Define query in queries.yaml
workbasket_distribution_filtered:
  description: "Count cases by WorkbasketHeading with date filter"
  entity: pega_cases
  sql: |
    SELECT 
      ISNULL(WorkbasketHeading, 'Unknown') AS workbasket_heading,
      COUNT(*) AS count
    FROM {table}
    WHERE [Created Date Time] >= ? AND [Created Date Time] < ?
    GROUP BY WorkbasketHeading
    ORDER BY count DESC
```

```python
# ✅ CORRECT: Call externalized query from repository
def get_workbasket_distribution(self):
    return self._execute_distribution_query(
        section="home_charts",
        query_name="workbasket_distribution_filtered"
    )

# ❌ WRONG: Inline SQL with Python aggregation
df = adapter.execute_query("SELECT * FROM L7DCases")
result = df.groupby("WorkbasketHeading").size()  # Never do this!
```

**When to use in-memory processing:**
- JSON file data (not in database)
- Post-processing already-returned SQL results (formatting, labeling)
- Combining results from multiple cached queries

### ⚠️ YAML Query Template Gotchas

Queries in `queries.yaml` use `{table}` placeholders via Python `str.format()`. This creates two traps:

**Trap 1: Curly braces in SQL** (e.g., JSON functions) must be **double-escaped**: `{{` and `}}`

```yaml
# ❌ BAD: Single braces interpreted as format() placeholders → KeyError
sql: |
  SELECT JSON_VALUE(data, '$.status') FROM {table}

# ✅ GOOD: Double-escape literal SQL curly braces
sql: |
  SELECT JSON_VALUE(data, '$[0]."status"') FROM {table}
```

**Trap 2: Every query entry MUST include an `entity:` key** that maps to the table configuration:

```yaml
# ✅ CORRECT: entity key present → table name resolved from config
workbasket_distribution:
  description: "Count by workbasket"
  entity: pega_cases              # ← REQUIRED
  sql: |
    SELECT WorkbasketHeading, COUNT(*) AS count
    FROM {table}
    GROUP BY WorkbasketHeading

# ❌ WRONG: Missing entity key → KeyError at runtime
workbasket_distribution:
  description: "Count by workbasket"
  sql: |
    SELECT WorkbasketHeading, COUNT(*) FROM {table}
```

**Trap 3: User input must NEVER flow into `{table}` substitution** — only trusted config values. User input goes through `?` parameter placeholders only. See security instructions (OWASP A03).

## Naming Conventions

### Tables
- Use **singular** names: `complaint` not `complaints`
- Use **lowercase** with underscores: `customer_order`
- Use schema prefixes: `complaints.complaint`, `eecc.contract`

### Columns
- Use **lowercase** with underscores: `customer_id`, `created_at`
- Boolean columns: prefix with `is_` or `has_`: `is_active`, `has_paid`
- Date/time columns: suffix with `_at` or `_date`: `created_at`, `due_date`

### Keys and Constraints
- Primary key: `id` (UNIQUEIDENTIFIER or INT)
- Foreign keys: `{referenced_table}_id`: `customer_id`, `complaint_id`
- Index names: `IX_{table}_{column}`: `IX_complaint_customer_id`
- Foreign key names: `FK_{child}_{parent}`: `FK_complaint_customer`

### Stored Procedures
- Prefix: `usp_` (user stored procedure)
- Use PascalCase: `usp_GetComplaintsByStatus`
- Use verbs: `Get`, `Create`, `Update`, `Delete`, `List`

### Views
- Prefix: `vw_`
- Use snake_case: `vw_open_complaints`, `vw_daily_summary`

## SQL Style Guide

### Keywords and Formatting

```sql
-- ✅ GOOD: Uppercase keywords, proper formatting
SELECT 
    c.id,
    c.customer_name,
    c.complaint_type,
    c.status,
    c.created_at,
    DATEDIFF(DAY, c.created_at, GETDATE()) AS days_open
FROM complaints.complaint c
INNER JOIN customer.customer cu ON c.customer_id = cu.id
WHERE c.status = 'open'
  AND c.priority <= 2
ORDER BY c.created_at DESC;

-- ❌ BAD: Poor formatting
select c.id,c.customer_name,c.complaint_type from complaints.complaint c inner join customer.customer cu on c.customer_id=cu.id where c.status='open' and c.priority<=2;
```

### Column Selection

```sql
-- ❌ BAD: SELECT *
SELECT * FROM complaints.complaint;

-- ✅ GOOD: Explicit columns
SELECT 
    id,
    customer_id,
    complaint_type,
    status,
    created_at
FROM complaints.complaint;
```

### JOINs

```sql
-- ✅ GOOD: Explicit JOIN syntax
SELECT c.id, cu.name
FROM complaints.complaint c
INNER JOIN customer.customer cu ON c.customer_id = cu.id
LEFT JOIN agent.agent a ON c.assigned_to = a.id;

-- ❌ BAD: Implicit join (old style)
SELECT c.id, cu.name
FROM complaints.complaint c, customer.customer cu
WHERE c.customer_id = cu.id;
```

### Date Filtering (Sargable)

```sql
-- ❌ BAD: Function on indexed column
SELECT * FROM complaints.complaint
WHERE YEAR(created_at) = 2024;

-- ✅ GOOD: Range comparison
SELECT * FROM complaints.complaint
WHERE created_at >= '2024-01-01'
  AND created_at < '2025-01-01';
```

## Table Creation Template

```sql
-- ============================================================
-- Table: complaints.complaint
-- Description: Customer complaints from all channels
-- Created: 2026-01-27
-- ============================================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'complaints')
    EXEC('CREATE SCHEMA complaints');
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'complaint' AND schema_id = SCHEMA_ID('complaints'))
BEGIN
    CREATE TABLE complaints.complaint (
        -- Primary Key
        id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
        
        -- Business Columns
        customer_id VARCHAR(50) NOT NULL,
        customer_name NVARCHAR(200),
        account_number VARCHAR(50),
        complaint_type VARCHAR(100) NOT NULL,
        complaint_category VARCHAR(100),
        description NVARCHAR(MAX),
        priority INT DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
        status VARCHAR(50) DEFAULT 'open',
        resolution NVARCHAR(MAX),
        
        -- Foreign Keys
        assigned_to VARCHAR(100),
        assigned_team VARCHAR(100),
        
        -- Source Tracking
        source_system VARCHAR(50) NOT NULL,
        source_id VARCHAR(100),
        
        -- SLA
        sla_due_at DATETIME2,
        
        -- Audit Columns
        created_at DATETIME2 DEFAULT GETDATE(),
        created_by VARCHAR(100),
        updated_at DATETIME2,
        updated_by VARCHAR(100),
        resolved_at DATETIME2,
        
        -- Indexes
        INDEX IX_complaint_customer (customer_id),
        INDEX IX_complaint_status (status),
        INDEX IX_complaint_created (created_at DESC),
        INDEX IX_complaint_sla (sla_due_at) WHERE status NOT IN ('resolved', 'closed')
    );
    
    PRINT 'Created complaints.complaint table';
END
GO
```

## Stored Procedure Template

```sql
/*
============================================================
Stored Procedure: usp_GetComplaintsByDateRange
Description: Retrieves complaints within a date range
Author: <TEAM_NAME>
Created: 2026-01-27
Modified: 
============================================================
Parameters:
    @startDate DATE - Start of date range (inclusive)
    @endDate DATE - End of date range (inclusive)
    @status VARCHAR(50) - Optional status filter (NULL = all)
    @pageNumber INT - Page number for pagination (default 1)
    @pageSize INT - Results per page (default 50)
Returns:
    Result set of complaints with pagination
============================================================
*/
CREATE OR ALTER PROCEDURE complaints.usp_GetComplaintsByDateRange
    @startDate DATE,
    @endDate DATE,
    @status VARCHAR(50) = NULL,
    @pageNumber INT = 1,
    @pageSize INT = 50
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Validate inputs
    IF @startDate > @endDate
        THROW 50001, 'Start date must be before end date', 1;
    
    IF @pageNumber < 1 SET @pageNumber = 1;
    IF @pageSize < 1 OR @pageSize > 1000 SET @pageSize = 50;
    
    BEGIN TRY
        -- Get total count
        DECLARE @totalCount INT;
        
        SELECT @totalCount = COUNT(*)
        FROM complaints.complaint
        WHERE created_at >= @startDate
          AND created_at < DATEADD(DAY, 1, @endDate)
          AND (@status IS NULL OR status = @status);
        
        -- Return results
        SELECT 
            id,
            customer_id,
            customer_name,
            complaint_type,
            description,
            priority,
            status,
            assigned_to,
            created_at,
            resolved_at,
            DATEDIFF(DAY, created_at, ISNULL(resolved_at, GETDATE())) AS days_open,
            @totalCount AS total_count
        FROM complaints.complaint
        WHERE created_at >= @startDate
          AND created_at < DATEADD(DAY, 1, @endDate)
          AND (@status IS NULL OR status = @status)
        ORDER BY created_at DESC
        OFFSET (@pageNumber - 1) * @pageSize ROWS
        FETCH NEXT @pageSize ROWS ONLY;
        
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END;
GO
```

## Security Best Practices

### Parameterized Queries (CRITICAL)

```sql
-- ❌ CRITICAL VULNERABILITY: SQL Injection
DECLARE @sql NVARCHAR(MAX);
SET @sql = 'SELECT * FROM users WHERE id = ' + @userId;
EXEC(@sql);

-- ✅ GOOD: Parameterized query
EXEC sp_executesql 
    N'SELECT * FROM users WHERE id = @id',
    N'@id UNIQUEIDENTIFIER',
    @id = @userId;
```

### Python Parameter Placeholders (pyodbc)

pyodbc uses `?` as the parameter placeholder. **Not** `%s` (psycopg2), `:name` (cx_Oracle), or `@param` (T-SQL inline).

```python
# ✅ CORRECT: pyodbc uses ? placeholders
cursor.execute(
    "SELECT * FROM users WHERE id = ? AND status = ?",
    (user_id, status)
)

# ❌ WRONG: These are for other database drivers
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))       # psycopg2
cursor.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})  # cx_Oracle
```

### Validate Dynamic SQL

```sql
-- Validate table names before use
IF @tableName NOT IN ('complaints', 'customers', 'orders')
    THROW 50001, 'Invalid table name', 1;

-- Use QUOTENAME for identifiers
SET @sql = N'SELECT * FROM ' + QUOTENAME(@schemaName) + N'.' + QUOTENAME(@tableName);
```

### SQL Server Bracket Notation + Pydantic Alias Mapping

SQL Server uses `[Square Brackets]` for column names with spaces. When mapping to Pydantic models, the `alias` string must match the SQL column name **exactly** (including spaces and case).

```python
from pydantic import BaseModel, Field, ConfigDict

class InteractionRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    interaction_id: str = Field(alias="Interaction ID")
    created_date: str = Field(alias="Created Date Time")
    account_number: str = Field(alias="AccountNumber")  # No spaces = no brackets needed in SQL
```

```sql
-- The SQL column names must match the alias strings
SELECT
    [Interaction ID],
    [Created Date Time],
    AccountNumber
FROM L30DInteractions
```

**Rule:** A mismatch between bracket-quoted SQL column names and Pydantic `alias` values causes silent `None` fields — always verify aliases against the actual database schema.

## Performance Guidelines

### Index Strategy

```sql
-- Create indexes for frequently filtered columns
CREATE INDEX IX_complaint_customer ON complaints.complaint(customer_id);

-- Composite index for common query patterns
CREATE INDEX IX_complaint_status_created 
ON complaints.complaint(status, created_at DESC)
INCLUDE (customer_id, priority);

-- Filtered index for active records only
CREATE INDEX IX_complaint_open 
ON complaints.complaint(created_at DESC)
WHERE status IN ('open', 'in_progress');
```

### Query Optimization

```sql
-- Use EXISTS instead of IN for large sets
-- ❌ Slower with large subquery
SELECT * FROM customers
WHERE id IN (SELECT customer_id FROM complaints);

-- ✅ Faster with EXISTS
SELECT * FROM customers c
WHERE EXISTS (SELECT 1 FROM complaints WHERE customer_id = c.id);

-- Use appropriate aggregation
-- ❌ Correlated subquery (slow)
SELECT c.*,
    (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) AS order_count
FROM customers c;

-- ✅ JOIN with aggregation (fast)
SELECT c.*, ISNULL(o.order_count, 0) AS order_count
FROM customers c
LEFT JOIN (
    SELECT customer_id, COUNT(*) AS order_count
    FROM orders GROUP BY customer_id
) o ON c.id = o.customer_id;
```

---

## Project Defaults

> These defaults should be defined in `project-config.md`. Override with your project's values.

| Placeholder | Default Value |
|-------------|---------------|
| `<DB_TYPE>` | SQL Server (MSSQL) |
