"""Generic doc-discipline checker for claudster-managed repos.

Lifted from rev-sight (commit 153b835) and made harness-generic: the same route-drift /
doc-map-integrity / CLAUDE.md-budget checks, but every check **auto-skips** when its inputs
are absent, so a backend-only or doc-less repo passes silently with no noise. Read-only; never writes.

Three checks (all relative to a passed-in repo root — no module-level ROOT):

1. **Page-guide route coverage** — every live route in ``frontend/src/routeTree.gen.ts`` has an
   entry in ``UI_PAGE_GUIDE.md``. A missing entry is a hard failure. Absent route tree OR page
   guide → skip **silently** (a backend repo must not be nagged to "run npm run build").
2. **Doc-map integrity** — every curated reference doc is indexed in ``.claudster/kb/DOC-MAP.md``
   (orphan = warning), and every path the map links to exists (dangling = hard failure). Absent
   doc-map → **skip** (NOT a hard failure: a repo without a KB is fine).
3. **CLAUDE.md budget** — always-loaded ``CLAUDE.md`` files stay lean (warning only).

Usage::

    python scripts/check_doc_coverage.py            # human report, exit 0
    python scripts/check_doc_coverage.py --check    # gate mode, exit 1 on a hard failure

Enforcement is tiered: only *missing routes* and *dangling doc-map links* fail the gate (they are
unambiguous and rare). Everything else warns. In --check mode a clean repo prints nothing.

Defaults are baked in as module constants; a per-repo ``.claudster/config.toml [doc_coverage]``
override is a deliberate fast-follow, not part of this version.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Default locations, relative to the repo root passed into run(). Generic — no repo-specific names.
DEFAULT_ROUTE_TREE = "frontend/src/routeTree.gen.ts"
DEFAULT_PAGE_GUIDE = "UI_PAGE_GUIDE.md"
DEFAULT_DOC_MAP = ".claudster/kb/DOC-MAP.md"

# Routes intentionally undocumented in the page guide (pure framework/internal paths). Keep tiny.
IGNORE_ROUTES: frozenset[str] = frozenset()

# Always-loaded context files; keep them lean. Warning only.
CLAUDE_MD_BUDGET = 200

# Curated reference docs the doc-map is expected to index. Conservative on purpose so orphan
# warnings stay signal: archives and the plugin/skill corpus are not governed.
GOVERNED_GLOBS: tuple[str, ...] = (
    "UI_PAGE_GUIDE.md",
    "STACK.md",
    "README.md",
    "CURRENT_STATE.md",
    "PROJECT_LANDSCAPE.md",
    "docs/reference/*.md",
    "docs/architecture/*.md",
    "docs/runbooks/*.md",
    "docs/guides/*.md",
    ".claudster/kb/*.md",
)


# --------------------------------------------------------------------------- #
# Pure functions (no filesystem) — the testable core. Ported verbatim.
# --------------------------------------------------------------------------- #
def extract_code_routes(route_tree_text: str) -> set[str]:
    """Route paths registered in the generated TanStack route tree."""
    return {
        route.strip()
        for route in re.findall(r"""path:\s*['"]([^'"]+)['"]""", route_tree_text)
        if route.strip().startswith("/")
    }


def extract_documented_routes(guide_text: str) -> set[str]:
    """Backtick-wrapped ``/route`` tokens in the page guide, excluding API endpoints.

    HTML comments are stripped first (symmetry with ``extract_docmap_entries``) so an example route
    in a maintenance comment is not mistaken for a documented route (which would warn as a phantom).
    """
    guide_text = re.sub(r"<!--.*?-->", "", guide_text, flags=re.DOTALL)
    found: set[str] = set()
    for token in re.findall(r"`(/[^`]*)`", guide_text):
        token = token.strip()
        if token.startswith("/api/"):
            continue
        found.add(token)
    return found


def route_coverage_gaps(
    route_tree_text: str,
    guide_text: str,
    ignore: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[str], list[str]]:
    """Return ``(missing, extra)`` — live routes absent from the guide, and vice versa."""
    code = extract_code_routes(route_tree_text) - set(ignore)
    documented = extract_documented_routes(guide_text)
    missing = sorted(code - documented)
    extra = sorted(documented - code)
    return missing, extra


def oversize_files(lengths: dict[str, int], budget: int) -> list[tuple[str, int]]:
    """Files whose line count exceeds ``budget``, sorted by name."""
    return sorted((name, n) for name, n in lengths.items() if n > budget)


def extract_docmap_entries(docmap_text: str) -> set[str]:
    """``*.md`` link targets the doc-map points at, as written (markdown link syntax).

    Targets are returned verbatim except for a stripped leading ``./``; ``http(s)`` links are
    excluded. Resolving them against the doc-map's directory is the caller's job (see ``run``).
    Links inside HTML comments are ignored — a doc-map's maintenance guide may show example links
    that don't exist yet, and those must not register as real (dangling) entries.
    """
    docmap_text = re.sub(r"<!--.*?-->", "", docmap_text, flags=re.DOTALL)
    entries: set[str] = set()
    for target in re.findall(r"\]\(([^)]+\.md)\)", docmap_text):
        target = target.strip()
        if target.startswith(("http://", "https://")):
            continue
        if target.startswith("./"):
            target = target[2:]
        entries.add(target)
    return entries


def docmap_issues(
    entries: set[str],
    governed: set[str],
    existing: set[str],
) -> tuple[list[str], list[str]]:
    """Return ``(orphans, dangling)``.

    orphan = a governed reference doc that the map does not index.
    dangling = a path the map links to that does not exist on disk.
    """
    orphans = sorted(governed - entries)
    dangling = sorted(e for e in entries if e not in existing)
    return orphans, dangling


# --------------------------------------------------------------------------- #
# Filesystem glue — all path resolution and skip logic lives here.
# --------------------------------------------------------------------------- #
def _to_root_relative(target: str, doc_map_file: Path, root: Path) -> str:
    """Resolve a doc-map link target (written relative to the doc-map) to a repo-root path."""
    resolved = (doc_map_file.parent / target).resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return target  # outside the repo — leave as-is (will surface as dangling)


def _governed_docs(root: Path, globs: tuple[str, ...]) -> set[str]:
    docs: set[str] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if path.is_file():
                docs.add(path.relative_to(root).as_posix())
    return docs


def _claude_md_lengths(root: Path) -> dict[str, int]:
    lengths: dict[str, int] = {}
    for path in root.rglob("CLAUDE.md"):
        if any(part in {".venv", "node_modules", ".git"} for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        # errors="replace": this scans arbitrary repo files harness-wide; a non-UTF-8 CLAUDE.md
        # must not crash the gate. We only count lines, so replacement chars are harmless.
        lengths[rel] = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    return lengths


def _repo_root() -> Path:
    """Resolve the repo root: git top-level if available, else cwd. Location-independent, so it
    works wherever setup-project-ai copies the checker (and matches the claudster hooks)."""
    try:
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def run(root: Path, check: bool) -> int:
    root = Path(root)
    route_tree = root / DEFAULT_ROUTE_TREE
    page_guide = root / DEFAULT_PAGE_GUIDE
    doc_map = root / DEFAULT_DOC_MAP

    hard_failures: list[str] = []
    warnings: list[str] = []

    # 1. Page-guide route coverage. Skip SILENTLY when either input is absent — a backend-only
    #    repo has no route tree and must not be nagged (inversion vs the rev-sight reference).
    if route_tree.exists() and page_guide.exists():
        missing, extra = route_coverage_gaps(
            route_tree.read_text(encoding="utf-8"),
            page_guide.read_text(encoding="utf-8"),
            ignore=IGNORE_ROUTES,
        )
        if missing:
            hard_failures.append("UI_PAGE_GUIDE.md missing route(s): " + ", ".join(missing))
        if extra:
            warnings.append("UI_PAGE_GUIDE.md documents route(s) not in code: " + ", ".join(extra))

    # 2. Doc-map integrity. Skip when the doc-map is absent — a repo without a KB is fine, NOT a
    #    hard failure (inversion vs the rev-sight reference, which failed here). Links are written
    #    relative to the doc-map's own location; normalise to repo-root-relative before comparing.
    if doc_map.exists():
        raw = extract_docmap_entries(doc_map.read_text(encoding="utf-8"))
        entries = {_to_root_relative(target, doc_map, root) for target in raw}
        governed = _governed_docs(root, GOVERNED_GLOBS) - {doc_map.relative_to(root).as_posix()}
        existing = {e for e in entries if (root / e).exists()}
        orphans, dangling = docmap_issues(entries, governed, existing)
        if dangling:
            hard_failures.append("DOC-MAP.md links to missing file(s): " + ", ".join(dangling))
        if orphans:
            warnings.append("DOC-MAP.md does not index governed doc(s): " + ", ".join(orphans))

    # 3. CLAUDE.md budget (warning only).
    for name, n in oversize_files(_claude_md_lengths(root), CLAUDE_MD_BUDGET):
        warnings.append(f"{name} is {n} lines (> {CLAUDE_MD_BUDGET} budget)")

    for w in warnings:
        print(f"  warning: {w}")

    if hard_failures:
        print("\nDoc coverage check FAILED:")
        for f in hard_failures:
            print(f"  - {f}")
        print("\nFix: add the missing page(s) to UI_PAGE_GUIDE.md / index them in DOC-MAP.md.")
        return 1 if check else 0

    # Quiet on success in gate mode (no noise); give the human a confirmation otherwise.
    if not check:
        print("Doc coverage OK." if not warnings else "\nDoc coverage OK (warnings above).")
    return 0


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 can't encode some doc names
    parser = argparse.ArgumentParser(
        description="Verify reference docs cover the live app; exit non-zero on hard drift.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Gate mode: exit non-zero on a hard failure (missing route / dangling link).",
    )
    args = parser.parse_args()
    # Resolve the repo root from git (cwd fallback) — the pre-push gate runs from the repo root,
    # so this is correct wherever the checker is copied. Tests call run() with an explicit root.
    sys.exit(run(_repo_root(), args.check))


if __name__ == "__main__":
    main()
