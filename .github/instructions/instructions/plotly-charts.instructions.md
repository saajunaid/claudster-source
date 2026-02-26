---
description: "Plotly chart best practices to avoid common issues like 'undefined' labels"
applyTo: "**/*.py"
---

# Plotly Chart Guidelines

Best practices for creating Plotly charts in Streamlit applications.

## Critical: Avoiding "undefined" Labels

### The Problem

When passing `title=None` or an empty/whitespace title directly to Plotly Express functions (`px.pie()`, `px.bar()`, `px.line()`, etc.), some browsers/versions may render "undefined" as the chart title.

```python
# ❌ BAD: Passing None or empty title to px functions can show "undefined"
fig = px.pie(
    data,
    names="category",
    values="count",
    title=None,  # May render as "undefined" in some browsers
)

# ❌ BAD: Passing title=chart_title where chart_title might be None
chart_title = title if title else None
fig = px.bar(data, x="x", y="y", title=chart_title)  # Risky!
```

### The Solution

**Never pass the `title` parameter to Plotly Express functions.** Instead, set the title explicitly in `fig.update_layout()` using an empty string when no title is desired:

```python
# ✅ GOOD: Don't pass title to px, set it in update_layout
chart_title = title if title and title.strip() else None

fig = px.pie(
    data,
    names="category",
    values="count",
    # NO title parameter here!
)

# Explicitly set title - use empty string for no title
fig.update_layout(
    title=chart_title if chart_title else "",
    height=300,
)
```

### Complete Pattern

```python
def render_my_chart(
    data: pd.DataFrame,
    title: str | None = None,
    height: int = 300,
) -> None:
    """Render a chart with proper title handling."""
    if data.empty:
        st.info("No data available")
        return

    # Determine if we have a valid title
    chart_title = title if title and title.strip() else None

    # Create figure WITHOUT title parameter
    fig = px.bar(
        data,
        x="category",
        y="value",
        color="category",
        # DO NOT include title here
    )

    # Apply layout with explicit title handling
    fig.update_layout(
        height=height,
        showlegend=False,
        title=chart_title if chart_title else "",  # Empty string, not None!
    )

    st.plotly_chart(fig, use_container_width=True)
```

### Why This Works

1. Plotly Express internally handles `title=None` inconsistently across versions
2. When `update_layout(title="")` is called, it explicitly sets an empty title
3. An empty string `""` is rendered as nothing, while `None` may be converted to "undefined" by JavaScript

## Additional Chart Best Practices

### Preventing Text/Data Truncation

When using `textposition='outside'` on bar charts, text labels can be clipped. **Always** prevent this:

```python
# ❌ BAD: Text labels get clipped at chart edges
fig = go.Figure(go.Bar(
    x=values,
    y=categories,
    orientation='h',
    text=[f"{v:,}" for v in values],
    textposition='outside',  # Text appears outside bars
))

# ✅ GOOD: Prevent text clipping with these THREE steps:
fig = go.Figure(go.Bar(
    x=values,
    y=categories,
    orientation='h',
    text=[f"{v:,}" for v in values],
    textposition='outside',
    cliponaxis=False,  # 1. Prevent clipping at axis boundary
))

# 2. Add padding to axis range for text labels
max_value = max(values)
fig.update_layout(
    xaxis=dict(
        range=[0, max_value * 1.15],  # 15% padding for outside text
    ),
    # 3. Add right margin for horizontal bars (or top margin for vertical)
    margin=dict(r=60),  # Right margin for text labels
)
```

### Key Points for Text Labels:

1. **`cliponaxis=False`**: Prevents text from being cut off at axis boundaries
2. **Axis range padding**: Add 10-20% extra range beyond max value
3. **Margin adjustment**: Add margin on the side where text appears
4. **For vertical bars**: Use `margin=dict(t=60)` for top margin
5. **For horizontal bars**: Use `margin=dict(r=60)` for right margin

### Unique Keys for Charts

Always provide unique keys to prevent Streamlit duplicate element errors:

```python
# ✅ GOOD: Use hash of data for unique keys
chart_key = f"chart_{hash(str(data.to_dict()))}_{id(data)}"
st.plotly_chart(fig, use_container_width=True, key=chart_key)
```

### Margin Adjustment Based on Title

Adjust top margin based on whether a title is present:

```python
def _apply_layout(fig: go.Figure, has_title: bool = True) -> go.Figure:
    """Apply consistent layout with proper margins."""
    top_margin = 60 if has_title else 20
    
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=40, r=40, t=top_margin, b=40),
    )
    return fig
```

### Color Consistency

Use the brand color palette (from project-config.md) defined in charts.py:

```python
CHART_COLORS = [
    "#3B82F6",  # Blue
    "#10B981",  # Emerald
    "#8B5CF6",  # Violet
    "#F59E0B",  # Amber
    "#06B6D4",  # Cyan
    "#EC4899",  # Pink
    "#6366F1",  # Indigo
    "#84CC16",  # Lime
    "#14B8A6",  # Teal
    "#F97316",  # Orange
]
```

## When NOT to Use Charts

Per UX design principles, avoid charts when:

1. **Single data point**: Use a metric card instead
2. **Two or fewer categories**: Use metric cards with comparison
3. **Data is primarily text-based**: Use tables or lists
4. **Exact values matter more than proportions**: Use tables

```python
# ❌ BAD: Pie chart for single value
interaction_types = {"Phone": 3975}  # Only one type!
# Don't use a pie chart here

# ✅ GOOD: Use metric card
st.metric("📞 Phone Interactions", f"{3975:,}")
```

## Deprecation Warning Fix

Replace deprecated `use_container_width` with `width`:

```python
# ❌ DEPRECATED (after 2025-12-31)
st.plotly_chart(fig, use_container_width=True)

# ✅ NEW SYNTAX
st.plotly_chart(fig, width="stretch")  # For full width
st.plotly_chart(fig, width="content")  # For content width
```
