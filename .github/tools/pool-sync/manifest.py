from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_POOL_ROOT = MODULE_DIR.parents[2]

TIER_MANAGED = "managed"
TIER_OWNED = "owned"
TIER_MANAGED_REGION = "managed_region"
TIER_LOCAL_PRIVATE = "local_private"
KNOWN_TIERS = {
    TIER_MANAGED,
    TIER_OWNED,
    TIER_MANAGED_REGION,
    TIER_LOCAL_PRIVATE,
}


class ManifestError(ValueError):
    """Raised when the pool manifest is invalid."""


class ClassificationError(ManifestError):
    """Raised when a path cannot be classified safely."""


@dataclass(frozen=True)
class ManagedRegionSpec:
    path: str
    start_marker: str
    end_marker: str


@dataclass(frozen=True)
class Classification:
    path: str
    top_level: str
    tier: str
    is_private: bool
    managed_region: ManagedRegionSpec | None = None

    @property
    def is_managed_region(self) -> bool:
        return self.tier == TIER_MANAGED_REGION


@dataclass(frozen=True)
class PoolManifest:
    version: int
    pool_root: Path
    github_dir: Path
    manifest_path: Path
    private_patterns_path: Path
    tiers: dict[str, dict[str, tuple[str, ...]]]
    top_level_tiers: dict[str, str]
    private_paths: tuple[str, ...]
    private_substrings: tuple[str, ...]
    profiles: dict[str, tuple[str, ...]]
    managed_regions: dict[str, ManagedRegionSpec]


def _manifest_path_for(pool_root: Path) -> Path:
    return pool_root / ".github" / "pool.manifest.yml"


@lru_cache(maxsize=None)
def _load_manifest_cached(pool_root_str: str) -> PoolManifest:
    return _load_manifest_uncached(Path(pool_root_str))


def load_manifest(pool_root: Path | None = None) -> PoolManifest:
    root = (pool_root or DEFAULT_POOL_ROOT).resolve()
    return _load_manifest_cached(str(root))


def _load_manifest_uncached(pool_root: Path) -> PoolManifest:
    manifest_path = _manifest_path_for(pool_root)
    if not manifest_path.exists():
        raise ManifestError(f"Missing pool manifest: {manifest_path}")

    try:
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ManifestError(f"Invalid YAML in {manifest_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ManifestError(f"Pool manifest must contain a mapping: {manifest_path}")

    version = payload.get("version")
    if version != 1:
        raise ManifestError(f"Unsupported manifest version {version!r}; expected 1")

    github_dir = pool_root / ".github"
    private_patterns_from = payload.get("private_patterns_from")
    if not isinstance(private_patterns_from, str) or not private_patterns_from.strip():
        raise ManifestError("Manifest must define non-empty 'private_patterns_from'")
    private_patterns_path = (pool_root / private_patterns_from).resolve()
    if not private_patterns_path.exists():
        raise ManifestError(
            f"private_patterns_from target does not exist: {private_patterns_path}"
        )

    tiers = _parse_tiers(payload.get("tiers"))
    top_level_tiers = _build_top_level_tiers(tiers)
    profiles = _parse_profiles(payload.get("profiles"))
    managed_regions = _parse_managed_regions(payload.get("managed_regions"))
    private_paths = _parse_private_paths(payload.get("private"))
    private_substrings = _load_private_substrings(private_patterns_path)

    manifest = PoolManifest(
        version=version,
        pool_root=pool_root,
        github_dir=github_dir,
        manifest_path=manifest_path,
        private_patterns_path=private_patterns_path,
        tiers=tiers,
        top_level_tiers=top_level_tiers,
        private_paths=private_paths,
        private_substrings=private_substrings,
        profiles=profiles,
        managed_regions=managed_regions,
    )
    _validate_current_top_level_inventory(manifest)
    return manifest


def _parse_tiers(raw_tiers: Any) -> dict[str, dict[str, tuple[str, ...]]]:
    if not isinstance(raw_tiers, dict):
        raise ManifestError("Manifest must define a 'tiers' mapping")

    parsed: dict[str, dict[str, tuple[str, ...]]] = {}
    for tier_name, tier_payload in raw_tiers.items():
        if tier_name not in KNOWN_TIERS:
            raise ManifestError(f"Unknown tier {tier_name!r}")
        if not isinstance(tier_payload, dict):
            raise ManifestError(f"Tier {tier_name!r} must be a mapping")

        directories = _normalize_name_list(tier_payload.get("directories"), f"{tier_name}.directories")
        files = _normalize_name_list(tier_payload.get("files"), f"{tier_name}.files")
        parsed[tier_name] = {"directories": directories, "files": files}
    return parsed


def _normalize_name_list(raw: Any, label: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ManifestError(f"{label} must be a list")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ManifestError(f"{label} entries must be non-empty strings")
        value = item.strip().strip("/\\")
        if not value:
            raise ManifestError(f"{label} entries must not normalize to empty strings")
        if "/" in value or "\\" in value:
            raise ManifestError(f"{label} entry must be top-level only: {item!r}")
        if value in seen:
            raise ManifestError(f"Duplicate {label} entry: {value}")
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _build_top_level_tiers(
    tiers: dict[str, dict[str, tuple[str, ...]]]
) -> dict[str, str]:
    top_level_tiers: dict[str, str] = {}
    for tier_name, tier_payload in tiers.items():
        for group in ("directories", "files"):
            for entry in tier_payload[group]:
                prior = top_level_tiers.get(entry)
                if prior is not None:
                    raise ManifestError(
                        f"Top-level path {entry!r} appears in both {prior!r} and {tier_name!r}"
                    )
                top_level_tiers[entry] = tier_name
    return top_level_tiers


def _parse_profiles(raw_profiles: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw_profiles, dict):
        raise ManifestError("Manifest must define a 'profiles' mapping")

    profiles: dict[str, tuple[str, ...]] = {}
    for profile_name, profile_payload in raw_profiles.items():
        if not isinstance(profile_payload, dict):
            raise ManifestError(f"Profile {profile_name!r} must be a mapping")
        globs = profile_payload.get("skill_globs")
        if not isinstance(globs, list) or not globs:
            raise ManifestError(f"Profile {profile_name!r} must define non-empty 'skill_globs'")

        normalized: list[str] = []
        seen: set[str] = set()
        for item in globs:
            if not isinstance(item, str) or not item.strip():
                raise ManifestError(
                    f"Profile {profile_name!r} contains an invalid skill_globs entry"
                )
            value = item.strip().replace("\\", "/").lstrip("/")
            if value in seen:
                raise ManifestError(
                    f"Profile {profile_name!r} contains duplicate skill glob {value!r}"
                )
            seen.add(value)
            normalized.append(value)
        profiles[profile_name] = tuple(normalized)
    return profiles


def _parse_managed_regions(raw_regions: Any) -> dict[str, ManagedRegionSpec]:
    if raw_regions is None:
        return {}
    if not isinstance(raw_regions, dict):
        raise ManifestError("managed_regions must be a mapping")

    regions: dict[str, ManagedRegionSpec] = {}
    for raw_path, region_payload in raw_regions.items():
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ManifestError("managed_regions keys must be non-empty strings")
        if not isinstance(region_payload, dict):
            raise ManifestError(f"Managed region {raw_path!r} must be a mapping")
        path = _normalize_github_relative_path(raw_path)
        start_marker = region_payload.get("start_marker")
        end_marker = region_payload.get("end_marker")
        if not isinstance(start_marker, str) or not start_marker:
            raise ManifestError(f"Managed region {path!r} is missing start_marker")
        if not isinstance(end_marker, str) or not end_marker:
            raise ManifestError(f"Managed region {path!r} is missing end_marker")
        regions[path] = ManagedRegionSpec(
            path=path,
            start_marker=start_marker,
            end_marker=end_marker,
        )
    return regions


def _parse_private_paths(raw_private: Any) -> tuple[str, ...]:
    if raw_private is None:
        return ()
    if not isinstance(raw_private, dict):
        raise ManifestError("private must be a mapping")

    raw_paths = raw_private.get("paths")
    if raw_paths is None:
        return ()
    if not isinstance(raw_paths, list):
        raise ManifestError("private.paths must be a list")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_paths:
        if not isinstance(item, str) or not item.strip():
            raise ManifestError("private.paths entries must be non-empty strings")
        value = item.strip().replace("\\", "/").lstrip("/")
        if value in seen:
            raise ManifestError(f"Duplicate private path pattern: {value!r}")
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _load_private_substrings(path: Path) -> tuple[str, ...]:
    patterns: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return tuple(patterns)


def _validate_current_top_level_inventory(manifest: PoolManifest) -> None:
    if not manifest.github_dir.exists():
        return

    on_disk = {child.name for child in manifest.github_dir.iterdir()}
    missing = sorted(on_disk - set(manifest.top_level_tiers))
    if missing:
        raise ManifestError(
            "Unclassified top-level .github paths: " + ", ".join(missing)
        )


def _normalize_github_relative_path(path: str | Path) -> str:
    raw = str(path).strip().replace("\\", "/")
    if not raw:
        raise ClassificationError("Cannot classify an empty path")

    if raw.startswith("./"):
        raw = raw[2:]
    if raw.startswith("/"):
        raw = raw.lstrip("/")

    marker = ".github/"
    if raw == ".github":
        return ""
    if marker in raw:
        raw = raw.split(marker, 1)[1]
    elif raw.startswith(".github"):
        raw = raw[len(".github") :].lstrip("/")

    return raw.strip("/")


def _normalize_relative_for_manifest(path: str | Path, manifest: PoolManifest) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(manifest.github_dir.resolve()).as_posix()
        except ValueError:
            raise ClassificationError(
                f"Path {candidate} is outside {manifest.github_dir}"
            ) from None
    return _normalize_github_relative_path(path)


def classify(path: str | Path) -> Classification:
    return _classify_with_manifest(path, load_manifest())


def _classify_with_manifest(path: str | Path, manifest: PoolManifest) -> Classification:
    relative_path = _normalize_relative_for_manifest(path, manifest)
    if not relative_path:
        raise ClassificationError("Cannot classify the .github root itself")

    top_level = relative_path.split("/", 1)[0]
    tier = manifest.top_level_tiers.get(top_level)
    if tier is None:
        raise ClassificationError(f"Unclassified top-level .github path: {top_level}")

    managed_region = manifest.managed_regions.get(relative_path)
    is_private = tier == TIER_LOCAL_PRIVATE or _is_private_path(relative_path, manifest)
    return Classification(
        path=relative_path,
        top_level=top_level,
        tier=tier,
        is_private=is_private,
        managed_region=managed_region,
    )


def _is_private_path(relative_path: str, manifest: PoolManifest) -> bool:
    if _matches_private_path_pattern(relative_path, manifest.private_paths):
        return True
    return _matches_private_substring(relative_path, manifest.private_substrings)


def _matches_private_path_pattern(relative_path: str, patterns: tuple[str, ...]) -> bool:
    candidate = relative_path.replace("\\", "/").strip("/")
    for pattern in patterns:
        normalized = pattern.replace("\\", "/").strip("/")
        if normalized.endswith("/**"):
            prefix = normalized[:-3].rstrip("/")
            if candidate == prefix or candidate.startswith(prefix + "/"):
                return True
            continue
        if candidate == normalized:
            return True
        if candidate.startswith(normalized.rstrip("/") + "/"):
            return True
    return False


def _matches_private_substring(relative_path: str, substrings: tuple[str, ...]) -> bool:
    forward = relative_path.replace("\\", "/")
    backward = forward.replace("/", "\\")
    for pattern in substrings:
        normalized = pattern.replace("\\", "/")
        if normalized in forward or pattern in backward:
            return True
    return False


def profile_skill_globs(profile: str) -> list[str]:
    manifest = load_manifest()
    try:
        return list(manifest.profiles[profile])
    except KeyError as exc:
        raise ManifestError(f"Unknown profile {profile!r}") from exc


def is_profile_included_skill(path: str | Path, profile: str) -> bool:
    manifest = load_manifest()
    try:
        globs = manifest.profiles[profile]
    except KeyError as exc:
        raise ManifestError(f"Unknown profile {profile!r}") from exc

    classification = _classify_with_manifest(path, manifest)
    if classification.top_level != "skills" or classification.is_private:
        return False

    skill_relative = _skill_relative_path(classification.path)
    if skill_relative is None:
        return False
    if profile == "full":
        return True
    return any(_match_profile_skill_glob(skill_relative, pattern) for pattern in globs)


def _skill_relative_path(relative_path: str) -> str | None:
    if not relative_path.startswith("skills/"):
        return None
    skill_relative = relative_path[len("skills/") :]
    if not skill_relative or skill_relative == "_registry.md":
        return None
    return skill_relative


def _match_profile_skill_glob(skill_relative_path: str, pattern: str) -> bool:
    candidate = skill_relative_path.replace("\\", "/").strip("/")
    normalized = pattern.replace("\\", "/").strip("/")
    if normalized == "**":
        return True
    if normalized.endswith("/**"):
        prefix = normalized[:-3].rstrip("/")
        return candidate == prefix or candidate.startswith(prefix + "/")
    return candidate == normalized


def managed_region_spec(path: str | Path) -> ManagedRegionSpec:
    classification = classify(path)
    if classification.managed_region is None:
        raise ClassificationError(
            f"Path {classification.path!r} is not a managed-region file"
        )
    return classification.managed_region


def is_managed_region_path(path: str | Path) -> bool:
    return classify(path).managed_region is not None


def extract_managed_region(path: str | Path, text: str) -> str:
    region = managed_region_spec(path)
    start = text.find(region.start_marker)
    end = text.find(region.end_marker)
    if start == -1 or end == -1 or end < start:
        raise ClassificationError(
            f"Managed region markers not found in {region.path!r}"
        )
    start += len(region.start_marker)
    return text[start:end]


def replace_managed_region(path: str | Path, text: str, replacement: str) -> str:
    region = managed_region_spec(path)
    start = text.find(region.start_marker)
    end = text.find(region.end_marker)
    if start == -1 or end == -1 or end < start:
        raise ClassificationError(
            f"Managed region markers not found in {region.path!r}"
        )
    start += len(region.start_marker)
    return text[:start] + replacement + text[end:]
