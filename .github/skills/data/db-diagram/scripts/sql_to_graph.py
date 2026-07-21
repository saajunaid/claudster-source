#!/usr/bin/env python3
"""Deterministic SQL -> typed-graph + Mermaid-skeleton extractor (the db-diagram skill).

This is the DETERMINISTIC half of /mermaid-db and /excalidraw-db. It parses SQL with sqlglot
(a proper AST, dialect-aware) into a stable node/edge model and renders a Mermaid skeleton with
the skill's typed-node conventions. The LLM narration layer wraps this output with business
prose, per-table descriptions, and the execution-plan caveat — but the STRUCTURE (which tables,
CTEs, joins+keys, filters) comes from here, deterministically, so the diagram diffs cleanly and
can be regenerated when the schema changes.

Two diagram types are derived structurally:
  * CREATE TABLE / DDL      -> erDiagram (entities, columns, PK/FK, FK relationships)
  * a query / proc / CTE    -> flowchart TD (tables [(T)], CTEs {{CTE: name}}, joins with keys,
                               filters as distinct nodes, final projection [/TOP.. ORDER BY../])

sqlglot is required. If it's absent, ``analyze`` raises ``SqlglotUnavailable`` with an actionable
message — the skill then falls back to LLM hand-parsing from the SQL text (marking inferred).

READ-ONLY by construction: this only parses SQL text. It never connects to or writes a database.

CLI:  python sql_to_graph.py --file query.sql [--dialect tsql] [--json]
      python sql_to_graph.py --sql "SELECT ..."           (default output: the Mermaid block)
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

try:  # sqlglot is required for structural extraction; absence is handled explicitly.
    import sqlglot
    from sqlglot import exp

    _HAVE_SQLGLOT = True
except Exception:  # noqa: BLE001
    _HAVE_SQLGLOT = False


class SqlglotUnavailable(RuntimeError):
    """Raised when sqlglot isn't importable. Carries an actionable install hint."""


def _sanitize_label(text: str) -> str:
    """Make a string safe inside a Mermaid node label: collapse whitespace and remove the
    double-quotes / brackets that break Mermaid's parser (the #1 rendering footgun)."""
    out = " ".join((text or "").split())
    return out.replace('"', "'").replace("[", "(").replace("]", ")")


def _node_id(prefix: str, name: str, seen: dict[str, int]) -> str:
    base = "".join(c if c.isalnum() else "_" for c in name.lower()) or "x"
    key = f"{prefix}_{base}"
    seen[key] = seen.get(key, 0) + 1
    return key if seen[key] == 1 else f"{key}_{seen[key]}"


# ── flowchart (query / proc) ──────────────────────────────────────────────────

def _analyze_query(ast, dialect: str) -> dict[str, Any]:
    cte_names = [c.alias for c in ast.find_all(exp.CTE)]
    cte_set = set(cte_names)

    # Source tables = every referenced table whose name is NOT a CTE alias, first-seen order.
    source_tables: list[str] = []
    for t in ast.find_all(exp.Table):
        name = t.name
        if name and name not in cte_set and name not in source_tables:
            source_tables.append(name)

    joins: list[dict[str, str]] = []
    for j in ast.find_all(exp.Join):
        target = j.this.name if isinstance(j.this, exp.Table) else _sanitize_label(j.this.sql(dialect=dialect))
        side = (j.args.get("side") or "").upper()
        kind = (j.args.get("kind") or "").upper()
        label = (f"{side} {kind}".strip()) or "INNER"
        on = j.args.get("on")
        joins.append({
            "kind": label.split()[0] if label else "INNER",
            "side_kind": label,
            "target": target,
            "on": _sanitize_label(on.sql(dialect=dialect)) if on else "",
        })

    # Filters: every WHERE in the tree (the outer query AND any CTE/subquery), each split on
    # top-level AND into distinct predicate nodes — so a filter inside a CTE still shows up.
    filters: list[str] = []
    for where in ast.find_all(exp.Where):
        stack = [where.this]
        parts: list[Any] = []
        while stack:
            node = stack.pop()
            if isinstance(node, exp.And):
                stack.extend([node.left, node.right])
            else:
                parts.append(node)
        for p in reversed(parts):  # preserve source order (stack reverses it)
            frag = _sanitize_label(p.sql(dialect=dialect))
            if frag not in filters:
                filters.append(frag)

    # Projection: TOP/LIMIT + ORDER BY, the "shape" of the final result.
    proj_bits: list[str] = []
    limit = ast.args.get("limit")
    if limit is not None:
        proj_bits.append(_sanitize_label(limit.sql(dialect=dialect)))
    # T-SQL TOP lives on the SELECT as `expressions[0]`-adjacent; sqlglot exposes it via `.args['limit']`
    # for LIMIT and a Top node for TOP — cover both.
    for top in ast.find_all(exp.Select):
        t = top.args.get("limit")
        if isinstance(t, exp.Limit) and t.sql(dialect=dialect) not in proj_bits:
            proj_bits.append(_sanitize_label(t.sql(dialect=dialect)))
    order = ast.args.get("order")
    if order is not None:
        proj_bits.append(_sanitize_label(order.sql(dialect=dialect)))
    projection = " . ".join(b for b in proj_bits if b) or None

    mermaid = _render_flowchart(source_tables, cte_names, joins, filters, projection)
    return {
        "diagram_type": "flowchart",
        "confidence": "high",
        "inferred": [],
        "source_tables": source_tables,
        "ctes": cte_names,
        "joins": joins,
        "filters": filters,
        "projection": projection,
        "entities": [],
        "relationships": [],
        "mermaid": mermaid,
    }


def _render_flowchart(source_tables, ctes, joins, filters, projection) -> str:
    seen: dict[str, int] = {}
    lines = ["flowchart TD"]
    ids: dict[str, str] = {}
    for name in source_tables:
        nid = _node_id("t", name, seen)
        ids[f"table:{name}"] = nid
        lines.append(f'    {nid}[({name})]')
    for name in ctes:
        nid = _node_id("cte", name, seen)
        ids[f"cte:{name}"] = nid
        lines.append(f'    {nid}{{{{"CTE: {name}"}}}}')
    result = "result"
    lines.append(f'    {result}[/"result"/]')
    # joins as labelled edges into the result
    for j in joins:
        target_id = ids.get(f"table:{j['target']}") or ids.get(f"cte:{j['target']}")
        if not target_id:
            target_id = _node_id("t", j["target"], seen)
            lines.append(f'    {target_id}[({j["target"]})]')
        on = f" on {j['on']}" if j["on"] else ""
        lines.append(f'    {target_id} -->|"{j["side_kind"]} JOIN{on}"| {result}')
    # filters as distinct nodes feeding the result
    for i, f in enumerate(filters, 1):
        fid = _node_id("filter", str(i), seen)
        lines.append(f'    {fid}["filter: {f}"] --> {result}')
    if projection:
        lines.append(f'    {result} --> proj[/"{projection}"/]')
    return "\n".join(lines)


# ── erDiagram (DDL) ───────────────────────────────────────────────────────────

def _analyze_ddl(statements, dialect: str) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, str]] = []
    for stmt in statements:
        if not isinstance(stmt, exp.Create):
            continue
        schema = stmt.this
        if not isinstance(schema, exp.Schema) or not isinstance(schema.this, exp.Table):
            continue
        tname = schema.this.name
        columns: list[dict[str, str]] = []
        pk_cols: set[str] = set()
        for col in schema.expressions:
            if isinstance(col, exp.ColumnDef):
                cname = col.name
                ctype = col.args.get("kind").sql(dialect=dialect) if col.args.get("kind") else ""
                key = ""
                for c in col.args.get("constraints", []) or []:
                    ck = c.kind if hasattr(c, "kind") else None
                    if isinstance(ck, exp.PrimaryKeyColumnConstraint):
                        key = "PK"
                        pk_cols.add(cname)
                columns.append({"name": cname, "type": _sanitize_label(ctype), "key": key})
            elif isinstance(col, exp.PrimaryKey):
                for e in col.expressions:
                    pk_cols.add(e.name)
            elif isinstance(col, exp.ForeignKey):
                local_cols = [e.name for e in col.expressions]
                ref = col.args.get("reference")
                ref_table = None
                if ref is not None:
                    rt = ref.find(exp.Table)
                    ref_table = rt.name if rt else None
                if ref_table:
                    relationships.append({
                        "from": tname, "to": ref_table,
                        "on": ", ".join(local_cols),
                    })
        # backfill PK flag for columns named in a table-level PRIMARY KEY
        for c in columns:
            if c["name"] in pk_cols and not c["key"]:
                c["key"] = "PK"
        # mark FK columns
        fk_cols = {lc for r in relationships if r["from"] == tname for lc in r["on"].split(", ")}
        for c in columns:
            if c["name"] in fk_cols and c["key"] != "PK":
                c["key"] = "FK"
        entities.append({"name": tname, "columns": columns})

    mermaid = _render_erdiagram(entities, relationships)
    return {
        "diagram_type": "erDiagram",
        "confidence": "high",
        "inferred": [],
        "source_tables": [e["name"] for e in entities],
        "ctes": [],
        "joins": [],
        "filters": [],
        "projection": None,
        "entities": entities,
        "relationships": relationships,
        "mermaid": mermaid,
    }


def _render_erdiagram(entities, relationships) -> str:
    lines = ["erDiagram"]
    for r in relationships:
        # child }o--|| parent (many optional children to exactly one parent)
        lines.append(f'    {r["to"].upper()} ||--o{{ {r["from"].upper()} : "{r["on"]}"')
    for e in entities:
        lines.append(f'    {e["name"].upper()} {{')
        for c in e["columns"]:
            typ = c["type"] or "unknown"
            key = f" {c['key']}" if c["key"] else ""
            lines.append(f'        {typ} {c["name"]}{key}')
        lines.append("    }")
    return "\n".join(lines)


# ── public API ────────────────────────────────────────────────────────────────

def analyze(sql: str, dialect: str = "tsql") -> dict[str, Any]:
    """Parse ``sql`` into the typed-graph model + a Mermaid skeleton. Raises
    ``SqlglotUnavailable`` if sqlglot isn't installed; returns a ``confidence: partial``
    result (never raises) when the SQL itself can't be parsed."""
    if not _HAVE_SQLGLOT:
        raise SqlglotUnavailable(
            "sqlglot is not installed — the deterministic SQL parse can't run. Either "
            "`pip install sqlglot`, or (per the db-diagram skill) hand-parse the SQL text and "
            "mark every inferred element clearly."
        )
    try:
        statements = [s for s in sqlglot.parse(sql, dialect=dialect) if s is not None]
    except Exception as exc:  # noqa: BLE001 — a parse failure degrades, never crashes the skill
        return {
            "diagram_type": "flowchart",
            "confidence": "partial",
            "inferred": [f"sqlglot could not parse this SQL ({type(exc).__name__}); "
                         "the structure below is best-effort and must be verified by hand"],
            "source_tables": [], "ctes": [], "joins": [], "filters": [],
            "projection": None, "entities": [], "relationships": [],
            "mermaid": "flowchart TD\n    unparsed[\"(could not parse SQL — hand-verify)\"]",
        }

    if not statements:
        return {
            "diagram_type": "flowchart", "confidence": "partial",
            "inferred": ["empty or comment-only SQL — nothing to diagram"],
            "source_tables": [], "ctes": [], "joins": [], "filters": [],
            "projection": None, "entities": [], "relationships": [],
            "mermaid": "flowchart TD\n    empty[\"(no SQL statements found)\"]",
        }

    creates = [s for s in statements if isinstance(s, exp.Create)]
    if creates and len(creates) == len(statements):
        return _analyze_ddl(statements, dialect)

    # query / proc: analyze the last top-level SELECT-bearing statement.
    query = next((s for s in reversed(statements) if s.find(exp.Select)), statements[-1])
    return _analyze_query(query, dialect)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic SQL -> Mermaid graph extractor (db-diagram skill).")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file", help="path to a .sql file")
    src.add_argument("--sql", help="inline SQL string")
    ap.add_argument("--dialect", default="tsql", help="sqlglot dialect (default: tsql)")
    ap.add_argument("--json", action="store_true", help="emit the full graph JSON instead of just Mermaid")
    args = ap.parse_args(argv)

    if args.file:
        sql = open(args.file, encoding="utf-8").read()
    elif args.sql:
        sql = args.sql
    else:
        sql = sys.stdin.read()

    try:
        g = analyze(sql, dialect=args.dialect)
    except SqlglotUnavailable as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    print(json.dumps(g, indent=2) if args.json else g["mermaid"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
