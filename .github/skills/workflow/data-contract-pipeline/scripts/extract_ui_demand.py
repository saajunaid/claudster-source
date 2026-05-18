"""Extract UI demand from HTML/JSX/TSX mockups and frontend files."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


DATA_REACT_RE = re.compile(r"data-react=[\"']([^\"']+)[\"']")
FUNCTION_COMPONENT_RE = re.compile(r"\bfunction\s+([A-Z][A-Za-z0-9_]*)\s*\(")
CONST_COMPONENT_RE = re.compile(r"\bconst\s+([A-Z][A-Za-z0-9_]*)\s*=\s*\(")
ROUTE_RE = re.compile(r"(?:path|key|href)\s*[:=]\s*[\"']([^\"']+)[\"']")
LABEL_RE = re.compile(r"<(?:h[1-6]|th|label|button|span|div)[^>]*>([^<{]{3,80})<", re.IGNORECASE)
SUPPORTED_SUFFIXES = {".html", ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte"}
SKIP_DIRS = {"node_modules", "dist", "build", ".git", ".next", ".turbo"}


def scan_file(path: Path) -> list[dict[str, object]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    items: list[dict[str, object]] = []
    for match in DATA_REACT_RE.finditer(text):
        items.append(
            {
                "kind": "component-annotation",
                "name": match.group(1),
                "source_file": str(path),
                "status": "unreconciled",
            }
        )
    for regex in (FUNCTION_COMPONENT_RE, CONST_COMPONENT_RE):
        for match in regex.finditer(text):
            items.append(
                {
                    "kind": "component",
                    "name": match.group(1),
                    "source_file": str(path),
                    "status": "unreconciled",
                }
            )
    for match in ROUTE_RE.finditer(text):
        value = match.group(1)
        if len(value) > 1:
            items.append(
                {
                    "kind": "route-or-key",
                    "name": value,
                    "source_file": str(path),
                    "status": "unreconciled",
                }
            )
    for match in LABEL_RE.finditer(text):
        label = " ".join(match.group(1).split())
        if label and not label.startswith("{"):
            items.append(
                {
                    "kind": "label",
                    "name": label,
                    "source_file": str(path),
                    "status": "unreconciled",
                }
            )
    return items


def should_scan(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES and not any(part in SKIP_DIRS for part in path.parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract UI demand into ui_demand_manifest.json.")
    parser.add_argument("--ui", type=Path, action="append", required=True, help="UI file or directory")
    parser.add_argument("--output", type=Path, required=True, help="Output ui_demand_manifest.json path")
    args = parser.parse_args()

    demand: list[dict[str, object]] = []
    for root in args.ui:
        paths = list(root.rglob("*")) if root.is_dir() else [root]
        for path in paths:
            if path.is_file() and should_scan(path):
                demand.extend(scan_file(path))

    for idx, item in enumerate(demand, start=1):
        item["id"] = f"UI-{idx:04d}"

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ui_demand": demand,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
