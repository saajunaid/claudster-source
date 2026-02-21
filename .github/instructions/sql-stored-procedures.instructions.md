---
description: "Stored procedure development patterns, parameter handling, and transaction management"
applyTo: "**/*.sql"
---

# SQL Stored Procedure Development

> Complements `sql.instructions.md` which covers naming conventions and the base template. This file adds depth on parameters, transactions, error handling, and security.

---

## Header Comment Block

Every stored procedure must include a header comment. Include description, parameters with types and purpose, return values, and change history.

```sql
/*
============================================================
Stored Procedure: usp_ProcessBatchPayments
Description: Processes pending payments in batches with retry logic
Author: <Team Name>
Created: YYYY-MM-DD
Modified:
    YYYY-MM-DD - <Author> - Added retry logic for failed payments
============================================================
Parameters:
    @batchSize INT - Number of records per batch (default 500)
    @maxRetries INT - Maximum retry attempts (default 3)
    @processedCount INT OUTPUT - Total records processed
    @errorCount INT OUTPUT - Total records that failed
Returns:
    0 = Success, 1 = Partial failure, -1 = Critical failure
============================================================
*/
```

---

## Parameter Handling

### Naming and Ordering

- Prefix all parameters with `@` and use camelCase: `@startDate`, `@customerId`
- List required parameters first, then optional parameters with defaults
- Use meaningful names that describe the data, not abbreviations

```sql
CREATE OR ALTER PROCEDURE dbo.usp_GetCustomerOrders
    -- Required parameters first
    @customerId VARCHAR(50),
    @startDate DATE,
    -- Optional parameters with defaults
    @endDate DATE = NULL,
    @status VARCHAR(50) = NULL,
    @pageNumber INT = 1,
    @pageSize INT = 50,
    -- Output parameters last
    @totalCount INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    -- Default NULL endDate to today
    SET @endDate = ISNULL(@endDate, CAST(GETDATE() AS DATE));

    -- ...
END;
```

### Parameter Validation

Validate all parameters before executing business logic. Fail early with clear messages.

```sql
CREATE OR ALTER PROCEDURE dbo.usp_UpdateOrderStatus
    @orderId INT,
    @newStatus VARCHAR(50),
    @updatedBy VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    -- Validate required parameters
    IF @orderId IS NULL OR @orderId <= 0
        THROW 50001, 'Parameter @orderId must be a positive integer.', 1;

    IF @newStatus IS NULL OR LEN(TRIM(@newStatus)) = 0
        THROW 50002, 'Parameter @newStatus cannot be empty.', 1;

    IF @newStatus NOT IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')
        THROW 50003, 'Parameter @newStatus contains an invalid status value.', 1;

    IF @updatedBy IS NULL OR LEN(TRIM(@updatedBy)) = 0
        THROW 50004, 'Parameter @updatedBy is required.', 1;

    -- Business logic here (inputs are validated)
    -- ...
END;
```

### Output Parameters for Status Reporting

Use OUTPUT parameters to return processing status alongside result sets.

```sql
CREATE OR ALTER PROCEDURE dbo.usp_ImportRecords
    @sourceTable VARCHAR(128),
    @importedCount INT OUTPUT,
    @skippedCount INT OUTPUT,
    @errorMessage NVARCHAR(500) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    SET @importedCount = 0;
    SET @skippedCount = 0;
    SET @errorMessage = NULL;

    BEGIN TRY
        -- Processing logic...
        SET @importedCount = @@ROWCOUNT;
    END TRY
    BEGIN CATCH
        SET @errorMessage = ERROR_MESSAGE();
        RETURN -1;  -- Signal failure
    END CATCH

    RETURN 0;  -- Signal success
END;
```

---

## Error Handling

### Standard TRY/CATCH Pattern

Always wrap business logic in TRY/CATCH. Return standardized error codes and messages.

```sql
CREATE OR ALTER PROCEDURE dbo.usp_TransferFunds
    @fromAccountId INT,
    @toAccountId INT,
    @amount DECIMAL(18, 2)
AS
BEGIN
    SET NOCOUNT ON;

    -- Validate inputs
    IF @amount <= 0
        THROW 50001, 'Transfer amount must be positive.', 1;

    IF @fromAccountId = @toAccountId
        THROW 50002, 'Source and destination accounts must differ.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        -- Debit source account
        UPDATE dbo.account
        SET balance = balance - @amount,
            updated_at = GETDATE()
        WHERE id = @fromAccountId
          AND balance >= @amount;

        IF @@ROWCOUNT = 0
            THROW 50010, 'Insufficient funds or source account not found.', 1;

        -- Credit destination account
        UPDATE dbo.account
        SET balance = balance + @amount,
            updated_at = GETDATE()
        WHERE id = @toAccountId;

        IF @@ROWCOUNT = 0
            THROW 50011, 'Destination account not found.', 1;

        COMMIT TRANSACTION;
        RETURN 0;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        -- Re-throw with original error context
        THROW;
    END CATCH
END;
```

### Error Code Conventions

| Range | Category |
|-------|----------|
| 50001 - 50099 | Parameter validation errors |
| 50100 - 50199 | Business rule violations |
| 50200 - 50299 | Data integrity errors |
| 50300 - 50399 | External dependency errors |

---

## Transaction Management

### Explicit Transaction Control

Always explicitly `BEGIN` and `COMMIT` transactions. Never rely on implicit transactions.

```sql
BEGIN TRY
    BEGIN TRANSACTION;

    -- All related operations inside the transaction
    INSERT INTO dbo.order_header (customer_id, order_date)
    VALUES (@customerId, GETDATE());

    DECLARE @orderId INT = SCOPE_IDENTITY();

    INSERT INTO dbo.order_line (order_id, product_id, quantity)
    SELECT product_id, quantity
    FROM @orderItems;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH
```

### Isolation Levels

Choose the appropriate isolation level for each operation.

```sql
-- For read-heavy reporting queries (avoids blocking writers)
SET TRANSACTION ISOLATION LEVEL READ COMMITTED SNAPSHOT;

-- For operations requiring consistent reads across multiple statements
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;

-- For critical financial operations
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
```

### Keep Transactions Short

- Do all preparation (validation, temp table population) before starting the transaction
- Only wrap the minimal set of statements that must be atomic
- Avoid calling external services or performing I/O inside transactions

```sql
-- ✅ GOOD: Preparation outside, minimal transaction scope
DECLARE @validRecords TABLE (id INT, amount DECIMAL(18,2));

-- Validate and stage data BEFORE the transaction
INSERT INTO @validRecords (id, amount)
SELECT id, amount
FROM dbo.pending_records
WHERE status = 'validated';

-- Short, focused transaction
BEGIN TRANSACTION;

UPDATE dbo.pending_records
SET status = 'processed', processed_at = GETDATE()
WHERE id IN (SELECT id FROM @validRecords);

INSERT INTO dbo.processed_log (record_id, amount, processed_at)
SELECT id, amount, GETDATE()
FROM @validRecords;

COMMIT TRANSACTION;
```

---

## Batch Processing for Large Data

Avoid processing millions of rows in a single statement. Use batched operations to reduce lock contention and transaction log pressure.

```sql
CREATE OR ALTER PROCEDURE dbo.usp_ArchiveOldRecords
    @cutoffDate DATE,
    @batchSize INT = 5000
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @rowsAffected INT = 1;
    DECLARE @totalArchived INT = 0;

    WHILE @rowsAffected > 0
    BEGIN
        BEGIN TRY
            BEGIN TRANSACTION;

            DELETE TOP (@batchSize)
            FROM dbo.audit_log
            OUTPUT DELETED.* INTO dbo.audit_log_archive
            WHERE created_at < @cutoffDate;

            SET @rowsAffected = @@ROWCOUNT;
            SET @totalArchived += @rowsAffected;

            COMMIT TRANSACTION;

            -- Brief pause to let other queries through
            WAITFOR DELAY '00:00:00.100';
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0
                ROLLBACK TRANSACTION;
            THROW;
        END CATCH
    END

    PRINT CONCAT('Archived ', @totalArchived, ' records.');
END;
```

---

## Temporary Table Conventions

- Prefix temporary tables with `tmp_` for clarity in stored procedure code
- Use table variables (`@tableVar`) for small result sets (< ~1000 rows)
- Use temp tables (`#tmp_`) for larger data sets that benefit from statistics and indexes
- Always clean up explicitly when using global temp tables (`##`)

```sql
-- Table variable for small lookups
DECLARE @tmp_ValidStatuses TABLE (
    status VARCHAR(50) PRIMARY KEY
);
INSERT INTO @tmp_ValidStatuses VALUES ('open'), ('in_progress'), ('pending');

-- Temp table for larger working sets
CREATE TABLE #tmp_StagedRecords (
    id INT PRIMARY KEY,
    customer_id VARCHAR(50),
    amount DECIMAL(18, 2),
    INDEX IX_tmp_staged_customer (customer_id)
);

-- Populate and use...
INSERT INTO #tmp_StagedRecords (id, customer_id, amount)
SELECT id, customer_id, amount
FROM dbo.incoming_records
WHERE status = 'new';

-- Clean up temp tables when done
DROP TABLE IF EXISTS #tmp_StagedRecords;
```

---

## Security in Stored Procedures

### Parameterize Dynamic SQL

Never concatenate user input into SQL strings. Always use `sp_executesql`.

```sql
-- ✅ GOOD: Parameterized dynamic SQL
DECLARE @sql NVARCHAR(MAX);
DECLARE @params NVARCHAR(500);

SET @sql = N'SELECT id, name FROM ' + QUOTENAME(@schemaName) + N'.' + QUOTENAME(@tableName)
         + N' WHERE status = @status AND created_at >= @startDate';
SET @params = N'@status VARCHAR(50), @startDate DATE';

EXEC sp_executesql @sql, @params,
    @status = @filterStatus,
    @startDate = @filterDate;
```

### Avoid Embedding Credentials

Never store connection strings, passwords, or API keys in stored procedure code. Use database-level security, linked server credentials, or externalized configuration.

```sql
-- ❌ BAD: Hardcoded credentials
EXEC('SELECT * FROM OPENROWSET(''SQLNCLI'', ''Server=prod;Uid=admin;Pwd=secret123;'',...)')

-- ✅ GOOD: Use linked server with managed credentials
SELECT * FROM [LinkedServerName].database.schema.table;
```

---

## Stored Procedure Checklist

- [ ] Header comment with description, parameters, and return values
- [ ] `SET NOCOUNT ON` at the start
- [ ] Required parameters listed before optional parameters
- [ ] All parameters validated before use
- [ ] TRY/CATCH wrapping business logic
- [ ] Transactions explicitly begun and committed
- [ ] `ROLLBACK` in CATCH block when `@@TRANCOUNT > 0`
- [ ] Standardized error codes and messages
- [ ] Dynamic SQL uses `sp_executesql` with parameters
- [ ] No embedded credentials
- [ ] Batch processing for large data operations
- [ ] Temp tables cleaned up
