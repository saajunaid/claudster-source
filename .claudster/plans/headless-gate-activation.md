---
type: plan
status: draft
feature: headless-gate-activation
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-10T00:00:00Z
Creating Model: claude-opus-4-8
---

# Headless gate activation — make preflight/code-review reliable in `claude -p`

## Problem (proven live, A8.6 2026-07-08)
`/claudster:preflight` and `/claudster:code-review` are **`context: fork` SKILLS** — model-invoked, not
deterministically expanded. In headless `claude -p` runs they **intermittently fail to activate**: in one
live run the model saw the raw `/claudster:code-review <sha-range>` text, didn't recognise it, and replied
*"I don't see a specific task in your message"* — no review happened at all. Even when they DO activate,
they emit their own prose verdicts (`Result: PASS`, `Verdict: approve`) and **ignore an injected "end with
MARKER" instruction** (proven across 3+ live runs). Docket worked around this on its side (self-contained
prompts + a fail-closed verdict classifier, docket commits `406b27b`/`5859599`/`d04d7fa`); claudster itself
still ships the weakness to every OTHER headless consumer.

By contrast, **commands** (`claude-harness/commands/*.md`, e.g. `/claudster:prd`) expand deterministically
in `-p` — proven across many live runs this month.

## Current state (verified 2026-07-10)
- Gate skills live in the pool at `.github/skills/<category>/<name>/SKILL.md` (find each with
  `Glob .github/skills/**/preflight/SKILL.md` etc.). Neither `preflight` nor `code-review` SKILL.md
  contains a machine-verdict line (`grep -c "PREFLIGHT: PASS"` → 0).
- The AGENTS (`claude-harness/agents/preflight.md`, `code-reviewer.md`) DID get mandatory machine-verdict
  last-lines in v1.3.22 — but agents aren't in the slash-invocation path.
- Commands live in `claude-harness/commands/` (8 files). No `preflight.md` / `code-review.md` command exists.
- `scripts/tests/test_headless_convention.py` guards the headless convention for interview-style commands
  only (`test_headless_section_forbids_interview`); it knows nothing about gates/markers.
- Canonical markers (the contract docket's parser + classifier already accept):
  `PREFLIGHT: PASS|FAIL` and `REVIEW: CLEAN|BLOCKING` — exactly one line, nothing after it.

## Decisions
| # | Decision |
|---|---|
| H1 | **Add machine-verdict contracts to the two gate SKILLs** (mirroring what v1.3.22 did for the agents): the SKILL.md return format ends with the mandatory canonical marker line. Helps whenever the skill *does* activate. |
| H2 | **Add two new COMMANDS** — `gate-preflight.md` and `gate-review.md` — that are **self-contained** (full task + criteria inline, the skill named only as an optional methodology nudge, exactly the pattern proven in docket's `_preflight_prompt`/`_review_prompt`). Distinct names avoid any command/skill resolution ambiguity with the existing `/claudster:preflight` skill. |
| H3 | **Never rename or remove the existing skills** — interactive/model-invoked use keeps working; docket's config defaults (`/claudster:preflight`, `/claudster:code-review`) stay valid because docket's prompts are already self-contained. |
| H4 | Extend `test_headless_convention.py` so the contract can't silently regress. |

## Phases

### Phase 1 — Machine-verdict contract in the two gate skills
**Touches:** `.github/skills/**/preflight/SKILL.md`, `.github/skills/**/code-review/SKILL.md`
(locate with Glob; there may be mirrored copies under `claude-harness/skills/` — if so, the POOL copy under
`.github/skills/` is canonical and the export sync propagates it; edit the pool copy only).
**Implement:** append to each SKILL.md's return-format section (mirror the agents' wording from
`claude-harness/agents/preflight.md` end):
- preflight: *"Then, as the very last line of your output (nothing after it), emit the machine verdict:
  `PREFLIGHT: PASS` (zero blocker findings) or `PREFLIGHT: FAIL` (one or more blockers). Automated runners
  read only this line; it must exactly match one of those two forms."*
- code-review: same shape with `REVIEW: CLEAN` (empty blocking list) / `REVIEW: BLOCKING`.
**Exit gate:** `grep -l "PREFLIGHT: PASS"` finds the preflight SKILL.md; same for `REVIEW: CLEAN`;
`python validate_pool.py` → OK.
**Commit:** `fix(skills): preflight + code-review end with the canonical machine verdict line`

### Phase 2 — Self-contained gate commands
**Touches:** `claude-harness/commands/gate-preflight.md` (new), `claude-harness/commands/gate-review.md` (new).
**Implement:** each is a command with frontmatter `description` + `argument-hint` (copy the style of
`claude-harness/commands/implement.md`). Bodies are SELF-CONTAINED — do not depend on any skill activating:
- `gate-preflight.md` (`argument-hint: <path to plan.md>`): validate the plan at `$ARGUMENTS` against the
  ACTUAL codebase — file paths exist (or are marked new), symbols exist with exact names (grep them),
  API/data shapes match, dependencies installed; a claim you cannot verify is a finding. HEADLESS RULES:
  non-interactive, never ask, READ-ONLY (no code writes, no branch changes). PASS only with zero blocking
  discrepancies. End with EXACTLY one line: `PREFLIGHT: PASS` or `PREFLIGHT: FAIL`.
  Add one line: *"If a `preflight` skill is available, use its methodology."*
- `gate-review.md` (`argument-hint: [git range, defaults to the working diff]`): adversarial review of the
  diff (`git diff $ARGUMENTS`, `git show` per commit) — correctness, tests, security, conventions
  (CLAUDE.md), simplicity; classify blocking / should-fix / nit. HEADLESS RULES as above. End with EXACTLY
  one line: `REVIEW: CLEAN` or `REVIEW: BLOCKING`.
  (Port the wording from docket `src/docket/runner.py` `_preflight_prompt`/`_review_prompt` — that text is
  live-proven; keep the two docs standalone, no cross-repo reference.)
**Exit gate:** both files exist; `validate_pool.py` → OK; the skills `_registry.md` (if commands are
registered there — check how `implement.md` was registered in commit `b9461d5` and mirror it).
**Commit:** `feat(commands): /claudster:gate-preflight + /claudster:gate-review — deterministic headless gates`

### Phase 3 — Convention tests
**Touches:** `scripts/tests/test_headless_convention.py`.
**Implement (TDD — write these first, watch them fail before Phases 1–2 are complete):**
- `test_gate_commands_end_with_machine_verdict`: for each of `gate-preflight.md`/`gate-review.md`, the LAST
  non-empty content line of the body demands the exact marker pair (regex `PREFLIGHT: PASS|FAIL` etc. is
  present, and the words "EXACTLY one line" appear).
- `test_gate_skills_declare_machine_verdict`: each gate SKILL.md contains its marker pair.
- `test_gate_commands_are_self_contained`: each command body contains the words "READ-ONLY"/"read-only",
  "never ask" (case-insensitive), and does NOT require a skill (the skill sentence must say "If ... available").
**Exit gate:** `python -m pytest scripts/tests/test_headless_convention.py -q` → all pass; full suite
(`python -m pytest -q --import-mode=importlib` from repo root) → green (325+).
**Commit:** `test: headless gate convention — markers + self-containment enforced`

### Phase 4 — Live probe + publish
**Implement:**
- Live probe (2 runs each, real `claude -p`, cheap): from a scratch dir with a trivial plan file,
  `claude -p "/claudster:gate-preflight <plan>" --output-format json` (strip `CLAUDECODE` from env —
  pattern in docket `runner.py` `_guarded_env`); assert stdout's `result` contains `PREFLIGHT: PASS` or
  `PREFLIGHT: FAIL`. Same for `gate-review` against a one-line diff. If a probe shows the marker missing,
  STOP and strengthen the command wording — do not publish.
- Publish: `. .\sync.ps1; junai-push` (bare form — mirror sync + version bump only; never `-Publish`).
- Record the result in `docs/analysis/IMPL-STATUS.md` (append a dated section).
**Exit gate:** both probes show the marker; junai-push reports the version bump.
**Commit:** `docs: headless gates live-probed + published`

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\headless-gate-activation.md fully, then execute it
autonomously in E:\Projects\claudster-source. Rules: never ask a question the plan or codebase can answer;
TDD (Phase 3's tests first where practical); run the full suite (python -m pytest -q --import-mode=importlib)
and validate_pool.py after each phase; commit per phase with the plan's commit message (commit ONLY files
your phase touched — the tree may hold other sessions' edits); update this plan's phase list with ✅ + commit
hash as you go. Phase 4's junai-push (bare, never -Publish) is allowed. Live probes spend a little Claude
quota — that is expected. Stop only if a live probe fails twice after a wording fix; report what you saw.
```
