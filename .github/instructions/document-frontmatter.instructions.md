---
description: "Document provenance frontmatter for plans, docs, READMEs, reports, handoffs, and other descriptive Markdown artifacts"
applyTo: "**/*.md"
priority: 120
---

# Document Frontmatter Instructions

Apply this rule whenever you create or update a **descriptive Markdown deliverable**, including:
- planning documents
- PRDs, ADRs, design docs, architecture docs, and requirements docs
- README files, runbooks, guides, reports, analyses, and handoffs
- status trackers, implementation notes, migration notes, and other prose-first Markdown artefacts

## Required metadata fields

When creating a **new** document, add YAML frontmatter at the top and include:

```yaml
Original Author: <active author or agent name>
Creation Date: <YYYY-MM-DD>
Creating Model: <actual model used for this document>
```

When **updating** an existing document, preserve those original fields and add or update:

```yaml
Last Author: <active author or agent name>
Last Updated: <YYYY-MM-DD>
Last Model Used: <actual model used for this update>
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
- Use the actual model used in that session for model fields.
- Use `YYYY-MM-DD` format for dates.
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
Creation Date: 2026-05-20
Creating Model: Claude Sonnet 4.6
---
```

### Updated existing document

```yaml
---
title: Incident Runbook
Original Author: GitHub Copilot
Creation Date: 2026-05-18
Creating Model: GPT-5.4
Last Author: GitHub Copilot
Last Updated: 2026-05-20
Last Model Used: GPT-5.4
---
```
