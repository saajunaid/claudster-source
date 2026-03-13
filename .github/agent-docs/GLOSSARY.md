# Pipeline Glossary

Canonical terms used across all agents, skills, and pipeline infrastructure.
When writing agent instructions, skills, or documentation, use ONLY these terms.

---

## Core Terms

| Canonical Term | Definition | DO NOT USE |
|---------------|------------|------------|
| artefact | Any file produced by an agent as pipeline output. This is the correct spelling in all contexts — field names, prose, section headers. | artifact, deliverable, output file |
| stage | A pipeline-level progression step (intent, prd, architect, plan, implement, tester, review, closed) | phase (for pipeline steps), step |
| phase | A subdivision of work within a Plan (Phase 1, Phase 2…). Phases exist WITHIN the implement stage. | stage (for plan subdivisions), step |
| chain_id | Feature tracking ID format: `FEAT-YYYY-MMDD-slug`. Links all artefacts for a feature. | feature_id, tracking_id |
| handoff | Transfer of work from one agent to another via Orchestrator | routing (for the transfer act), delegation, dispatch, hand-off |
| handoff payload | The `_notes.handoff_payload` object written by Orchestrator via `update_notes` MCP tool before routing to a specialist | routing context, task context |
| evidence bundle | Anchor's structured proof-of-work document (`agent-docs/anchor-evidence-*.md`) | proof, verification report |
| gate | A supervision checkpoint requiring approval before pipeline advances (`supervision_gates.*`) | checkpoint, approval point |
| HARD STOP | Absolute refusal to proceed — security violation, out-of-scope request, or rogue state edit | halt, block, refuse |
| skill | A reusable knowledge pack in `.github/skills/{category}/{name}/SKILL.md` | SKILL (when referring to the concept, not the filename) |
| prompt | A reusable prompt file in `.github/prompts/*.prompt.md` | skill (when referring to prompt files — prompts are not skills) |
| onboarding prompt | The project bootstrap prompt at `.github/prompts/onboarding.prompt.md` | onboarding skill |

## Pipeline Modes

| Term | Definition |
|------|------------|
| supervised | All gates require manual user approval. Default mode. |
| assisted | Manual gates with AI guidance hints. Auto-routing between stages. |
| autopilot | All gates auto-satisfied except `intent_approved`. Fully hands-free after intent approval. |

## Result Statuses

### MCP `notify_orchestrator` — `result_status` parameter

| Value | Meaning | Used By |
|-------|---------|---------|
| `complete` | Standard stage completion | All agents |
| `phase_complete` | Multi-phase loop — implement stays in implement for next phase | Implement agent |
| `recovered` | Recovery after guard failure | Orchestrator (debug flow) |

### Agent-Specific Result Fields

| Agent | Field | Possible Values | Meaning |
|-------|-------|-----------------|---------|
| Tester | `tester_result.status` | `passed`, `failed` | All tests pass / any test fails |
| Code Reviewer | `Verdict` | `approved`, `revision-requested` | Code meets standards / needs changes |
| All agents (artefact YAML header) | `approval` | `approved`, `pending`, `revision-requested` | Artefact acceptance status |

### Orchestrator Artefact Validation Guards

| Guard | Checks |
|-------|--------|
| `artefact_exists` | File at `artefact_path` exists on disk |
| `artefact_approved` | YAML header `approval:` field is `approved` |
| `all_phases_done` | All implementation phases complete |

## File Naming Conventions

| Pattern | Example | Usage |
|---------|---------|-------|
| Agent file | `frontend-developer.agent.md` | Lowercase kebab-case matching `name` frontmatter field |
| Skill file | `.github/skills/{category}/{name}/SKILL.md` | Category folder + name folder + SKILL.md |
| Plan file | `.github/plans/{feature-slug}.md` | Feature slug from chain_id |
| Evidence file | `agent-docs/anchor-evidence-{feature}.md` | Per-feature evidence bundle |
| Artefact registry | `agent-docs/ARTIFACTS.md` | Single registry for all pipeline artefacts |
| Pipeline state | `.github/pipeline-state.json` | Live pipeline state — written ONLY by MCP tools |

## Pipeline State Field Ownership

All writes to `pipeline-state.json` go through MCP tools. Only `stages[*].status`, `stages[*].artefact`, `stages[*].completed_at`, and `blocked_by` may be set via `editFiles`.

| Field | Writer | Tool |
|-------|--------|------|
| `current_stage` | Pipeline runner | `notify_orchestrator` |
| `supervision_gates[*]` | Orchestrator | `satisfy_gate` |
| `pipeline_mode` | Orchestrator | `set_pipeline_mode` |
| `_notes.*` | Orchestrator / agents | `update_notes` |
| `project`, `feature`, `type` | Orchestrator | `pipeline_init` / `pipeline_reset` |

## Common Conflations to Avoid

| Wrong | Correct | Why |
|-------|---------|-----|
| "Phase 3 of the pipeline" | "The implement stage" | Phases are within a Plan; stages are pipeline-level |
| "The artifact registry" | "The artefact registry" | British spelling is canonical (matches all field names) |
| "Run the onboarding skill" | "Run the onboarding prompt" | `.prompt.md` files are prompts, not skills |
| "Route to the agent" | "Hand off to the agent" | Routing is Orchestrator's internal logic; handoff is the transfer act |
| `[Stage/Phase N]` | `[Phase N]` (within Plan) or `[Stage: implement]` (pipeline-level) | Don't conflate the two with a slash |
