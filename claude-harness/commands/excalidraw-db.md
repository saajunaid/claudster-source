---
description: Turn a SQL artifact into an Excalidraw diagram for a design review / ARB pack / slide — higher-level, drag-the-boxes format
argument-hint: [file path | object name | pasted SQL]
---

# /excalidraw-db — diagram a SQL artifact as Excalidraw

Explain a SQL artifact as an **Excalidraw** diagram — for a design review, an ARB pack, or a slide deck,
anywhere someone needs to drag boxes around rather than read a text file. For a git-tracked reference
diagram, prefer `/mermaid-db` instead.

Input: **$ARGUMENTS**

## Do this

Load and follow the **`db-diagram`** skill; produce the Excalidraw output specifically. In short:

1. **Get the SQL** — same resolution as `/mermaid-db` (file / DB object via MCP or read-only `sqlcmd` /
   context / pasted). Multiple objects → ONE diagram of their relationships.
2. **Extract deterministically** — run the skill's `scripts/sql_to_graph.py` for the typed node/edge graph.
3. **Draw via the `excalidraw` skill** — load it and hand it the graph. It writes `.excalidraw` JSON
   directly (no MCP server needed). **Layout: left-to-right data flow** — sources left, transform/staging
   middle, outputs/consumers right; group related nodes; keep it deliberately **higher-level** than the
   Mermaid version (this is for a conversation, not a reference).
4. **Narrate + caveat** — include the business context and the execution-plan caveat (verbatim, per the
   skill).

## Rules (from the skill — non-negotiable)

- **Read-only.** Never run DDL/DML.
- **Never guess schema.** Mark anything inferred-from-SQL-only.
- **Don't maintain both formats for one artifact.** If a Mermaid diagram already exists for this object,
  say so and ask: a one-off review copy, or a replacement?
