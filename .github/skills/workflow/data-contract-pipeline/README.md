# Data Contract Pipeline — How to Use

This skill builds and validates end-to-end typed data pipelines: from raw source payload → Pydantic ingestion model → display DTO → API router → TypeScript types → frontend service, with drift detection baked into every layer.

This guide covers **three common scenarios** and shows exactly how to use agents, scripts, or both in each.

Default operating model: **agent-first and mostly agent-last**. The agent should infer schema, assemble golden sample fixtures, and run validation. User input is mainly intent, constraints, and the freeze signal ("schema/model is now frozen").

---

## Quick Reference

| What you want | Use |
|---------------|-----|
| Build a brand-new pipeline from raw data | Agent (greenfield scenario) |
| Add a DTO layer to an existing adapter | Agent (partial scenario) |
| Update existing DTOs after source schema changed | Script → Agent |
| Check for drift in CI | Script (`drift_check.py`, `generate_mapping_doc.py --check`) |
| Generate a mapping doc | Script (`generate_mapping_doc.py`) or Agent |
| Audit alignment across all layers | Agent (audit scenario) or Script |
| Nominate golden samples | Agent auto-nominates from corpus; user signals freeze |

---

## Scenario 1 — New App with a Schema Document

**Situation**: You have a raw data source (JSON file, CSV, Markdown report, XLSX workbook, etc.) and need a complete typed pipeline from scratch.

### Using the Agent

1. Open Copilot Chat and load the skill (the skill auto-activates when you say "data contract", "build DTO", etc.)

2. **Prompt the agent:**

   ```
   I have a new data source: [path/to/data.json]
   Build a complete data contract pipeline for it.
   ```

   Or be more specific:

   ```
   Build a data contract pipeline from data/monthly/2026-03.json.
   The display DTO should be called NpsMonthlyResponse.
   Apply camelCase aliases for the frontend.
   Expose all fields except internal_id and raw_score.
   ```

3. **What the agent does** (in order):
   - Reads the source file and extracts the schema
   - Asks follow-up questions (DTO name, which fields, aliasing preference)
   - Auto-nominates golden sample fixtures from available records
   - Generates all 8 layers:
     1. Ingestion model (`src/models/ingestion/`)
     2. Display DTO (`src/models/responses/`)
     3. Normalizer (`src/services/normalizers/`)
     4. API router (`src/api/routers/`)
     5. TypeScript types (`frontend/src/types/`)
     6. Frontend service (`frontend/src/services/`)
     7. Golden sample fixture set (`tests/fixtures/payloads/`)
     8. Contract tests (`tests/unit/test_contract_*.py`)
   - Runs drift checks to validate alignment
   - Reports the result

### Golden Sample Nomination (Agent-first)

The user should not be required to handcraft an all-fields payload. The agent should:

1. Scan available payloads and compute recursive field coverage
2. Build fixture set:
   - `sample.core.json` (common paths)
   - `sample.edge.json` (rare/optional paths)
   - `sample.nulls.json` (null/empty behavior)
3. Produce a coverage report and uncovered path list
4. Promote canonical `sample.json` when quality criteria are met

**Freeze trigger**: treat all semantic variants as equivalent, including:
- "schema is frozen"
- "model is frozen"
- "schema/model frozen"
- "freeze the schema/model/contract"

When freeze intent is detected, switch to hard gating:
- `CONTRACT_SCHEMA_FROZEN=1` (preferred explicit override)
- or fixture marker `_contract_state.json` with `{"schema_frozen": true}`
- Require full coverage or explicit `KNOWN_EXCLUDED_KEYS`

If user forgets to mention freeze, fallback precedence is:
1. `CONTRACT_SCHEMA_FROZEN` env var
2. `_contract_state.json` marker file
3. CI fallback (`CI=true` and `sample.json` exists) → hard mode
4. otherwise soft mode

### Using Scripts (for the schema extraction step)

If you want to understand the schema before involving the agent:

```bash
# Extract schema from any supported format
python scripts/extract_schema.py data/monthly/2026-03.json

# Save a baseline for future comparison
python scripts/extract_schema.py data/monthly/2026-03.json --save-baseline baseline.json
```

Then hand the output to the agent:

```
Here's the schema I extracted (see baseline.json).
Build the full pipeline from it. DTO name: NpsMonthlyResponse.
```

### Using Both (recommended for complex sources)

1. **Script first** — extract and review the schema:
   ```bash
   python scripts/extract_schema.py data/complex-report.json
   ```
2. **Review** — confirm the field list and types look right
3. **Agent** — hand the schema to the agent to generate all layers:
   ```
   Build a data contract pipeline from this schema.
   I've already reviewed it — generate all 8 layers.
   ```

---

## Scenario 2 — Introducing a DTO Pipeline to an Existing Adapter

**Situation**: You already have a service or adapter that fetches data, but it returns raw `dict` or untyped `pd.DataFrame`. You want to add proper Pydantic models, types, and contract tests.

### Using the Agent

```
I have an existing adapter at src/services/nps_data_service.py 
that returns raw JSON dicts. Add a typed DTO pipeline:
- Ingestion model for the raw payload shape
- Display DTO with camelCase aliases
- Contract tests for drift detection
- TypeScript types for the frontend
```

The agent will:
1. Read the existing adapter to understand the data shape
2. Discover representative records and generate golden sample fixture set
3. Generate the missing layers without touching the existing adapter
4. Wire the new models into the existing service

### Using Scripts

Run a drift check to see what's missing:

```bash
# After generating models, verify alignment
python scripts/drift_check.py \
    --payload tests/fixtures/payloads/nps_monthly/sample.json \
    --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
    --dto src.models.responses.nps_monthly:NpsMonthlyResponse
```

Generate a mapping doc for visibility:

```bash
python scripts/generate_mapping_doc.py \
    --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
    --dto src.models.responses.nps_monthly:NpsMonthlyResponse \
    --ts-types frontend/src/types/nps-monthly.ts \
    --output docs/mapping/nps-monthly-mapping.md
```

### Using Both

1. **Agent** — generates the models, tests, and types
2. **Script** — validates alignment post-generation:
   ```bash
   python scripts/drift_check.py \
       --payload tests/fixtures/payloads/nps_monthly/sample.json \
       --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
       --dto src.models.responses.nps_monthly:NpsMonthlyResponse
   ```
3. **Script** — generates the mapping doc:
   ```bash
   python scripts/generate_mapping_doc.py \
       --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
       --dto src.models.responses.nps_monthly:NpsMonthlyResponse \
       --output docs/mapping/nps-monthly-mapping.md
   ```

---

## Scenario 3 — Updating Existing DTOs After Source Schema Changes

**Situation**: The upstream data source added new fields, removed some, or changed types. Your existing pipeline is now drifting.

### Step 1 — Detect the drift

#### With scripts

```bash
# Compare new payload against your models
python scripts/drift_check.py \
    --payload data/monthly/2026-04.json \
    --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
    --dto src.models.responses.nps_monthly:NpsMonthlyResponse
```

Output example:
```
❌ 3 drift finding(s):

  D1: Payload key 'newMetric' not in ingestion model
  D1: Payload key 'surveys.broadband.extraField' not in ingestion model
  D2: Ingestion field 'deprecated_score' not in display DTO
```

#### With schema evolution tracking

```bash
# Diff the new payload against a saved baseline
python scripts/extract_schema.py data/monthly/2026-04.json \
    --diff baseline.json
```

Output example:
```
+ ADDED newMetric: float
+ ADDED surveys.broadband.extraField: str
- REMOVED deprecated_score: int
```

### Step 2 — Fix the drift

#### With the agent

```
The drift check found 3 issues (see above).
Update the pipeline:
- Add newMetric and surveys.broadband.extraField to the ingestion model and DTO.
- Remove deprecated_score from the ingestion model (add to KNOWN_EXCLUDED_KEYS if still in payload).
- Update TypeScript types to match.
- Regenerate the mapping doc.
```

#### With scripts (post-fix verification)

After the agent makes changes, verify everything is clean:

```bash
# Re-run drift check
python scripts/drift_check.py \
    --payload data/monthly/2026-04.json \
    --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
    --dto src.models.responses.nps_monthly:NpsMonthlyResponse

# Regenerate mapping doc
python scripts/generate_mapping_doc.py \
    --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
    --dto src.models.responses.nps_monthly:NpsMonthlyResponse \
    --ts-types frontend/src/types/nps-monthly.ts \
    --output docs/mapping/nps-monthly-mapping.md

# Save new baseline
python scripts/extract_schema.py data/monthly/2026-04.json \
    --save-baseline baseline.json
```

If the model is now frozen, also flip hard drift mode in contract tests:

```bash
# Example environment-triggered hard mode in CI
$env:CONTRACT_SCHEMA_FROZEN = "1"
```

### Step 3 — Freeze when ready

When the schema stabilises:

1. Set freeze state via precedence:
  - `CONTRACT_SCHEMA_FROZEN=1` (preferred)
  - or `_contract_state.json` with `{"schema_frozen": true}`
  - or rely on CI fallback (`CI=true` + `sample.json` exists)
2. Any new untyped key now fails CI instead of warning
3. Intentionally untyped keys go in `KNOWN_EXCLUDED_KEYS`

---

## Script Reference

### `extract_schema.py`

Extracts a typed schema from any supported format. Produces Pydantic model code.

```bash
# Basic extraction
python scripts/extract_schema.py data.json

# With baseline save
python scripts/extract_schema.py data.json --save-baseline baseline.json

# Diff against baseline
python scripts/extract_schema.py data_v2.json --diff baseline.json

# Specify format explicitly
python scripts/extract_schema.py raw_export.txt --format text
```

**Supported formats**: JSON, Markdown, CSV/TSV, XLSX, YAML, plain text, DB tables.

### `drift_check.py`

Compares Pydantic model fields against a golden sample payload. Detects D1, D2, D3, D8 drift.

```bash
python scripts/drift_check.py \
    --payload tests/fixtures/payloads/nps/sample.json \
    --ingestion src.models.ingestion.nps:NpsPayload \
    --dto src.models.responses.nps:NpsResponse
```

Exit code: `0` = clean, `1` = drift found.

### `ts_dto_compare.py`

Compares TypeScript interface properties against Python DTO fields.

```bash
python scripts/ts_dto_compare.py \
    --dto src.models.responses.nps:NpsResponse \
    --ts-types frontend/src/types/nps.ts
```

### `generate_mapping_doc.py`

Generates a human-readable field mapping document from Pydantic models.

```bash
# Generate mode — write the mapping doc
python scripts/generate_mapping_doc.py \
    --ingestion src.models.ingestion.nps:NpsPayload \
    --dto src.models.responses.nps:NpsResponse \
    --ts-types frontend/src/types/nps.ts \
    --output docs/mapping/nps-mapping.md

# Check mode — validate existing doc is current (for CI)
python scripts/generate_mapping_doc.py \
    --ingestion src.models.ingestion.nps:NpsPayload \
    --dto src.models.responses.nps:NpsResponse \
    --check docs/mapping/nps-mapping.md
```

Exit code: `0` = current, `1` = stale (regenerate needed).

---

## CI Integration

Add these to your CI pipeline to catch drift automatically:

```yaml
# Drift check
- name: Check data contract drift
  run: |
    python scripts/drift_check.py \
      --payload tests/fixtures/payloads/nps_monthly/sample.json \
      --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
      --dto src.models.responses.nps_monthly:NpsMonthlyResponse

# Mapping doc freshness
- name: Check mapping doc is current
  run: |
    python scripts/generate_mapping_doc.py \
      --ingestion src.models.ingestion.nps_monthly:NpsMonthlyPayload \
      --dto src.models.responses.nps_monthly:NpsMonthlyResponse \
      --check docs/mapping/nps-monthly-mapping.md

# TypeScript alignment
- name: Check TS types match DTO
  run: |
    python scripts/ts_dto_compare.py \
      --dto src.models.responses.nps_monthly:NpsMonthlyResponse \
      --ts-types frontend/src/types/nps-monthly.ts
```

---

## Schema Evolution Lifecycle

| Stage | What to do | Schema frozen? |
|-------|-----------|----------------|
| **Early development** | Use `extra="allow"` on ingestion models. Drift tests warn but don't block. | No (`SCHEMA_FROZEN = False`) |
| **Schema stabilising** | Run `drift_check.py` regularly. Add typed fields for persistent keys. | No |
| **Schema frozen** | Set `CONTRACT_SCHEMA_FROZEN=1` (or `_contract_state.json`; CI fallback if missing). Any untyped key now fails CI. | Yes |
| **Intentional exclusion** | Add keys to `KNOWN_EXCLUDED_KEYS` in contract tests. | Either |

See [SKILL.md — Schema Evolution Lifecycle](./SKILL.md#schema-evolution-lifecycle) for the full three-layer defence documentation.

---

## Which Agents Can Use This Skill?

| Agent | Typical use |
|-------|-------------|
| `@Implement` / Default | Full end-to-end pipeline generation |
| `@Frontend Developer` | TypeScript types + service functions from a DTO |
| `@Data Engineer` | Adapter + ingestion model + normalizer |
| `@Tester` | Contract test generation and drift audit |
| `@Code Reviewer` | Audit existing pipeline for drift and contract violations |
| `@Anchor` | Evidence-first verification of each layer |
| `@Preflight` | Pre-implementation validation of data contracts in a plan |

---

## Decision Tree

```
Do you have raw data and need a full pipeline?
  └─ YES → Scenario 1 (Greenfield)
      └─ Agent: "Build a data contract pipeline from [file]"
      └─ Script: extract_schema.py → review → agent generates

Do you have an existing adapter returning raw dicts?
  └─ YES → Scenario 2 (Partial)
      └─ Agent: "Add a typed DTO pipeline to [adapter]"
      └─ Script: drift_check.py after generation

Did the upstream schema change?
  └─ YES → Scenario 3 (Update)
      └─ Script: drift_check.py or extract_schema.py --diff
      └─ Agent: "Fix these drift findings: [paste output]"
      └─ Script: drift_check.py + generate_mapping_doc.py to verify

Just want to audit alignment?
  └─ YES → Run scripts directly
      └─ drift_check.py, ts_dto_compare.py, generate_mapping_doc.py --check
```
