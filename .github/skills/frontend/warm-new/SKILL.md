---
name: warm-new
description: Apply the "Warm New" design system for React/web UIs using the RevSight design tokens and implementation guide. Use this skill whenever the user requests a UI, dashboard, or component with the RevSight look, or references the attached design tokens/implementation guide. Always ensure dropdown/select panels have a smooth, modern appearance (not blocky), and follow all theme, typography, and component rules from the attached guides.
---


# Warm New — RevSight Design System Skill


A premium, executive-grade UI skill for React/web apps, based on the RevSight design tokens and implementation guide. This skill ensures:
- All UI follows the attached DESIGN_TOKENS.md and IMPLEMENTATION_GUIDE.md
- Both light and dark themes are supported
- Typography, color, spacing, and component rules are strictly enforced
- Dropdown/select panels have a smooth, modern appearance (never blocky)
- **All color appearance preferences (theme, accent, etc.) must be contained within the Settings tab in the UI.**
- **The switch for dark or light mode must always be displayed as an icon (e.g., sun/moon), never as full text.**
## Appearance Settings & Theme Switch Requirements

- All color appearance preferences (theme, accent color, etc.) must be accessible only from the Settings tab in the UI. Do not place color/theme controls in other locations.
- The dark/light mode toggle must always be an icon (such as a sun/moon, or similar), not a text label. Place this icon in the Settings tab, not in the main navigation or top bar.
- When implementing the theme switch, use a visually clear icon button. Example:

```jsx
// Example: Theme switch icon in Settings tab
<button className="theme-toggle-icon" aria-label="Switch theme">
  {/* Render sun or moon icon based on current theme */}
  {theme === 'dark' ? <MoonIcon /> : <SunIcon />}
</button>
```

- Do not use text like "Switch to dark mode" or "Light mode" as the toggle. Use only the icon, with an accessible label for screen readers.
- See the Implementation Guide for more on settings layout and accessibility.

---

## Canonical References
- **Design Tokens:** See [DESIGN_TOKENS.md](DESIGN_TOKENS.md)
- **Implementation Guide:** See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)

---

## Core Principles
- Use only the documented tokens for color, radius, spacing, and elevation
- Never hard-code colors or fonts outside the token system
- Always support both light and dark mode (see Implementation Guide)
- Typography: DM Sans (UI), IBM Plex Sans (tables), JetBrains Mono (code/IDs)
- Accent: Signal Red by default; alternate accents as documented

---

## Dropdown/Select Panel Styling

**Goal:** Dropdowns (select panels) must have a smooth, modern, premium appearance. Avoid the blocky, harsh look (see screenshot for what NOT to do).

**Implementation Guidance:**
- Use the shared premium control tokens for dropdowns/selects:
  - `--control-bg`, `--control-bg-hover`, `--control-bg-active`
  - `--control-border`, `--control-border-strong`, `--control-ring`
  - `--shadow-control`, `--shadow-control-strong`
  - `--radius-control`
- Apply these tokens to the dropdown trigger and the panel itself
- Use subtle box-shadow for the dropdown panel (`--shadow-control-strong`)
- Use `--radius-control` for rounded corners (avoid sharp/boxy edges)
- Ensure the dropdown panel background uses `--control-bg` (light) or `--control-bg` (dark)
- On hover/focus, border and shadow should intensify slightly (see token guide)
- Remove default browser outline; use `--control-ring` for focus
- For React: use a custom select component or style a native `<select>` with CSS-in-JS or CSS modules, mapping all visual states to the tokens
- Example (CSS):

```css
.select-panel {
  background: var(--control-bg);
  border: 1.5px solid var(--control-border);
  border-radius: var(--radius-control);
  box-shadow: var(--shadow-control-strong);
  padding: 6px 0;
  min-width: 180px;
  transition: box-shadow 0.18s, border-color 0.18s;
}
.select-panel:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--control-ring), var(--shadow-control-strong);
  border-color: var(--control-border-strong);
}
.select-panel__option {
  padding: 8px 18px;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.14s;
}
.select-panel__option:hover,
.select-panel__option:focus {
  background: var(--control-bg-hover);
}
```

- For shadcn/ui, Chakra, or MUI: override the select/menu styles to use these tokens
- Never use default browser select panel appearance
- Test in both light and dark mode

---

## Design Tokens

See [DESIGN_TOKENS.md](DESIGN_TOKENS.md) for the full token list. All colors, fonts, radii, spacing, and shadows must use these tokens.

---

## Implementation Guide

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for layout, theming, and component rules. Always follow the shell, layout, and component structure described there.

---


## Example Usage


```jsx
// Example: Smooth select panel using tokens
<div className="select-panel">
  <div className="select-panel__option">UID</div>
  <div className="select-panel__option">Remote ID</div>
  <div className="select-panel__option">MAC address</div>
  <div className="select-panel__option">Serial number</div>
</div>

// Example: Theme switch icon in Settings tab
<button className="theme-toggle-icon" aria-label="Switch theme">
  {theme === 'dark' ? <MoonIcon /> : <SunIcon />}
</button>
```

---

## Test Prompts
- "Build a dashboard using the warm-new design system."
- "Add a dropdown for lookup type that matches the smooth style, not blocky."
- "How do I apply the RevSight tokens for dark mode?"

---

## See Also
- [DESIGN_TOKENS.md](DESIGN_TOKENS.md)
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)

---

This skill is the canonical reference for all new UI work using the RevSight design system. Always check the attached guides for updates before implementing new components.
