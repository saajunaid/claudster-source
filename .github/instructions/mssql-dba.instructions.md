---
description: "SQL Server DBA administration, maintenance, and troubleshooting guidelines"
applyTo: "**/*.sql"
---

# SQL Server DBA Guidelines

DBA-focused operations: server configuration, maintenance, monitoring, security, HA, and troubleshooting. For SQL coding conventions and query style, see `sql.instructions.md`.

---

## Server Configuration and Tuning

### Memory

```sql
-- Set max server memory (leave 4GB+ for OS on dedicated server)
EXEC sp_configure 'max server memory (MB)', 28672;  -- 28GB on a 32GB server
RECONFIGURE;

-- Check current memory usage
SELECT
    physical_memory_in_use_kb / 1024 AS memory_used_mb,
    locked_page_allocations_kb / 1024 AS locked_pages_mb,
    total_virtual_address_space_kb / 1024 AS virtual_space_mb
FROM sys.dm_os_process_memory;
```

### TempDB

```sql
-- TempDB best practice: one data file per logical CPU core (up to 8),
-- all equal size, on fast storage separate from user databases
ALTER DATABASE tempdb ADD FILE (
    NAME = tempdev2, FILENAME = 'T:\TempDB\tempdev2.ndf', SIZE = 8192MB, FILEGROWTH = 1024MB
);
-- Repeat for each additional file. Keep all files the same size.
```

### Max Degree of Parallelism (MAXDOP)

```sql
-- General guidance: set to number of cores per NUMA node (max 8)
EXEC sp_configure 'max degree of parallelism', 4;
EXEC sp_configure 'cost threshold for parallelism', 50;  -- raise from default 5
RECONFIGURE;
```

---

## Backup and Restore Strategies

### Full + Differential + Log Backup Pattern

```sql
-- Full backup (weekly or nightly depending on size)
BACKUP DATABASE [MyDatabase] TO DISK = 'D:\Backups\MyDatabase_FULL.bak'
    WITH COMPRESSION, CHECKSUM, INIT, FORMAT;

-- Differential backup (every 4-6 hours between fulls)
BACKUP DATABASE [MyDatabase] TO DISK = 'D:\Backups\MyDatabase_DIFF.bak'
    WITH DIFFERENTIAL, COMPRESSION, CHECKSUM, INIT;

-- Transaction log backup (every 15-30 min for point-in-time recovery)
BACKUP LOG [MyDatabase] TO DISK = 'D:\Backups\MyDatabase_LOG.trn'
    WITH COMPRESSION, CHECKSUM;
```

### Restore Sequence

```sql
-- 1. Full → 2. Latest Diff → 3. All Logs after Diff
RESTORE DATABASE [MyDatabase] FROM DISK = 'D:\Backups\MyDatabase_FULL.bak'
    WITH NORECOVERY, REPLACE;
RESTORE DATABASE [MyDatabase] FROM DISK = 'D:\Backups\MyDatabase_DIFF.bak'
    WITH NORECOVERY;
RESTORE LOG [MyDatabase] FROM DISK = 'D:\Backups\MyDatabase_LOG.trn'
    WITH RECOVERY;  -- RECOVERY on last step only
```

### Verify Backups

```sql
-- Always verify after backup
RESTORE VERIFYONLY FROM DISK = 'D:\Backups\MyDatabase_FULL.bak' WITH CHECKSUM;
```

---

## Database Maintenance

### Index Maintenance

```sql
-- Find fragmented indexes (>30% = rebuild, 10-30% = reorganize)
SELECT
    OBJECT_NAME(ips.object_id) AS table_name,
    i.name AS index_name,
    ips.avg_fragmentation_in_percent,
    ips.page_count
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
WHERE ips.avg_fragmentation_in_percent > 10 AND ips.page_count > 1000
ORDER BY ips.avg_fragmentation_in_percent DESC;

-- Rebuild (offline or online for Enterprise)
ALTER INDEX [IX_MyIndex] ON [dbo].[MyTable] REBUILD WITH (ONLINE = ON, MAXDOP = 4);

-- Reorganize (always online, less resource-intensive)
ALTER INDEX [IX_MyIndex] ON [dbo].[MyTable] REORGANIZE;
```

### Statistics Updates

```sql
-- Update statistics with full scan for critical tables
UPDATE STATISTICS [dbo].[MyTable] WITH FULLSCAN;

-- Update all statistics in a database (after maintenance window)
EXEC sp_updatestats;
```

### Integrity Checks

```sql
-- Run DBCC CHECKDB weekly (at minimum) in maintenance window
DBCC CHECKDB ('MyDatabase') WITH NO_INFOMSGS, ALL_ERRORMSGS, DATA_PURITY;

-- Lighter check for large databases (daily)
DBCC CHECKALLOC ('MyDatabase') WITH NO_INFOMSGS;
DBCC CHECKCATALOG ('MyDatabase') WITH NO_INFOMSGS;
```

---

## Security

### Authentication Preference

Use Windows Authentication when possible; avoid SQL logins unless necessary for cross-domain or application-specific access.

### Contained Database Users (Portable)

```sql
-- Enable contained databases at server level
EXEC sp_configure 'contained database authentication', 1;
RECONFIGURE;

-- Create a contained user (no server-level login needed)
ALTER DATABASE [MyDatabase] SET CONTAINMENT = PARTIAL;
USE [MyDatabase];
CREATE USER [AppUser] WITH PASSWORD = 'StrongP@ssw0rd!';
```

### Role-Based Access

```sql
-- Create application-specific roles instead of granting permissions directly
CREATE ROLE [app_reader];
GRANT SELECT ON SCHEMA::dbo TO [app_reader];

CREATE ROLE [app_writer];
GRANT SELECT, INSERT, UPDATE ON SCHEMA::dbo TO [app_writer];

-- Assign users to roles
ALTER ROLE [app_reader] ADD MEMBER [ReportingUser];
ALTER ROLE [app_writer] ADD MEMBER [AppUser];

-- Never grant db_owner to application accounts
```

### Auditing

```sql
-- Create a server audit
CREATE SERVER AUDIT [SecurityAudit]
    TO FILE (FILEPATH = 'D:\Audits\', MAXSIZE = 512 MB, MAX_ROLLOVER_FILES = 10);

CREATE SERVER AUDIT SPECIFICATION [LoginAuditSpec]
    FOR SERVER AUDIT [SecurityAudit]
    ADD (FAILED_LOGIN_GROUP),
    ADD (LOGIN_CHANGE_PASSWORD_GROUP);

ALTER SERVER AUDIT [SecurityAudit] WITH (STATE = ON);
```

---

## Monitoring with DMVs

### Top Expensive Queries

```sql
SELECT TOP 20
    qs.total_elapsed_time / qs.execution_count AS avg_elapsed_us,
    qs.execution_count,
    qs.total_logical_reads / qs.execution_count AS avg_reads,
    SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
        ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(st.text)
          ELSE qs.statement_end_offset END - qs.statement_start_offset)/2)+1) AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY qs.total_elapsed_time DESC;
```

### Blocking and Lock Waits

```sql
-- Current blocking chains
SELECT
    blocking.session_id AS blocking_session,
    blocked.session_id AS blocked_session,
    blocked.wait_type,
    blocked.wait_time / 1000 AS wait_seconds,
    st.text AS blocking_query
FROM sys.dm_exec_requests blocked
JOIN sys.dm_exec_sessions blocking ON blocked.blocking_session_id = blocking.session_id
CROSS APPLY sys.dm_exec_sql_text(blocking.most_recent_sql_handle) st
WHERE blocked.blocking_session_id <> 0;
```

### Wait Statistics (Top Waits)

```sql
SELECT TOP 15
    wait_type,
    wait_time_ms / 1000 AS wait_seconds,
    signal_wait_time_ms / 1000 AS signal_wait_seconds,
    waiting_tasks_count,
    wait_time_ms * 100.0 / SUM(wait_time_ms) OVER() AS pct
FROM sys.dm_os_wait_stats
WHERE wait_type NOT IN (
    'SLEEP_TASK','BROKER_TO_FLUSH','SQLTRACE_BUFFER_FLUSH',
    'CLR_AUTO_EVENT','CLR_MANUAL_EVENT','LAZYWRITER_SLEEP',
    'CHECKPOINT_QUEUE','WAITFOR','XE_TIMER_EVENT','BROKER_EVENTHANDLER',
    'FT_IFTS_SCHEDULER_IDLE_WAIT','XE_DISPATCHER_WAIT','DIRTY_PAGE_POLL'
)
ORDER BY wait_time_ms DESC;
```

### Deadlock Detection

```sql
-- Enable deadlock trace flag (if Extended Events not configured)
DBCC TRACEON(1222, -1);  -- logs deadlock graphs to error log

-- Or use Extended Events (preferred)
CREATE EVENT SESSION [DeadlockCapture] ON SERVER
    ADD EVENT sqlserver.xml_deadlock_report
    ADD TARGET package0.event_file (SET filename = N'D:\XEvents\Deadlocks.xel');
ALTER EVENT SESSION [DeadlockCapture] ON SERVER STATE = START;
```

---

## High Availability Overview

### Always On Availability Groups

- Use synchronous commit for zero-data-loss failover within the same data center
- Use asynchronous commit for disaster recovery across data centers
- Monitor with `sys.dm_hadr_availability_replica_states` and `sys.dm_hadr_database_replica_states`
- Test failover regularly in non-production environments

### Log Shipping (Simpler Alternative)

- Good for read-only secondary and DR; no Enterprise license required
- Monitor `log_shipping_monitor_history_detail` for backup/restore lag
- Typical schedule: backup every 15 min, copy/restore every 15 min

### Replication

- **Transactional**: near real-time, best for reporting replicas
- **Merge**: bidirectional sync, use sparingly (conflict resolution complexity)
- **Snapshot**: periodic full refresh, suitable for small reference data

---

## Deprecated Features and Upgrade Awareness

### Avoid Deprecated Syntax

```sql
-- ❌ Deprecated: old-style outer join
SELECT * FROM orders, customers WHERE orders.cust_id *= customers.id;

-- ✅ Use standard ANSI JOIN
SELECT * FROM orders LEFT JOIN customers ON orders.cust_id = customers.id;

-- ❌ Deprecated: RAISERROR with format string
RAISERROR 50001 'Something failed';

-- ✅ Use modern THROW or RAISERROR syntax
THROW 50001, 'Something failed', 1;
```

### Before Upgrading

- Run `SELECT * FROM sys.dm_db_persisted_sku_features` to check edition-specific features in use
- Check compatibility level: `SELECT name, compatibility_level FROM sys.databases`
- Test with Query Store enabled on lower compat level first to catch plan regressions
- Review deprecated features: `SELECT * FROM sys.dm_os_performance_counters WHERE counter_name = 'Deprecated Features'`

---

## Connection Troubleshooting

### Named Instances

- Default instance: `SERVER_NAME` (port 1433)
- Named instance: `SERVER_NAME\INSTANCE_NAME` (dynamic port via SQL Browser)
- Ensure SQL Browser service is running for named instances
- Check firewall allows UDP 1434 (Browser) and the instance TCP port

### ODBC / Python Connection Strings

```python
# Windows Authentication
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=myserver\\SQLEXPRESS;"
    "DATABASE=MyDatabase;"
    "Trusted_Connection=yes;"
)

# SQL Authentication
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=myserver,1433;"
    "DATABASE=MyDatabase;"
    "UID=myuser;PWD=mypassword;"
)
```

### Common Connection Failures

| Symptom | Check |
|---------|-------|
| "Cannot connect to server" | SQL Server service running? Firewall open? |
| "Login failed for user" | Correct credentials? User mapped to database? |
| "Named Pipes Provider" error | Enable TCP/IP in SQL Configuration Manager |
| Timeout on named instance | SQL Browser service running? UDP 1434 open? |
| "Certificate not trusted" | Add `TrustServerCertificate=yes` or install cert |

---

## Quick Reference: Daily DBA Checks

1. **Backup status** — Verify last full/diff/log backup completed for all databases
2. **Disk space** — Check data, log, tempdb, and backup drives
3. **Error log** — Review SQL Server and Agent error logs for failures
4. **Job history** — Confirm maintenance and ETL jobs succeeded
5. **Blocking** — Check for long-running blocking chains during business hours
6. **AG/Log Shipping health** — Verify replicas are synchronized and lag is acceptable
