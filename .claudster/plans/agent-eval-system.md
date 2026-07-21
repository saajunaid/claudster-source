---
type: plan
status: draft
feature: agent-eval-system
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-21T00:00:00Z
Creating Model: claude-opus-4-8
---

# Agent-Eval System — keep claudster's skills/agents/plans measurably improving over time

## The question this answers

"How do we evaluate our agents, skills, plans, etc. so they keep improving over time — is this realistic,
and did Hermes build it?"

**Short answers, up front:**
- **Realistic? Yes — the load-bearing half is proven, and claudster is unusually far along.** ~60% of
  the primitives already exist in this repo (see *What already exists*). This is not a from-scratch build.
- **Did Hermes build it? It built the proven half.** Nous Research's Hermes Agent ships a per-skill YAML
  test-suite harness gated on a weekly cron that **blocks a skill upgrade if it regresses** — exactly the
  "golden gate" below. That half is real, boring, and buildable now.
- **The novel half — learning from real usage — is genuinely research-grade and must earn trust.** Nous's
  own published finding is that agent self-improvement **does not transfer across domains** (a skill tuned
  on research tasks doesn't help code review). So the usage-signal half starts as *measurement and
  prioritization*, never auto-mutation, until the data says otherwise.

## Goal

A closed loop where every reusable claudster artifact (skills first, then subagents, commands, plans) has
a **quality baseline that can only go up**:

```
  real usage signals  ──▶  prioritize which artifacts to eval/improve
        (Dream Memory)          │
                                ▼
  golden eval suites  ──▶  score an artifact against verifiable expectations
   (skill-creator harness)      │
                                ▼
  release gate         ──▶  block any change that regresses a baseline
   (validate_pool)             │
                                ▼
  improve loop         ──▶  propose a better version (human-approved), commit new baseline
   (run_loop.py)
```

The user chose the **hybrid: golden gate + usage signals** architecture. This plan builds it in that
dependency order — measurement, then gate, then loop — so each phase is independently valuable and the
riskiest part (learning from usage) ships last, on top of a trustworthy floor.

## Why now

- claudster is going public (Track B) and portable across harnesses (toolbox-portability). Both multiply
  the blast radius of a bad skill edit: a regression now ships to every install on every harness. A gate
  that catches "this description change dropped the trigger rate from 0.9 → 0.4" before publish is the
  difference between a plugin that compounds in quality and one that rots.
- **140 skills, 0 eval sets, harness wired into no gate.** The tooling exists but is inert — nobody runs
  it, nothing enforces it. The gap is integration and coverage, not invention.

## What already exists (the honest inventory — build on this, don't reinvent)

| Primitive | Where | What it does | Gap |
|---|---|---|---|
| **Trigger eval** | `.github/skills/workflow/skill-creator/scripts/run_eval.py` | Golden `should_trigger` set → runs `claude -p` per query → measures whether the skill's *description* causes Claude to load it. The **routing** dimension. | Author-run, manual, per-skill. Not systematic, not gated. |
| **Behavioral eval** | `skill-creator/references/schemas.md` `evals.json` (`{prompt, expected_output, expectations[]}`) + grader agents (`analyzer`/`comparator`/`grader`) | Golden task cases → run the skill → an LLM grader checks each verifiable `expectation`. The **quality-of-guidance** dimension, tracked as `expectation_pass_rate`. | **0 of 140 skills have an `evals.json`.** The format + graders exist; the content doesn't. |
| **Improve loop** | `skill-creator/scripts/run_loop.py` | eval → `improve_description.py` → re-eval, with **train/test split** (anti-overfit) and `history.json` version tracking (`v0→v1→v2`, pass-rate per version, `is_current_best`). | Only improves the *description* (routing), not the skill body. Not scheduled, not gated. |
| **Reporting** | `aggregate_benchmark.py`, `generate_report.py`, `eval-viewer/` HTML | Aggregates results, renders an HTML review. | Not surfaced anywhere durable. |
| **Usage capture** | `claude-harness/scripts/dream_capture.py` + `dream_memory.py`, fired by `session_end.py` | Per-repo `.claudster/memory.jsonl` of deterministic facts: `failure-mode`, `rejected-approach`, `repo-fact`, `workflow-success`, with `hitCount`. | Captures *facts*, **not which skill/agent was active** or the session's outcome. No link from a fact to the artifact that was in play. |
| **Session usage log** | `session_end.py` → `.claudster/usage-log.jsonl` | Per-session tokens/cost/models. | No artifact attribution. |
| **Publish gate** | `validate_pool.py` (+ `validate_agents.py`) | Structural/privacy/frontmatter gates run before every `junai-push`. | The natural home for an eval-regression gate — but has no eval check today. |
| **Headless executor** | docket's `runner.py` (out of scope here) | Runs `claude -p` agent jobs at scale with a review gate. | A future option to offload the eval batch; **not built in this plan** (docket is owned by another session). |

**The synthesis:** claudster already has a behavioral-eval *format*, a trigger-eval *runner*, an improve
*loop*, a usage *capture*, and a publish *gate* — five of the six pieces. What's missing is (1) **content**
(eval sets), (2) **integration** (wire the harness into the gate), (3) **attribution** (connect usage
signals to the artifact that produced them), and (4) **coverage beyond skills** (agents/commands/plans).

## Architecture — the two halves and how they close the loop

### Half 1 — the golden gate (proven; the trustworthy floor)

For each artifact, a committed **baseline score** derived from its golden eval set. A change to that
artifact must not drop the score below baseline, or the publish gate fails. Concretely:

- **Skills** reuse the existing harness verbatim: `run_eval.py` for the routing score
  (`trigger_accuracy`) and `evals.json` + graders for the behavioral score (`expectation_pass_rate`).
- **Baselines are committed in-repo** (a `baselines.json` per skill, or one pool-level
  `.github/eval/baselines.json`), so the gate compares "this PR's score" vs "the last committed score" —
  a pure regression check, no external state, reproducible on any checkout.
- **The gate degrades gracefully:** a skill with no eval set is *reported as uncovered* (a warning +
  a coverage number), never a hard failure — same fail-open-on-absence discipline `check_doc_coverage.py`
  already uses. Only a *regression on a skill that HAS a baseline* blocks the publish. This lets coverage
  grow incrementally without ever blocking a legitimate ship.
- **Non-determinism is handled by thresholds, not single runs:** LLM grading is noisy, so a "score" is a
  pass-rate over N cases with a regression band (e.g. block only on a drop > 1 stderr, not a 1-case
  flake). The comparator/grader agents already exist for this.

This half is exactly what Hermes ships and is buildable with the code already in the repo.

### Half 2 — usage signals (novel; measurement first, never auto-mutation)

Real sessions are the ground truth the golden suites approximate. Two problems the golden gate can't see:
1. **Which skills matter** — where should scarce eval-writing effort go? (High-traffic + low-coverage.)
2. **Which skills underperform in the wild** — a skill can trigger perfectly and still leave sessions
   churning (repeated `rejected-approach` facts, review-gate failures, red-stays-red).

The signal source is **Dream Memory, extended with artifact attribution**. Today a fact records *what*
happened (a command failed); it doesn't record *which skill/agent was loaded* when it happened. Add a
lightweight, privacy-safe attribution: at session end, record which skills/agents the transcript shows
were activated, alongside a coarse outcome (did it end red→green? did a review pass? how many
rejected-approach churns?). Aggregate per-artifact into a **health signal**.

**Crucial discipline (from Nous's own non-transfer finding):** this signal **prioritizes and surfaces**,
it does **not** gate and does **not** auto-edit. It answers "write evals for `fastapi-dev` next — it's in
40% of backend sessions and 3 of them churned" — a work-list, not a verdict. Auto-improvement (running
`run_loop` unattended) is Phase 4, gated by the golden suite AND human review, and only after the signal
has demonstrably predicted real quality on a held-out set.

### How they close the loop

`usage signal (weak + high-traffic skill) → author/loop writes or expands its golden eval → run_loop
proposes an improvement → it must clear the golden gate → commit with a raised baseline`. Each turn of the
crank raises a floor that can't fall. The usage half aims the effort; the golden half guarantees the
direction is up.

## Phased implementation

Measurement → gate → coverage → loop. Each phase ships value alone; stop after any phase and the repo is
better off.

### Phase 0 — Measurement & attribution (no gating, build the data)
**Touches:** `dream_capture.py` (add skill/agent activation + coarse outcome to the capture),
`scripts/eval/coverage_report.py` (new — inventory which skills have eval sets), tests.
**Implement:**
- Extend session-end capture to attribute activated skills/agents (parse the transcript for skill loads /
  subagent dispatches) and a coarse session outcome, written as a new Dream-Memory-adjacent signal
  (`.claudster/artifact-signals.jsonl`, per-repo, privacy-scrubbed by the existing `redact`). Fail-open,
  never slows a Stop.
- A `coverage_report.py` that prints, for all 140 skills: has-eval-set? trigger-baseline? behavioral-
  baseline? — the honest starting scoreboard.
**Exit gate:** the coverage report runs and shows 0/140; a scratch session records artifact-attributed
signals; full suite + `validate_pool` green. **No behavior gated yet.**
**Commit:** `feat(eval): artifact-attributed usage signals + skill eval-coverage report`

### Phase 1 — The golden gate for skills (the Hermes half)
**Touches:** `scripts/eval/run_pool_evals.py` (new — batch-runs whatever eval sets exist, records scores),
`.github/eval/baselines.json` (new — committed baselines), a new `validate_pool.py` check, tests.
**Implement:**
- `run_pool_evals.py`: for each skill with an `evals.json` and/or a `should_trigger` set, run the existing
  harness, emit `{skill, trigger_accuracy, expectation_pass_rate}` with N-run averaging.
- A `validate_pool.py` check `check_eval_regression`: compares fresh scores to `baselines.json`; **blocks
  only a regression beyond the noise band on a skill that has a baseline**; reports coverage % as info;
  never fails on an uncovered skill. Mirrors the graceful-degradation of the existing checks.
- Backfill **golden eval sets for the top ~10 highest-traffic skills** identified by Phase 0's signals
  (not all 140 — prioritized). Record their baselines.
**Exit gate:** editing a covered skill's description to a deliberately worse one fails `validate_pool`;
an uncovered skill still passes; coverage % reported. `junai-push` path unaffected for unchanged skills.
**Commit:** `feat(eval): pool eval-regression gate — a covered skill can't ship a regression`

### Phase 2 — Behavioral coverage + the reviewable report
**Touches:** more `evals.json` backfill; wire `aggregate_benchmark.py`/`generate_report.py` into
`run_pool_evals.py`; a committed `docs/analysis/EVAL-STATUS.md` snapshot.
**Implement:**
- Expand behavioral eval sets from the top-10 toward top-30 (traffic-ordered). Each `evals.json` gets
  3–5 verifiable `expectations` per the existing schema.
- Emit a durable HTML/markdown eval report so quality is *visible* (like the coverage scoreboard, but with
  scores and trends). Commit a snapshot to `docs/analysis/EVAL-STATUS.md`.
**Exit gate:** ≥30 skills covered with behavioral baselines; the report renders and is committed; gate
still green.
**Commit:** `feat(eval): behavioral eval coverage to top-30 skills + visible eval report`

### Phase 3 — Extend the pattern beyond skills
**Touches:** eval-shape definitions for the other artifact types; `validate_agents.py` for agents.
**Implement — each artifact type gets a fit-for-purpose eval shape (do NOT force the skill shape):**
- **Subagents** (`.github/agents/*.md`): eval = "given a task, does the subagent return the correct
  *structured verdict/contract*?" (e.g. code-reviewer returns a well-formed verdict + issue list). The
  contract already exists (`CONTRACT-REFERENCE.md`); the eval checks conformance + correctness on golden
  tasks.
- **Commands** (`claude-harness/commands/*.md`): mostly thin routers — eval their *routing* (does the
  command load the right skill / produce the right artifact path), reusing the trigger harness.
- **Plans** (`golden-plan`/`feature-plan` output): eval = "does `preflight` pass the generated plan
  against a real fixture codebase?" — a plan that references nonexistent files/symbols fails. This reuses
  the existing `preflight` skill as the grader; no new grader needed.
**Exit gate:** at least one agent, one command, one plan-skill has a baseline and is gated; contract doc
per type.
**Commit:** `feat(eval): eval shapes + baselines for subagents, commands, and plan output`

### Phase 4 (later, human-gated) — close the improvement loop
**Blocked on:** Phases 0–2 trustworthy (the usage signal has predicted real quality on a held-out check).
**Implement:**
- A scheduled (opt-in) job that, for the N weakest covered skills by usage signal, runs `run_loop.py` to
  propose an improved version, and opens it as a **branch/PR for human review** — never auto-committed.
  The proposal must clear the golden gate to even be offered.
- Optionally offload the eval batch to docket's runner (headless `claude -p` at scale) — **coordinate with
  the docket owner; not built here.**
**Exit gate:** one human-approved, loop-proposed skill improvement lands with a raised baseline.
**Commit:** `feat(eval): opt-in improve-loop proposals (human-approved) for weakest skills`

## Realism & risks (the honest part)

- **Cost.** Running `claude -p` across 140 skills × N cases is expensive. Mitigation: the usage signal
  *prioritizes* — you eval the 30 skills that matter, not all 140; N is small (3–5); the gate only re-runs
  evals for *changed* skills, not the whole pool, on a normal push.
- **LLM-grader non-determinism.** A single grading run is noisy. Mitigation: pass-rate over N with a
  regression *band* (block on a real drop, not a flake); the comparator/grader agents already encode this.
- **Overfitting to the eval set.** Mitigation: the train/test split already in `run_loop.py`; never
  optimize on the test half.
- **The non-transfer finding (Nous).** Self-improvement doesn't generalize across domains. Mitigation:
  keep every eval set domain-specific to its skill; expect no cross-skill learning; the usage signal
  targets effort, it doesn't claim a universal reward.
- **Attribution noise.** Parsing a transcript for "which skill was active" is imperfect. Mitigation: it
  feeds prioritization only (Half 2), which is allowed to be fuzzy; it never gates.
- **Gate friction.** A flaky gate that blocks legitimate ships erodes trust fast. Mitigation: fail-open on
  absence, regression-band not exact-match, and a documented `--force`/override with an audit line —
  exactly the pattern `junai-release`'s content-diff gate already uses.

## Non-goals

- **No auto-mutation of shipped artifacts.** The loop *proposes*; a human *approves*. (Phase 4, gated.)
- **No universal reward model / RL.** This is regression-gated golden evals + usage-signal prioritization,
  not policy learning.
- **No reinvention.** The skill-creator harness, Dream Memory, and `validate_pool` are the substrate; this
  plan is integration + content + attribution, not new frameworks.
- **No docket work in this plan.** docket as an eval executor is a noted future option, coordinated
  separately.

## Prompt (to execute this later)

```
Read .claudster/plans/agent-eval-system.md fully. Execute Phases 0→1→2 in order in E:\Projects\claudster-
source (Phase 3/4 are separate follow-ups). Build ON the existing skill-creator harness
(.github/skills/workflow/skill-creator/) and Dream Memory (claude-harness/scripts/) — integration and
content, not new frameworks. TDD every script; after each phase run
`python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q --import-mode=importlib && python
validate_pool.py`. The eval-regression gate must fail-OPEN on an uncovered skill and only block a real
regression on a covered one. Commit per phase, only files it touches. Do NOT auto-edit any shipped skill.
```
