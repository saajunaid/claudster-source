# Debug Help Prompt

## Purpose

Structure debugging requests to efficiently identify and resolve issues.

## Pipeline Boundary (when used with JUNO pipeline)

If `.github/pipeline-state.json` exists:

- Produce a **diagnostic brief** and a project-ready troubleshooting prompt.
- Do not include pipeline-stage transitions, gate instructions, or pipeline-state edits.
- Do not provide direct handoff routing.
- End with: "Use `@Orchestrator` to route this troubleshooting brief."

## Input Required

- Error message or symptom
- Code context
- What was tried

## Template

```
I need help debugging an issue:

## The Problem
**What's happening**: {symptom_description}

**Expected behavior**: {what_should_happen}

**Error message** (if any):
```
{error_message}
```

## Context

**File/Function**: {location}

**Relevant code**:
```python
{code_snippet}
```

**When it happens**: {trigger_conditions}

**Environment**:
- Python version: {version}
- OS: {os}
- Relevant packages: {packages}

## What I've Tried
1. {attempt_1}
2. {attempt_2}
3. {attempt_3}

## Additional Context
{any_other_info}

Please help me:
1. Identify the root cause
2. Suggest a fix
3. Explain why the issue occurred
```

## Example

### Input

```
I need help debugging an issue:

## The Problem
**What's happening**: Dashboard crashes when loading complaints data

**Expected behavior**: Dashboard should display the complaints table

**Error message**:
```
pyodbc.OperationalError: ('08001', '[08001] [Microsoft][ODBC Driver 17 for SQL Server]
Named Pipes Provider: Could not open a connection to SQL Server [53]. (53)')
```

## Context

**File/Function**: app/pages/dashboard.py, load_complaints_data()

**Relevant code**:
```python
@st.cache_data(ttl=timedelta(minutes=15))
def load_complaints_data():
    adapter = DatabaseAdapter()
    return adapter.fetch_dataframe(
        "SELECT * FROM complaints WHERE status = 'open'"
    )
```

**When it happens**: On first page load, after recent server restart

**Environment**:
- Python version: 3.11.4
- OS: Windows Server 2019
- Relevant packages: pyodbc 4.0.39, streamlit 1.28.0

## What I've Tried
1. Checked SQL Server is running (it is)
2. Tested connection string in SQL Server Management Studio (works)
3. Restarted the Streamlit app

## Additional Context
This was working yesterday. Server was restarted overnight for updates.
```

### Expected Output

```markdown
## Diagnosis

The error `[08001] Named Pipes Provider: Could not open a connection` 
indicates the application cannot establish a network connection to SQL Server.

### Likely Causes (in order of probability)

1. **SQL Server Network Configuration Changed**
   - After restart, SQL Server may have disabled TCP/IP protocol
   - Named Pipes may be disabled

2. **Firewall Blocking Connection**
   - Windows Firewall rules may have reset after update

3. **SQL Server Browser Service Not Running**
   - Required for named instance connections

### Troubleshooting Steps

**Step 1: Check SQL Server Configuration Manager**
```
1. Open SQL Server Configuration Manager
2. Go to SQL Server Network Configuration
3. Verify TCP/IP is Enabled
4. Verify the correct port (default 1433)
```

**Step 2: Check SQL Server Browser Service**
```powershell
Get-Service -Name SQLBrowser
# If stopped:
Start-Service -Name SQLBrowser
```

**Step 3: Check Firewall**
```powershell
# Check if SQL Server port is open
Test-NetConnection -ComputerName SQLSERVER01 -Port 1433
```

**Step 4: Verify Connection String**

Your connection string should explicitly use TCP/IP:
```python
# In .env or config
DB_SERVER=tcp:SQLSERVER01,1433  # Explicit TCP with port
```

### Quick Fix

Try updating your DatabaseAdapter connection to use explicit TCP:

```python
# In <SHARED_LIBS>/adapter.py
connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER=tcp:{settings.db_server},1433;"  # Explicit TCP
    f"DATABASE={settings.db_name};"
    f"UID={settings.db_user};"
    f"PWD={settings.db_password};"
)
```

### Prevention

Add connection retry logic:

```python
import time
from loguru import logger

def get_connection(max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            return pyodbc.connect(connection_string)
        except pyodbc.OperationalError as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    raise ConnectionError("Failed to connect to database after retries")
```
```

## Tips for Effective Debugging Requests

1. **Include the full error message** - Stack traces are helpful
2. **Show relevant code** - Not too much, not too little
3. **Describe what changed** - "It was working until..."
4. **List what you tried** - Prevents redundant suggestions
5. **Include environment details** - Versions matter
