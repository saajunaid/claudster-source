from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from manifest import (
    Classification,
    ClassificationError,
    ManagedRegionSpec,
    ManifestError,
    _classify_with_manifest,
    load_manifest,
)
from nuggets_inbox import NuggetCandidate, parse_nuggets_inbox


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_POOL_ROOT = MODULE_DIR.parents[2]
DRIFT_STATUSES = [
    "unchanged",
    "pool-newer",
    "project-newer",
    "both-changed",
    "project-only",
    "pool-only",
]
GENERATED_ARTIFACT_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
}
GENERATED_ARTIFACT_SUFFIXES = {".pyc", ".pyo"}


class PoolSyncError(RuntimeError):
    """Raised when a pool CLI operation cannot proceed."""


@dataclass(frozen=True)
class PoolStamp:
    pool_sha: str
    deployed_at: str | None = None
    profile: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pool_sha": self.pool_sha,
            "deployed_at": self.deployed_at,
            "profile": self.profile,
        }


@dataclass(frozen=True)
class DiffEntry:
    path: str
    status: str
    tier: str
    managed_region: bool
    has_project_file: bool
    has_pool_file: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status": self.status,
            "tier": self.tier,
            "managed_region": self.managed_region,
            "has_project_file": self.has_project_file,
            "has_pool_file": self.has_pool_file,
        }


@dataclass(frozen=True)
class DiffReport:
    project_root: Path
    pool_root: Path
    pool_sha: str
    project_profile: str
    stamp: PoolStamp | None
    stamp_error: str | None
    entries: tuple[DiffEntry, ...]

    @property
    def drift_entries(self) -> tuple[DiffEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status != "unchanged")

    def counts(self) -> dict[str, int]:
        counts = {status: 0 for status in DRIFT_STATUSES}
        for entry in self.entries:
            counts[entry.status] += 1
        return counts

    def to_dict(self, *, drift_only: bool = False) -> dict[str, Any]:
        entries = self.drift_entries if drift_only else self.entries
        return {
            "project_root": str(self.project_root),
            "pool_root": str(self.pool_root),
            "pool_sha": self.pool_sha,
            "project_profile": self.project_profile,
            "stamp_present": self.stamp is not None,
            "stamp": self.stamp.to_dict() if self.stamp else None,
            "stamp_error": self.stamp_error,
            "counts": self.counts(),
            "entry_count": len(entries),
            "entries": [entry.to_dict() for entry in entries],
        }


@dataclass(frozen=True)
class DeployReport:
    project_root: Path
    pool_root: Path
    pool_sha: str
    profile: str
    copied_directories: tuple[str, ...]
    copied_files: tuple[str, ...]
    managed_regions: tuple[str, ...]
    registry_written: bool
    stamp_path: Path

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "pool_root": str(self.pool_root),
            "pool_sha": self.pool_sha,
            "profile": self.profile,
            "copied_directories": list(self.copied_directories),
            "copied_files": list(self.copied_files),
            "managed_regions": list(self.managed_regions),
            "registry_written": self.registry_written,
            "stamp_path": str(self.stamp_path),
        }


@dataclass(frozen=True)
class PromotionRefusal:
    path: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "reason": self.reason}


@dataclass(frozen=True)
class PromotionReport:
    project_root: Path
    pool_root: Path
    project_profile: str
    branch_name: str | None
    deployed_pool_sha: str | None
    reason: str | None
    dry_run: bool
    selected_paths: tuple[str, ...]
    kept_local_paths: tuple[str, ...]
    refusals: tuple[PromotionRefusal, ...]
    validation_passed: bool
    commit_sha: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "pool_root": str(self.pool_root),
            "project_profile": self.project_profile,
            "branch_name": self.branch_name,
            "deployed_pool_sha": self.deployed_pool_sha,
            "reason": self.reason,
            "dry_run": self.dry_run,
            "selected_paths": list(self.selected_paths),
            "kept_local_paths": list(self.kept_local_paths),
            "refusals": [refusal.to_dict() for refusal in self.refusals],
            "validation_passed": self.validation_passed,
            "commit_sha": self.commit_sha,
        }


@dataclass(frozen=True)
class NuggetsReviewItem:
    fingerprint: str | None
    date: str | None
    version: str | None
    commit: str | None
    source: str | None
    raw: str | None
    shape: str | None
    suggested_route: str | None
    action: str
    target_path: str | None
    lesson: str | None
    auto_discarded: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "date": self.date,
            "version": self.version,
            "commit": self.commit,
            "source": self.source,
            "raw": self.raw,
            "shape": self.shape,
            "suggested_route": self.suggested_route,
            "action": self.action,
            "target_path": self.target_path,
            "lesson": self.lesson,
            "auto_discarded": self.auto_discarded,
        }


@dataclass(frozen=True)
class NuggetsReviewReport:
    project_root: Path
    pool_root: Path
    inbox_path: Path
    dry_run: bool
    pending_before: int
    pending_remaining: int
    reviewed: tuple[NuggetsReviewItem, ...]
    promotion_report: PromotionReport | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "pool_root": str(self.pool_root),
            "inbox_path": str(self.inbox_path),
            "dry_run": self.dry_run,
            "pending_before": self.pending_before,
            "pending_remaining": self.pending_remaining,
            "reviewed_count": len(self.reviewed),
            "reviewed": [item.to_dict() for item in self.reviewed],
            "promotion_report": self.promotion_report.to_dict() if self.promotion_report else None,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="junai pool sync and review commands")
    parser.add_argument("--pool-root", default=os.environ.get("JUNAI_POOL_ROOT"), help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("version", help="Print the current pool git SHA")

    status_parser = subparsers.add_parser("status", help="Summarize project pool drift")
    status_parser.add_argument("--project", required=True, help="Path to the project root")
    status_parser.add_argument("--json", action="store_true", help="Emit JSON")

    diff_parser = subparsers.add_parser("diff", help="List project drift against the pool")
    diff_parser.add_argument("--project", required=True, help="Path to the project root")
    diff_parser.add_argument("--json", action="store_true", help="Emit JSON")

    deploy_parser = subparsers.add_parser("deploy", help=argparse.SUPPRESS)
    deploy_parser.add_argument("--project", required=True, help=argparse.SUPPRESS)
    deploy_parser.add_argument("--json", action="store_true", help=argparse.SUPPRESS)

    promote_parser = subparsers.add_parser("promote", help="Promote reusable project changes into a review branch")
    promote_parser.add_argument("--project", required=True, help="Path to the project root")
    promote_parser.add_argument("--dry-run", action="store_true", help="Preview promotion without writing or branching")
    promote_parser.add_argument("--reason", help="Human reason to include in the promotion commit")
    promote_parser.add_argument("--select-path", action="append", default=None, help=argparse.SUPPRESS)

    nuggets_parser = subparsers.add_parser("nuggets", help="Review captured nugget candidates")
    nuggets_subparsers = nuggets_parser.add_subparsers(dest="nuggets_command", required=True)
    review_parser = nuggets_subparsers.add_parser("review", help="Review pending nugget candidates for a project")
    review_parser.add_argument("--project", required=True, help="Path to the project root")
    review_parser.add_argument("--dry-run", action="store_true", help="Preview nugget actions without writing changes")
    review_parser.add_argument("--json", action="store_true", help="Emit JSON summary")

    args = parser.parse_args(argv)
    pool_root = Path(args.pool_root).resolve() if args.pool_root else DEFAULT_POOL_ROOT

    try:
        if args.command == "version":
            return _cmd_version(pool_root)
        if args.command == "status":
            return _cmd_status(pool_root, Path(args.project), as_json=args.json)
        if args.command == "diff":
            return _cmd_diff(pool_root, Path(args.project), as_json=args.json)
        if args.command == "deploy":
            return _cmd_deploy(pool_root, Path(args.project), as_json=args.json)
        if args.command == "promote":
            return _cmd_promote(
                pool_root,
                Path(args.project),
                dry_run=args.dry_run,
                reason=args.reason,
                requested_paths=args.select_path,
            )
        if args.command == "nuggets" and args.nuggets_command == "review":
            return _cmd_nuggets_review(
                pool_root,
                Path(args.project),
                dry_run=args.dry_run,
                as_json=args.json,
            )
        raise PoolSyncError(f"Unsupported command: {args.command}")
    except PoolSyncError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        else:
            print(f"[junai pool] {exc}")
        return 1


def _cmd_version(pool_root: Path) -> int:
    print(_git_head_sha(pool_root))
    return 0


def _cmd_status(pool_root: Path, project_root: Path, *, as_json: bool) -> int:
    report = build_diff_report(project_root, pool_root=pool_root)
    payload = report.to_dict(drift_only=False)
    payload["ok"] = True
    payload["pool_matches_stamp"] = bool(report.stamp and report.stamp.pool_sha == report.pool_sha)
    payload["drift_count"] = len(report.drift_entries)
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(f"Project: {report.project_root}")
    print(f"Pool:    {report.pool_root}")
    print(f"Head:    {report.pool_sha}")
    if report.stamp:
        print(f"Stamp:   {report.stamp.pool_sha}")
    else:
        print("Stamp:   missing")
    if report.stamp_error:
        print(f"Note:    {report.stamp_error}")
    print(f"Profile: {report.project_profile}")
    print(f"Drift:   {len(report.drift_entries)} / {len(report.entries)} managed path(s)")
    for status, count in report.counts().items():
        if count:
            print(f"{status:13} {count}")
    return 0


def _cmd_diff(pool_root: Path, project_root: Path, *, as_json: bool) -> int:
    report = build_diff_report(project_root, pool_root=pool_root)
    payload = report.to_dict(drift_only=True)
    payload["ok"] = True
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if not report.drift_entries:
        print("No drift.")
        return 0

    for entry in report.drift_entries:
        print(f"{entry.status:13} {entry.path}")
    return 0


def _cmd_deploy(pool_root: Path, project_root: Path, *, as_json: bool) -> int:
    report = deploy_project(project_root, pool_root=pool_root)
    payload = report.to_dict()
    payload["ok"] = True
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(f"Deployed {len(report.copied_directories)} directories, {len(report.copied_files)} files.")
    print(f"Profile: {report.profile}")
    print(f"Stamp:   {report.stamp_path}")
    return 0


def _cmd_promote(
    pool_root: Path,
    project_root: Path,
    *,
    dry_run: bool,
    reason: str | None,
    requested_paths: list[str] | None,
) -> int:
    report = promote_project_changes(
        project_root,
        pool_root=pool_root,
        dry_run=dry_run,
        reason=reason,
        requested_paths=requested_paths,
    )

    if report.refusals:
        for refusal in report.refusals:
            print(f"Refused: {refusal.path} ({refusal.reason})")

    if not report.selected_paths:
        print("No managed project changes were selected for promotion.")
        return 1 if requested_paths and report.refusals else 0

    if report.dry_run:
        print(f"Dry run: would promote {len(report.selected_paths)} path(s).")
        for path in report.selected_paths:
            print(f"  {path}")
        return 0

    print(f"Branch:  {report.branch_name}")
    print(f"Commit:  {report.commit_sha}")
    print(f"Source:  {report.project_root}")
    print("Review:  inspect the branch, run validation, and merge manually if approved.")
    return 0


def _cmd_nuggets_review(
    pool_root: Path,
    project_root: Path,
    *,
    dry_run: bool,
    as_json: bool,
) -> int:
    report = review_project_nuggets(
        project_root,
        pool_root=pool_root,
        dry_run=dry_run,
        display_candidates=not as_json,
        prompt_to_stderr=as_json,
    )
    payload = report.to_dict()
    payload["ok"] = True
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if not report.reviewed:
        print("No pending nugget candidates.")
        return 0

    print(f"Reviewed {len(report.reviewed)} candidate(s); {report.pending_remaining} pending remain.")
    if dry_run:
        print("Dry run: no inbox, project, or pool files were changed.")
    if report.promotion_report and report.promotion_report.selected_paths:
        print(f"Branch:  {report.promotion_report.branch_name}")
        print(f"Commit:  {report.promotion_report.commit_sha}")
    return 0


def build_diff_report(project_root: Path, *, pool_root: Path | None = None) -> DiffReport:
    resolved_pool_root = (pool_root or DEFAULT_POOL_ROOT).resolve()
    resolved_project_root = _resolve_project_root(project_root)
    manifest = load_manifest(resolved_pool_root)
    pool_sha = _git_head_sha(resolved_pool_root)
    stamp, stamp_error = _load_project_stamp(resolved_project_root)
    project_profile = _resolve_project_profile(resolved_project_root, manifest, stamp)

    pool_paths = _collect_pool_paths(resolved_pool_root, manifest, project_profile)
    project_paths = _collect_project_paths(resolved_project_root, manifest, project_profile)
    candidate_paths = sorted(pool_paths | project_paths)

    entries: list[DiffEntry] = []
    for relative_path in candidate_paths:
        classification = _classify_candidate(relative_path, manifest)
        project_content = _read_project_content(resolved_project_root, relative_path, classification)
        pool_content = _read_pool_worktree_content(resolved_pool_root, relative_path, classification)
        base_content = _read_base_content(resolved_pool_root, stamp, relative_path, classification)
        status = _classify_content_state(project_content, base_content, pool_content)
        entries.append(
            DiffEntry(
                path=relative_path,
                status=status,
                tier=classification.tier,
                managed_region=classification.managed_region is not None,
                has_project_file=project_content is not None,
                has_pool_file=pool_content is not None,
            )
        )

    return DiffReport(
        project_root=resolved_project_root,
        pool_root=resolved_pool_root,
        pool_sha=pool_sha,
        project_profile=project_profile,
        stamp=stamp,
        stamp_error=stamp_error,
        entries=tuple(entries),
    )


def deploy_project(project_root: Path, *, pool_root: Path | None = None) -> DeployReport:
    resolved_pool_root = (pool_root or DEFAULT_POOL_ROOT).resolve()
    resolved_project_root = _resolve_project_root(project_root)
    manifest = load_manifest(resolved_pool_root)
    pool_sha = _git_head_sha(resolved_pool_root)
    project_profile = _resolve_project_profile(resolved_project_root, manifest, None)

    pool_github = resolved_pool_root / ".github"
    project_github = resolved_project_root / ".github"

    copied_directories: list[str] = []
    copied_files: list[str] = []
    managed_regions: list[str] = []

    for directory_name in manifest.tiers["managed"]["directories"]:
        if directory_name == "skills":
            _deploy_skills_directory(pool_github, project_github, manifest, project_profile)
            copied_directories.append("skills")
            continue
        _deploy_managed_directory(pool_github, project_github, directory_name)
        copied_directories.append(directory_name)

    for file_name in manifest.tiers["managed"]["files"]:
        _deploy_managed_file(pool_github / file_name, project_github / file_name)
        copied_files.append(file_name)

    for relative_path, region in manifest.managed_regions.items():
        _deploy_managed_region(pool_github / relative_path, project_github / relative_path, region)
        managed_regions.append(relative_path)

    _write_project_registry(resolved_pool_root, resolved_project_root, project_profile)
    stamp_path = _write_project_stamp(project_github, pool_sha, project_profile)

    return DeployReport(
        project_root=resolved_project_root,
        pool_root=resolved_pool_root,
        pool_sha=pool_sha,
        profile=project_profile,
        copied_directories=tuple(copied_directories),
        copied_files=tuple(copied_files),
        managed_regions=tuple(managed_regions),
        registry_written=True,
        stamp_path=stamp_path,
    )


def promote_project_changes(
    project_root: Path,
    *,
    pool_root: Path | None = None,
    dry_run: bool = False,
    reason: str | None = None,
    requested_paths: list[str] | None = None,
    selector: Callable[[tuple[DiffEntry, ...]], list[str] | tuple[str, ...]] | None = None,
    now: datetime | None = None,
) -> PromotionReport:
    resolved_pool_root = (pool_root or DEFAULT_POOL_ROOT).resolve()
    resolved_project_root = _resolve_project_root(project_root)
    manifest = load_manifest(resolved_pool_root)
    report = build_diff_report(resolved_project_root, pool_root=resolved_pool_root)
    deployed_pool_sha = report.stamp.pool_sha if report.stamp else None
    eligible_entries = tuple(
        entry for entry in report.entries if entry.status in {"project-newer", "project-only"}
    )
    eligible_paths = {entry.path for entry in eligible_entries}

    selected_paths: list[str] = []
    kept_local_paths: list[str] = []
    refusals: list[PromotionRefusal] = []

    if requested_paths is not None:
        for raw_path in requested_paths:
            relative_path = _normalize_relative_path(raw_path)
            allowed, refusal_reason = _evaluate_requested_promotion(relative_path, report, manifest, eligible_paths)
            if allowed:
                if relative_path not in selected_paths:
                    selected_paths.append(relative_path)
            else:
                refusals.append(PromotionRefusal(path=relative_path, reason=refusal_reason or "not promotable"))
    elif selector is not None:
        selected_by_selector = {_normalize_relative_path(path) for path in selector(eligible_entries)}
        unknown_paths = sorted(selected_by_selector - eligible_paths)
        for relative_path in unknown_paths:
            refusals.append(PromotionRefusal(path=relative_path, reason="not offered as an eligible promotion candidate"))
        selected_paths.extend(sorted(selected_by_selector & eligible_paths))
        kept_local_paths.extend(sorted(path for path in eligible_paths if path not in selected_by_selector))
    else:
        selected_paths, kept_local_paths = _prompt_for_promotion(eligible_entries)

    if requested_paths is not None:
        requested_normalized = {_normalize_relative_path(path) for path in requested_paths}
        kept_local_paths.extend(sorted(eligible_paths - requested_normalized))

    selected_paths = sorted(dict.fromkeys(selected_paths))
    kept_local_paths = sorted(dict.fromkeys(kept_local_paths))
    branch_name = _promotion_branch_name(resolved_project_root.name, now=now)

    if dry_run or not selected_paths:
        return PromotionReport(
            project_root=resolved_project_root,
            pool_root=resolved_pool_root,
            project_profile=report.project_profile,
            branch_name=branch_name if selected_paths else None,
            deployed_pool_sha=deployed_pool_sha,
            reason=reason,
            dry_run=dry_run,
            selected_paths=tuple(selected_paths),
            kept_local_paths=tuple(kept_local_paths),
            refusals=tuple(refusals),
            validation_passed=False,
            commit_sha=None,
        )

    _checkout_promotion_branch(resolved_pool_root, branch_name)
    for relative_path in selected_paths:
        classification = _classify_candidate(relative_path, manifest)
        _apply_project_change_to_pool(resolved_project_root, resolved_pool_root, relative_path, classification)

    _run_pool_validation(resolved_pool_root)
    _stage_promotion_paths(resolved_pool_root, selected_paths)
    _commit_promotion(resolved_pool_root, resolved_project_root, selected_paths, deployed_pool_sha, reason)
    commit_sha = _git_head_sha(resolved_pool_root)

    return PromotionReport(
        project_root=resolved_project_root,
        pool_root=resolved_pool_root,
        project_profile=report.project_profile,
        branch_name=branch_name,
        deployed_pool_sha=deployed_pool_sha,
        reason=reason,
        dry_run=False,
        selected_paths=tuple(selected_paths),
        kept_local_paths=tuple(kept_local_paths),
        refusals=tuple(refusals),
        validation_passed=True,
        commit_sha=commit_sha,
    )


def review_project_nuggets(
    project_root: Path,
    *,
    pool_root: Path | None = None,
    dry_run: bool = False,
    input_func: Callable[[str], str] | None = None,
    now: datetime | None = None,
    display_candidates: bool = True,
    prompt_to_stderr: bool = False,
) -> NuggetsReviewReport:
    resolved_pool_root = (pool_root or DEFAULT_POOL_ROOT).resolve()
    resolved_project_root = _resolve_project_root(project_root)
    resolved_now = now or datetime.now(timezone.utc)
    today = resolved_now.date()
    manifest = load_manifest(resolved_pool_root)
    prompt = input_func or input

    inbox_path = resolved_project_root / ".github" / "agent-docs" / "nuggets-inbox.md"
    inbox_text = inbox_path.read_text(encoding="utf-8") if inbox_path.exists() else ""
    inbox = parse_nuggets_inbox(inbox_text)
    pending_before = sum(1 for candidate in inbox.candidates if _candidate_status(candidate) == "pending")
    reviewed_items: list[NuggetsReviewItem] = []
    promote_plans: list[tuple[NuggetCandidate, str, str]] = []
    keep_local_plans: list[tuple[NuggetCandidate, str, str]] = []

    for candidate in inbox.candidates:
        if _candidate_status(candidate) != "pending":
            continue
        if _is_stale_pending_candidate(candidate, today):
            _record_review_state(
                candidate,
                status="discarded",
                lesson=None,
                target_path=None,
                reviewed_at=today,
            )
            reviewed_items.append(_review_item_from_candidate(candidate, action="discard", auto_discarded=True))
            continue

        if display_candidates:
            _print_candidate_for_review(candidate)
        lesson = _normalize_lesson_text(
            _prompt_review_input(prompt, "Durable lesson: ", to_stderr=prompt_to_stderr),
            candidate,
        )
        action = _resolve_review_action(
            _prompt_review_input(
                prompt,
                "Action? [k]eep-local/[p]romote-to-pool/[d]iscard (default: discard): ",
                to_stderr=prompt_to_stderr,
            )
        )
        target_path: str | None = None
        if action in {"keep-local", "promote-to-pool"}:
            target_path = _select_nugget_target_path(resolved_project_root, manifest, candidate, lesson)
            if action == "promote-to-pool":
                promote_plans.append((candidate, target_path, lesson))
            else:
                keep_local_plans.append((candidate, target_path, lesson))
        else:
            _record_review_state(
                candidate,
                status="discarded",
                lesson=None,
                target_path=None,
                reviewed_at=today,
            )

        reviewed_items.append(
            _review_item_from_candidate(
                candidate,
                action=action,
                target_path=target_path,
                lesson=lesson if action != "discard" else None,
                auto_discarded=False,
            )
        )

    promotion_report: PromotionReport | None = None
    if dry_run:
        pending_remaining = pending_before
        return NuggetsReviewReport(
            project_root=resolved_project_root,
            pool_root=resolved_pool_root,
            inbox_path=inbox_path,
            dry_run=True,
            pending_before=pending_before,
            pending_remaining=pending_remaining,
            reviewed=tuple(reviewed_items),
            promotion_report=None,
        )

    for candidate, target_path, lesson in promote_plans:
        _write_nugget_lesson_to_project(resolved_project_root, manifest, target_path, lesson)

    if promote_plans:
        requested_paths = sorted({target_path for _, target_path, _ in promote_plans})
        promotion_report = promote_project_changes(
            resolved_project_root,
            pool_root=resolved_pool_root,
            dry_run=False,
            reason="Promote reviewed nuggets into the pool",
            requested_paths=requested_paths,
            now=resolved_now,
        )
        promoted_paths = set(promotion_report.selected_paths)
        missing_paths = [path for path in requested_paths if path not in promoted_paths]
        if missing_paths:
            raise PoolSyncError(
                "Reviewed nugget promotion did not produce promotable changes for: "
                + ", ".join(missing_paths)
            )
        for candidate, target_path, lesson in promote_plans:
            _record_review_state(
                candidate,
                status="promoted-to-pool",
                lesson=lesson,
                target_path=target_path,
                reviewed_at=today,
            )

    for candidate, target_path, lesson in keep_local_plans:
        _write_nugget_lesson_to_project(resolved_project_root, manifest, target_path, lesson)
        _record_review_state(
            candidate,
            status="kept-local",
            lesson=lesson,
            target_path=target_path,
            reviewed_at=today,
        )

    if reviewed_items:
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        inbox_path.write_text(inbox.render(), encoding="utf-8")

    pending_remaining = sum(1 for candidate in inbox.candidates if _candidate_status(candidate) == "pending")
    return NuggetsReviewReport(
        project_root=resolved_project_root,
        pool_root=resolved_pool_root,
        inbox_path=inbox_path,
        dry_run=False,
        pending_before=pending_before,
        pending_remaining=pending_remaining,
        reviewed=tuple(reviewed_items),
        promotion_report=promotion_report,
    )


def _resolve_project_root(project_root: Path) -> Path:
    resolved = project_root.resolve()
    if not resolved.exists():
        raise PoolSyncError(f"Project path does not exist: {resolved}")
    github_dir = resolved / ".github"
    if not github_dir.exists():
        raise PoolSyncError(f"Project path is missing .github/: {resolved}")
    return resolved


def _git_head_sha(pool_root: Path) -> str:
    result = _run_git(pool_root, ["rev-parse", "HEAD"])
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise PoolSyncError(f"Could not resolve pool HEAD in {pool_root}: {stderr or 'git failed'}")
    return result.stdout.decode("utf-8", errors="replace").strip()


def _load_project_stamp(project_root: Path) -> tuple[PoolStamp | None, str | None]:
    stamp_path = project_root / ".github" / ".pool-version"
    if not stamp_path.exists():
        return None, None
    try:
        payload = json.loads(stamp_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"Invalid .pool-version: {exc}"
    if not isinstance(payload, dict):
        return None, "Invalid .pool-version: expected a JSON object"
    pool_sha = str(payload.get("pool_sha", "")).strip()
    if not pool_sha:
        return None, "Invalid .pool-version: missing pool_sha"
    return (
        PoolStamp(
            pool_sha=pool_sha,
            deployed_at=_optional_string(payload.get("deployed_at")),
            profile=_optional_string(payload.get("profile")),
        ),
        None,
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_project_profile(project_root: Path, manifest, stamp: PoolStamp | None) -> str:
    profile_path = project_root / ".github" / ".junai-profile"
    profile: str | None = None
    if profile_path.exists():
        profile = profile_path.read_text(encoding="utf-8").strip() or None
    if not profile and stamp and stamp.profile:
        profile = stamp.profile
    if not profile:
        profile = "full"
    if profile not in manifest.profiles:
        raise PoolSyncError(f"Unknown project profile {profile!r}")
    return profile


def _deploy_managed_directory(pool_github: Path, project_github: Path, directory_name: str) -> None:
    source_dir = pool_github / directory_name
    destination_dir = project_github / directory_name
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    if source_dir.exists():
        shutil.copytree(source_dir, destination_dir, ignore=shutil.ignore_patterns(*GENERATED_ARTIFACT_PARTS, "*.pyc", "*.pyo"))


def _deploy_managed_file(source_path: Path, destination_path: Path) -> None:
    if destination_path.exists():
        destination_path.unlink()
    if not source_path.exists():
        return
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)


def _deploy_skills_directory(pool_github: Path, project_github: Path, manifest, profile: str) -> None:
    source_root = pool_github / "skills"
    destination_root = project_github / "skills"
    if destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    for source_path in sorted(source_root.rglob("*")):
        if not source_path.is_file():
            continue
        relative_path = source_path.relative_to(pool_github).as_posix()
        if _is_generated_artifact_path(Path(relative_path)):
            continue
        classification = _classify_candidate(relative_path, manifest)
        if classification.is_private:
            continue
        if relative_path == "skills/_registry.md":
            continue
        if not _profile_includes_skill(relative_path, manifest, profile):
            continue

        target_path = project_github / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _deploy_managed_region(source_path: Path, destination_path: Path, region: ManagedRegionSpec) -> None:
    if not source_path.exists():
        return
    source_text = source_path.read_text(encoding="utf-8")
    if not destination_path.exists():
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(source_text, encoding="utf-8")
        return

    destination_text = destination_path.read_text(encoding="utf-8")
    updated = _replace_managed_region_text(
        source_text,
        destination_text,
        region,
        source_label=source_path,
        destination_label=destination_path,
    )
    destination_path.write_text(updated, encoding="utf-8")


def _write_project_registry(pool_root: Path, project_root: Path, profile: str) -> None:
    from generate_registry import collect_public_skills, render_registry  # type: ignore[import]

    registry_text = render_registry(collect_public_skills(pool_root, profile=profile))
    registry_path = project_root / ".github" / "skills" / "_registry.md"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(registry_text, encoding="utf-8")


def _write_project_stamp(project_github: Path, pool_sha: str, profile: str) -> Path:
    stamp_path = project_github / ".pool-version"
    payload = {
        "pool_sha": pool_sha,
        "deployed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
    }
    stamp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return stamp_path


def _collect_pool_paths(pool_root: Path, manifest, profile: str) -> set[str]:
    github_dir = pool_root / ".github"
    paths: set[str] = set()

    for directory_name in manifest.tiers["managed"]["directories"]:
        directory = github_dir / directory_name
        if not directory.exists():
            continue
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            if _is_generated_artifact_path(file_path.relative_to(github_dir)):
                continue
            relative_path = file_path.relative_to(github_dir).as_posix()
            if _should_include_candidate(relative_path, manifest, profile):
                paths.add(relative_path)

    for file_name in manifest.tiers["managed"]["files"]:
        file_path = github_dir / file_name
        if file_path.is_file():
            relative_path = file_path.relative_to(github_dir).as_posix()
            if _should_include_candidate(relative_path, manifest, profile):
                paths.add(relative_path)

    for relative_path in manifest.managed_regions:
        file_path = github_dir / relative_path
        if file_path.is_file():
            paths.add(relative_path)

    return paths


def _collect_project_paths(project_root: Path, manifest, profile: str) -> set[str]:
    github_dir = project_root / ".github"
    paths: set[str] = set()

    for directory_name in manifest.tiers["managed"]["directories"]:
        directory = github_dir / directory_name
        if not directory.exists():
            continue
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            if _is_generated_artifact_path(file_path.relative_to(github_dir)):
                continue
            relative_path = file_path.relative_to(github_dir).as_posix()
            if _should_include_candidate(relative_path, manifest, profile):
                paths.add(relative_path)

    for file_name in manifest.tiers["managed"]["files"]:
        file_path = github_dir / file_name
        if file_path.is_file():
            relative_path = file_path.relative_to(github_dir).as_posix()
            if _should_include_candidate(relative_path, manifest, profile):
                paths.add(relative_path)

    for relative_path in manifest.managed_regions:
        file_path = github_dir / relative_path
        if file_path.is_file():
            paths.add(relative_path)

    return paths


def _should_include_candidate(relative_path: str, manifest, profile: str) -> bool:
    classification = _classify_candidate(relative_path, manifest)
    if classification.tier not in {"managed", "managed_region"}:
        return False
    if classification.is_private:
        return False
    if classification.top_level == "skills":
        return _profile_includes_skill(relative_path, manifest, profile)
    return True


def _is_generated_artifact_path(relative_path: Path) -> bool:
    return any(part in GENERATED_ARTIFACT_PARTS for part in relative_path.parts) or (
        relative_path.suffix.lower() in GENERATED_ARTIFACT_SUFFIXES
    )


def _classify_candidate(relative_path: str, manifest) -> Classification:
    try:
        return _classify_with_manifest(relative_path, manifest)
    except (ManifestError, ClassificationError) as exc:
        raise PoolSyncError(str(exc)) from exc


def _profile_includes_skill(relative_path: str, manifest, profile: str) -> bool:
    if not relative_path.startswith("skills/"):
        return False
    skill_relative = relative_path[len("skills/") :]
    if not skill_relative or skill_relative == "_registry.md":
        return False
    if profile == "full":
        return True
    return any(_match_skill_glob(skill_relative, pattern) for pattern in manifest.profiles[profile])


def _match_skill_glob(skill_relative: str, pattern: str) -> bool:
    candidate = skill_relative.replace("\\", "/").strip("/")
    normalized = pattern.replace("\\", "/").strip("/")
    if normalized == "**":
        return True
    if normalized.endswith("/**"):
        prefix = normalized[:-3].rstrip("/")
        return candidate == prefix or candidate.startswith(prefix + "/")
    return candidate == normalized


def _read_project_content(project_root: Path, relative_path: str, classification: Classification) -> bytes | None:
    path = project_root / ".github" / relative_path
    return _read_comparison_content(path, classification)


def _read_pool_worktree_content(pool_root: Path, relative_path: str, classification: Classification) -> bytes | None:
    path = pool_root / ".github" / relative_path
    return _read_comparison_content(path, classification)


def _read_base_content(
    pool_root: Path,
    stamp: PoolStamp | None,
    relative_path: str,
    classification: Classification,
) -> bytes | None:
    if stamp is None:
        return None
    result = _run_git(pool_root, ["show", f"{stamp.pool_sha}:.github/{relative_path}"])
    if result.returncode != 0:
        return None
    if classification.managed_region is None:
        return _normalize_content_bytes(result.stdout)
    return _normalize_content_bytes(_extract_region_bytes(result.stdout, classification.managed_region))


def _read_comparison_content(path: Path, classification: Classification) -> bytes | None:
    if not path.exists() or not path.is_file():
        return None
    content = path.read_bytes()
    if classification.managed_region is None:
        return _normalize_content_bytes(content)
    return _normalize_content_bytes(_extract_region_bytes(content, classification.managed_region))


def _extract_region_bytes(content: bytes, region: ManagedRegionSpec) -> bytes:
    text = content.decode("utf-8", errors="replace")
    start = text.find(region.start_marker)
    end = text.find(region.end_marker)
    if start == -1 or end == -1 or end < start:
        return b""
    start += len(region.start_marker)
    return text[start:end].encode("utf-8")


def _normalize_content_bytes(content: bytes) -> bytes:
    if b"\x00" in content:
        return content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    return text.replace("\r\n", "\n").encode("utf-8")


def _classify_content_state(
    project_content: bytes | None,
    base_content: bytes | None,
    pool_content: bytes | None,
) -> str:
    if project_content == pool_content and project_content is not None:
        return "unchanged"
    if project_content is None and pool_content is not None:
        return "pool-only"
    if project_content is not None and pool_content is None:
        return "project-only"
    if project_content is None and pool_content is None:
        return "unchanged"
    if base_content is None:
        return "project-newer"
    if project_content == base_content and pool_content != base_content:
        return "pool-newer"
    if pool_content == base_content and project_content != base_content:
        return "project-newer"
    if project_content == pool_content:
        return "unchanged"
    return "both-changed"


def _run_git(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        capture_output=True,
    )


def _normalize_relative_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    if normalized.startswith(".github/"):
        normalized = normalized[len(".github/") :]
    return normalized


def _candidate_status(candidate: NuggetCandidate) -> str:
    return (candidate.get("status") or "").strip().lower()


def _candidate_commit(candidate: NuggetCandidate) -> str | None:
    return candidate.get("commit") or candidate.get("from-commits")


def _candidate_proposed_target(candidate: NuggetCandidate) -> str | None:
    proposed_target = candidate.get("proposed-target")
    if not proposed_target:
        return None
    normalized = proposed_target.strip()
    if not normalized or normalized.startswith("("):
        return None
    return normalized


def _is_stale_pending_candidate(candidate: NuggetCandidate, today) -> bool:
    if _candidate_status(candidate) != "pending" or not candidate.date:
        return False
    try:
        candidate_date = datetime.strptime(candidate.date, "%Y-%m-%d").date()
    except ValueError:
        return False
    return candidate_date <= today - timedelta(days=14)


def _print_candidate_for_review(candidate: NuggetCandidate) -> None:
    print("")
    print(candidate.heading)
    print(f"  date:             {candidate.date or '(missing)'}")
    print(f"  version:          {candidate.version or '(missing)'}")
    print(f"  commit:           {_candidate_commit(candidate) or '(missing)'}")
    print(f"  source:           {candidate.get('source') or '(missing)'}")
    print(f"  raw:              {candidate.get('raw') or '(missing)'}")
    print(f"  shape:            {candidate.get('shape') or '(missing)'}")
    print(f"  suggested_route:  {candidate.get('suggested-route') or '(missing)'}")


def _prompt_review_input(
    prompt_func: Callable[[str], str],
    prompt_text: str,
    *,
    to_stderr: bool,
) -> str:
    if prompt_func is input and to_stderr:
        print(prompt_text, end="", file=sys.stderr, flush=True)
        return input()
    return prompt_func(prompt_text)


def _resolve_review_action(raw_choice: str) -> str:
    choice = raw_choice.strip().lower()
    if choice in {"k", "keep", "keep-local"}:
        return "keep-local"
    if choice in {"p", "promote", "promote-to-pool"}:
        return "promote-to-pool"
    return "discard"


def _normalize_lesson_text(raw_lesson: str, candidate: NuggetCandidate) -> str:
    collapsed = " ".join(raw_lesson.split()).strip()
    if collapsed:
        return collapsed
    fallback = candidate.get("nugget") or candidate.get("raw") or "Capture the durable lesson from this candidate."
    return re.sub(r"^\w+(?:\([^)]*\))?!?:\s*", "", fallback).strip()


def _select_nugget_target_path(project_root: Path, manifest, candidate: NuggetCandidate, lesson: str) -> str:
    proposed_target = _candidate_proposed_target(candidate)
    if proposed_target:
        normalized = _normalize_relative_path(proposed_target)
        try:
            classification = _classify_candidate(normalized, manifest)
        except PoolSyncError:
            classification = None
        if classification and classification.tier in {"managed", "managed_region"}:
            return normalized

    instructions_root = project_root / ".github" / "instructions"
    instruction_paths = sorted(
        path.relative_to(project_root / ".github").as_posix()
        for path in instructions_root.glob("*.instructions.md")
        if path.is_file()
    )
    target_text = " ".join(
        value
        for value in (
            lesson,
            candidate.get("raw"),
            candidate.get("nugget"),
            candidate.get("category"),
        )
        if value
    )
    target_tokens = _meaningful_tokens(target_text)
    best_path: str | None = None
    best_score = 0
    for relative_path in instruction_paths:
        stem = Path(relative_path).name
        if stem.endswith(".instructions.md"):
            stem = stem[: -len(".instructions.md")]
        score = len(target_tokens & _meaningful_tokens(stem.replace("-", " ")))
        if score > best_score:
            best_score = score
            best_path = relative_path
    if best_path and best_score > 0:
        return best_path
    return "copilot-instructions.md"


def _meaningful_tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= 3}


def _write_nugget_lesson_to_project(project_root: Path, manifest, relative_path: str, lesson: str) -> None:
    normalized_path = _normalize_relative_path(relative_path)
    classification = _classify_candidate(normalized_path, manifest)
    if classification.tier not in {"managed", "managed_region"}:
        raise PoolSyncError(f"Nugget target is not writable managed content: {normalized_path}")

    destination_path = project_root / ".github" / normalized_path
    if classification.managed_region is None:
        existing_text = destination_path.read_text(encoding="utf-8") if destination_path.exists() else ""
        updated_text = _append_reviewed_nugget(existing_text, lesson)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(updated_text, encoding="utf-8")
        return

    if destination_path.exists():
        destination_text = destination_path.read_text(encoding="utf-8")
    else:
        destination_text = (
            f"{classification.managed_region.start_marker}\n"
            f"{classification.managed_region.end_marker}\n"
        )
    replacement = _append_reviewed_nugget(
        _extract_region_text(destination_text, classification.managed_region),
        lesson,
    )
    updated = _replace_managed_region_text(
        destination_text,
        destination_text,
        classification.managed_region,
        source_label=destination_path,
        destination_label=destination_path,
    )
    managed_region = classification.managed_region
    region_start = updated.find(managed_region.start_marker) + len(managed_region.start_marker)
    region_end = updated.find(managed_region.end_marker)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(updated[:region_start] + replacement + updated[region_end:], encoding="utf-8")


def _append_reviewed_nugget(existing_text: str, lesson: str) -> str:
    bullet = f"- {lesson.strip()}"
    normalized = existing_text.replace("\r\n", "\n").rstrip("\n")
    if not normalized:
        return f"## Reviewed Nuggets\n\n{bullet}\n"
    if "## Reviewed Nuggets" not in normalized:
        return normalized + f"\n\n## Reviewed Nuggets\n\n{bullet}\n"
    return normalized + f"\n{bullet}\n"


def _extract_region_text(content: str, region: ManagedRegionSpec) -> str:
    start = content.find(region.start_marker)
    end = content.find(region.end_marker)
    if start == -1 or end == -1 or end < start:
        raise PoolSyncError(f"Managed region markers not found in {region.path!r}")
    start += len(region.start_marker)
    return content[start:end]


def _record_review_state(
    candidate: NuggetCandidate,
    *,
    status: str,
    lesson: str | None,
    target_path: str | None,
    reviewed_at,
) -> None:
    candidate.set("status", status)
    candidate.set("reviewed-at", reviewed_at.isoformat())
    if lesson:
        candidate.set("durable-lesson", lesson)
    if target_path:
        candidate.set("final-target", target_path)


def _review_item_from_candidate(
    candidate: NuggetCandidate,
    *,
    action: str,
    target_path: str | None = None,
    lesson: str | None = None,
    auto_discarded: bool,
) -> NuggetsReviewItem:
    return NuggetsReviewItem(
        fingerprint=candidate.get("fingerprint"),
        date=candidate.date,
        version=candidate.version,
        commit=_candidate_commit(candidate),
        source=candidate.get("source"),
        raw=candidate.get("raw"),
        shape=candidate.get("shape"),
        suggested_route=candidate.get("suggested-route"),
        action=action,
        target_path=target_path,
        lesson=lesson,
        auto_discarded=auto_discarded,
    )


def _evaluate_requested_promotion(
    relative_path: str,
    report: DiffReport,
    manifest,
    eligible_paths: set[str],
) -> tuple[bool, str | None]:
    try:
        classification = _classify_candidate(relative_path, manifest)
    except PoolSyncError as exc:
        return False, str(exc)

    if classification.tier not in {"managed", "managed_region"}:
        return False, f"{classification.tier} content cannot be promoted"
    if classification.is_private:
        return False, "private content cannot be promoted"
    if classification.top_level == "skills" and not _profile_includes_skill(relative_path, manifest, report.project_profile):
        return False, f"excluded by project profile {report.project_profile!r}"
    if relative_path not in eligible_paths:
        entry = next((candidate for candidate in report.entries if candidate.path == relative_path), None)
        if entry is not None:
            return False, f"status {entry.status!r} is not promotable"
        return False, "path is not present in the promotable managed diff set"
    return True, None


def _prompt_for_promotion(entries: tuple[DiffEntry, ...]) -> tuple[list[str], list[str]]:
    selected_paths: list[str] = []
    kept_local_paths: list[str] = []

    for entry in sorted(entries, key=lambda candidate: candidate.path):
        print(f"{entry.status:13} {entry.path}")
        choice = input("Promote to pool? [k]eep-local/[p]romote (default: keep-local): ").strip().lower()
        if choice in {"p", "promote", "y", "yes"}:
            selected_paths.append(entry.path)
        else:
            kept_local_paths.append(entry.path)

    return selected_paths, kept_local_paths


def _promotion_branch_name(project_name: str, *, now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in project_name).strip("-") or "project"
    return f"promote/{safe_name}-{moment.strftime('%Y%m%d')}"


def _checkout_promotion_branch(pool_root: Path, branch_name: str) -> None:
    branch_exists = _run_git(pool_root, ["rev-parse", "--verify", f"refs/heads/{branch_name}"])
    if branch_exists.returncode == 0:
        result = _run_git(pool_root, ["checkout", branch_name])
        if result.returncode != 0:
            raise PoolSyncError(_git_error(result, f"Could not switch to promotion branch {branch_name!r}"))
        return

    result = _run_git(pool_root, ["checkout", "-b", branch_name])
    if result.returncode != 0:
        raise PoolSyncError(_git_error(result, f"Could not create promotion branch {branch_name!r}"))


def _apply_project_change_to_pool(
    project_root: Path,
    pool_root: Path,
    relative_path: str,
    classification: Classification,
) -> None:
    source_path = project_root / ".github" / relative_path
    destination_path = pool_root / ".github" / relative_path
    if not source_path.exists():
        raise PoolSyncError(f"Selected promotion path is missing in the project: {source_path}")

    if classification.managed_region is None:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        return

    if not destination_path.exists():
        raise PoolSyncError(f"Managed-region promotion target is missing in the pool: {destination_path}")

    source_text = source_path.read_text(encoding="utf-8")
    destination_text = destination_path.read_text(encoding="utf-8")
    updated = _replace_managed_region_text(
        source_text,
        destination_text,
        classification.managed_region,
        source_label=source_path,
        destination_label=destination_path,
    )
    destination_path.write_text(updated, encoding="utf-8")


def _replace_managed_region_text(
    source_text: str,
    destination_text: str,
    region: ManagedRegionSpec,
    *,
    source_label: Path,
    destination_label: Path,
) -> str:
    source_start = source_text.find(region.start_marker)
    source_end = source_text.find(region.end_marker)
    if source_start == -1 or source_end == -1 or source_end < source_start:
        raise PoolSyncError(f"Managed region markers missing in source file: {source_label}")
    destination_start = destination_text.find(region.start_marker)
    destination_end = destination_text.find(region.end_marker)
    if destination_start == -1 or destination_end == -1 or destination_end < destination_start:
        raise PoolSyncError(f"Managed region markers missing in destination file: {destination_label}")

    source_start += len(region.start_marker)
    destination_start += len(region.start_marker)
    return destination_text[:destination_start] + source_text[source_start:source_end] + destination_text[destination_end:]


def _run_pool_validation(pool_root: Path) -> None:
    validator_path = pool_root / "validate_pool.py"
    if not validator_path.exists():
        raise PoolSyncError(f"Pool validator is missing: {validator_path}")

    result = subprocess.run(
        [sys.executable, str(validator_path)],
        cwd=str(pool_root),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        raise PoolSyncError(f"Pool validation failed before commit:\n{output or 'validate_pool.py exited non-zero'}")


def _stage_promotion_paths(pool_root: Path, selected_paths: list[str]) -> None:
    result = _run_git(pool_root, ["add", "--", *[f".github/{path}" for path in selected_paths]])
    if result.returncode != 0:
        raise PoolSyncError(_git_error(result, "Could not stage promoted paths"))


def _commit_promotion(
    pool_root: Path,
    project_root: Path,
    selected_paths: list[str],
    deployed_pool_sha: str | None,
    reason: str | None,
) -> None:
    subject = f"chore(pool): sync reusable changes from {project_root.name}"
    reason_text = reason.strip() if reason and reason.strip() else "(none provided)"
    source_pool_sha = deployed_pool_sha or "(missing .pool-version)"
    file_lines = "\n".join(f"- {path}" for path in selected_paths)
    body = "\n".join(
        [
            f"Source-Project: {project_root}",
            f"Source-Pool-SHA: {source_pool_sha}",
            f"Reason: {reason_text}",
            "",
            "Selected files:",
            file_lines,
        ]
    )
    result = _run_git(pool_root, ["commit", "-m", subject, "-m", body])
    if result.returncode != 0:
        raise PoolSyncError(_git_error(result, "Could not create promotion commit"))


def _git_error(result: subprocess.CompletedProcess[bytes], message: str) -> str:
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    detail = stderr or stdout or "git failed"
    return f"{message}: {detail}"


if __name__ == "__main__":
    raise SystemExit(main())
