---
description: "Python coding conventions and guidelines"
applyTo: "**/*.py"
---

# Python Coding Standards

## CRITICAL: Path Handling (Portability)

**NEVER use absolute paths.** All code must be portable and work when copied to any location.

```python
from pathlib import Path

# ✅ CORRECT: Relative to script location
PROJECT_ROOT = Path(__file__).parent.parent  # adjust .parent count based on file depth
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "config.json"

# ❌ WRONG: Absolute paths break portability
DATA_DIR = Path("E:\\Projects\\MyApp\\data")  # NEVER DO THIS
CONFIG_PATH = "/home/user/app/config.json"   # NEVER DO THIS
```

**Standard path resolution pattern:**

```python
from pathlib import Path

# Get paths relative to current file
CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parent.parent  # from src/services/file.py → project root

# Common directories
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
STATIC_DIR = PROJECT_ROOT / "static"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
```

See `portability.instructions.md` for complete guidelines.

---

## Code Style

### PEP 8 Compliance
- Follow PEP 8 style guide
- Line length: 100 characters maximum
- Use 4 spaces for indentation (no tabs)
- Two blank lines between top-level definitions
- One blank line between method definitions

### Imports

Organize imports in three groups, alphabetically within each:

```python
# 1. Standard library
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# 2. Third-party packages
import pandas as pd
import streamlit as st
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

# 3. Local imports
from <SHARED_LIBS>.theme import apply_theme        # from project-config.md
from <SHARED_LIBS>.adapters import DatabaseAdapter  # from project-config.md
from config import settings
```

### Type Hints

Use type hints on all functions:

```python
# ✅ GOOD: Full type hints
def get_complaints(
    status: str,
    limit: int = 100,
    include_resolved: bool = False
) -> pd.DataFrame:
    """Fetch complaints from database."""
    ...

# ❌ BAD: No type hints
def get_complaints(status, limit=100, include_resolved=False):
    ...
```

### Docstrings (PEP 257)

```python
def calculate_sla_compliance(
    complaints: pd.DataFrame,
    sla_hours: int = 48
) -> float:
    """Calculate SLA compliance rate for complaints.
    
    Args:
        complaints: DataFrame with complaint records.
        sla_hours: SLA target in hours. Defaults to 48.
        
    Returns:
        Compliance rate as percentage (0-100).
        
    Raises:
        ValueError: If complaints DataFrame is empty.
        
    Example:
        >>> df = load_complaints()
        >>> rate = calculate_sla_compliance(df, sla_hours=24)
        >>> print(f"SLA Compliance: {rate:.1f}%")
    """
    if complaints.empty:
        raise ValueError("Cannot calculate SLA for empty DataFrame")
    ...
```

### Naming Conventions

```python
# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_PAGE_SIZE = 50
BRAND_PRIMARY_COLOR = "<BRAND_PRIMARY>"  # from project-config.md

# Variables and functions: snake_case
customer_id = "CUST001"
def get_customer_name(customer_id: str) -> str:
    ...

# Classes: PascalCase
class ComplaintRepository:
    ...

class CustomerNotFoundException(Exception):
    ...

# Private members: leading underscore
class DataProcessor:
    def __init__(self):
        self._cache = {}
    
    def _validate_input(self, data: dict) -> bool:
        ...
```

### Error Handling

```python
# ✅ GOOD: Specific exceptions with logging
from loguru import logger

def fetch_complaint(complaint_id: str) -> Complaint:
    """Fetch complaint by ID."""
    try:
        result = adapter.fetch_one(query, (complaint_id,))
        if not result:
            raise ComplaintNotFoundError(f"Complaint {complaint_id} not found")
        return Complaint(**result)
    except pyodbc.Error as e:
        logger.error(f"Database error fetching complaint {complaint_id}: {e}")
        raise DatabaseError(f"Failed to fetch complaint: {e}") from e

# ❌ BAD: Bare except, silent failure
def fetch_complaint(complaint_id):
    try:
        result = adapter.fetch_one(query, (complaint_id,))
        return result
    except:
        return None
```

### Resource Cleanup (Context Managers)

Always use context managers for resources that need cleanup. Manual `connect()`/`disconnect()` calls leak on exceptions.

```python
# ✅ GOOD: Context manager ensures cleanup on both success and error
with get_connection() as conn:
    result = conn.execute(query)

# ❌ BAD: Manual connect/disconnect leaks on exception
conn = get_connection()
conn.connect()
result = conn.execute(query)  # If this throws...
conn.disconnect()              # ...this never runs
```

**Rule:** If a class has `connect()`/`disconnect()` or `open()`/`close()` methods, prefer its context manager (`with` statement) or wrap in `try/finally`.

### Logging

Use loguru, never print():

```python
from loguru import logger

# Configure at app startup
logger.add(
    "logs/{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)

# Use throughout code
logger.debug(f"Fetching data for customer {customer_id}")
logger.info(f"Processed {len(records)} records")
logger.warning(f"Cache miss for key {cache_key}")
logger.error(f"Failed to connect to database: {e}")
```

### Configuration

Use pydantic-settings for configuration:

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    app_name: str = "<APP_TITLE>"  # from project-config.md
    debug: bool = False
    
    # Database
    db_host: str
    db_port: int = 1433
    db_name: str
    db_user: str
    db_password: str = Field(..., repr=False)  # Hide in logs
    
    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### Pydantic Field Defaults

```python
from pydantic import BaseModel, Field
from datetime import datetime

# ❌ BAD: default=fn() evaluates ONCE at class definition time
class Record(BaseModel):
    created_at: datetime = Field(default=datetime.now())  # Same timestamp for ALL instances!

# ✅ GOOD: default_factory=fn evaluates per-instance
class Record(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)  # Fresh timestamp each time
```

**Rule:** Use `default_factory` (no parentheses) for any default that should be computed fresh per instance. Use `default` only for immutable constants (`str`, `int`, `None`).

## Project-Specific Patterns

### Use Shared Libraries

Always check shared library paths (from `project-config.md`) before creating new:

```python
# ✅ GOOD: Use existing components
from <SHARED_LIBS>.theme import apply_theme        # from project-config.md
from <SHARED_LIBS>.components import render_header  # from project-config.md
from <SHARED_LIBS>.adapters import DatabaseAdapter   # from project-config.md

# ❌ BAD: Duplicate existing functionality
def my_custom_header(title):
    st.markdown(f"<h1>{title}</h1>", unsafe_allow_html=True)
```

### Database Access Pattern

```python
from <SHARED_LIBS>.adapters import DatabaseAdapter  # from project-config.md

# Use parameterized queries
adapter = DatabaseAdapter()

# ✅ GOOD: Parameterized
query = "SELECT * FROM complaints WHERE status = ? AND priority <= ?"
results = adapter.fetch_dataframe(query, (status, max_priority))

# ❌ BAD: SQL Injection risk
query = f"SELECT * FROM complaints WHERE status = '{status}'"
```

### Async Pattern (for FastAPI)

```python
from <SHARED_LIBS>.adapters import AsyncDatabaseAdapter  # from project-config.md

async def get_complaints_async(status: str) -> list[dict]:
    """Fetch complaints asynchronously."""
    adapter = AsyncDatabaseAdapter()
    async with adapter.get_connection() as conn:
        result = await conn.fetch_all(query, (status,))
    return result
```

## Function Design

### Keep Functions Small and Focused

Break complex functions into smaller, composable pieces:

```python
# ❌ BAD: One monolithic function doing too much
def process_complaints(raw_data: list[dict]) -> pd.DataFrame:
    # 50+ lines of validation, transformation, aggregation, and formatting
    ...

# ✅ GOOD: Decomposed into focused functions
def process_complaints(raw_data: list[dict]) -> pd.DataFrame:
    """Process raw complaint data into a clean DataFrame."""
    validated = _validate_complaint_data(raw_data)
    transformed = _transform_complaint_records(validated)
    return _apply_business_rules(transformed)
```

### Document Design Decisions

When a non-obvious approach is chosen, explain **why** in comments:

```python
# We use a dict lookup instead of if/elif chain because the mapping
# changes per-tenant and is loaded from config at startup.
STATUS_MAP: dict[str, str] = load_status_mapping(settings.tenant)
```

---

## Testing

### Write Tests for Critical Paths

```python
import pytest

def test_sla_compliance_returns_zero_for_all_breached():
    """All complaints past SLA should yield 0% compliance."""
    complaints = pd.DataFrame({
        "created_at": [datetime(2024, 1, 1)],
        "resolved_at": [datetime(2024, 1, 10)],
    })
    assert calculate_sla_compliance(complaints, sla_hours=24) == 0.0

def test_sla_compliance_raises_on_empty_dataframe():
    """Empty input should raise ValueError, not silently return."""
    with pytest.raises(ValueError, match="empty"):
        calculate_sla_compliance(pd.DataFrame(), sla_hours=24)
```

### Edge Case Coverage

Always account for:
- **Empty inputs**: empty lists, empty DataFrames, blank strings
- **None/null values**: missing fields, optional parameters
- **Boundary values**: zero, negative numbers, maximum sizes
- **Invalid types**: wrong data types passed to public functions

```python
@pytest.mark.parametrize("bad_input", [None, "", "   ", 0, -1])
def test_get_customer_rejects_invalid_id(bad_input):
    with pytest.raises((ValueError, TypeError)):
        get_customer(bad_input)
```

### Test Organization

- Use `pytest` as the test framework
- Name test files `test_<module>.py`
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Follow Arrange-Act-Assert pattern
- Mock external dependencies (database, APIs), not domain logic

---

## Code Quality Checks

Run before committing:

```powershell
# Format code
black .

# Lint
ruff check .

# Type checking
mypy .

# All checks
ruff check . && black --check . && mypy .
```

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values. The profile defines `<LOGGING_LIB>`, `<SHARED_LIBS>`, `<DB_TYPE>`, and other project-specific tokens.
