---
name: mockup
description: Create framework-aware UI mockups with feasibility checks. Prevents wasted effort by validating that proposed designs work within the target framework's constraints.
---

# Mockup Skill

## Purpose

Create visual mockups (HTML/SVG) for UI features with **mandatory framework feasibility validation**. This skill exists because of a real incident: a beautiful HTML mockup was created for a Streamlit app using `position: fixed` — which doesn't work in Streamlit's DOM. 24 hours were wasted discovering this.

**This skill prevents that class of failure for ANY framework.**

---

## When to Use

- Creating a UI mockup for a proposed feature
- Visualizing a design before implementation
- Producing a reference artifact for implementing agents
- When `@ux-designer` or `@ui-ux-designer` routes mockup creation here

---

## Steps

### Step 1: Read Project Context

1. Read `project-config.md` → identify:
   - **Frontend framework** (Streamlit, React, Vue, Angular, Next.js, etc.)
   - **Brand colors** (from profile or placeholder values)
   - **CSS conventions** (scoping method, custom properties, etc.)
2. Read `copilot-instructions.md` → identify:
   - Existing component patterns
   - Framework-specific conventions already documented
3. If a `chain_id` is provided, read the Intent Document from `agent-docs/intents/`

### Step 2: Framework Feasibility Check (MANDATORY)

**Before creating ANY mockup, validate that the proposed design is feasible in the target framework.**

Run through this checklist:

| Check | Question | If NO |
|-------|----------|-------|
| **DOM Control** | Does the framework give you full control over the DOM? | Identify which HTML/CSS features are restricted |
| **Positioning** | Does `position: fixed/absolute` work as expected? | Document the limitation and alternative approach |
| **Custom HTML** | Can you inject arbitrary HTML/JS? | Identify the framework's component/extension API |
| **Event Handling** | Can you attach custom JS event listeners? | Document how events work in this framework |
| **Styling** | Can you use global CSS freely? | Document CSS scoping constraints |
| **Third-party Libraries** | Can you load external JS/CSS? | Check if air-gapped deployment restricts this |

#### Known Framework Constraints

| Framework | Key Constraints |
|-----------|----------------|
| **Streamlit** | No `position: fixed/absolute` (DOM wrapping breaks it). No arbitrary HTML injection without `components.html()` or `declare_component()`. CSS is scoped — use `st.container(key=)` + `.st-key-` selectors. No external CDN in air-gapped environments. |
| **React** | JSX required. CSS-in-JS or CSS Modules typical. Virtual DOM diffing may interfere with manual DOM manipulation. |
| **Vue** | Template syntax. Scoped styles by default. `v-html` for raw HTML but XSS risk. |
| **Gradio** | Similar DOM constraints to Streamlit. Limited CSS control. Use `gr.HTML()` for custom elements. |
| **Next.js** | SSR considerations. `useEffect` needed for client-only code. CSS Modules or Tailwind typical. |

> **If ANY constraint would prevent the proposed design from working:**
> 1. **STOP** — do not create a mockup that can't be implemented
> 2. **WARN** the user with specific details about what won't work and why
> 3. **PROPOSE ALTERNATIVES** that work within the framework's constraints
> 4. **Get confirmation** before proceeding with an alternative approach

### Step 3: Create the Mockup

**Output format**: HTML file (preferred for interactive mockups) or SVG (for static layouts)

**Requirements:**
- Use brand colors from `project-config.md` (never hardcode colors — use CSS custom properties)
- Include responsive behavior if applicable
- Add comments explaining key layout decisions
- If the mockup uses workarounds for framework constraints, document them clearly in comments

**HTML mockup template:**
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{Feature Name} — Mockup</title>
    <style>
        /* Brand colors from project-config.md */
        :root {
            --brand-primary: {<BRAND_PRIMARY>};
            --brand-dark: {<BRAND_DARK>};
            --brand-light: {<BRAND_LIGHT>};
            /* Additional colors from profile */
        }

        /* Mockup styles */
        /* ... */
    </style>
</head>
<body>
    <!-- MOCKUP: {Feature description} -->
    <!-- FRAMEWORK: {Target framework} -->
    <!-- CONSTRAINTS: {Any framework constraints that shaped this design} -->
    <!-- ALTERNATIVES: {If using a workaround, what was the original approach and why it wouldn't work} -->

    <!-- Mockup content -->
</body>
</html>
```

### Step 4: Write Artifact

1. Save the mockup file to `agent-docs/ux/mockups/{feature-slug}.html` (or `.svg`)
2. Add YAML header to a companion markdown file or embed as HTML comment:
   ```yaml
   agent: ux-designer (or ui-ux-designer)
   created: {date}
   status: current
   chain_id: {chain_id if provided}
   approval: pending
   framework: {target framework}
   feasibility_warnings: {list any constraints encountered}
   ```
3. Update `agent-docs/ARTIFACTS.md` manifest with the new entry

### Step 5: Report

Provide:
- Path to the mockup file
- Framework feasibility summary (what was checked, any warnings)
- Implementation notes for the agent that will build this (which API/component to use, what CSS approach works)
- If alternatives were chosen, explain why the original approach wouldn't work

---

## Framework Feasibility Quick Reference

### Streamlit-Specific

| Want to do | Don't use | Instead use |
|-----------|-----------|-------------|
| Floating element (chat widget, FAB) | `position: fixed/absolute` | `declare_component()` with custom HTML/JS |
| Custom styled container | Global CSS | `st.container(key="name")` + `.st-key-name` selector |
| Modal/overlay | `z-index` + absolute positioning | `st.dialog()` (Streamlit 1.33+) or `st.modal()` |
| Sidebar content | Custom sidebar HTML | `st.sidebar` API |
| Custom header | Fixed position header | `st.container()` at top + CSS with `st.container(key=)` |
| External JavaScript | `<script src="cdn...">` | Bundle locally for air-gapped; use `components.html()` |

### React-Specific

| Want to do | Watch out for | Recommended approach |
|-----------|---------------|---------------------|
| Direct DOM manipulation | React re-renders will overwrite | Use refs (`useRef`) or state-driven rendering |
| Global styles | May conflict with component styles | CSS Modules, styled-components, or Tailwind |
| Third-party widgets | jQuery plugins fight React | Find React-native alternatives or wrap in `useEffect` |

---

## Important Notes

- This skill is designed to be loaded by `@ux-designer`, `@ui-ux-designer`, or `@frontend-developer` agents
- The framework constraint tables should be extended as new frameworks and gotchas are discovered
- Always check `project-config.md` for the deployment environment — air-gapped deployments restrict external dependencies
