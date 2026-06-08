---
description: Design-first UI brief — lock the aesthetic before writing any code
argument-hint: <what you're building, e.g. "dashboard for NPS scores" or "login page">
---

# /ui-brief — design first, code second

You are about to build a React frontend. **Do not write any code yet.**

Your job right now is to propose the visual direction and get approval before touching a file.

## What you're building

**$ARGUMENTS**

## Step 1 — Load the right skill

If this is a VMIE app (appointment-assist, nps-lens, rev-sight, app-sight): load `warm-editorial-ui`.
If this is a standalone or public-facing product: load `frontend-design`.
If this is a data dashboard: load `enterprise-dashboard-aesthetic-system`.

## Step 2 — Propose the brief (3 things only)

Present exactly this, in plain language, no code:

```
FONT PAIRING
  Heading: <specific font name and weight — not Inter, not Roboto>
  Body:    <specific font name>
  Why:     <one sentence on the mood it creates>

COLOUR STORY
  Background: <hex>  Surface: <hex>  Primary: <hex>  Accent: <hex>
  Why:        <one sentence — warm/cold/bold/editorial?>

ONE ANIMATION MOMENT
  What moves:  <the one element that gets the hero animation>
  How:         <spring entrance / stagger reveal / scroll trigger / etc.>
  Why:         <what it communicates — speed, weight, personality>

LAYOUT APPROACH
  <2 sentences: grid structure, whitespace philosophy, any asymmetry or grid-breaking>
```

## Step 3 — Wait

Do not proceed until the user responds with one of:
- **"go"** — build exactly as proposed
- feedback / changes — revise the brief and re-present, then wait again
- **"skip"** — proceed with your best judgement immediately

## Step 4 — Build

Once approved: implement using the loaded skill as your design system.
Use Framer Motion for the approved animation moment.
Every component must reflect the agreed colour story and font pairing — no fallback to defaults.
