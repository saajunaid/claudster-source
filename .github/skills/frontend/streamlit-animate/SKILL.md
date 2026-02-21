---
name: streamlit-animate
description: >
  Use this skill when adding animations or micro-interactions to an existing
  Streamlit application. Covers enterprise-safe hover effects, skeleton loaders,
  expander transitions, and gradient accents via CSS injection. Always combine
  with the streamlit-dev skill when building or modifying the broader app.
---

# streamlit-animate

This skill adds **minimal, enterprise-safe micro-interactions** to Streamlit pages
via CSS injection (`st.markdown` with `unsafe_allow_html=True`).

Use this skill **only when the user explicitly asks for animation or visual polish**
on a Streamlit page. For all other Streamlit development, defer to the
`streamlit-dev` skill.

---

## Ground Rules

Before writing a single line of CSS, confirm all three:

1. The deployment context is **not** regulated (no fintech, healthcare, legal UIs)
2. The audience is **internal, demo, or exploratory** — not public-facing production
3. Visual polish was explicitly requested

When in doubt, keep this skill disabled and ship without animation.

---

## How Animation Works in Streamlit

Streamlit has no built-in animation API. All motion is injected via a single
CSS block placed at the top of the page:

```python
st.markdown("""
<style>
/* All animation CSS goes here */
</style>
""", unsafe_allow_html=True)
```

This must be the **first `st` call** after imports so styles apply before
components render. Never scatter multiple `<style>` blocks across the page —
one block, one source of truth.

---

## Allowed Animations

### 1. Card Hover Elevation

Adds a subtle lift when the user hovers over a metric card or container.
Maximum shadow depth: 2px. No color shift. No size change.

```python
st.markdown("""
<style>
div[data-testid="stMetric"],
div[data-testid="stVerticalBlock"] > div {
    transition: box-shadow 150ms ease, transform 150ms ease;
}

div[data-testid="stMetric"]:hover,
div[data-testid="stVerticalBlock"] > div:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)
```

**Constraints:** `transition` duration must be 100–200ms. `transform` max is
`translateY(-2px)`. Never change background color on hover.

---

### 2. Expander Open/Close Transition

Smooths the expand/collapse motion on `st.expander` elements.

```python
st.markdown("""
<style>
div[data-testid="stExpander"] details summary ~ div {
    transition: opacity 200ms ease;
}

div[data-testid="stExpander"] details:not([open]) summary ~ div {
    opacity: 0;
}

div[data-testid="stExpander"] details[open] summary ~ div {
    opacity: 1;
}
</style>
""", unsafe_allow_html=True)
```

**Note:** Streamlit manages the `open` attribute natively — this CSS hooks into
that attribute without overriding Streamlit's click handler.

---

### 3. Skeleton Loader (Async AI Generation)

Use during long-running AI or data generation calls to show a placeholder
instead of a spinner. Renders a shimmering grey bar in place of content.

```python
def skeleton_placeholder(n_lines: int = 3) -> str:
    lines = "".join(
        f'<div class="sk-line" style="width:{70 + (i * 7) % 25}%"></div>'
        for i in range(n_lines)
    )
    return f'<div class="sk-block">{lines}</div>'


st.markdown("""
<style>
@keyframes sk-shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
}

.sk-block {
    padding: 12px 0;
}

.sk-line {
    height: 14px;
    margin-bottom: 10px;
    border-radius: 4px;
    background: linear-gradient(
        90deg,
        #e8e8e8 25%,
        #f5f5f5 50%,
        #e8e8e8 75%
    );
    background-size: 800px 100%;
    animation: sk-shimmer 1.4s linear infinite;
}
</style>
""", unsafe_allow_html=True)

# Usage
placeholder = st.empty()
placeholder.markdown(skeleton_placeholder(3), unsafe_allow_html=True)

result = run_expensive_operation()   # your AI/data call

placeholder.empty()
st.write(result)
```

**Constraints:** Skeleton shimmer is the **only** animation permitted to
auto-play. It must be replaced (`.empty()`) immediately when content is ready.
Never leave a skeleton visible after data loads.

---

### 4. Gradient Accent Borders

Adds a thin gradient line as a left-border indicator on callout or info cards.
Used only to draw attention to a section — never as decoration.

```python
st.markdown("""
<style>
div[data-testid="stAlert"],
div.callout-card {
    border-left: 3px solid;
    border-image: linear-gradient(180deg, #4F8EF7, #A78BFA) 1;
    padding-left: 12px;
}
</style>
""", unsafe_allow_html=True)
```

**Constraints:** Max border width 3px. Gradient must be vertical (180deg).
Never apply to data tables, charts, or input widgets.

---

## Prohibited Patterns

Never introduce any of the following, regardless of user request:

| Pattern | Reason |
|---|---|
| `animation` on backgrounds | Distracting, breaks screenshot fidelity |
| `@keyframes` on text | Implies urgency or status change |
| Looping `pulse` / `blink` on any element | Accessibility violation (WCAG 2.3.3) |
| Motion not triggered by user interaction | Violates enterprise motion policy |
| Animated gradients on chart containers | Conflicts with Plotly/Altair rendering |
| CSS applied to `stDataFrame` rows | Breaks sort/filter interaction states |

If a user requests a prohibited pattern, explain why it is excluded and offer
the nearest permitted alternative.

---

## Streamlit Selector Reference

Streamlit's data-testid attributes are the stable hook for CSS targeting.
Use these — never target internal class names (they change with Streamlit versions).

| Element | Selector |
|---|---|
| Metric card | `div[data-testid="stMetric"]` |
| Expander | `div[data-testid="stExpander"]` |
| Alert / info box | `div[data-testid="stAlert"]` |
| Sidebar | `section[data-testid="stSidebar"]` |
| Button | `div[data-testid="stButton"] > button` |
| Column block | `div[data-testid="stHorizontalBlock"]` |

---

## Integration with streamlit-dev

This skill handles **only** CSS injection and animation logic. It does not
scaffold apps, manage state, or define page structure. When animation is one
part of a larger Streamlit task:

1. Read `streamlit-dev` SKILL.md first to handle app structure
2. Apply this skill's patterns at the end, inside a dedicated `apply_animations()`
   helper function called at the top of each page

```python
# page.py
import streamlit as st
from animations import apply_animations   # isolated module

apply_animations()   # injects all CSS — always first

st.title("My Dashboard")
# ... rest of page
```

Keeping animations in a single isolated module makes them easy to disable
for regulated deployments without touching page logic.

---

## Quality Checklist

Before finishing, confirm:

- [ ] All animations are user-initiated (except skeleton loader)
- [ ] No `animation-duration` exceeds 300ms
- [ ] No `transform` exceeds 2px translation or 1.02 scale
- [ ] The page looks identical in a static screenshot
- [ ] CSS is in one `st.markdown` block at page top
- [ ] A `apply_animations()` helper isolates all injection
- [ ] Skeleton loader is cleared immediately after data loads
- [ ] No prohibited patterns from the table above are present
