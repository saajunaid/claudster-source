---
name: ux-design
description: Design user experiences with consistent brand color system and accessibility standards
---

# UX Design

> **Project Context** — Read `project-config.md` in the repo root for brand tokens, color palette, and project metadata.

## When to Use

Invoke this skill when:
- Designing the UI/UX for a new dashboard or feature
- Planning navigation, layout, and information hierarchy
- Creating wireframes or mockups for apps
- Applying brand consistency to charts, cards, and components
- Reviewing accessibility compliance (WCAG 2.2 AA)
- Designing KPI card layouts and data visualizations
- Planning responsive design for internal dashboards

---

## Steps

### Step 1: User Research (JTBD Framework)

Define the user's job-to-be-done:

```
When I am [situation/context]
I want to [motivation/desired outcome]
So that I can [expected benefit]
```

**Example:**
```
When I am reviewing customer complaints
I want to quickly filter by status and priority
So that I can focus on urgent issues first
```

### Step 2: Define Information Architecture

**Navigation:** Fixed header (NOT sidebar) for apps with up to 5 sections.

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] App Title  │  Home  Search  Analytics                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    Main Content Area                        │
│                    (Full width, max 1600px)                 │
│                                                             │
│    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│    │  KPI 1  │ │  KPI 2  │ │  KPI 3  │ │  KPI 4  │       │
│    └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                             │
│    ┌───────────────────────────────────────────────┐       │
│    │              Primary Chart                     │       │
│    └───────────────────────────────────────────────┘       │
│                                                             │
│    ┌──────────────────┐  ┌──────────────────┐             │
│    │ Secondary Chart 1 │  │ Secondary Chart 2 │             │
│    └──────────────────┘  └──────────────────┘             │
└─────────────────────────────────────────────────────────────┘
```

**Content Hierarchy:**
1. KPI cards (most important metrics at top)
2. Primary chart (main trend/distribution)
3. Secondary charts (supporting analysis)
4. Data tables (detail level)
5. Filters (contextual, near the content they affect)

### Step 3: Apply Brand Color System

#### Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `BRAND_RED` | #E10A0A | CTAs, active states, accents (10%) |
| `BRAND_RED_HOVER` | #B30808 | Hover states |
| `BRAND_NAVY` | #1F2937 | Text, headers, dark elements (30%) |
| `GRAY_500` | #6C757D | Secondary text, muted labels |
| `GRAY_100` | #E9ECEF | Borders, dividers |
| `LIGHT_BG` | #F8F9FA | Page/card backgrounds (60%) |
| `SUCCESS` | #22C55E | Positive indicators |
| `WARNING` | #F59E0B | Warning indicators |
| `ERROR` | #EF4444 | Error/negative indicators |

#### 60-30-10 Color Rule
- **60%**: Light backgrounds (#F8F9FA, white)
- **30%**: Dark text and structure (#1F2937, #6C757D)
- **10%**: Brand red accents (#E10A0A) -- buttons, borders, highlights

#### CSS Custom Properties

```css
:root {
    --brand-red: #E10A0A;
    --brand-red-dark: #B30808;
    --brand-dark: #1F2937;
    --brand-light: #F8F9FA;
    --brand-gray-100: #E9ECEF;
    --brand-gray-500: #6C757D;
    --brand-success: #10B981;
    --brand-warning: #F59E0B;
    --brand-error: #DC2626;
    --brand-active-bg: #FEE2E2;
}
```

### Step 4: Design Fixed Header Navigation

```css
.app-fixed-header {
    position: fixed !important;
    top: 0; left: 0; right: 0;
    height: 60px;
    background: white;
    border-bottom: 1px solid var(--brand-gray-100);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
    z-index: 999999;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
}

/* Content offset for fixed header */
.main .block-container {
    padding-top: calc(60px + 2rem) !important;
    max-width: 1600px;
}

/* Nav link states */
.app-nav-link { color: var(--brand-gray-500); padding: 0.5rem 0.875rem; border-radius: 6px; }
.app-nav-link:hover { background: var(--brand-gray-100); color: var(--brand-dark); }
.app-nav-link.active { background: var(--brand-active-bg); color: var(--brand-red); font-weight: 600; }
```

**Header structure:**
- Left: Logo (base64 SVG) + App Title (gray)
- Right: Navigation links (gray, active = red on light red background)

### Step 5: Design KPI Cards

```python
# KPI card layout pattern
cols = st.columns(4)
metrics = [
    {"label": "Open Cases", "value": 42, "delta": -5},
    {"label": "Avg Resolution", "value": "2.3 days", "delta": 0.2},
    {"label": "SLA Compliance", "value": "94%", "delta": 2.1},
    {"label": "Customer Sat", "value": "4.2/5", "delta": 0.1},
]

for col, metric in zip(cols, metrics):
    with col:
        st.metric(**metric)
```

**KPI with Info Tooltip (for cross-validation):**

```
┌─────────────────────────────────┐
│  Calls Offered                  │
│  ┌─────────────────────────┐   │
│  │ 1,088 [?]               │   │ ← Small gray circled ?
│  └─────────────────────────┘   │
│  [Mobile Calls]                 │
└─────────────────────────────────┘

On hover over [?]:
       ┌─────────────────────┐
       │ Cross-Validation    │
       │ ─────────────────── │
       │ Cisco: 439          │
       │ Qfiniti: 387        │
       │ Variance: 13.4%     │
       └─────────────────────┘
```

### Step 6: Theme Plotly Charts

```python
CHART_COLORS = ["#E10A0A", "#1F2937", "#6B7280", "#9CA3AF", "#D1D5DB"]

def apply_brand_theme(fig):
    """Apply brand theming to any Plotly figure."""
    fig.update_layout(
        template="plotly_white",
        font_family="Inter, sans-serif",
        title_font_size=18,
        title_font_color="#1F2937",
        legend_title_text="",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig
```

### Step 7: Ensure Accessibility (WCAG 2.2 AA)

| Requirement | Standard | Verification |
|-------------|----------|-------------------|
| Text contrast | 4.5:1 minimum | #1F2937 on #FFFFFF = 13.5:1 |
| Large text contrast | 3:1 minimum | #FFFFFF on #E10A0A = 4.6:1 |
| UI component contrast | 3:1 minimum | All borders/icons meet |
| Touch targets | 44px minimum | Buttons, links, nav items |
| Focus indicators | Visible | Tab navigation works |
| Alt text | All images | SVG logos have alt attributes |
| Form labels | Descriptive | All inputs labeled |
| Color not sole indicator | Additional cues | Icons + color for status |

---

## Patterns and Examples

### Dashboard Layout (Full Page)

```python
# KPI row
render_kpi_row(kpi_data)

# Primary chart (full width)
st.plotly_chart(trend_chart, use_container_width=True)

# Two-column secondary charts
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(distribution_chart, use_container_width=True)
with col2:
    st.plotly_chart(comparison_chart, use_container_width=True)

# Data table
st.dataframe(df, use_container_width=True, hide_index=True)
```

### Empty States

```python
if df.empty:
    st.info("No data found for the selected filters. Try adjusting your date range.")
    return
```

### Loading States

```python
with st.spinner("Loading dashboard..."):
    data = load_dashboard_data()
```

### Loading States for Entity Switch (CRITICAL)

For customer/account switch flows, define loading behavior to avoid stale-content flash:

- Use **one visual loader** only (single circular progress with percentage).
- Reserve a dedicated results region so loader replaces previous content immediately.
- While loading, hide high-recognition frames (customer identity banner and tabs) to avoid ghost UI.
- Show progress labels by stage (identity fetch → activity fetch → AI summary).
- After completion, rerun once to reveal the final state only.

UX acceptance criteria:

1. No old-customer identity frame visible at any point during loading.
2. No stale tab content visible while loader is active.
3. No overlapping loaders or mixed visual patterns.
4. Transition appears as: old state → single loader → new state.

---

## Checklist

- [ ] JTBD defined for target users
- [ ] Fixed header navigation (not sidebar)
- [ ] 60-30-10 rule color rule applied
- [ ] KPI cards at top of dashboard
- [ ] Charts themed with brand colors
- [ ] Plotly charts use `update_layout` (not `title=` in px call)
- [ ] WCAG 2.2 AA contrast ratios met
- [ ] Touch targets minimum 44px
- [ ] Empty states show helpful messages
- [ ] Loading spinners for data fetches
- [ ] Responsive layout tested (1024px+)
- [ ] No sidebar (hidden via CSS)

## Related Resources

| Resource | Path |
|----------|------|
| UI review skill | `skills/frontend/ui-review/SKILL.md` |
| Streamlit dev skill | `skills/frontend/streamlit-dev/SKILL.md` |
| Frontend instructions | `instructions/frontend.instructions.md` |
| Accessibility instructions | `instructions/accessibility.instructions.md` |
| UX Designer agent | `agents/ux-designer.agent.md` |
