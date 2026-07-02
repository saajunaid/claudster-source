---
description: Rebuild the KB index (.claudster/kb/DOC-MAP.md) — create it if missing, index un-indexed notes, report dangling links
---

# /kb — bring the knowledge-base index up to date

Reconcile `.claudster/kb/DOC-MAP.md` (the KB index) with the notes on disk. Use this in a repo that
has the harness but no KB yet (the KB was introduced recently), or after adding/removing KB notes.

## Step 1 — locate the checker
It ships with the harness. Try, in order:
- `scripts/check_doc_coverage.py` — a project set up via `setup-project-ai` (checker copied in).
- `claude-harness/scripts/check_doc_coverage.py` — the harness source repo itself.

## Step 2 — run the reindexer
```
python <path>/check_doc_coverage.py --reindex
```
It is **additive and safe** — never deletes your rows:
- **Missing map** → creates `.claudster/kb/DOC-MAP.md` from a scaffold, pre-linking the repo's obvious
  reference docs (README, `docs/…`) and any existing `.claudster/kb/*.md` notes.
- **Existing map** → indexes any KB note that isn't yet linked (adds a row with a placeholder description).
- **Dangling links** (a linked file that's gone) → **reported, not removed** — those are yours to fix.

## Step 3 — finish by hand
Read the `[kb]` summary it printed, then:
- For each **newly auto-indexed** note, open it and replace the placeholder description with a real
  one-line "what / when to read".
- For each **dangling** link reported, fix or delete that row (the note was moved/removed).

## Step 4 — verify clean
```
python <path>/check_doc_coverage.py --check
```
Exit `0` = the index is honest (no dangling links; every note indexed). The SessionStart hook will now
surface the `[DOC-MAP]` "read the index first" pointer for future sessions in this repo.
