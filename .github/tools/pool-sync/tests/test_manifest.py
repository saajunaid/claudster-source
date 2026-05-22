from __future__ import annotations

from pathlib import Path

import pytest

from manifest import (
    DEFAULT_POOL_ROOT,
    ClassificationError,
    ManifestError,
    classify,
    extract_managed_region,
    is_managed_region_path,
    is_profile_included_skill,
    load_manifest,
    managed_region_spec,
    profile_skill_globs,
    replace_managed_region,
)


CURRENT_TOP_LEVEL_EXPECTATIONS = {
    "agent-docs": "owned",
    "agents": "managed",
    "diagrams": "managed",
    "handoffs": "owned",
    "hooks": "managed",
    "instructions": "managed",
    "pipeline": "owned",
    "plans": "owned",
    "prompts": "managed",
    "recipes": "managed",
    "skills": "managed",
    "tools": "managed",
    "workflows": "managed",
    "copilot-instructions.md": "managed_region",
    "diagrams.zip": "local_private",
    "pipeline-state.json": "owned",
    "pipeline-state.template.json": "owned",
    "pool.manifest.yml": "owned",
    "project-config.md": "owned",
    "runtime-targets.json": "managed",
}


@pytest.mark.parametrize(
    ("path", "expected_tier"),
    [(path, tier) for path, tier in CURRENT_TOP_LEVEL_EXPECTATIONS.items()],
)
def test_classifies_every_current_github_top_level_path(path: str, expected_tier: str) -> None:
    classification = classify(path)
    assert classification.top_level == path
    assert classification.tier == expected_tier


def test_load_manifest_exposes_expected_profile_globs() -> None:
    manifest = load_manifest()
    assert manifest.version == 1
    assert manifest.private_patterns_path.name == "denylist-exceptions.txt"
    assert profile_skill_globs("frontend-dashboard") == [
        "frontend/**",
        "coding/**",
        "data/**",
        "testing/**",
        "workflow/**",
        "docs/**",
    ]


def test_owned_runtime_state_below_top_level_stays_owned() -> None:
    classification = classify("agent-docs/nuggets-inbox.md")
    assert classification.tier == "owned"
    assert classification.top_level == "agent-docs"


def test_private_vmie_skill_is_flagged_private() -> None:
    classification = classify("skills/vmie/windows-deployment/SKILL.md")
    assert classification.tier == "managed"
    assert classification.is_private is True
    assert is_profile_included_skill("skills/vmie/windows-deployment/SKILL.md", "full") is False


def test_denylist_exception_path_is_private_at_read_time() -> None:
    classification = classify("instructions/security.instructions.md")
    assert classification.tier == "managed"
    assert classification.is_private is True


def test_copilot_file_is_managed_region() -> None:
    classification = classify("copilot-instructions.md")
    assert classification.tier == "managed_region"
    assert classification.managed_region is not None
    assert classification.managed_region.start_marker == "<!-- junai:start -->"
    assert classification.managed_region.end_marker == "<!-- junai:end -->"
    assert is_managed_region_path("copilot-instructions.md") is True


def test_managed_region_helpers_extract_and_replace() -> None:
    text = "prefix\n<!-- junai:start -->\nmanaged block\n<!-- junai:end -->\nsuffix\n"
    assert extract_managed_region("copilot-instructions.md", text) == "\nmanaged block\n"
    assert (
        replace_managed_region("copilot-instructions.md", text, "\nreplacement\n")
        == "prefix\n<!-- junai:start -->\nreplacement\n<!-- junai:end -->\nsuffix\n"
    )
    region = managed_region_spec("copilot-instructions.md")
    assert region.path == "copilot-instructions.md"


def test_full_profile_includes_non_private_skills() -> None:
    assert is_profile_included_skill("skills/workflow/golden-nuggets/SKILL.md", "full") is True


def test_frontend_dashboard_profile_filters_skill_categories() -> None:
    assert is_profile_included_skill("skills/frontend/react-dev/SKILL.md", "frontend-dashboard") is True
    assert is_profile_included_skill("skills/workflow/golden-nuggets/SKILL.md", "frontend-dashboard") is True
    assert is_profile_included_skill("skills/cloud/aws-cdk-development/SKILL.md", "frontend-dashboard") is False


def test_data_pipeline_profile_excludes_frontend_only_skills() -> None:
    assert is_profile_included_skill("skills/data/database-design/SKILL.md", "data-pipeline") is True
    assert is_profile_included_skill("skills/frontend/react-dev/SKILL.md", "data-pipeline") is False


def test_unknown_profile_fails() -> None:
    with pytest.raises(ManifestError):
        profile_skill_globs("unknown-profile")


def test_unknown_top_level_path_fails_closed() -> None:
    with pytest.raises(ClassificationError):
        classify("example-temp/file.txt")


def test_absolute_paths_under_github_are_supported() -> None:
    github_file = DEFAULT_POOL_ROOT / ".github" / "agent-docs" / "README.md"
    classification = classify(github_file)
    assert classification.tier == "owned"


def test_absolute_paths_outside_github_are_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("x\n", encoding="utf-8")
    with pytest.raises(ClassificationError):
        classify(outside)


def test_manifest_load_fails_when_a_current_top_level_entry_is_unclassified(tmp_path: Path) -> None:
    github_dir = tmp_path / ".github"
    github_dir.mkdir(parents=True)
    (github_dir / "pool.manifest.yml").write_text(
        """
version: 1
private_patterns_from: .github/tools/pool-validator/denylist-exceptions.txt
tiers:
  managed:
    directories: [agents, tools]
profiles:
  full:
    skill_globs: ["**"]
managed_regions: {}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    private_patterns = github_dir / "tools" / "pool-validator" / "denylist-exceptions.txt"
    private_patterns.parent.mkdir(parents=True)
    private_patterns.write_text("", encoding="utf-8")
    (github_dir / "agents").mkdir()
    (github_dir / "unclassified").mkdir()

    with pytest.raises(
        ManifestError,
        match="Unclassified top-level \\.github paths: pool\\.manifest\\.yml, unclassified",
    ):
        load_manifest(tmp_path)
