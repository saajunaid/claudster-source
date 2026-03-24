# Contract Reference

> Canonical registry of every agent's input/output contract.
> Orchestrator uses this to validate artefacts before routing.
> Agents use this to understand what upstream produces and what downstream expects.
>
> **See also:** [GLOSSARY.md](GLOSSARY.md) for canonical terminology.

---

## How to Use This Document

1. **Orchestrator** — Before routing to next agent, verify the upstream agent's `required_fields` are present and non-empty in the artefact at `artefact_path`.
2. **Producing agent** — Check your own Output Contract table below; ensure your artefact satisfies all `required_fields`.
3. **Consuming agent** — Check the upstream agent's contract to know what fields you can rely on.
4. **validate_agents.py** — Parses this document to verify contract consistency across handoff chains.

---

## Contract Table Format

Every agent's contract follows this schema:

| Column | Description |
|--------|-------------|
| `artefact_path` | Where the output file(s) live (glob or specific path) |
| `required_fields` | Fields that MUST be present and non-empty for Orchestrator to route forward |
| `approval_on_completion` | Initial approval status: `pending` (needs review), `approved` (auto-approved), or `N/A` (no gate) |
| `next_agent` | Default downstream agent(s) — Orchestrator may override based on pipeline state |

---

## Pipeline Core Agents

### PRD → Architect

| Field | Value |
|-------|-------|
| **Agent** | PRD |
| `artefact_path` | `agent-docs/prd/<feature-slug>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `functional_requirements`, `non_functional_requirements` |
| `approval_on_completion` | `pending` |
| `next_agent` | `architect` |

> **Orchestrator check:** Verify `approval: approved` in the artefact YAML header before routing to Architect.

---

### Architect → Planner

| Field | Value |
|-------|-------|
| **Agent** | Architect |
| `artefact_path` | `agent-docs/architecture/<feature-slug>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `component_breakdown`, `adr_list`, `nfr_compliance_matrix` |
| `approval_on_completion` | `pending` |
| `next_agent` | `plan` |

> **Orchestrator check:** Verify `approval: approved` in architecture doc before routing to Planner.

---

### Planner → Implement

| Field | Value |
|-------|-------|
| **Agent** | Planner |
| `artefact_path` | `.github/plans/<feature-slug>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `phases`, `agent_assignments`, `track_labels` |
| `approval_on_completion` | `pending` |
| `next_agent` | `implement` |

> **Orchestrator check:** Verify `approval: approved` in plan YAML header before routing to Implement.
>
> **Phase-level fields** (each phase in `phases[]`):
>
> | Phase Field | Required | Description |
> |-------------|----------|-------------|
> | `agent` | yes | Agent name to execute the phase |
> | `required_skills` | no | Skills the assigned agent MUST load |
> | `evidence_tier` | no | `standard` or `anchor` (default: `standard`) |
> | `intent_references` | no | `[artefact_path#section]` links back to PRD/ADR decisions |
> | `design_intent` | no | One-sentence rationale explaining WHY this phase exists |
> | `deliverables` | yes | What the phase produces |
> | `verification` | yes | How to verify phase completion |

---

### Implement → Tester

| Field | Value |
|-------|-------|
| **Agent** | Implement |
| `artefact_path` | `src/**` (code committed to repo) + optional `agent-docs/<feature>-impl-notes.md` |
| `required_fields` | `chain_id`, `status`, `approval` (in impl-notes if produced) |
| `approval_on_completion` | `pending` |
| `next_agent` | `tester`, `code-reviewer` |

> **Orchestrator check:** Verify `approval: approved` in impl-notes (if produced) before routing to next agent.

---

### Tester → Code Reviewer

| Field | Value |
|-------|-------|
| **Agent** | Tester |
| `artefact_path` | `tests/**` (test files) + `agent-docs/testing/coverage-<feature>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `pass_rate`, `uncovered_requirements` |
| `approval_on_completion` | `pending` |
| `next_agent` | `code-reviewer` (on `status: passed`) or back to implementing agent (on `status: failed`) |

> **Orchestrator check:** Read `tester_result.status`. If `passed` — verify `approval: approved` in coverage report then route to Code Reviewer. If `failed` — trigger retry loop.

---

### Code Reviewer → Done / Implement

| Field | Value |
|-------|-------|
| **Agent** | Code Reviewer |
| `artefact_path` | `agent-docs/reviews/review-<feature>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `verdict`, `issues` |
| `approval_on_completion` | `approved` or `revision-requested` |
| `next_agent` | `implement` (on `revision-requested`) or `done` (on `approved`) |

> **Orchestrator check:** Route to Implement if `approval: revision-requested`; mark pipeline stage complete if `approval: approved`.

---

## Quality Gate Agents

### Security Analyst

| Field | Value |
|-------|-------|
| **Agent** | Security Analyst |
| `artefact_path` | `agent-docs/security/threat-<feature>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `threat_level`, `findings`, `mitigations` |
| `approval_on_completion` | `pending` |
| `next_agent` | `architect` (design change required) or `implement` (code-level fix) |

> **Orchestrator check:** Verify `approval: approved` in threat report before routing to next agent.

---

### Accessibility

| Field | Value |
|-------|-------|
| **Agent** | Accessibility |
| `artefact_path` | `agent-docs/reviews/accessibility-<feature>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `wcag_level`, `findings`, `remediation_priority` |
| `approval_on_completion` | `approved` or `revision-requested` |
| `next_agent` | `implement` or `janitor` (on `revision-requested`) |

> **Orchestrator check:** Route to Implement or Janitor if `approval: revision-requested`.

---

### Debug

| Field | Value |
|-------|-------|
| **Agent** | Debug |
| `artefact_path` | `agent-docs/debug/debug-<feature>-<date>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `root_cause`, `fix_applied`, `verification_steps` |
| `approval_on_completion` | `pending` |
| `next_agent` | `implement` (for code fix) or `janitor` (for targeted patch) |

> **Orchestrator check:** Verify `approval: approved` in debug report before routing to next agent.

---

## High-Rigour Agent

### Anchor

| Field | Value |
|-------|-------|
| **Agent** | Anchor |
| `artefact_path` | `src/**` (code) + `agent-docs/anchor-evidence-<feature>.md` (Evidence Bundle) |
| `required_fields` | `chain_id`, `status`, `approval`, `task_size`, `baseline`, `verification`, `evidence_bundle` |
| `approval_on_completion` | `pending` |
| `next_agent` | `security-analyst` (if `security_sensitive: true`) or `tester` (default) |

> **Routing note:** Orchestrator reads `task_type` and `security_sensitive` fields from the Evidence Bundle to determine the correct route.

---

## Implementation Agents

### Frontend Developer

| Field | Value |
|-------|-------|
| **Agent** | Frontend Developer |
| `artefact_path` | `src/frontend/**` (code files committed to repo) |
| `required_fields` | `chain_id`, `status`, `approval` (in `agent-docs/` summary if produced) |
| `approval_on_completion` | `pending` |
| `next_agent` | `tester`, `code-reviewer` |

---

### Streamlit Developer

| Field | Value |
|-------|-------|
| **Agent** | Streamlit Developer |
| `artefact_path` | `src/**/*.py` (Streamlit app files committed to repo) |
| `required_fields` | `chain_id`, `status`, `approval` (in `agent-docs/` summary if produced) |
| `approval_on_completion` | `pending` |
| `next_agent` | `tester`, `code-reviewer` |

---

### Data Engineer

| Field | Value |
|-------|-------|
| **Agent** | Data Engineer |
| `artefact_path` | `src/ingestion_config/**` + `agent-docs/<feature>-data-notes.md` (if produced) |
| `required_fields` | `chain_id`, `status`, `approval` (in data-notes if produced) |
| `approval_on_completion` | `pending` |
| `next_agent` | `implement` or `tester` |

---

### SQL Expert

| Field | Value |
|-------|-------|
| **Agent** | SQL Expert |
| `artefact_path` | `src/**/*.sql` + `agent-docs/<feature>-query-notes.md` (if produced) |
| `required_fields` | `chain_id`, `status`, `approval` (in query-notes if produced) |
| `approval_on_completion` | `pending` |
| `next_agent` | `implement` or `data-engineer` |

---

### DevOps

| Field | Value |
|-------|-------|
| **Agent** | DevOps |
| `artefact_path` | `.github/workflows/**` + deployment config files |
| `required_fields` | `chain_id`, `status`, `approval` (in deployment notes if produced) |
| `approval_on_completion` | `pending` |
| `next_agent` | `done` (deployment complete) |

---

### Janitor

| Field | Value |
|-------|-------|
| **Agent** | Janitor |
| `artefact_path` | In-place code patches (no separate artefact required) |
| `required_fields` | N/A |
| `approval_on_completion` | N/A |
| `next_agent` | `code-reviewer` |

> **Orchestrator check:** Route to Code Reviewer after all targeted patches are applied.

---

## Design Agents

### UX Designer

| Field | Value |
|-------|-------|
| **Agent** | UX Designer |
| `artefact_path` | `agent-docs/ux/ux-<feature>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `user_flows`, `pain_points`, `success_criteria` |
| `approval_on_completion` | `pending` |
| `next_agent` | `ui-ux-designer` |

---

### UI/UX Designer

| Field | Value |
|-------|-------|
| **Agent** | UI/UX Designer |
| `artefact_path` | `agent-docs/ux/design-<feature>.md` |
| `required_fields` | `chain_id`, `status`, `approval`, `component_specs`, `interaction_flows`, `brand_tokens` |
| `approval_on_completion` | `pending` |
| `next_agent` | `frontend-developer` or `streamlit-developer` |

---

## Support Agents (No Pipeline Gate)

### Knowledge Transfer

| Field | Value |
|-------|-------|
| **Agent** | Knowledge Transfer |
| `artefact_path` | `docs/gold-nuggets-log.md` (primary) + `.github/instructions/*.instructions.md` (secondary) |
| `required_fields` | N/A (golden nuggets are additive) |
| `approval_on_completion` | N/A |
| `next_agent` | `orchestrator` (pipeline) or none (standalone) |

---

### Mentor

| Field | Value |
|-------|-------|
| **Agent** | Mentor |
| `artefact_path` | Ephemeral — no persistent artefact required |
| `required_fields` | N/A |
| `approval_on_completion` | N/A |
| `next_agent` | None — user decides next action |

> **Orchestrator note:** Mentor is a support agent, not part of the main pipeline.

---

### Project Manager

| Field | Value |
|-------|-------|
| **Agent** | Project Manager |
| `artefact_path` | `agent-docs/pm-update-<date>.md` (status update) |
| `required_fields` | `chain_id`, `status`, `blocked_by`, `next_actions` |
| `approval_on_completion` | `pending` |
| `next_agent` | `plan` (for new feature cycle) or `user` (for decision gate) |

> **Orchestrator check:** PM updates are informational. Route as directed by `next_actions` field.

---

### Prompt Engineer

| Field | Value |
|-------|-------|
| **Agent** | Prompt Engineer |
| `artefact_path` | `.github/prompts/<name>.prompt.md` |
| `required_fields` | N/A (prompt file is the artefact) |
| `approval_on_completion` | N/A |
| `next_agent` | None — pool resource update |

> **Orchestrator note:** Prompt Engineer produces pool resources, not pipeline artefacts. No routing required.

---

## Visual Artefact Agents (No Pipeline Gate)

### Mermaid Diagram Specialist

| Field | Value |
|-------|-------|
| **Agent** | Mermaid Diagram Specialist |
| `artefact_path` | `diagrams/<name>.mmd` or `agent-docs/architecture/<name>.mmd` |
| `required_fields` | N/A (diagram file is the artefact) |
| `approval_on_completion` | N/A |
| `next_agent` | `architect` or `plan` (for documentation reference) |

---

### SVG Diagram

| Field | Value |
|-------|-------|
| **Agent** | SVG Diagram |
| `artefact_path` | `diagrams/<name>.svg` |
| `required_fields` | N/A (SVG file is the artefact) |
| `approval_on_completion` | N/A |
| `next_agent` | None — visual asset only |

---

## Orchestrator (Router — No Output Artefact)

Orchestrator does not produce deliverable artefacts. It reads `pipeline-state.json`, validates upstream artefacts against the contracts above, and routes to the next agent.

**Orchestrator validation protocol:**

1. Read the upstream agent's contract from this document
2. Verify artefact file exists at `artefact_path`
3. Verify all `required_fields` are present and non-empty
4. Verify `approval` status meets the routing condition
5. If validation fails → set `blocked_by` in `pipeline-state.json` and halt

**Hotfix exception:** For `implement` and `tester` stages with `type: hotfix`, skip YAML header validation — instead confirm commit SHA is present.

---

## Revision Tracking

When an artefact is reworked (e.g., Implement reworks after Code Reviewer returns `revision-requested`):

1. **Producing agent** sets the old ARTIFACTS.md row to `superseded` with `superseded_by: <new artefact path>`
2. **Producing agent** adds a new row for the replacement artefact
3. **Producing agent** increments `_notes._revision_count[stage_name]` via `update_notes` MCP tool
4. **Orchestrator** reads `_revision_count` for retry budget enforcement and observability

This is revision awareness (not full version numbering) — the pipeline knows "this is the Nth attempt at stage X."

---

## Handoff Chain Summary

```
PRD ──→ Architect ──→ Planner ──→ Implement ──→ Tester ──→ Code Reviewer ──→ Done
                                    │                        │
                                    │            ┌───────────┘ (revision-requested)
                                    ▼            ▼
                                 Implement ◄─────┘
```

**Branching paths:**
- Anchor replaces Implement for `evidence_tier: anchor` phases
- Security Analyst gates before Tester when `security_sensitive: true`
- Debug enters mid-pipeline when bugs are discovered
- Knowledge Transfer runs post-completion to extract learnings
