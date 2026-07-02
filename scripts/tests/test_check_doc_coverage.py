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

    def test_ignores_routes_inside_html_comments(self):
        # An example route in a maintenance comment must not count as documented (else phantom warn).
        md = "<!-- e.g. write the path in backticks: `/exceptions` -->\nReal page `/dashboard`"
        assert cdc.extract_documented_routes(md) == {"/dashboard"}


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

    def test_orphan_kb_note_warns_but_does_not_block(self, tmp_path, capsys):
        """A KB note the DOC-MAP fails to index warns, yet --check still returns 0."""
        _write(tmp_path, ".claudster/kb/domain-model.md", "# Domain model\n")
        _write(tmp_path, ".claudster/kb/DOC-MAP.md", "# Doc map\n\nNo links yet.\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "domain-model.md" in out
        assert "does not index" in out

    def test_docs_folder_is_not_governed(self, tmp_path, capsys):
        """The project's wider docs/ folder is NOT policed — an un-indexed docs/ file never warns."""
        _write(tmp_path, "docs/reference/database.md", "# DB\n")
        _write(tmp_path, "docs/architecture/overview.md", "# Arch\n")
        _write(tmp_path, ".claudster/kb/DOC-MAP.md", "# Doc map\n\nNo links yet.\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert out.strip() == ""  # no orphan warnings for docs/ files

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

    def test_config_overrides_claude_md_budget(self, tmp_path, capsys):
        """A [doc_coverage] claude_md_budget override raises the threshold so a mid-size file passes."""
        _write(tmp_path, "CLAUDE.md", "\n".join(f"line {i}" for i in range(cdc.CLAUDE_MD_BUDGET + 50)))
        _write(tmp_path, ".claudster/config.toml", "[doc_coverage]\nclaude_md_budget = 10000\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "budget" not in out  # raised budget → no oversize warning

    def test_config_overrides_ignore_routes(self, tmp_path, capsys):
        """A route listed in [doc_coverage] ignore_routes no longer hard-fails when undocumented."""
        _write(tmp_path, "frontend/src/routeTree.gen.ts", "const r = { path: '/internal' }")
        _write(tmp_path, "UI_PAGE_GUIDE.md", "# Pages\n\n(none)\n")
        _write(tmp_path, ".claudster/config.toml", '[doc_coverage]\nignore_routes = ["/internal"]\n')
        rc = cdc.run(tmp_path, check=True)
        assert rc == 0  # would be 1 (missing route) without the override

    def test_config_overrides_route_tree_and_page_guide_paths(self, tmp_path, capsys):
        """Custom route_tree / page_guide paths are honored."""
        _write(tmp_path, "app/routes.gen.ts", "const r = { path: '/cost' }")
        _write(tmp_path, "docs/PAGES.md", "# Pages\n")  # does NOT document /cost
        _write(tmp_path, ".claudster/config.toml",
               '[doc_coverage]\nroute_tree = "app/routes.gen.ts"\npage_guide = "docs/PAGES.md"\n')
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 1  # the custom-path route tree IS read → missing route blocks
        assert "/cost" in out

    def test_claude_md_scan_prunes_vendor_dirs(self, tmp_path, capsys):
        """CLAUDE.md inside node_modules/.venv is ignored — the scan prunes vendored trees and never
        descends into them (a broken symlink there would otherwise crash the gate)."""
        big = "\n".join(f"line {i}" for i in range(cdc.CLAUDE_MD_BUDGET + 50))
        _write(tmp_path, "node_modules/pkg/CLAUDE.md", big)
        _write(tmp_path, ".venv/lib/CLAUDE.md", big)
        _write(tmp_path, "CLAUDE.md", "# tiny\n")
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "node_modules" not in out  # pruned → no oversize warning from vendored files
        assert ".venv" not in out


# --------------------------------------------------------------------------- #
# Doc-map generation & reindex (KB backfill) — deterministic scaffolding.
# --------------------------------------------------------------------------- #
class TestDiscoverReferenceDocs:
    def test_finds_known_root_docs_that_exist(self, tmp_path):
        _write(tmp_path, "README.md", "# r")
        _write(tmp_path, "MIGRATION.md", "# m")
        found = dict(cdc.discover_reference_docs(tmp_path))
        assert "README.md" in found and "MIGRATION.md" in found
        assert "CHANGELOG.md" not in found  # absent on disk → never linked (would dangle)

    def test_docs_folder_capped_and_sorted(self, tmp_path):
        for i in range(cdc._MAX_DISCOVERED_DOCS + 4):
            _write(tmp_path, f"docs/n{i:02d}.md", "x")
        docs = [p for p, _ in cdc.discover_reference_docs(tmp_path) if p.startswith("docs/")]
        assert len(docs) == cdc._MAX_DISCOVERED_DOCS
        assert docs == sorted(docs)

    def test_excludes_the_kb_itself(self, tmp_path):
        _write(tmp_path, ".claudster/kb/note.md", "x")
        assert not any(p.startswith(".claudster")
                       for p, _ in cdc.discover_reference_docs(tmp_path))

    def test_prunes_vendored_dirs_under_docs(self, tmp_path):
        """os.walk pruning (fix #2): a vendored subdir under docs/ is skipped, real docs still found."""
        _write(tmp_path, "docs/real.md", "x")
        _write(tmp_path, "docs/node_modules/pkg/readme.md", "x")
        docs = [p for p, _ in cdc.discover_reference_docs(tmp_path)]
        assert "docs/real.md" in docs
        assert not any("node_modules" in p for p in docs)


class TestInsertTableRows:
    _MAP = (
        "## Knowledge base (`.claudster/kb/`)\n\n"
        "| Doc | What / when to read |\n|---|---|\n"
        "| _(placeholder)_ | |\n\n"
        "## Other key code-relevant docs\n\n"
        "| Doc | What / when to read |\n|---|---|\n"
        "| _(placeholder)_ | |\n"
    )

    def test_appends_row_and_drops_placeholder(self):
        out = cdc.insert_table_rows(self._MAP, "Knowledge base", ["| [a.md](a.md) | note |"])
        kb = out.split("## Other")[0]
        assert "[a.md](a.md)" in kb
        assert "_(placeholder)_" not in kb  # placeholder in the KB table removed

    def test_targets_only_the_named_heading(self):
        out = cdc.insert_table_rows(self._MAP, "Other key", ["| [b.md](../../b.md) | ref |"])
        assert "[b.md](../../b.md)" in out.split("## Other")[1]
        assert "b.md" not in out.split("## Other")[0]      # KB section untouched
        assert "_(placeholder)_" in out.split("## Other")[0]

    def test_empty_rows_is_noop(self):
        assert cdc.insert_table_rows(self._MAP, "Knowledge base", []) == self._MAP

    def test_missing_heading_is_noop(self):
        assert cdc.insert_table_rows(self._MAP, "Nonexistent", ["| x | y |"]) == self._MAP

    def test_real_row_with_underscore_paren_in_description_is_preserved(self):
        """DATA-LOSS REGRESSION: a real note whose DESCRIPTION contains '_(' must survive an insert.
        Only the *label* cell (`_(…)_`) marks a scaffold placeholder — descriptions are user prose."""
        text = ("## Knowledge base (`.claudster/kb/`)\n\n"
                "| Doc | What / when to read |\n|---|---|\n"
                "| [auth.md](auth.md) | covers the `_(login)_` edge case |\n")
        out = cdc.insert_table_rows(text, "Knowledge base", ["| [new.md](new.md) | n |"])
        assert "[auth.md](auth.md)" in out   # real row NOT dropped as a placeholder
        assert "[new.md](new.md)" in out     # new row appended


class TestReindex:
    def test_creates_missing_docmap_with_discovered_docs(self, tmp_path):
        _write(tmp_path, "README.md", "# r")
        changed, summary = cdc.reindex(tmp_path, "proj")
        dm = tmp_path / ".claudster" / "kb" / "DOC-MAP.md"
        assert changed and dm.is_file()
        assert "(../../README.md)" in dm.read_text(encoding="utf-8")
        assert cdc.run(tmp_path, check=True) == 0  # fresh map is gate-clean

    def test_indexes_orphan_kb_note_and_passes_gate(self, tmp_path):
        _write(tmp_path, ".claudster/kb/DOC-MAP.md",
               "## Knowledge base (`.claudster/kb/`)\n\n| Doc | X |\n|---|---|\n| _(none)_ | |\n")
        _write(tmp_path, ".claudster/kb/domain.md", "# d")
        changed, summary = cdc.reindex(tmp_path, "proj")
        dm = (tmp_path / ".claudster/kb/DOC-MAP.md").read_text(encoding="utf-8")
        assert changed
        assert "[domain.md](domain.md)" in dm
        assert cdc.run(tmp_path, check=True) == 0        # orphan warning is gone
        assert any("domain.md" in s for s in summary)

    def test_reports_dangling_without_deleting(self, tmp_path):
        _write(tmp_path, ".claudster/kb/DOC-MAP.md",
               "## Knowledge base (`.claudster/kb/`)\n\n| Doc | X |\n|---|---|\n"
               "| [gone](../../docs/gone.md) | x |\n")
        changed, summary = cdc.reindex(tmp_path, "proj")
        dm = (tmp_path / ".claudster/kb/DOC-MAP.md").read_text(encoding="utf-8")
        assert "docs/gone.md" in dm                        # human-written row preserved
        assert any("dangling" in s for s in summary)

    def test_idempotent_when_in_sync(self, tmp_path):
        _write(tmp_path, "README.md", "# r")
        cdc.reindex(tmp_path, "proj")
        changed2, _ = cdc.reindex(tmp_path, "proj")
        assert changed2 is False

    def test_write_is_atomic_no_tmp_left_behind(self, tmp_path):
        """Fix #3: reindex writes via temp+replace and leaves no .tmp turd on success."""
        _write(tmp_path, "README.md", "# r")
        cdc.reindex(tmp_path, "proj")
        assert (tmp_path / ".claudster/kb/DOC-MAP.md").is_file()
        assert not (tmp_path / ".claudster/kb/DOC-MAP.md.tmp").exists()

    def test_auto_indexed_row_survives_a_second_reindex(self, tmp_path):
        """The auto-indexed description must NOT be an _(…)_ placeholder, or the next reindex drops it."""
        _write(tmp_path, ".claudster/kb/DOC-MAP.md",
               "## Knowledge base (`.claudster/kb/`)\n\n| Doc | X |\n|---|---|\n")
        _write(tmp_path, ".claudster/kb/first.md", "# 1")
        cdc.reindex(tmp_path, "proj")
        _write(tmp_path, ".claudster/kb/second.md", "# 2")
        cdc.reindex(tmp_path, "proj")
        dm = (tmp_path / ".claudster/kb/DOC-MAP.md").read_text(encoding="utf-8")
        assert "[first.md](first.md)" in dm and "[second.md](second.md)" in dm


class TestRemoveRowsWithTargets:
    def test_removes_only_matching_table_rows(self):
        text = ("| [a](../../a.md) | keep |\n"
                "| [gone](../../docs/gone.md) | x |\n"
                "a prose mention of ../../docs/gone.md is not a row\n")
        out = cdc.remove_rows_with_targets(text, ["../../docs/gone.md"])
        assert "| [gone]" not in out                     # dangling row removed
        assert "[a](../../a.md)" in out                  # unrelated row kept
        assert "prose mention of ../../docs/gone.md" in out  # non-row prose untouched

    def test_tolerates_leading_dot_slash(self):
        text = "| [g](./gone.md) | x |\n| [k](keep.md) | y |\n"
        out = cdc.remove_rows_with_targets(text, ["gone.md"])
        assert "gone.md" not in out and "[k](keep.md)" in out

    def test_empty_targets_is_noop(self):
        text = "| [a](a.md) | x |\n"
        assert cdc.remove_rows_with_targets(text, []) == text


class TestReindexPrune:
    _MAP = ("## Knowledge base (`.claudster/kb/`)\n\n| Doc | X |\n|---|---|\n"
            "| [live](live.md) | x |\n| [gone](../../docs/gone.md) | x |\n")

    def test_prune_removes_dangling_keeps_valid_and_passes_gate(self, tmp_path):
        _write(tmp_path, ".claudster/kb/DOC-MAP.md", self._MAP)
        _write(tmp_path, ".claudster/kb/live.md", "# live")
        changed, summary = cdc.reindex(tmp_path, "proj", prune=True)
        dm = (tmp_path / ".claudster/kb/DOC-MAP.md").read_text(encoding="utf-8")
        assert "docs/gone.md" not in dm            # dangling row pruned
        assert "[live](live.md)" in dm             # valid row kept
        assert changed and any("pruned" in s for s in summary)
        assert cdc.run(tmp_path, check=True) == 0

    def test_without_prune_keeps_dangling_and_hints(self, tmp_path):
        _write(tmp_path, ".claudster/kb/DOC-MAP.md", self._MAP)
        _write(tmp_path, ".claudster/kb/live.md", "# live")
        _changed, summary = cdc.reindex(tmp_path, "proj")   # prune defaults False
        dm = (tmp_path / ".claudster/kb/DOC-MAP.md").read_text(encoding="utf-8")
        assert "docs/gone.md" in dm                # not removed without opt-in
        assert any("--prune" in s for s in summary)

    def test_prune_and_index_orphan_in_one_run(self, tmp_path):
        _write(tmp_path, ".claudster/kb/DOC-MAP.md",
               "## Knowledge base (`.claudster/kb/`)\n\n| Doc | X |\n|---|---|\n"
               "| [gone](../../docs/gone.md) | x |\n")
        _write(tmp_path, ".claudster/kb/fresh.md", "# f")   # orphan to index
        cdc.reindex(tmp_path, "proj", prune=True)
        dm = (tmp_path / ".claudster/kb/DOC-MAP.md").read_text(encoding="utf-8")
        assert "[fresh.md](fresh.md)" in dm        # orphan indexed
        assert "docs/gone.md" not in dm            # dangling pruned
        assert cdc.run(tmp_path, check=True) == 0
