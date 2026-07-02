# DOC-MAP — claudster-source code knowledge index (the KB)

> **What this is:** the curated index of the docs that matter for understanding *this codebase* — one
> line each: what it is and when to read it. A router, not a summary; detail lives in the linked docs.
> KB notes live beside this file in `.claudster/kb/`. You may also link any other code-relevant doc
> from here (a key design doc, a runbook) — but this is for **code-relevant** docs, not every file.
>
> **How to use it:** when a task touches an area, open the doc(s) for it first. Read heavy docs via a
> dispatched subagent that returns only the conclusion, so the main thread's context stays lean.
>
> **Discipline:** kept honest by [`check_doc_coverage.py`](../../claude-harness/scripts/check_doc_coverage.py)
> — every link here must resolve (a link to a missing file is a **hard failure**), and a KB note
> (`.claudster/kb/*.md`) that isn't indexed here **warns**. It does NOT police the wider repo docs.

## Read first
1. [claude-harness/README.md](../../claude-harness/README.md) — the harness: agents, commands, hooks, and the memory model.
2. The entries below, by area.

## Knowledge base (`.claudster/kb/`)

| Doc | What / when to read |
|---|---|
| [harness-memory.md](harness-memory.md) | The four-layer memory model (relay · dream · KB · cross-repo), how the hooks wire it, and what's automatic vs curated. |

## Other key code-relevant docs

| Doc | What / when to read |
|---|---|
| [README.md](../../README.md) | Repo overview — what claudster is, install, two-plugin skill tiering. |
| [MIGRATION.md](../../MIGRATION.md) | Public-source migration / cutover notes and history. |
| [claude-harness/README.md](../../claude-harness/README.md) | Canonical harness layout, Phase-0 design rules, model-portability seam. |

---

*Governed = `.claudster/kb/*.md` only (must be indexed here). The wider repo docs are the project's
own documentation and are intentionally not policed.*
