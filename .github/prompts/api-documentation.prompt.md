---
description: "Generate comprehensive API documentation for FastAPI endpoints."
---

# API Documentation Prompt

## Purpose

Generate comprehensive API documentation for FastAPI endpoints.

## Input Required

- Endpoint code or router file
- Context about the API purpose

## Template

```
Generate API documentation for the following FastAPI endpoints:

**API Context**: {api_description}

**Base URL**: {base_url}

**Code**:
```python
{router_code}
```

Generate documentation including:
1. API Overview
2. Authentication requirements
3. Each endpoint with:
   - Method and path
   - Description
   - Request parameters/body
   - Response format
   - Example request/response
   - Error responses
4. Common error codes
5. Rate limiting (if applicable)

Format as Markdown suitable for a docs site or README.
```

## Example

### Input

```
Generate API documentation for the following FastAPI endpoints:

**API Context**: API for <APP_TITLE>

**Base URL**: http://localhost:8000/api/v1

**Code**:
```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/complaints", tags=["complaints"])

class ComplaintCreate(BaseModel):
    customer_id: str
    complaint_type: str
    description: str
    priority: int = 3

class ComplaintResponse(BaseModel):
    id: UUID
    customer_id: str
    complaint_type: str
    description: str
    priority: int
    status: str

@router.get("/")
async def list_complaints(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100)
) -> dict:
    """List all complaints with optional filtering."""
    ...

@router.get("/{complaint_id}")
async def get_complaint(complaint_id: UUID) -> ComplaintResponse:
    """Get a specific complaint by ID."""
    ...

@router.post("/", status_code=201)
async def create_complaint(complaint: ComplaintCreate) -> ComplaintResponse:
    """Create a new complaint."""
    ...
```
```

### Expected Output

```markdown
# Complaints API

API for managing resources in the <APP_TITLE> system.

**Base URL**: `http://localhost:8000/api/v1`

## Authentication

All endpoints require API key authentication via header:

```
X-API-Key: your-api-key
```

---

## Endpoints

### List Complaints

Retrieve a paginated list of complaints with optional filtering.

**Endpoint**: `GET /complaints/`

**Query Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | null | Filter by status (open, closed, pending) |
| `page` | integer | No | 1 | Page number (min: 1) |
| `per_page` | integer | No | 25 | Items per page (min: 1, max: 100) |

**Response**: `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "customer_id": "CUST001",
      "complaint_type": "billing",
      "description": "Incorrect charge on bill",
      "priority": 3,
      "status": "open"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 25,
  "pages": 6
}
```

**Example Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/complaints/?status=open&page=1" \
  -H "X-API-Key: your-api-key"
```

---

### Get Complaint

Retrieve a specific complaint by ID.

**Endpoint**: `GET /complaints/{complaint_id}`

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `complaint_id` | UUID | Unique complaint identifier |

**Response**: `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "CUST001",
  "complaint_type": "billing",
  "description": "Incorrect charge on bill",
  "priority": 3,
  "status": "open"
}
```

**Error Responses**:

| Status | Description |
|--------|-------------|
| `404 Not Found` | Complaint with specified ID not found |

**Example Request**:

```bash
curl -X GET "http://localhost:8000/api/v1/complaints/550e8400-e29b-41d4-a716-446655440000" \
  -H "X-API-Key: your-api-key"
```

---

### Create Complaint

Create a new complaint record.

**Endpoint**: `POST /complaints/`

**Request Body**:

```json
{
  "customer_id": "CUST001",
  "complaint_type": "billing",
  "description": "Incorrect charge on bill",
  "priority": 3
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `customer_id` | string | Yes | - | Customer identifier |
| `complaint_type` | string | Yes | - | Type: billing, technical, service |
| `description` | string | Yes | - | Complaint description |
| `priority` | integer | No | 3 | Priority level (1-5) |

**Response**: `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "CUST001",
  "complaint_type": "billing",
  "description": "Incorrect charge on bill",
  "priority": 3,
  "status": "open"
}
```

**Error Responses**:

| Status | Description |
|--------|-------------|
| `422 Unprocessable Entity` | Validation error in request body |

**Example Request**:

```bash
curl -X POST "http://localhost:8000/api/v1/complaints/" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "complaint_type": "billing",
    "description": "Incorrect charge on bill",
    "priority": 3
  }'
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| `400 Bad Request` | Invalid request format |
| `401 Unauthorized` | Missing or invalid API key |
| `403 Forbidden` | Insufficient permissions |
| `404 Not Found` | Resource not found |
| `422 Unprocessable Entity` | Validation error |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Server error |

## Rate Limiting

- **Limit**: 100 requests per minute per API key
- **Headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
```

## Tips

- Include realistic example values
- Document all error cases
- Show curl examples for quick testing
- Keep response examples concise but complete
