---
description: 'Frontend development standards for HTML, CSS, and styling'
applyTo: '**/*.html, **/*.css, **/*.scss, **/*.py, **/*.ts, **/*.tsx, **/*.js, **/*.jsx'
---

# Frontend Development Instructions

Guidelines for building consistent, accessible, and visually appealing user interfaces.

## SPA Chunk Resilience (React/Vite)

When using route-level code splitting (`import()` / `React.lazy`), implement one-time stale-chunk recovery:

1. Wrap lazy imports with retry logic for transient failures.
2. On exhausted retries, detect chunk-load errors (`Failed to fetch dynamically imported module`, `ChunkLoadError`).
3. Trigger exactly one automatic reload per chunk key via `sessionStorage`.
4. If reload still fails, show a user-facing fallback with retry button.

```typescript
const CHUNK_RELOAD_KEY_PREFIX = "app:chunk-reload:";

function tryOneTimeChunkReload(error: unknown): boolean {
    const message = error instanceof Error ? error.message : String(error ?? "");
    const isChunkError = /Failed to fetch dynamically imported module|ChunkLoadError|Loading chunk/i.test(message);
    if (!isChunkError) return false;

    const chunkLike = message.match(/[A-Za-z0-9_-]+\.[cm]?js/i)?.[0] ?? "unknown";
    const key = `${CHUNK_RELOAD_KEY_PREFIX}${chunkLike}`;
    if (sessionStorage.getItem(key) === "1") return false;

    sessionStorage.setItem(key, "1");
    window.location.reload();
    return true;
}
```

This pattern prevents users from getting stuck on stale chunk hashes after deployments while avoiding infinite reload loops.

## Proactive Version Detection (Long-Lived Sessions)

Reactive chunk recovery (above) handles errors after they happen. For long-lived sessions — dashboards left open for days by executives — add **proactive** version detection so the browser reloads **before** stale chunks are requested.

### Why Not Service Workers?

Service workers are the FAANG standard (Gmail, Twitter/X, YouTube). However, they require HTTPS. Intranet apps served over plain HTTP (common with IIS on internal hostnames) cannot register a service worker. If your prod server has HTTPS, prefer `vite-plugin-pwa` (Workbox). Otherwise, use the 3-layer polling approach below.

### 3-Layer Architecture

Three layers provide **zero-gap** coverage — no scenario lets the CEO hit a stale chunk:

| Layer | Trigger | What it catches |
|-------|---------|----------------|
| **Router `beforeLoad`** | Every route/tab navigation | User clicks a tab → version check fires BEFORE the stale chunk is requested |
| **Periodic polling** (60 s) | Interval timer | Tab sitting idle on one page for hours |
| **`visibilitychange`** | Tab regains focus | User returns from another browser tab/window |

All three layers share a single **module-level** version-check module (non-React) so state is consistent.

### Build-Time: Vite Plugin

Emits `version.json` into `dist/` and injects the same ID as `import.meta.env.VITE_BUILD_VERSION`:

```typescript
// src/lib/vite-version-plugin.ts
import type { Plugin } from "vite";

export function versionJsonPlugin(): Plugin {
  const buildVersion =
    Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

  return {
    name: "version-json",
    apply: "build",
    config() {
      return {
        define: {
          "import.meta.env.VITE_BUILD_VERSION": JSON.stringify(buildVersion),
        },
      };
    },
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "version.json",
        source: JSON.stringify({ version: buildVersion }) + "\n",
      });
    },
  };
}
```

### Runtime: Shared Version-Check Module

A non-React module that all three layers call into. Caches the last fetch for 30 seconds so rapid tab switching doesn't hammer the server:

```typescript
// src/lib/version-check.ts
const STALE_MS = 30_000;
const STORAGE_KEY = "app:last-reloaded-version";

let _deployed: string | null = null;
let _lastFetchMs = 0;

export async function fetchDeployedVersion(): Promise<string | null> {
  const url = `${import.meta.env.BASE_URL}version.json?_t=${Date.now()}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) return null;
  const json = await res.json();
  _deployed = json.version ?? null;
  _lastFetchMs = Date.now();
  return _deployed;
}

export async function ensureFreshVersion(): Promise<void> {
  if (!import.meta.env.VITE_BUILD_VERSION) return;
  if (Date.now() - _lastFetchMs > STALE_MS) await fetchDeployedVersion();
}

export function hasNewerVersion(): boolean {
  if (!import.meta.env.VITE_BUILD_VERSION || !_deployed) return false;
  return _deployed !== import.meta.env.VITE_BUILD_VERSION;
}

export function triggerReload(): boolean {
  if (!_deployed) return false;
  if (sessionStorage.getItem(STORAGE_KEY) === _deployed) return false;
  sessionStorage.setItem(STORAGE_KEY, _deployed);
  window.location.reload();
  return true;
}

export async function checkAndReloadIfStale(): Promise<boolean> {
  await ensureFreshVersion();
  return hasNewerVersion() ? triggerReload() : false;
}
```

### Layer 1: Router `beforeLoad` (zero-gap navigation check)

Add to the root route so every navigation checks version before loading chunks:

```typescript
// routes/__root.tsx
import { checkAndReloadIfStale } from "@/lib/version-check";

export const Route = createRootRoute({
  beforeLoad: async () => {
    await checkAndReloadIfStale();
  },
  component: RootComponent,
});
```

### Layer 2 + 3: Polling Hook + VisibilityChange

```typescript
// hooks/useVersionCheck.ts — delegates to version-check.ts
// Polls every 60s + listens to visibilitychange.
// On mismatch:
//   - document.hidden → triggerReload() immediately (silent)
//   - visible → call onUpdateDetected callback (toast), then reload after 3s
```

Mount at app root via `<VersionGuard />` — a minimal toast component.

### Key Requirements

- Plugin must use `apply: "build"` — no version file or polling in dev.
- Fetch must bypass HTTP cache: `{ cache: "no-store" }` plus `_t=` query-string buster.
- `version.json` must be served without caching (sits in dist root, not `/assets/`).
- `sessionStorage` prevents infinite reloads — check before reloading, set before triggering.
- Router `beforeLoad` on root route is the **critical** layer — it catches navigation to stale chunks before they 404.
- Shared module caches fetch results for 30 s — `beforeLoad` on rapid tab switches uses cached state, not fresh fetches.
- Foreground toast must be non-intrusive and auto-dismiss (reload happens within seconds).
- **HTTPS required for Service Workers** — if HTTP-only, this 3-layer approach is the best alternative.

## Branding & Color System

### Brand Colors
```css
:root {
    /* Primary Palette — resolve from project-config.md */
    --brand-primary: <BRAND_PRIMARY>;
    --brand-secondary: <BRAND_SECONDARY>;
    --brand-white: #FFFFFF;
    --brand-black: #000000;
    --brand-gray: #7D7D7D;

    /* Secondary Palette */
    --brand-light-gray: #D9D9D9;
    --brand-dark-gray: #4A4A4A;

    /* Semantic aliases */
    --brand-primary-hover: <BRAND_DARK>;     /* from project-config.md */
    --brand-text: var(--brand-dark-gray);
    --brand-surface: var(--brand-white);
    --brand-border: var(--brand-light-gray);
    --brand-muted: var(--brand-gray);

    /* Status Colors (universal) */
    --status-success: #10B981;
    --status-warning: #F59E0B;
    --status-info: #3B82F6;
    --status-error: #DC2626;

    /* Neutral Palette */
    --gray-50: #F9FAFB;
    --gray-200: #E5E7EB;
    --gray-300: #D1D5DB;
    --gray-400: #9CA3AF;
    --gray-600: #4B5563;
    --gray-700: #374151;
    --gray-800: #4A4A4A;
    --gray-900: #111827;
}
```

---

## Fixed Header Navigation

For Streamlit apps that use fixed header navigation:

### Header CSS Pattern
```css
/* Fixed header - stays at top while content scrolls */
.app-fixed-header {
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: white;
    border-bottom: 1px solid var(--brand-border);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
    z-index: 999999;  /* High z-index to overlay Streamlit elements */
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2rem;
}

/* Push main content below fixed header */
.main .block-container {
    padding-top: calc(60px + 2rem) !important;
    max-width: 1600px;
}

/* Navigation link styling */
.app-nav-link {
    color: var(--brand-muted);
    text-decoration: none;
    padding: 0.5rem 0.875rem;
    border-radius: 6px;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.15s ease;
}

.app-nav-link:hover {
    background: var(--brand-light-gray);
    color: var(--brand-secondary);
}

.app-nav-link.active {
    background: var(--brand-primary);
    color: var(--brand-primary);
}
```

### Header HTML Structure
```html
<div class="app-fixed-header">
    <!-- Left: Logo + Branding -->
    <div style="display: flex; align-items: center; gap: 8px;">
        <img src="data:image/svg+xml;base64,..." alt="Logo" style="height: 28px;">
        <span style="color: var(--brand-primary); font-weight: 700; font-size: 1.5rem;"><ORG_NAME></span>
        <span style="color: #7D7D7D; font-size: 1rem;">App Title</span>
    </div>
    
    <!-- Right: Navigation -->
    <nav style="display: flex; gap: 0.25rem;">
        <a href="/" class="app-nav-link active">Home</a>
        <a href="/Search" class="app-nav-link">Search</a>
        <a href="/Analytics" class="app-nav-link">Analytics</a>
    </nav>
</div>
```

### Hide Streamlit Sidebar
```css
/* IMPORTANT: Hide ALL sidebar elements including the arrow during load */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"],
div[data-testid="collapsedControl"],
section[data-testid="stSidebar"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
}

header[data-testid="stHeader"] { display: none !important; }
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }
.stDeployButton { display: none !important; }
```

### SVG Logo Embedding (Base64)
SVG logos in `st.markdown()` get escaped as HTML text. Use base64 encoding:

```python
import base64
from pathlib import Path

def get_logo_base64() -> str:
    logo_path = Path(__file__).parent.parent / "assets" / "logo.svg"  # adjust per project
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_data = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/svg+xml;base64,{logo_data}" alt="Logo" style="height: 28px;">'
    return ""
```

---

### 60-30-10 Color Rule
- **60% Primary**: Light surfaces (#FFFFFF, #D9D9D9)
- **30% Secondary**: Text and structure (#4A4A4A, #7D7D7D)
- **10% Accent**: Brand accents (from project-config.md `<BRAND_PRIMARY>`, `<BRAND_SECONDARY>`)

### Color Usage Guidelines

**Background Colors - Use:**
- White or light neutral surfaces (#FFFFFF, #D9D9D9)
- Light cool colors for sections
- Subtle gradients with minimal color shift

**Background Colors - Avoid:**
- Hot colors (red, orange, yellow) for large areas
- Purple, magenta, or pink backgrounds
- High-saturation colors

**Text Colors:**
- Dark neutrals for body text (#4A4A4A, #7D7D7D)
- Near-black for maximum contrast (#111827)
- White text only on dark/red backgrounds
- Never use yellow or light colors for text

## Typography

### Font Stack
```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
                 Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 16px;
    line-height: 1.5;
    color: #4A4A4A;
}

h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    color: #111827;
    margin-bottom: 0.5em;
}
```

### Type Scale
| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| h1 | 2.25rem (36px) | 600 | 1.2 |
| h2 | 1.875rem (30px) | 600 | 1.25 |
| h3 | 1.5rem (24px) | 600 | 1.3 |
| h4 | 1.25rem (20px) | 600 | 1.4 |
| body | 1rem (16px) | 400 | 1.5 |
| small | 0.875rem (14px) | 400 | 1.5 |

## Spacing System

Use consistent spacing based on 4px grid:
```css
:root {
    --space-1: 0.25rem;   /* 4px */
    --space-2: 0.5rem;    /* 8px */
    --space-3: 0.75rem;   /* 12px */
    --space-4: 1rem;      /* 16px */
    --space-5: 1.25rem;   /* 20px */
    --space-6: 1.5rem;    /* 24px */
    --space-8: 2rem;      /* 32px */
    --space-10: 2.5rem;   /* 40px */
    --space-12: 3rem;     /* 48px */
    --space-16: 4rem;     /* 64px */
}
```

## Component Styles

### Buttons
```css
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.15s ease;
}

.btn-primary {
    background-color: #E30613;
    color: white;
    border: none;
}

.btn-primary:hover {
    background-color: #B71C1C;
}

.btn-secondary {
    background-color: #FFFFFF;
    color: #4A4A4A;
    border: 1px solid #D9D9D9;
}

.btn-secondary:hover {
    background-color: #F3F4F6;
}
```

### Cards
```css
.card {
    background-color: #FFFFFF;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    padding: 1.5rem;
}

.card-header {
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #E5E7EB;
}
```

### Form Elements
```css
.form-input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    font-size: 0.875rem;
    border: 1px solid #D1D5DB;
    border-radius: 0.375rem;
    background-color: #FFFFFF;
    color: #4A4A4A;
}

.form-input:focus {
    outline: none;
    border-color: #5A2D82;
    box-shadow: 0 0 0 3px rgba(90, 45, 130, 0.15);
}

.form-label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: #4A4A4A;
    margin-bottom: 0.25rem;
}
```

## Accessibility Requirements

### Color Contrast
- **WCAG AA Minimum**: 4.5:1 for normal text, 3:1 for large text
- **Verified Combinations**:
    - #4A4A4A on #FFFFFF ✓
    - #FFFFFF on #E30613 ✓
    - #111827 on #D9D9D9 ✓

### Focus States
```css
:focus {
    outline: 2px solid #3B82F6;
    outline-offset: 2px;
}

/* Never remove focus indicators */
:focus:not(:focus-visible) {
    outline: 2px solid #3B82F6;
}
```

### Skip Links
```html
<a href="#main" class="skip-link">Skip to main content</a>
```

```css
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
    background: #E30613;
    color: white;
    z-index: 9999;
}
```

## Responsive Design

### Breakpoints
```css
/* Mobile first approach */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
```

### Responsive Patterns
- Use flexible layouts (flexbox, grid)
- Avoid fixed widths
- Test at all breakpoints
- Ensure touch-friendly sizes (min 44px tap targets)

## Streamlit Custom CSS

```python
st.markdown("""
<style>
/* Project Theme for Streamlit */
.stApp {
    background-color: #D9D9D9;
}

.stButton > button {
    background-color: #E30613;
    color: white;
    border: none;
    border-radius: 0.375rem;
    font-weight: 500;
}

.stButton > button:hover {
    background-color: #B71C1C;
}

.stMetric {
    background-color: white;
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stDataFrame {
    border-radius: 0.5rem;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)
```

## Best Practices

1. **Consistency**: Use design tokens consistently
2. **Hierarchy**: Establish clear visual hierarchy
3. **Whitespace**: Use generous spacing
4. **Feedback**: Provide visual feedback for interactions
5. **Loading States**: Show progress indicators
6. **Error States**: Clear, actionable error messages
7. **Responsive**: Test at all viewport sizes
8. **Accessible**: Meet WCAG AA standards

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values. The profile defines `<ORG_NAME>`, `<BRAND_PRIMARY>`, `<BRAND_DARK>`, `<BRAND_LIGHT>`, and other brand tokens.
