---
name: data-contract-pipeline
description: "**WORKFLOW SKILL** — Build and validate end-to-end typed data pipelines from source payload to frontend display. Generates Pydantic ingestion models, normalizers, display DTOs, FastAPI routers, TypeScript types, typed service functions, and contract tests from a raw data sample. Detects and reports drift between layers. USE FOR: building a new data pipeline from any source format (JSON, Markdown, CSV, XLSX, YAML, DB tables, plain text), discovering database schemas and tables, extracting schemas with data sampling from any SQL database (SQL Server, PostgreSQL, MySQL, SQLite), detecting embedded structured data (JSON, XML, markdown, YAML) inside DB columns, multi-table aggregation with FK-based DTO nesting, adding a DTO layer to an existing adapter, auditing drift between backend DTOs and frontend types, generating contract tests for data validation, creating golden sample fixtures, aligning TypeScript types with Python DTOs, reviewing data mapping docs for staleness, tracking schema evolution over time. Use when the user says 'data contract', 'build DTO', 'create types from JSON', 'payload to API', 'data pipeline', 'drift check', 'contract test', 'schema drift', 'type alignment', 'golden sample', 'data mapping', 'schema evolution', 'schema baseline', 'extract schema', 'data is in the database', 'table in SQL Server', 'discover tables', 'what tables exist', or provides raw data in any structured format and wants typed backend+frontend code generated from it."
---

# Data Contract Pipeline

Build typed, validated data pipelines from raw source payloads to frontend display — with drift detection baked into every run.

## When to Use

- User provides a raw data source (JSON, CSV, Markdown, XLSX, YAML, TXT, or DB table) and wants typed code generated end-to-end
- An adapter exists but there's no DTO, normalizer, or typed frontend service yet
- All layers exist but may have drifted (fields added/removed/renamed without propagation)
- User wants to audit an existing pipeline for contract violations
- User says "build data contract", "generate types from this JSON", "drift check", etc.

## Who Can Load This Skill

This skill works with any agent. It produces instructions, not agent-specific behavior.

| Agent | How They Use It |
|-------|----------------|
| Default / `@Implement` | Full end-to-end pipeline generation |
| `@Frontend Developer` | TypeScript types + service functions from a DTO |
| `@Data Engineer` | Adapter + ingestion model + normalizer |
| `@Tester` | Contract test generation and drift audit |
| `@Code Reviewer` | Audit existing pipeline for drift and contract violations |
| `@Anchor` | Evidence-first verification of each layer |
| `@Preflight` | Pre-implementation validation of data contracts in a plan |
| `@Orchestrator` | Route to appropriate specialist based on detected scenario |

---

## Entry Flow

### Step 1 — Gather Input

Ask the user for **one thing**: the raw source data (any structured file, DB table reference, or pasted payload).

By default, run in **agent-first / mostly agent-last** mode:
- Agent discovers schema and field coverage from available data
- Agent builds and maintains the golden sample set
- User input is primarily business intent and freeze state (for example: "schema is now frozen")

Prompt:
> "Provide the raw source data — a JSON file, CSV, markdown report, XLSX workbook, YAML config, text file, DB table name, or paste the payload. I'll analyze it and handle the rest."

If the user provides a file path, read it. If they paste data, parse it. If they describe a schema, confirm your understanding before proceeding.

**DB source detection** — When the user mentions a database, table, or column (e.g., "the data is in the appointments table in our SQL Server"), treat this as a DB source. Do NOT ask the user for `--format db` or CLI flags. Instead:
1. Ask for the connection details if not already in project config (DB host, name, credentials)
2. Use `extract_schema.py --format db --discover` to enumerate all tables
3. Use `--table <name> --sample 50` to extract schema with data sampling
4. The script auto-detects embedded formats (JSON, XML, markdown, YAML, pipe-delimited) in string columns

**Supported input formats** (auto-detected from file extension or user description):
- **JSON** (.json) — parsed directly, recursive nesting, list-of-objects, Field(alias=...)
- **Markdown** (.md) — tables (2-col KV + multi-col row models), bold KV, code block KV, bullet KV, outer wrapper stripping
- **CSV/TSV** (.csv/.tsv) — column headers, type inference from sample rows (up to 100)
- **XLSX** (.xlsx/.xls) — openpyxl, multi-sheet support, same column logic as CSV
- **YAML** (.yaml/.yml) — safe_load, delegates to JSON dict logic for nested extraction
- **Plain text** (.txt/.log) — `Key: Value`, `Key = Value` patterns, `[Section]` headers
- **DB table** — SQLAlchemy inspect + data sampling + embedded format detection. Supports SQL Server, PostgreSQL, MySQL, SQLite, and any SQLAlchemy-compatible engine.

All formats produce a unified `extract_schema.py` output: sections with typed fields → Pydantic model source code.

### Step 1.5 — DB Discovery (DB sources only)

When the source is a database, run discovery BEFORE schema extraction:

**1. Enumerate tables and views:**
```bash
python extract_schema.py --format db --connection-string "..." --discover
```
This lists all tables/views with column counts, primary keys, and foreign key relationships. Present this to the user so they can confirm which tables contain the data they need.

**2. Extract with data sampling:**
```bash
python extract_schema.py --format db --connection-string "..." --table appointments --sample 50
```
Sampling does three things metadata-only inspection cannot:
- **Type refinement** — a `VARCHAR(MAX)` column's actual values reveal whether it's always numeric, always a date, or truly free-text
- **Embedded format detection** — discovers JSON objects, XML documents, markdown, YAML, or pipe-delimited data stored inside string columns. When found, the embedded content is parsed and its nested schema is extracted automatically.
- **Real examples** — provides actual sample values for the generated model comments

**3. Multi-table aggregation:**
When the user's data spans multiple tables (common for dashboards), run extraction on each relevant table, then:
- Use FK relationships to suggest DTO nesting (e.g., `Appointment.customer` as a nested model)
- Propose a unified display DTO that joins across tables
- Generate the normalizer with join logic

**4. Relationship mapping:**
The discovery output includes FK chains. Use these to inform:
- Which tables to join for the API endpoint
- How to structure nested DTOs
- Which fields are IDs vs display data

### Step 2 — Analyze and Ask Follow-ups

After reading the source data:

1. **Infer the schema** — list all top-level and nested keys with their types
2. **Detect the scenario** (see §Scenarios below)
3. **Ask targeted follow-ups** — only what you can't infer:

```markdown
I've analyzed the payload. Here's what I found:

**Schema** (N top-level keys, M nested objects):
| Key | Type | Sample Value |
|-----|------|-------------|
| ... | ...  | ...         |

**Detected scenario**: [Greenfield / Partial / Full-with-drift / Audit]

**Questions:**
1. What should the display DTO be called? (e.g., `NpsMonthlyResponse`)
2. Which keys should be exposed to the frontend? (all / subset)
3. Should camelCase aliasing be applied? (recommended for JS/TS frontends)
4. Where does this data come from? (file on disk / external API / database query)
```

### Step 3 — Generate Layers

Generate code for each layer in dependency order. Read the [layer responsibilities reference](./references/layer-responsibilities.md) for detailed specs per layer.

**Generation order:**
1. **Ingestion Model** (`src/models/ingestion/`) — 1:1 with raw payload shape
2. **Display DTO** (`src/models/responses/`) — frozen, aliased, no `extra="ignore"`
3. **Normalizer** (`src/services/normalizers/`) — transforms ingestion → display
4. **API Router** (if applicable) — FastAPI endpoint with `response_model=`
5. **Frontend Types** (`frontend/src/types/`) — TypeScript interfaces mirroring DTO
6. **Frontend Service** (`frontend/src/services/`) — typed fetch functions
7. **Golden Sample Set** (`tests/fixtures/payloads/`) — agent-generated fixture(s) with coverage metadata
8. **Contract Tests** (`tests/unit/test_contract_*.py`) — drift detection tests

Use the templates in [assets/](./assets/) as starting points. Adapt to the project's existing patterns — read the project's `copilot-instructions.md`, existing models, and services first.

### Step 4 — Run Drift Checks

After generation, validate alignment between all layers:

```
✅ Ingestion Model covers 100% of payload keys (recursive, all depths)
✅ Display DTO maps to 100% of ingestion model fields (recursive)
✅ Normalizer transforms all ingestion fields to DTO fields
✅ TypeScript types match DTO aliases 1:1
❌ Payload key "surveys.broadband.newField" not in DTO → DRIFT DETECTED
```

Report findings in this format. If drift is found, provide the fix.

**Drift test mode**: If the upstream schema is still evolving, contract tests emit `warnings.warn()` (CI passes). After freeze, flip `SCHEMA_FROZEN = True` — drift becomes a hard assertion failure. See §Schema Evolution Lifecycle.

### Step 5 — Nominate Golden Sample(s)

Golden samples are **nominated by the agent**, not manually assembled by the user in normal flow.

1. Scan available payload corpus and compute recursive field coverage.
2. Build fixture set by role:
    - `sample.core.json` for common fields
    - `sample.edge.json` for optional/rare branches
    - `sample.nulls.json` for null/empty behavior (if relevant)
3. Emit coverage report and uncovered-path list.
4. Promote to canonical `sample.json` when coverage and stability criteria are met.
5. When user signals **"schema/model is frozen"**, enforce hard gate:
    - Require full coverage or explicit `KNOWN_EXCLUDED_KEYS`
    - Set `CONTRACT_SCHEMA_FROZEN=1` (preferred) or `_contract_state.json` with `{"schema_frozen": true}`

Freeze intent matching should be semantic, not exact-phrase. Treat these as equivalent:
- "schema is frozen"
- "model is frozen"
- "schema/model frozen"
- "freeze the schema"
- "freeze the model/contract"

If user forgets to mention freeze state, apply fallback precedence:
1. `CONTRACT_SCHEMA_FROZEN` env var (explicit override)
2. `_contract_state.json` marker in payload fixture folder
3. CI fallback (`CI=true` + `sample.json` exists) → hard mode
4. Otherwise soft mode (`warnings.warn`)

Only request a user-provided payload when no data source is accessible to the agent.

---

## Scenarios

### Greenfield (No existing pipeline)

**Detection**: No `src/models/` files for this data source, or user says "new data source."

**Action**: Generate all 8 layers from scratch. Ask user which layers they need (some projects don't have frontend, some don't need normalizers for simple payloads).

### Partial (Adapter exists, no DTO/normalizer)

**Detection**: Adapter or service fetches data, but returns raw `dict` or untyped `pd.DataFrame`. No Pydantic model for the response.

**Action**: 
1. Read the adapter to understand the raw data shape
2. Discover representative records from available data and auto-nominate golden sample set
3. Generate layers 1-8, integrating with the existing adapter

### Full-with-Drift (All layers exist, possibly misaligned)

**Detection**: Pydantic models exist, TypeScript types exist, but user reports bugs or says "drift check."

**Action**:
1. Read the golden sample set and/or actual data file
2. Read the display DTO
3. Read the TypeScript types
4. Compare field-by-field using the [drift check catalog](./references/drift-check-catalog.md)
5. Report all mismatches with fixes

### Audit Only

**Detection**: User says "audit", "review contracts", or "check alignment."

**Action**: Read-only analysis. No code generation — just a report of findings.

---
## Schema Evolution Lifecycle

Most pipelines begin with an evolving schema. The three-layer defence handles this:

| Layer | Mechanism | What it does |
|-------|-----------|--------------|
| **1 — Passthrough** | `extra="allow"` (`_FLEX` constant) on ingest DTOs | Unknown keys flow through `model_extra`, not dropped |
| **2 — Recursive drift detection** | `_collect_dropped_keys()` in contract tests | Compares JSON keys vs model fields at every nesting depth |
| **3 — Exclusion allow-list** | `KNOWN_EXCLUDED_KEYS` with fnmatch globs | Intentionally untyped keys excluded from drift reports |

### Workflow by Schema State

| State | Ingest DTO config | Drift test mode | Toggle |
|---|---|---|---|
| **Evolving** | `extra="allow"` | Soft: `warnings.warn()` — CI passes | `SCHEMA_FROZEN = False` (default) |
| **Frozen** | `extra="allow"` (ingest) / `extra="forbid"` (display) | Hard: `assert` — CI blocks | `CONTRACT_SCHEMA_FROZEN=1` OR `_contract_state.json` OR CI fallback |
| **Key intentionally untyped** | n/a | Excluded from both modes | Add to `KNOWN_EXCLUDED_KEYS` with ticket ref |

### Decision Checklist for New Keys

1. **Key in every payload?** → Add typed field now.
2. **Experimental / may be removed?** → Leave untyped; `extra="allow"` forwards it. Add to exclusion list if noisy.
3. **Deprecated upstream?** → Add to `KNOWN_EXCLUDED_KEYS` permanently.
4. **Schema frozen?** → Flip to hard assert. Any untyped key fails CI.

Hard/soft mode resolution uses precedence from the contract-test template:
1. `CONTRACT_SCHEMA_FROZEN` env var
2. `_contract_state.json` marker
3. CI fallback (`CI=true` + `sample.json` exists)
4. default soft mode

See [layer-responsibilities.md](./references/layer-responsibilities.md#schema-evolution-lifecycle) for full details and anti-patterns.

---
## Drift Check Catalog

Quick reference — see [references/drift-check-catalog.md](./references/drift-check-catalog.md) for full details.

| Check | What It Catches |
|-------|----------------|
| Payload → Ingestion Model | Missing keys (recursive, all nesting depths), type mismatches, new keys not in model |
| Ingestion → Display DTO | Fields present in ingestion but silently dropped in DTO (recursive) |
| DTO `extra` config | `extra="ignore"` on display DTOs (silent data loss) |
| DTO → TypeScript | Field name/alias mismatch, missing fields, type mismatch |
| DTO → API Router | `response_model` not set, or set to wrong type |
| Mapping Doc → Reality | Doc claims a field maps to X but code shows Y |
| Drift test mode | `SCHEMA_FROZEN` flag doesn't match actual upstream state (D11) |
| Exclusion allow-list | Intentionally untyped keys missing from `KNOWN_EXCLUDED_KEYS` (D12) |
| DB embedded format | String column contains structured data (JSON/XML) not extracted to typed model (D13) |
| DB FK → DTO nesting | FK relationship exists in DB but DTO is flat — no nested model generated (D14) |

---

## Code Generation Conventions

These conventions make generated code project-agnostic. Override with project-specific patterns when detected.

### Python (Pydantic v2)

```python
from pydantic import BaseModel, ConfigDict, Field

class {{DtoName}}(BaseModel):
    """Display DTO for {{source_name}} data."""
    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        extra="forbid",
    )

    {{field_name}}: {{python_type}} = Field(alias="{{camelCaseName}}")
```

### TypeScript

```typescript
export interface {{DtoName}} {
  {{camelCaseName}}: {{tsType}};
}
```

### Contract Test

```python
import json
from pathlib import Path
import pytest

PAYLOAD_DIR = Path(__file__).parent.parent / "fixtures" / "payloads"

class TestPayloadContract:
    """Validate {{source_name}} payload against {{DtoName}}."""

    def test_golden_sample_validates(self):
        raw = json.loads(
            (PAYLOAD_DIR / "{{source_slug}}" / "sample.json").read_text()
        )
        dto = {{DtoName}}.model_validate(raw)
        assert dto is not None

    def test_no_uncovered_keys(self):
        raw = json.loads(
            (PAYLOAD_DIR / "{{source_slug}}" / "sample.json").read_text()
        )
        dto_aliases = {
            info.alias or name
            for name, info in {{DtoName}}.model_fields.items()
        }
        uncovered = set(raw.keys()) - dto_aliases
        assert not uncovered, f"Payload keys missing from DTO: {uncovered}"
```

---

## Reference Files

Load these as needed — don't read all upfront.

| File | When to Read |
|------|-------------|
| [references/layer-responsibilities.md](./references/layer-responsibilities.md) | When generating any layer — defines exact responsibilities and anti-patterns per layer |
| [references/drift-check-catalog.md](./references/drift-check-catalog.md) | When running drift checks — detailed detection rules and fix patterns |
| [references/consumer-driven-contracts.md](./references/consumer-driven-contracts.md) | When explaining the approach to a user or reviewing contract design decisions |

## Asset Templates

Templates in [assets/](./assets/) provide starting points. Read the specific template before generating that layer.

| Template | Purpose |
|----------|---------|
| [assets/ingestion-model.py.template](./assets/ingestion-model.py.template) | Raw Pydantic model matching source payload 1:1 |
| [assets/display-dto.py.template](./assets/display-dto.py.template) | Frozen display DTO with aliases |
| [assets/normalizer.py.template](./assets/normalizer.py.template) | Ingestion → Display DTO transformer |
| [assets/adapter.py.template](./assets/adapter.py.template) | Source data adapter skeleton |
| [assets/api-router.py.template](./assets/api-router.py.template) | FastAPI router with typed response |
| [assets/frontend-types.ts.template](./assets/frontend-types.ts.template) | TypeScript interface mirroring DTO |
| [assets/frontend-service.ts.template](./assets/frontend-service.ts.template) | Typed fetch/axios service |
| [assets/contract-test.py.template](./assets/contract-test.py.template) | pytest contract drift tests |
| [assets/mapping-doc.md.template](./assets/mapping-doc.md.template) | UI→JSON mapping doc template |

## Scripts

Utility scripts for automated checks. Run via terminal.

| Script | Purpose |
|--------|---------|
| [scripts/extract_schema.py](./scripts/extract_schema.py) | Unified schema extractor — any format (JSON, MD, CSV, XLSX, YAML, DB, text) → Pydantic model code. Supports `--save-baseline` / `--diff` for schema evolution tracking. DB mode: `--discover` to enumerate tables, `--sample N` for data sampling, `--schema` for DB schema targeting. |
| [scripts/drift_check.py](./scripts/drift_check.py) | Compare DTO fields vs payload keys → report mismatches |
| [scripts/ts_dto_compare.py](./scripts/ts_dto_compare.py) | Compare TypeScript interface properties vs Python DTO fields |
| [scripts/generate_mapping_doc.py](./scripts/generate_mapping_doc.py) | Generate or validate a field mapping doc from Pydantic models (`--output` / `--check`) |

### DB Discovery & Sampling

When the source is a database:

```bash
# 1. Discover all tables/views with columns, PKs, FKs
python scripts/extract_schema.py --format db --connection-string "mssql+pyodbc://..." --discover

# 2. Discover within a specific schema
python scripts/extract_schema.py --format db --connection-string "..." --discover --schema dbo

# 3. Extract single table (metadata only — original behavior)
python scripts/extract_schema.py --format db --connection-string "..." --table appointments

# 4. Extract with data sampling (50 rows, detects embedded JSON/XML/markdown)
python scripts/extract_schema.py --format db --connection-string "..." --table appointments --sample 50

# 5. Extract from a specific schema
python scripts/extract_schema.py --format db --connection-string "..." --table appointments --schema dbo --sample 50
```

Connection string examples:
- **SQL Server**: `mssql+pyodbc://user:pass@host/dbname?driver=ODBC+Driver+17+for+SQL+Server`
- **PostgreSQL**: `postgresql://user:pass@host:5432/dbname`
- **MySQL**: `mysql+pymysql://user:pass@host:3306/dbname`
- **SQLite**: `sqlite:///path/to/db.sqlite3`

### Schema Evolution Tracking

When source schemas change frequently (common with LLM-generated reports, evolving APIs, or pre-freeze data):

```bash
# 1. Save a baseline snapshot from current data
python scripts/extract_schema.py data.json --save-baseline baseline.json

# 2. Later, diff against the baseline to detect drift
python scripts/extract_schema.py data_v2.json --diff baseline.json
# Output: + ADDED field_x: str | - REMOVED old_field: int | ~ CHANGED field_y: str -> int
```

The baseline is a JSON file containing field names, types, source patterns, and extraction timestamp. Diff reports three change types: `ADDED`, `REMOVED`, `TYPE_CHANGED`.
