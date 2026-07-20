---
type: plan
status: current
feature: oss-model-lanes-and-public-readiness
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-15T00:00:00Z
Creating Model: claude-opus-4-8
Last Author: Claude Code
Last Updated: 2026-07-20T00:00:00Z
Last Model Used: claude-opus-4-8
---

# OSS model lanes → public-readiness → cross-vendor review

Three tracks, **executed in this order** (the user set the sequence). Each is independently shippable;
do not start the next until the prior track's Ship phase is green.

- **Track A (#2) — DONE (2026-07-19, A1–A4 all shipped, `junai-push`'d).** Model-switching as a real,
  easy-to-use claudster feature. Today the only way to run a Claude Code session on GLM is a *personal*
  machine-local wrapper (`C:\Users\jshaik\Documents\claude-glm.ps1`) that hardcodes a key path. Make it a
  first-class, cross-platform, teammate-usable capability shipped in the plugin.
- **Track B (#1) — B1/B2/B3 DONE (2026-07-20); B4 (publish decision) awaiting the user.** Make claudster
  public-ready. Add a LICENSE, sweep internal references, genericize the guide. docket is **not** being
  made public now — only confirm the *wider team* can use it. Reports:
  `docs/analysis/PUBLIC-READINESS.md` (B2 privacy sweep + B3 docket checklist).
- **Track C (#3) — DONE (2026-07-20), `feat/cross-review-gate` (docket, not pushed).** Cross-vendor
  code-review in the pipeline. The real need isn't per-phase quota-saving; it's running the *review* on a
  different vendor (DeepSeek) for genuine blind-spot diversity. The Implement lane already HAS a review
  gate — points it (optionally) at `tools/cross_review_gate.py`. C3 skipped (see the investigation note —
  the plan-skill review dispatch is a separate, non-conflicting mechanism). Results:
  `E:\Projects\docket\docs\analysis\track-c-cross-review-gate-results.md`.
  **Note:** run out of the plan's stated A→B→C order (C before B) per explicit user direction after A
  shipped — each track is independently shippable, so this is safe.

## Current state (verified 2026-07-15)
- **Model switching:** no claudster feature exists. `oss_review.py` (`.github/tools/`) has provider presets
  (`deepseek`/`glm`/`openrouter`) + env override — reuse its resolver idea. The `claude-glm` wrapper is
  personal and not in the repo.
- **Headless model:** fixed at process launch. docket's adapters add `--model <model>` from
  `agent_track.model` (`src/docket/harness.py:92`); harness chosen by `agent_track.harness`. **One
  `/implement` run = one process = one model for all phases** — no mid-run switching, no per-phase input.
- **Review gate already exists:** docket's Implement lane runs a code-review gate (`runner._review_prompt`,
  `agent_track.review_cmd`, `REVIEW: CLEAN`/`BLOCKING` → `needs_review`). The gate seam accepts ANY
  executable, so a wrapper can drop cross-vendor review in with ZERO docket code change.
- **Public-readiness gaps:** no root `LICENSE` in claudster-source **or** docket; internal-flavoured refs
  (`vmie-`, hostnames, the `enterprise-dashboard` recipe, a VMIE handoff doc) exist in the pool; the new
  `docs/guide/providers-and-keys.md` bakes in a `C:\Users\jshaik\…` path.
- **Prior art:** `.claudster/plans/codex-integration.md` Phase 5 scoped "codex as the Implement review gate."
  Track C **supersedes** it with a provider-agnostic version built on `oss_review.py`.

---

## Track 0 — security & privacy hardening (from the Fable audits) — RUNS FIRST

Added 2026-07-16 after the two Fable audits ([`docs/analysis/fable-audit-claudster-2026-07-15.md`],
[`docs/analysis/fable-audit-docket-2026-07-15.md`]). These precede Track A because several are live-ish
exposures and they turn Track B's vague "privacy sweep" into concrete, done work.

**P0 — claudster (main thread can do; do first):**
1. **Confirmed internal-infra leak in the public `claude-extras` bundle** — `deploy-local/SKILL.md` (+ the
   generated `_registry.md`) carry `iegbcoppoc02` / `gitea.internal` / `VMIE_BOT_TOKEN`. Genericize the
   internal identifiers to placeholders (or classify private + exclude), regenerate the registry, re-export,
   and **grep the built bundle to prove it's clean**.
2. **Privacy gate can't catch it** — `validate_pool.py` denylists only `vmie-`. Broaden to org identifiers /
   hosts / usernames (`iegbcoppoc`, `gitea.internal`, `VMIE_BOT_TOKEN`, `jshaik`) so the class can't regress.
3. **Personal paths + credential-incident handoff in public files** — genericize `docs/guide/*`,
   `claude-harness/README.md`, `copilot-instructions.md`, tracked plans; remove the `2026-02-26` handoff from
   the public tree.

**P0 — docket (feature-branch `feat/run-safety`; before wider team use):** the autonomous-run safety trio.
- **F1 ✅ (docket 06b7cdc)** — `requires_confirmation` now enforced: a run needing confirmation is skipped
  by `claim_agent_run` + the runner's `_execute` until a lead confirms it (new `agent.run.confirmed` event +
  lead-only `POST /api/tasks/{id}/runs/{rid}/confirm`). A Ship-lane drag can no longer auto-deploy prod.
- **F17 ✅ (docket a76a5e9)** — the lane-drag auto-trigger is gated to leads (`move_task(trigger_agents=...)`,
  the `/move` endpoint passes `is_lead`). A contributor staging a card in an agent lane no longer auto-runs.
- **F12 — PARTIAL shipped, full isolation DEFERRED.**
  - **Shipped (docket e8a369b):** `_sweep_stale_guard` self-heals a crash-leftover pre-commit guard — a died
    Implement run no longer (a) blocks the human's own commits via the orphaned guard, nor (b) buries their
    real hook when the next run backs the stale guard up as if it were theirs. Called before each guard
    install; tested.
  - **Still DEFERRED — full worktree isolation** (so a run never switches the human's branch / entangles WIP):
    replace `_ensure_feature_branch`'s `checkout -B` (`runner.py:1202`) with `git worktree add <path> -b
    agent/<slug>`, thread that cwd through EVERY `project` use in `_execute_implement` (preflight/implement/
    review spawns, test run, branch+protected checks), `git worktree remove --force` in `finally` + a startup
    reconcile, and keep the guard (worktrees share `.git/hooks`).
  - **⚠ Correctness subtleties found (2026-07-16) — the reason a blind refactor is unsafe:**
    1. **Uncommitted plan artifacts.** The pipeline reads `.claudster/plans/<slug>.md` from the working tree
       (`runner.py:1182`); if the Plan lane leaves it uncommitted, a fresh worktree branched from HEAD won't
       contain it → "plan not found". The worktree impl MUST copy `.claudster/` artifacts into the worktree
       (or ensure they're committed first). Same for `PROJECT-FACTS.md` / the resolved test command.
    2. **A dirty-tree refusal is NOT a clean substitute** — `git status --porcelain` is non-empty precisely
       because docket writes those `.claudster/` artifacts, so a naive "refuse if dirty" blocks every run;
       it would have to scope to changes OUTSIDE `.claudster/`.
    Verify with a LIVE Implement run (stand up a test repo + a real/fake harness), not unit tests alone.

**P1 — claudster:** guard.py Windows-delete + force-push-refspec gaps; `sync.ps1` `$LASTEXITCODE` checks
(push-fail-as-success); make `/claudster:cross-review` actually resolve; Dream Memory full-command
fingerprint (kill hitCount inflation); exporter fail-closed on phantom/missing skills + no implicit `Bash`.
**P1 — docket:** stuck-run runtime reconcile, corrupt-log handling, ~~accessibility (keyboard DnD + real
dialogs)~~ **✅ shipped 2026-07-17** (docket branch `feat/a11y`, 7 commits `710f89d…4f21dfa`, F30–F34 per
`.claudster/prompts/docket-accessibility-implement.md`; verification note in docket
`docs/analysis/a11y-implementation-2026-07-17.md` — web suite 138 green, keyboard walkthrough ALL PASS;
NOT merged to docket main), stakeholder bug-upload.

**HUMAN actions (not code):** rotate the three tokens (`pypimcp.key` + 2 PATs) and relocate to a secret
store; decide whether the `claudster`/`claudster-extras` marketplace is public (sets whether #1 is a live
leak needing republish, or a pre-public cleanup).

Corrected from the audit: the `junai-mcp` shell tool is **stdio/local** (footgun to gate, not remote RCE);
the credential files are **gitignored/untracked** (rotate anyway, but not an active git leak).

---

## Track A (#2) — Model-switching as a real claudster feature

**Goal:** any user (not just the author) switches their Claude Code session to GLM/DeepSeek/etc. with **one
command**, cross-platform, with **no hardcoded key paths**. "Easy to use" is the acceptance bar.

**Design decisions (settled):**
1. **Keys are resolved, never hardcoded.** Precedence: explicit env (`GLM_API_KEY`, `DEEPSEEK_API_KEY`,
   `OPENROUTER_API_KEY`) → a keys file at `CLAUDSTER_KEYS_FILE` (default `~/.claudster/keys.env`, INI/env
   style) → error with an actionable message. The current personal `api-keys.txt` becomes just one possible
   `CLAUDSTER_KEYS_FILE`.
2. **One provider table, shared with `oss_review.py`.** Reuse the `deepseek`/`glm`/`openrouter` presets
   (base_url + default model + which env key). A rename is a one-line edit; env always overrides.
3. **Cross-platform launchers.** Ship both `claude-oss.ps1` (Windows/PowerShell) and `claude-oss.sh`
   (bash/macOS/Linux). Each sets `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` (+ `ANTHROPIC_MODEL`),
   launches `claude` with passthrough args, and **restores env on exit** so the default `claude` is untouched.
4. **Discoverable + installable.** A `/claudster:use-model` command doc explains it; `/setup-project-ai`
   (or a documented one-liner) installs a `claude-glm` / `claude-oss` shim onto PATH / into the shell profile.

### Phase A1 — provider+keys resolver (TDD)
**Touches:** `claude-harness/scripts/oss_model.py` (new, the shared resolver), `scripts/tests/test_oss_model.py`.
**Implement:** `resolve(provider, env) -> {base_url, model, api_key}` with the precedence above; a `PROVIDERS`
table matching `oss_review.py`; `KeyError`-style `ConfigError` with an actionable message when no key resolves;
a keys-file parser (INI/`KEY=VALUE`, comments allowed). Consider having `oss_review.py` import this later
(note it; don't refactor `oss_review.py` in this phase to keep the diff small).
**TDD (RED first):** env-key wins; keys-file fallback; unknown provider needs explicit base_url+model or errors;
missing key → ConfigError; trailing-slash trim; comment/blank lines ignored in the keys file.
**Exit gate:** `python -m pytest scripts/tests/test_oss_model.py -q` green; full suite green.
**Commit:** `feat(tools): oss_model resolver — provider presets + non-hardcoded key resolution`

### Phase A2 — cross-platform launchers
**Touches:** `claude-harness/scripts/claude-oss.ps1`, `claude-harness/scripts/claude-oss.sh`,
`scripts/tests/test_claude_oss_launchers.py` (content-lint).
**Implement:** both launchers call the resolver (or replicate its precedence), set the `ANTHROPIC_*` env,
`exec`/`&` the real `claude` with all passthrough args, and restore/clear env on exit. No `param()` capture of
`-p` in PowerShell (learned bug: use `$args`). Accept `claude-oss <provider> [claude args…]` and support a
`claude-glm` convenience alias.
**TDD (content-lint, no live claude):** assert each launcher sets `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`,
restores env, passes args through, and NEVER writes a key to stdout.
**Exit gate:** suite green; manual smoke `claude-oss glm -p "say ok"` documented (HUMAN, needs a key).
**Commit:** `feat(scripts): cross-platform claude-oss / claude-glm launchers (env-restoring, key-safe)`

### Phase A3 — command doc + install path
**Touches:** `claude-harness/commands/use-model.md` (new), `claude-harness/commands/setup-project-ai.md`
(add an install step or a documented one-liner), `docs/guide/providers-and-keys.md` (replace the personal
path with the `CLAUDSTER_KEYS_FILE` story) + mirror to `E:\Projects\docket\web\src\help\providers-and-keys.md`.
**Implement:** `/claudster:use-model` documents the lanes, the launchers, the key resolution, and exit behavior.
`setup-project-ai` installs (or prints) the profile function so `claude-glm` works from anywhere.
**ALSO in A3 — the `.claudster/` artifacts convention (user request 2026-07-15):** make `.claudster/` the
default home so nobody re-specifies it. `setup-project-ai` scaffolds `.claudster/{plans,prd,kb,prompts,reviews}`
and writes a CLAUDE.md convention block: *"Working artifacts default to `.claudster/`: a plan →
`.claudster/plans/`, a PRD → `.claudster/prd/`, the KB → `.claudster/kb/`, a prompt → `.claudster/prompts/`,
a review → `.claudster/reviews/`. Interpret unqualified references accordingly; never scatter these to the
repo root or `.github/`."* This makes the rule part of every project's CLAUDE.md that agents read each session.
**Exit gate:** `validate_pool.py` OK (new command discovered); the CLAUDE.md convention block is present in the
setup template; suite green.
**Commit:** `feat(commands): /claudster:use-model + setup install; genericize the key path in the guide`

### Phase A4 — Ship Track A
`validate_pool.py` + full suite + bare `junai-push`; append a dated section to `docs/analysis/IMPL-STATUS.md`.
**Commit:** `docs: model-switching shipped as a first-class claudster feature`

---

## Track B (#1) — claudster public-readiness (docket = team-usable only)

**Goal:** claudster can be published publicly with no legal ambiguity and no leaked internal data. docket is
**explicitly out of scope for public release**; only verify the wider team can use it.

**Decision required from the user (BLOCKER for B1):** license choice. **Recommendation: MIT** (permissive,
simplest for a tools/harness project); Apache-2.0 if patent-grant matters. Do not guess — confirm before B1.

### Phase B1 — LICENSE + public README + genericize
**Touches:** `LICENSE` (new, root), `README.md` (a public-facing intro/install/quickstart/license section),
`docs/guide/*` (strip any remaining personal/internal specifics).
**Exit gate:** LICENSE present; README renders; no `C:\Users\<name>` paths in shipped docs.
**Commit:** `docs: add LICENSE + public README + genericize the guide for open distribution`

### Phase B2 — privacy sweep (audit + reclassify/genericize)
**Touches:** an audit report `docs/analysis/PUBLIC-READINESS.md` (new); `.github/tools/pool-validator/`
denylist/manifest as needed; `validate_pool.py` privacy scan (extend if it misses a pattern).
**Implement:** grep the *exported* pool (per target profile, not the whole source tree) for internal markers
(`vmie-`, hostnames like `iegbcoppoc02`, personal identifiers, the `enterprise-dashboard` recipe, the VMIE
handoff). For each hit: (a) genericize it, or (b) confirm it's classified **private** and excluded from the
public export — then prove it with `export_runtime_resources.py` + a grep of `dist/runtime-resources/claude`.
Record every decision in the report. Add any missed pattern to the privacy scanner so it can't regress.
**Exit gate:** `validate_pool.py --profile claude` privacy scan clean; a grep of the exported `claude` bundle
shows zero internal markers; report committed.
**Commit:** `chore(privacy): public-export sweep — internal refs genericized or confirmed private`

### Phase B3 — docket "team-usable" checklist (lighter, no public release)
**Touches:** `docs/analysis/PUBLIC-READINESS.md` (a docket section) + any doc gaps found.
**Implement:** verify the wider team can actually use docket: the Help page onboards them (built), auth works
for team members (NTLM/SSO), the board URL + access are documented, and the "how to enable agents" path is
clear. This is enablement, NOT open-sourcing docket. List anything blocking a teammate from logging in and
running a board; fix doc gaps; file code gaps as follow-ups.
**Exit gate:** a teammate could go from "given the URL" → "using a board" using only the docs.
**Commit:** `docs: docket team-usability checklist + gaps`

### Phase B4 — publish decision (HUMAN)
Summarize readiness; the user decides whether/where to publish claudster publicly (public GitHub repo vs the
existing marketplace mirror). No auto-publish in this track.

---

## Track C (#3) — Cross-vendor code-review in the pipeline

**Goal:** the Implement lane's **existing** review gate can run on a *different vendor* (DeepSeek via the
already-built `oss_review.py`) for real blind-spot diversity — the review is the genuine need, not per-phase
quota routing (explicitly **out of scope**).

### Phase C1 — investigate (no code)
**Answer, with evidence, in a short note (`.claudster/reviews/` or the plan itself):**
1. Confirm docket's Implement lane already runs a code-review gate (expected: yes — `runner._review_prompt`,
   `review_cmd`, `REVIEW:` verdicts).
2. Do `feature-plan` / `golden-plan` emit a review *phase* inside the plan itself, or is review only the
   pipeline gate? (Locate the skills — check `.github/skills/**` and `claude-harness/commands/` for
   `feature-plan`/`golden-plan`.)
3. Confirm the value is "same review, different vendor" (diversity), and that `oss_review.py` can emit the
   claude-shaped JSON the runner expects.
**Exit gate:** findings recorded; decide whether C3 (plan-skill change) is needed at all.

### Phase C2 — cross-vendor review gate wrapper (docket)
**Repo:** `E:\Projects\docket`, branch `feat/cross-review-gate` off `main` (**NEVER push docket main — it
deploys**).
**Touches:** `tools/cross_review_gate.py` (new — or reuse claudster's `oss_review.py`), `tests/…` (one
integration test with a stubbed provider). **Implement:** accept the claude-style argv the runner passes
(`-p <prompt> --output-format json …`), extract the prompt, run `oss_review.py` (provider from
`agent_track` config/env, default DeepSeek), emit a claude-shaped envelope
`{"is_error": false, "result": "…REVIEW: CLEAN|BLOCKING"}` on stdout. Config: `agent_track.review_cmd` →
a launcher for this script. This is `codex-integration.md` Phase 5, provider-agnostic.
**Exit gate:** an Implement-lane run (fake implement + THIS gate with a stubbed provider) parses the verdict;
docket suite green (`uv run --extra dev pytest -q`).
**Commit:** `feat(agents): provider-agnostic cross-vendor review gate for the Implement lane`

### Phase C3 — (conditional) teach the plan skills to name the cross-review gate
Only if C1 shows plans should carry it. Add **prose** guidance to `feature-plan`/`golden-plan` that a
cross-vendor review runs at the gate (not machine-actionable per-phase tags — there is no per-phase executor,
so tags would be cargo-cult). **Commit:** `docs(skills): note the cross-vendor review gate in plan output`

### Explicitly OUT OF SCOPE
Per-phase model routing inside a single `/implement` run (would require spawn-per-phase orchestration; the
user confirmed quota-saving isn't the need). If it ever becomes one, it's a separate docket-runner plan.

---

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\oss-model-lanes-and-public-readiness.md fully, then
execute Track A, then B, then C — IN THAT ORDER, not before the prior track's Ship phase is green. Tracks A
and B run in E:\Projects\claudster-source; Track C Phase C2 runs in E:\Projects\docket on branch
feat/cross-review-gate (create from main; NEVER push docket main — it deploys prod). Rules: TDD (RED tests
first); full suite after each phase (claudster: python -m pytest -q --import-mode=importlib + validate_pool.py;
docket: uv run --extra dev pytest -q); commit per phase with the plan's commit message, only files that phase
touches; update this plan's phase headings with ✅ + hash. STOP and ask the user for the license choice before
Track B Phase B1 (the single permitted question). Bare junai-push allowed after each claudster track.
```

## Provenance
Drafted 2026-07-15 at the user's request, sequencing three tracks they prioritized: make model-switching a
real, easy claudster feature (#2); make claudster public-ready while keeping docket team-only for now (#1);
wire cross-vendor code-review into the pipeline gate — the genuine need over per-phase quota routing (#3).
Builds on the shipped `oss_review.py` + `/claudster:cross-review` and supersedes `codex-integration.md`
Phase 5.
