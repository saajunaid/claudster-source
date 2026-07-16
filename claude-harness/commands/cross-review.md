---
description: Cross-vendor code review of the current diff — a second-vendor model (DeepSeek/GLM/any OpenAI-compatible endpoint) reviews your changes to catch bugs a same-vendor reviewer misses
argument-hint: [git range, e.g. origin/main..HEAD]
---

# /claudster:cross-review — a second-vendor set of eyes on your diff

Run a cross-vendor review of the current changes with a DIFFERENT model family than the one that wrote them
(default **DeepSeek** — the cheapest + most architecturally distinct-from-Claude option). Use after a phase
is green and before you commit, or for a second opinion on a risky diff. This is the *cross-vendor*
complement to `/claudster:code-review`, not a replacement.

## Prerequisite (one-time)
Set `REVIEW_API_KEY` (and optionally `REVIEW_PROVIDER` = `deepseek` | `glm` | `openrouter`). Key resolution
and provider details: see the `coding/cross-review` skill and the **Providers & keys** guide.

## Run it
The tool ships at `.github/tools/oss_review.py` (stdlib-only, no install):
```
python .github/tools/oss_review.py                    # review the working tree (staged + unstaged)
python .github/tools/oss_review.py --range $ARGUMENTS  # review a git range, e.g. origin/main..HEAD
```
Optional: `--provider glm`, `--base-url <url>`, `--model <id>` (env always overrides the preset).

## Interpret the exit code
- **0 — REVIEW: CLEAN** → no blocking issues. Proceed.
- **1 — REVIEW: BLOCKING** → read the printed findings, then **FIX each blocking item** (or explicitly
  justify why one is a false positive). Re-run until CLEAN.
- **2 — error** → no verdict parsed, or a git/endpoint failure. Read stderr; do NOT treat as clean.
- **3 — misconfigured** → `REVIEW_API_KEY` is unset. Set it (see Prerequisite) and re-run.

## Rules
- Read-only second opinion — the tool never edits, commits, or pushes. YOU apply fixes in the main thread.
- Treat exit 2/3 as blocking-unknown, never as approval (the tool is fail-closed by design).
- A different vendor means a different style; weigh its findings on merit, don't cargo-cult them.
