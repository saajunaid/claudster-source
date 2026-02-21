---
description: "Testing guidelines for applications using pytest"
applyTo: "**/*test*.py, **/conftest.py, **/fixtures*.py, **/tests/**/*.py"
---

# Testing Guidelines

Standards for writing tests for Streamlit, FastAPI, and Python applications.

## Test Structure

```
project/
├── src/
│   └── app/
│       ├── services/
│       └── repositories/
└── tests/
    ├── conftest.py          # Shared fixtures
    ├── unit/
    │   ├── test_services.py
    │   └── test_utils.py
    ├── integration/
    │   ├── test_api.py
    │   └── test_database.py
    └── e2e/
        └── test_workflows.py
```

---

## Naming Conventions

```python
# Test files: test_<module>.py
# test_complaint_service.py

# Test functions: test_<action>_<scenario>_<expected_outcome>
def test_create_complaint_with_valid_data_returns_complaint_id():
    ...

def test_create_complaint_with_missing_description_raises_validation_error():
    ...

# Test classes: Test<ClassName>
class TestComplaintService:
    def test_create_returns_id(self):
        ...
```

---

## Fixtures

### conftest.py

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from uuid import uuid4

from app.models.complaint import Complaint, ComplaintCreate

@pytest.fixture
def sample_complaint() -> Complaint:
    """Create a sample complaint for testing."""
    return Complaint(
        id=uuid4(),
        customer_id="CUST001",
        complaint_type="billing",
        description="Test complaint description",
        priority=3,
        status="open",
        created_at=datetime.now()
    )

@pytest.fixture
def sample_complaint_create() -> ComplaintCreate:
    """Create sample complaint creation data."""
    return ComplaintCreate(
        customer_id="CUST001",
        complaint_type="billing",
        description="Test complaint description for creation",
        priority=3
    )

@pytest.fixture
def mock_db_adapter():
    """Create a mock database adapter."""
    adapter = MagicMock()
    adapter.fetch_dataframe = MagicMock(return_value=pd.DataFrame())
    adapter.execute = MagicMock(return_value=True)
    return adapter

@pytest.fixture
def mock_async_db():
    """Create a mock async database adapter."""
    adapter = AsyncMock()
    adapter.fetch = AsyncMock(return_value=[])
    adapter.execute = AsyncMock(return_value=True)
    return adapter
```

---

## Unit Tests

### Testing Services

```python
# tests/unit/test_complaint_service.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from app.services.complaint_service import ComplaintService
from app.models.complaint import ComplaintCreate

class TestComplaintService:
    """Tests for ComplaintService."""
    
    @pytest.fixture
    def mock_repo(self):
        """Create mock repository."""
        return MagicMock()
    
    @pytest.fixture
    def service(self, mock_repo):
        """Create service with mock repository."""
        return ComplaintService(repository=mock_repo)
    
    @pytest.mark.asyncio
    async def test_create_complaint_calls_repository(
        self, service, mock_repo, sample_complaint_create, sample_complaint
    ):
        """Test that creating a complaint calls the repository."""
        # Arrange
        mock_repo.create = AsyncMock(return_value=sample_complaint)
        
        # Act
        result = await service.create_complaint(sample_complaint_create)
        
        # Assert
        mock_repo.create.assert_called_once_with(sample_complaint_create)
        assert result.id == sample_complaint.id
    
    @pytest.mark.asyncio
    async def test_get_complaint_not_found_returns_none(self, service, mock_repo):
        """Test that getting a non-existent complaint returns None."""
        # Arrange
        mock_repo.get = AsyncMock(return_value=None)
        complaint_id = uuid4()
        
        # Act
        result = await service.get_complaint(complaint_id)
        
        # Assert
        assert result is None
        mock_repo.get.assert_called_once_with(complaint_id)
```

### Testing Utilities

```python
# tests/unit/test_utils.py
import pytest
from app.utils.validators import validate_customer_id, sanitize_input

class TestValidators:
    """Tests for validation utilities."""
    
    @pytest.mark.parametrize("customer_id,expected", [
        ("CUST001", True),
        ("CUST999999", True),
        ("", False),
        ("INVALID", False),
        ("cust001", False),  # Case sensitive
    ])
    def test_validate_customer_id(self, customer_id, expected):
        """Test customer ID validation with various inputs."""
        assert validate_customer_id(customer_id) == expected
    
    @pytest.mark.parametrize("input_str,expected", [
        ("hello", "hello"),
        ("hello<script>", "helloscript"),
        ("a" * 1000, "a" * 500),  # Truncation
    ])
    def test_sanitize_input(self, input_str, expected):
        """Test input sanitization."""
        assert sanitize_input(input_str) == expected
```

---

## Integration Tests

### Testing FastAPI Endpoints

```python
# tests/integration/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.dependencies import get_complaint_service
from app.services.complaint_service import ComplaintService

class TestComplaintsAPI:
    """Integration tests for complaints API."""
    
    @pytest.fixture
    def mock_service(self, sample_complaint):
        """Create mock service."""
        service = MagicMock(spec=ComplaintService)
        service.list_complaints = MagicMock(return_value={
            "items": [sample_complaint],
            "total": 1,
            "page": 1,
            "per_page": 25,
            "pages": 1
        })
        return service
    
    @pytest.fixture
    def client(self, mock_service):
        """Create test client with mocked dependencies."""
        app.dependency_overrides[get_complaint_service] = lambda: mock_service
        
        with TestClient(app) as client:
            yield client
        
        app.dependency_overrides.clear()
    
    def test_list_complaints_returns_200(self, client):
        """Test listing complaints returns success."""
        response = client.get("/api/v1/complaints/")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
    
    def test_create_complaint_with_invalid_data_returns_422(self, client):
        """Test creating complaint with invalid data returns validation error."""
        response = client.post(
            "/api/v1/complaints/",
            json={"customer_id": ""}  # Invalid: missing required fields
        )
        
        assert response.status_code == 422
    
    def test_get_complaint_not_found_returns_404(self, client, mock_service):
        """Test getting non-existent complaint returns 404."""
        mock_service.get_complaint = MagicMock(return_value=None)
        
        response = client.get("/api/v1/complaints/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 404
```

### Testing Database Integration

```python
# tests/integration/test_database.py
import pytest
from <SHARED_LIBS>.data import DatabaseAdapter

@pytest.fixture(scope="module")
def db_adapter():
    """Create real database adapter for integration tests."""
    adapter = DatabaseAdapter(connection_string="test_connection_string")
    yield adapter
    adapter.close()

class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.mark.integration
    def test_fetch_dataframe_returns_dataframe(self, db_adapter):
        """Test fetching data returns a DataFrame."""
        result = db_adapter.fetch_dataframe("SELECT 1 AS value")
        
        assert len(result) == 1
        assert result.iloc[0]["value"] == 1
    
    @pytest.mark.integration
    def test_execute_stored_procedure(self, db_adapter):
        """Test executing a stored procedure."""
        result = db_adapter.execute(
            "EXEC [dbo].[usp_GetHealthCheck]"
        )
        
        assert result is True
```

---

## Testing Streamlit

```python
# tests/unit/test_streamlit_components.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

# Mock Streamlit before importing components
@pytest.fixture(autouse=True)
def mock_streamlit():
    """Mock Streamlit for testing."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        yield

class TestDashboardComponents:
    """Tests for dashboard components."""
    
    def test_filter_dataframe_by_status(self):
        """Test filtering DataFrame by status."""
        from app.components.filters import filter_by_status
        
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "status": ["open", "closed", "open"]
        })
        
        result = filter_by_status(df, "open")
        
        assert len(result) == 2
        assert all(result["status"] == "open")
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        from app.components.metrics import calculate_summary_metrics
        
        df = pd.DataFrame({
            "status": ["open", "closed", "open"],
            "priority": [1, 3, 5]
        })
        
        metrics = calculate_summary_metrics(df)
        
        assert metrics["total"] == 3
        assert metrics["open"] == 2
        assert metrics["avg_priority"] == 3.0
```

---

## Mocking Guidelines

### When to Mock

| Mock | Real |
|------|------|
| External APIs | Pure functions |
| Database in unit tests | In-memory calculations |
| File system | Data transformations |
| Network calls | Business logic |
| Third-party services | Utility functions |

### Mock Examples

```python
from unittest.mock import MagicMock, AsyncMock, patch

# Mock a method
@patch.object(ComplaintRepository, "create")
def test_with_patched_method(mock_create):
    mock_create.return_value = sample_complaint
    ...

# Mock a module function
@patch("app.services.complaint_service.send_notification")
def test_with_patched_function(mock_send):
    mock_send.return_value = True
    ...

# Mock context manager
@patch("builtins.open", mock_open(read_data="file content"))
def test_file_reading():
    ...

# Mock async function
mock_repo.create = AsyncMock(return_value=sample_complaint)
```

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_services.py

# Run specific test
pytest tests/unit/test_services.py::TestComplaintService::test_create_complaint_calls_repository

# Run marked tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

---

## Coverage Requirements

- **Minimum coverage**: 80% for new code
- **Critical paths**: 100% (authentication, data access)
- **Generated reports**: HTML in `htmlcov/`

```ini
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: marks tests as integration tests",
    "slow: marks tests as slow",
]

[tool.coverage.run]
source = ["app"]
omit = ["tests/*", "*/__pycache__/*"]

[tool.coverage.report]
fail_under = 80
```

---

## Test-Driven Development (TDD)

Follow the TDD cycle for new code:

1. **RED**: Write a failing test for the desired behavior
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Improve code while keeping tests green

```python
# Step 1: Write failing test (RED)
def test_add_numbers():
    result = add(2, 3)
    assert result == 5

# Step 2: Write minimal implementation (GREEN)
def add(a, b):
    return a + b

# Step 3: Refactor if needed (REFACTOR)
```

---

## Advanced Fixture Patterns

### Fixture Scopes

```python
# Function scope (default) - runs for each test
@pytest.fixture
def temp_file():
    with open("temp.txt", "w") as f:
        yield f
    os.remove("temp.txt")

# Module scope - runs once per module
@pytest.fixture(scope="module")
def module_db():
    db = Database(":memory:")
    db.create_tables()
    yield db
    db.close()

# Session scope - runs once per test session
@pytest.fixture(scope="session")
def shared_resource():
    resource = ExpensiveResource()
    yield resource
    resource.cleanup()
```

### Autouse Fixtures

```python
@pytest.fixture(autouse=True)
def reset_config():
    """Automatically runs before every test."""
    Config.reset()
    yield
    Config.cleanup()
```

### Parameterized Fixtures

```python
@pytest.fixture(params=["sqlite", "postgresql", "mysql"])
def db(request):
    """Test against multiple backends."""
    if request.param == "sqlite":
        return Database(":memory:")
    elif request.param == "postgresql":
        return Database("postgresql://localhost/test")
    elif request.param == "mysql":
        return Database("mysql://localhost/test")
```

---

## Parametrize with IDs

```python
@pytest.mark.parametrize("input,expected", [
    ("valid@email.com", True),
    ("invalid", False),
    ("@no-domain.com", False),
], ids=["valid-email", "missing-at", "missing-domain"])
def test_email_validation(input, expected):
    """Test email validation with readable test IDs."""
    assert is_valid_email(input) is expected
```

---

## Markers and Test Selection

### Custom Markers

```python
@pytest.mark.slow
def test_slow_operation():
    time.sleep(5)

@pytest.mark.integration
def test_api_integration():
    response = requests.get("https://api.example.com")
    assert response.status_code == 200

@pytest.mark.unit
def test_unit_logic():
    assert calculate(2, 3) == 5
```

### Configure Markers in pytest.ini

```ini
[pytest]
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

---

## Advanced Mocking Patterns

### Using Autospec

```python
@patch("mypackage.DBConnection", autospec=True)
def test_autospec(db_mock):
    """Autospec catches API misuse — fails if method doesn't exist."""
    db = db_mock.return_value
    db.query("SELECT * FROM users")
    db_mock.assert_called_once()
```

### Mock Properties

```python
from unittest.mock import Mock, PropertyMock

@pytest.fixture
def mock_config():
    config = Mock()
    type(config).debug = PropertyMock(return_value=True)
    type(config).api_key = PropertyMock(return_value="test-key")
    return config

def test_with_mock_config(mock_config):
    assert mock_config.debug is True
    assert mock_config.api_key == "test-key"
```

### Mocking Exceptions

```python
@patch("mypackage.api_call")
def test_api_error_handling(api_call_mock):
    api_call_mock.side_effect = ConnectionError("Network error")
    with pytest.raises(ConnectionError):
        api_call()
```

### Mocking Async Functions

```python
@pytest.mark.asyncio
@patch("mypackage.async_api_call")
async def test_async_mock(api_call_mock):
    api_call_mock.return_value = {"status": "ok"}
    result = await my_async_function()
    api_call_mock.assert_awaited_once()
    assert result["status"] == "ok"
```

---

## Testing Side Effects

### Using pytest's tmp_path Fixture

```python
def test_with_tmp_path(tmp_path):
    """Built-in temp directory fixture — auto cleaned up."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    result = process_file(str(test_file))
    assert result == "hello world"
```

### Testing File Operations with tempfile

```python
import tempfile, os

def test_file_processing():
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("test content")
        temp_path = f.name
    try:
        result = process_file(temp_path)
        assert result == "processed: test content"
    finally:
        os.unlink(temp_path)
```

---

## Testing Exceptions

```python
def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_custom_exception_message():
    with pytest.raises(ValueError, match="invalid input"):
        validate_input("invalid")

def test_exception_attributes():
    with pytest.raises(CustomError) as exc_info:
        raise CustomError("error", code=400)
    assert exc_info.value.code == 400
```

---

## Test Classes with Fixture Setup

```python
class TestCalculator:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.calc = Calculator()

    def test_add(self):
        assert self.calc.add(2, 3) == 5

    def test_divide_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            self.calc.divide(10, 0)
```

---

## Best Practices

### DO

- **Follow TDD**: Write tests before code (red-green-refactor)
- **Test one thing**: Each test should verify a single behavior
- **Use descriptive names**: `test_user_login_with_invalid_credentials_fails`
- **Use fixtures**: Eliminate duplication with fixtures
- **Mock external dependencies**: Don't depend on external services
- **Test edge cases**: Empty inputs, None values, boundary conditions
- **Aim for 80%+ coverage**: Focus on critical paths
- **Keep tests fast**: Use marks to separate slow tests

### DON'T

- **Don't test implementation**: Test behavior, not internals
- **Don't use complex conditionals in tests**: Keep tests simple
- **Don't ignore test failures**: All tests must pass
- **Don't test third-party code**: Trust libraries to work
- **Don't share state between tests**: Tests should be independent
- **Don't catch exceptions in tests**: Use `pytest.raises`
- **Don't use print statements**: Use assertions and pytest output
- **Don't write brittle tests**: Avoid over-specific mocks

---

## Checklist

- [ ] Test file naming follows `test_*.py` pattern
- [ ] Test functions named descriptively
- [ ] Fixtures in `conftest.py` for shared setup
- [ ] Unit tests mock external dependencies
- [ ] Integration tests use real connections (where safe)
- [ ] Async tests use `@pytest.mark.asyncio`
- [ ] Parametrized tests for multiple inputs
- [ ] Coverage meets 80% threshold
- [ ] TDD cycle followed for new code
- [ ] Markers configured for test categories
- [ ] Exception testing uses `pytest.raises`
- [ ] Temp files use `tmp_path` fixture

---

## Project Defaults

> See `project-config.md` for project-specific values for these placeholders.

| Placeholder | Description |
|-------------|-------------|
| `<SHARED_LIBS>` | Shared libraries path |
| `<DB_TYPE>` | Database type |
