# Known limits — KB index & Dream Memory

Accepted trade-offs in the KB-index (`check_doc_coverage.py` / `/kb`) and Dream Memory machinery.
These are **intentional** or low-severity; documented so they aren't rediscovered as "bugs."

## KB index (`check_doc_coverage.py --reindex` / `--prune`, `/kb`)

- **`--prune` only removes *table-row* dangling links.** A dangling `.md` link written in *prose*
  (not inside a `| … |` row) is still flagged by the gate but not removed by `--prune`, so
  `--prune && --check` could still fail in that rare case. Doc-map links live in tables by
  convention; fix a prose dangling link by hand. *(Deliberate — pruning prose is unsafe.)*
- **`--reindex` re-discovers "Other key docs" only on *create*.** Adding a `docs/…` file after the
  DOC-MAP exists won't auto-link it (the discovery runs in the fresh-scaffold path). The KB-notes
  table (`.claudster/kb/*.md`) *is* kept current on every reindex; the "Other" table is a one-time
  convenience you then curate. Link a new external doc by hand.
- **Only top-level `.claudster/kb/*.md` is governed/indexed.** Notes nested in
  `.claudster/kb/<subdir>/*.md` are neither policed by the gate nor auto-indexed (both
  `GOVERNED_GLOBS` and `kb_note_rows` use a non-recursive `*.md`). Keep KB notes flat.
- **`--prune` has no `--dry-run` at the script level.** It writes immediately, but only ever removes
  rows that link to *already-missing* files, and the `/kb` command shows the dangling list and
  confirms before running it. Direct CLI use is the explicit, destructive opt-in.

## Dream Memory (`memory.jsonl`)

- **Concurrent same-repo sessions can lose a fact update (last-writer-wins).** Writes are atomic
  (temp + replace) so the store never *corrupts*, but capture/consolidate is read-modify-write: two
  sessions' Stop hooks — or a `knowledge-transfer` append racing a Stop consolidate — can drop one
  side's update. Low probability (two live sessions in one repo) and self-healing (facts recur and
  reinforce). File-level locking isn't worth the cost for a decaying, best-effort store.

## See also

- `.claudster/kb/harness-memory.md` — the four-layer memory model this sits within.
- `claude-harness/scripts/check_doc_coverage.py` — the gate + reindex/prune implementation.
