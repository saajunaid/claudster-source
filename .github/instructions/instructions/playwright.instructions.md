---
description: 'Playwright test generation and automation guidelines'
applyTo: '**/tests/**/*.ts, **/tests/**/*.py, **/*.spec.ts, **/*.test.ts'
---

# Playwright Testing Instructions

Guidelines for writing robust, maintainable end-to-end tests using Playwright applications.

## Test Structure

### Python Test Template
```python
import pytest
from playwright.sync_api import Page, expect

class TestNetworkDashboard:
    """Tests for the Network Dashboard feature."""
    
    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Navigate to the dashboard before each test."""
        page.goto("/dashboard")
        # Wait for dashboard to load
        expect(page.locator("h1")).to_have_text("Network Dashboard")
    
    def test_displays_key_metrics(self, page: Page):
        """Verify key metrics are displayed on the dashboard."""
        # Arrange - setup is handled by fixture
        
        # Act - page is already loaded
        
        # Assert
        expect(page.get_by_role("heading", name="Total Users")).to_be_visible()
        expect(page.get_by_test_id("active-users-metric")).to_have_text_matching(r"\d+")
        expect(page.get_by_role("img", name="Traffic Chart")).to_be_visible()
    
    def test_filter_by_date_range(self, page: Page):
        """Verify filtering by date range updates the data."""
        # Arrange
        date_picker = page.get_by_label("Date Range")
        
        # Act
        date_picker.click()
        page.get_by_role("option", name="Last 7 Days").click()
        
        # Assert
        expect(page.get_by_text("Showing data for Last 7 Days")).to_be_visible()
        # Verify chart updated
        expect(page.locator(".chart-container")).to_have_attribute(
            "data-range", "7d"
        )
```

### TypeScript Test Template
```typescript
import { test, expect } from '@playwright/test';

test.describe('Network Dashboard', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/dashboard');
        await expect(page.locator('h1')).toHaveText('Network Dashboard');
    });

    test('displays key metrics', async ({ page }) => {
        // Verify metrics are visible
        await expect(page.getByRole('heading', { name: 'Total Users' }))
            .toBeVisible();
        await expect(page.getByTestId('active-users-metric'))
            .toHaveText(/\d+/);
    });

    test('filter by date range updates data', async ({ page }) => {
        // Open date picker
        await page.getByLabel('Date Range').click();
        
        // Select option
        await page.getByRole('option', { name: 'Last 7 Days' }).click();
        
        // Verify update
        await expect(page.getByText('Showing data for Last 7 Days'))
            .toBeVisible();
    });
});
```

## Locator Best Practices

### Preferred Locators (Most Resilient)
```python
# 1. Role-based (most accessible and resilient)
page.get_by_role("button", name="Submit")
page.get_by_role("textbox", name="Email")
page.get_by_role("link", name="Dashboard")
page.get_by_role("heading", level=1)

# 2. Label-based (accessible)
page.get_by_label("Email Address")
page.get_by_placeholder("Enter email...")

# 3. Text-based
page.get_by_text("Welcome back")
page.get_by_text("Submit", exact=True)

# 4. Test IDs (controlled, stable)
page.get_by_test_id("submit-button")
page.get_by_test_id("user-profile-card")
```

### Avoid These Locators
```python
# ❌ Fragile: CSS classes change often
page.locator(".btn-primary")

# ❌ Fragile: DOM structure changes
page.locator("div > div > button")

# ❌ Fragile: XPath is hard to maintain
page.locator("//button[@class='submit']")

# ❌ Fragile: Indexes change with content
page.locator("button").nth(3)
```

## Assertions (Web-First)

### Use Auto-Retrying Assertions
```python
# ✅ Good: Auto-retrying, waits for condition
expect(page.locator("h1")).to_have_text("Dashboard")
expect(page.get_by_role("button")).to_be_enabled()
expect(page.get_by_test_id("loading")).to_be_hidden()

# ❌ Bad: No auto-retry
assert page.locator("h1").inner_text() == "Dashboard"
```

### Prefer Specific Assertions
```python
# ✅ Better: Use the most specific assertion available
expect(page.get_by_role("heading")).to_have_text("Dashboard")
expect(page.get_by_label("Email")).to_have_value("user@example.com")
expect(page).to_have_url(re.compile(r"/dashboard"))

# ⚠️ Less ideal: to_be_visible() is generic — prefer more specific assertions
# when testing for a particular value, text, or attribute
expect(page.get_by_role("heading")).to_be_visible()  # OK for visibility tests

# ✅ Always prefer expect() over assert for UI tests
# expect() auto-retries until timeout; assert does not
expect(page.get_by_text("Saved")).to_be_visible()   # ✅ retries
assert page.get_by_text("Saved").is_visible()        # ❌ no retry
```

### Common Assertions
```python
# Visibility
expect(locator).to_be_visible()
expect(locator).to_be_hidden()
expect(locator).to_be_attached()

# Text content
expect(locator).to_have_text("exact text")
expect(locator).to_contain_text("partial text")
expect(locator).to_have_text(re.compile(r"\d+ items"))

# Attributes
expect(locator).to_have_attribute("disabled", "")
expect(locator).to_have_class(re.compile(r"active"))

# Count
expect(locator).to_have_count(5)

# Input values
expect(locator).to_have_value("user@example.com")
expect(locator).to_be_checked()

# URL
expect(page).to_have_url(re.compile(r"/dashboard"))
expect(page).to_have_title("<APP_TITLE>")
```

## Page Object Pattern

```python
# pages/dashboard_page.py
from playwright.sync_api import Page, expect

class DashboardPage:
    """Page object for the Network Dashboard."""
    
    def __init__(self, page: Page):
        self.page = page
        # Locators
        self.heading = page.get_by_role("heading", level=1)
        self.date_picker = page.get_by_label("Date Range")
        self.metrics_section = page.get_by_test_id("metrics-section")
        self.refresh_button = page.get_by_role("button", name="Refresh")
    
    def navigate(self):
        """Navigate to the dashboard."""
        self.page.goto("/dashboard")
        expect(self.heading).to_have_text("Network Dashboard")
    
    def select_date_range(self, range_name: str):
        """Select a date range from the picker."""
        self.date_picker.click()
        self.page.get_by_role("option", name=range_name).click()
    
    def get_metric_value(self, metric_name: str) -> str:
        """Get the value of a specific metric."""
        metric = self.page.get_by_test_id(f"{metric_name}-value")
        return metric.inner_text()
    
    def refresh_data(self):
        """Click the refresh button and wait for update."""
        with self.page.expect_response(lambda r: "/api/metrics" in r.url):
            self.refresh_button.click()

# tests/test_dashboard.py
from pages.dashboard_page import DashboardPage

def test_dashboard_metrics(page: Page):
    dashboard = DashboardPage(page)
    dashboard.navigate()
    
    value = dashboard.get_metric_value("active-users")
    assert int(value) > 0
```

## Handling Asynchronous Content

### Wait for Network
```python
# Wait for specific API call
with page.expect_response(lambda r: "/api/data" in r.url) as response:
    page.get_by_role("button", name="Load Data").click()

data = response.value.json()
```

### Wait for State Changes
```python
# Wait for loading to complete
page.get_by_role("button", name="Submit").click()
expect(page.get_by_test_id("loading")).to_be_hidden()
expect(page.get_by_text("Success")).to_be_visible()

# Wait for navigation
async with page.expect_navigation():
    page.get_by_role("link", name="Dashboard").click()
```

### Avoid Hard Waits
```python
# ❌ Bad: Arbitrary wait
page.wait_for_timeout(3000)

# ✅ Good: Wait for condition
page.wait_for_selector("[data-loaded='true']")
expect(page.locator(".content")).to_be_visible()
```

## Testing Streamlit Applications

```python
def test_streamlit_app(page: Page):
    page.goto("http://localhost:8501")
    
    # Wait for Streamlit to initialize
    page.wait_for_selector("[data-testid='stAppViewContainer']")
    
    # Interact with Streamlit components
    page.get_by_label("Enter your name").fill("Test User")
    page.get_by_role("button", name="Submit").click()
    
    # Verify output
    expect(page.get_by_text("Hello, Test User")).to_be_visible()
    
    # Interact with selectbox
    page.get_by_label("Select option").click()
    page.get_by_role("option", name="Option A").click()
    
    # Verify chart rendered
    expect(page.locator(".js-plotly-plot")).to_be_visible()
```

## Test Configuration

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    smoke: marks tests for smoke testing
```

### conftest.py
```python
import pytest
from playwright.sync_api import Page

@pytest.fixture
def authenticated_page(page: Page):
    """Page with authenticated user session."""
    page.goto("/login")
    page.get_by_label("Username").fill("testuser")
    page.get_by_label("Password").fill("testpass")
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_text("Welcome")).to_be_visible()
    return page

@pytest.fixture
def mock_api(page: Page):
    """Mock API responses for isolated testing."""
    page.route("**/api/users", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='[{"id": 1, "name": "Test User"}]'
    ))
    return page
```

## Debugging

```python
# Pause for debugging
page.pause()

# Screenshot on failure
page.screenshot(path="screenshot.png")

# Trace viewer
# Run with: pytest --tracing=on
# View with: playwright show-trace trace.zip

# Console logs
page.on("console", lambda msg: print(f"Console: {msg.text}"))
```

## File Organization

- **Location**: Store test files in a dedicated `tests/` directory or follow the existing project structure
- **Naming**: Test files must follow the `test_<feature-or-page>.py` naming convention for Pytest discovery
- **Scope**: Aim for one test file per major application feature or page
- **Imports**: Every test file should begin with `from playwright.sync_api import Page, expect`

## Test Quality Checklist

- [ ] Tests have descriptive names explaining what they verify
- [ ] Use role-based or test-id locators
- [ ] Use auto-retrying assertions (prefer `expect` over `assert`)
- [ ] Use the most specific assertion available (not just `to_be_visible`)
- [ ] No hard-coded waits
- [ ] Tests are independent (no order dependency)
- [ ] Page objects used for complex pages
- [ ] Tests cover happy path and error cases
- [ ] Accessibility tested (keyboard navigation, screen reader)
