"""Tests for the db-diagram skill's deterministic SQL->graph extractor.

The extractor is the DETERMINISTIC half of the /mermaid-db + /excalidraw-db feature (the
LLM narration layer wraps its output). It must turn SQL into a stable, typed node/edge model
+ a Mermaid skeleton, reproducibly — that reproducibility is the whole point (diffable, regen-
able diagrams). These golden cases pin that behavior.

The script lives inside the skill dir; loaded by path (it's not a top-level module).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / ".github" / "skills" / "data" / "db-diagram" / "scripts" / "sql_to_graph.py"
_SPEC = importlib.util.spec_from_file_location("sql_to_graph", _SCRIPT)
s2g = importlib.util.module_from_spec(_SPEC)
sys.modules["sql_to_graph"] = s2g
_SPEC.loader.exec_module(s2g)  # type: ignore[union-attr]

# The extractor requires sqlglot (a documented skill dependency). On a minimal checkout
# without it, the real-parse tests SKIP rather than fail; the graceful-degradation test
# (missing-sqlglot) always runs. CI/dev envs have sqlglot, so the full set runs there.
requires_sqlglot = pytest.mark.skipif(
    not s2g._HAVE_SQLGLOT, reason="sqlglot not installed (pip install sqlglot)"
)


_QUERY = """
WITH active_subs AS (
  SELECT sub_id, customer_id FROM Subscriptions WHERE status = 'active'
)
SELECT TOP 100 c.name, s.sub_id
FROM active_subs s
INNER JOIN Customers c ON c.customer_id = s.customer_id
LEFT JOIN Invoices i ON i.sub_id = s.sub_id
WHERE c.region = 'EU'
ORDER BY c.name
"""


# ── flowchart path (query / proc) — the novel, high-value case ────────────────

@requires_sqlglot
def test_query_classified_as_flowchart():
    g = s2g.analyze(_QUERY)
    assert g["diagram_type"] == "flowchart"
    assert g["confidence"] == "high"


@requires_sqlglot
def test_source_tables_exclude_cte_references():
    g = s2g.analyze(_QUERY)
    # active_subs is a CTE, NOT a source table — it must not appear in source_tables.
    assert set(g["source_tables"]) == {"Subscriptions", "Customers", "Invoices"}
    assert g["ctes"] == ["active_subs"]


@requires_sqlglot
def test_joins_carry_kind_and_key():
    g = s2g.analyze(_QUERY)
    kinds = {(j["kind"], j["target"]) for j in g["joins"]}
    assert ("INNER", "Customers") in kinds
    assert ("LEFT", "Invoices") in kinds
    inner = next(j for j in g["joins"] if j["target"] == "Customers")
    assert "customer_id" in inner["on"]  # the join KEY is captured, not just the table


@requires_sqlglot
def test_filters_are_distinct_predicates():
    g = s2g.analyze(_QUERY)
    joined = " || ".join(g["filters"])
    assert "status = 'active'" in joined
    assert "c.region = 'EU'" in joined


@requires_sqlglot
def test_projection_captures_top_and_order():
    g = s2g.analyze(_QUERY)
    proj = g["projection"] or ""
    assert "100" in proj          # TOP 100
    assert "name" in proj.lower()  # ORDER BY c.name


@requires_sqlglot
def test_flowchart_mermaid_uses_typed_node_shapes():
    g = s2g.analyze(_QUERY)
    m = g["mermaid"]
    assert m.startswith("flowchart LR")    # left-to-right data flow (matches the Excalidraw layout)
    assert "[(Subscriptions)]" in m        # table shape [(...)]
    assert "CTE: active_subs" in m         # CTE labelled
    assert "{{" in m and "}}" in m         # CTE hexagon shape
    assert "INNER JOIN on" in m            # join label with type
    assert "customer_id" in m              # join key on the edge


@requires_sqlglot
def test_mermaid_labels_have_no_unescaped_double_quotes():
    # Unescaped quotes/brackets inside a label break Mermaid rendering — the #1 footgun.
    g = s2g.analyze("SELECT * FROM T WHERE name = 'a\"b'")
    for line in g["mermaid"].splitlines():
        # every quoted label must be balanced; a stray double-quote in content is sanitized out
        assert line.count('"') % 2 == 0, line


# ── erDiagram path (schema DDL) ───────────────────────────────────────────────

_DDL = """
CREATE TABLE Customers (
  id INT PRIMARY KEY,
  email VARCHAR(200),
  name VARCHAR(100)
);
CREATE TABLE Orders (
  id INT PRIMARY KEY,
  customer_id INT,
  total DECIMAL(10,2),
  FOREIGN KEY (customer_id) REFERENCES Customers(id)
);
"""


@requires_sqlglot
def test_ddl_classified_as_erdiagram():
    g = s2g.analyze(_DDL)
    assert g["diagram_type"] == "erDiagram"


@requires_sqlglot
def test_erdiagram_has_entities_with_columns_and_keys():
    g = s2g.analyze(_DDL)
    names = {e["name"] for e in g["entities"]}
    assert names == {"Customers", "Orders"}
    orders = next(e for e in g["entities"] if e["name"] == "Orders")
    cols = {c["name"]: c for c in orders["columns"]}
    assert "id" in cols and cols["id"]["key"] == "PK"
    assert "customer_id" in cols


@requires_sqlglot
def test_erdiagram_relationship_from_foreign_key():
    g = s2g.analyze(_DDL)
    rels = g["relationships"]
    assert any(r["from"] == "Orders" and r["to"] == "Customers" for r in rels)
    assert "erDiagram" in g["mermaid"]
    assert "CUSTOMERS" in g["mermaid"] or "Customers" in g["mermaid"]


# ── robustness / graceful degradation ─────────────────────────────────────────

@requires_sqlglot
def test_unparseable_sql_degrades_not_crashes():
    g = s2g.analyze("this is not valid sql at all ;;;")
    assert g["confidence"] == "partial"
    assert g["inferred"]  # says what it couldn't resolve
    assert isinstance(g["mermaid"], str)  # still returns *something*


def test_missing_sqlglot_raises_actionable(monkeypatch):
    # If sqlglot isn't installed, the caller must get an actionable message (the skill then
    # falls back to LLM hand-parsing) — never a bare ImportError deep in a stack.
    monkeypatch.setattr(s2g, "_HAVE_SQLGLOT", False)
    with pytest.raises(s2g.SqlglotUnavailable) as ei:
        s2g.analyze(_QUERY)
    assert "sqlglot" in str(ei.value).lower()


@requires_sqlglot
def test_multiple_objects_diagram_relationships_not_separate():
    # Two CREATE TABLEs with an FK -> ONE erDiagram showing the relationship, not two diagrams.
    g = s2g.analyze(_DDL)
    assert g["mermaid"].count("erDiagram") == 1


# ── Mermaid: wrapping + colour (readability without breaking the parser) ───────

@requires_sqlglot
def test_mermaid_wraps_long_node_labels():
    # A long filter predicate must be broken with <br/> so it stays inside the node box.
    g = s2g.analyze(
        "SELECT * FROM T WHERE some_really_long_column_name = 'a_fairly_long_literal_value_here'"
    )
    m = g["mermaid"]
    assert "<br/>" in m  # long label was wrapped
    # every rendered line stays reasonably short (no runaway one-liner overflowing the box)
    for line in m.splitlines():
        for seg in line.split("<br/>"):
            assert len(seg) < 120, seg


@requires_sqlglot
def test_mermaid_has_classdefs_for_typed_nodes():
    g = s2g.analyze(_QUERY)
    m = g["mermaid"]
    assert "classDef table" in m and "classDef cte" in m
    assert "class " in m  # nodes are assigned to their classes


# ── Excalidraw export: alignment + text containment (deterministic) ────────────

@requires_sqlglot
def test_excalidraw_is_valid_scene_shape():
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    assert ex["type"] == "excalidraw" and ex["version"] == 2
    assert ex["appState"]["theme"] == "light"          # default light, as required
    assert isinstance(ex["elements"], list) and ex["elements"]
    json.loads(json.dumps(ex))                          # round-trips as JSON


@requires_sqlglot
def test_excalidraw_text_is_container_bound_and_fits():
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    rects = {e["id"]: e for e in ex["elements"] if e["type"] == "rectangle"}
    arrows = {e["id"]: e for e in ex["elements"] if e["type"] == "arrow"}
    texts = [e for e in ex["elements"] if e["type"] == "text"]
    assert texts, "every box must carry a label"
    for t in texts:
        cid = t["containerId"]
        if cid is None:  # a free-floating join label — tagged to its arrow via customData
            assert t.get("customData", {}).get("edgeLabelOf") in arrows
            continue
        assert cid in rects, "label bound to a real rectangle"
        rect = rects[cid]
        # binding is bidirectional (rect lists the text back)
        assert any(b.get("id") == t["id"] for b in rect.get("boundElements", []))
        # CONTAINMENT: the wrapped text fits inside its box, both axes
        assert t["height"] <= rect["height"] + 0.5, "text taller than its box"
        assert t["width"] <= rect["width"] + 0.5, "text wider than its box"


@requires_sqlglot
def test_excalidraw_long_filter_grows_its_box_to_contain_text():
    # A deliberately long predicate must wrap AND its box must grow so the text stays contained.
    g = s2g.analyze(
        "SELECT * FROM T WHERE a_very_long_column = 'and_an_even_longer_literal_value_to_force_wrap'"
    )
    ex = s2g.to_excalidraw(g)
    rects = {e["id"]: e for e in ex["elements"] if e["type"] == "rectangle"}
    filt = next(t for t in ex["elements"]
                if t["type"] == "text" and rects[t["containerId"]]["customData"]["kind"] == "filter")
    assert filt["text"].count("\n") >= 1, "long predicate wrapped to multiple lines"
    assert filt["height"] <= rects[filt["containerId"]]["height"] + 0.5


@requires_sqlglot
def test_excalidraw_columns_are_left_to_right_and_aligned():
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    xs = {}
    for e in ex["elements"]:
        if e["type"] == "rectangle":
            xs.setdefault(e["customData"]["kind"], []).append(e["x"])
    # data flows sources -> result -> projection, strictly left to right
    assert max(xs["table"]) < min(xs["result"])
    assert max(xs["result"]) < min(xs["projection"])
    # same-kind boxes in the sources column share an x (vertical alignment)
    assert len(set(round(x) for x in xs["table"])) == 1


@requires_sqlglot
def test_excalidraw_arrows_bind_real_elements():
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    ids = {e["id"] for e in ex["elements"]}
    arrows = [e for e in ex["elements"] if e["type"] == "arrow"]
    assert arrows
    for a in arrows:
        assert a["startBinding"]["elementId"] in ids
        assert a["endBinding"]["elementId"] in ids


@requires_sqlglot
def test_excalidraw_is_deterministic():
    a = json.dumps(s2g.to_excalidraw(s2g.analyze(_QUERY)), sort_keys=True)
    b = json.dumps(s2g.to_excalidraw(s2g.analyze(_QUERY)), sort_keys=True)
    assert a == b  # same SQL -> byte-identical scene (no random ids/seeds/timestamps)


@requires_sqlglot
def test_excalidraw_works_for_erdiagram_too():
    ex = s2g.to_excalidraw(s2g.analyze(_DDL))
    kinds = {e["customData"]["kind"] for e in ex["elements"] if e["type"] == "rectangle"}
    assert kinds == {"entity"}


# ── pipeline rule: no arrow crosses a box, no arrowhead pile-up ────────────────

@requires_sqlglot
def test_excalidraw_edges_connect_adjacent_columns_only():
    # The rule that makes crossings impossible: every arrow bridges exactly one column gap,
    # so the space an arrow travels through contains no boxes at all.
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    rects = [e for e in ex["elements"] if e["type"] == "rectangle"]
    xs = sorted({round(r["x"], 1) for r in rects})
    col = {r["id"]: xs.index(round(r["x"], 1)) for r in rects}
    for a in (e for e in ex["elements"] if e["type"] == "arrow"):
        src, dst = a["startBinding"]["elementId"], a["endBinding"]["elementId"]
        assert col[dst] == col[src] + 1, f"arrow skips a stage: {src} -> {dst}"


@requires_sqlglot
def test_excalidraw_anded_filters_are_one_where_box():
    # _QUERY has two ANDed predicates (CTE status + outer region) — they must render as ONE
    # WHERE box, not stacked boxes that read like alternative paths.
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    filt_rects = [e for e in ex["elements"]
                  if e["type"] == "rectangle" and e["customData"]["kind"] == "filter"]
    assert len(filt_rects) == 1
    label = next(t for t in ex["elements"]
                 if t["type"] == "text" and t.get("containerId") == filt_rects[0]["id"])
    assert "WHERE" in label["text"] and "AND" in label["text"]


@requires_sqlglot
def test_excalidraw_fan_in_arrows_land_on_distinct_points():
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    by_dst: dict[str, list[dict]] = {}
    for a in (e for e in ex["elements"] if e["type"] == "arrow"):
        by_dst.setdefault(a["endBinding"]["elementId"], []).append(a)
    fanned = [g for g in by_dst.values() if len(g) > 1]
    assert fanned, "the query has a fan-in (several sources into one stage)"
    for group in fanned:
        focuses = [a["endBinding"]["focus"] for a in group]
        end_ys = [round(a["y"] + a["points"][1][1], 1) for a in group]
        assert len(set(focuses)) == len(group), "arrows share a binding focus (pile-up)"
        assert len(set(end_ys)) == len(group), "arrows share an endpoint (pile-up)"


@requires_sqlglot
def test_excalidraw_join_info_lives_inside_source_box():
    # Flowchart arrows carry NO text (in a converging fan, any floating label eventually covers
    # some arrow). The join condition is a sub-line INSIDE the joined table's box instead.
    ex = s2g.to_excalidraw(s2g.analyze(_QUERY))
    rects = {e["id"]: e for e in ex["elements"] if e["type"] == "rectangle"}
    box_labels = [t for t in ex["elements"]
                  if t["type"] == "text" and t.get("containerId") in rects]
    assert any("JOIN" in t["text"] and "customer_id" in t["text"] for t in box_labels), \
        "join type + key must be visible inside the joined table's box"
    # and nothing floats: every text in a flowchart is container-bound
    assert all(t.get("containerId") for t in ex["elements"] if t["type"] == "text")


@requires_sqlglot
def test_excalidraw_no_text_covers_any_arrow():
    # The neatness invariant, checked by sampling every arrow's line: no text element's
    # bounding box may touch any arrow. Run on both diagram types (ER has FK edge labels).
    for sql in (_QUERY, _DDL):
        ex = s2g.to_excalidraw(s2g.analyze(sql))
        texts = [t for t in ex["elements"] if t["type"] == "text"
                 and t.get("customData", {}).get("edgeLabelOf")]
        arrows = [e for e in ex["elements"] if e["type"] == "arrow"]
        for a in arrows:
            (x0, y0), (dx, dy) = (a["x"], a["y"]), a["points"][1]
            for k in range(21):
                px, py = x0 + dx * k / 20, y0 + dy * k / 20
                for t in texts:
                    inside = (t["x"] - 1 <= px <= t["x"] + t["width"] + 1
                              and t["y"] - 1 <= py <= t["y"] + t["height"] + 1)
                    assert not inside, f"label {t['id']} covers arrow {a['id']}"


@requires_sqlglot
def test_mermaid_follows_the_same_pipeline():
    m = s2g.analyze(_QUERY)["mermaid"]
    assert 'where[' in m and "where --> result" in m
    # every join-labelled edge feeds the WHERE stage, never skips ahead to result
    join_lines = [ln for ln in m.splitlines() if "JOIN" in ln]
    assert join_lines and all(ln.rstrip().endswith("where") for ln in join_lines)


# ── SVG / HTML export: self-contained, dual-theme, default light ───────────────

@requires_sqlglot
def test_svg_is_self_contained():
    svg = s2g.to_svg(s2g.analyze(_QUERY))
    assert svg.strip().startswith("<svg") and svg.strip().endswith("</svg>")
    # no external fetches (the xmlns namespace URI is fine — it's not a request)
    assert 'href="http' not in svg and 'src="http' not in svg
    assert "cdn" not in svg.lower()
    assert "prefers-color-scheme" in svg  # standalone SVG supports dark, default light


@requires_sqlglot
def test_html_export_dual_theme_default_light_no_cdn():
    html = s2g.to_html(s2g.analyze(_QUERY), title="Orders", source="test.sql", date="2026-07-21")
    low = html.lower()
    assert low.startswith("<!doctype html")
    assert 'data-theme="light"' in html            # DEFAULT is light
    assert '[data-theme="dark"]' in html           # dark is available via the toggle
    assert "<svg" in html                          # diagram embedded inline
    assert "cdn" not in low and 'src="http' not in low  # self-contained, no external JS/CSS
    assert "Orders" in html and "test.sql" in html


@requires_sqlglot
def test_render_dispatches_all_formats():
    g = s2g.analyze(_QUERY)
    assert s2g.render(g, "mermaid").startswith("flowchart")
    assert json.loads(s2g.render(g, "excalidraw"))["type"] == "excalidraw"
    assert s2g.render(g, "svg").strip().startswith("<svg")
    assert s2g.render(g, "html").lower().startswith("<!doctype")
    assert json.loads(s2g.render(g, "json"))["diagram_type"] == "flowchart"
    with pytest.raises(ValueError):
        s2g.render(g, "nope")
