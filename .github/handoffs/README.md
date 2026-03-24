# Emergency Context Handoffs

This directory contains **emergency handoff documents** created when work is unexpectedly interrupted.

## When This Is Used

- ⚠️ Context window nearly exhausted mid-task
- 🔄 Handing work to another person
- 🚨 Unexpected interruption requiring session end
- 📍 Checkpoint before risky operation

## This Is NOT For

- ❌ Planned multi-session work → Use `.github/plans/` instead
- ❌ Regular session endings → Just end naturally
- ❌ Completed work → No handoff needed

## Plan Amendment Briefs

This directory also hosts **plan amendment briefs** written by the Debug agent when a bug reveals incorrect or missing information in an implementation plan.

**Naming:** `plan-amendment-YYYY-MM-DD-<topic>.md`

**Lifecycle:**
```
🐛 Created    → Debug agent finds plan issue, writes brief
📋 Active     → Waiting for Planner agent to apply
✅ Applied    → Renamed to *-APPLIED.md after Planner agent processes it
🗑️ Archived  → Delete after 7 days
```

**Not emergencies** — these are structured inter-agent communication, not context recovery.

## Creating Handoffs

User invokes: `/context-handoff`

This creates: `.github/handoffs/YYYY-MM-DD_{task-name}.md`

## File Naming

Format: `YYYY-MM-DD_{brief-task-name}.md`

Examples:
- `2026-02-05_interaction-linking.md`
- `2026-02-05_analytics-refactor.md`

## Lifecycle

```
🚨 Created    → Emergency handoff invoked
📋 Active     → Contains continuation context
✅ Resumed    → Work continued in new session
🗑️ Archived  → Move to .github/handoffs/archive/ after 7 days
```

## Cleanup

Handoff documents are temporary. After resuming work:
1. The continuation session uses the handoff context
2. After 7 days, archive or delete old handoffs
3. Keep only if the work is still pending

## Why Here (Not docs/)

Emergency handoffs are AI workflow artifacts, not project documentation.
Keeping them in `.github/handoffs/` separates them from user-facing docs.
