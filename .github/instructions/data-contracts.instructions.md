---
description: "Data contract conventions — DTO aliasing, contract test structure, display DTO rules, payload fixtures, and frontend type alignment for any project with a source→backend→frontend data pipeline"
applyTo: "**/models/**/*.py, **/responses/**/*.py, **/types/*.ts, **/types/**/*.ts"
---

# Data Contract Conventions

Rules for building and maintaining typed data pipelines from source payload to frontend display.

---

## Layer Architecture

Every data pipeline has up to 6 layers. Not all are required for every project.

```
Source → Adapter → Ingestion Model → Normalizer → Display DTO → API Router → Frontend Types/Services
```

| Layer | Location | Responsibility |
|-------|----------|---------------|
| Source Adapter | `src/services/adapters/` or `src/services/` | Fetches raw data from external source (API, file, DB) |
| Ingestion Model | `src/models/ingestion/` | 1:1 Pydantic model matching raw source payload shape |
| Normalizer | `src/services/normalizers/` | Transforms ingestion model → display DTO (business logic lives here) |
| Display DTO | `src/models/responses/` | Frozen Pydantic model defining the API boundary contract |
| API Router | `src/api/routers/` | FastAPI endpoint returning typed `response_model` |
| Frontend Types | `frontend/src/types/` | TypeScript interfaces mirroring display DTO |
| Frontend Service | `frontend/src/services/` | Typed axios/fetch functions consuming API endpoints |

---

## Display DTO Rules

### Field Aliasing

When JSON source uses camelCase but Python uses snake_case, use `Field(alias=...)`:

```python
from pydantic import BaseModel, Field

class CustomerScore(BaseModel):
    customer_id: str = Field(alias="customerId")
    net_promoter_score: float = Field(alias="netPromoterScore")

    model_config = ConfigDict(populate_by_name=True)
```

### No Silent Data Dropping

```python
# ❌ CRITICAL: Silently drops unknown fields — data loss bug
class SurveyData(BaseModel):
    model_config = ConfigDict(extra="ignore")

# ✅ GOOD: Explicit about every field; unknown fields cause validation error
class SurveyData(BaseModel):
    model_config = ConfigDict(extra="forbid")

# ✅ ALSO GOOD: Allow extras during migration, but log them
class SurveyData(BaseModel):
    model_config = ConfigDict(extra="allow")
```

**Rule:** Display DTOs at the API boundary must never use `extra="ignore"`. Use `extra="forbid"` (strict) or `extra="allow"` (migration period) with logging.

### Optional Fields with Defaults

New fields are additive. Always provide defaults so older payloads still validate:

```python
class TrendData(BaseModel):
    nps_deltas: dict[str, float] = Field(default_factory=dict, alias="npsDeltas")
    theme_movement: list[dict] = Field(default_factory=list, alias="themeMovement")
```

### Frozen Display DTOs

Display DTOs should be immutable after construction:

```python
class ProductMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    product_name: str = Field(alias="productName")
    nps: float
    responses: int
```

---

## Golden Sample Payloads

Every data source must have at least one curated sample payload:

- **Location:** `tests/fixtures/payloads/{source_name}/`
- **Naming:** `{source_name}_sample.json` (or `.csv`, `.xml`)
- **Purpose:** Contract tests validate DTO against this file
- **Maintenance:** Update when source schema changes, never delete old samples (rename to `{source_name}_sample_v1.json`)

```
tests/fixtures/payloads/
├── nps_monthly/
│   ├── nps_monthly_sample.json      ← current golden sample
│   └── nps_monthly_sample_v1.json   ← previous version (for migration tests)
├── customer_events/
│   └── customer_events_sample.json
```

---

## Contract Tests

Contract tests validate alignment between layers. Location: `tests/unit/test_contract_*.py`

### What to Test

| Test | Validates |
|------|-----------|
| Payload → Ingestion Model | Raw JSON keys match ingestion model fields |
| Ingestion Model → Display DTO | Normalizer produces valid display DTO from ingestion model |
| Display DTO → API Response | Router returns the expected response shape |
| Display DTO → Frontend Types | Python DTO fields match TypeScript interface properties |

### Test Pattern

```python
import json
from pathlib import Path

PAYLOAD_DIR = Path(__file__).parent.parent / "fixtures" / "payloads"

def test_payload_validates_against_dto():
    """Golden sample payload must parse into the display DTO without error."""
    sample = json.loads((PAYLOAD_DIR / "source" / "sample.json").read_text())
    dto = DisplayDTO.model_validate(sample)
    assert dto is not None

def test_dto_covers_all_payload_keys():
    """Every key in the golden sample must map to a DTO field (no silent drops)."""
    sample = json.loads((PAYLOAD_DIR / "source" / "sample.json").read_text())
    dto_fields = {
        field_info.alias or name
        for name, field_info in DisplayDTO.model_fields.items()
    }
    payload_keys = set(sample.keys())
    uncovered = payload_keys - dto_fields
    assert not uncovered, f"Payload keys not in DTO: {uncovered}"
```

---

## Frontend Type Alignment

TypeScript types must mirror the display DTO:

```typescript
// ✅ GOOD: Mirrors Python DTO field-for-field
export interface CustomerScore {
  customerId: string;        // ← matches Field(alias="customerId")
  netPromoterScore: number;  // ← matches Field(alias="netPromoterScore")
}

// ❌ BAD: Extra fields not in DTO, or missing DTO fields
export interface CustomerScore {
  customerId: string;
  nps: number;              // ← name doesn't match DTO alias
  extraField: string;       // ← not in DTO at all
}
```

**Rule:** When adding a field to the display DTO, add the corresponding field to the TypeScript interface in the same PR.

---

## Mapping Documentation

Data mapping docs (e.g., `ui-json-data-mapping.md`) are reference artifacts, not runtime code. They should be generated or validated by scripts, not hand-maintained.

**Rule:** If a mapping doc exists, run a drift check against the actual payload + DTO before trusting it. Treat mapping docs as "last known good" — the contract tests are the source of truth.

---

## Drift Detection (Local)

Run drift checks locally before committing:

```bash
# Check DTO fields against golden sample payload
pytest tests/unit/test_contract_drift.py -v

# Or use the skill script directly
python scripts/drift_check.py --payload tests/fixtures/payloads/source/sample.json --dto src/models/responses/source_dto.py
```

When CI is available, add contract tests to the test pipeline. Until then, run locally before every PR.
