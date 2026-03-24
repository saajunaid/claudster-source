# Agent Artifacts

> **For agents**: Only read artifacts with status `current`. Ignore `superseded` and `archived`.
> **For humans**: This is a working directory for inter-agent communication. Do NOT include these in project documentation without human review.

---

## How to Read This Manifest

- **chain_id**: Links all artifacts in a feature chain (format: `FEAT-YYYY-MMDD-{slug}`)
- **status**: `current` (active) | `superseded` (replaced) | `archived` (historical) | `completed` (done)
- **approval**: `pending` (awaiting review) | `approved` (proceed) | `revision-requested` (needs changes)

### Rules for Agents

1. **Before reading any artifact**, check this manifest first
2. **Only read `current` artifacts** — `superseded` and `archived` are stale
3. **When creating a new artifact**: add a row to the table below, set status to `current`, approval to `pending`
4. **When replacing an artifact**: update the old row to `superseded`, add `superseded_by` path, then add new row
5. **Carry `chain_id`** through all artifacts in the same feature chain
6. **Documentation skills**: Do NOT scan `agent-docs/` for project documentation. This is agent working space only.

### Rules for Janitor Agent

- Scan this manifest periodically
- Move `superseded` or `archived` artifacts older than 30 days to `agent-docs/.archive/` (preserve subfolder structure)
- Update the manifest after moving files
- Clean up resolved escalations

---

## Folder Structure

```
agent-docs/
├── ARTIFACTS.md        ← this file
├── .archive/           ← stale artifacts (managed by janitor)
├── intents/            ← Intent Documents + amendments
├── escalations/        ← agent-to-agent escalations
├── prd/                ← PRD agent output
├── architecture/       ← Architect agent output
├── ux/
│   ├── mockups/        ← UI mockups (HTML/SVG)
│   └── reviews/        ← UI review findings
├── security/           ← Security audit reports
├── reviews/            ← Code review findings
├── debug/              ← Debug investigation reports
└── testing/            ← Test coverage analysis
```

---

## Artifacts

> **Note:** Plans live in `.github/plans/` and finalized project docs live in `docs/`. These are registered here for traceability — `agent-docs/` sub-folders are for in-transit drafts only.

| Date | Agent | Type | Description | Path | Status | Approval | Chain ID |
|------|-------|------|-------------|------|--------|----------|----------|
| 2026-02-19 | Planner | plan | Track B — Insight/FCard/Identity redesign (5 phases) | `.github/plans/2026-02-19-insight-cards-fcard-identity-redesign.md` | completed | approved | FEAT-2026-0219-track-b-redesign |
| 2026-02-19 | Debug | fix-up | Post-Track B cross-component polish (7 issues A–G) | `.github/plans/PostTrackB-Cross-Component-Fix-Up.md` | completed | approved | FEAT-2026-0219-track-b-redesign |
| 2026-02-19 | Architect | ADR | Chat widget architecture — Option B (micro-frontend hybrid) | `docs/architecture/agentic-adr/ADR-chat-widget-architecture.md` | current | approved | FEAT-2026-0219-track-a-chat-widget |
| 2026-02-19 | Planner | plan | Track A — Chat widget micro-frontend migration (5 phases) | `.github/plans/track-a-chat-widget-microfrontend.md` | current | approved | FEAT-2026-0219-track-a-chat-widget |
