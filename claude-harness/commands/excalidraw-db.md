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
2. **Generate the `.excalidraw` directly** — run the skill's extractor with
   `scripts/sql_to_graph.py --file <path> --format excalidraw` and save the output as a `.excalidraw` file.
   The generator produces the layout deterministically: **left-to-right data flow** (sources left,
   filters/transform middle, result/projection right), grid-aligned boxes, and **container-bound text that
   auto-wraps and stays inside every box**. No separate drawing skill, no MCP server.
3. **Optional no-app preview** — for a shareable page, `--format html` emits a self-contained HTML (inline
   SVG, light/dark toggle, **default light**, no external requests); `--format svg` emits a standalone SVG.
4. **Narrate + caveat** — include the business context and the execution-plan caveat (verbatim, per the
   skill).

## Rules (from the skill — non-negotiable)

- **Read-only.** Never run DDL/DML.
- **Never guess schema.** Mark anything inferred-from-SQL-only.
- **Don't maintain both formats for one artifact.** If a Mermaid diagram already exists for this object,
  say so and ask: a one-off review copy, or a replacement?
