"""Extract requirement demand from markdown/text documents."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
LIST_RE = re.compile(r"^\s*[-*]\s+(.+)$")
MUST_RE = re.compile(r"\b(must|should|required|shall|needs?|display|show|report|filter)\b", re.IGNORECASE)


def extract_doc(path: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    section = ""
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return items

    for line_no, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading:
            section = heading.group(2).strip()
            continue
        bullet = LIST_RE.match(line)
        text = bullet.group(1).strip() if bullet else line.strip()
        if not text or not MUST_RE.search(text):
            continue
        items.append(
            {
                "id": f"REQ-{len(items) + 1:04d}",
                "source_file": str(path),
                "line": line_no,
                "section": section,
                "text": text,
                "status": "unreconciled",
            }
        )
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract requirements into requirements_manifest.json.")
    parser.add_argument("--docs", type=Path, action="append", required=True, help="Doc file or directory")
    parser.add_argument("--output", type=Path, required=True, help="Output requirements_manifest.json path")
    args = parser.parse_args()

    requirements: list[dict[str, object]] = []
    for doc in args.docs:
        paths = list(doc.rglob("*")) if doc.is_dir() else [doc]
        for path in paths:
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".rst"}:
                requirements.extend(extract_doc(path))

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirements": requirements,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
