---
description: "Template for creating or modifying MCP (Model Context Protocol) servers."
---

# MCP Server Development Prompt

Use this prompt template when asking AI to create or modify MCP (Model Context Protocol) servers.

## Context Template

```
I need to create/modify an MCP server for [PURPOSE].

## Environment
- Language: Python 3.11+
- Framework: FastMCP / MCP Python SDK
- Target: VS Code Copilot / Claude Code / Cursor

## Required Capabilities
[List the tools/resources this MCP should provide]

## Integration Points
- [External API / Database / Service to connect to]
- Authentication method: [API key / OAuth / Connection string]

## Constraints
- [Air-gapped: Must work offline]
- [Security: No credential exposure]
- [Performance: Response time requirements]
```

## Example: Database MCP

```
I need to create an MCP server for SQL Server database access.

## Environment
- Language: Python 3.11+
- Framework: FastMCP
- Target: VS Code Copilot Chat

## Required Capabilities
- query_database: Execute read-only SQL queries
- get_schema: Retrieve table schemas
- list_tables: Show available tables
- get_sample_data: Get sample rows from a table

## Integration Points
- SQL Server via pyodbc
- Connection string from environment variables

## Constraints
- Read-only queries only (no INSERT/UPDATE/DELETE)
- Query timeout: 30 seconds
- Result limit: 1000 rows
- No credential logging
```

## Expected Output Structure

```python
from mcp import FastMCP
from pydantic import BaseModel
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Environment configuration"""
    db_server: str
    db_name: str
    db_user: str
    db_password: str
    
    class Config:
        env_prefix = "DB_"

# Initialize MCP server
mcp = FastMCP("<APP_NAME>-database")
settings = Settings()

@mcp.tool()
def query_database(sql: str) -> dict:
    """Execute a read-only SQL query and return results"""
    # Implementation
    pass

@mcp.tool()
def get_schema(table_name: str) -> dict:
    """Get the schema for a specific table"""
    # Implementation
    pass

@mcp.resource("schema://tables")
def list_tables() -> str:
    """List all available tables in the database"""
    # Implementation
    pass

if __name__ == "__main__":
    mcp.run()
```

## Configuration Template

After creating the MCP server, configure it in `.vscode/mcp.json`:

```json
{
  "servers": {
    "server-name": {
      "command": "python",
      "args": ["path/to/server.py"],
      "env": {
        "API_KEY": "${env:API_KEY}"
      }
    }
  }
}
```

## Usage in Chat

Once configured:
```
@server-name What tables are available in the database?
@server-name Query the top 10 customers by order count
```
