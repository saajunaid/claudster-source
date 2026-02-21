---
description: "Code portability and location-agnostic patterns for all projects"
applyTo: "**/*"
---

# Code Portability Standards

All code must be **location-agnostic** and portable. Projects should work when copied to any machine or directory.

## Critical Rules

### NEVER Use Absolute Paths

```python
# ❌ NEVER DO THIS - Hardcoded paths break portability
config_path = "<PROJECT_ROOT>/config.json"
data_file = "C:\\Users\\john\\data\\complaints.csv"
log_path = "/home/user/app/logs/app.log"

# ✅ ALWAYS DO THIS - Relative to script location
from pathlib import Path

# Get project root relative to current file
PROJECT_ROOT = Path(__file__).parent.parent  # adjust .parent based on file depth
config_path = PROJECT_ROOT / "config.json"
data_file = PROJECT_ROOT / "data" / "complaints.csv"
log_path = PROJECT_ROOT / "logs" / "app.log"
```

### Path Resolution Patterns

#### For Python Files

```python
from pathlib import Path

# Current file's directory
CURRENT_DIR = Path(__file__).parent

# Project root (from src/package/module.py → project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Common paths
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
```

#### For Config Files (config.py)

```python
"""
Configuration module with portable path resolution.
"""
from pathlib import Path
from dotenv import load_dotenv
import os

# Resolve paths relative to this file's location
CONFIG_DIR = Path(__file__).parent
PROJECT_ROOT = CONFIG_DIR.parent if CONFIG_DIR.name == "src" else CONFIG_DIR

# Load .env from project root
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

# All paths relative to project root
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
STATIC_DIR = PROJECT_ROOT / "static"
```

### Environment-Specific Values

Use `.env` files for machine-specific configuration:

```python
# ❌ NEVER hardcode machine-specific values
DB_HOST = "192.168.1.100"
LOG_PATH = "E:\\Logs\\app.log"

# ✅ ALWAYS use environment variables
import os
DB_HOST = os.getenv("DB_HOST", "localhost")
LOG_PATH = os.getenv("LOG_PATH", str(LOGS_DIR / "app.log"))
```

### Windows UNC Path Handling

UNC paths (`\\server\share\folder`) require special handling in `.env` files and Python:

```env
# .env file — use single backslashes (dotenv handles them literally)
NETWORK_PATH=\\server\share\incoming_raw

# ❌ WRONG: Double-escaping in .env creates literal double backslashes
NETWORK_PATH=\\\\server\\share\\incoming_raw
```

```python
from pathlib import Path
import os

# ✅ GOOD: Use Path() for UNC — handles backslashes correctly
unc_path = Path(os.getenv("NETWORK_PATH", r"\\server\share\default"))

# ✅ GOOD: Validate UNC path exists before use
if unc_path.exists():
    files = list(unc_path.glob("*.json"))
else:
    logger.warning(f"UNC path not accessible: {unc_path}")
```

**Rule:** UNC paths from environment variables should use single backslashes in `.env`. Python code should use `Path()` or raw strings, never manual string escaping.

### .env.example Template

Always include a template with relative defaults:

```env
# Application
APP_NAME=MyApp
DEBUG=true

# Database (machine-specific - update per environment)
DB_HOST=localhost
DB_PORT=1433
DB_NAME=mydb
DB_USER=
DB_PASSWORD=

# Paths (optional - defaults to relative paths if not set)
# LOG_PATH=logs/app.log
# DATA_PATH=data/
```

## Import Path Handling

### Do NOT modify sys.path with absolute paths

```python
# ❌ BAD - Hardcoded absolute path
sys.path.insert(0, "E:\\WorkProjects\\libs")

# ✅ GOOD - Relative path resolution
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "libs"))
```

### Better: Use proper package structure

```python
# ✅ BEST - Install as editable package
# In pyproject.toml or setup.py, then:
# pip install -e .

# Then import normally
from mypackage.utils import helper_function
```

## File Operations

### Reading Files

```python
from pathlib import Path

def load_data(filename: str) -> pd.DataFrame:
    """Load data file from project's data directory."""
    data_dir = Path(__file__).parent.parent / "data"
    file_path = data_dir / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    return pd.read_csv(file_path)
```

### Writing Files

```python
from pathlib import Path

def save_export(df: pd.DataFrame, filename: str) -> Path:
    """Save export to project's exports directory."""
    export_dir = Path(__file__).parent.parent / "exports"
    export_dir.mkdir(exist_ok=True)
    
    file_path = export_dir / filename
    df.to_csv(file_path, index=False)
    
    return file_path
```

## Logging Configuration

```python
from pathlib import Path
from loguru import logger

# Configure logging with relative paths
PROJECT_ROOT = Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger.add(
    LOG_DIR / "app.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)
```

## Database Connection Strings

```python
import os
from pathlib import Path

# SQLite - relative path
PROJECT_ROOT = Path(__file__).parent.parent
SQLITE_PATH = PROJECT_ROOT / "data" / "app.db"
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

# Other databases - from environment
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_NAME = os.getenv("DB_NAME", "mydb")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Build connection string
MSSQL_URL = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
```

## Streamlit Apps

```python
import streamlit as st
from pathlib import Path

# Resolve paths relative to the app file
APP_DIR = Path(__file__).parent
PROJECT_ROOT = APP_DIR.parent if APP_DIR.name == "src" else APP_DIR

# Load assets with relative paths
LOGO_PATH = PROJECT_ROOT / "static" / "logo.png"
if LOGO_PATH.exists():
    st.image(str(LOGO_PATH))

# Load data
DATA_PATH = PROJECT_ROOT / "data" / "sample.csv"
df = pd.read_csv(DATA_PATH)
```

## Testing for Portability

Before committing, verify:

1. **No hardcoded paths**: `grep -r "C:\\" --include="*.py"` should return nothing
2. **No username in paths**: `grep -r "$USER" --include="*.py"` should return nothing
3. **Path resolution**: All paths use `Path(__file__)` or environment variables

## Checklist

When writing code, always ask:
- [ ] Will this work if copied to another directory?
- [ ] Will this work on a different machine?
- [ ] Will this work on Linux/Mac (if applicable)?
- [ ] Are all machine-specific values in `.env`?
- [ ] Do I use `Path(__file__)` for file locations?

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values.
