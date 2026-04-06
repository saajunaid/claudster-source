# Diagrams Audit

**Audited:** 2026-02-20  
**Auditor:** GitHub Copilot (advisory session)  
**Reason:** 23rd agent (orchestrator) added, model tier assignments changed from Opus → Sonnet for PRD + Code Review agents, pipeline folder renamed.

---

## Status Summary

| File | Status | Action Required |
|------|--------|-----------------|
| `pipeline-entry-guide.svg` | ✅ Current | NEW — created this session |
| `agent-workflow-design-reference.md` | ✅ Valid | Keep as living reference — pipeline architecture intent still accurate |
| `debug-plan-amendment-workflow.svg` | ✅ Valid | Debug/hotfix workflow still correct — no model references |
| `skills-reference-card.md` | ⚠️ Minor stale | Add orchestrator agent row + pipeline skills (pipeline-state, context-curator) |
| `AGENT_WORKFLOW_CHEATSHEET.md` | ❌ Stale | Model tiers wrong; missing orchestrator; update before next polishing sprint |
| `agent-reference-card.md` | ❌ Stale | Model tiers wrong; missing orchestrator row; handoff table incomplete |
| `agent-pipeline-poster.svg` | ❌ Stale | Shows 22 agents with wrong tier groupings; regenerate after agent polishing |

---

## Detailed Findings

### ✅ `pipeline-entry-guide.svg` — NEW this session
- Created 2026-02-20.
- A3 landscape printable SVG — 6 entry scenarios, @Orchestrator node, full pipeline stage row, artefact prep table, one-liner reference card.
- No further action needed.

---

### ✅ `agent-workflow-design-reference.md` — Valid
- Documents original pipeline architecture intent, chain_id system, intent document structure, supervisor gate design.
- These design decisions are all still reflected in the live codebase.
- **Keep as-is.** Mark as a historical design reference at the top if you like.

---

### ✅ `debug-plan-amendment-workflow.svg` — Valid
- Shows the debug → diagnose → plan amendment → implement → verify loop.
- Does not reference model tiers or agent head-count.
- **No changes needed.**

---

### ⚠️ `skills-reference-card.md` — Minor Stale
**What's wrong:**
- Missing entry for `orchestrator.agent.md` (the 23rd agent, added this sprint).
- Missing two new pipeline skills: `workflow/pipeline-state` and `workflow/context-curator`.

**Fix (low priority — do in next polishing sprint):**
1. Add `orchestrator` to the agent list section.
2. Add pipeline skills to the skills table.

---

### ❌ `AGENT_WORKFLOW_CHEATSHEET.md` — Stale
**What's wrong:**
- `@prd` is listed under **Opus** tier — it runs on **Sonnet**.
- `@code-reviewer` is listed under **Opus** tier — it runs on **Sonnet**.
- Orchestrator agent is missing entirely (23rd agent).
- Total agent count shown as 22 — should be 23.

**Correct model tier assignments:**
| Tier | Agents |
|------|--------|
| Opus / highest | `@architect`, `@debug`, `@security-analyst` |
| Sonnet / standard | All others including `@prd`, `@code-reviewer`, `@orchestrator` |

**Fix:**
1. Move `@prd` and `@code-reviewer` from Opus section to Sonnet section.
2. Add `@orchestrator` to the Sonnet section or create a separate "supervisor" tier row.
3. Update total agent count to 23.

---

### ❌ `agent-reference-card.md` — Stale
**What's wrong:**
- Same model tier errors as the cheatsheet.
- `@orchestrator` row is entirely absent.
- Handoff table is incomplete — does not include orchestrator handoff patterns.

**Fix:**
1. Correct model column values for `@prd` and `@code-reviewer` → Sonnet.
2. Add `@orchestrator` row: input = pipeline-state.json + artefacts, output = routed handoff, model = Sonnet.
3. Add orchestrator handoff patterns to the handoff table.

---

### ❌ `agent-pipeline-poster.svg` — Stale (defer to polishing sprint)
**What's wrong:**
- Renders 22 agent cards — missing orchestrator card.
- Model tier section (top legend) shows `@prd` and `@code-reviewer` under Opus.
- Layout will need a new orchestrator card in the supervisor tier row.

**Fix (medium effort — defer):**
- After all agent polishing is done, regenerate the poster SVG with:
  - 23 agent cards
  - Correct model tier groupings
  - Orchestrator in its own "supervisor" row at the top

---

## Priority Order for Fixes

1. **Now (this session):** ✅ `pipeline-entry-guide.svg` created.
2. **Next polishing sprint (GAP items):**  
   a. `AGENT_WORKFLOW_CHEATSHEET.md` — fix model tiers, add orchestrator  
   b. `agent-reference-card.md` — fix model tiers, add orchestrator row  
   c. `skills-reference-card.md` — add orchestrator + 2 pipeline skills  
3. **After full agent polishing sprint:**  
   d. `agent-pipeline-poster.svg` — full regeneration (23 agents, correct tiers)

---

## Not Audited (out of scope)

- Files under `.github/agent-docs/` — living documents, updated per-feature, no fixed version.
- `.github/plans/` — feature-specific, expected to age out.
- `.github/pipeline/` — current session documents, always up to date.
