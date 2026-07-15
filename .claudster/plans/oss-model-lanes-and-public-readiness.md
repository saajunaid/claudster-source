---
type: plan
status: draft
feature: oss-model-lanes-and-public-readiness
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-15T00:00:00Z
Creating Model: claude-opus-4-8
---

# OSS model lanes → public-readiness → cross-vendor review

Three tracks, **executed in this order** (the user set the sequence). Each is independently shippable;
do not start the next until the prior track's Ship phase is green.

- **Track A (#2) — Model-switching as a real, easy-to-use claudster feature.** Today the only way to run a
  Claude Code session on GLM is a *personal* machine-local wrapper (`C:\Users\jshaik\Documents\claude-glm.ps1`)
  that hardcodes a key path. Make it a first-class, cross-platform, teammate-usable capability shipped in the
  plugin.
- **Track B (#1) — Make claudster public-ready.** Add a LICENSE, sweep internal references, genericize the
  guide. docket is **not** being made public now — only confirm the *wider team* can use it.
- **Track C (#3) — Cross-vendor code-review in the pipeline.** The real need isn't per-phase quota-saving;
  it's running the *review* on a different vendor (DeepSeek) for genuine blind-spot diversity. The Implement
  lane already HAS a review gate — point it (optionally) at `oss_review.py`.

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
