---
agent: tester
difficulty: medium
expected-verdict: changes-requested
---

# Task: FastAPI route missing edge-case coverage

## Input

```python
# src/routers/cases.py
@router.get("/cases/{case_id}")
async def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(Case).filter(Case.id == case_id).first()
    return case

# tests/test_cases.py
def test_get_case(client, db_case):
    resp = client.get(f"/cases/{db_case.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == db_case.id
```

## Expected findings (blocking)

- **Missing 404 test**: No test for `GET /cases/99999` (non-existent ID). The route returns
  `null` (FastAPI serialises `None` as `null`) rather than a 404 — this is likely a bug AND
  there's no test proving the intended behaviour either way. Blocking.

## Expected findings (should-fix)

- **Return type**: Route returns `Case | None` with no `response_model` declared, so the
  OpenAPI schema is wrong. Should-fix.

## Pass criteria

The subagent must:
1. Return `verdict: changes-requested`
2. Identify the missing 404 / None-return test as a blocking finding
3. Not invent test code — report only, no edits
