"""Generic doc-discipline checker for claudster-managed repos.

Lifted from rev-sight (commit 153b835) and made harness-generic: the same route-drift /
doc-map-integrity / CLAUDE.md-budget checks, but every check **auto-skips** when its inputs
are absent, so a backend-only or doc-less repo passes silently with no noise. Read-only; never writes.

Three checks (all relative to a passed-in repo root — no module-level ROOT):

1. **Page-guide route coverage** — every live route in ``frontend/src/routeTree.gen.ts`` has an
   entry in ``UI_PAGE_GUIDE.md``. A missing entry is a hard failure. Absent route tree OR page
   guide → skip **silently** (a backend repo must not be nagged to "run npm run build").
2. **Doc-map integrity** — every link in ``.claudster/kb/DOC-MAP.md`` resolves (dangling = hard
   failure), and every KB note (``.claudster/kb/*.md``) is indexed in it (orphan = warning). Only the
   curated KB is governed — the wider ``docs/`` folder is NOT policed. Absent doc-map → **skip**.
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
import os
import re
import sys
from pathlib import Path

# Shared per-repo config reader (fail-open). Fall back to no-op shims if it's ever absent, so the
# gate degrades to baked-in defaults rather than crashing.
try:
    from claudster_config import get_int, get_str, get_str_list, load_config
except Exception:  # pragma: no cover - defensive shim
    def load_config(root, section):  # type: ignore
        return {}

    def get_int(cfg, key, default):  # type: ignore
        return default

    def get_str(cfg, key, default):  # type: ignore
        return default

    def get_str_list(cfg, key, default):  # type: ignore
        return default

# Directories never worth scanning for CLAUDE.md — pruned DURING the walk so we never descend into a
# huge/vendored tree (and never trip over a broken symlink inside node_modules, which crashes rglob).
_SKIP_DIRS = {".venv", "venv", "node_modules", ".git", "__pycache__", ".mypy_cache",
              ".ruff_cache", ".pytest_cache", ".tanstack", "dist", "build"}

# Default locations, relative to the repo root passed into run(). Generic — no repo-specific names.
DEFAULT_ROUTE_TREE = "frontend/src/routeTree.gen.ts"
DEFAULT_PAGE_GUIDE = "UI_PAGE_GUIDE.md"
DEFAULT_DOC_MAP = ".claudster/kb/DOC-MAP.md"

# Routes intentionally undocumented in the page guide (pure framework/internal paths). Keep tiny.
IGNORE_ROUTES: frozenset[str] = frozenset()

# Always-loaded context files; keep them lean. Warning only.
CLAUDE_MD_BUDGET = 200

# The doc-map governs ONLY the curated KB it indexes (.claudster/kb/). The wider docs/ folder is the
# project's own documentation and is intentionally NOT policed — the KB is the code-relevant set the
# team curates. Orphan = a KB note that isn't indexed in the doc-map (warning only). Scoping this to
# the KB means zero assumptions about any project's docs/ layout, and no noise.
GOVERNED_GLOBS: tuple[str, ...] = (
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
    # os.walk with in-place dir pruning: skip vendored/generated trees DURING traversal so we never
    # descend into node_modules (slow, and a broken symlink there raises FileNotFoundError mid-rglob).
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        if "CLAUDE.md" not in filenames:
            continue
        path = Path(dirpath) / "CLAUDE.md"
        try:
            rel = path.relative_to(root).as_posix()
            # errors="replace": scans arbitrary repo files; a non-UTF-8 CLAUDE.md must not crash the gate.
            lengths[rel] = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            continue  # vanished/locked file mid-scan — skip, never crash the gate
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


# --------------------------------------------------------------------------- #
# Doc-map generation & reindex — deterministic scaffolding / backfill for repos
# that have the harness but no KB yet (the KB was introduced late). ADDITIVE: it
# creates a missing map and indexes un-indexed KB notes, but never deletes a
# human-written row (mirrors knowledge-transfer's "append, don't delete"); a
# dangling link is *reported*, not removed. Reused by setup_project_ai for the
# fresh-scaffold path so both share one implementation.
# --------------------------------------------------------------------------- #

# Root-level docs worth linking from a fresh map, each with a canned one-liner. Only the
# ones that actually exist get linked (a dangling link is a hard gate failure).
_KNOWN_ROOT_DOCS: tuple[tuple[str, str], ...] = (
    ("README.md", "Repo overview — what it is, how to run it."),
    ("ARCHITECTURE.md", "System architecture."),
    ("DESIGN.md", "Design notes / decisions."),
    ("MIGRATION.md", "Migration / cutover notes."),
    ("CONTRIBUTING.md", "How to contribute / dev setup."),
    ("CHANGELOG.md", "Release history."),
    ("ROADMAP.md", "Roadmap."),
)
_MAX_DISCOVERED_DOCS = 8   # cap docs/ links so a large docs tree can't bloat the map

_DOCMAP_SCAFFOLD = """\
# DOC-MAP — {name} code knowledge index (the KB)

> **What this is:** the curated index of the docs that matter for understanding *this codebase* —
> one line each: what it is and when to read it. A router, not a summary; detail lives in the linked
> docs. KB notes live beside this file in `.claudster/kb/`.
>
> **Discipline:** kept honest by [`check_doc_coverage.py`](../../scripts/check_doc_coverage.py) —
> every link here must resolve (a link to a missing file is a **hard failure**), and a KB note
> (`.claudster/kb/*.md`) not indexed here **warns**. Only `.claudster/kb/*.md` is governed.

## Read first
1. `CLAUDE.md` — project laws + the dev harness (if the repo has one).
2. The entries below, by area.

## Knowledge base (`.claudster/kb/`)

| Doc | What / when to read |
|---|---|
| _(no KB notes yet — add them here as links)_ | |

## Other key code-relevant docs

| Doc | What / when to read |
|---|---|
| _(optionally link a README, design doc, or runbook)_ | |

---

*Governed = `.claudster/kb/*.md` only (must be indexed here). The wider repo docs are not policed.*
"""


def discover_reference_docs(root: Path) -> list[tuple[str, str]]:
    """Deterministically find code-relevant docs worth linking from a fresh map.

    Returns ``(repo-root-relative posix path, one-line description)`` pairs. Only **existing** files
    are returned (a dangling link would hard-fail the gate). Scans the known root docs, then
    ``docs/**/*.md`` (sorted, capped); never the KB itself or vendored trees.
    """
    root = Path(root)
    found: list[tuple[str, str]] = []
    for name, desc in _KNOWN_ROOT_DOCS:
        if (root / name).is_file():
            found.append((name, desc))
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        rels: list[str] = []
        for p in sorted(docs_dir.rglob("*.md")):
            if p.is_file() and not any(part in _SKIP_DIRS for part in p.parts):
                rels.append(p.relative_to(root).as_posix())
        found.extend((rel, "Reference doc.") for rel in rels[:_MAX_DISCOVERED_DOCS])
    return found


def _row(target: str, label: str, desc: str) -> str:
    """One markdown table row: ``| [label](target) | desc |``."""
    return f"| [{label}]({target}) | {desc} |"


def reference_rows(root: Path) -> list[str]:
    """Table rows for every discovered reference doc, its link written relative to the doc-map dir.

    The doc-map lives two levels deep (`.claudster/kb/`), so a repo-root path is reached via `../../`.
    """
    return [_row("../../" + rel, rel, desc) for rel, desc in discover_reference_docs(root)]


def kb_note_rows(root: Path, indexed: set[str] = frozenset()) -> list[str]:
    """Rows for `.claudster/kb/*.md` notes (excluding DOC-MAP), skipping already-indexed ones.

    ``indexed`` holds repo-root-relative paths already linked in the map. The description is a plain
    nudge (NOT an ``_(…)_`` placeholder, so a later reindex won't drop it) for the agent/human to fill.
    """
    root = Path(root)
    rows: list[str] = []
    for p in sorted((root / ".claudster" / "kb").glob("*.md")):
        rel = p.relative_to(root).as_posix()
        if p.name == "DOC-MAP.md" or rel in indexed:
            continue
        rows.append(_row(p.name, p.name, "auto-indexed — add a one-line 'when to read'."))
    return rows


def insert_table_rows(text: str, heading_contains: str, rows: list[str]) -> str:
    """Append ``rows`` to the markdown table under the first ``## …heading_contains…`` heading. Pure.

    Drops italic placeholder rows (a first cell containing ``_(``) when adding real rows. If the
    heading or its table can't be located, returns ``text`` unchanged — fail-safe, never corrupts.
    """
    if not rows:
        return text
    lines = text.splitlines()
    heading = next(
        (i for i, ln in enumerate(lines)
         if ln.strip().startswith("## ") and heading_contains.lower() in ln.strip().lower()),
        None,
    )
    if heading is None:
        return text
    start = end = None
    for i in range(heading + 1, len(lines)):
        s = lines[i].strip()
        if s.startswith("## "):
            break
        if s.startswith("|"):
            start = i if start is None else start
            end = i
        elif start is not None and not s:
            break
    if start is None:
        return text
    head = lines[start:start + 2]                     # header row + |---| separator
    body = [b for b in lines[start + 2:end + 1] if "_(" not in b]  # existing rows minus placeholders
    return "\n".join(lines[:start] + head + body + rows + lines[end + 1:])


def build_docmap(root: Path, project_name: str = "project") -> str:
    """Full DOC-MAP text for a fresh repo: scaffold + discovered reference docs + existing KB notes."""
    text = _DOCMAP_SCAFFOLD.replace("{name}", project_name)
    text = insert_table_rows(text, "Knowledge base", kb_note_rows(root))
    text = insert_table_rows(text, "Other key", reference_rows(root))
    return text


def dangling_as_written(text: str, doc_map_file: Path, root: Path) -> list[str]:
    """As-written ``.md`` link targets in ``text`` whose resolved file is missing on disk (sorted).

    Returned verbatim (not root-relative) so a row can be matched and removed as-written by
    :func:`remove_rows_with_targets`.
    """
    return sorted(
        t for t in extract_docmap_entries(text)
        if not (root / _to_root_relative(t, doc_map_file, root)).exists()
    )


def remove_rows_with_targets(text: str, targets: list[str]) -> str:
    """Drop markdown table rows whose link points at any of ``targets`` (as-written). Pure.

    Only ``|``-delimited rows are removed (the index table itself) — prose links are left alone.
    Tolerates a leading ``./`` in the written link, and preserves a trailing newline.
    """
    if not targets:
        return text
    tset = set(targets)

    def _links_dangling(line: str) -> bool:
        return line.lstrip().startswith("|") and any(
            f"]({t})" in line or f"](./{t})" in line for t in tset
        )

    kept = [ln for ln in text.splitlines() if not _links_dangling(ln)]
    out = "\n".join(kept)
    return out + "\n" if text.endswith("\n") else out


def reindex(
    root: Path, project_name: str = "project", write: bool = True, prune: bool = False
) -> tuple[bool, list[str]]:
    """Create a missing DOC-MAP, index un-indexed KB notes, and (with ``prune``) drop dangling rows.

    Returns ``(changed, summary_lines)``. Indexing is additive (never deletes). ``prune`` is the
    explicit, destructive opt-in: it removes index rows that link to now-missing files. Without it,
    dangling links are only *reported* (auto-removing human-written rows would be unsafe by default).
    """
    root = Path(root)
    doc_map = root / DEFAULT_DOC_MAP
    if not doc_map.exists():
        text = build_docmap(root, project_name)
        if write:
            doc_map.parent.mkdir(parents=True, exist_ok=True)
            doc_map.write_text(text, encoding="utf-8", newline="\n")
        return True, [f"created {DEFAULT_DOC_MAP} ({text.count('](')} link(s) pre-indexed)"]

    original = doc_map.read_text(encoding="utf-8")
    entries = {_to_root_relative(t, doc_map, root) for t in extract_docmap_entries(original)}
    governed = _governed_docs(root, GOVERNED_GLOBS) - {doc_map.relative_to(root).as_posix()}
    existing = {e for e in entries if (root / e).exists()}
    orphans, dangling = docmap_issues(entries, governed, existing)

    summary: list[str] = []
    updated = original
    if orphans:
        updated = insert_table_rows(updated, "Knowledge base", kb_note_rows(root, entries))
        summary.append(f"indexed {len(orphans)} KB note(s): " + ", ".join(orphans))
    if dangling:
        if prune:
            updated = remove_rows_with_targets(updated, dangling_as_written(updated, doc_map, root))
            summary.append(f"pruned {len(dangling)} dangling link(s): " + ", ".join(dangling))
        else:
            summary.append(f"{len(dangling)} dangling link(s) to fix (run --prune to remove): "
                           + ", ".join(dangling))
    changed = updated != original
    if changed and write:
        doc_map.write_text(updated, encoding="utf-8", newline="\n")
    if not summary:
        summary.append("DOC-MAP.md already in sync — nothing to do.")
    return changed, summary


def run(root: Path, check: bool) -> int:
    root = Path(root)
    # Optional per-repo overrides ([doc_coverage] in .claudster/config.toml); baked-in defaults otherwise.
    cfg = load_config(root, "doc_coverage")
    route_tree = root / get_str(cfg, "route_tree", DEFAULT_ROUTE_TREE)
    page_guide = root / get_str(cfg, "page_guide", DEFAULT_PAGE_GUIDE)
    doc_map = root / DEFAULT_DOC_MAP
    budget = get_int(cfg, "claude_md_budget", CLAUDE_MD_BUDGET)
    ignore = frozenset(get_str_list(cfg, "ignore_routes", list(IGNORE_ROUTES)))

    hard_failures: list[str] = []
    warnings: list[str] = []

    # 1. Page-guide route coverage. Skip SILENTLY when either input is absent — a backend-only
    #    repo has no route tree and must not be nagged (inversion vs the rev-sight reference).
    if route_tree.exists() and page_guide.exists():
        missing, extra = route_coverage_gaps(
            route_tree.read_text(encoding="utf-8"),
            page_guide.read_text(encoding="utf-8"),
            ignore=ignore,
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
    for name, n in oversize_files(_claude_md_lengths(root), budget):
        warnings.append(f"{name} is {n} lines (> {budget} budget)")

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
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Create a missing DOC-MAP or index un-indexed KB notes (additive; writes the file).",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="With reindex: also REMOVE index rows that link to missing files (destructive; opt-in).",
    )
    args = parser.parse_args()
    root = _repo_root()
    # Reindex/prune are maintenance actions (the `/kb` command drives them), not a gate — run, exit 0.
    if args.reindex or args.prune:
        _changed, summary = reindex(root, root.name, prune=args.prune)
        for line in summary:
            print(f"[kb] {line}")
        sys.exit(0)
    # Resolve the repo root from git (cwd fallback) — the pre-push gate runs from the repo root,
    # so this is correct wherever the checker is copied. Tests call run() with an explicit root.
    sys.exit(run(root, args.check))


if __name__ == "__main__":
    main()
