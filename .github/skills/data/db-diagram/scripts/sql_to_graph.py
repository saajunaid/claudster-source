#!/usr/bin/env python3
"""Deterministic SQL -> typed-graph + multi-format renderer (the db-diagram skill).

This is the DETERMINISTIC half of /mermaid-db and /excalidraw-db. It parses SQL with sqlglot
(a proper AST, dialect-aware) into a stable node/edge model, then renders it four ways — all from
ONE deterministic layout so the geometry is reproducible, never luck:

  * Mermaid   — git-diffable text; dagre auto-layout; light-first, adapts to the viewer's theme.
  * Excalidraw — native .excalidraw JSON; container-bound (auto-wrapping, vertically-centred) text so
                 every label stays INSIDE its box; bound arrows; grid-aligned columns; theme "light".
  * SVG        — self-contained, no external refs; dual-theme via CSS custom props (default light).
  * HTML       — self-contained page wrapping the SVG with a light/dark toggle (default LIGHT).

The LLM narration layer wraps this output with business prose, per-table descriptions, and the
execution-plan caveat — but the STRUCTURE (which tables, CTEs, joins+keys, filters) and the GEOMETRY
(where every box sits, how wide, how the text wraps) come from here, deterministically.

Two diagram types are derived structurally:
  * CREATE TABLE / DDL      -> erDiagram (entities, columns, PK/FK, FK relationships)
  * a query / proc / CTE    -> flowchart (tables [(T)], CTEs {{CTE: name}}, joins with keys,
                               filters as distinct nodes, final projection [/TOP.. ORDER BY../])

sqlglot is required. If it's absent, ``analyze`` raises ``SqlglotUnavailable`` with an actionable
message — the skill then falls back to LLM hand-parsing from the SQL text (marking inferred).

READ-ONLY by construction: this only parses SQL text. It never connects to or writes a database.

CLI:  python sql_to_graph.py --file query.sql [--dialect tsql] [--format mermaid|excalidraw|svg|html|json]
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


def _wrap(text: str, max_chars: int) -> list[str]:
    """Greedy word-wrap into lines of at most ``max_chars`` (a word longer than the limit is
    hard-split). This is what keeps every label INSIDE its box — box heights are computed from
    the resulting line count, so wrapping and containment are two ends of the same guarantee."""
    words = (text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    cur = ""
    for w in words:
        while len(w) > max_chars:  # a single over-long token: hard-split it
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:max_chars])
            w = w[max_chars:]
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= max_chars:
            cur = f"{cur} {w}"
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


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


# Mermaid classDef fills — light-first, but chosen to stay legible if the viewer flips to dark
# (Mermaid re-tints on the viewer's theme; these are the base hues, matching the SVG/Excalidraw palette).
# Palette: evergreen / violet dusk / amber sand / slate indigo / terracotta on warm paper — deliberate
# hues, not the default pastel set every generated diagram ships with.
_MERMAID_CLASSDEF = {
    "table": "fill:#DDEEE4,stroke:#1F7A5C,color:#123D2E",
    "cte": "fill:#E9E4F5,stroke:#67589E,color:#322852",
    "filter": "fill:#F9EED9,stroke:#B97C10,color:#5B3A05",
    "result": "fill:#E1E7F8,stroke:#3E5C9A,color:#1C2C50",
    "projection": "fill:#F8E7DF,stroke:#C05B41,color:#5F2A1B",
}
_MERMAID_WRAP = 26  # chars before inserting <br/> in a node label (keeps text inside the box)


def _mwrap(text: str) -> str:
    """Wrap a Mermaid node label with <br/> so long filters/projections don't overflow the box."""
    return "<br/>".join(_wrap(text, _MERMAID_WRAP))


def _render_flowchart(source_tables, ctes, joins, filters, projection) -> str:
    # PIPELINE rule: sources/CTEs -> WHERE (one box, all ANDed predicates) -> result -> projection.
    # Every edge connects ADJACENT stages only — an arrow can never cross a box, and there is
    # exactly one fan-in point (the WHERE box or, without filters, the result).
    seen: dict[str, int] = {}
    lines = ["flowchart LR"]
    ids: dict[str, str] = {}
    classes: dict[str, list[str]] = {k: [] for k in _MERMAID_CLASSDEF}
    order: list[str] = []  # node keys in display order (drives edge order too)
    for name in source_tables:
        nid = _node_id("t", name, seen)
        ids[f"table:{name}"] = nid
        lines.append(f'    {nid}[({name})]')
        classes["table"].append(nid)
        order.append(f"table:{name}")
    for name in ctes:
        nid = _node_id("cte", name, seen)
        ids[f"cte:{name}"] = nid
        lines.append(f'    {nid}{{{{"CTE: {name}"}}}}')
        classes["cte"].append(nid)
        order.append(f"cte:{name}")
    # join labels by target; a join target that isn't a plain source (e.g. a subquery) still
    # gets its own node so its label has somewhere to hang.
    join_label: dict[str, str] = {}
    for j in joins:
        on = f" on {j['on']}" if j["on"] else ""
        join_label[j["target"]] = f'{j["side_kind"]} JOIN{on}'
        if not (ids.get(f"table:{j['target']}") or ids.get(f"cte:{j['target']}")):
            nid = _node_id("t", j["target"], seen)
            ids[f"table:{j['target']}"] = nid
            lines.append(f'    {nid}[({j["target"]})]')
            classes["table"].append(nid)
            order.append(f"table:{j['target']}")
    hub = "result"
    if filters:
        parts = [_mwrap(("WHERE " if i == 0 else "AND ") + f) for i, f in enumerate(filters)]
        lines.append(f'    where["{"<br/>".join(parts)}"]')
        classes["filter"].append("where")
        hub = "where"
    lines.append('    result[/"result"/]')
    classes["result"].append("result")
    for key in order:
        name = key.split(":", 1)[1]
        lbl = join_label.get(name, "")
        edge = f'-->|"{lbl}"|' if lbl else "-->"
        lines.append(f'    {ids[key]} {edge} {hub}')
    if filters:
        lines.append("    where --> result")
    if projection:
        lines.append(f'    result --> proj[/"{_mwrap(projection)}"/]')
        classes["projection"].append("proj")
    # classDefs + assignments (colour the typed nodes; harmless if a viewer strips styling)
    for role, style in _MERMAID_CLASSDEF.items():
        lines.append(f"    classDef {role} {style};")
    for role, nids in classes.items():
        if nids:
            lines.append(f"    class {','.join(nids)} {role};")
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


# ── deterministic geometry (shared by Excalidraw / SVG / HTML) ─────────────────
#
# ONE layout pass positions every node on a grid: same-column nodes share an x (perfect vertical
# alignment); every column is centred on the same mid-line (balanced); box heights are computed from
# the WRAPPED line count (text always fits). Every renderer below just reads these coordinates — so
# alignment and containment are reproducible properties of the layout, not per-format luck.

_FONT = 16          # node label font size (px)
_PAD_H = 12         # horizontal text padding inside a box
_PAD_V = 12         # vertical text padding inside a box
_MIN_H = 46         # minimum box height
_COL_GAP = 88       # horizontal gap between columns
_ROW_GAP = 26       # vertical gap between boxes in a column
_MARGIN = 36        # canvas margin
_CHAR_W = _FONT * 0.55  # approx glyph advance for wrap-width math

# target box width per role (px) — wrap width derives from this, so text is guaranteed to fit.
_ROLE_W = {"table": 200, "cte": 200, "filter": 250, "result": 150, "projection": 230, "entity": 240}
_EDGE_LABEL_WRAP = 28   # chars per line for a join label riding beside its arrow
_EDGE_LABEL_FONT = 12   # edge label font size (px)
# fixed Excalidraw palette (the app re-tints for dark itself; these are the light/base hues) —
# same evergreen/violet/amber/indigo/terracotta family as Mermaid + SVG.
_EXCALI = {
    "table": ("#DDEEE4", "#1F7A5C"), "cte": ("#E9E4F5", "#67589E"),
    "filter": ("#F9EED9", "#B97C10"), "result": ("#E1E7F8", "#3E5C9A"),
    "projection": ("#F8E7DF", "#C05B41"), "entity": ("#DDEEE4", "#1F7A5C"),
}
_EXCALI_INK = "#1F2A33"
_EDGE_COLOR = "#4A5568"


def _edge_label_size(label: str) -> tuple[list[str], float, float]:
    """Wrapped lines + pixel (w, h) of an edge label block."""
    lines = _wrap(label, _EDGE_LABEL_WRAP)
    w = round(max(len(ln) for ln in lines) * _EDGE_LABEL_FONT * 0.55 + 8, 2)
    h = len(lines) * (_EDGE_LABEL_FONT + 3)
    return lines, w, h


def _role_max_chars(role: str) -> int:
    return max(6, int((_ROLE_W[role] - 2 * _PAD_H) / _CHAR_W))


def _mk_node(nid: str, role: str, label: str, *, sub: str | None = None,
             align: str = "center", font: int = _FONT) -> dict[str, Any]:
    """Build a laid-out node with wrapped lines + a box tall enough to contain them.
    ``sub`` adds a secondary info block under the title (e.g. a table's join condition) —
    inside the box, where containment is guaranteed, instead of floating in the diagram."""
    max_chars = _role_max_chars(role)
    lines = _wrap(label, max_chars)
    if sub:
        lines.append("")  # breathing room between title and sub-line
        lines.extend(_wrap(sub, max_chars))
    line_px = int(font * 1.25)
    h = max(_MIN_H, len(lines) * line_px + 2 * _PAD_V)
    return {"id": nid, "role": role, "lines": lines, "text": "\n".join(lines),
            "w": _ROLE_W[role], "h": h, "font": font, "align": align, "line_px": line_px,
            "x": 0.0, "y": 0.0}


def _place_columns(columns: list[list[dict[str, Any]]],
                   gaps: list[float] | None = None) -> dict[str, Any]:
    """Position a list of columns left-to-right; centre each column on a shared mid-line.
    ``gaps[i]`` overrides the gap AFTER column i — used to widen a gap that must also hold
    edge labels, so a label never has to sit on top of a box or an arrow."""
    col_heights = [sum(n["h"] for n in col) + _ROW_GAP * max(0, len(col) - 1) for col in columns]
    canvas_h = max(col_heights) if col_heights else 0
    mid = _MARGIN + canvas_h / 2
    x = float(_MARGIN)
    nodes: list[dict[str, Any]] = []
    last_gap = _COL_GAP
    for idx, col in enumerate(columns):
        if not col:
            continue
        col_w = max(n["w"] for n in col)
        total = sum(n["h"] for n in col) + _ROW_GAP * (len(col) - 1)
        y = mid - total / 2
        for n in col:
            n["x"] = x + (col_w - n["w"]) / 2  # centre the box within its column band
            n["y"] = y
            y += n["h"] + _ROW_GAP
            nodes.append(n)
        last_gap = gaps[idx] if gaps and idx < len(gaps) else _COL_GAP
        x += col_w + last_gap
    width = x - last_gap + _MARGIN if nodes else 2 * _MARGIN
    height = canvas_h + 2 * _MARGIN
    return {"nodes": nodes, "width": round(width), "height": round(height)}


def _layout(graph: dict[str, Any]) -> dict[str, Any]:
    """Turn an ``analyze`` result into positioned nodes + edges (the geometry every renderer reads)."""
    if graph.get("diagram_type") == "erDiagram":
        return _layout_er(graph)
    return _layout_flowchart(graph)


def _annotate_fan_in(edges: list[dict[str, Any]]) -> None:
    """Stamp each edge with its slot among edges sharing a destination, so renderers can spread
    arrowheads along the target's edge instead of piling them onto one point."""
    by_dst: dict[str, list[dict[str, Any]]] = {}
    for e in edges:
        by_dst.setdefault(e["dst"], []).append(e)
    for group in by_dst.values():
        for i, e in enumerate(group):
            e["slot"], e["slots"] = i, len(group)


def _mk_where_node(filters: list[str]) -> dict[str, Any]:
    """ONE box for all ANDed predicates (one per line, wrapped) — three stacked filter boxes read
    as three alternative paths; one WHERE box reads as what it is: a single conjunctive gate."""
    lines: list[str] = []
    for i, f in enumerate(filters):
        lines.extend(_wrap(("WHERE " if i == 0 else "AND ") + f, _role_max_chars("filter")))
    line_px = int(_FONT * 1.25)
    h = max(_MIN_H, len(lines) * line_px + 2 * _PAD_V)
    return {"id": "where", "role": "filter", "lines": lines, "text": "\n".join(lines),
            "w": _ROLE_W["filter"], "h": h, "font": _FONT, "align": "left",
            "line_px": line_px, "x": 0.0, "y": 0.0}


def _layout_flowchart(graph: dict[str, Any]) -> dict[str, Any]:
    # PIPELINE rule (same as the Mermaid renderer): sources -> WHERE -> result -> projection,
    # edges between ADJACENT stages only. Geometrically that means no arrow can ever cross a box:
    # the gap between two columns contains nothing but the arrows that bridge exactly those columns.
    # Join info lives INSIDE each source box (a "⋈ …" sub-line) — flowchart arrows carry NO
    # text. In a converging fan the space beside arrow N is occupied by arrow N±1, so any
    # floating label will eventually cover some arrow; inside the box, containment is already
    # guaranteed and every arrow stays fully visible.
    join_label: dict[str, str] = {}
    for j in graph.get("joins", []):
        on = f" on {j['on']}" if j["on"] else ""
        join_label[j["target"]] = f"⋈ {j['side_kind']} JOIN{on}"

    seen: dict[str, int] = {}
    by_name: dict[str, dict[str, Any]] = {}
    sources_col: list[dict[str, Any]] = []
    for name in graph.get("source_tables", []):
        n = _mk_node(_node_id("t", name, seen), "table", name, sub=join_label.get(name))
        by_name[f"table:{name}"] = n
        sources_col.append(n)
    for name in graph.get("ctes", []):
        n = _mk_node(_node_id("cte", name, seen), "cte", f"CTE: {name}", sub=join_label.get(name))
        by_name[f"cte:{name}"] = n
        sources_col.append(n)

    filters = graph.get("filters", [])
    where_col = [_mk_where_node(filters)] if filters else []
    result = _mk_node("result", "result", "result")
    proj = graph.get("projection")
    proj_col = [_mk_node("proj", "projection", proj)] if proj else []

    placed = _place_columns([sources_col, where_col, [result], proj_col])

    hub = where_col[0] if where_col else result
    edges: list[dict[str, Any]] = []
    for n_key in ([f"table:{t}" for t in graph.get("source_tables", [])]
                  + [f"cte:{c}" for c in graph.get("ctes", [])]):
        edges.append({"src": by_name[n_key]["id"], "dst": hub["id"], "label": ""})
    if where_col:
        edges.append({"src": hub["id"], "dst": result["id"], "label": ""})
    if proj_col:
        edges.append({"src": result["id"], "dst": proj_col[0]["id"], "label": ""})
    _annotate_fan_in(edges)

    placed["edges"] = edges
    return placed


def _layout_er(graph: dict[str, Any]) -> dict[str, Any]:
    """Entities as boxes in a wrapped grid (rows of 3); FK relationships as arrows."""
    nodes: list[dict[str, Any]] = []
    node_by_name: dict[str, dict[str, Any]] = {}
    seen: dict[str, int] = {}
    per_row = 3
    col_w = _ROLE_W["entity"]
    x0, y = float(_MARGIN), float(_MARGIN)
    row_max_h = 0.0
    for i, e in enumerate(graph.get("entities", [])):
        header = e["name"]
        col_lines = [f"{c['name']}: {c['type'] or '?'}{(' ' + c['key']) if c['key'] else ''}"
                     for c in e["columns"]]
        raw_lines = [header] + col_lines
        lines: list[str] = []
        for raw in raw_lines:
            lines.extend(_wrap(raw, _role_max_chars("entity")))
        line_px = int(_FONT * 1.25)
        h = max(_MIN_H, len(lines) * line_px + 2 * _PAD_V)
        col = i % per_row
        if col == 0 and i > 0:
            y += row_max_h + _ROW_GAP + 24
            row_max_h = 0.0
        n = {"id": _node_id("e", e["name"], seen), "role": "entity", "lines": lines,
             "text": "\n".join(lines), "w": col_w, "h": h, "font": _FONT, "align": "left",
             "line_px": line_px, "x": x0 + col * (col_w + _COL_GAP), "y": y}
        row_max_h = max(row_max_h, h)
        nodes.append(n)
        node_by_name[e["name"]] = n
    width = round(x0 + min(per_row, max(1, len(nodes))) * (col_w + _COL_GAP) - _COL_GAP + _MARGIN)
    height = round(y + row_max_h + _MARGIN)
    edges = []
    for r in graph.get("relationships", []):
        if r["from"] in node_by_name and r["to"] in node_by_name:
            edges.append({"src": node_by_name[r["from"]]["id"], "dst": node_by_name[r["to"]]["id"],
                          "label": r["on"]})
    _annotate_fan_in(edges)
    return {"nodes": nodes, "edges": edges, "width": width, "height": height}


# ── Excalidraw export (container-bound text, bound arrows, theme=light) ─────────

def to_excalidraw(graph: dict[str, Any]) -> dict[str, Any]:
    """Render the layout as Excalidraw scene JSON. Every box carries a container-BOUND text element
    (so the label auto-wraps and stays vertically centred INSIDE the box, forever), and every arrow
    is bound to real start/end elements. Ids/seeds are deterministic — same SQL, byte-identical JSON."""
    lay = _layout(graph)
    elements: list[dict[str, Any]] = []
    rect_by_id: dict[str, dict[str, Any]] = {}

    def _base(i: int) -> dict[str, Any]:
        return {"angle": 0, "strokeWidth": 1.5, "strokeStyle": "solid", "fillStyle": "solid",
                "roughness": 1, "opacity": 100, "groupIds": [], "frameId": None,
                "roundness": {"type": 3}, "seed": 1000 + i, "version": 1, "versionNonce": 5000 + i,
                "isDeleted": False, "boundElements": [], "updated": 1, "link": None, "locked": False}

    for i, n in enumerate(lay["nodes"]):
        fill, stroke = _EXCALI[n["role"]]
        text_id = f"{n['id']}__label"
        rect = {**_base(i), "id": n["id"], "type": "rectangle",
                "x": round(n["x"], 2), "y": round(n["y"], 2),
                "width": n["w"], "height": n["h"],
                "strokeColor": stroke, "backgroundColor": fill,
                "boundElements": [{"type": "text", "id": text_id}],
                "customData": {"kind": n["role"]}}
        text_h = len(n["lines"]) * n["line_px"]
        text = {**_base(1000 + i), "id": text_id, "type": "text",
                "x": round(n["x"] + _PAD_H, 2),
                "y": round(n["y"] + (n["h"] - text_h) / 2, 2),
                "width": n["w"] - 2 * _PAD_H, "height": text_h,
                "strokeColor": _EXCALI_INK, "backgroundColor": "transparent",
                "text": n["text"], "originalText": n["text"], "fontSize": n["font"],
                "fontFamily": 2, "textAlign": n["align"],
                "verticalAlign": "middle" if n["align"] == "center" else "top",
                "containerId": n["id"], "lineHeight": 1.25, "autoResize": False,
                "roundness": None}
        elements.append(rect)
        elements.append(text)
        rect_by_id[n["id"]] = rect

    for j, e in enumerate(lay["edges"]):
        src, dst = rect_by_id[e["src"]], rect_by_id[e["dst"]]
        slot, slots = e.get("slot", 0), e.get("slots", 1)
        sx, sy = src["x"] + src["width"], src["y"] + src["height"] / 2
        ex = dst["x"]
        # fan-in: spread arrowheads along the target's left edge (and tell Excalidraw the same
        # via binding `focus`) so N arrows land on N distinct points, never one pile-up.
        if slots <= 1:
            ey, focus = dst["y"] + dst["height"] / 2, 0
        else:
            span = min(dst["height"] - 20, 26.0 * (slots - 1))
            ey = dst["y"] + dst["height"] / 2 - span / 2 + slot * (span / (slots - 1))
            focus = round((slot / (slots - 1)) * 1.2 - 0.6, 3)
        arrow_id = f"edge_{j}"
        arrow = {**_base(3000 + j), "id": arrow_id, "type": "arrow",
                 "x": round(sx, 2), "y": round(sy, 2),
                 "width": round(abs(ex - sx), 2), "height": round(abs(ey - sy), 2),
                 "strokeColor": _EDGE_COLOR, "backgroundColor": "transparent",
                 "points": [[0, 0], [round(ex - sx, 2), round(ey - sy, 2)]],
                 "lastCommittedPoint": None, "startArrowhead": None, "endArrowhead": "arrow",
                 "roundness": {"type": 2},
                 "startBinding": {"elementId": e["src"], "focus": 0, "gap": 6},
                 "endBinding": {"elementId": e["dst"], "focus": focus, "gap": 6}}
        elements.append(arrow)
        src["boundElements"].append({"type": "arrow", "id": arrow_id})
        dst["boundElements"].append({"type": "arrow", "id": arrow_id})
        if e.get("label"):
            # join label floats BESIDE its arrow, never on it: staggered above (early slots) or
            # below (late slots) the line, so every arrow stays fully visible. Unbound on purpose —
            # a bound label sits centred ON the line and knocks a hole in it.
            label_lines, lw, lh = _edge_label_size(e["label"])
            mx, my = sx + (ex - sx) / 2, sy + (ey - sy) / 2
            above = slots <= 1 or slot < slots / 2
            # a slanted line rises/falls across the label's width — clear that too, not just
            # the midpoint, so the label can never touch its own arrow
            rise = abs((ey - sy) / (ex - sx)) * lw / 2 if ex != sx else 0.0
            ly = (my - rise - 8 - lh) if above else (my + rise + 8)
            label = {**_base(6000 + j), "id": f"{arrow_id}__label", "type": "text",
                     "x": round(mx - lw / 2, 2), "y": round(ly, 2),
                     "width": lw, "height": lh,
                     "strokeColor": _EDGE_COLOR, "backgroundColor": "transparent",
                     "text": "\n".join(label_lines), "originalText": "\n".join(label_lines),
                     "fontSize": _EDGE_LABEL_FONT, "fontFamily": 2, "textAlign": "center",
                     "verticalAlign": "top", "containerId": None,
                     "lineHeight": 1.25, "autoResize": False, "roundness": None,
                     "customData": {"edgeLabelOf": arrow_id}}
            elements.append(label)

    return {"type": "excalidraw", "version": 2, "source": "db-diagram skill",
            "elements": elements, "files": {},
            "appState": {"viewBackgroundColor": "#FDFCF9", "gridSize": None, "theme": "light"}}


# ── SVG / HTML export (self-contained, dual-theme via CSS custom props) ─────────

# role -> (fill, stroke, ink); page-level keys bg/ink/edge/edge_ink. Light is the default.
_SVG_ROLES = ["table", "cte", "filter", "result", "projection", "entity"]
_SVG_LIGHT = {
    "page": {"bg": "#FDFCF9", "ink": "#23303B", "edge": "#8B93A7", "edge_ink": "#4A5568"},
    "table": ("#DDEEE4", "#1F7A5C", "#123D2E"), "cte": ("#E9E4F5", "#67589E", "#322852"),
    "filter": ("#F9EED9", "#B97C10", "#5B3A05"), "result": ("#E1E7F8", "#3E5C9A", "#1C2C50"),
    "projection": ("#F8E7DF", "#C05B41", "#5F2A1B"), "entity": ("#DDEEE4", "#1F7A5C", "#123D2E"),
}
_SVG_DARK = {
    "page": {"bg": "#171C26", "ink": "#E5EAF3", "edge": "#55617A", "edge_ink": "#A8B3C7"},
    "table": ("#12352A", "#3FBF95", "#C5EBDD"), "cte": ("#241F3D", "#9C8BD8", "#DCD4F5"),
    "filter": ("#33270E", "#D9A03E", "#F2DDB5"), "result": ("#16223D", "#7396E0", "#CBD8F5"),
    "projection": ("#351E15", "#E08A66", "#F5D5C8"), "entity": ("#12352A", "#3FBF95", "#C5EBDD"),
}


def _vars_block(selector: str, theme: dict[str, Any]) -> str:
    p = theme["page"]
    out = [selector + " {",
           f"  --dbd-bg:{p['bg']}; --dbd-ink:{p['ink']}; --dbd-edge:{p['edge']}; --dbd-edge-ink:{p['edge_ink']};"]
    for role in _SVG_ROLES:
        f, s, i = theme[role]
        out.append(f"  --dbd-{role}-fill:{f}; --dbd-{role}-stroke:{s}; --dbd-{role}-ink:{i};")
    out.append("}")
    return "\n".join(out)


def _svg_struct_css() -> str:
    """Which element consumes which var — identical whether standalone or embedded in HTML."""
    rules = [".dbd-node rect { stroke-width: 1.5; }",
             ".dbd-node text { font-family: 'Segoe UI', system-ui, sans-serif; }",
             ".dbd-edge { stroke: var(--dbd-edge); stroke-width: 1.5; fill: none; marker-end: url(#dbd-arrow); }",
             ".dbd-edge-label { fill: var(--dbd-edge-ink); font: 12px 'Segoe UI', system-ui, sans-serif; "
             "paint-order: stroke; stroke: var(--dbd-bg); stroke-width: 4px; stroke-linejoin: round; }",
             "#dbd-arrow path { fill: var(--dbd-edge); }"]
    for role in _SVG_ROLES:
        rules.append(f".dbd-node.{role} rect {{ fill: var(--dbd-{role}-fill); stroke: var(--dbd-{role}-stroke); }}")
        rules.append(f".dbd-node.{role} text {{ fill: var(--dbd-{role}-ink); }}")
    return "\n".join(rules)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _svg_node(n: dict[str, Any]) -> str:
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    font = n["font"]
    total = len(n["lines"]) * n["line_px"]
    if n["align"] == "center":
        anchor, tx = "middle", x + w / 2
        first = y + (h - total) / 2 + font * 0.8
    else:
        anchor, tx = "start", x + _PAD_H
        first = y + _PAD_V + font * 0.8
    tspans = "".join(
        f'<tspan x="{round(tx, 1)}" y="{round(first + i * n["line_px"], 1)}">{_esc(line)}</tspan>'
        for i, line in enumerate(n["lines"])
    )
    return (
        f'<g class="dbd-node {n["role"]}">'
        f'<rect x="{round(x, 1)}" y="{round(y, 1)}" width="{w}" height="{h}" rx="8"/>'
        f'<text text-anchor="{anchor}" font-size="{font}">{tspans}</text>'
        f'</g>'
    )


def _svg_edges(lay: dict[str, Any]) -> tuple[str, str]:
    """Returns (paths, labels) separately: paths are painted UNDER the nodes, labels ON TOP of
    everything (with a bg-colour halo) — an edge label can never end up hidden behind a box."""
    by_id = {n["id"]: n for n in lay["nodes"]}
    paths: list[str] = []
    labels: list[str] = []
    for e in lay["edges"]:
        s, d = by_id[e["src"]], by_id[e["dst"]]
        slot, slots = e.get("slot", 0), e.get("slots", 1)
        sx, sy = s["x"] + s["w"], s["y"] + s["h"] / 2
        ex = d["x"]
        if slots <= 1:
            ey = d["y"] + d["h"] / 2
        else:  # fan-in: N arrows land on N distinct points along the target's left edge
            span = min(d["h"] - 20, 26.0 * (slots - 1))
            ey = d["y"] + d["h"] / 2 - span / 2 + slot * (span / (slots - 1))
        mx = (sx + ex) / 2
        # gentle S-curve so parallel edges stay individually traceable
        path = (f'M {round(sx, 1)},{round(sy, 1)} '
                f'C {round(mx, 1)},{round(sy, 1)} {round(mx, 1)},{round(ey, 1)} '
                f'{round(ex - 4, 1)},{round(ey, 1)}')
        paths.append(f'<path class="dbd-edge" d="{path}"/>')
        if e.get("label"):
            # label floats ABOVE (early slots) or BELOW (late slots) the arrow — never on the
            # line itself, so the arrow stays fully visible under all of its text.
            elines, lw, lh = _edge_label_size(e["label"])
            my = (sy + ey) / 2
            above = slots <= 1 or slot < slots / 2
            # clear the line's rise across the label width too (slanted fan-in arrows)
            rise = abs((ey - sy) / (ex - sx)) * lw / 2 if ex != sx else 0.0
            first_baseline = (my - rise - 8 - lh + _EDGE_LABEL_FONT) if above \
                else (my + rise + 8 + _EDGE_LABEL_FONT)
            for i, ln in enumerate(elines):
                labels.append(f'<text class="dbd-edge-label" text-anchor="middle" '
                              f'x="{round(mx, 1)}" '
                              f'y="{round(first_baseline + i * (_EDGE_LABEL_FONT + 3), 1)}">{_esc(ln)}</text>')
    return "".join(paths), "".join(labels)


def to_svg(graph: dict[str, Any], standalone: bool = True) -> str:
    """Self-contained SVG. ``standalone`` embeds the theme variables (default LIGHT, follows
    prefers-color-scheme for dark); embedded (False) relies on the host page's variables so the
    HTML toggle can drive it. No external references — safe to inline anywhere."""
    lay = _layout(graph)
    w, h = lay["width"], lay["height"]
    if standalone:
        dark_body = _vars_block(":root", _SVG_DARK).split("{", 1)[1].rsplit("}", 1)[0]
        style = (_vars_block(":root", _SVG_LIGHT) + "\n"
                 + "@media (prefers-color-scheme: dark){ :root {" + dark_body + "} }\n"
                 + _svg_struct_css())
    else:
        style = _svg_struct_css()
    defs = ('<defs><marker id="dbd-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>')
    bg = '<rect x="0" y="0" width="100%" height="100%" fill="var(--dbd-bg)"/>' if standalone else ""
    edge_paths, edge_labels = _svg_edges(lay)
    # paint order: arrows under boxes, boxes, then edge labels ON TOP (halo keeps them readable)
    body = edge_paths + "".join(_svg_node(n) for n in lay["nodes"]) + edge_labels
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="database diagram">'
        f'<style>{style}</style>{defs}{bg}{body}</svg>'
    )


def to_html(graph: dict[str, Any], *, title: str = "DB diagram",
            source: str = "", date: str = "") -> str:
    """Self-contained HTML page: the SVG inline + a light/dark toggle. Default is LIGHT (it does NOT
    auto-follow the OS to dark — dark is opt-in via the toggle), and there are zero external requests."""
    svg = to_svg(graph, standalone=False)
    light = _vars_block(":root", _SVG_LIGHT)
    dark = _vars_block(':root[data-theme="dark"]', _SVG_DARK)
    struct = _svg_struct_css()
    meta = " · ".join(x for x in [_esc(source), _esc(date)] if x)
    caveat = ("This diagram is the query's STRUCTURE, extracted from the SQL text — not its execution "
              "plan. The optimizer decides actual join order, index use, and physical operators at "
              "runtime; verify performance against the real plan.")
    return f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>
{light}
{dark}
{struct}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 24px; background: var(--dbd-bg); color: var(--dbd-ink);
        font-family: 'Segoe UI', system-ui, sans-serif; transition: background .2s, color .2s; }}
header {{ display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }}
h1 {{ font-size: 18px; margin: 0; }}
.meta {{ opacity: .65; font-size: 13px; }}
.toggle {{ margin-left: auto; cursor: pointer; border: 1px solid var(--dbd-edge);
           background: transparent; color: inherit; border-radius: 6px; padding: 6px 12px; font: inherit; }}
.diagram {{ overflow-x: auto; border: 1px solid var(--dbd-edge); border-radius: 10px; padding: 8px; }}
.diagram svg {{ max-width: 100%; height: auto; display: block; }}
.caveat {{ margin-top: 16px; font-size: 12px; opacity: .7; max-width: 70ch; line-height: 1.5; }}
</style>
</head>
<body>
<header>
  <h1>{_esc(title)}</h1>
  <span class="meta">{meta}</span>
  <button class="toggle" onclick="var r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark';this.textContent=r.dataset.theme==='dark'?'☀ Light':'☾ Dark';">☾ Dark</button>
</header>
<div class="diagram">{svg}</div>
<p class="caveat">{caveat}</p>
</body>
</html>"""


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


def render(graph: dict[str, Any], fmt: str, **kw: Any) -> str:
    """Render a parsed graph to a chosen format: mermaid | excalidraw | svg | html | json."""
    if fmt == "mermaid":
        return graph["mermaid"]
    if fmt == "excalidraw":
        return json.dumps(to_excalidraw(graph), indent=2)
    if fmt == "svg":
        return to_svg(graph)
    if fmt == "html":
        return to_html(graph, **kw)
    if fmt == "json":
        return json.dumps(graph, indent=2)
    raise ValueError(f"unknown format: {fmt!r}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic SQL -> diagram extractor (db-diagram skill).")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file", help="path to a .sql file")
    src.add_argument("--sql", help="inline SQL string")
    ap.add_argument("--dialect", default="tsql", help="sqlglot dialect (default: tsql)")
    ap.add_argument("--format", default="mermaid",
                    choices=["mermaid", "excalidraw", "svg", "html", "json"],
                    help="output format (default: mermaid)")
    ap.add_argument("--json", action="store_true",
                    help="shorthand for --format json (full graph JSON)")
    ap.add_argument("--title", default="DB diagram", help="title for --format html")
    args = ap.parse_args(argv)

    # SVG/HTML output can carry non-ASCII (theme toggle glyphs, the · separator); force UTF-8 so a
    # Windows cp1252 console doesn't choke when the output is redirected to a file.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — older/odd streams: fall back to default encoding
        pass

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
    fmt = "json" if args.json else args.format
    print(render(g, fmt, title=args.title, source=(args.file or "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
