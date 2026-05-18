---
name: data-contract-pipeline
context: fork
description: "**WORKFLOW SKILL** - Build, audit, and validate data-to-UI contracts for apps. Use whenever the user mentions data mapping, UI lineage, DB-to-UI, file-to-UI, DisplayDTOs, source-to-screen mapping, data contracts, schema drift, typed API responses, frontend type alignment, mockup grounding, requirements-to-UI mapping, or asks whether a UI is backed by real DB/file data. Works for DBs, JSON, Markdown, CSV, XLSX, YAML, APIs, existing DTOs, and UI mockups. The workflow discovers app config first, asks only after analysis, reconciles requirements + source capabilities + UI demand, generates read models/normalizers/DisplayDTOs/API/frontend types, and produces lineage, gap reports, and drift tests."
---

# Data Contract Pipeline

Build a verified path from data sources to UI fields without leaking raw database or file structure into frontend components.

Core principle:

```
Requirements + UI demand decide what should be displayed.
DBs/files/APIs decide what can be displayed.
Read models, normalizers, and DisplayDTOs define the safe contract between them.
```

Do not map raw database tables directly to UI components. Always pass through a read model or adapter, a normalizer, a DisplayDTO/API response, frontend types, and UI lineage.

---

## When To Use

Use this skill when the user asks to:

- Map DB tables, views, JSON, Markdown, CSV, XLSX, YAML, or APIs into an app UI.
- Check whether a mockup or existing UI is backed by real data.
- Build DTOs, typed API contracts, frontend types, or data lineage.
- Detect drift between source schema, backend DTOs, frontend types, and UI.
- Find gaps between requirements, backend data, and mockups.
- Create or audit source-to-screen documentation.

Do not use it for a single isolated SQL query unless the user also needs UI/API/DTO mapping or lineage.

---

## Required Operating Model

Default to **agent-first discovery, then user Q&A**.

1. First inspect the app repo, source docs, DB/file schemas, existing APIs, DTOs, frontend routes, and mockups.
2. Then summarize evidence and ask only the unresolved questions.
3. Ask no more than 3 high-impact questions at once.
4. Save user answers as `contract_decisions.json` or include a clearly named decision section in the generated report.

Never ask for details that can be found in the repo. Never print secrets or full connection strings.

---

## Standard Stages

### Stage 1 - Intake

Collect or infer:

- App repo path.
- Source inputs: DB/table/view names, connection config, APIs, JSON/Markdown/CSV/XLSX/YAML files, or schema docs.
- Consumer inputs: requirements docs, PRDs, tickets, existing routes, UI mockups, HTML/JSX/TSX files, screenshots, or final UI files.
- Desired mode: `build`, `audit`, `drift-check`, or `lineage-only`.

If DB credentials are needed, search the app repo first. Look for `.env*`, settings modules, connection factories, Docker Compose, deployment manifests, README/runbooks, and CI variables. Ask the user only for missing or ambiguous values.

Use `scripts/discover_connections.py` when an app repo is available.

### Stage 2 - Connection Discovery

Identify data access configuration without exposing secrets:

- Provider and driver.
- Host/server, port, database, schema.
- Auth mode: trusted, SQL login, service account, cloud identity, API token, file path, or unknown.
- Secret variable names, not secret values.
- Staleness or conflicts across config files.

If a connection test is possible, use a read-only/safe query such as `SELECT 1` or metadata inspection. If not possible, continue with docs/DDL and mark confidence lower.

Output: `connection_manifest.json`.

### Stage 3 - Source Discovery

Inspect what the backend data can provide.

For DBs:

- Discover schemas, tables, views, columns, PK/FK relationships, nullable fields, indexes when permitted, safe row estimates, and sample rows only from small or explicitly approved tables.
- Prefer metadata and bounded samples. Do not aggregate large LIVE tables without approval.
- Detect documented-vs-live schema drift.

For files:

- Parse JSON, Markdown, CSV/TSV, XLSX, YAML, plain text, and embedded structured data.
- Capture field paths, types, examples, optionality, and source file paths.

Use existing `extract_schema.py` for low-level schema extraction. Use `scripts/discover_sources.py` to emit a normalized manifest.

Output: `source_manifest.json`.

### Stage 4 - Requirements and UI Demand Extraction

Extract what the product/UI needs.

Requirement sources:

- PRDs, markdown docs, tickets, runbooks, API docs, business metric definitions.

UI sources:

- Existing routed pages, React/Vue/Svelte components, HTML mockups, `data-react` annotations, visible labels, mock data constants, forms, tables, charts, filters, and exports.

Use `scripts/extract_requirements.py` and `scripts/extract_ui_demand.py`.

Outputs:

- `requirements_manifest.json`
- `ui_demand_manifest.json`

### Stage 5 - Analysis Summary and Q&A Checkpoint

Before generating contracts, present a short evidence summary:

- Sources found.
- Requirements found.
- UI demand found.
- Candidate mappings.
- Conflicts and missing evidence.
- Items requiring user/product decisions.

Ask only questions that affect mapping, scope, source access, DTO shape, UI placement, metric definitions, or release readiness.

Do not ask open-ended broad questions. Prefer concrete defaults:

- "I found two DB configs. I will use `config/.env.api.dev` unless you want the production config."
- "The mockup has a Fraud page but no backed source. I will mark it `mockup-only` and remove/replace it in production unless you promote it with a requirement and source."
- "The requirements mention revenue at risk but do not define the formula. I will block this metric until the formula is confirmed."

Persist answers in `contract_decisions.json`.

### Stage 6 - Reconciliation and Status Classification

Compare requirements, UI demand, source capabilities, and existing contracts.

Every item must get one of these statuses:

| Status | Meaning |
|--------|---------|
| `contract-backed` | Requirement/UI field has verified source, transform, DTO/API, and UI placement. |
| `required-unplaced` | Required by docs/backend but missing from mockup/final UI placement. |
| `source-capability-only` | Source has data but no requirement/UI demand uses it. Do not expose by default. |
| `mockup-only` | Present in mockup/demo data but not part of the backed production UI unless promoted by the user. |
| `partially-backed` | Some fields or states map, but required data, formula, freshness, or source coverage is incomplete. |
| `blocked` | Cannot map safely due to missing credentials, missing source, ambiguous metric, source error, or unsafe query. |
| `deferred` | Explicitly out of current release scope. |

Use `scripts/reconcile_contract.py`.

Outputs:

- `mapping_manifest.json`
- `gap_register.json`

### Stage 7 - Read Model and DTO Design

Generate or specify layers in this order:

1. Source adapter or SQL/file read model.
2. Ingestion/read model DTO: exact shape of source query/file/API.
3. Normalizer: transforms source semantics into app semantics.
4. DisplayDTO: stable frontend-facing contract with aliases.
5. OpenAPI-first REST API route/response contract.
6. MCP-first tools/resources for approved app data capabilities.
7. Frontend TypeScript types.
8. Typed frontend service/hook and optional MCP client.
9. UI binding to components.

Rules:

- Raw source fields do not cross into UI components.
- DisplayDTO fields must be named for the UI/domain, not for vendor/source tables.
- DB-only fields remain `source-capability-only` unless required by UI, filters, exports, lineage panels, audit, or diagnostics.
- Metric definitions must include formula, grain, timezone, unit, null semantics, and freshness.
- REST endpoints must be OpenAPI-first: define path, method, params, response schema, auth, errors, and examples before implementation.
- MCP endpoints must be MCP-first: define tool/resource name, input schema, output schema, auth/PII policy, read/write behavior, and rate-limit expectation before implementation.
- Do not expose every read model as public REST/MCP. Expose only approved, backed, permissioned capabilities.

Use current templates in `assets/` and lower-level scripts:

- `extract_schema.py`
- `drift_check.py`
- `ts_dto_compare.py`
- `generate_mapping_doc.py`

Use `scripts/compile_read_catalog.py` for query/read-model catalog scaffolding.
Use `scripts/generate_api_contracts.py` for OpenAPI and MCP contract scaffolding.

### Stage 8 - UI Lineage Generation

Every production UI field must trace:

```
UI component -> frontend prop/type -> API response field -> DisplayDTO field
-> normalizer transform -> read model field -> source object/field -> source system
```

Output `lineage_manifest.json` with:

- Component/page/route.
- Display label.
- DTO/API field.
- Source object and column/path.
- Transform and formula.
- Status and confidence.
- PII classification.
- Known blockers.

Use `scripts/validate_lineage.py` to check coverage.

### Stage 9 - Validation and Drift Tests

Generate or run:

- Source schema drift checks.
- DTO-to-frontend type checks.
- Contract tests using golden samples.
- Query smoke tests for read models.
- UI lineage coverage checks.
- Gap report freshness checks.

Failure mode:

- Exploratory/evolving contracts: warn and report.
- Frozen contracts: fail CI on unmapped fields, DTO/type drift, stale lineage, and missing production UI lineage.

Use `scripts/generate_gap_report.py` for human-readable gap reporting.

---

## Missing UI Handling

If backend data or requirements demand a UI element but the mockup/final UI lacks it:

1. Mark it `required-unplaced`.
2. Generate `ui_gap_brief.md` with:
   - Requirement/source evidence.
   - Proposed page or workflow area.
   - Suggested component type: KPI, table column, filter, chart, detail panel, export, lineage panel, or alert.
   - DisplayDTO fields needed.
   - Acceptance criteria.
3. Do not silently add it to a random screen.
4. Ask the user/product owner to place it, accept the proposed placement, or mark it `deferred`.

If a mockup contains UI that no requirement/source supports:

1. Mark it `mockup-only`.
2. Treat it as prototype-only, not a backlog item.
3. Do not build production REST or MCP endpoints for it.
4. Consult the user and either remove it from the production UI, replace it with a data-backed element, or promote it by adding a requirement and source contract.

Use `deferred` only when the user explicitly says the feature is intended for a later release.

---

## Landmines

- **Secret leakage**: mask passwords, tokens, and full connection strings.
- **SQL performance**: no unbounded aggregation on large LIVE tables; use read models, pre-aggregates, or bounded queries.
- **PII exposure**: classify MSISDN, IMSI, email, customer IDs, addresses, names, and account IDs.
- **Mockup hallucination**: demo data is not a production contract.
- **Backend overexposure**: do not expose DB-only fields just because they exist.
- **Metric ambiguity**: block metrics without formula, grain, unit, timezone, and freshness.
- **Date/time drift**: define timezone and date grain.
- **Currency/units drift**: define cents vs euros, bytes vs MB/GB, percentages vs fractions.
- **Null semantics**: distinguish zero, null, missing, unavailable, and not applicable.
- **Auth drift**: app config can be stale; test and report the actual connection mode.
- **Schema doc drift**: live schema wins over stale docs unless the user confirms otherwise.
- **Service contract sprawl**: do not publish every read model as REST/MCP.
- **MCP security**: every tool/resource needs auth, PII, rate limit, and read/write behavior.
- **Small-model fragility**: force stage artifacts and status classes so weaker models do not skip reconciliation.

---

## Enterprise Pattern Check

This workflow matches the practical version of mature engineering patterns:

- Consumer-driven contracts.
- Read models and DTO boundaries.
- Typed APIs and generated/checked frontend types.
- OpenAPI-first REST and MCP-first service contracts.
- Source-to-screen lineage.
- Contract and drift tests.
- Gap registers for product/design/backend mismatches.

Large teams may add heavier tools such as GraphQL schema registries, OpenAPI codegen, dbt semantic layers, DataHub/OpenLineage, schema registries, or internal developer portals. For app-by-app agent development, this skill plus deterministic scripts is the simpler and more reliable approach.
