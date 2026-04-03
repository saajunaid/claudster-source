from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / ".github" / "runtime-targets.json"

TOOL_MAP: dict[str, list[str]] = {
    "read": ["Read", "Glob"],
    "search": ["Grep"],
    "edit": ["Edit", "Write", "MultiEdit"],
    "execute": ["Bash"],
    "web": ["WebSearch", "WebFetch"],
    "problems": [],
    "testFailure": [],
    "changes": [],
}


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load the runtime export manifest."""
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def ensure_clean_dir(path: Path) -> None:
    """Recreate a directory from scratch."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(source: Path, destination: Path, excluded_names: set[str] | None = None) -> None:
    """Copy a directory tree while excluding top-level names when requested."""
    excluded_names = excluded_names or set()
    destination.mkdir(parents=True, exist_ok=True)

    for child in source.iterdir():
        if child.name in excluded_names:
            continue
        target = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def copy_file(source: Path, destination: Path) -> None:
    """Copy a single file, creating parent directories when necessary."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def convert_tools_to_claude_format(copilot_tools: list[str]) -> str:
    """Map Copilot tool names to Claude agent tool names."""
    claude_tools: list[str] = []

    for tool in copilot_tools:
        normalized = tool.strip()
        if "/" in normalized:
            continue
        for mapped in TOOL_MAP.get(normalized, []):
            if mapped and mapped not in claude_tools:
                claude_tools.append(mapped)

    if not claude_tools:
        claude_tools = ["Read", "Grep", "Glob", "Bash"]

    return ", ".join(claude_tools)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split a markdown file into frontmatter and body."""
    if not text.startswith("---"):
        return "", text

    closing_index = text.find("\n---", 3)
    if closing_index == -1:
        return "", text

    frontmatter = text[4:closing_index]
    body = text[closing_index + 4 :].lstrip("\n")
    return frontmatter, body


def extract_simple_frontmatter(frontmatter: str) -> dict[str, str]:
    """Extract simple frontmatter key/value pairs without a YAML dependency."""
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def extract_tools(frontmatter: str) -> list[str]:
    """Extract tools from a one-line list in frontmatter."""
    for line in frontmatter.splitlines():
        if not line.startswith("tools:"):
            continue
        raw = line.split("[", 1)[-1].rsplit("]", 1)[0]
        return [item.strip().strip('"').strip("'") for item in raw.split(",") if item.strip()]
    return []


def convert_agent_to_claude(source_file: Path, destination_file: Path) -> None:
    """Convert a Copilot .agent.md file into Claude-compatible agent markdown."""
    content = source_file.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(content)
    data = extract_simple_frontmatter(frontmatter)
    claude_tools = convert_tools_to_claude_format(extract_tools(frontmatter))

    lines = [
        "---",
        f"name: {data.get('name', source_file.stem)}",
        f'description: {json.dumps(data.get("description", ""))}',
        f'tools: {json.dumps(claude_tools)}',
        "---",
        "",
        body,
    ]
    destination_file.parent.mkdir(parents=True, exist_ok=True)
    destination_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def convert_instruction_to_rule(source_file: Path, destination_file: Path) -> None:
    """Convert a Copilot instruction file into a Claude rules file."""
    content = source_file.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(content)
    data = extract_simple_frontmatter(frontmatter)
    description = data.get("description", "")
    globs = data.get("applyTo", "**")

    lines = [
        "---",
        f'description: {json.dumps(description)}',
        f'globs: [{json.dumps(globs)}]',
        "---",
        "",
        body,
    ]
    destination_file.parent.mkdir(parents=True, exist_ok=True)
    destination_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def export_target(manifest: dict[str, Any], target: dict[str, Any]) -> None:
    """Export one runtime target from the canonical .github source."""
    canonical_root = PROJECT_ROOT / manifest["canonical_root"]
    output_root = PROJECT_ROOT / manifest["output_root"] / target["name"]
    workspace_root = output_root / target["workspace_root"]
    exclusions = set(manifest.get("exclusions", {}).get("skills", []))

    ensure_clean_dir(output_root)

    for copy_spec in target.get("copies", []):
        source = canonical_root / copy_spec["source"]
        destination = workspace_root / copy_spec["destination"]
        excluded_names = exclusions if copy_spec["source"] == "skills" else set()
        copy_tree(source, destination, excluded_names=excluded_names)

    for file_spec in target.get("files", []):
        source = canonical_root / file_spec["source"]
        destination = workspace_root / file_spec["destination"]
        copy_file(source, destination)

    for transform_spec in target.get("transforms", []):
        source_dir = canonical_root / transform_spec["source"]
        destination_dir = workspace_root / transform_spec["destination"]
        destination_dir.mkdir(parents=True, exist_ok=True)

        if transform_spec["type"] == "agents_to_claude":
            for source_file in source_dir.glob("*.agent.md"):
                destination_file = destination_dir / f"{source_file.stem.replace('.agent', '')}.md"
                convert_agent_to_claude(source_file, destination_file)
        elif transform_spec["type"] == "instructions_to_rules":
            for source_file in source_dir.glob("*.instructions.md"):
                destination_file = destination_dir / f"{source_file.stem.replace('.instructions', '')}.md"
                convert_instruction_to_rule(source_file, destination_file)
        else:
            raise ValueError(f"Unsupported transform type: {transform_spec['type']}")


def main() -> int:
    """Build runtime-specific resource exports from the canonical .github source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to the runtime export manifest.",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    for target in manifest["targets"]:
        export_target(manifest, target)
        print(f"[OK] Exported {target['name']} resources")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
