---
description: "Streamlit development standards for dashboards and applications"
applyTo: "**/app.py, **/pages/**/*.py, **/components/**/*.py, **/views/**/*.py, **/tabs/**/*.py"
---

# Streamlit Development Guidelines

Standards for building Streamlit dashboards with project branding and shared libraries.

## Page Configuration

Always configure page settings at the very top of the main file:

```python
import streamlit as st

st.set_page_config(
    page_title="<APP_TITLE>",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
```

## Branding & Theme

Use the shared UI library for consistent branding:

```python
from <SHARED_LIBS>.ui import apply_theme  # from project-config.md

# Apply at start of app
apply_theme()
```

### Color Palette

```python
# Brand colors (from project-config.md)
COLORS = {
    "plum": "#5A2D82",
    "red": "#E30613",
    "white": "#FFFFFF",
    "black": "#000000",
    "gray": "#7D7D7D",
    "light_gray": "#D9D9D9",
    "dark_gray": "#4A4A4A",
    "light_red": "#F28B82",
    "dark_red": "#B71C1C",
    "bright_red": "#A61A07",
    "light_plum": "#B39DDB",
    "dark_plum": "#3B022A",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "text": "#4A4A4A"
}
```

### Custom CSS

```python
def apply_custom_styles():
    """Apply project custom styles."""
    st.markdown("""
        <style>
        /* Primary button styling */
        .stButton > button[kind="primary"] {
            background-color: #E30613;
            border: none;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: #B71C1C;
        }
        
        /* Header styling */
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #4A4A4A;
            border-bottom: 3px solid #E30613;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }
        
        /* Card styling */
        .metric-card {
            background-color: white;
            padding: 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            border-left: 4px solid #5A2D82;
        }
        </style>
    """, unsafe_allow_html=True)
```

---

## Caching Strategies

### Cache Data with TTL

```python
from datetime import timedelta

@st.cache_data(ttl=timedelta(minutes=15), show_spinner="Loading data...")
def load_complaints_data() -> pd.DataFrame:
    """Load complaints data with 15-minute cache."""
    from <SHARED_LIBS>.data import DatabaseAdapter
    
    adapter = DatabaseAdapter()
    return adapter.fetch_dataframe(
        "SELECT * FROM complaints WHERE created_at > DATEADD(day, -30, GETDATE())"
    )
```

### Cache Resources (Connections, Models)

```python
@st.cache_resource
def get_database_adapter():
    """Get cached database adapter."""
    from <SHARED_LIBS>.data import DatabaseAdapter
    return DatabaseAdapter()

@st.cache_resource
def load_ml_model():
    """Load and cache ML model."""
    import joblib
    return joblib.load("models/classifier.joblib")
```

### When to Use Each

| Decorator | Use For | Returns |
|-----------|---------|---------|
| `@st.cache_data` | Data (DataFrames, lists, dicts) | Serialized copy |
| `@st.cache_resource` | Connections, models, file handles | Same object |

### ⚠️ Caching Gotchas (MUST READ)

> These patterns cause production failures. Review before adding any caching decorator.

| # | Gotcha | Severity | Rule |
|---|--------|----------|------|
| 1 | `@st.cache_data` + Pydantic `@computed_field` | **CRITICAL** | Pickle can't serialize computed fields. Cache `model_dump_json()` string, reconstruct with `model_validate_json()` |
| 2 | `@st.cache_resource` + hot-reload | **HIGH** | Singleton survives reload but class identity changes. Only cache stateless I/O (adapters, clients), never services returning typed objects |
| 3 | `st.cache_resource.clear()` is global | **HIGH** | Clears ALL `@st.cache_resource` entries app-wide. Use `function_name.clear()` for targeted invalidation |
| 4 | Full-script re-execution | **HIGH** | Streamlit re-runs the entire script on every interaction. Any uncached DB call runs on every click — audit all function calls |
| 5 | `st.session_state` inside `@st.cache_resource` | **HIGH** | Session state is per-user; cached resources are shared. Never reference session state in cached resource functions |
| 6 | `date.today()` in cached function | **MEDIUM** | Dates computed inside cached functions freeze at cache time. Pass date as a parameter so the cache key changes daily |
| 7 | Mutable cache parameters | **MEDIUM** | `dict`, `list` as function args break `@st.cache_data` (unhashable). Convert to `tuple` or use `str` keys |
| 8 | `session_state` flag gating CSS | **MEDIUM** | Streamlit rebuilds DOM each rerun but session_state persists. CSS injected conditionally via session_state flag disappears on rerun |

```python
# ❌ cache_resource.clear() nukes ALL cached resources
st.cache_resource.clear()  # Clears DB adapters, ML models, everything!

# ✅ Clear only the specific function's cache
get_database_adapter.clear()  # Targeted invalidation
```

```python
# ❌ Frozen date in cached function
@st.cache_data(ttl=timedelta(hours=1))
def get_daily_stats():
    today = date.today()  # Frozen when first cached!
    return fetch_stats(today)

# ✅ Pass date as parameter (changes cache key daily)
@st.cache_data(ttl=timedelta(hours=1))
def get_daily_stats(date_str: str):
    return fetch_stats(date_str)
```

---

## Session State Management

### Initialize State

```python
def init_session_state():
    """Initialize session state with defaults."""
    defaults = {
        "authenticated": False,
        "current_user": None,
        "selected_filters": {},
        "page_number": 1,
        "items_per_page": 25
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Call at app start
init_session_state()
```

### State Management Pattern

```python
# ❌ BAD: Direct mutation
st.session_state.filters = {}

# ✅ GOOD: Use callbacks for widget state
def on_filter_change():
    st.session_state.page_number = 1  # Reset pagination

st.selectbox(
    "Category",
    options=categories,
    key="category_filter",
    on_change=on_filter_change
)
```

---

## Multi-Page Applications

### Directory Structure

```
app/
├── Home.py                    # Main entry point (named Home.py for nice display)
├── pages/
│   ├── 1_🔍_Search.py         # Emoji prefixes for visual appeal
│   ├── 2_📊_Analytics.py
│   ├── 3_📤_Import.py
│   └── 4_⚙️_Settings.py
├── components/
│   ├── shared_header.py       # Fixed header with navigation
│   ├── kpi_cards.py
│   └── charts.py
├── assets/
│   └── logo.svg               # Logo file
└── styles/
    └── theme.css              # External CSS theme
```

### PREFERRED: Fixed Header Navigation (No Sidebar)

For apps using fixed header navigation, use a fixed header with navigation instead of sidebar:

```python
# src/components/shared_header.py
import streamlit as st
import base64
from pathlib import Path

BRAND_PRIMARY = "<BRAND_PRIMARY>"  # from project-config.md
BRAND_SECONDARY = "<BRAND_SECONDARY>"  # from project-config.md
GRAY_500 = "#7D7D7D"
GRAY_100 = "#D9D9D9"
HEADER_HEIGHT = "60px"


def get_logo_base64() -> str:
    """Encode SVG as base64 for safe embedding (avoids HTML escaping issues)."""
    logo_path = Path(__file__).parent.parent / "assets" / "logo.svg"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/svg+xml;base64,{logo_data}" alt="Logo" style="height: 28px;">'
    return ""


def hide_sidebar():
    """Hide sidebar completely including arrows during initial load."""
    st.markdown(\"\"\"
    <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"],
        div[data-testid="collapsedControl"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
        }
        header[data-testid="stHeader"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }
    </style>
    \"\"\", unsafe_allow_html=True)


def inject_fixed_header_styles():
    """CSS for fixed header that stays at top while content scrolls."""
    st.markdown(f\"\"\"
    <style>
        .vm-fixed-header {{
            position: fixed !important;
            top: 0;
            left: 0;
            right: 0;
            height: {HEADER_HEIGHT};
            background: white;
            border-bottom: 1px solid {GRAY_100};
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
            z-index: 999999;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
        }}
        
        .main .block-container {{
            padding-top: calc({HEADER_HEIGHT} + 2rem) !important;
        }}
        
        .app-nav-link {{
            color: {GRAY_500};
            text-decoration: none;
            padding: 0.5rem 0.875rem;
            border-radius: 6px;
            font-size: 0.875rem;
        }}
        
        .app-nav-link:hover {{ background: {GRAY_100}; color: {BRAND_SECONDARY}; }}
        .app-nav-link.active {{ background: #F28B82; color: {BRAND_PRIMARY}; }}
    </style>
    \"\"\", unsafe_allow_html=True)


def render_header(current_page: str = "Home"):
    \"\"\"Render fixed header with navigation.\"\"\"
    hide_sidebar()
    inject_fixed_header_styles()
    
    logo_img = get_logo_base64()
    nav_items = [("Home", "/"), ("Search", "/Search"), ("Analytics", "/Analytics")]
    
    nav_html = "".join(
        f'<a href="{url}" class="app-nav-link {"active" if name == current_page else ""}">{name}</a>'
        for name, url in nav_items
    )
    
    st.markdown(f\"\"\"
    <div class="vm-fixed-header">
        <div style="display: flex; align-items: center; gap: 8px;">
            {logo_img}
            <span style="color: {BRAND_PRIMARY}; font-weight: 700; font-size: 1.5rem;"><ORG_NAME></span>
            <span style="color: {GRAY_500};">App Title</span>
        </div>
        <nav style="display: flex; gap: 0.25rem;">{nav_html}</nav>
    </div>
    \"\"\", unsafe_allow_html=True)
```

### Using Fixed Header in Pages

```python
# src/pages/1_🔍_Search.py
from src.components.shared_header import apply_page_config, render_header

apply_page_config("Search", "🔍")  # MUST be first Streamlit command
render_header(current_page="Search")

# Page content here...
```

---

### LEGACY: Sidebar Navigation (Only for 6+ sections)

```python
# components/sidebar.py
import streamlit as st

def render_sidebar():
    """Render consistent sidebar across pages."""
    with st.sidebar:
        st.image("assets/logo.png", width=150)
        st.markdown("---")
        
        # User info
        if st.session_state.get("authenticated"):
            st.write(f"👤 {st.session_state.current_user}")
            if st.button("Logout", type="secondary"):
                st.session_state.authenticated = False
                st.rerun()
        
        st.markdown("---")
        
        # Common filters
        st.subheader("Filters")
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=30), datetime.now())
        )
        
        return {"date_range": date_range}
```

---

## Data Display Patterns

### DataFrames

```python
# Configure display
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "complaint_id": st.column_config.TextColumn("ID", width="small"),
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=["Open", "In Progress", "Resolved"],
            required=True
        ),
        "created_at": st.column_config.DatetimeColumn(
            "Created",
            format="DD/MM/YYYY HH:mm"
        ),
        "priority": st.column_config.NumberColumn(
            "Priority",
            format="%d ⭐"
        )
    }
)
```

### Metrics

```python
# KPI row with brand styling
def render_kpis(metrics: dict):
    cols = st.columns(4)
    
    for col, (label, value, delta) in zip(cols, metrics.items()):
        with col:
            st.metric(
                label=label,
                value=value,
                delta=delta,
                delta_color="normal"
            )
```

### KPI Info Tooltip Component

For KPIs that need validation or explanation, use a **CSS-based hover tooltip** with a small circled `?` icon. This is non-intrusive and follows common UX patterns.

**Pattern name:** `kpi-info-tooltip`

```python
# Step 1: Inject CSS once at page level
st.markdown("""
<style>
/* Tooltip container */
.kpi-tooltip-container {
    position: relative;
    display: inline-block;
}
/* The info icon - small circled question mark */
.kpi-info-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #7D7D7D;
    color: white;
    font-size: 11px;
    font-weight: 600;
    cursor: help;
    margin-left: 6px;
    vertical-align: middle;
    transition: background 0.2s;
}
.kpi-info-icon:hover {
    background: #4A4A4A;
}
/* Tooltip box */
.kpi-tooltip-container .kpi-tooltip-text {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    z-index: 1000;
    background-color: #4A4A4A;
    color: white;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 12px;
    white-space: nowrap;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
    transition: opacity 0.2s, visibility 0.2s;
}
/* Tooltip arrow */
.kpi-tooltip-container .kpi-tooltip-text::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: #4A4A4A transparent transparent transparent;
}
/* Show tooltip on hover */
.kpi-tooltip-container:hover .kpi-tooltip-text {
    visibility: visible;
    opacity: 1;
}
</style>
""", unsafe_allow_html=True)

# Step 2: Use in KPI rendering
def render_kpi_with_info(value: str, tooltip_content: str):
    """Render KPI value with hover tooltip."""
    tooltip_html = (
        f'<span class="kpi-tooltip-container">'
        f'<span class="kpi-info-icon">?</span>'
        f'<span class="kpi-tooltip-text">{tooltip_content}</span>'
        f'</span>'
    )
    st.markdown(
        f"<p style='font-size: 1.75rem; font-weight: 700;'>"
        f"{value}{tooltip_html}</p>",
        unsafe_allow_html=True
    )

# Example usage:
render_kpi_with_info(
    value="439",
    tooltip_content=(
        "<strong>Cross-Validation</strong><br>"
        "Cisco: 439<br>"
        "Qfiniti: 387<br>"
        "Variance: 13.4%"
    )
)
```

**When to use:**
- Cross-validation indicators (comparing two data sources)
- Calculation explanations (how a metric is derived)
- Data freshness indicators
- Any KPI needing contextual help

**Alternatives:**
- `st.metric(help="...")` - Native Streamlit tooltip (less customizable)
- `st.popover()` - For detailed info requiring interaction

### Charts with Plotly

```python
import plotly.express as px

def create_trend_chart(df: pd.DataFrame) -> go.Figure:
    """Create trend chart with project branding."""
    fig = px.line(
        df,
        x="date",
        y="count",
        color="category",
        color_discrete_sequence=["#E30613", "#5A2D82", "#A61A07"]
    )
    
    fig.update_layout(
        template="plotly_white",
        font_family="Inter, sans-serif",
        title_font_size=18,
        legend_title_text="",
        hovermode="x unified"
    )
    
    return fig

st.plotly_chart(create_trend_chart(df), width="stretch")
```

### Preventing Chart Text/Data Truncation

When using bar charts with `textposition='outside'`, labels can be clipped:

```python
# ✅ GOOD: Prevent text clipping in bar charts
import plotly.graph_objects as go

fig = go.Figure(go.Bar(
    x=values,
    y=categories,
    orientation='h',
    text=[f"{v:,}" for v in values],
    textposition='outside',
    cliponaxis=False,  # CRITICAL: Prevents text clipping
))

max_value = max(values)
fig.update_layout(
    xaxis=dict(range=[0, max_value * 1.15]),  # 15% padding
    margin=dict(r=60),  # Right margin for horizontal bars
)
```

**Key settings to prevent truncation:**
- `cliponaxis=False` on the trace
- Axis range with 10-20% padding beyond max value
- Margin on the side where text appears (right for horizontal, top for vertical)

---

## Form Handling

```python
with st.form("complaint_form", clear_on_submit=True):
    st.subheader("New Complaint")
    
    customer_id = st.text_input("Customer ID*", placeholder="CUST001")
    complaint_type = st.selectbox(
        "Type*",
        options=["Billing", "Service", "Technical"]
    )
    description = st.text_area(
        "Description*",
        placeholder="Describe the issue...",
        max_chars=2000
    )
    priority = st.slider("Priority", 1, 5, 3)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        submitted = st.form_submit_button("Submit", type="primary")
    with col2:
        if st.form_submit_button("Clear"):
            st.rerun()
    
    if submitted:
        if not customer_id or not description:
            st.error("Please fill in all required fields")
        else:
            # Process form
            save_complaint(customer_id, complaint_type, description, priority)
            st.success("Complaint submitted successfully!")
```

---

## Error Handling

```python
from loguru import logger

def render_with_error_handling():
    """Render page with proper error handling."""
    try:
        data = load_data()
        render_dashboard(data)
    except ConnectionError as e:
        logger.error(f"Database connection failed: {e}")
        st.error(
            "Unable to connect to database. Please try again later.",
            icon="🔌"
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        st.error(
            "An unexpected error occurred. Please contact support.",
            icon="⚠️"
        )
```

---

## Performance Tips

1. **Minimize reruns**: Use `st.session_state` and callbacks
2. **Cache aggressively**: Data fetches, computations, model loading
3. **Lazy loading**: Only load data when needed
4. **Pagination**: For large datasets, paginate display

```python
# Pagination pattern
def paginate_df(df: pd.DataFrame, page: int, per_page: int) -> pd.DataFrame:
    """Return paginated slice of dataframe."""
    start = (page - 1) * per_page
    end = start + per_page
    return df.iloc[start:end]

# Usage
total_pages = (len(df) - 1) // st.session_state.items_per_page + 1

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.session_state.page_number = st.number_input(
        f"Page (of {total_pages})",
        min_value=1,
        max_value=total_pages,
        value=st.session_state.page_number
    )

paginated_df = paginate_df(
    df,
    st.session_state.page_number,
    st.session_state.items_per_page
)
st.dataframe(paginated_df)
```

---

## Framework Limitations & Workarounds

### Streamlit DOM Wrapping (CRITICAL)

Streamlit wraps every `st.markdown(unsafe_allow_html=True)` call in **20-30 nested `<div>` containers** with auto-generated classes. This fundamentally breaks CSS approaches that rely on DOM position:

| CSS Technique | Works? | Why |
|---------------|--------|-----|
| `position: fixed` | **NO** | Wrapper divs create new stacking contexts and `overflow: hidden` boundaries |
| `position: absolute` | **NO** | Positioned relative to nearest Streamlit wrapper, not `<body>` |
| `z-index` escalation | **NO** | Streamlit's own z-index layers (header, sidebar, modals) compete and win |
| `!important` overrides | **FRAGILE** | Class names change between Streamlit versions |

### When to Use Each Rendering Approach

| Approach | Use For | Limitations |
|----------|---------|-------------|
| `st.markdown(unsafe_allow_html=True)` | Inline styling, cards, badges, formatted text | Wrapped in nested divs; no DOM control |
| `st.html()` | Self-contained HTML snippets | Renders in **sandboxed iframe**; no access to parent DOM |
| `components.declare_component()` | **Floating UI, chat widgets, FABs, toasts, modals** | Requires HTML/JS file; bi-directional communication via `setComponentValue` |

### Floating UI Pattern (declare_component)

For any UI element that must float above the page (chat widgets, floating action buttons, toast notifications, modals), use `streamlit.components.v1.declare_component()`:

```python
from streamlit.components.v1 import declare_component
from pathlib import Path

# Register component with path to HTML/JS frontend
_component = declare_component(
    "my_floating_widget",
    path=str(Path(__file__).parent / "my_frontend")
)

def render_floating_widget(**kwargs):
    """Render floating widget via zero-height iframe that injects into parent DOM."""
    return _component(
        key="my_widget",
        height=0,  # Zero-height iframe — widget renders in parent document.body
        **kwargs
    )
```

**Frontend pattern** (`my_frontend/index.html`):
```html
<script>
// Inject widget directly into parent document body (escapes Streamlit DOM)
const container = window.parent.document.createElement('div');
container.id = 'my-floating-widget';
window.parent.document.body.appendChild(container);

// Communication: JS → Python
window.parent.Streamlit.setComponentValue({ action: "click", data: "..." });

// Communication: Python → JS (received via streamlit:render event)
window.addEventListener("message", (event) => {
    if (event.data.type === "streamlit:render") {
        const args = event.data.args;
        // Update widget with args from Python
    }
});
</script>
```

**Key design decisions:**
- `height=0` makes the iframe invisible; the widget lives in `window.parent.document.body`
- Bi-directional: Python → JS via render args; JS → Python via `setComponentValue()`
- Use sequence numbers (`seq`) to deduplicate re-renders (Streamlit reruns the full script on every interaction)

> **Lesson learned (2026-02):** Six rounds of CSS/JS patches on a chat widget FAB failed before this architectural pivot. The `declare_component()` approach is the **only reliable way** to create floating UI in Streamlit.

---

## Checklist

- [ ] Page config set with proper title and icon
- [ ] Project branding applied consistently
- [ ] Session state initialized with defaults
- [ ] Data cached with appropriate TTL
- [ ] Error handling with user-friendly messages
- [ ] Forms have validation
- [ ] Large datasets paginated
- [ ] Using `<SHARED_LIBS>` for shared components

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values. The profile defines `<ORG_NAME>`, `<BRAND_PRIMARY>`, `<SHARED_LIBS>`, and other project-specific tokens.
