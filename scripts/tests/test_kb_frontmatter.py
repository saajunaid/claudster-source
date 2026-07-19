"""OKF-lite (pass1 Phase 4) — KB notes carry frontmatter; the checker is frontmatter-proof.

Lives in its own file (not test_check_doc_coverage.py) deliberately: that file is contended by
parallel sessions, and these three tests guard a separate concern — the OKF-lite contract.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "claude-harness" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_doc_coverage as cdc  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class TestFrontmatterHandling:
    def test_frontmattered_note_is_governed_and_checked_normally(self, tmp_path, capsys):
        """A KB note that starts with an OKF frontmatter block behaves exactly like one
        without it: indexed row -> no orphan, file exists -> no dangling, --check exit 0."""
        _write(
            tmp_path,
            ".claudster/kb/DOC-MAP.md",
            "# Doc map\n\n| Doc | What |\n|---|---|\n| [note.md](note.md) | A note. |\n",
        )
        _write(
            tmp_path,
            ".claudster/kb/note.md",
            "---\ntype: note\ntitle: A note\ntimestamp: 2026-07-20\n---\n\n# A note\n",
        )
        rc = cdc.run(tmp_path, check=True)
        out = capsys.readouterr().out
        assert rc == 0
        assert "note.md" not in out  # neither orphaned nor dangling

    def test_docmap_frontmatter_links_are_not_entries(self):
        """If DOC-MAP itself ever gains frontmatter, a `.md` link inside that block must
        not register as an entry (it would otherwise show up as a dangling link)."""
        md = "---\ntype: reference\nsee: [ghost](ghost.md)\n---\n# Map\n\n- [real](real.md) x\n"
        assert cdc.extract_docmap_entries(md) == {"real.md"}

    def test_plain_docmap_unaffected_by_the_strip(self):
        md = "# Map\n\n- [real](real.md) x\n"
        assert cdc.extract_docmap_entries(md) == {"real.md"}


class TestRepoKbFrontmatter:
    """Repo-content guard (the OKF-lite mandate): every real KB note in THIS repo declares
    `type:` frontmatter. DOC-MAP.md is the index, not a note - exempt."""

    def test_every_kb_note_declares_type_frontmatter(self):
        notes = sorted((REPO_ROOT / ".claudster" / "kb").glob("*.md"))
        assert notes, "expected at least one KB file"
        offenders = []
        for note in notes:
            if note.name == "DOC-MAP.md":
                continue
            head = note.read_text(encoding="utf-8").lstrip().splitlines()[:8]
            if not head or head[0] != "---" or not any(l.startswith("type:") for l in head):
                offenders.append(note.name)
        assert not offenders, f"KB notes missing OKF-lite frontmatter (type:): {offenders}"
