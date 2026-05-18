"""Generate OpenAPI and MCP contract scaffolds from a read catalog."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "read-model"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_openapi(read_catalog: dict[str, Any], title: str) -> str:
    lines = [
        "openapi: 3.1.0",
        "info:",
        f"  title: {title}",
        "  version: 0.1.0",
        "  description: Generated scaffold. Review auth, errors, examples, and schemas before implementation.",
        "paths:",
    ]
    read_models = read_catalog.get("read_models", [])
    if not read_models:
        lines.append("  {}")
        return "\n".join(lines) + "\n"

    for model in read_models:
        query_id = str(model.get("query_id", "read_model"))
        name = str(model.get("ui_name") or query_id)
        path = f"/data/{slugify(query_id)}"
        operation_id = slugify(query_id).replace("-", "_")
        lines.extend(
            [
                f"  {path}:",
                "    get:",
                f"      operationId: {operation_id}",
                f"      summary: Read data for {name}",
                "      tags:",
                "        - data-contract",
                "      parameters: []",
                "      responses:",
                "        '200':",
                "          description: Successful response",
                "          content:",
                "            application/json:",
                "              schema:",
                "                type: object",
                "                additionalProperties: true",
                "        '400':",
                "          description: Invalid request",
                "        '401':",
                "          description: Unauthorized",
                "        '500':",
                "          description: Server error",
            ]
        )
    return "\n".join(lines) + "\n"


def build_mcp(read_catalog: dict[str, Any], title: str) -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    for model in read_catalog.get("read_models", []):
        query_id = str(model.get("query_id", "read_model"))
        name = slugify(query_id).replace("-", "_")
        ui_name = str(model.get("ui_name") or query_id)
        tools.append(
            {
                "name": f"get_{name}",
                "title": f"Get {ui_name}",
                "description": "Generated MCP tool scaffold. Review auth, PII, rate limits, and schema before implementation.",
                "readOnlyHint": True,
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
                "outputSchema": {"type": "object", "additionalProperties": True},
                "sourceQueryId": query_id,
                "piiClassification": "review-required",
                "auth": "review-required",
                "rateLimit": "review-required",
            }
        )
        resources.append(
            {
                "uri": f"app://data-contract/{slugify(query_id)}",
                "name": ui_name,
                "description": "Generated MCP resource scaffold for a backed read model.",
                "sourceQueryId": query_id,
                "mimeType": "application/json",
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "tools": tools,
        "resources": resources,
        "notes": [
            "Expose only approved, backed, permissioned capabilities.",
            "Review PII classification before enabling MCP clients.",
            "Generated schemas are scaffolds and must be tightened before production.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenAPI and MCP contract scaffolds.")
    parser.add_argument("--read-catalog", type=Path, required=True, help="read_catalog.json")
    parser.add_argument("--openapi", type=Path, required=True, help="openapi_contract.yaml output")
    parser.add_argument("--mcp", type=Path, required=True, help="mcp_contract.json output")
    parser.add_argument("--title", default="Data Contract API", help="Contract title")
    args = parser.parse_args()

    read_catalog = load_json(args.read_catalog)
    args.openapi.parent.mkdir(parents=True, exist_ok=True)
    args.mcp.parent.mkdir(parents=True, exist_ok=True)
    args.openapi.write_text(build_openapi(read_catalog, args.title), encoding="utf-8")
    args.mcp.write_text(json.dumps(build_mcp(read_catalog, args.title), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
