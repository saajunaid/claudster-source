---
type: state-template
description: "Living state document for active implementation plans. Overwrite Section 1 (Current Status) each session; append-only in Section 2 (Session Log)."
---

# CURRENT_STATE

> **How to use:**
> - **Section 1 (Current Status):** Replace this section wholesale at the start and end of every agent session.
> - **Section 2 (Session Log):** Append one entry per session. Never edit past entries.
> - See `.github/skills/workflow/state-tracking/SKILL.md` for the full protocol.

---

## Current Status

**Plan:** *(path to the active plan file)*
**Tracker:** *(path to the active tracker file)*
**Last updated:** *(YYYY-MM-DDTHH:MM:SSZ)*
**Active agent:** *(@Agent — model: Model)*
**Current phase:** *(Phase N — Name)*
**Phase status:** *(Not started | In progress | Blocked | Complete)*

### What is done

*(List each completed phase with commit hash)*

- Phase 0 (Context & Decisions): complete — plan authored
- Phase 1 ([Name]): complete — commit `xxxxxxx`

### What is in progress

*(Describe current step within current phase, or "nothing — starting fresh")*

### What is blocked

*(Describe any blocker, or "nothing")*

### Next action

*(One sentence: exactly what the next agent session should start with)*

---

## Session Log

*(Append one entry per session below. Never edit past entries.)*

### [YYYY-MM-DDTHH:MM:SSZ] — @Agent (model: Model)

**Phase covered:** Phase N *(partial | complete)*
**Commits:** `xxxxxxx` *(phase(N): Name complete)*
**Stopped at:** *(exact description of stopping point)*
**Handoff note:** *(any context the next agent needs)*

---
