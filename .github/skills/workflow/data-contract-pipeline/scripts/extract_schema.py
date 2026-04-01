"""
Unified Schema Extractor — Reads any structured data source and generates Pydantic models.

Supported formats:
  - JSON (.json) — recursive nesting, list-of-objects, Field(alias=...)
  - Markdown (.md) — tables, bold KV, code blocks, bullet KV, outer wrapper strip
  - CSV/TSV (.csv/.tsv) — column headers, type inference from sample rows
  - XLSX (.xlsx/.xls) — openpyxl, same column logic as CSV
  - YAML (.yaml/.yml) — safe_load, delegates to dict logic
  - Plain text (.txt/.log) — Key: Value, Key = Value, [Section] headers
  - DB table (--format db) — SQLAlchemy inspect, SQL type mapping

Schema evolution:
  --save-baseline snap.json — snapshot current schema for later comparison
  --diff snap.json — compare current extraction vs baseline

Usage:
    python extract_schema.py data.json
    python extract_schema.py report.md --class-name NetworkReport
    python extract_schema.py data.csv --output models/ingestion/report.py
    python extract_schema.py data.json --save-baseline baseline.json
    python extract_schema.py data_v2.json --diff baseline.json
    python extract_schema.py --format db --connection-string "mssql+pyodbc://..." --table users

Part of the data-contract-pipeline skill.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ExtractedField:
    name: str
    python_type: str
    source_pattern: str
    example_value: str = ""
    section: str = "Root"


@dataclass
class ExtractedSection:
    name: str
    fields: list[ExtractedField] = field(default_factory=list)
    table_rows_model: str | None = None


@dataclass
class SchemaChange:
    field_name: str
    change_type: str  # added, removed, type_changed
    old_value: str = ""
    new_value: str = ""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def to_snake_case(name: str) -> str:
    name = name.replace("**", "").strip().rstrip(":")
    s = re.sub(r"[^a-zA-Z0-9]", "_", name)
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()


def to_class_name(name: str) -> str:
    snake = to_snake_case(name)
    return "".join(word.capitalize() for word in snake.split("_"))


def infer_type_from_value(value: Any) -> str:
    if value is None:
        return "Any | None"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        if not value:
            return "list"
        types = {infer_type_from_value(v) for v in value}
        return f"list[{types.pop()}]" if len(types) == 1 else "list"
    if isinstance(value, dict):
        return "dict"
    v = str(value).strip()
    if not v or v.lower() in ("n/a", "not available", "none", "null", "-"):
        return "str | None"
    if v.lower() in ("true", "false", "yes", "no"):
        return "bool"
    try:
        int(v.replace(",", ""))
        return "int"
    except ValueError:
        pass
    try:
        float(v.replace(",", ""))
        return "float"
    except ValueError:
        pass
    return "str"


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

FORMAT_MAP = {
    ".json": "json",
    ".md": "md",
    ".markdown": "md",
    ".csv": "csv",
    ".tsv": "csv",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".txt": "text",
    ".log": "text",
}


def detect_format(path: Path | None, explicit: str | None) -> str:
    if explicit and explicit != "auto":
        return explicit
    if path:
        return FORMAT_MAP.get(path.suffix.lower(), "text")
    return "text"


# ---------------------------------------------------------------------------
# JSON extractor
# ---------------------------------------------------------------------------


def extract_json_fields(
    data: Any, section: str = "Root"
) -> list[ExtractedSection]:
    sections: list[ExtractedSection] = []
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        return sections

    root = ExtractedSection(name=section)
    for key, value in data.items():
        snake = to_snake_case(key)
        if not snake or not snake.replace("_", "").isalnum():
            continue

        if isinstance(value, dict) and value:
            child_class = to_class_name(key)
            child_sections = extract_json_fields(value, section=key)
            sections.extend(child_sections)
            root.fields.append(
                ExtractedField(
                    name=snake,
                    python_type=child_class,
                    source_pattern="json_nested",
                    example_value=f"{len(value)} keys",
                    section=section,
                )
            )
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            row_class = to_class_name(key) + "Item"
            row_sections = extract_json_fields(value[0], section=f"{key} (Item)")
            for rs in row_sections:
                if rs.name == f"{key} (Item)":
                    rs.name = f"{key} (Row Model)"
            sections.extend(row_sections)
            root.fields.append(
                ExtractedField(
                    name=snake,
                    python_type=f"list[{row_class}]",
                    source_pattern="json_list",
                    example_value=f"{len(value)} items",
                    section=section,
                )
            )
        else:
            example = str(value)[:80] if value is not None else "null"
            root.fields.append(
                ExtractedField(
                    name=snake,
                    python_type=infer_type_from_value(value),
                    source_pattern="json_key",
                    example_value=example,
                    section=section,
                )
            )

    if root.fields:
        sections.insert(0, root)
    return sections


# ---------------------------------------------------------------------------
# Markdown extractor
# ---------------------------------------------------------------------------


def strip_outer_table_wrapper(text: str) -> str:
    """Strip single-cell table wrapper (| col | / | --- | header) from LLM outputs."""
    lines = text.strip().split("\n")
    if len(lines) < 3:
        return text
    header = lines[0].strip()
    if not re.match(r"^\|[^|]+\|\s*$", header):
        return text
    separator = lines[1].strip()
    if not re.match(r"^\|[-\s:]+\|\s*$", separator):
        return text
    content_lines = lines[2:]
    if content_lines:
        first = content_lines[0].strip()
        if first.startswith("|"):
            content_lines[0] = first[1:].lstrip()
    return "\n".join(content_lines)


def parse_markdown_tables(text: str) -> list[dict]:
    tables: list[dict] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        # Separator regex: dash MUST be first in char class to avoid range
        if re.match(r"^\|[-\s:]+\|[-\s:|]+\|$", line.replace(" ", "")):
            if i > 0 and "|" in lines[i - 1]:
                header_row = lines[i - 1].strip()
                data_rows: list[str] = []
                j = i + 1
                while j < len(lines) and "|" in lines[j] and lines[j].strip():
                    data_rows.append(lines[j].strip())
                    j += 1
                header_cells = [
                    c.strip()
                    for c in header_row.strip().strip("|").split("|")
                    if c.strip()
                ]
                tables.append(
                    {
                        "header_row": header_row,
                        "data_rows": data_rows,
                        "column_count": len(header_cells),
                    }
                )
                i = j
                continue
        i += 1
    return tables


def extract_bold_kv(text: str) -> list[ExtractedField]:
    fields: list[ExtractedField] = []
    for m in re.finditer(
        r"\*\*(.+?)\*\*\s*:?\s*(.+?)(?:\s{2,}|$)", text, re.MULTILINE
    ):
        key = m.group(1).strip().rstrip(":")
        value = m.group(2).strip()
        if value.startswith("**") or value.startswith("#"):
            continue
        snake = to_snake_case(key)
        if not snake or not snake.replace("_", "").isalnum():
            continue
        fields.append(
            ExtractedField(
                name=snake,
                python_type=infer_type_from_value(value),
                source_pattern="bold_kv",
                example_value=value[:80],
            )
        )
    return fields


def extract_code_block_kv(block: str) -> list[ExtractedField]:
    fields: list[ExtractedField] = []
    seen: set[str] = set()
    for line in block.split("\n"):
        line = line.strip()
        if not line or line.startswith("\u2501") or line.startswith("---"):
            continue
        for seg in line.split("|"):
            seg = seg.strip()
            m = re.match(r"^([A-Za-z][A-Za-z0-9 _/#()-]+?)\s*:\s*(.+)$", seg)
            if m:
                snake = to_snake_case(m.group(1).strip())
                if (
                    snake
                    and snake.replace("_", "").isalnum()
                    and snake not in seen
                ):
                    seen.add(snake)
                    fields.append(
                        ExtractedField(
                            name=snake,
                            python_type=infer_type_from_value(
                                m.group(2).strip()
                            ),
                            source_pattern="code_block_kv",
                            example_value=m.group(2).strip()[:80],
                        )
                    )
    return fields


def extract_bullet_kv(
    text: str, already: set[str] | None = None
) -> list[ExtractedField]:
    """Extract non-bold bullet KV pairs. Bold bullets are handled by bold_kv."""
    if already is None:
        already = set()
    fields: list[ExtractedField] = []
    seen: set[str] = set()
    for m in re.finditer(
        r"^[-*]\s+(?!\*\*)([^*:]+?)\s*:\s*(.+)$", text, re.MULTILINE
    ):
        snake = to_snake_case(m.group(1).strip())
        if (
            snake
            and snake.replace("_", "").isalnum()
            and snake not in seen
            and snake not in already
        ):
            seen.add(snake)
            fields.append(
                ExtractedField(
                    name=snake,
                    python_type=infer_type_from_value(m.group(2).strip()),
                    source_pattern="bullet_kv",
                    example_value=m.group(2).strip()[:80],
                )
            )
    return fields


def extract_md_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    matches = list(re.finditer(r"^#{1,3}\s+(.+)$", text, re.MULTILINE))
    if not matches:
        return [("Root", text)]
    if matches[0].start() > 0:
        sections.append(("Root", text[: matches[0].start()]))
    for i, m in enumerate(matches):
        heading = re.sub(r"^\d+\.\s*", "", m.group(1).strip())
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((heading, text[m.end() : end].strip()))
    return sections


def extract_markdown(text: str) -> list[ExtractedSection]:
    text = strip_outer_table_wrapper(text)
    result: list[ExtractedSection] = []
    for heading, content in extract_md_sections(text):
        section = ExtractedSection(name=heading)

        # Markdown tables
        for table in parse_markdown_tables(content):
            if table["column_count"] == 2:
                for row in table["data_rows"]:
                    cells = [
                        c.strip().replace("**", "")
                        for c in row.strip().strip("|").split("|")
                    ]
                    if len(cells) >= 2:
                        snake = to_snake_case(cells[0])
                        if snake and snake.replace("_", "").isalnum():
                            section.fields.append(
                                ExtractedField(
                                    name=snake,
                                    python_type=infer_type_from_value(
                                        cells[1].strip()
                                    ),
                                    source_pattern="md_table_kv",
                                    example_value=cells[1].strip()[:80],
                                )
                            )
            elif table["column_count"] >= 3:
                headers = [
                    c.strip().replace("**", "")
                    for c in table["header_row"].strip().strip("|").split("|")
                    if c.strip()
                ]
                first_vals = (
                    [
                        c.strip().replace("**", "")
                        for c in table["data_rows"][0]
                        .strip()
                        .strip("|")
                        .split("|")
                        if c.strip()
                    ]
                    if table["data_rows"]
                    else []
                )
                row_fields = []
                for idx, h in enumerate(headers):
                    snake = to_snake_case(h)
                    if snake and snake.replace("_", "").isalnum():
                        val = first_vals[idx] if idx < len(first_vals) else ""
                        row_fields.append(
                            ExtractedField(
                                name=snake,
                                python_type=infer_type_from_value(val),
                                source_pattern="md_table_multi",
                                example_value=val[:80],
                            )
                        )
                row_class = to_class_name(heading) + "Row"
                result.append(
                    ExtractedSection(
                        name=f"{heading} (Row Model)", fields=row_fields
                    )
                )
                section.fields.append(
                    ExtractedField(
                        name=to_snake_case(heading) + "_rows",
                        python_type=f"list[{row_class}]",
                        source_pattern="md_table_multi",
                        example_value=f"{len(table['data_rows'])} rows",
                    )
                )

        # Code blocks
        for block in re.findall(r"```[^\n]*\n(.*?)```", content, re.DOTALL):
            section.fields.extend(extract_code_block_kv(block))

        # Bold + bullet KV (after removing tables and code blocks)
        clean = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        clean = re.sub(r"^\|.+\|$", "", clean, flags=re.MULTILINE)
        bold_fields = extract_bold_kv(clean)
        section.fields.extend(bold_fields)
        bold_names = {f.name for f in bold_fields}
        section.fields.extend(extract_bullet_kv(clean, already=bold_names))

        if section.fields:
            if heading == "Root":
                result.insert(0, section)
            else:
                result.append(section)
    return result


# ---------------------------------------------------------------------------
# CSV extractor
# ---------------------------------------------------------------------------


def extract_csv(
    text: str, delimiter: str | None = None
) -> list[ExtractedSection]:
    if delimiter is None:
        try:
            dialect = csv.Sniffer().sniff(text[:4096])
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    if len(rows) < 2:
        return []

    headers = rows[0]
    data_rows = rows[1:101]  # sample up to 100 rows for type inference

    section = ExtractedSection(name="Root")
    for col_idx, header in enumerate(headers):
        snake = to_snake_case(header)
        if not snake or not snake.replace("_", "").isalnum():
            snake = f"col_{col_idx}"

        sample_values = [
            r[col_idx]
            for r in data_rows
            if col_idx < len(r) and r[col_idx].strip()
        ]
        if sample_values:
            types = {infer_type_from_value(v) for v in sample_values[:20]}
            if len(types) == 1:
                py_type = types.pop()
            elif types <= {"int", "float"}:
                py_type = "float"
            elif "str | None" in types:
                py_type = "str | None"
            else:
                py_type = "str"
            example = sample_values[0][:80]
        else:
            py_type = "str | None"
            example = ""

        section.fields.append(
            ExtractedField(
                name=snake,
                python_type=py_type,
                source_pattern="csv_col",
                example_value=example,
            )
        )
    return [section]


# ---------------------------------------------------------------------------
# XLSX extractor
# ---------------------------------------------------------------------------


def extract_xlsx(path: Path) -> list[ExtractedSection]:
    try:
        import openpyxl
    except ImportError:
        print(
            "Error: openpyxl required for xlsx. Install: pip install openpyxl",
            file=sys.stderr,
        )
        sys.exit(1)

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    all_sections: list[ExtractedSection] = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if len(rows) < 2:
            continue

        headers = [
            str(c) if c else f"col_{i}" for i, c in enumerate(rows[0])
        ]
        data_rows = rows[1:101]

        section = ExtractedSection(
            name=sheet_name if len(wb.sheetnames) > 1 else "Root"
        )
        for col_idx, header in enumerate(headers):
            snake = to_snake_case(header)
            if not snake or not snake.replace("_", "").isalnum():
                snake = f"col_{col_idx}"

            samples = [
                r[col_idx]
                for r in data_rows
                if col_idx < len(r) and r[col_idx] is not None
            ]
            if samples:
                py_type = infer_type_from_value(samples[0])
                example = str(samples[0])[:80]
            else:
                py_type = "str | None"
                example = ""

            section.fields.append(
                ExtractedField(
                    name=snake,
                    python_type=py_type,
                    source_pattern="xlsx_col",
                    example_value=example,
                )
            )
        all_sections.append(section)

    wb.close()
    return all_sections


# ---------------------------------------------------------------------------
# YAML extractor
# ---------------------------------------------------------------------------


def extract_yaml(text: str) -> list[ExtractedSection]:
    try:
        import yaml
    except ImportError:
        print(
            "Error: PyYAML required. Install: pip install pyyaml",
            file=sys.stderr,
        )
        sys.exit(1)
    data = yaml.safe_load(text)
    return extract_json_fields(data)


# ---------------------------------------------------------------------------
# Plain text extractor
# ---------------------------------------------------------------------------


def extract_text(text: str) -> list[ExtractedSection]:
    sections: list[ExtractedSection] = []
    current_section = "Root"
    current_fields: list[ExtractedField] = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # INI-style section header
        sec_match = re.match(r"^\[(.+)\]$", line)
        if sec_match:
            if current_fields:
                sections.append(
                    ExtractedSection(
                        name=current_section, fields=current_fields
                    )
                )
            current_section = sec_match.group(1).strip()
            current_fields = []
            continue

        # Key: Value or Key = Value
        kv_match = re.match(
            r"^([A-Za-z][A-Za-z0-9 _.-]+?)\s*[:=]\s*(.+)$", line
        )
        if kv_match:
            snake = to_snake_case(kv_match.group(1).strip())
            value = kv_match.group(2).strip()
            if snake and snake.replace("_", "").isalnum():
                current_fields.append(
                    ExtractedField(
                        name=snake,
                        python_type=infer_type_from_value(value),
                        source_pattern="text_kv",
                        example_value=value[:80],
                    )
                )

    if current_fields:
        sections.append(
            ExtractedSection(name=current_section, fields=current_fields)
        )
    return sections


# ---------------------------------------------------------------------------
# DB table extractor
# ---------------------------------------------------------------------------

SQL_TYPE_MAP = {
    "INTEGER": "int",
    "BIGINT": "int",
    "SMALLINT": "int",
    "TINYINT": "int",
    "FLOAT": "float",
    "REAL": "float",
    "DECIMAL": "float",
    "NUMERIC": "float",
    "MONEY": "float",
    "SMALLMONEY": "float",
    "BIT": "bool",
    "VARCHAR": "str",
    "NVARCHAR": "str",
    "CHAR": "str",
    "NCHAR": "str",
    "TEXT": "str",
    "NTEXT": "str",
    "DATE": "str",
    "DATETIME": "str",
    "DATETIME2": "str",
    "SMALLDATETIME": "str",
    "TIME": "str",
    "DATETIMEOFFSET": "str",
    "UNIQUEIDENTIFIER": "str",
    "VARBINARY": "bytes",
    "BINARY": "bytes",
    "IMAGE": "bytes",
}


def extract_db_table(
    connection_string: str, table_name: str
) -> list[ExtractedSection]:
    try:
        from sqlalchemy import create_engine
        from sqlalchemy import inspect as sa_inspect
    except ImportError:
        print(
            "Error: sqlalchemy required. Install: pip install sqlalchemy",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = create_engine(connection_string)
    inspector = sa_inspect(engine)

    columns = inspector.get_columns(table_name)
    section = ExtractedSection(name="Root")
    for col in columns:
        snake = to_snake_case(col["name"])
        sql_type = type(col["type"]).__name__.upper()
        py_type = SQL_TYPE_MAP.get(sql_type, "Any")
        if col.get("nullable", True):
            py_type = f"{py_type} | None"

        section.fields.append(
            ExtractedField(
                name=snake,
                python_type=py_type,
                source_pattern="db_column",
                example_value=f"SQL: {sql_type}",
            )
        )

    engine.dispose()
    return [section] if section.fields else []


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def deduplicate_fields(
    fields: list[ExtractedField],
) -> list[ExtractedField]:
    seen: set[str] = set()
    result: list[ExtractedField] = []
    for f in fields:
        if f.name not in seen:
            seen.add(f.name)
            result.append(f)
    return result


# ---------------------------------------------------------------------------
# Model code generation (shared across all formats)
# ---------------------------------------------------------------------------


def generate_model_source(
    sections: list[ExtractedSection], root_class_name: str = "GeneratedPayload"
) -> str:
    lines = [
        '"""',
        "Auto-generated ingestion model.",
        "Generated by: extract_schema.py",
        "",
        "Review and adjust:",
        "  - Field names and types",
        "  - Which sections become nested models vs flat fields",
        "  - Optional fields and defaults",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
    ]

    row_models: list[ExtractedSection] = []
    content_sections: list[ExtractedSection] = []
    for s in sections:
        if s.name.endswith("(Row Model)"):
            row_models.append(s)
        else:
            content_sections.append(s)

    # Nested/row models first
    for rm in row_models:
        cname = to_class_name(rm.name.replace(" (Row Model)", "")) + "Row"
        if "(Item)" in rm.name:
            cname = (
                to_class_name(
                    rm.name.replace(" (Item)", "").replace(
                        " (Row Model)", ""
                    )
                )
                + "Item"
            )
        rm_fields = deduplicate_fields(rm.fields)
        lines += [
            "",
            f"class {cname}(BaseModel):",
            f'    """Row from {rm.name.replace(" (Row Model)", "")}."""',
            "",
        ]
        if not rm_fields:
            lines.append("    pass")
        else:
            for f in rm_fields:
                comment = (
                    f"  # e.g., {f.example_value}" if f.example_value else ""
                )
                lines.append(f"    {f.name}: {f.python_type}{comment}")
        lines.append("")

    # Root model
    all_fields: list[ExtractedField] = []
    section_markers: list[tuple[int, str]] = []
    for cs in content_sections:
        cs_fields = deduplicate_fields(cs.fields)
        if cs_fields:
            section_markers.append((len(all_fields), cs.name))
            all_fields.extend(cs_fields)
    all_fields = deduplicate_fields(all_fields)

    lines += [
        "",
        f"class {root_class_name}(BaseModel):",
        f'    """1:1 representation of source payload."""',
        "",
        '    model_config = ConfigDict(extra="allow")',
        "",
    ]

    if not all_fields:
        lines.append("    pass")
    else:
        marker_idx = 0
        for i, f in enumerate(all_fields):
            if marker_idx < len(section_markers):
                fidx, sname = section_markers[marker_idx]
                if i >= fidx:
                    lines.append(f"    # --- {sname} ---")
                    marker_idx += 1
            comment = (
                f"  # e.g., {f.example_value}" if f.example_value else ""
            )
            lines.append(f"    {f.name}: {f.python_type}{comment}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Schema evolution
# ---------------------------------------------------------------------------


def sections_to_schema_dict(
    sections: list[ExtractedSection], source: str, fmt: str
) -> dict:
    fields = []
    for s in sections:
        for f in s.fields:
            fields.append(
                {
                    "name": f.name,
                    "type": f.python_type,
                    "source_pattern": f.source_pattern,
                    "section": s.name,
                }
            )
    return {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_file": source,
        "format": fmt,
        "field_count": len(fields),
        "fields": fields,
    }


def save_baseline(
    sections: list[ExtractedSection], path: Path, source: str, fmt: str
) -> None:
    schema = sections_to_schema_dict(sections, source, fmt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(
        f"Baseline saved: {path} ({schema['field_count']} fields)",
        file=sys.stderr,
    )


def diff_baseline(
    sections: list[ExtractedSection], baseline_path: Path
) -> list[SchemaChange]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    old_fields = {f["name"]: f["type"] for f in baseline["fields"]}
    new_fields: dict[str, str] = {}
    for s in sections:
        for f in s.fields:
            if f.name not in new_fields:
                new_fields[f.name] = f.python_type

    changes: list[SchemaChange] = []
    for name in sorted(set(old_fields) | set(new_fields)):
        if name not in old_fields:
            changes.append(
                SchemaChange(name, "added", new_value=new_fields[name])
            )
        elif name not in new_fields:
            changes.append(
                SchemaChange(name, "removed", old_value=old_fields[name])
            )
        elif old_fields[name] != new_fields[name]:
            changes.append(
                SchemaChange(
                    name,
                    "type_changed",
                    old_value=old_fields[name],
                    new_value=new_fields[name],
                )
            )
    return changes


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Unified schema extractor — any format to Pydantic"
    )
    parser.add_argument(
        "source",
        type=Path,
        nargs="?",
        default=None,
        help="Path to source data file",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        default="auto",
        choices=["auto", "json", "md", "csv", "xlsx", "yaml", "db", "text"],
        help="Source format (default: auto-detect from extension)",
    )
    parser.add_argument(
        "--class-name",
        default="GeneratedPayload",
        help="Root class name",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .py file path",
    )
    parser.add_argument(
        "--show-sections",
        action="store_true",
        help="Print extracted sections instead of code",
    )
    parser.add_argument(
        "--save-baseline",
        type=Path,
        default=None,
        help="Save schema snapshot to JSON",
    )
    parser.add_argument(
        "--diff",
        type=Path,
        default=None,
        help="Diff current schema against baseline JSON",
    )
    parser.add_argument(
        "--connection-string",
        default=None,
        help="DB connection string (for --format db)",
    )
    parser.add_argument(
        "--table",
        default=None,
        help="DB table name (for --format db)",
    )
    args = parser.parse_args()

    fmt = detect_format(args.source, args.fmt)

    if fmt == "db":
        if not args.connection_string or not args.table:
            print(
                "Error: --connection-string and --table required for db format",
                file=sys.stderr,
            )
            sys.exit(1)
        sections = extract_db_table(args.connection_string, args.table)
        source_label = f"{args.table} (db)"
    else:
        if not args.source or not args.source.exists():
            print(
                f"Error: File not found: {args.source}", file=sys.stderr
            )
            sys.exit(1)
        source_label = str(args.source)

        if fmt == "xlsx":
            sections = extract_xlsx(args.source)
        else:
            text = args.source.read_text(encoding="utf-8")
            extractors = {
                "json": lambda t: extract_json_fields(json.loads(t)),
                "md": extract_markdown,
                "csv": extract_csv,
                "yaml": extract_yaml,
                "text": extract_text,
            }
            sections = extractors[fmt](text)

    if args.save_baseline:
        save_baseline(sections, args.save_baseline, source_label, fmt)

    if args.diff:
        if not args.diff.exists():
            print(
                f"Error: Baseline not found: {args.diff}", file=sys.stderr
            )
            sys.exit(1)
        changes = diff_baseline(sections, args.diff)
        if not changes:
            print("No schema changes detected.")
        else:
            print(f"{len(changes)} schema change(s) detected:\n")
            for c in changes:
                if c.change_type == "added":
                    print(f"  + ADDED   {c.field_name}: {c.new_value}")
                elif c.change_type == "removed":
                    print(f"  - REMOVED {c.field_name}: {c.old_value}")
                else:
                    print(
                        f"  ~ CHANGED {c.field_name}: {c.old_value} -> {c.new_value}"
                    )
        sys.exit(0)

    if args.show_sections:
        print(f"Extracted {len(sections)} sections:\n")
        for s in sections:
            print(f"  [{s.name}] -- {len(s.fields)} fields")
            for f in s.fields:
                print(
                    f"    {f.name}: {f.python_type} ({f.source_pattern}) = {f.example_value!r}"
                )
            print()
        sys.exit(0)

    source_code = generate_model_source(
        sections, root_class_name=args.class_name
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(source_code, encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(source_code)


if __name__ == "__main__":
    main()
