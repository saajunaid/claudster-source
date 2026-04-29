from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass, field
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


CACHE_DIR_NAMES = {"__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".coverage", "htmlcov"}


@dataclass
class ExportStats:
    profile: str
    files_copied: int = 0
    skipped_by_reason: dict[str, int] = field(default_factory=dict)
    dependency_errors: list[str] = field(default_factory=list)

    def bump_skip(self, reason: str, count: int = 1) -> None:
        self.skipped_by_reason[reason] = self.skipped_by_reason.get(reason, 0) + count


def _ignore_caches(_dir: str, names: list[str]) -> list[str]:
    """shutil.copytree ignore callable that drops Python cache dirs at every depth."""
    return [n for n in names if n in CACHE_DIR_NAMES]


def copy_tree(
    source: Path,
    destination: Path,
    excluded_names: set[str] | None = None,
    stats: ExportStats | None = None,
) -> int:
    """Copy a directory tree while excluding top-level names when requested."""
    excluded_names = excluded_names or set()
    destination.mkdir(parents=True, exist_ok=True)
    copied_files = 0

    for root_str, dirs, files in os.walk(source):
        root = Path(root_str)
        rel_root = root.relative_to(source)

        kept_dirs: list[str] = []
        for d in dirs:
            if d in CACHE_DIR_NAMES:
                if stats is not None:
                    stats.bump_skip("cache_dir")
                continue
            if d in excluded_names:
                if stats is not None:
                    stats.bump_skip("excluded_name")
                continue
            kept_dirs.append(d)
        dirs[:] = kept_dirs

        for filename in files:
            if filename in CACHE_DIR_NAMES:
                if stats is not None:
                    stats.bump_skip("cache_file")
                continue
            if filename in excluded_names:
                if stats is not None:
                    stats.bump_skip("excluded_name")
                continue

            src_file = root / filename
            dest_dir = destination / rel_root
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_dir / filename)
            copied_files += 1

    return copied_files


def copy_file(source: Path, destination: Path) -> int:
    """Copy a single file, creating parent directories when necessary."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return 1


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


def _normalize_paths(paths: list[str]) -> set[str]:
    """Normalize manifest path entries to forward-slash relative form."""
    return {p.replace("\\", "/").strip("/") for p in paths if p}


def _check_dependency_closure(workspace_root: Path, stats: ExportStats) -> None:
    """Validate all agent_file references in agents.registry.json resolve in exported profile."""
    registry_path = workspace_root / "tools" / "pipeline-runner" / "agents.registry.json"
    if not registry_path.exists():
        stats.dependency_errors.append(f"Missing registry file: {registry_path}")
        return

    try:
        registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        stats.dependency_errors.append(f"Invalid registry JSON: {exc}")
        return

    for stage_name, info in (registry_data.get("stages") or {}).items():
        agent_file = info.get("agent_file")
        if not agent_file:
            continue
        resolved = workspace_root / agent_file
        if not resolved.exists():
            stats.dependency_errors.append(
                f"Stage '{stage_name}' references missing agent file: {agent_file}"
            )


def export_target(manifest: dict[str, Any], target: dict[str, Any]) -> ExportStats:
    """Export one runtime target from the canonical .github source."""
    canonical_root = PROJECT_ROOT / manifest["canonical_root"]
    output_root = PROJECT_ROOT / manifest["output_root"] / target["name"]
    workspace_root = output_root / target["workspace_root"]
    stats = ExportStats(profile=target["name"])
    exclusion_cfg = manifest.get("exclusions", {})
    skill_exclusions = set(exclusion_cfg.get("skills", []))
    private_roots = set(exclusion_cfg.get("private_roots", []))
    private_paths = _normalize_paths(exclusion_cfg.get("private_paths", []))

    ensure_clean_dir(output_root)

    for copy_spec in target.get("copies", []):
        source_rel = copy_spec["source"].replace("\\", "/").strip("/")
        if source_rel in private_paths or source_rel in private_roots:
            print(f"[SKIP] {target['name']}: copy '{source_rel}' is in exclusions")
            stats.bump_skip("private_path")
            continue
        source = canonical_root / copy_spec["source"]
        destination = workspace_root / copy_spec["destination"]
        excluded_names: set[str] = set(private_roots)
        if source_rel == "skills":
            excluded_names |= skill_exclusions
        excluded_names |= set(copy_spec.get("excluded_names", []))
        if not source.exists():
            stats.bump_skip("missing_source")
            print(f"[SKIP] {target['name']}: source '{source_rel}' does not exist")
            continue
        stats.files_copied += copy_tree(source, destination, excluded_names=excluded_names, stats=stats)

    for file_spec in target.get("files", []):
        source_rel = file_spec["source"].replace("\\", "/").strip("/")
        top = source_rel.split("/", 1)[0]
        if source_rel in private_paths or top in private_paths or top in private_roots:
            print(f"[SKIP] {target['name']}: file '{source_rel}' is in exclusions")
            stats.bump_skip("private_path")
            continue
        source = canonical_root / file_spec["source"]
        destination = workspace_root / file_spec["destination"]
        if not source.exists():
            stats.bump_skip("missing_source")
            print(f"[SKIP] {target['name']}: file '{source_rel}' does not exist")
            continue
        stats.files_copied += copy_file(source, destination)

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

    if target.get("dependency_closure"):
        _check_dependency_closure(workspace_root, stats)

    return stats


def _select_targets(manifest: dict[str, Any], profiles: list[str] | None) -> list[dict[str, Any]]:
    targets = manifest["targets"]
    if not profiles:
        return targets
    requested = {p.strip() for p in profiles if p and p.strip()}
    selected = [t for t in targets if t.get("name") in requested]
    if len(selected) != len(requested):
        known = {t.get("name") for t in targets}
        missing = sorted(requested - known)
        raise ValueError(f"Unknown profile(s): {', '.join(missing)}; known: {', '.join(sorted(known))}")
    return selected


def _print_report(all_stats: list[ExportStats]) -> None:
    print("\n=== Export report ===")
    for stats in all_stats:
        print(f"profile={stats.profile}")
        print(f"  files_copied: {stats.files_copied}")
        if stats.skipped_by_reason:
            print("  skipped:")
            for reason, count in sorted(stats.skipped_by_reason.items()):
                print(f"    - {reason}: {count}")
        else:
            print("  skipped: none")
        if stats.dependency_errors:
            print("  dependency_errors:")
            for err in stats.dependency_errors:
                print(f"    - {err}")
        else:
            print("  dependency_errors: none")


def main() -> int:
    """Build runtime-specific resource exports from the canonical .github source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Path to the runtime export manifest.",
    )
    parser.add_argument(
        "--profile",
        action="append",
        help="Export only the named profile(s). Repeat the flag to select multiple.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print per-profile export counts, skip counts, and dependency errors.",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    exclusion_cfg = manifest.get("exclusions", {})
    forbidden_names = set(exclusion_cfg.get("private_roots", [])) | set(
        exclusion_cfg.get("skills", [])
    ) | _normalize_paths(exclusion_cfg.get("private_paths", []))

    all_stats: list[ExportStats] = []
    try:
        selected_targets = _select_targets(manifest, args.profile)
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        return 1

    for target in selected_targets:
        stats = export_target(manifest, target)
        all_stats.append(stats)
        print(f"[OK] Exported {target['name']} resources")

    if args.report:
        _print_report(all_stats)

    dependency_errors = [
        f"{stats.profile}: {err}" for stats in all_stats for err in stats.dependency_errors
    ]
    if dependency_errors:
        print(f"[FAIL] Dependency closure errors detected ({len(dependency_errors)}):")
        for err in dependency_errors:
            print(f"   - {err}")
        return 1

    # Post-export verification: no private content in any output tree
    output_root = PROJECT_ROOT / manifest["output_root"]
    leaks: list[str] = []
    target_names = {t["name"] for t in selected_targets}
    for path in output_root.rglob("*"):
        rel_parts = path.relative_to(output_root).parts
        if rel_parts and rel_parts[0] not in target_names:
            continue
        if any(part in forbidden_names for part in rel_parts):
            leaks.append(str(path.relative_to(output_root)))
    if leaks:
        print(f"[FAIL] Private content leaked into export ({len(leaks)} paths):")
        for leak in leaks[:20]:
            print(f"   - {leak}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
