"""Reconcile source capability, requirements, and UI demand."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def flatten_source_fields(source_manifest: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    for source in source_manifest.get("sources", []):
        for field in source.get("fields", []):
            value = field.get("path") or field.get("name")
            if value:
                fields.add(str(value).lower())
        for obj in source.get("objects", []):
            for col in obj.get("columns", []):
                name = col.get("name")
                if name:
                    fields.add(str(name).lower())
    return fields


def match_score(text: str, source_fields: set[str]) -> tuple[str, str]:
    normalized = text.lower().replace("_", " ")
    for field in source_fields:
        if field.replace("_", " ") in normalized:
            return "partially-backed", field
    return "unmatched", ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile data contract manifests.")
    parser.add_argument("--sources", type=Path, help="source_manifest.json")
    parser.add_argument("--requirements", type=Path, help="requirements_manifest.json")
    parser.add_argument("--ui-demand", type=Path, help="ui_demand_manifest.json")
    parser.add_argument("--output", type=Path, required=True, help="mapping_manifest.json path")
    parser.add_argument("--gaps", type=Path, required=True, help="gap_register.json path")
    args = parser.parse_args()

    source_manifest = load_json(args.sources)
    requirements_manifest = load_json(args.requirements)
    ui_manifest = load_json(args.ui_demand)
    source_fields = flatten_source_fields(source_manifest)

    mappings: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for item in ui_manifest.get("ui_demand", []):
        status, field = match_score(str(item.get("name", "")), source_fields)
        final_status = "partially-backed" if status == "partially-backed" else "mockup-only"
        record = {
            "ui_id": item.get("id"),
            "ui_name": item.get("name"),
            "ui_kind": item.get("kind"),
            "source_field_candidate": field,
            "status": final_status,
            "notes": (
                "Heuristic match; confirm before code generation."
                if final_status != "mockup-only"
                else "Prototype-only UI demand; remove/replace unless user promotes it with a requirement and source."
            ),
        }
        mappings.append(record)
        if final_status != "partially-backed":
            gaps.append({**record, "gap_type": final_status})

    for req in requirements_manifest.get("requirements", []):
        status, field = match_score(str(req.get("text", "")), source_fields)
        if status != "partially-backed":
            gaps.append(
                {
                    "requirement_id": req.get("id"),
                    "requirement": req.get("text"),
                    "source_field_candidate": field,
                    "status": "required-unplaced",
                    "gap_type": "required-unplaced",
                    "notes": "Requirement needs source/UI placement confirmation.",
                }
            )

    mapping_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_classes": [
            "contract-backed",
            "required-unplaced",
            "source-capability-only",
            "mockup-only",
            "partially-backed",
            "blocked",
            "deferred",
        ],
        "mappings": mappings,
    }
    gap_register = {
        "generated_at": mapping_manifest["generated_at"],
        "gaps": gaps,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.gaps.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(mapping_manifest, indent=2) + "\n", encoding="utf-8")
    args.gaps.write_text(json.dumps(gap_register, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
