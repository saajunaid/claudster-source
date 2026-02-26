---
description: "MCP (Model Context Protocol) server development guidelines"
applyTo: "**/*mcp*.py"
---

# MCP Server Development Guidelines

Standards for building Model Context Protocol servers using FastMCP for tool integration.

## Overview

MCP servers provide tools, resources, and prompts that can be used by AI assistants. They enable:

- **Tools**: Functions the AI can call (database queries, file operations, API calls)
- **Resources**: Data the AI can access (files, database records, configurations)
- **Prompts**: Reusable prompt templates with parameters

---

## Basic Structure

```python
# mcp_server.py
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("<APP_NAME>-tools")

@mcp.tool()
def query_complaints(
    customer_id: str,
    status: str | None = None
) -> list[dict]:
    """
    Query complaints from the database.
    
    Args:
        customer_id: Customer ID to filter by
        status: Optional status filter (open, closed, pending)
    
    Returns:
        List of complaint records
    """
    from <SHARED_LIBS>.data import DatabaseAdapter
    
    adapter = DatabaseAdapter()
    query = "SELECT * FROM complaints WHERE customer_id = ?"
    params = [customer_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    return adapter.fetch_records(query, params)

if __name__ == "__main__":
    mcp.run()
```

---

## Tool Definition

### Basic Tool

```python
@mcp.tool()
def get_customer_info(customer_id: str) -> dict:
    """
    Retrieve customer information by ID.
    
    Args:
        customer_id: The unique customer identifier (e.g., CUST001)
    
    Returns:
        Customer record with name, email, and account status
    """
    adapter = DatabaseAdapter()
    result = adapter.fetch_one(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    )
    
    if not result:
        return {"error": f"Customer {customer_id} not found"}
    
    return result
```

### Tool with Complex Parameters

```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import date

class ComplaintFilter(BaseModel):
    """Filter parameters for complaint search."""
    status: Literal["open", "closed", "pending"] | None = None
    priority: int | None = Field(None, ge=1, le=5)
    start_date: date | None = None
    end_date: date | None = None

@mcp.tool()
def search_complaints(
    customer_id: str,
    filters: ComplaintFilter | None = None,
    limit: int = 50
) -> list[dict]:
    """
    Search complaints with advanced filtering.
    
    Args:
        customer_id: Customer ID to search
        filters: Optional filter criteria
        limit: Maximum number of results (default 50)
    
    Returns:
        List of matching complaint records
    """
    query = "SELECT TOP (?) * FROM complaints WHERE customer_id = ?"
    params = [limit, customer_id]
    
    if filters:
        if filters.status:
            query += " AND status = ?"
            params.append(filters.status)
        if filters.priority:
            query += " AND priority = ?"
            params.append(filters.priority)
        if filters.start_date:
            query += " AND created_at >= ?"
            params.append(filters.start_date)
        if filters.end_date:
            query += " AND created_at <= ?"
            params.append(filters.end_date)
    
    adapter = DatabaseAdapter()
    return adapter.fetch_records(query, params)
```

### Async Tool

```python
import aiohttp

@mcp.tool()
async def fetch_external_data(endpoint: str) -> dict:
    """
    Fetch data from external API.
    
    Args:
        endpoint: API endpoint path (e.g., /api/v1/data)
    
    Returns:
        Response data from the API
    """
    base_url = settings.external_api_url
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}{endpoint}") as response:
            if response.status != 200:
                return {"error": f"API returned status {response.status}"}
            return await response.json()
```

---

## Resource Definition

### Static Resource

```python
@mcp.resource("config://app-settings")
def get_app_settings() -> str:
    """
    Get application configuration settings.
    
    Returns current environment settings as JSON.
    """
    import json
    from app.config import settings
    
    return json.dumps({
        "environment": settings.app_env,
        "database": settings.db_name,
        "llm_model": settings.ollama_model
    })
```

### Dynamic Resource

```python
@mcp.resource("complaint://{complaint_id}")
def get_complaint_resource(complaint_id: str) -> str:
    """
    Get a specific complaint as a resource.
    
    Args:
        complaint_id: Unique complaint identifier
    
    Returns:
        Complaint details as JSON
    """
    import json
    
    adapter = DatabaseAdapter()
    complaint = adapter.fetch_one(
        "SELECT * FROM complaints WHERE id = ?",
        (complaint_id,)
    )
    
    if not complaint:
        return json.dumps({"error": "Complaint not found"})
    
    return json.dumps(complaint)
```

### File Resource

```python
@mcp.resource("file://templates/{template_name}")
def get_template(template_name: str) -> str:
    """
    Get a template file content.
    
    Args:
        template_name: Name of the template file
    
    Returns:
        Template content
    """
    from pathlib import Path
    
    template_path = Path("templates") / template_name
    
    # Security: Prevent path traversal
    if ".." in template_name or not template_path.is_relative_to("templates"):
        return "Error: Invalid template path"
    
    if not template_path.exists():
        return f"Error: Template {template_name} not found"
    
    return template_path.read_text()
```

---

## Prompt Definition

```python
@mcp.prompt()
def analyze_complaint(
    complaint_text: str,
    customer_history: str | None = None
) -> str:
    """
    Generate a prompt for analyzing a customer complaint.
    
    Args:
        complaint_text: The complaint description
        customer_history: Optional history of previous interactions
    
    Returns:
        Formatted analysis prompt
    """
    prompt = f"""Analyze the following customer complaint and provide:
1. Category classification (billing, technical, service)
2. Sentiment analysis (positive, negative, neutral)
3. Priority recommendation (1-5)
4. Suggested resolution approach

Complaint:
{complaint_text}
"""
    
    if customer_history:
        prompt += f"""
Previous Customer Interactions:
{customer_history}
"""
    
    prompt += """
Provide your analysis in a structured format."""
    
    return prompt

@mcp.prompt()
def sql_query_generator(
    table_name: str,
    requirements: str
) -> str:
    """
    Generate a prompt for SQL query generation.
    
    Args:
        table_name: Target table name
        requirements: Natural language requirements
    
    Returns:
        Formatted SQL generation prompt
    """
    return f"""Generate a SQL Server query for the following requirements:

Table: {table_name}
Requirements: {requirements}

Guidelines:
- Use parameterized queries with ? placeholders
- Include appropriate WHERE clauses
- Use proper SQL Server syntax (TOP, GETDATE(), etc.)
- Add appropriate indexes hints if needed

Return only the SQL query, no explanations."""
```

---

## Error Handling

```python
from loguru import logger

@mcp.tool()
def safe_database_query(query_type: str) -> dict:
    """
    Execute a predefined safe database query.
    
    Args:
        query_type: Type of query (summary, details, metrics)
    
    Returns:
        Query results or error information
    """
    ALLOWED_QUERIES = {
        "summary": "SELECT COUNT(*) as count, status FROM complaints GROUP BY status",
        "metrics": "SELECT AVG(priority) as avg_priority FROM complaints",
        "recent": "SELECT TOP 10 * FROM complaints ORDER BY created_at DESC"
    }
    
    if query_type not in ALLOWED_QUERIES:
        logger.warning(f"Invalid query type requested: {query_type}")
        return {
            "error": f"Unknown query type: {query_type}",
            "allowed": list(ALLOWED_QUERIES.keys())
        }
    
    try:
        adapter = DatabaseAdapter()
        result = adapter.fetch_records(ALLOWED_QUERIES[query_type])
        return {"success": True, "data": result}
    
    except ConnectionError as e:
        logger.error(f"Database connection failed: {e}")
        return {"error": "Database connection failed", "retry": True}
    
    except Exception as e:
        logger.exception(f"Query execution failed: {e}")
        return {"error": "Query execution failed"}
```

---

## Security Considerations

### Input Validation

```python
import re

def validate_customer_id(customer_id: str) -> bool:
    """Validate customer ID format."""
    return bool(re.match(r'^CUST\d{3,10}$', customer_id))

@mcp.tool()
def get_customer_complaints(customer_id: str) -> dict:
    """Get complaints for a validated customer ID."""
    if not validate_customer_id(customer_id):
        return {"error": "Invalid customer ID format"}
    
    # Safe to proceed with validated ID
    ...
```

### Parameterized Queries Only

```python
# ❌ NEVER: String concatenation
query = f"SELECT * FROM users WHERE id = '{user_input}'"

# ✅ ALWAYS: Parameterized queries
query = "SELECT * FROM users WHERE id = ?"
result = adapter.fetch_records(query, (user_input,))
```

### Limit Data Exposure

```python
@mcp.tool()
def get_user_public_info(user_id: str) -> dict:
    """Get non-sensitive user information."""
    adapter = DatabaseAdapter()
    
    # Only return public fields, not passwords, tokens, etc.
    result = adapter.fetch_one(
        """SELECT id, name, email, created_at 
           FROM users 
           WHERE id = ?""",
        (user_id,)
    )
    
    return result or {"error": "User not found"}
```

---

## Configuration

### Environment Setup

```python
# config.py
from pydantic_settings import BaseSettings

class MCPSettings(BaseSettings):
    """MCP server configuration."""
    
    db_connection_string: str
    allowed_tables: list[str] = ["complaints", "customers", "metrics"]
    max_query_results: int = 100
    
    class Config:
        env_prefix = "MCP_"
        env_file = ".env"

settings = MCPSettings()
```

### VS Code Configuration

```json
// .vscode/mcp.json
{
  "servers": {
    "<APP_NAME>-tools": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "MCP_DB_CONNECTION_STRING": "${env:DB_CONNECTION_STRING}"
      }
    }
  }
}
```

---

## Testing MCP Servers

```python
# tests/test_mcp_server.py
import pytest
from unittest.mock import patch, MagicMock

# Import the tools directly for testing
from mcp_server import query_complaints, get_customer_info

class TestMCPTools:
    """Tests for MCP server tools."""
    
    @patch("mcp_server.DatabaseAdapter")
    def test_query_complaints_returns_results(self, mock_adapter):
        """Test complaint query returns expected results."""
        mock_instance = MagicMock()
        mock_instance.fetch_records.return_value = [
            {"id": 1, "customer_id": "CUST001", "status": "open"}
        ]
        mock_adapter.return_value = mock_instance
        
        result = query_complaints("CUST001")
        
        assert len(result) == 1
        assert result[0]["customer_id"] == "CUST001"
    
    @patch("mcp_server.DatabaseAdapter")
    def test_get_customer_info_not_found(self, mock_adapter):
        """Test customer info returns error for invalid ID."""
        mock_instance = MagicMock()
        mock_instance.fetch_one.return_value = None
        mock_adapter.return_value = mock_instance
        
        result = get_customer_info("INVALID")
        
        assert "error" in result
```

---

## Checklist

- [ ] All tools have descriptive docstrings with Args/Returns
- [ ] Input validation on all user-provided parameters
- [ ] Parameterized queries for all database operations
- [ ] Error handling with informative error messages
- [ ] Logging for debugging and monitoring
- [ ] No sensitive data in tool responses
- [ ] Tests for each tool function
- [ ] Configuration via environment variables

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values. The profile defines `<APP_NAME>`, `<SHARED_LIBS>`, and other project-specific tokens.
