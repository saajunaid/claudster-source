---
type: plan
status: draft
feature: antigravity-plugin-parity
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-23T00:00:00Z
Creating Model: claude-fable-5
Last Author: Claude Code
Last Updated: 2026-07-23T00:00:00Z
Last Model Used: claude-fable-5
---

# AGENTS.md-canonical rules + fleet rollout + Antigravity plugin parity

## Goal
One claudster, same experience in every coding agent. Three linked outcomes:
1. **Rules single-sourcing** — `AGENTS.md` is the canonical rules file (root AND subfolders);
   `CLAUDE.md` becomes a shim (`@AGENTS.md` + Claude-native extras). No duplicated mirrors, no drift.
2. **Nothing manual, anywhere** — the new-project pipeline (platform-infra → project-template →
   app-forge) AND every existing repo across `E:\Projects` + `C:\Users\jshaik\Documents` adopt the
   pattern via tooling: pilot-validated on ONE repo before any fleet rollout.
3. **claudster as a first-class agy plugin** — install once, update centrally, with the portable
   hooks/agents/MCP slice.

## Status tracker & resume protocol (the interruption insurance — keep this current)
**Rule: a phase is not done until its row below is flipped, and the flip is committed IN the same
commit as the phase's work.** On ANY resume (new session, crash, interruption): read this table
first, then the phase text of the first ⬜ row — never re-derive completed work.

| Phase | Status |
|---|---|
| 0 — templates + setup script | ⬜ |
| 0b — knowledge-flow writers sweep + /add-rules | ⬜ |
| 1 — bootstrap infra (platform-infra / project-template) | ⬜ |
| 2 — migration tool | ⬜ |
| 3 — PILOT uni-sight (hard gate) | ⬜ |
| 4 — fleet rollout (per-repo sub-tracker below) | ⬜ |
| 5 — agy plugin contract probe | ⬜ |
| 6 — exporter target antigravity-plugin | ⬜ |
| 7 — distribution (marketplace + bundles) | ⬜ |
| 7b — bundle tiering core/extras | ⬜ |
| 8 — hooks/agents/MCP parity | ⬜ |
| 9 — adoption & lifecycle (user-level, registry, doctor, uninstall) | ⬜ |
| 10 — claudster-everywhere guide | ⬜ |

**Phase 4 per-repo sub-tracker** (flip each row in the commit made IN that repo; claudster-source
tracker commit may batch several flips):
⬜ app-forge · ⬜ app-sight · ⬜ appointment-assist · ⬜ nps-lens · ⬜ rev-sight · ⬜ serve-sight ·
⬜ career-ops · ⬜ nusba · ⬜ platform-infra(root) · ⬜ project-template(root) ·
⬜ docket (branch `chore/agents-md-canonical` — parked for user merge)

**Mandatory handoffs (run `/claudster:handoff` — relay.md update — at these points, plus at ANY
early stop):**
- **After Phase 4** — the fleet milestone: rules-everywhere is complete and consistent; relay must
  record the sub-tracker state, any conflict-repos resolved by hand, and docket's parked branch.
- **After Phase 7** — the distribution milestone: what's published where (marketplace URL, bundles/),
  what `claudster-init`/`agy plugin install` command now works from a clean machine.
- On interruption mid-Phase-4: the sub-tracker above + a one-line relay note ("resume at repo X")
  is sufficient — per-repo commits make every completed repo durable.

## Verified facts (explored 2026-07-23 — trust these, re-verify only if stale)

### The generation chain (today)
- `scripts/setup_project_ai.py` `compose_claude_md()` (~line 154-192) writes root `CLAUDE.md` from
  `claude-harness/claude-md/root.md.tmpl` AND root `AGENTS.md` from `agents.md.tmpl` — **two
  independent near-duplicates** (root.md.tmpl is the fuller one). Folder fragments
  (`backend-python.md`, `backend-fastapi.md`, `frontend-react.md`, `tests-pytest.md`, selected via
  `stack-map.json` `target:` e.g. `src/CLAUDE.md`, `frontend/CLAUDE.md`, `tests/CLAUDE.md`) are
  written as **CLAUDE.md only — no subfolder AGENTS.md exists today**. Script is idempotent
  (skip-if-exists unless `--force`); exit 3 = unresolved `{{TOKEN}}`s.
- **Bootstrap pipeline**: `E:\Projects\platform-infra\bootstrap\new-vmie-project.ps1` (2103 lines,
  13 stages) copies `E:\Projects\project-template` (Stage 1 `Copy-TemplateDeterministic` ~313-420;
  **CLAUDE.md/AGENTS.md are in the exclude list** ~352-353), then Stage 10 (~1675-1737) runs
  `setup_project_ai.py` from `$env:JUNO_POOL` **defaulting to `E:\Projects\agent-sandbox`**, then
  (~1711-1728) appends `project-template\template-overlays\claude-md\platform-rules.md` to BOTH
  `CLAUDE.md` and `AGENTS.md` (`foreach ($mirror in @("CLAUDE.md","AGENTS.md"))`).
- **`E:\Projects\app-forge`** (FastAPI+React bootstrap console) does NOT re-implement generation —
  `src\services\forge_service.py` shells to the same `new-vmie-project.ps1`
  (env `FORGE_PLATFORM_INFRA`). No template edits needed there; it inherits every fix.
- **DRIFT BUG (fix in Phase 1):** `agent-sandbox` is the FROZEN pre-extraction monorepo (last
  commit: "claudster extraction complete (agent-sandbox now private)"). Its `setup_project_ai.py`
  and both templates DIFFER from claudster-source (missing e.g. the ask-rules self-heal). Stage 10
  therefore bootstraps new projects from a stale harness TODAY.
- Claude Code `CLAUDE.md` supports `@path` imports (≤5 hops) — the shim mechanism. `@AGENTS.md` in
  a subfolder CLAUDE.md resolves relative to that file. LIVE-VERIFY in Phase 0 before relying on it.
- agy reads directory-based AGENTS.md (root + subfolders) — live-validated 2026-07-23 (root; verify
  nested during Phase 0 pilot probe). codex 0.137 reads root AGENTS.md only (`child_agents_md` off).

### The fleet (inventoried 2026-07-23 — the rollout worklist)
20 git repos under the two roots (top 2 levels), claudster-source excluded:

| Group | Repos |
|---|---|
| **A — full claudster pair (CLAUDE.md + mirror AGENTS.md + subfolder CLAUDE.mds)** | app-forge, app-sight, appointment-assist, nps-lens, rev-sight, serve-sight, uni-sight |
| **B — CLAUDE.md hierarchy, NO AGENTS.md** | docket (4 subfolders; **deploy-on-push — branch only!**), career-ops (3), nusba (14) |
| **C — root-only CLAUDE.md** | platform-infra, project-template (handled in Phase 1, not the fleet tool) |
| **D — EXCLUDE from rollout** | agent-sandbox (frozen), backup\AppointmentAssist + AppointmentAssist (backups/dupes), docket-livetest (scratch), app-sight-orgs\*, claudster-private, Customer360, junaid\site (no claudster rules) |

### agy plugin surface (probed 2026-07-23)
`agy plugin install <plugin@marketplace> | validate <path> | link <mp> <target> | import | enable |
disable`; manifests `plugin.json` (+`import_manifest.json`); marketplaces `.agents/plugins/marketplace.json`;
hooks live example on this box: `~/.agents/hooks/hooks.json` + `scripts/`; custom agents (`agy agents`
— empty today); MCP `~/.gemini/config/mcp_config.json`; settings `~/.gemini/antigravity-cli/settings.json`.
Binary has NO `.claude/` paths — `plugin import claude` targets something else; do not depend on it.
Headless gotchas (cite `docs/analysis/antigravity-contract.md`): `agy -p` binds to LAST project — always
`--new-project`; permissions auto-denied headless — `--dangerously-skip-permissions` (scratch only);
`--sandbox` hangs on this box.

## Phases

### Phase 0 — Templates + setup script: AGENTS.md canonical, CLAUDE.md shim (claudster-source)
**Touches:** `claude-harness/claude-md/agents.md.tmpl`, `root.md.tmpl`, the 4 folder fragments,
`stack-map.json` (targets), `scripts/setup_project_ai.py`, `scripts/tests/test_setup_claudster.py`.
**Implement (TDD — tests first):**
1. `agents.md.tmpl` becomes the single canonical root doc: merge IN everything root.md.tmpl has that
   it lacks (harness loop diagram, "Where things live", doc-discipline). Keep it agent-neutral
   (no Claude-only phrasing); placeholders `{{PROJECT_NAME}}`/`{{PROJECT_DESCRIPTION}}`/
   `{{STACK_SUMMARY}}`/`{{STACK_REFERENCE_LINE}}` move here.
2. `root.md.tmpl` becomes the shim: `# {{PROJECT_NAME}} — Project Memory` + `@AGENTS.md` + a short
   **Claude-native block** (subagents/skills/commands pointers, statusline note — ONLY things other
   agents can't use). Target ≤15 lines.
3. Folder fragments: `compose_claude_md()` writes each fragment body to `<folder>/AGENTS.md`
   (canonical) and `<folder>/CLAUDE.md` as the 2-line shim `@AGENTS.md`. Adjust `stack-map.json`
   targets or the write loop accordingly (keep the map's `target` keys stable if possible — derive
   both paths in code).
4. Update docstring/comments asserting "AGENTS.md mirror"; `--force` semantics unchanged.
**Exit gate (LIVE, scratch project):** run the script on a scratch FastAPI+React tree; then
(a) `claude -p` (or a session) answers "what are The Laws?" WITHOUT reading AGENTS.md explicitly —
proves the `@AGENTS.md` import inlines; (b) same for a subfolder rule via `frontend/CLAUDE.md`;
(c) `agy -p --new-project` reads root AND `frontend/AGENTS.md`; (d) `codex debug prompt-input`
shows root AGENTS.md content. Full suite + validate_pool green.
**Commit:** `feat(setup): AGENTS.md-canonical rules; CLAUDE.md becomes an @import shim (root + folders)`

### Phase 0b — Knowledge-flow writers/readers sweep (nothing may still write rules to CLAUDE.md)
**Why:** after Phase 0, a CLAUDE.md is a shim. Any flow that APPENDS learnings/conventions to
CLAUDE.md re-forks the rules for Claude only — silent single-sourcing breakage. Swept 2026-07-23;
the lists below are exact (re-grep `CLAUDE.md` across `claude-harness/` + `.github/skills/` to catch
additions since).
**WRITERS — must now target AGENTS.md (the canonical file):**
- `claude-harness/agents/knowledge-transfer.md` — "writes to … CLAUDE.md" → durable repo
  rules/conventions go to the matching `AGENTS.md` (root or subfolder); Claude-native-only notes
  (subagent/skill/statusline specifics) may go to the CLAUDE.md shim's Claude-native block.
- `claude-harness/agents/claude-md-curator.md` — re-scope: curates `AGENTS.md` files (the ~80-line
  bloat threshold applies to AGENTS.md now); treats 2-line shims as fixed artifacts (flag a shim
  that has grown as a smell); keep the agent name (rename is churn) but fix its brief.
- `claude-harness/commands/handoff.md` + `claude-harness/commands/setup-project-ai.md` +
  `.github/skills/workflow/setup-project-ai/SKILL.md` — every "enrich/update CLAUDE.md" step
  becomes "enrich AGENTS.md" (the shim is never enriched).
- `scripts/setup_project_ai.py` ~line 551 — harness-facts scaffold text "copy … into the matching
  CLAUDE.md (root vs backend/ vs frontend/)" → "matching AGENTS.md".
- `claude-harness/scripts/check_doc_coverage.py` ~line 525 — `claude_md_budget` measures the
  always-loaded rules file: point it at AGENTS.md (+ shim size); accept `claude_md_budget` config
  key for back-compat, add `agents_md_budget` alias. Update the config comment in
  `setup_project_ai.py` ~617.
**READERS — mechanical wording pass ("conventions live in AGENTS.md; CLAUDE.md may be a shim"):**
harness agents `code-reviewer, preflight, tester, data-engineer, security-analyst, sql-expert,
ui-design-reviewer`; commands `implement, tdd, ship, ship-pr, ship-merge`; pool skills
`best-practices (SKILL + references + codebase-context-builder), agent-md-refactor,
receiving-code-review, using-git-worktrees, understand-anything (references/commands.md)`.
**NEW command — `/claudster:add-rules <folder> [purpose]`** (`claude-harness/commands/add-rules.md` +
`claude-harness/claude-md/folder-agents.md.tmpl`): creates rules for ANY folder, not just the
stack-map ones. Behavior: refuse if `<folder>/AGENTS.md` exists (point at knowledge-transfer for
updates); write `<folder>/AGENTS.md` from the template (folder purpose, conventions, gotchas
sections — seeded from `[purpose]` + a quick read of the folder's contents) and `<folder>/CLAUDE.md`
as the standard 2-line shim; remind that ongoing updates flow through knowledge-transfer/curator
(no separate upkeep command needed — they match ANY existing AGENTS.md, not a fixed folder list).
Register it wherever commands are registered; convention test covers its template too.
**Enforcement:** add `scripts/tests/test_agents_md_canonical.py` — greps the harness agents/commands
for instruction patterns that direct WRITING rules into CLAUDE.md (allowlist the shim-block
exception) so regressions fail the build.
**Exit gate:** grep sweep clean; new convention test + full suite + validate_pool green;
`junai-push` (templates + agents + commands ship in the plugin → version bump expected).
**Commit:** `fix(harness): knowledge flows write AGENTS.md — handoff/knowledge-transfer/curator/doc-budget swept`

### Phase 1 — Bootstrap infra: platform-infra + project-template (+ app-forge inherits)
**Touches:** `E:\Projects\platform-infra\bootstrap\new-vmie-project.ps1`,
`E:\Projects\project-template\template-overlays\claude-md\platform-rules.md` (+ both repos'
own root rules via the Phase-2 tool later). app-forge: NO code change (shells to the generator).
**Implement:**
1. **Repoint the harness source**: Stage 10 default `$agentSandboxRoot` from `E:\Projects\agent-sandbox`
   → `E:\Projects\claudster-source` (keep `$env:JUNO_POOL` override). This also picks up the newer
   script fixes (drift bug above).
2. Stage 10 append loop: append `platform-rules.md` to **AGENTS.md only** (appending prose after a
   shim's `@AGENTS.md` line would defeat single-sourcing). Update the success print text.
3. `platform-rules.md`: fix the header ("Appended … to CLAUDE.md" → AGENTS.md) and any
   "`<repo>/CLAUDE.md §…`" style references.
4. Stage 1 exclude list: unchanged (both names stay excluded) — confirm.
**Exit gate (LIVE):** bootstrap a scratch project end-to-end via `new-vmie-project.ps1` (or its
non-Gitea dry path if available): resulting tree has canonical AGENTS.md (with platform rules
appended at the END of AGENTS.md only), shim CLAUDE.md, subfolder pairs; the Phase-0 (a)-(d) probes
pass on it. Commit in platform-infra + project-template (their own repos, their own conventions).
**Commit:** `feat(bootstrap): generator emits AGENTS.md-canonical rules; repoint harness to claudster-source`

### Phase 2 — The migration tool (fleet automation, TDD)
**Touches:** `scripts/claudster_migrate_rules.py` (new), `scripts/tests/test_migrate_rules.py` (new),
ship in the plugin (`runtime-targets.json` claude target files list, like claudster_init).
**Behavior (per target repo):**
- Refuse to run on a dirty working tree (unless `--allow-dirty`). `--dry-run` default; `--apply` executes.
- ROOT: if `AGENTS.md` exists and is the old claudster mirror → replace with content derived from
  the (fuller, possibly enriched) `CLAUDE.md`, re-headed agent-neutrally; if `AGENTS.md` is absent
  (group B) → `CLAUDE.md` content becomes `AGENTS.md`. Then write `CLAUDE.md` shim. **If the two
  existing files have DIVERGED beyond the known template skeleton (project enrichments on both
  sides), do NOT guess: emit a per-repo conflict report and skip the root pair (exit 1)** — the
  session running the rollout resolves those few by hand-merge, tool re-run confirms.
- SUBFOLDERS: each `<dir>/CLAUDE.md` → `git mv` to `<dir>/AGENTS.md` + write `<dir>/CLAUDE.md` shim.
- Preserve document-frontmatter provenance if present; idempotent (re-run = no-op); `git mv` when
  tracked; never touch `done/`-style archived files; summary report (migrated / skipped / conflicts).
- **`--check` mode (fork detector, for re-runs after migration):** flag any `CLAUDE.md` that is NOT
  a shim while a sibling `AGENTS.md` exists (drifted shim), and any bare `CLAUDE.md` with no sibling
  `AGENTS.md` (a hand-created fork — the fix is `/claudster:add-rules` semantics: promote content to
  AGENTS.md + shim). Exit 1 on findings so it can gate future sweeps.
**Exit gate:** tests cover: mirror-replace, absent-AGENTS create, divergence-conflict skip,
subfolder pair, idempotent re-run, dirty-tree refusal, dry-run touches nothing. Full suite green.
**Commit:** `feat(tools): claudster_migrate_rules — CLAUDE.md→AGENTS.md-canonical fleet migration`

### Phase 3 — PILOT on ONE repo (hard gate before any fleet work)
**Pilot: `E:\Projects\uni-sight`** (group A: full pair + 3 subfolders + copilot file — the richest
single test). Run the tool `--apply`, then the full validation battery:
1. Claude Code: session answers Laws + a subfolder rule through the shims (no direct AGENTS.md read).
2. agy: `agy -p --new-project` from the repo — root Laws + one subfolder rule + one skill still fires.
3. codex: `codex debug prompt-input` shows the root AGENTS.md content.
4. Repo's own tests still pass (whatever suite uni-sight has) — migration touched only rules files.
5. `git diff` review: nothing lost from either old file (spot-check enrichments survived).
**Exit gate:** all 5 green, committed IN uni-sight. **If any fail: fix tool/templates, re-pilot.
DO NOT proceed to Phase 4.**
**Commit (uni-sight):** `chore(rules): migrate to AGENTS.md-canonical (claudster pilot)`

### Phase 4 — Fleet rollout (automated, per-repo commits)
**Worklist:** Group A remainder (app-forge, app-sight, appointment-assist, nps-lens, rev-sight,
serve-sight) then Group B (career-ops, nusba; **docket LAST and on branch `chore/agents-md-canonical`
— NEVER push docket main, it deploys**). Group C (platform-infra, project-template roots) via the
same tool. Group D untouched.
**Per repo:** clean-tree check → tool `--apply` → quick probe (Claude Laws answer + `agy -p
--new-project` root check) → commit `chore(rules): migrate to AGENTS.md-canonical rules` → next.
Conflict-report repos: hand-merge in-session, re-run, then commit. Summary table at the end
(repo / migrated / conflicts / validation). docket: open PR/branch, STOP for the user's merge.
**Exit gate:** every non-excluded repo migrated & validated (docket parked on its branch); summary
recorded in `docs/analysis/agents-md-rollout-2026-07.md`.

### Phase 5 — Probe the agy plugin/hooks/agents contract
As previously planned: scaffold hello-world plugin, iterate against `agy plugin validate` (the
schema oracle); read the live `~/.agents/hooks/hooks.json` + `scripts/`; probe marketplace.json via
`agy plugin link`; probe custom-agent format until `agy agents` lists one. Record ALL schemas
verbatim in `docs/analysis/antigravity-plugin-contract.md`; hello-world must install, enable, and
its skill fire in a live `agy -p --new-project` session.
**Commit:** `docs(analysis): agy plugin/hooks/agents contract — probed`

### Phase 6 — Exporter target `antigravity-plugin`
Package claudster (skill roster = the antigravity bundle roster; rules templates; mapped extras)
in agy plugin layout with generated `plugin.json`; version follows the claudster manifest bump flow.
`agy plugin validate` green; local install → a skill fires live; `validate_pool` extended to lint
the bundle; full suite green.
**Commit:** `feat(export): antigravity-plugin target — claudster as an agy plugin`

### Phase 7 — Distribution: marketplace + bundles publish (junai repo)
Extend `sync.ps1` junai-push: publish the agy plugin + `marketplace.json` AND the deferred
`bundles/<target>/` (codex, antigravity — closes toolbox-portability Phase 4's tail so
`claudster-init` GitHub mode works). Leak-free `git grep` gate before the mirror push. Validate:
on this box, `agy plugin install claudster@<marketplace-from-GitHub>` → skill fires; `claudster-init
--target codex` with NO `--from` works. README "Installing outside Claude Code" updated.
**Commit:** `feat(dist): claudster agy plugin + harness bundles published — install-once from GitHub`

### Phase 7b — Bundle tiering: core by default, extras opt-in (context budget)
**Why:** Claude Code deliberately ships core (~38 skills) always-on + extras opt-in to keep context
lean; the codex/antigravity bundles flattened that away — all 94 skills' metadata loads every
session (codex even logs "truncated skill metadata to fit skills context budget").
**Implement:** split the codex + antigravity targets (and the Phase-6 agy plugin) into the SAME
core/extras tiers as the claude/claude-extras rosters (reuse those roster lists — do not invent a
third tier split). `claudster-init` gains `--extras` to add the tail; codex disable mechanism
(`[[skills.config]]`) and agy equivalent documented for per-skill trimming. Default install = core.
**Exit gate:** default bundle ≤ core roster; `--extras` adds the rest; both verified via the
harness-native probes (`codex debug prompt-input` skill count; `agy -p --new-project` skill listing).
**Commit:** `feat(export): core/extras tiering for codex+antigravity bundles (context budget parity)`

### Phase 8 — Deeper parity: hooks, agents, MCP
Map the portable hook slice onto agy's hooks.json (per Phase-5 schema; skip non-equivalents,
record the parity table in `docs/guide/porting-to-a-harness.md`); ship 2-3 claudster agents
(code-reviewer, preflight) as agy custom agents if the format proved out; junai-mcp into
`~/.gemini/config/mcp_config.json` + codex `[[mcp_servers]]` (absorbs toolbox-portability Phase 5).
One hook + one agent + one MCP tool demonstrably firing in agy.
**Commit:** `feat(agy): hooks/agents/MCP parity slice`

### Phase 9 — Adoption & lifecycle: user-level installs, registry, doctor, uninstall
**The real-world smoothness layer — each item is a probed-fact-backed fix to a lifecycle pain:**
1. **User-level install mode (NEW DEFAULT for skills):** both harnesses merge user-level skills
   (probed: codex `r1/r2 = ~/.codex/skills`; agy merges `~/.agents/skills` — validated live).
   `claudster-init --user --target codex|antigravity` installs skills there ONCE (namespaced
   sub-tree where the harness allows, to avoid collisions with existing user skills e.g. the
   azure-* set); per-repo mode (`--dest`) remains for AGENTS.md (always per-repo) and for teams
   that want vendored/pinned skills. Update README guidance: repo = rules, user = skills.
2. **Install registry + fleet update:** every `claudster-init` apply appends
   `{location, target, mode, version, timestamp}` to `~/.claudster/installs.json`;
   `claudster-init --update-all` re-runs every registered install (conflict rules unchanged).
3. **Version stamping + skew detection:** record the claudster bundle version in
   `.claudster-init.json` and an `<!-- claudster vX.Y.Z -->` footer in generated AGENTS.md;
   doctor reports skew across registry entries.
4. **`claudster-init --doctor` (or `claudster_doctor.py`):** per harness — binary present + PATH
   health (incl. the "new terminal" Windows gotcha), version vs the probed-contract version
   (WARN on drift, e.g. codex 0.145 vs probed 0.137 → "re-probe the contract"), auth state
   (codex: distrust `codex doctor`'s token-presence claim — attempt-based check; agy: keyring
   check), rules-file integrity (root AGENTS.md present; shims are shims — reuse the Phase-2
   fork detector), skills discovered at the harness's probed path, python availability for the
   tooling itself. Read-only, exit 1 on failures, human-readable report.
5. **`claudster-init --uninstall`:** remove manifest-tracked UNMODIFIED files (+ registry entry);
   modified files listed and left. Makes trying claudster risk-free.
6. **Maintenance signals (deterministic detectors, NOT scheduled LLM runs):** doctor also computes
   and reports — (a) rules-file budget breaches (AGENTS.md over `claude_md_budget`/alias — the
   "run claude-md-curator now" signal), (b) kb DOC-MAP dangling links (the "run /claudster:kb"
   signal), (c) harness-contract version drift (probed version vs installed), (d) days since last
   doctor run (stamp `~/.claudster/last-doctor.json`). The SessionStart hook prints ONE nudge line
   when any signal fires (pure file checks, no LLM, no auto-fix) — curator/kb stay human-triggered,
   surfaced instead of forgotten.
**TDD throughout; ship all of it in the plugin scripts/ like claudster_init.**
**Commit:** `feat(dist): user-level installs, install registry + update-all, doctor, uninstall`

### Phase 10 — The onboarding surface: one page, every harness
`docs/guide/claudster-everywhere.md`: the 10-minute path — one table (harness / install command /
where skills live / where rules live / update command / doctor), the three quickstarts
(Claude Code marketplace; codex + agy via `claudster-init --user` then per-repo AGENTS.md), the
shim convention explained in 5 lines, troubleshooting = "run the doctor". Link it from README and
from `docs/guide/start-here.md`; refresh the docket-Help-rendered guide pages that describe
claudster as Claude-Code-only (the guide is the canonical md under docs/guide — docket renders it).
**Commit:** `docs(guide): claudster-everywhere — cross-harness onboarding + troubleshooting`

## Landmines & edge cases (checked 2026-07-23 — read before the phase that owns each)
- **platform-infra drift/spec libs** (`bootstrap\lib\template-drift.ps1`, `sync-specs.ps1`): check
  for CLAUDE.md filename/checksum assumptions during Phase 1 — the generator's exclude list is not
  the only place the filename appears.
- **docket runner** `_review_prompt` says "conventions (CLAUDE.md)" — harmless (Claude Code inlines
  the shim's import at load), but tweak the wording on the Phase-4 docket branch while there.
- **User-level `~/.claude/CLAUDE.md`** is Claude-personal config — NOT part of this migration; never
  touch it.
- **Installed-plugin staleness:** Phases 2-4 run the migration tool from the claudster-source
  checkout (not the installed plugin), so fleet work doesn't depend on plugin update timing; still
  `junai-push` after 0/0b so other machines get the new templates.
- **Copilot lane unaffected:** `.github/copilot-instructions.md` files (12 repos) are a separate
  convention — out of scope, do not migrate or delete.
- **uni-sight has a real pytest suite** (verified) — pilot gate #4 stands as written.
- **@import depth:** shims use exactly 1 hop (limit 5) — do not chain shims to shims.
- **CRLF:** fleet repos are Windows-checked-out; write files with the repo's existing line endings
  (git will warn — that's fine); never let the tool rewrite unrelated lines.
- **`~/.agents/skills` collisions (Phase 6):** the user profile already carries non-claudster skills
  (azure-*, etc.); the agy plugin must namespace or install to its plugin dir — never dump into
  `~/.agents/skills` where names could collide.
- **Two-session coordination:** before touching shared claudster-source build files
  (`sync.ps1`, `export_runtime_resources.py`, `validate_pool.py`), check `.claudster/relay.md` for
  a concurrent session's ownership claims (pattern from 2026-07-21).

## Non-goals
- No second claudster; no hand-maintained copies; no symlinks for rules (Windows privilege + git
  fragility — the `@AGENTS.md` shim is the mechanism).
- No statusline/permission-mode/slash-UX parity chasing; no reliance on `agy plugin import claude`.
- No pushing docket main, ever. No fleet work before the Phase-3 pilot gate passes.
- agent-sandbox stays frozen — repointed away from, never edited.

## Rules for the implementing session
- Probe-first: every harness format claim from live tools/files/binary strings; cite
  `docs/analysis/antigravity-contract.md` + `codex-cli-contract.md`; never remembered flags.
- TDD all code. After each claudster-source phase: `python -m pytest scripts/tests/
  claude-harness/hooks/tests/ -q --import-mode=importlib` AND `python validate_pool.py`.
- Commit per phase (per repo in Phase 4), only files the phase touched; update this plan's phases
  with ✅ + hash as you go. `junai-push` (bare) after claudster-source phases that change the
  plugin/bundles; the Phase-7 mirror push needs the leak-free `git grep` gate first.
- Fleet repos are OTHER git repos: check `git status` before and commit IN that repo; never cross-commit.
- If a HUMAN step blocks (auth, docket merge), record blocked-on-human in this plan and continue
  with the next unblocked work.

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\antigravity-plugin-parity.md FULLY, then execute
it autonomously from E:\Projects\claudster-source. It is the single source of truth — its Verified
facts section carries the probed contracts, exact file/line anchors, and the 20-repo fleet worklist
with exclusions; do not re-derive them, and probe live (never from memory) anywhere it says probe.
Order is strict: Phase 0 (templates+setup script, TDD, live-verified @AGENTS.md shim on all three
harnesses) → Phase 0b (knowledge-flow writers sweep — handoff/knowledge-transfer/curator/doc-budget
must write AGENTS.md, with the new convention test) → Phase 1 (platform-infra generator: repoint
agent-sandbox→claudster-source, append platform rules to AGENTS.md only; live bootstrap proof;
check template-drift/sync-specs libs) → Phase 2 (migration tool, TDD) → Phase 3
(PILOT uni-sight — hard gate: all 5 validations green or STOP and fix, never proceed) → Phase 4
(fleet rollout per the worklist; docket ONLY on branch chore/agents-md-canonical, never push docket
main) → Phases 5-10 (agy plugin probe → exporter target → GitHub distribution incl. the deferred
bundles/ publish → 7b core/extras bundle tiering → hooks/agents/MCP parity → 9 adoption layer:
user-level installs as the skills default, install registry + --update-all, version stamping,
claudster doctor, --uninstall → 10 the claudster-everywhere onboarding guide). Gates after every
claudster-source phase: python -m
pytest scripts/tests/ claude-harness/hooks/tests/ -q --import-mode=importlib AND python
validate_pool.py. RESUMABILITY IS LAW: commit per phase (per repo in Phase 4); flip the Status
tracker row (and Phase-4 sub-tracker rows) IN the same commit as the work; on any resume read the
Status tracker first and continue at the first ⬜ row; run /claudster:handoff after Phase 4, after
Phase 7, and at any early stop. junai-push (bare) where the plan says so,
with the leak-free git grep gate before any mirror publish. agy and Claude Code are authenticated
on this box; codex may need login — if any live step blocks on auth or a human merge, mark it
blocked-on-human in the plan and continue with the next unblocked work. Never ask a question this
plan can answer.
```
