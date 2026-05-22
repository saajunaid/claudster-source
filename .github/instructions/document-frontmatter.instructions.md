---
description: "Document provenance frontmatter for plans, docs, READMEs, reports, handoffs, and other descriptive Markdown artifacts"
applyTo: "**/*.md"
priority: 120
---

# Document Frontmatter Instructions

Apply this rule whenever you create or update a **descriptive Markdown deliverable**. The YAML frontmatter block must be the first content in the file, before the title, blockquotes, comments, or generated status headers.

This applies to outputs produced by planning, intent, preflight, relay, ADR, README, handoff, documentation, and report workflows, including outputs from `writing-plans`, `golden-plan`, `intent-writer`, `preflight`, `relay`, `plan.prompt.md`, `adr.prompt.md`, and `create-readme.prompt.md`.

Include frontmatter for:
- planning documents
- PRDs, ADRs, design docs, architecture docs, and requirements docs
- README files, runbooks, guides, reports, analyses, and handoffs
- status trackers, implementation notes, migration notes, and other prose-first Markdown artefacts

## Required metadata fields

When creating a **new** document, add YAML frontmatter at the top and include:

```yaml
Original Author: <active author or agent name>
Creation Date: <YYYY-MM-DDTHH:MM:SSZ>
Creating Model: <exact runtime model identifier or display name>
```

When **updating** an existing document, preserve those original fields and add or update:

```yaml
Last Author: <active author or agent name>
Last Updated: <YYYY-MM-DDTHH:MM:SSZ>
Last Model Used: <exact runtime model identifier or display name>
```

> For newly created documents, `Last Author`, `Last Updated`, and `Last Model Used` are optional and should be omitted until the first update.

## Merge rules

- Merge these fields into the existing YAML frontmatter block. Do **not** replace document-specific keys such as `description`, `type`, `status`, `chain_id`, `approval`, `tags`, `model`, `tools`, or `applyTo`.
- If the document has no YAML frontmatter, add one.
- Do **not** change `Original Author`, `Creation Date`, or `Creating Model` unless they are missing and you are backfilling a legacy document.
- If a legacy document has no recoverable original metadata, backfill with:
  - `Original Author: Unknown (legacy document)`
  - `Creation Date: Unknown`
  - `Creating Model: Unknown`
  Then add the current `Last Author`, `Last Updated`, and `Last Model Used` fields.
- Use the active author identity for author fields, for example `GitHub Copilot`, `Planner`, `Architect`, `PRD`, or the human author if explicitly provided.
- Use the exact model identifier or display name exposed by the active runtime for model fields, for example `gpt-5.4`, `gpt-5.3-codex`, or `GPT-5.5`.
- Do not record only a generic model family such as `GPT-5`, `GPT-4`, `Claude`, or `Gemini` when a more specific runtime model identifier or display name is available.
- If the runtime does not expose an exact model identifier, record the most precise deterministic runtime identity available and say that the exact ID was unavailable, for example `Codex (GPT-5-based; exact runtime model ID unavailable)`. Do not silently fall back to the family label alone.
- Use full ISO 8601 UTC timestamps for metadata values, in `YYYY-MM-DDTHH:MM:SSZ` format. Do not use local timezone offsets in these fields.
- Despite the field name `Creation Date`, the value must be a full timestamp for auditability and provenance.
- For non-Markdown descriptive deliverables that support a native metadata/header block, mirror the same fields in that format.

## Examples

### New planning document

```yaml
---
chain_id: FEAT-2026-0520-doc-metadata
type: plan
status: current
approval: pending
Original Author: Planner
Creation Date: 2026-05-20T18:42:11Z
Creating Model: Claude Sonnet 4.6
---
```

### Updated existing document

```yaml
---
title: Incident Runbook
Original Author: GitHub Copilot
Creation Date: 2026-05-18T09:14:32Z
Creating Model: GPT-5.4
Last Author: GitHub Copilot
Last Updated: 2026-05-20T19:03:27Z
Last Model Used: GPT-5.4
---
```
