---
type: analysis
status: current
feature: oss-model-lanes-and-public-readiness
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-20T00:00:00Z
Creating Model: claude-opus-4-8
---

# Public readiness — privacy sweep (Track B Phase B2)

Grep of the **exported** pool (`export_runtime_resources.py --profile <name>`), across every profile
that ships to the public marketplace mirror (`saajunaid/junai`) — `copilot`, `ptarmigan`, `liffey`,
`claude`, `claude-extras` — not the whole source tree. Marker classes checked: `vmie-`/hostnames
(existing denylist), real internal product codenames, an internal scaffolding-tool name, and personal
dev-machine paths.

## Method
1. `export_runtime_resources.py --profile copilot --profile ptarmigan --profile liffey --profile claude
   --profile claude-extras --report` (all clean, 0 errors — thanks to this session's earlier fail-closed
   exporter fix, a bad roster/missing source would now hard-fail this step instead of silently skipping).
2. Grep `dist/runtime-resources/<profile>/` for each marker class, independent of
   `validate_pool.py`'s own denylist (so a scanner gap doesn't hide a real leak from this audit).
3. For each hit: genericize (preferred, when the surrounding content is otherwise reusable) or exclude
   from the export roster (when the whole item is inherently internal-only, e.g. describes a tool with
   no public existence). Record the decision below.
4. Add every new marker class found to `validate_pool.py`'s `PRIVACY_SUBSTRINGS` so it fails closed on
   regression, with a regression test (`scripts/tests/test_validate_pool.py`).
5. Re-export + re-grep to confirm zero remaining hits, on **every** profile (not just `claude`).

## Findings & decisions

| # | File (source) | What leaked | Decision | Fix |
|---|---|---|---|---|
| 1 | `claude-harness/commands/ui-brief.md` | Real VMIE app codenames as skill-routing trigger examples: `appointment-assist, nps-lens, rev-sight, app-sight` | Genericize | Replaced with "your organization's internal app family" |
| 2 | `.github/skills/frontend/design-md/SKILL.md` | "the project is VMIE" | Genericize | → "your organization's internal app family" |
| 3 | `.github/skills/frontend/popular-web-designs/SKILL.md` | "VMIE apps" | Genericize | → "your organization's internal app family" |
| 4 | `.github/skills/workflow/setup-project-ai/SKILL.md` | "dogfood learning from appointment-assist" | Genericize | → "a live incident on an existing project" |
| 5 | `.github/skills/frontend/responsive-mobile-native/SKILL.md` | "nps-lens NPSIGHT dashboard" real-world example | Genericize | → generic "an analytics dashboard" example, same structural detail (9→4 tabs) kept |
| 6 | `.github/instructions/validation-discipline.instructions.md` | `-Pattern "nps-lens"` in a PowerShell example | Genericize | → `-Pattern "my-service"` |
| 7 | `.github/recipes/enterprise-dashboard.recipe.md` | `OBS_APP_ID` example values `nps-lens`, `appointment-assist` | Genericize | → `billing-service`, `customer-portal` |
| 8 | `claude-harness/hooks/tests/test_hook_paths.py` | "(the rev-sight bug)" in a test docstring | Genericize | → "(a real bug seen in the wild)" |
| 9 | `claude-harness/scripts/check_doc_coverage.py` | "Lifted from rev-sight (commit 153b835)" + 2 more "rev-sight reference" comments | Genericize | → "Ported from an internal project" / "the ported reference impl" (3 sites) |
| 10 | `.github/skills/workflow/data-contract-pipeline/SKILL.md` | `platform-infra/templates/data-feature/` scaffold path (a tool with no public existence) | Genericize | → "If your organization has a reference scaffold for this pattern..." |
| 11 | `.github/agent-docs/PROJECT-ONBOARDING-RUNBOOK.md` | An entire 304-line runbook for VMIE's internal `platform-infra` bootstrap tool (explicitly states "Audience: … VMIE platform" in its own first line); absolute `E:\Projects\` paths throughout | **Exclude from export** (genericizing would document a tool nobody outside VMIE can use) | Removed from `liffey`'s `agent-docs` `included_names` roster in `runtime-targets.json` |
| 12 | `.github/agent-docs/RECIPE-RUNBOOK.md` | Same `platform-infra`/`new-vmie-project.ps1` bootstrap references | **Exclude from export** | Removed from the same roster, same edit |

**Confirmed already private (checked, not touched):** `.github/agent-docs/GITIGNORE-POLLUTION-
INVESTIGATION.md` — grepped for every marker class; does not appear in ANY exported profile's roster
(not in `liffey`'s `included_names`, not copied by any other target). No action needed.

**Existing denylist (`vmie-`, `iegbcoppoc*`, `gitea.internal`, `VMIE_BOT_TOKEN`, etc., added 2026-07-16
after the prior Fable audit) re-verified clean** — zero hits across all 5 profiles.

## Scanner hardening (regression prevention)

`validate_pool.py`'s `PRIVACY_SUBSTRINGS` gained 6 new entries, covering the two marker classes found
here that the existing denylist didn't catch:
- Internal product codenames: `appointment-assist`, `nps-lens`, `rev-sight`, `app-sight`.
- Internal tool names: `platform-infra`, `new-vmie-project`.

A bare `vmie` mention is deliberately **not** denylisted — it's also a legitimate, intentional category
label for the private-skill opt-in mechanism (`setup-project-ai.md`'s "deploy vmie skills (optional,
personal)" step, which transparently documents that vmie-specific skills are excluded from the public
plugin). Blanket-banning it would either false-positive on that legitimate documentation or require a
path-allowlist exception broad enough to blind the scanner to a future unrelated leak in the same file —
targeting the specific identifying strings is more precise.

6 new regression tests in `scripts/tests/test_validate_pool.py` (RED-verified: temporarily reverting the
denylist addition reproduces the original failure before re-applying the fix).

## Exit gate

- `validate_pool.py --profile claude` / `--profile claude-extras` / `--profile ptarmigan` / `--profile
  liffey`: **all pass clean.** (`copilot` has no dedicated `validate_pool.py --profile` mode; covered by
  the manual grep sweep instead.)
- `liffey`'s one remaining `[FAIL]` (`devops/ci-cd-pipeline/` skill on disk but not in `_registry.md`) is
  a **pre-existing, unrelated** registry-drift issue (found and flagged during this session's earlier
  `junai-push`, predates this sweep) — not a privacy finding, out of scope for B2.
- A grep of all 5 exported profile bundles for every marker class checked here (existing denylist +
  the 6 new patterns + personal dev-machine paths `E:\Projects\`/`C:\Users\`) → **zero hits.**
- Full suite: `python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q` → **358 passed, 1
  skipped.**

---

# docket team-usability checklist (Track B Phase B3)

**Goal:** verify the wider team can actually use docket — enablement, not open-sourcing (docket is
explicitly out of scope for public release). Exit gate: a teammate could go from "given the URL" →
"using a board" using only the docs.

## Verified (code-level, not just doc claims)

- **NTLM auto-provisioning actually works with zero setup.** `src/docket/api.py:436`: a first-seen
  Windows-authenticated user auto-provisions as a read-only `stakeholder` — no admin has to
  pre-create an account. A teammate who is simply handed the URL is authenticated and usable on
  first visit.
- **The Help tab is universally accessible.** `web/src/components/Sidebar.tsx:453`: "Help & guide —
  available to every role; it's just docs." Confirmed no role gate blocks reading the onboarding
  content itself.
- **`docket.md`** (the in-app Help page, `web/src/help/docket.md`) already covers: install/quickstart,
  what docket is and how it relates to claudster, core concepts (event sourcing, projects vs boards,
  lanes), the full agent pipeline (lane commands, harness adapters, the Implement mini-pipeline,
  config surface), roles & auth, and the safety rules (never push `main`, branch isolation, untested
  implements never pass).

## Doc gaps found and fixed

Two gaps that could genuinely confuse a first-time teammate, both fixed in `docket.md`:
1. **NTLM was described but not spelled out as "nothing to do."** A reader unfamiliar with SSO could
   wonder whether they need to request an account or find a login page. Added: "there is no login page
   and nothing to request... just open the board URL," plus how to get a role upgrade (ask a lead).
2. **The "Turn on agents" quickstart step didn't flag that Settings is lead-only.** A contributor or
   stakeholder following the quickstart literally would hit a wall with no explanation. Added: "Settings
   is lead-only; a contributor or stakeholder should ask a lead to do this step."

Both verified: `cd web && npx vitest run src/help/help.test.ts` → 5 passed (the existing content-shape
test suite for the Help page markdown).

## Code gaps (filed as follow-ups, not fixed here — B3 is docs-only)

- **F20/F21 (already tracked, OPEN in `fable-remediation-status.md`):** NTLM trust rests on loopback;
  first-seen users auto-provision with no opt-in gate. This is the *same* mechanism that makes
  zero-setup onboarding possible (a feature for B3's goal) but is flagged elsewhere as a security
  concern (an unexpected caller on the loopback proxy could also auto-provision). Not re-litigated
  here — tracked where it already is.
- No in-app "request a role upgrade" flow exists — a stakeholder wanting contributor+ access must know
  to informally ask a lead (now documented, per the fix above) rather than there being a request button
  or notification. Not blocking (the doc fix covers it), but a nicer flow is a future enhancement.

## Exit gate

A teammate given only the board URL: opens it → NTLM authenticates them silently → auto-provisions as
stakeholder → lands on a board they can view and report bugs from → Help tab (unrestricted) explains
the rest, including exactly who to ask for more access. **Met**, via the two doc additions above; no
code changes were required (the auto-provisioning + universal-Help-access mechanisms already existed
and were verified, not assumed).
