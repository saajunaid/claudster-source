---
name: warm-editorial-ui
description: Apply the "Warm Editorial Refinement" design system — a sophisticated, magazine-inspired aesthetic with warm cream surfaces, Syne + DM Sans typography, generous rounded corners, multi-layer shadows, and a warm neutral palette. Use this skill whenever the user wants to build an app, dashboard, component, or web UI using the abc-project visual style. Trigger on phrases like "use our design system", "apply our template", "make it look like abc-project", "use the warm editorial style", "use our brand template", or any request to build a new tool/app/dashboard for XYZ Brand or similar contexts. This is the canonical design template for all new frontend builds.
---

# Warm Editorial Refinement — Design System

A premium, editorial-grade UI template built for data-rich internal tools. Combines the warmth of analogue design with the precision of modern SaaS.

**Canonical reference apps:** `abc-project-mockup.html`, `nps-lens-v3.html`

---

## Design Philosophy

> Warm surfaces. Editorial type. Intentional depth. Not corporate grey — warm cream.

This system was designed for **XYZ Brand internal tools** but is brand-agnostic at the token level. It avoids cold grey SaaS aesthetics and instead uses warm-toned surfaces, editorial typography, and refined component geometry.

---

## Design Tokens

Always define these CSS custom properties in `:root`:

```css
:root {
  /* Brand Accent — replace with your brand color */
  --brand:          #E10A0A;
  --brand-dark:     #C00909;
  --brand-soft:     #FEF2F2;
  --brand-tint:     rgba(225,10,10,0.08);

  /* Warm Surfaces — NOT cold grey */
  --bg:             #F5F3F0;   /* page background */
  --surface:        #FFFFFF;   /* cards, panels */
  --surface-2:      #F8F7F5;   /* subtle inset, inputs */
  --surface-3:      #F2F0ED;   /* deeper inset, table rows */
  --surface-hover:  #EFEDE9;   /* hover states */

  /* Warm Borders */
  --border:         #E5E2DC;
  --border-strong:  #D1CEC8;

  /* Warm Ink (text) — slightly brown-tinged, never cold */
  --ink-1:          #1A1816;   /* primary text */
  --ink-2:          #3D3A36;   /* secondary text */
  --ink-3:          #6B6760;   /* tertiary text */
  --ink-4:          #9C9890;   /* muted/placeholder */

  /* Status Palette */
  --green:          #16A34A;
  --green-soft:     #F0FDF4;
  --green-tint:     rgba(22,163,74,0.12);
  --green-border:   #A7F3D0;

  --amber:          #D97706;
  --amber-soft:     #FFFBEB;

  --red:            #DC2626;
  --red-soft:       #FEF2F2;
  --red-border:     #FCA5A5;

  --blue:           #2563EB;
  --blue-soft:      #EFF6FF;
  --blue-border:    #BFDBFE;

  /* Radius Scale — generous, not tight */
  --r-xs:           4px;
  --r-sm:           8px;
  --r-md:           12px;
  --r-lg:           16px;    /* standard cards */
  --r-xl:           22px;    /* panels, large containers */

  /* Shadows — multi-layer, warm-tinted */
  --shadow-xs:      0 1px 2px rgba(0,0,0,0.04);
  --shadow-sm:      0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md:      0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
  --shadow-lg:      0 12px 32px rgba(0,0,0,0.10), 0 4px 8px rgba(0,0,0,0.05);

  /* Typography */
  --font-sans:      'DM Sans', sans-serif;
  --font-display:   'DM Serif Display', serif;
  --font-heading:   'Syne', sans-serif;
  --font-mono:      'JetBrains Mono', monospace;
}
```

### Google Fonts Import
```html
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Serif+Display:ital@0;1&family=Syne:wght@600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

---

## Typography Rules

| Role | Font | Weight | Usage |
|------|------|--------|-------|
| UI body | DM Sans | 400–600 | Labels, body text, navigation |
| Numbers/data | JetBrains Mono | 400–600 | KPI values, counts, codes |
| Section headings | Syne | 700–800 | Card titles, panel headers, brand name |
| Display / hero | DM Serif Display | 400 | Large display text, hero numbers (optional) |

**Never use:** Inter, Roboto, Space Grotesk, Arial as primary fonts.

---

## Layout Architecture

### App Shell with Left Sidebar
```
┌──────────────────────────────────────────────────────┐
│  Sidebar (236px)  │  Top Filter Bar (52px)            │
│                   ├──────────────────────────────────┤
│  Brand Logo       │  Sub-tab Bar (40px)               │
│  Nav Groups       ├──────────────────────────────────┤
│  Footer / User    │  Page Content (scrollable)        │
└──────────────────────────────────────────────────────┘
```

### Sidebar Pattern
```css
.sidebar {
  width: 236px;
  background: var(--surface);
  border-right: 1px solid var(--border);
}

/* Brand lockup */
.brand-logo {
  width: 36px; height: 36px;
  background: var(--brand);
  border-radius: 10px;
  box-shadow: 0 3px 10px rgba(225,10,10,0.3);
  font-family: var(--font-heading);
  font-size: 14px; font-weight: 800;
}

/* Active nav item */
.nav-item.active {
  background: var(--brand-soft);
  color: var(--brand);
  font-weight: 600;
}
.nav-item.active::before {
  content: '';
  position: absolute; left: 0;
  top: 5px; bottom: 5px; width: 3px;
  background: var(--brand);
  border-radius: 0 3px 3px 0;
}
```

---

## Component Patterns

### KPI Cards
```css
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);      /* 16px */
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.15s, transform 0.15s;
}
.kpi-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.kpi-card::before {
  /* colored top bar */
  content: ''; position: absolute; top: 0; left: 0; right: 0;
  height: 3px; border-radius: var(--r-lg) var(--r-lg) 0 0;
  background: var(--kpi-color, var(--border));
}
/* KPI value uses Syne for that editorial punch */
.kpi-value {
  font-family: var(--font-heading);
  font-size: 30px; font-weight: 700; letter-spacing: -1px;
}
```

### Filter Pills (Topbar)
```css
.fchip {
  border: 1.5px solid var(--border);
  border-radius: 20px;
  padding: 4px 11px;
  font-size: 12px; font-weight: 500;
  background: var(--surface);
  transition: all 0.12s;
}
.fchip:hover  { border-color: var(--brand); color: var(--brand); background: var(--brand-soft); }
.fchip.active { border-color: var(--brand); color: var(--brand); background: var(--brand-soft); }
```

### Buttons
```css
/* Primary */
.btn-primary {
  height: 32px; padding: 0 16px;
  background: var(--brand); color: white; border: none;
  border-radius: var(--r-sm);
  font-family: var(--font-heading); font-size: 12.5px; font-weight: 700;
  box-shadow: 0 2px 8px rgba(225,10,10,0.2);
  transition: all 0.12s;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(225,10,10,0.3); }

/* Ghost */
.btn-ghost {
  height: 32px; padding: 0 12px;
  border: 1.5px solid var(--border); border-radius: var(--r-sm);
  background: var(--surface); color: var(--ink-3);
  font-family: var(--font-sans); font-weight: 500;
}
.btn-ghost:hover { background: var(--surface-2); color: var(--ink-1); }
```

### Status Badges / Pills
```css
.badge { padding: 2px 7px; border-radius: 20px; font-size: 10px; font-weight: 700; }
.badge.success { background: var(--green-soft); color: var(--green); border: 1px solid var(--green-tint); }
.badge.warning { background: var(--amber-soft); color: var(--amber); }
.badge.danger  { background: var(--red-soft);   color: var(--red);   border: 1px solid var(--red-border); }
```

### Chart Cards
```css
.chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);     /* 16px */
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
}
/* Card title uses Syne */
.chart-title { font-family: var(--font-heading); font-size: 13.5px; font-weight: 700; letter-spacing: -0.2px; }
.chart-sub   { font-size: 11px; color: var(--ink-4); }
```

### Section Labels
```css
.section-title {
  font-size: 10px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--ink-4);
  font-family: var(--font-sans);
}
```

---

## Alert / Highlight Cards
```css
/* Warning alert */
.alert-card {
  background: linear-gradient(135deg, #FFF8F5 0%, #FFF2EE 100%);
  border: 1.5px solid #FCCAB4;
  border-radius: var(--r-lg);
}
/* Success callout */
.callout-green {
  background: var(--green-soft);
  border: 1px solid var(--green-border);
  border-radius: var(--r-md);
  padding: 10px 13px;
}
/* Info callout */
.callout-blue {
  background: var(--blue-soft);
  border: 1px solid var(--blue-border);
  border-radius: var(--r-md);
  padding: 10px 13px;
}
```

---

## React Component Structure

When building React components with this design system:

```tsx
// Design tokens map directly to Tailwind-like CSS vars
// Use inline styles or a theme provider pattern:

const theme = {
  surface: 'var(--surface)',
  surface2: 'var(--surface-2)',
  border: 'var(--border)',
  ink1: 'var(--ink-1)',
  ink4: 'var(--ink-4)',
  brand: 'var(--brand)',
  brandSoft: 'var(--brand-soft)',
  fontHeading: 'var(--font-heading)',
  fontMono: 'var(--font-mono)',
  // Radius
  rLg: 'var(--r-lg)',
  rXl: 'var(--r-xl)',
  // Shadows
  shadowSm: 'var(--shadow-sm)',
  shadowMd: 'var(--shadow-md)',
};

// KPI Card example
function KpiCard({ label, value, delta, color, trend }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--r-lg)',
      padding: '14px 16px',
      boxShadow: 'var(--shadow-sm)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Colored top bar */}
      <div style={{ position:'absolute', top:0, left:0, right:0, height:'3px', background:color }} />
      <p style={{ fontSize:'10px', fontWeight:700, letterSpacing:'1.2px', textTransform:'uppercase', color:'var(--ink-4)', marginBottom:'8px' }}>
        {label}
      </p>
      <p style={{ fontFamily:'var(--font-heading)', fontSize:'30px', fontWeight:700, letterSpacing:'-1px', color }}>
        {value}
      </p>
    </div>
  );
}
```

---

## Grid Layouts

```css
/* KPI row — 6 columns */
.kpi-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }

/* 2-column charts */
.charts-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* 3-column charts */
.charts-3col { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
```

---

## Sidebar Nav Badge Colors

```css
.nav-badge.red   { background: var(--red-soft);   color: var(--red);   border: 1px solid var(--red-border); }
.nav-badge.green { background: var(--green-soft);  color: var(--green); }
.nav-badge.grey  { background: var(--surface-3);   color: var(--ink-4); }
```

---

## What Makes This Style Distinctive

1. **Warm vs cold**: Surfaces are `#F8F7F5` and `#F2F0ED` — cream/linen, not cold `#F9FAFB`
2. **Ink tones**: Text is `#1A1816` (warm black) not `#111827` (cold)
3. **Borders**: `#E5E2DC` (warm beige) not `#E5E7EB` (cool grey)
4. **Typography**: Syne headings give editorial weight; DM Sans body is humanist not geometric
5. **Radius**: 16px cards, 22px panels — generous, contemporary
6. **Shadows**: Always multi-layer (`0 1px 3px ... 0 1px 2px ...`) for depth

---

## Don'ts

- ❌ No `Inter`, `Roboto`, or `Space Grotesk`
- ❌ No cold grey surfaces (`#F9FAFB`, `#F3F4F6`)
- ❌ No generic SaaS blue (`#3B82F6`) as primary
- ❌ No glass morphism effects
- ❌ No tight corners (avoid radius < 8px on cards)
- ❌ No single-layer flat shadows
- ❌ No uppercase text in `var(--font-heading)` for body copy

---

## Adapting for Different Brands

Change only the brand token and optionally the accent palette:

```css
/* e.g. for a teal-branded product */
:root {
  --brand:       #0891B2;
  --brand-dark:  #0E7490;
  --brand-soft:  #ECFEFF;
  --brand-tint:  rgba(8,145,178,0.08);
}
/* All other tokens remain the same */
```

The warm surface, ink, and border tokens are **brand-neutral** — they work for any brand colour.
