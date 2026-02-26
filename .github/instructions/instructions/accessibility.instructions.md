---
description: 'Accessibility (a11y) development guidelines for WCAG 2.2 compliance'
applyTo: '**/*.html, **/*.css, **/*.py, **/*.tsx, **/*.jsx'
---

# Accessibility (a11y) Instructions

Guidelines for creating accessible code that conforms to WCAG 2.2 Level AA and provides inclusive experiences for users with disabilities.

## Core Principles (POUR)

### 1. Perceivable
Information must be presentable to users in ways they can perceive.

### 2. Operable
User interface components must be operable.

### 3. Understandable
Information and operation must be understandable.

### 4. Robust
Content must be robust enough for assistive technologies.

## Key Requirements

### Color and Contrast

#### Minimum Contrast Ratios (WCAG AA)
| Element | Ratio | Example |
|---------|-------|---------|
| Normal text | 4.5:1 | #1F2937 on #FFFFFF (13.5:1) ✓ |
| Large text (18pt+) | 3:1 | #4B5563 on #FFFFFF (6.2:1) ✓ |
| UI components | 3:1 | #E10A0A border on #FFFFFF ✓ |
| Focus indicators | 3:1 | #3B82F6 outline on #FFFFFF ✓ |

#### Color as Sole Indicator
Never use color alone to convey information:

```html
<!-- ❌ Bad: Color only -->
<span class="text-red-500">Error</span>

<!-- ✅ Good: Color + icon + text -->
<span class="text-red-500">
    <svg aria-hidden="true"><!-- error icon --></svg>
    Error: Invalid email format
</span>
```

### Keyboard Navigation

#### Focus Order
```html
<!-- Focus should follow logical reading order -->
<header><!-- Tab 1 --></header>
<nav><!-- Tab 2-5 --></nav>
<main><!-- Tab 6+ --></main>
<footer><!-- Last tabs --></footer>
```

#### Focus Visibility
```css
/* Always provide visible focus indicators */
:focus {
    outline: 2px solid #3B82F6;
    outline-offset: 2px;
}

/* Enhance for keyboard users */
:focus-visible {
    outline: 3px solid #3B82F6;
    outline-offset: 2px;
}

/* NEVER do this */
:focus { outline: none; } /* ❌ */
```

#### Skip Links
```html
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    <header>...</header>
    <nav>...</nav>
    <main id="main">...</main>
</body>

<style>
.skip-link {
    position: absolute;
    left: -9999px;
    top: auto;
    width: 1px;
    height: 1px;
    overflow: hidden;
}

.skip-link:focus {
    position: fixed;
    top: 0;
    left: 0;
    width: auto;
    height: auto;
    padding: 0.5rem 1rem;
    background: #E10A0A;
    color: white;
    z-index: 9999;
}
</style>
```

### Semantic HTML

```html
<!-- Use semantic elements -->
<header>Site header</header>
<nav aria-label="Main navigation">Navigation</nav>
<main>
    <article>
        <h1>Page Title</h1>
        <section aria-labelledby="section-heading">
            <h2 id="section-heading">Section</h2>
        </section>
    </article>
    <aside>Sidebar</aside>
</main>
<footer>Site footer</footer>
```

### Heading Hierarchy

```html
<!-- ✅ Correct hierarchy -->
<h1>Page Title</h1>
    <h2>Section 1</h2>
        <h3>Subsection 1.1</h3>
        <h3>Subsection 1.2</h3>
    <h2>Section 2</h2>

<!-- ❌ Skipped levels -->
<h1>Page Title</h1>
    <h3>Oops, skipped h2</h3>
```

### Forms

```html
<form>
    <!-- Labels associated with inputs -->
    <div class="form-group">
        <label for="email">Email Address</label>
        <input 
            type="email" 
            id="email" 
            name="email"
            aria-required="true"
            aria-describedby="email-help email-error"
        >
        <span id="email-help" class="help-text">
            We'll never share your email
        </span>
        <span id="email-error" class="error" role="alert" hidden>
            Please enter a valid email address
        </span>
    </div>

    <!-- Grouped fields -->
    <fieldset>
        <legend>Notification Preferences</legend>
        <input type="checkbox" id="notify-email" name="notify">
        <label for="notify-email">Email notifications</label>
    </fieldset>

    <!-- Error summary at top -->
    <div role="alert" aria-live="polite" id="error-summary">
        <!-- Dynamically populated with error list -->
    </div>
</form>
```

### Images

```html
<!-- Informative images need alt text -->
<img src="chart.png" alt="Revenue increased 25% in Q4 2024">

<!-- Decorative images use empty alt -->
<img src="decorative.png" alt="">

<!-- Complex images need long descriptions -->
<figure>
    <img src="architecture.png" 
         alt="System architecture diagram"
         aria-describedby="arch-desc">
    <figcaption id="arch-desc">
        The system has three layers: presentation (Streamlit),
        business logic (FastAPI), and data (SQL Server).
    </figcaption>
</figure>

<!-- Icon buttons -->
<button aria-label="Close dialog">
    <svg aria-hidden="true"><!-- close icon --></svg>
</button>
```

### ARIA Usage

```html
<!-- Live regions for dynamic content -->
<div aria-live="polite" role="status">
    Loading complete. 50 results found.
</div>

<!-- Expanded/collapsed state -->
<button aria-expanded="false" aria-controls="panel1">
    Toggle Panel
</button>
<div id="panel1" hidden>Panel content</div>

<!-- Modal dialogs -->
<div role="dialog" 
     aria-modal="true" 
     aria-labelledby="dialog-title"
     aria-describedby="dialog-desc">
    <h2 id="dialog-title">Confirm Action</h2>
    <p id="dialog-desc">Are you sure you want to proceed?</p>
</div>

<!-- Tabs -->
<div role="tablist" aria-label="Data views">
    <button role="tab" aria-selected="true" aria-controls="tab1">
        Overview
    </button>
    <button role="tab" aria-selected="false" aria-controls="tab2">
        Details
    </button>
</div>
<div role="tabpanel" id="tab1">Overview content</div>
<div role="tabpanel" id="tab2" hidden>Details content</div>
```

### Streamlit Accessibility

```python
import streamlit as st

# Proper heading hierarchy
st.title("Dashboard")  # h1
st.header("Overview")  # h2
st.subheader("Key Metrics")  # h3

# Descriptive labels
st.text_input("Email Address", key="email", help="Enter work email")
st.selectbox("Department", options=departments, help="Select your team")

# Alt text for images
st.image("chart.png", caption="Network traffic over 24 hours")

# Status messages for screen readers
st.success("✓ Data saved successfully")
st.error("⚠ Error: Failed to load data")

# Data table with caption
st.caption("Table 1: Customer data for Q4 2024")
st.dataframe(df)

# Chart accessibility
fig = px.line(df, x='date', y='value', title='Performance Trend')
st.plotly_chart(fig, use_container_width=True)
st.caption("Figure shows performance increasing 25% since January")
```

## Inclusive Language

- Use people-first language: "person using a screen reader" not "blind user"
- Avoid stereotypes about ability
- Be neutral and respectful in error messages
- Don't use color names alone: "click the red button" → "click Cancel"

## Testing Checklist

### Automated Testing
- [ ] Run axe-core or Accessibility Insights
- [ ] Check color contrast with tools
- [ ] Validate HTML for semantic issues
- [ ] Test with ESLint a11y rules

### Manual Testing
- [ ] Navigate with keyboard only (Tab, Enter, Escape, Arrow keys)
- [ ] Test with screen reader (NVDA, VoiceOver)
- [ ] Verify focus indicators are visible
- [ ] Check heading hierarchy
- [ ] Test at 200% zoom
- [ ] Test with high contrast mode

### Screen Reader Testing
```
NVDA Commands:
- H: Next heading
- 1-6: Headings by level
- F: Next form field
- B: Next button
- L: Next list
- T: Next table
```

## Tools and Resources

1. **Accessibility Insights**: https://accessibilityinsights.io/
2. **axe DevTools**: Browser extension for automated testing
3. **WAVE**: https://wave.webaim.org/
4. **Color Contrast Checker**: https://webaim.org/resources/contrastchecker/
5. **NVDA Screen Reader**: https://www.nvaccess.org/
6. **WCAG 2.2 Guidelines**: https://www.w3.org/TR/WCAG22/

## Best Practices Summary

1. **Structure**: Use semantic HTML and proper heading hierarchy
2. **Keyboard**: Make everything keyboard accessible with visible focus
3. **Color**: Maintain contrast ratios, don't rely on color alone
4. **Forms**: Associate labels, provide error messages
5. **Images**: Add meaningful alt text
6. **Dynamic**: Use ARIA live regions for updates
7. **Test**: Use automated tools AND manual testing
8. **Iterate**: Accessibility is ongoing, not a one-time task
