---
agent: preflight
difficulty: easy
expected-verdict: FAIL
---

# Task: Plan with incorrect file path

## Input (give this plan excerpt to the subagent)

```
## Phase 1 — Add retry decorator

Edit `src/utils/retry.py` to add an exponential backoff decorator.
Call it from `src/services/data_store.py` line 47.
Import: `from src.utils.retry import with_retry`
```

## Repo state (tell the subagent to check these paths)

- `src/utils/` does not exist — the project uses `src/lib/` for utilities
- `src/services/data_store.py` exists at line 47 but has no import section nearby
- `src/lib/` contains `cache.py`, `db.py`, `logging.py` — no `retry.py`

## Expected findings

- **blocker / paths**: `src/utils/retry.py` — parent dir `src/utils/` does not exist; should be `src/lib/retry.py`
- **blocker / symbols**: `from src.utils.retry import with_retry` — wrong module path given the actual layout

## Pass criteria

The subagent must:
1. Return `verdict: FAIL`
2. Cite `src/utils/` as non-existent with the correct path `src/lib/`
3. List at least one blocker finding
