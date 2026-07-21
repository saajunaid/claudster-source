"""Tests for the db-diagram skill's deterministic SQL->graph extractor.

The extractor is the DETERMINISTIC half of the /mermaid-db + /excalidraw-db feature (the
LLM narration layer wraps its output). It must turn SQL into a stable, typed node/edge model
+ a Mermaid skeleton, reproducibly — that reproducibility is the whole point (diffable, regen-
able diagrams). These golden cases pin that behavior.

The script lives inside the skill dir; loaded by path (it's not a top-level module).
"""
from __future__ import annotations

import importlib.util
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
    assert m.startswith("flowchart TD")
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
