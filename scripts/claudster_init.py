"""claudster-init — install a claudster toolbox bundle into a project, for any harness.

One canonical toolbox, many harnesses: Claude Code gets the plugin/marketplace; every other
harness (codex, antigravity, copilot, …) gets a per-harness bundle laid into the project by
this script. See docs/guide/porting-to-a-harness.md for how bundles are produced.

Usage:
    python claudster_init.py --target codex                 # fetch from GitHub (published bundles)
    python claudster_init.py --target antigravity --from E:\\path\\to\\claudster-source
    python claudster_init.py --target codex --from repo.tar.gz --dest C:\\proj

Source resolution (--from may be):
    • a published junai checkout       → <src>/bundles/<target>/
    • a claudster-source checkout      → <src>/dist/runtime-resources/<target>/
    • a .tar.gz (GitHub codeload shape, single top-level dir) → same roots inside it
    • omitted → download DEFAULT_TARBALL_URL and proceed as tarball

Safety contract:
    • a sha256 manifest (.claudster-init.json) records every file this tool wrote;
    • re-runs update only files still matching their manifest hash (unmodified);
    • files the user edited — or pre-existing files never written by this tool — are
      CONFLICTS: reported, left untouched, exit 1. --force overwrites them.

Exit codes: 0 ok / up-to-date · 1 conflicts (rest installed) · 2 bad target or source.
Windows-first: stdlib only, no POSIX assumptions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

MANIFEST_NAME = ".claudster-init.json"
DEFAULT_TARBALL_URL = (
    "https://codeload.github.com/saajunaid/junai/tar.gz/refs/heads/main"
)
# Roots (relative to a source checkout) that may hold bundles, in preference order.
BUNDLE_ROOTS = ("bundles", "dist/runtime-resources")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _available_targets(src_root: Path) -> dict[str, Path]:
    """Map target name -> bundle dir for every bundle the source offers."""
    found: dict[str, Path] = {}
    for rel in BUNDLE_ROOTS:
        root = src_root / rel
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir() and child.name not in found:
                found[child.name] = child
    return found


def _resolve_source(from_arg: str | None, scratch: Path) -> Path:
    """Return a directory that contains one of BUNDLE_ROOTS. Downloads/extracts as needed."""
    if from_arg is None:
        tgz = scratch / "bundle-source.tar.gz"
        print(f"Fetching {DEFAULT_TARBALL_URL} ...")
        urllib.request.urlretrieve(DEFAULT_TARBALL_URL, tgz)  # noqa: S310 — fixed https URL
        return _extract_tarball(tgz, scratch)
    src = Path(from_arg)
    if src.is_file():  # tarball path
        return _extract_tarball(src, scratch)
    return src


def _extract_tarball(tgz: Path, scratch: Path) -> Path:
    out = scratch / "extracted"
    with tarfile.open(tgz, "r:gz") as tf:
        tf.extractall(out, filter="data")
    # codeload tarballs have exactly one top-level directory (<repo>-<ref>/)
    entries = [p for p in out.iterdir() if p.is_dir()]
    return entries[0] if len(entries) == 1 else out


def _install(bundle: Path, dest: Path, target: str, force: bool) -> int:
    manifest_path = dest / MANIFEST_NAME
    old_hashes: dict[str, str] = {}
    if manifest_path.exists():
        old_hashes = json.loads(manifest_path.read_text(encoding="utf-8")).get("files", {})

    new_hashes: dict[str, str] = {}
    installed, updated, conflicts, unchanged = [], [], [], []

    for src_file in sorted(p for p in bundle.rglob("*") if p.is_file()):
        rel = src_file.relative_to(bundle).as_posix()
        dst_file = dest / rel
        src_hash = _sha256(src_file)

        if not dst_file.exists():
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            installed.append(rel)
            new_hashes[rel] = src_hash
            continue

        dst_hash = _sha256(dst_file)
        if dst_hash == src_hash:
            unchanged.append(rel)  # identical — adopt (covers pre-existing identical files)
            new_hashes[rel] = src_hash
        elif rel in old_hashes and dst_hash == old_hashes[rel]:
            shutil.copy2(src_file, dst_file)  # ours, unmodified — safe to update
            updated.append(rel)
            new_hashes[rel] = src_hash
        elif force:
            shutil.copy2(src_file, dst_file)
            updated.append(rel)
            new_hashes[rel] = src_hash
        else:
            conflicts.append(rel)  # user-modified or never ours — do not touch
            new_hashes[rel] = old_hashes.get(rel, dst_hash)

    manifest_path.write_text(
        json.dumps({"target": target, "files": new_hashes}, indent=2) + "\n",
        encoding="utf-8",
    )

    if installed:
        print(f"Installed {len(installed)} file(s).")
    if updated:
        print(f"Updated {len(updated)} file(s).")
    if not installed and not updated and not conflicts:
        print(f"Already up to date ({len(unchanged)} file(s) verified).")
    if conflicts:
        print("CONFLICTS — locally modified (or pre-existing) files left untouched;")
        print("re-run with --force to overwrite:")
        for rel in conflicts:
            print(f"  {rel}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="claudster-init", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--target", required=True, help="Harness bundle to install (e.g. codex, antigravity).")
    parser.add_argument("--from", dest="from_", metavar="SRC",
                        help="Local checkout dir or .tar.gz. Omit to download from GitHub.")
    parser.add_argument("--dest", default=".", help="Project directory to install into (default: cwd).")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite locally modified / pre-existing conflicting files.")
    args = parser.parse_args(argv)

    dest = Path(args.dest).resolve()
    if not dest.is_dir():
        print(f"[FAIL] --dest is not a directory: {dest}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="claudster-init-") as tmp:
        try:
            src_root = _resolve_source(args.from_, Path(tmp))
        except Exception as exc:  # download/extract failure — actionable, fail-closed
            print(f"[FAIL] could not obtain bundle source: {exc}", file=sys.stderr)
            return 2

        targets = _available_targets(src_root)
        if args.target not in targets:
            avail = ", ".join(sorted(targets)) or "none found"
            print(f"[FAIL] no '{args.target}' bundle in source. Available: {avail}", file=sys.stderr)
            return 2

        return _install(targets[args.target], dest, args.target, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
