---
description: "FastAPI development standards for backend services"
applyTo: "**/api/**/*.py, **/routers/**/*.py, **/services/**/*.py, **/endpoints/**/*.py, **/main.py"
---

# FastAPI Development Guidelines

Standards for building FastAPI backends with proper structure, validation, and security.

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Settings and configuration
│   ├── dependencies.py      # Shared dependencies
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── complaints.py
│   │   └── analytics.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── complaint.py     # Pydantic models
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── complaint_service.py
│   └── repositories/
│       ├── __init__.py
│       └── complaint_repo.py
├── tests/
├── .env
└── requirements.txt
```

---

## Application Setup

### Main Application

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.config import settings
from app.routers import complaints, analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting API...")
    # Startup: Initialize connections, load models
    yield
    # Shutdown: Clean up resources
    logger.info("Shutting down API...")

app = FastAPI(
    title="<APP_TITLE> API",       # from project-config.md
    description="<APP_DESCRIPTION>",  # from project-config.md
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(complaints.router, prefix="/api/v1/complaints", tags=["complaints"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.0"}
```

### Configuration

```python
# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Application
    app_name: str = "<APP_TITLE>"  # from project-config.md
    debug: bool = False
    
    # Database
    db_server: str = Field(..., description="SQL Server host")
    db_name: str = Field(..., description="Database name")
    db_user: str = Field(..., description="Database user")
    db_password: str = Field(..., repr=False)  # Hide in logs
    
    # API
    api_key: str = Field(..., repr=False)
    allowed_origins: list[str] = ["http://localhost:8501"]
    
    # LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

settings = get_settings()
```

---

## Pydantic Models

### Request/Response Models

```python
# app/models/complaint.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Literal
from uuid import UUID

class ComplaintBase(BaseModel):
    """Base complaint model."""
    customer_id: str = Field(..., min_length=1, max_length=50, example="CUST001")
    complaint_type: Literal["billing", "service", "technical"]
    description: str = Field(..., min_length=10, max_length=5000)
    priority: int = Field(default=3, ge=1, le=5)

class ComplaintCreate(ComplaintBase):
    """Model for creating a complaint."""
    pass

class ComplaintUpdate(BaseModel):
    """Model for updating a complaint."""
    status: Literal["open", "in_progress", "resolved"] | None = None
    resolution_notes: str | None = Field(None, max_length=2000)
    priority: int | None = Field(None, ge=1, le=5)

class ComplaintResponse(ComplaintBase):
    """Model for complaint response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    resolution_notes: str | None = None

class ComplaintList(BaseModel):
    """Paginated list of complaints."""
    items: list[ComplaintResponse]
    total: int
    page: int
    per_page: int
    pages: int
```

---

## Router Implementation

```python
# app/routers/complaints.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from uuid import UUID
from typing import Annotated

from app.models.complaint import (
    ComplaintCreate, ComplaintUpdate, ComplaintResponse, ComplaintList
)
from app.services.complaint_service import ComplaintService
from app.dependencies import get_complaint_service

router = APIRouter()

@router.get("/", response_model=ComplaintList)
async def list_complaints(
    service: Annotated[ComplaintService, Depends(get_complaint_service)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
) -> ComplaintList:
    """List all complaints with pagination."""
    return await service.list_complaints(
        page=page, per_page=per_page, status=status
    )

@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    service: Annotated[ComplaintService, Depends(get_complaint_service)],
    complaint_id: UUID = Path(..., description="Complaint ID"),
) -> ComplaintResponse:
    """Get a specific complaint by ID."""
    complaint = await service.get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.post("/", response_model=ComplaintResponse, status_code=201)
async def create_complaint(
    service: Annotated[ComplaintService, Depends(get_complaint_service)],
    complaint: ComplaintCreate,
) -> ComplaintResponse:
    """Create a new complaint."""
    return await service.create_complaint(complaint)

@router.patch("/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    service: Annotated[ComplaintService, Depends(get_complaint_service)],
    complaint_id: UUID,
    updates: ComplaintUpdate,
) -> ComplaintResponse:
    """Update an existing complaint."""
    complaint = await service.update_complaint(complaint_id, updates)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.delete("/{complaint_id}", status_code=204)
async def delete_complaint(
    service: Annotated[ComplaintService, Depends(get_complaint_service)],
    complaint_id: UUID,
) -> None:
    """Delete a complaint."""
    success = await service.delete_complaint(complaint_id)
    if not success:
        raise HTTPException(status_code=404, detail="Complaint not found")
```

---

## Dependencies

```python
# app/dependencies.py
from typing import Annotated, Generator
from fastapi import Depends, Header, HTTPException

from app.config import settings
from app.services.complaint_service import ComplaintService
from app.repositories.complaint_repo import ComplaintRepository
from <SHARED_LIBS>.data import DatabaseAdapter  # adjust path per project-config.md

def get_db_adapter() -> Generator[DatabaseAdapter, None, None]:
    """Get database adapter with proper cleanup."""
    adapter = DatabaseAdapter()
    try:
        yield adapter
    finally:
        adapter.close()

def get_complaint_repository(
    db: Annotated[DatabaseAdapter, Depends(get_db_adapter)]
) -> ComplaintRepository:
    """Get complaint repository."""
    return ComplaintRepository(db)

def get_complaint_service(
    repo: Annotated[ComplaintRepository, Depends(get_complaint_repository)]
) -> ComplaintService:
    """Get complaint service."""
    return ComplaintService(repo)

async def verify_api_key(
    x_api_key: Annotated[str, Header(..., description="API Key")]
) -> str:
    """Verify API key for protected endpoints."""
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
```

---

## Service Layer

```python
# app/services/complaint_service.py
from uuid import UUID
from loguru import logger

from app.models.complaint import (
    ComplaintCreate, ComplaintUpdate, ComplaintResponse, ComplaintList
)
from app.repositories.complaint_repo import ComplaintRepository

class ComplaintService:
    """Business logic for complaints."""
    
    def __init__(self, repository: ComplaintRepository):
        self.repo = repository
    
    async def create_complaint(self, data: ComplaintCreate) -> ComplaintResponse:
        """Create a new complaint with validation."""
        logger.info(f"Creating complaint for customer {data.customer_id}")
        
        # Business logic validation
        if data.priority >= 4:
            # High priority complaints get auto-escalation
            logger.warning(f"High priority complaint created for {data.customer_id}")
        
        complaint = await self.repo.create(data)
        return ComplaintResponse.model_validate(complaint)
    
    async def list_complaints(
        self, page: int, per_page: int, status: str | None = None
    ) -> ComplaintList:
        """List complaints with pagination."""
        items, total = await self.repo.list(
            offset=(page - 1) * per_page,
            limit=per_page,
            status=status
        )
        
        return ComplaintList(
            items=[ComplaintResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
```

---

## Error Handling

```python
# app/main.py - add exception handlers
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"}
    )
```

---

## Testing

```python
# tests/test_complaints.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_complaint_service

# Mock service for testing
class MockComplaintService:
    async def list_complaints(self, **kwargs):
        return ComplaintList(items=[], total=0, page=1, per_page=25, pages=0)

@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    app.dependency_overrides[get_complaint_service] = MockComplaintService
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

def test_list_complaints(client):
    """Test listing complaints."""
    response = client.get("/api/v1/complaints/")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 0

def test_create_complaint_validation(client):
    """Test complaint creation validation."""
    response = client.post(
        "/api/v1/complaints/",
        json={"customer_id": "", "complaint_type": "invalid"}
    )
    
    assert response.status_code == 422
```

---

## Checklist

- [ ] Proper project structure with separation of concerns
- [ ] Pydantic models for all request/response types
- [ ] Dependency injection for services and repositories
- [ ] Error handling with appropriate HTTP status codes
- [ ] Logging with loguru (not print statements)
- [ ] API key or authentication on protected endpoints
- [ ] Health check endpoint
- [ ] CORS configured for Streamlit frontend
- [ ] Tests with proper mocking

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values. The profile defines `<ORG_NAME>`, `<APP_TITLE>`, `<SHARED_LIBS>`, and other project-specific tokens.
