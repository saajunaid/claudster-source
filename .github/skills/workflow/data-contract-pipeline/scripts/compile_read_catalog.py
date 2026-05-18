"""Compile a read model catalog scaffold from a mapping manifest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile read_catalog.json from mappings.")
    parser.add_argument("--mapping", type=Path, required=True, help="mapping_manifest.json")
    parser.add_argument("--output", type=Path, required=True, help="read_catalog.json path")
    args = parser.parse_args()

    mapping = json.loads(args.mapping.read_text(encoding="utf-8-sig"))
    read_models: list[dict[str, Any]] = []
    for idx, item in enumerate(mapping.get("mappings", []), start=1):
        if item.get("status") not in {"partially-backed", "contract-backed"}:
            continue
        read_models.append(
            {
                "query_id": f"read_model_{idx:04d}",
                "ui_id": item.get("ui_id"),
                "ui_name": item.get("ui_name"),
                "source_field_candidate": item.get("source_field_candidate"),
                "parameters": [],
                "sql_or_adapter": "",
                "performance_class": "unknown",
                "notes": "Fill with bounded SQL or file/API adapter before implementation.",
            }
        )

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_models": read_models,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
