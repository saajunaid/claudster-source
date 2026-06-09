# SVG Poster Brief — JUNAI Pipeline Flow

> **For:** `@svg-diagram.agent.md`
> **Format:** SVG poster, A3 landscape (420 × 297 mm / 1587 × 1122 px at 96 dpi)
> **Output path:** `diagrams/junai-pipeline-poster.svg`
> **Style:** Dark background (#0d1117), accent palette below, clean sans-serif type

---

## Purpose

A wall-poster–quality diagram that shows the complete JUNAI pipeline in a single
view.  It will be used onboarding new contributors and displayed in the project wiki.

---

## Content Specification

### Panel A — Pipeline Spine (centre column, ~55% width)

Vertical swimlane showing the 9 canonical stages connected by arrows.
Each stage box must contain:
- Stage number (#1–#9) in large muted text top-left
- Stage name (`intent`, `prd`, `architect`, `plan`, `implement`, `tester`, `review`, `deploy`, `closed`) in bold
- Agent name in small italic below (e.g. "Orchestrator", "PRD agent")
- Advance event label on the connecting arrow (e.g. `intent_complete`)

| Stage | Accent colour |
|-------|---------------|
| intent | #58a6ff |
| prd | #58a6ff |
| architect | #79c0ff |
| plan | #79c0ff |
| implement | #56d364 |
| tester | #56d364 |
| review | #d2a8ff |
| deploy | #ffa657 |
| closed | #2ea043 (filled) |

### Panel B — Hotfix Fast-Track (left sidebar, ~20% width)

Show the short path: `init (hotfix) → implement → tester → closed`.
Indicate conditional branch: "security nit? → review".
Use amber accent (#ffa657) for hotfix boxes.

### Panel C — Gate Legend (right sidebar, ~20% width)

A small legend showing two gate types with icons:
- 🔴 `tester_retry_limit` — raised after 3 failed retries; requires human diagnosis
- 🟠 `pre_deploy` — production gate; satisfied via `junai pipeline gate --name pre_deploy`

Below the gate legend, add a Mode panel:
- 🔵 `supervised` — Orchestrator shows button and waits
- 🟢 `assisted` — Orchestrator invokes immediately; gates require your approval
- ⚫ `autopilot` ⚠️ — Auto-routing + auto-gates (beta)
  Toggle: `junai pipeline mode --value supervised|assisted|autopilot`

### Panel D — Footer bar (full width, bottom 8%)

| Left | Centre | Right |
|------|--------|-------|
| JUNAI — Junaid's Unified Neural AI | Version 1.0 · 2026-02-21 | `junai pipeline status` to check current state |

---

## Style Guide

| Token | Value |
|-------|-------|
| Background | `#0d1117` |
| Surface | `#161b22` |
| Border | `#30363d` |
| Text primary | `#e6edf3` |
| Text muted | `#8b949e` |
| Font | Inter, or system sans-serif fallback |
| Corner radius | 8px on stage boxes, 4px on labels |
| Arrow style | 2px solid, colour matches source stage accent |
| Gate icon | Red/orange hexagon shape |

---

## Do Not Include

- Code listings or long prose
- Any reference to `juno-ai` (the old brand name)
- Non-pipeline agent commands (`junai agent *` belongs in the cheatsheet, not this poster)

---

## Deliverables

1. `diagrams/junai-pipeline-poster.svg` — vector file, all text as `<text>` elements (not paths)
2. Brief comment block at top of SVG: `<!-- JUNAI Pipeline Poster v1.0 2026-02-21 -->`

---

*This brief was generated as part of Phase D (GAP-I2/I3/I4/I5/I6 implementation run).*
