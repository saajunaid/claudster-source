---
description: "Mobile-native + PWA implementation playbook for React/Vite dashboards"
applyTo: "**/*.html, **/*.css, **/*.scss, **/*.ts, **/*.tsx, **/*.js, **/*.jsx"
---

# Mobile-Native + PWA Playbook

Use this when converting an existing desktop-first web app into a mobile-native, installable PWA while preserving desktop behavior.

## Core Principle

Do not "shrink desktop". Build explicit mobile interaction paths (navigation, list density, detail flows, touch affordances), while keeping route contracts and desktop workflows stable.

## 1. Navigation Architecture: Preserve Routes, Adapt Surfaces

- Keep route paths and route IDs stable.
- Build a reduced mobile-primary navigation surface (bottom nav, quick tabs, or compact menu) for highest-frequency workflows.
- Keep advanced routes routable via deep links or secondary menus.
- Derive active state from route families, not string equality only.

Example mapping pattern:

```ts
function resolveActiveRoute(pathname: string): AppNavRoute {
  if (pathname.startsWith("/cases")) return "/queue";
  if (pathname.startsWith("/settings")) return "/settings";
  return "/";
}
```

Rule: Information architecture is a data contract. Mobile UX should re-surface it, not rewrite it.

## 2. Dense Data Views: Branch Mobile and Desktop Rendering

For operational tables and multi-column grids:

- Render a dedicated mobile card/list view on compact breakpoints.
- Render desktop table/grid separately for larger breakpoints.
- Keep data model and selection state shared between both branches.
- On mobile, prioritize tap-to-open detail flow over inline multi-action rows.

Rule: One compressed table for all breakpoints creates unreadable and error-prone mobile interactions.

## 3. Detail Interactions: Use Bottom Sheets for Mobile Drill-Down

When row selection opens details on mobile:

- Use bottom sheet/dialog patterns for context retention.
- Ensure sheet content has explicit accessible title and description.

```tsx
<SheetContent side="bottom">
  <SheetHeader className="sr-only">
    <SheetTitle>Item details</SheetTitle>
    <SheetDescription>Review details and take an action.</SheetDescription>
  </SheetHeader>
  <DetailsPanel />
</SheetContent>
```

Rule: Visual correctness is not enough. Dialog semantics must be explicit for screen readers and a11y tooling.

## 4. Touch UX Baseline

Add touch-first primitives:

- Horizontal rails use `overflow-x-auto` + momentum scrolling.
- Increase mobile hit targets (roughly >= 44px height).
- Disable tap highlight artifacts where appropriate.
- Add subtle active-state feedback for tap interactions.

Example:

```css
.touch-scroll {
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
}

html {
  -webkit-tap-highlight-color: transparent;
}
```

Rule: If an interaction depends on hover precision, it is not mobile-native yet.

## 5. PWA Shell Must Ship as a Bundle

Deliver PWA prerequisites together:

- `index.html`: `manifest`, favicon/app icon links, `theme-color`, mobile-web-app meta tags.
- `public/manifest.json`: app name, short name, display mode, theme/background colors, icons.
- Icon pipeline: include at least 192x192 and 512x512 plus apple-touch icon.
- Layout safe area: account for `env(safe-area-inset-bottom)` when fixed bottom UI exists.

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<link rel="manifest" href="/manifest.json" />
```

Rule: Partial PWA setup causes inconsistent install behavior and visual clipping on notched devices.

## 6. Subpath Deployment Safety (Vite)

If app deploys under a subpath:

- Keep router `basepath` tied to `import.meta.env.BASE_URL`.
- Avoid root-absolute runtime asset fetches (`fetch("/file.json")`).
- Ensure manifest/start URL aligns with deployed base path.

Rule: Subpath correctness requires all URL categories (router, API, static fetches, manifest entry) to align.

## 7. Verification Gate for Mobile-Native + PWA Work

Do not mark complete until all pass:

1. Build succeeds for target mode/environment.
2. Editor diagnostics are clean in modified files.
3. Mobile viewport interaction pass is executed in browser:
   - primary navigation
   - search/filter inputs
   - list selection to detail sheet flow
   - open/close behavior for compact menus/sheets
4. PWA smoke checks:
   - manifest discoverable
   - correct icon shown
   - standalone launch behavior works as expected

Rule: Compile-time success alone does not prove runtime mobile correctness.

## 8. Rollout Strategy

For existing products, sequence work in this order:

1. Shell and navigation adaptation
2. Dense list/table mobile branch
3. Detail interaction model (sheet/dialog)
4. Touch and safe-area polish
5. PWA metadata and icon packaging
6. End-to-end mobile verification

Rule: Ship vertical slices that are user-testable; avoid broad unverified styling-only sweeps.
