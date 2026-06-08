---
description: Record and review subagent dispatches — a files-first run log (no server, no telemetry)
argument-hint: [show N | clear]
---

# /agent-log — files-first agent observability

Lightweight visibility into what the subagents did this project, without a dashboard, daemon, or remote
telemetry. The log is a plain append-only JSONL file at `.claude/agent-runs.jsonl` — readable offline,
diffable in git, provider-neutral. This is the deliberate minimal analog of a "mission control" UI: the
value is *run tracking*, and that does not require a server.

> **Rejected on purpose:** no web dashboard, no WebSocket stream, no PostHog/remote telemetry. Those
> break offline use and provider-neutrality (and matter even less under local models with small context
> budgets). If a visual of the workflow is ever wanted, render the active plan's tracker table to Mermaid
> on demand (`mermaid-diagrams` skill) — the plan file is the human-facing DAG.

## Record (do this after each subagent returns)
When a subagent (tester / code-reviewer / preflight / security-analyst / debug / anchor / data-engineer /
sql-expert / knowledge-transfer) finishes, append ONE line to `.claude/agent-runs.jsonl`, parsing its
return block for the verdict:

```json
{"ts":"<ISO-8601>","agent":"<name>","verdict":"<passed|approved|FAIL|VERIFIED|...>","summary":"<one line>","phase":"<plan phase if any>"}
```

Mapping from each agent's return block:
- `tester` → `tester_result.status`  · `code-reviewer` → `review.verdict`  · `preflight` → `preflight.verdict`
- `security-analyst` → `security_review.posture`  · `debug` → `debug.status`  · `anchor` → `evidence_bundle.verdict`
- `sql-expert` → `sql_review.verdict`  · `data-engineer` → `data_engineering.task` (no verdict; note status)
- `knowledge-transfer` → count of `live_writes`

Create the file if absent. Never rewrite prior lines — append only.

## Review — `/agent-log` or `/agent-log show 20`
Read `.claude/agent-runs.jsonl`, render the last N (default 15) as a table:

```
agent run log (last N)
ts (local)         | agent           | verdict   | phase   | summary
-------------------+-----------------+-----------+---------+----------------------------------
2026-06-08 14:02   | preflight       | PASS      | 1       | plan claims verified
2026-06-08 14:11   | tester          | passed    | 1       | 5 passed
2026-06-08 14:13   | code-reviewer   | approved  | 1       | clean
```
Then one summary line: counts by verdict, and any `FAIL`/`changes-requested`/`REGRESSED` highlighted.

## `/agent-log clear`
Truncate `.claude/agent-runs.jsonl` (confirm first). The file is git-ignored by default — it's a local
run trace, not a shared artifact.
