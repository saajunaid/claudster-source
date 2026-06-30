"""Unit tests for claude-harness/scripts/check_doc_coverage.py — the generic doc-discipline checker.

Ported from rev-sight (commit 153b835) and generalised for the claudster harness:
  • the pure-function core is unchanged (text in → result out), so those tests port verbatim;
  • the filesystem glue (`run`) now takes an explicit `root` and AUTO-SKIPS when inputs are absent
    (two behaviour inversions vs the rev-sight reference — see the *_skips_* and *silent* tests below);
  • only the two high-confidence invariants (missing route, dangling doc-map link) hard-fail in
    --check mode — the teeth tests assert that, the skip tests assert the "no noise" contract.

The module lives under claude-harness/scripts/ (NOT the repo-root scripts/), so the shim points there.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "claude-harness" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_doc_coverage as cdc  # noqa: E402


# --------------------------------------------------------------------------- #
# Pure-function core — ported verbatim from rev-sight (filesystem-free).
# --------------------------------------------------------------------------- #
class TestExtractCodeRoutes:
    def test_extracts_single_and_double_quoted_paths(self):
        text = """
        const x = { path: '/control-points' }
        const y = { path: "/raworkbench/query-editor" }
        """
        assert cdc.extract_code_routes(text) == {
            "/control-points",
            "/raworkbench/query-editor",
        }

    def test_ignores_non_slash_path_values(self):
        text = "path: 'relative'  path: '/real'"
        assert cdc.extract_code_routes(text) == {"/real"}

    def test_empty_text_returns_empty_set(self):
        assert cdc.extract_code_routes("") == set()


class TestExtractDocumentedRoutes:
    def test_captures_backtick_wrapped_routes(self):
        md = "### Command Centre — `/control-points`\n| `/cost` | Cost |"
        assert cdc.extract_documented_routes(md) == {"/control-points", "/cost"}

    def test_excludes_api_endpoint_paths(self):
        md = "calls `GET` `/api/v1/assurance/exceptions` and lives at `/exceptions`"
        assert cdc.extract_documented_routes(md) == {"/exceptions"}

    def test_index_route_is_documented(self):
        md = "### Executive View — `/`"
        assert "/" in cdc.extract_documented_routes(md)


class TestRouteCoverageGaps:
    def test_missing_route_is_flagged(self):
        route_tree = "path: '/cost'  path: '/exceptions'"
        guide = "### Exceptions — `/exceptions`"
        missing, extra = cdc.route_coverage_gaps(route_tree, guide)
        assert missing == ["/cost"]
        assert extra == []

    def test_extra_documented_route_not_in_code(self):
        route_tree = "path: '/exceptions'"
        guide = "`/exceptions` and a phantom `/rate-integrity`"
        missing, extra = cdc.route_coverage_gaps(route_tree, guide)
        assert missing == []
        assert extra == ["/rate-integrity"]

    def test_ignore_set_suppresses_known_aliases(self):
        route_tree = "path: '/home'  path: '/exceptions'"
        guide = "`/exceptions`"
        missing, extra = cdc.route_coverage_gaps(route_tree, guide, ignore={"/home"})
        assert missing == []

    def test_results_are_sorted(self):
        route_tree = "path: '/zebra'  path: '/alpha'"
        guide = ""
        missing, _ = cdc.route_coverage_gaps(route_tree, guide)
        assert missing == ["/alpha", "/zebra"]


class TestOversizeFiles:
    def test_returns_only_over_budget_sorted(self):
        lengths = {"a/CLAUDE.md": 50, "b/CLAUDE.md": 200, "c/CLAUDE.md": 130}
        assert cdc.oversize_files(lengths, budget=120) == [
            ("b/CLAUDE.md", 200),
            ("c/CLAUDE.md", 130),
        ]

    def test_at_budget_is_not_oversize(self):
        assert cdc.oversize_files({"x": 120}, budget=120) == []


class TestDocmapIssues:
    def test_orphan_is_governed_but_not_indexed(self):
        entries = {"UI_PAGE_GUIDE.md"}
        governed = {"UI_PAGE_GUIDE.md", "STACK.md"}
        existing = {"UI_PAGE_GUIDE.md", "STACK.md"}
        orphans, dangling = cdc.docmap_issues(entries, governed, existing)
        assert orphans == ["STACK.md"]
        assert dangling == []

    def test_dangling_is_indexed_but_missing_on_disk(self):
        entries = {"docs/gone.md"}
        governed: set[str] = set()
        existing: set[str] = set()
        orphans, dangling = cdc.docmap_issues(entries, governed, existing)
        assert dangling == ["docs/gone.md"]


class TestExtractDocmapEntries:
    def test_extracts_markdown_link_targets(self):
        md = "- [Page guide](UI_PAGE_GUIDE.md) — pages\n- [Stack](./STACK.md) — deps"
        assert cdc.extract_docmap_entries(md) == {"UI_PAGE_GUIDE.md", "STACK.md"}

    def test_ignores_non_md_links(self):
        md = "[site](https://example.com) [doc](docs/x.md)"
        assert cdc.extract_docmap_entries(md) == {"docs/x.md"}

    def test_ignores_links_inside_html_comments(self):
        # Example links in a maintenance comment must not register as real entries (would dangle).
        md = "<!--\nexample: [DB](../../docs/reference/DB.md)\n-->\n- [Real](real.md)"
        assert cdc.extract_docmap_entries(md) == {"real.md"}


# --------------------------------------------------------------------------- #
# Filesystem glue — generic `run(root, check)` with graceful auto-skip.
# These are the claudster generalisation: a doc-less / backend-only repo must
# pass silently, and the two hard invariants must still block in --check mode.
# --------------------------------------------------------------------------- #
def _write(root: Path, rel: str, text: str = "x") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class TestGracefulSkip:
    def test_backend_only_repo_passes_silently(self, tmp_path, capsys):
        """No frontend, no DOC-MAP, lean CLAUDE.md → exit 0, zero output (the 'no noise' contract)."""
        _write(tmp_path, "pyproject.toml", "[project]\nname='x'\n")
        _write(tmp_path, "CLAUDE.md", "# tiny\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert out.strip() == ""

    def test_docmap_check_skips_when_docmap_absent(self, tmp_path, capsys):
        """INVERSION 1: rev-sight hard-failed when DOC-MAP was absent; the generic checker skips."""
        _write(tmp_path, "CLAUDE.md", "# tiny\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0  # NOT 1
        assert "doc-map not found" not in out
        assert "DOC-MAP" not in out

    def test_route_check_skips_when_routetree_absent(self, tmp_path, capsys):
        """INVERSION 2: rev-sight warned 'run npm run build'; the generic checker is silent."""
        # A valid, link-free DOC-MAP so check 2 is active and clean, isolating the route skip.
        _write(tmp_path, ".claudster/kb/DOC-MAP.md", "# Doc map\n\nNo links yet.\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "npm run build" not in out
        assert "route" not in out.lower()


class TestHardInvariantsBlock:
    def test_missing_route_hard_fails_in_check_mode(self, tmp_path, capsys):
        """Teeth: a live route absent from the page guide blocks the gate (--check → exit 1)."""
        _write(tmp_path, "frontend/src/routeTree.gen.ts", "const r = { path: '/cost' }")
        _write(tmp_path, "UI_PAGE_GUIDE.md", "# Pages\n\n(no routes documented)\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 1
        assert "/cost" in out

    def test_dangling_docmap_link_hard_fails_in_check_mode(self, tmp_path, capsys):
        """Teeth: a doc-map link to a missing file blocks the gate (--check → exit 1)."""
        _write(tmp_path, ".claudster/kb/DOC-MAP.md", "- [Gone](../../docs/gone.md)\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 1
        assert "gone.md" in out

    def test_hard_failure_does_not_block_in_human_mode(self, tmp_path, capsys):
        """Without --check (human report) a hard failure prints but returns 0."""
        _write(tmp_path, "frontend/src/routeTree.gen.ts", "const r = { path: '/cost' }")
        _write(tmp_path, "UI_PAGE_GUIDE.md", "# Pages\n")
        rc = cdc.run(tmp_path, check=False)
        assert rc == 0


class TestWarnTier:
    """The soft tier must WARN but never block — guards against a future edit that promotes a
    soft signal into hard_failures (which would silently turn the gate over-strict)."""

    def test_orphan_warns_but_does_not_block(self, tmp_path, capsys):
        """A governed doc the DOC-MAP fails to index warns, yet --check still returns 0."""
        _write(tmp_path, "STACK.md", "# Stack\n")
        _write(tmp_path, ".claudster/kb/DOC-MAP.md", "# Doc map\n\nNo links yet.\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "STACK.md" in out
        assert "does not index" in out

    def test_phantom_route_warns_but_does_not_block(self, tmp_path, capsys):
        """A documented route not in code warns, yet --check still returns 0."""
        _write(tmp_path, "frontend/src/routeTree.gen.ts", "const r = { path: '/real' }")
        _write(tmp_path, "UI_PAGE_GUIDE.md", "Pages: `/real` and a phantom `/gone`\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "/gone" in out

    def test_oversize_claude_md_warns_but_does_not_block(self, tmp_path, capsys):
        """An oversize always-loaded CLAUDE.md warns, yet --check still returns 0."""
        _write(tmp_path, "CLAUDE.md", "\n".join(f"line {i}" for i in range(cdc.CLAUDE_MD_BUDGET + 5)))
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "budget" in out
