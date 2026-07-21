---
name: db-diagram
context: fork
description: Turn a SQL artifact — a stored procedure, view, query, .sql file, or table name — into a diagram that explains it to a human. Use when the user says "diagram this query/proc/view/schema", "explain this SQL visually", "draw the ER diagram", "show me the data flow of this stored proc", "/mermaid-db", or "/excalidraw-db". Produces Mermaid (default, git-diffable) or Excalidraw (for design reviews). Read-only — never touches the database.
---

# db-diagram — explain SQL as a diagram

Take a SQL artifact and produce a diagram that explains it to a human. Two output formats, one shared
extraction: **Mermaid** (default — plain text, diffs cleanly, renders in VS Code/Gitea, regenerable) and
**Excalidraw** (for a design review / ARB pack / slide — someone drags boxes around).

The structure is extracted **deterministically** by `scripts/sql_to_graph.py` (a real sqlglot-based
parser); you (the model) add the **business narration** on top. Never hand-derive the node graph when the
script can run — its whole value is reproducibility.

## Two non-negotiable safety rules

1. **Never write to the database.** Read-only by definition — no DDL, no DML, not even in a rolled-back
   transaction. The extractor only ever parses SQL *text*.
2. **Never guess schema.** Inspect the actual tables/columns before diagramming. If you can't reach the
   database, diagram only what's provable from the SQL text and **mark inferred elements clearly**.

## Step 1 — get the SQL

Resolve the argument:
- **A file path** → read that file.
- **A database object name** (proc/view/table) → look it up. Prefer a registered DB **MCP tool** if one
  is available in the session; else `sqlcmd`/`psql` **read-only**; else ask the user to paste it. Never
  guess an object's body.
- **No argument** → operate on the SQL in the current file/context, or ask.
- **Multiple objects** → diagram the **relationships between them**, in ONE diagram — not one diagram each.

## Step 2 — run the deterministic extractor

```bash
python <skill-dir>/scripts/sql_to_graph.py --file <path> --json     # full graph JSON
python <skill-dir>/scripts/sql_to_graph.py --sql "<SELECT ...>"      # just the Mermaid block
```
`--dialect` defaults to `tsql`; pass `postgres`/`mysql`/etc. for other engines. Requires `sqlglot`
(`pip install sqlglot` — pure-Python, no DB driver). **If sqlglot is absent** the script exits with an
actionable message; then hand-parse the SQL yourself and mark every inferred element (per safety rule 2).

The extractor classifies the input and picks the diagram type:

| Input | Diagram type | Extractor emits |
|---|---|---|
| `CREATE TABLE` / schema DDL | `erDiagram` | entities, columns, PK/FK, FK relationships |
| A query, proc, or CTE chain | `flowchart TD` | tables `[(T)]`, CTEs `{{CTE: name}}`, joins (with keys, on the edge), filters as distinct nodes, final projection `[/…/]` |
| An API/service path ending in a DB call | `sequenceDiagram` | *not structural — you build this from the code path; the extractor won't* |
| A status/lifecycle column | `stateDiagram-v2` | *not structural — you build this from the state values* |

The `sequenceDiagram`/`stateDiagram-v2` cases are judgement, not parsing — build those yourself and say so.
For the two structural cases, **trust the extractor's graph**; your job is narration, not re-deriving nodes.

The extractor returns `confidence` (`high` | `partial`) and an `inferred` list. If `partial`, the SQL
couldn't be fully parsed — surface the `inferred` notes in the output and mark those parts.

## Step 3 — wrap it with narration (your job)

Around the extractor's Mermaid block, add:
- **Above the diagram**: one paragraph explaining what the query/proc is *for* in **business terms** (not
  a restatement of the SQL — the *why*).
- **Below the diagram**: a bulleted list of every source table with a **one-line description** of what it
  holds and why this query touches it. Inspect the real table (MCP/`sqlcmd`) for this — don't invent.
- **Traceability**: the source file path or object name, and a **generation date**.
- **This caveat, verbatim:**

  > This diagram shows the SQL as written, not the execution plan. For performance analysis use the
  > actual execution plan (SSMS Ctrl+M), which reflects what the optimiser actually chose — the two
  > diverge frequently.

## Step 4 — validate before saving

Malformed Mermaid renders as an error block — worse than no diagram. Before writing:
- Confirm the diagram **parses** (the extractor already sanitizes labels — no unescaped `"`/`[`/`]` — but
  if you hand-edited or hand-built the diagram, re-check).
- Common breakages: unescaped parentheses, quotes, and square brackets inside node labels.

## Output rules — `/mermaid-db` (the default)

- Save as a **`.md`** file. Default path `docs/diagrams/<object-name>.md`, overridable by an argument.
- **If the file already exists**, diff against it and tell the user *what changed* — don't silently
  overwrite. (Regenerating on a schema change and showing the delta is the point of Mermaid-as-text.)

## Output rules — `/excalidraw-db` (for human conversation)

Use for a design review / ARB / slide deck. Produce the `.excalidraw` via the **`excalidraw` skill** (it
writes `.excalidraw` JSON directly — no MCP server required). Load that skill and hand it the extractor's
graph.
- **Layout**: left-to-right data flow — sources left, transform/staging middle, outputs/consumers right.
  Group related nodes. Deliberately **higher-level** than the Mermaid version — this is for a conversation,
  not a reference.
- **Do not maintain both formats for the same artifact.** If a Mermaid diagram already exists for an
  object and the user runs `/excalidraw-db` on it, say so and ask: a one-off review copy, or a replacement?

## The read-only, never-guess discipline (restated because it matters)

- Never run anything that mutates the DB.
- Never assert a table's columns or relationships you haven't verified against the real schema; mark
  anything inferred-from-SQL-text-only.
- If the extractor's `confidence` is `partial` or sqlglot is unavailable, the diagram is best-effort —
  say so in the output, don't present it as authoritative.
