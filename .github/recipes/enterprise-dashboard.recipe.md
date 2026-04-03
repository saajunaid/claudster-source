---
name: enterprise-dashboard
description: Cross-project delivery recipe for data-to-UI enterprise dashboard products
target_profile: react-fastapi-vite-mssql
applies_to: Executive dashboards, analytics portals, KPI monitoring tools, data exploration UIs
---

# Enterprise Dashboard Recipe

> **What this file is:** A composition manifest — it references existing skills and defines the mandatory delivery workflow for enterprise dashboard products. It does NOT duplicate skill content.
>
> **When agents use it:** When `project-config.md` sets `recipe: enterprise-dashboard` AND the task involves data-to-UI delivery (new feature, new data source, new dashboard). Not used for bug fixes, refactors, or docs-only work.

---

## Delivery Pipeline

Every feature in an enterprise-dashboard product follows this mandatory sequence.
Phases MUST NOT be skipped or reordered. Sub-phases may be added within a phase.

```
1. DATA-INTAKE     → Gather source files, identify format, assess schema
2. ADAPTER         → Build source adapter (data-contract-pipeline Layer 1)
3. NORMALIZE       → Build ingestion model + normalizer (Layers 2-3)
4. DISPLAY-DTO     → Build display DTO + mapping reference doc (Layer 4)
5. CONTRACT-TEST   → Generate golden samples + contract tests (Layers 7-8)
6. API-SURFACE     → Build FastAPI router + frontend types + service (Layers 5-6)
7. UI-DESIGN       → Annotated HTML mockup with full DTO lineage
8. IMPLEMENT       → React components from annotated mockup
9. VERIFY          → Visual match, contract pass, accessibility pass
```

---

## Mandatory Skill Composition

| Phase | Skills (MUST load) | Instructions (auto-applied) |
|-------|--------------------|-----------------------------|
| DATA-INTAKE | `.github/skills/workflow/data-contract-pipeline/SKILL.md` | `python.instructions.md` |
| ADAPTER | `.github/skills/workflow/data-contract-pipeline/SKILL.md` | `python.instructions.md` |
| NORMALIZE | `.github/skills/workflow/data-contract-pipeline/SKILL.md` | `python.instructions.md` |
| DISPLAY-DTO | `.github/skills/workflow/data-contract-pipeline/SKILL.md` | `python.instructions.md` |
| CONTRACT-TEST | `.github/skills/workflow/data-contract-pipeline/SKILL.md` | `python.instructions.md`, `testing.instructions.md` |
| API-SURFACE | `.github/skills/workflow/data-contract-pipeline/SKILL.md`, `.github/skills/coding/fastapi-dev/SKILL.md`, `.github/skills/coding/backend-to-frontend-handoff/SKILL.md` | `python.instructions.md`, `fastapi.instructions.md` |
| UI-DESIGN | `.github/skills/frontend/mockup/SKILL.md`, `.github/skills/frontend/warm-editorial-ui/SKILL.md`, `.github/skills/frontend/high-end-visual-design/SKILL.md` | `frontend.instructions.md`, `accessibility.instructions.md` |
| IMPLEMENT | `.github/skills/frontend/react-best-practices/SKILL.md`, `.github/skills/frontend/shadcn-radix/SKILL.md`, `.github/skills/frontend/css-architecture/SKILL.md`, `.github/skills/frontend/premium-react/SKILL.md` | `frontend.instructions.md`, `accessibility.instructions.md` |
| VERIFY | `.github/skills/workflow/verification-loop/SKILL.md` | `testing.instructions.md`, `code-review.instructions.md` |

---

## Cross-Skill Conventions

These rules bridge the gaps between individual skills. They are the "glue" that no single skill owns.

### DTO Field Lineage — Naming Chain

One unbroken chain from source to screen. If any two adjacent layers disagree on a field name, the contract test must catch it.

| Layer | Naming Convention | Example |
|-------|-------------------|---------|
| Source file header | Exact match to source (any casing) | `Net Promoter Score` |
| Adapter output key | snake_case matching source semantics | `net_promoter_score` |
| Ingestion model field | snake_case Python attribute | `net_promoter_score` |
| Display DTO field | snake_case Python attribute with camelCase alias | `net_promoter_score` (alias `netPromoterScore`) |
| TypeScript interface field | camelCase matching DTO alias | `netPromoterScore` |
| Mockup DATA-SOURCE annotation | camelCase matching TypeScript field | `<!-- DATA-SOURCE: npsData.broadband.netPromoterScore -->` |
| React component prop | camelCase matching TypeScript field | `data.netPromoterScore` |

### Component Directory Structure

All enterprise-dashboard products use this layout under `frontend/src/components/`:

```
components/
  ui/          → shadcn/ui primitives (never modified directly)
  cards/       → KPI cards, metric cards, summary cards
  charts/      → Recharts wrappers, chart containers
  tables/      → Data tables, detail views
  layout/      → App shell, sidebar, header, tab containers
  filters/     → Period pickers, product selectors, filter bars
```

### Service Layer Structure

```
frontend/src/
  services/
    {domain}.ts         → One service per API domain, typed return values
  hooks/
    use{Domain}Data.ts  → One query hook per service, wraps TanStack Query
  stores/
    {domain}-store.ts   → Client-only state (filters, UI preferences)
  types/
    {domain}.ts         → TypeScript interfaces mirroring display DTO aliases
```

### Backend Layer Conventions

```
src/
  api/routers/          → HTTP endpoints only — no business logic
  services/             → Business logic, normalizers, adapters
  repositories/         → Database queries only — no business logic
  models/
    ingestion/          → 1:1 Pydantic models matching raw payload
    responses/          → Frozen display DTOs with camelCase aliases
    requests/           → Request validation schemas
  config/
    settings.py         → Pydantic Settings (single source of truth)
    database.py         → SQLAlchemy engine configuration
```

### File Naming Conventions

| Artifact | Pattern | Example |
|----------|---------|---------|
| Backend adapter | `{source}_adapter.py` | `excel_adapter.py` |
| Backend normalizer | `{domain}_normalizer.py` | `nps_normalizer.py` |
| Backend display DTO | `{domain}_dto.py` | `nps_dto.py` |
| Backend router | `{domain}.py` | `nps.py` |
| Frontend service | `{domain}.ts` | `nps.ts` |
| Frontend hook | `use{Domain}Data.ts` | `useNpsData.ts` |
| Frontend types | `{domain}.ts` | `nps.ts` |
| Contract test | `test_contract_{domain}.py` | `test_contract_nps.py` |

---

## Visualization Decision Matrix

| Data Shape | Recommended Chart | Recharts Component | Notes |
|---|---|---|---|
| Single KPI value + trend | Stat card or flip card | Custom component | Use `cards/` directory |
| Time series (≤3 series) | Area chart with gradient fill | `AreaChart` | Gradient uses brand token at 20% opacity |
| Time series (4+ series) | Line chart, no fill | `LineChart` | Keep legend outside chart area |
| Category comparison | Horizontal bar chart | `BarChart layout="vertical"` | Sort by value descending |
| Part-to-whole | Donut chart | `PieChart innerRadius={60}` | Center label shows total |
| Distribution | Histogram bars | `BarChart` | Fixed bin widths |
| Correlation (2 variables) | Scatter plot | `ScatterChart` | Add regression line if r² > 0.5 |
| Geographic | Choropleth map | `react-leaflet` | Use project's Leaflet setup |
| Small multiples | Grid of sparklines | Grid + mini `AreaChart` | Consistent y-axis scale across grid |
| Ranked list with magnitude | Horizontal bar with labels | `BarChart layout="vertical"` | Show value labels on bars |

### Chart Styling Rules

- Never use default Recharts colors — always use design system tokens from `warm-editorial-ui`
- Grid lines: `var(--border-default)` at `0.3` opacity — or hide entirely for cleaner look
- Axis labels: `var(--ink-muted)`, font-mono (`JetBrains Mono`), `text-xs` (12px)
- Tooltip background: `var(--surface-card)`, `shadow-card`, rounded-lg
- Animation: `800ms` ease-out on initial page load, disabled during tab switches (use `isAnimationActive={!isTabSwitch}`)
- Responsive: Charts must fill container width. Use `ResponsiveContainer width="100%" height={300}`
- Empty state: Show centered muted text message — never a blank space

---

## Mockup-to-React Contract

Every annotated mockup MUST satisfy ALL of these before implementation begins. If ANY annotation is missing, the implementing agent MUST refuse to proceed and request mockup completion.

### 1. DATA-SOURCE annotations

Every dynamic value must have an exact TypeScript field path:
```html
<!-- DATA-SOURCE: npsData.broadband.currentNps -->
```

### 2. COMPONENT annotations

Every visual section must name the exact React component:
```html
<!-- React: <KpiCard product="broadband" data={npsData.broadband} /> -->
```

### 3. IMPLEMENTATION NOTE annotations

Every chart must specify the Recharts component, data keys, and animation config:
```html
<!-- IMPLEMENTATION NOTE [CHART]: AreaChart with dataKey="nps",
     animationDuration={800}, gradient fill using var(--brand-primary) at 20% opacity.
     X-axis: month labels. Y-axis: NPS range -100 to 100. -->
```

### 4. STYLE annotations

Every styled element must specify Tailwind classes and design tokens:
```html
<!-- STYLE: bg-surface-card rounded-xl shadow-card p-6 -->
```

### 5. IMPORT MAP comment

The mockup must include a summary comment listing all required imports:
```html
<!-- IMPORT MAP:
  shadcn/ui: Card, Badge, Separator, Skeleton
  Custom: KpiCard (cards/), NpsTrendChart (charts/), PeriodPicker (filters/)
  Hooks: useNpsData, usePeriods
  Services: npsService
  Stores: useFilterStore
-->
```

### Completeness Check

Before handing off to implementation:
- [ ] Every section has COMPONENT annotations
- [ ] Every dynamic value has DATA-SOURCE with exact JSON path
- [ ] Every chart has IMPLEMENTATION NOTE with Recharts config
- [ ] Every styled element has STYLE annotation with Tailwind classes
- [ ] IMPORT MAP lists all dependencies
- [ ] An implementing agent could build from this mockup alone — zero guesswork

---

## Cross-Cutting: Observability Integration

Every enterprise-dashboard product MUST integrate the VMIE Observability SDK before the VERIFY phase.

### Backend Integration (FastAPI Middleware)

1. Add `vmie-observability-fastapi` to `pyproject.toml` dependencies
2. Import and add the observability middleware in `src/api/main.py`
3. Configure environment variables in `config/.env.api.dev` and `config/.env.api.prod`:
   - `OBS_INGESTION_URL` — URL of the central ingestion service
   - `OBS_API_KEY` — per-app API key (request from platform team)
   - `OBS_APP_ID` — unique app identifier (e.g., `nps-lens`, `appointment-assist`)
   - `OBS_ENVIRONMENT` — `dev` or `prod`
4. Verify middleware captures HTTP request duration and error events automatically
5. Add custom backend events for domain-specific operations if needed

### Frontend Integration (TypeScript SDK)

1. Install `@vmie/observability-web` in `frontend/package.json`
2. Initialize the SDK in `frontend/src/main.tsx`:
   - Set `appId`, `environment`, `ingestionUrl`, `apiKey`
3. Add route tracking hook to the root layout component
4. Configure session correlation via Axios interceptor (`X-Session-ID` header)
5. Add custom business events throughout the app:

### Standard Event Names for Dashboards

| Event | When to Fire | Metadata |
|-------|-------------|----------|
| `tab.viewed` | Every tab switch | `{ tabName, previousTab }` |
| `filter.applied` | Every filter change | `{ filterType, filterValue }` |
| `export.triggered` | Data export clicked | `{ format, rowCount }` |
| `chart.interaction` | Chart tooltip/click | `{ chartType, dataPoint }` |
| `error.unhandled` | Uncaught JS error | `{ message, stack (redacted) }` |
| `app.performance` | Page load complete | `{ lcp, fcp, cls }` |

### Kill Switch

If observability causes issues, set `OBS_API_KEY` to empty string — SDK disables all tracking without code changes or redeployment.

---

## When This Recipe Does NOT Apply

Skip recipe scaffolding for:
- Bug fixes (use standard planning methodology)
- Refactoring (not a data-to-UI workflow)
- Documentation-only changes
- Test-only additions
- Infrastructure or CI/CD changes
- Backend-only work with no UI impact

In these cases, agents use their built-in expertise and plan-embedded skills as usual.

---

## References

This recipe composes these existing skills — read them for detailed patterns:

| Concern | Skill |
|---------|-------|
| Data pipeline (adapter → DTO → contract) | `.github/skills/workflow/data-contract-pipeline/SKILL.md` |
| HTML mockup with annotations | `.github/skills/frontend/mockup/SKILL.md` |
| Design system (Warm Editorial) | `.github/skills/frontend/warm-editorial-ui/SKILL.md` |
| Premium visual design | `.github/skills/frontend/high-end-visual-design/SKILL.md` |
| CSS token architecture | `.github/skills/frontend/css-architecture/SKILL.md` |
| React best practices | `.github/skills/frontend/react-best-practices/SKILL.md` |
| shadcn/ui + Radix patterns | `.github/skills/frontend/shadcn-radix/SKILL.md` |
| React animation + visual engineering | `.github/skills/frontend/premium-react/SKILL.md` |
| FastAPI development | `.github/skills/coding/fastapi-dev/SKILL.md` |
| Backend-to-frontend handoff | `.github/skills/coding/backend-to-frontend-handoff/SKILL.md` |
| Verification workflow | `.github/skills/workflow/verification-loop/SKILL.md` |
