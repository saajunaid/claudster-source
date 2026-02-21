---
description: "Security best practices based on OWASP Top 10"
applyTo: "**/*"
---

# Security Guidelines

Based on OWASP Top 10 and security best practices for Python, SQL Server, and web applications.

## Core Principle

**Security First**: When in doubt, choose the more secure option. All code should be secure by default.

---

## A01: Broken Access Control

### Principle of Least Privilege

```python
# ✅ GOOD: Check specific permissions
def get_complaint(complaint_id: str, user: User) -> Complaint:
    complaint = repo.get(complaint_id)
    
    if not user.can_view_complaint(complaint):
        raise ForbiddenError("Not authorized to view this complaint")
    
    return complaint

# ❌ BAD: No access control
def get_complaint(complaint_id: str) -> Complaint:
    return repo.get(complaint_id)
```

### Deny by Default

```python
# ✅ GOOD: Explicit allow list
ALLOWED_ROLES = {"admin", "analyst", "viewer"}

def check_role(user_role: str) -> bool:
    return user_role in ALLOWED_ROLES

# ❌ BAD: Blacklist approach
BLOCKED_ROLES = {"guest"}

def check_role(user_role: str) -> bool:
    return user_role not in BLOCKED_ROLES
```

---

## A02: Cryptographic Failures

### Never Hardcode Secrets

```python
# ❌ CRITICAL: Hardcoded credentials
DB_PASSWORD = "super_secret_123"
API_KEY = "sk-abc123xyz"

# ✅ GOOD: Environment variables
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_password: str = Field(..., repr=False)  # Hide in logs
    api_key: str = Field(..., repr=False)
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Secure Password Hashing

```python
# ✅ GOOD: Use bcrypt or argon2
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ❌ BAD: Weak hashing
import hashlib
def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()  # NEVER USE MD5
```

---

## A03: Injection

### SQL Injection Prevention (CRITICAL)

```python
# ❌ CRITICAL VULNERABILITY: SQL Injection
query = f"SELECT * FROM users WHERE id = '{user_input}'"
query = "SELECT * FROM users WHERE id = " + user_input

# ✅ GOOD: Parameterized queries
query = "SELECT * FROM users WHERE id = ?"
result = adapter.fetch_dataframe(query, (user_input,))

# ✅ GOOD: SQLAlchemy ORM
from sqlalchemy import select
stmt = select(User).where(User.id == user_input)
result = session.execute(stmt)
```

```sql
-- ❌ CRITICAL: Dynamic SQL without parameters
EXEC('SELECT * FROM users WHERE id = ' + @userId);

-- ✅ GOOD: sp_executesql with parameters
EXEC sp_executesql 
    N'SELECT * FROM users WHERE id = @id',
    N'@id UNIQUEIDENTIFIER',
    @id = @userId;
```

### Command Injection Prevention

```python
import shlex
import subprocess

# ❌ CRITICAL: Shell injection
filename = user_input
os.system(f"process_file {filename}")

# ✅ GOOD: Escape and validate
filename = shlex.quote(user_input)
subprocess.run(["process_file", filename], check=True)
```

### XSS Prevention

```python
# In Streamlit, use proper escaping
import streamlit as st

# ❌ BAD: Raw HTML from user input
st.markdown(user_input, unsafe_allow_html=True)

# ✅ GOOD: Let Streamlit escape
st.write(user_input)
st.text(user_input)

# If HTML needed, sanitize first
from bleach import clean
safe_html = clean(user_input, tags=['b', 'i', 'u'])
st.markdown(safe_html, unsafe_allow_html=True)
```

### YAML Template Injection

When SQL queries are externalized to YAML files with `{table}` placeholders, the substitution uses Python `str.format()`. User input must **NEVER** flow into these template variables.

```python
# ❌ CRITICAL: User input reaches .format() template
query_template = yaml_config["sql"]  # "SELECT * FROM {table} WHERE id = ?"
table_name = user_input              # Attacker: "users; DROP TABLE users--"
query = query_template.format(table=table_name)

# ✅ GOOD: Table names from config only, never from user input
table_name = config.get_table_name("pega_cases")  # From trusted config
query = query_template.format(table=table_name)
# User input goes through parameterized ? placeholders only
```

**Rule:** `{table}` in YAML queries is a config-only substitution. All user-supplied values must use `?` parameter placeholders in the SQL itself.

---

## A03.5: Server-Side Request Forgery (SSRF) — OWASP A10

```python
from urllib.parse import urlparse

# ✅ GOOD: Validate URLs against an allow-list before making server-side requests
ALLOWED_HOSTS = {"api.trusted.com", "internal.example.local"}

def validate_url(url: str) -> bool:
    """Validate that a URL is on the allow-list."""
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Host not allowed: {parsed.hostname}")
    if parsed.scheme not in ("https",):
        raise ValueError("Only HTTPS allowed")
    return True

# ❌ BAD: Fetching arbitrary URLs from user input
import requests
def fetch_webhook(url: str):
    return requests.get(url)  # Attacker can target internal services

# ✅ GOOD: Validate first
def fetch_webhook(url: str):
    validate_url(url)
    return requests.get(url, timeout=10)
```

When the server makes requests to user-provided URLs (webhooks, callbacks, URL previews), always validate the host, port, and scheme against a strict allow-list. Block requests to private IP ranges (`127.0.0.1`, `10.x.x.x`, `169.254.x.x`).

---

## A04: Insecure Design

### Input Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Literal

class ComplaintCreate(BaseModel):
    """Validated complaint creation model."""
    
    customer_id: str = Field(..., min_length=1, max_length=50)
    complaint_type: Literal["billing", "service", "technical"] 
    description: str = Field(..., min_length=10, max_length=5000)
    priority: int = Field(default=3, ge=1, le=5)
    
    @validator('customer_id')
    def validate_customer_id(cls, v):
        if not v.startswith('CUST'):
            raise ValueError('Customer ID must start with CUST')
        return v
```

### Path Traversal Prevention

```python
import os
from pathlib import Path

# ❌ CRITICAL: Path traversal vulnerability
def read_file(filename: str) -> str:
    with open(f"uploads/{filename}") as f:
        return f.read()
# Attacker can use: ../../etc/passwd

# ✅ GOOD: Validate and resolve path
UPLOAD_DIR = Path("/app/uploads").resolve()

def read_file(filename: str) -> str:
    # Remove path separators
    safe_name = os.path.basename(filename)
    file_path = (UPLOAD_DIR / safe_name).resolve()
    
    # Verify path is within allowed directory
    if not str(file_path).startswith(str(UPLOAD_DIR)):
        raise ValueError("Invalid file path")
    
    if not file_path.exists():
        raise FileNotFoundError("File not found")
    
    with open(file_path) as f:
        return f.read()
```

---

## A04.5: Security Headers

```python
# FastAPI middleware for essential security headers
from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# Also restrict allowed hosts
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["app.example.com"])
```

Key headers:
- **`Content-Security-Policy` (CSP)**: Prevent XSS by controlling which resources can load
- **`Strict-Transport-Security` (HSTS)**: Force HTTPS connections
- **`X-Content-Type-Options: nosniff`**: Prevent MIME type sniffing
- **`X-Frame-Options: DENY`**: Prevent clickjacking via iframes

---

## A05: Security Misconfiguration

### Environment-Specific Configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = False
    
    # Only enable debug in development
    @property
    def is_debug_enabled(self) -> bool:
        return self.debug and self.app_env == "development"

settings = Settings()

# In application
if settings.is_debug_enabled:
    # Only in development
    app.debug = True
else:
    # Production: no debug info
    app.debug = False
```

### Error Handling in Production

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full error for debugging
    logger.exception(f"Unhandled error: {exc}")
    
    # Return safe message to client (no stack trace)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."}
    )
```

---

## A07: Authentication Failures

### Session Security

```python
# Streamlit session configuration
import streamlit as st

# Generate secure session ID
import secrets

if 'session_id' not in st.session_state:
    st.session_state.session_id = secrets.token_urlsafe(32)

# Set secure cookie flags (in FastAPI)
from fastapi import Response

@app.post("/login")
async def login(response: Response, credentials: Credentials):
    # ... validate credentials ...
    
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,     # Prevent JavaScript access
        secure=True,       # HTTPS only
        samesite="strict", # Prevent CSRF
        max_age=3600       # 1 hour expiry
    )
```

### Rate Limiting

```python
from fastapi import FastAPI, Request, HTTPException
from collections import defaultdict
import time

# Simple in-memory rate limiter
request_counts = defaultdict(list)
RATE_LIMIT = 100  # requests per minute

def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    minute_ago = now - 60
    
    # Clean old entries
    request_counts[client_ip] = [
        t for t in request_counts[client_ip] if t > minute_ago
    ]
    
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return False
    
    request_counts[client_ip].append(now)
    return True

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")
    
    return await call_next(request)
```

---

## A08: Software and Data Integrity Failures

### Insecure Deserialization

```python
# ❌ CRITICAL: Never unpickle untrusted data
import pickle
data = pickle.loads(user_provided_bytes)  # Remote code execution risk

# ✅ GOOD: Use safe formats for untrusted data
import json
data = json.loads(user_provided_string)

# ✅ If deserialization is required, validate types strictly
from pydantic import BaseModel

class SafePayload(BaseModel):
    action: str
    value: int

payload = SafePayload.model_validate_json(user_provided_string)
```

- Never deserialize data from untrusted sources with `pickle`, `marshal`, or `yaml.load()` (use `yaml.safe_load()`)
- Prefer JSON for data interchange with untrusted sources
- Use Pydantic or similar for strict type validation on deserialized data

---

## Logging Security

### Never Log Sensitive Data

```python
from loguru import logger

# ❌ BAD: Logging credentials
logger.info(f"Login attempt for user {username} with password {password}")
logger.debug(f"API key: {api_key}")

# ✅ GOOD: Mask sensitive data
logger.info(f"Login attempt for user {username}")
logger.debug(f"API key: {api_key[:4]}***{api_key[-4:]}")

# ✅ BEST: Use repr=False in Pydantic
class Credentials(BaseModel):
    username: str
    password: str = Field(..., repr=False)
```

---

## Security in Code Reviews

When identifying a security vulnerability during review:
1. Explain the specific risk (e.g., "This string concatenation enables SQL injection")
2. Provide the corrected code
3. Reference the OWASP category (e.g., A03: Injection)

When writing code that mitigates a security risk, add a brief comment explaining what it protects against:
```python
# Parameterized query to prevent SQL injection (OWASP A03)
result = adapter.fetch_dataframe("SELECT * FROM users WHERE id = ?", (user_id,))
```

## Checklist Before Deployment

- [ ] No hardcoded secrets (check with `git grep -i password`)
- [ ] All SQL queries are parameterized
- [ ] Input validation on all user inputs
- [ ] SSRF protection: URL allow-lists for server-side requests
- [ ] Security headers configured (CSP, HSTS, X-Content-Type-Options)
- [ ] Error messages don't expose internals
- [ ] Debug mode disabled in production
- [ ] HTTPS enforced
- [ ] Rate limiting implemented
- [ ] No insecure deserialization (no `pickle.loads` on untrusted data)
- [ ] Logging excludes sensitive data
- [ ] Dependencies scanned for vulnerabilities (`pip-audit`)
- [ ] `.env` files in `.gitignore`

## Project Defaults

> Read `project-config.md` to resolve placeholder values.
