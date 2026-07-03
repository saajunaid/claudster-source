# Reconciliation brief — claudster × docket feasibility analysis

**Purpose:** two parallel Fable 5 analysis passes write their outputs here. Once both exist, a fresh
Claude session reads this brief + both files and produces one merged decision document.

## Expected files (both passes write here)
- `pass1-foundations.md` — Pass 1: claudster-internal (portability A, knowledge model B, Kun's tools C,
  self-audit + internal plugin-vs-harness E, onboarding G). Contains its own Part 1 (decisions) + Part 2
  (build-ready PRD).
- `pass2-integration.md` — Pass 2: claudster↔docket integration + ClaudsterOS (D, F), the integration
  MECHANISM decision (file contract / event bridge / **MCP** / merged runtime), the PACKAGING decision
  (ship together vs separately), and the interface contracts. Deep-inspects BOTH codebases (its Phase 0).
  Contains Part 1 (decisions) + Part 2 (build-ready PRD).

## What the reconciler must do
1. **Verify against ground truth** — re-inspect the actual code where the two passes disagree; don't
   take either pass's word. Repos: `E:\Projects\claudster-source` and `E:\Projects\docket`.
2. **The one real consistency seam — plugin vs harness.** Does Pass 1's claudster-internal verdict agree
   with Pass 2's integration-angle take? Prior: Pass 2's MCP option likely *dissolves* the tension
   (claudster stays plugin-shaped but becomes triggerable via its existing `junai-mcp` server). Confirm
   or challenge against what they actually wrote.
3. **Internal consistency of Pass 2's rulings** — mechanism + packaging + event-log stance must not be a
   mix (e.g. "separate packages + MCP coupling" vs "one package + shared runtime", not a blend). The two
   event logs (docket `.docket/events.jsonl` vs claudster `pipeline-runner` transition registry) must be
   ruled bridge-or-collapse consistently with the packaging call.
4. **Cross-pass config fit** — Pass 1's unified onboarding/config model must leave room for Pass 2's
   lane↔stage keys. Flag any collision between `.claudster/config.toml` and docket's `config.json`.
5. **PRD quality gate** — if either Part-2 PRD is too thin for a Sonnet/Opus agent to implement (most
   likely risk: docket's first end-to-end slice, candidate OLI→PRD), say which section to deepen before
   building.

## Reconciler output
- One merged decision document + one unified, dependency-ordered roadmap (deduped across passes).
- The plugin/harness + packaging + mechanism verdicts stated once, consistently.
- All remaining open questions surfaced for the user (lead with "Pi" harness identity).
- If the two passes diverge badly on plugin/harness or packaging: frame it as an explicit user decision
  with a recommendation — do NOT average them.

## Settled anchors (do not reopen)
- Directory ownership: claudster owns/writes `.claudster/`; docket owns/writes `.docket/` and
  reads/watches `.claudster/`.
- claudster stages ≈ OLID lanes: OLI≈intake, PRD≈prd, IPD≈plan, IID≈implement, IVD≈test+review, ISD≈ship.
- Both repos already ship MCP servers → MCP is an already-present integration seam.
- Over-engineering guard: OLID agentic pipeline is OPT-IN over docket's generic kanban; prove
  single-agent (Claude Code) end-to-end first; ISD→prod-deploy is hard-gated behind human confirmation.
