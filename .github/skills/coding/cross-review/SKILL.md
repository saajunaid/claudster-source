---
name: cross-review
description: Cross-vendor code review — have a different vendor's model (DeepSeek/GLM/any OpenAI-compatible endpoint) review the current diff to catch bugs a same-vendor reviewer misses. Use after a phase is green and before commit/merge, or for a second opinion on a risky diff.
---

# Cross-Review — a second-vendor set of eyes on your diff

A different vendor's model has different blind spots. Claude reviewing Claude's diff shares those
blind spots; a **DeepSeek** (or GLM, or any OpenAI-compatible) reviewer catches a different class of
issue. This skill runs that second reviewer over the current changes and acts on its verdict.

## When to use
- After a phase is green, **before** you commit or merge.
- On a risky diff (auth, crypto, data-touching, concurrency) where a second opinion is cheap insurance.
- NOT a replacement for the in-repo `/claudster:code-review` — this is the *cross-vendor* complement.

## Prerequisites (one-time)
Set three env vars (the tool defaults to DeepSeek, the cheapest + most architecturally distinct-from-Claude
option; a review costs well under a cent):
```
REVIEW_API_KEY   = <your provider key>              # REQUIRED
REVIEW_BASE_URL  = https://api.deepseek.com         # default; or GLM/OpenRouter/OpenAI-compatible
REVIEW_MODEL     = deepseek-chat                     # default; e.g. glm-4.6, or an OpenRouter id
```
To point at GLM instead: `REVIEW_BASE_URL=https://api.z.ai/api/coding/paas/v4`, `REVIEW_MODEL=glm-4.6`.

## How to run
From the repo root (the tool ships at `.github/tools/oss_review.py`):
```
python .github/tools/oss_review.py                       # review the working tree (staged+unstaged)
python .github/tools/oss_review.py --range origin/main..HEAD   # review a branch's commits
```
Optional flags: `--cwd <repo>`, `--base-url <url>`, `--model <id>` (override the env).

## Interpret the exit code
- **0 — REVIEW: CLEAN** → no blocking issues. Proceed.
- **1 — REVIEW: BLOCKING** → the reviewer found blocking issues. **Read the printed findings, then FIX
  each blocking item** (or, if you judge one a false positive, state explicitly why it's safe to ignore).
  Re-run until CLEAN.
- **2 — error** → no verdict parsed, a git failure, or an endpoint/parse failure. Read stderr; do not
  treat this as CLEAN — investigate.
- **3 — misconfigured** → `REVIEW_API_KEY` is unset. Set it (see Prerequisites) and re-run.

## Rules
- This is a **read-only second opinion** — the tool never edits, commits, or pushes. YOU apply fixes in
  the main thread after reading the findings.
- Treat exit 2/3 as blocking-unknown, never as approval (the tool is fail-closed by design).
- Different vendor ⇒ different style; weigh its findings on merit, don't cargo-cult them.
