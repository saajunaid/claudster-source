---
type: plan
status: draft (DECISION GATE open — name choice + scope; do NOT start before antigravity-plugin-parity completes)
feature: brand-rename
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-23T00:00:00Z
Creating Model: claude-fable-5
---

# Brand rename (claudster → ?) — scoped feasibility + plan

## Verdict from the 2026-07-23 blast-radius scan (sonnet subagent, 6 locations, ~2500 refs)
- **Full rename (brand + `/claudster:` prefix + `.claudster/` dir): Medium-leaning-LARGE. NOT recommended.**
  The killer is NOT the ~2500 text occurrences — it's that `.claudster/` is **externally-persisted
  state**: committed artifact dirs in every bootstrapped repo (app-forge + the sight-family repos),
  docket board state storing `.claudster/...` paths, docket's `api.py` hardcoded path allow-list
  (`rel.parts[:1] != (".claudster",)`), platform-infra cross-repo pointers. Renaming the dir means a
  fleet migration + permanent dual-path support for near-zero user value.
- **Brand-only rename (Scope A below): SMALL-MEDIUM (1-2 sessions).** Plugin/marketplace display
  name, docs, env vars — while `.claudster/` stays frozen forever as the artifact-dir convention
  (it's a filename, like `.git/` — git the brand could rename tomorrow and `.git/` wouldn't).
- **Timing leverage:** external installs today ≈ this machine only. The moment claudster goes
  public (B4), a rename's cost multiplies permanently. So: **decide BEFORE B4; execute AFTER the
  antigravity-plugin-parity program** (renaming mid-program would churn its plan/tracker/docs).

## DECISION GATE (user)
1. **New name.** Recommendation: **NOT "claudexity"** — a portmanteau of today's three vendors
   (claude+codex+antigravity) ages exactly like "claudster" is aging now, and it echoes
   "Perplexity". If the motive is vendor-neutrality (valid!), pick a vendor-free name (criteria:
   pronounceable, unclaimed on PyPI/npm/GitHub, no AI-vendor substring). If no better name wins,
   keeping "claudster" is a legitimate outcome of this gate.
2. **Scope: A only** (recommended) or A+deferred-B. `.claudster/` freeze is assumed either way.

## Scope A — brand-only rename (the plan)

### Phase 0 — Hygiene precondition (do regardless of rename)
The scan found `vscode-extensions/junai/vscode-extensions/junai/` — a committed, byte-identical
**self-nested duplicate checkout inside the junai mirror** (doubles its content; a naive rename
find/replace would touch it inconsistently). Remove it from the mirror repo + add a guard in
`sync.ps1` against re-introduction. Also confirm `claudster-private`'s marketplace/plugin names and
decide whether it follows the rename (it's local/VMIE-only — it can lag).
**Commit (junai repo):** `chore: remove self-nested duplicate checkout`

### Phase 1 — The identity flip (one coordinated pass, claudster-source + mirror)
All of these are lookup-key couplings — change together, verify with the existing test suite:
- `runtime-targets.json` `plugin`/`marketplace` blocks (names, descriptions, keywords)
- `sync.ps1` `Bump-RuntimeTargetsPluginVersion -PluginName "claudster"` + `$bumpedClaudster` vars
- Mirror `marketplace.json` + both `plugin.json`s (post-Phase-0 there is exactly one copy of each)
- README/guide install lines (`claudster@claudster` → `<new>@<new>`)
- **The `/claudster:` prefix follows the plugin name automatically** (Claude Code derives command
  namespace from plugin name — observed live). Every doc mentioning `/claudster:` updates in the
  same pass (~40 files, mechanical).
**Gate:** export + validate_pool + full suite; local `claude plugin install <new>@<new>` from the
mirror; every renamed command resolves.

### Phase 2 — Coordinated dependents (same day as Phase 1 ships)
- **docket** (branch, never main): `config.py` `DEFAULT_LANES` slash-commands (~lines 82-91),
  `runner.py` prompt strings (`/claudster:preflight`, `/claudster:code-review`),
  `CLAUDSTER_GUARD_DISABLED` env var (rename in lockstep with `claude-harness/hooks/guard.py:216`
  + `runner.py:497` + tests — exact-string coupling), `has_claudster` API field → keep as-is OR
  rename with a back-compat alias (decide at gate; keeping is cheaper and invisible to users).
  `.claudster/` paths: UNTOUCHED (frozen).
- **This machine's `~/.claude/settings.json`**: `enabledPlugins` + `extraKnownMarketplaces` keys →
  re-add marketplace under the new name, re-install, remove old keys; old plugin cache dirs are
  orphaned cruft — delete.
- Env-var bundle (`CLAUDSTER_KEYS_FILE`, `CLAUDSTER_HARNESS_SRC`, `CLAUDSTER_GUARD_DISABLED`):
  self-contained per the scan — rename in one grep-verified pass, accept old names as fallback for
  one version (read old THEN new, warn on old).
**Gate:** docket full suite green on the branch; live smoke: one docket lane run invoking the
renamed command end-to-end. STOP for user merge (docket main deploys).

### Phase 3 — Prose sweep + provenance
Docs/analysis, guides, MIGRATION.md note recording the rename + the `.claudster/` freeze decision;
`creation-agent:` values in NEW documents use the new name (existing frontmatter is history — leave).
Fleet repos' prose mentions: fold into normal knowledge-transfer passes, no dedicated sweep.

## Explicitly frozen (never rename)
- `.claudster/` artifact directory — everywhere, forever (documented in the MIGRATION.md note).
- GitHub repo names (`claudster-source`, `junai`) — repo ≠ brand already; renaming repos breaks
  remotes/clones for zero display value. Revisit only at B4 public-release time if ever.
- Script filenames (`claudster_config.py`, `claudster_init.py`) inside already-bootstrapped repos —
  new bootstraps get new names via the harness; old repos keep working copies (they self-reference
  by relative import).

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\brand-rename.md fully. Confirm the DECISION GATE
is closed (new name chosen + scope A confirmed by the user IN THIS SESSION — if not, STOP and ask).
Prerequisite: the antigravity-plugin-parity program is complete or parked at a phase boundary.
Then execute Phases 0-3 in order: per-phase commits, tracker flips in-commit, full claudster suite +
validate_pool per claudster-source phase, docket work on a branch with its own suite green and STOP
before merge (docket main deploys). junai-push only after Phase 1's local install validation passes.
```
