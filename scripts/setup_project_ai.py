"""setup_project_ai — deterministic layer of the Claude Code harness generator.

Deploys and customizes the canonical harness (claude-harness/) into a target project:
  • stack detection (pyproject/requirements/package.json + path signals, per stack-map.json)
  • placeholder substitution for provided keys, with a report of any leftovers (Phase 0 friction #1)
  • CLAUDE.md hierarchy composed from fragments by detected stack + AGENTS.md mirror
  • subagents → .claude/agents/, commands → .claude/commands/, settings → .claude/settings.json (merged)
  • frontend Vitest/jsdom test-harness scaffold when react+vitest but no DOM env (Phase 0 friction #4)
  • venv / dev-deps detection (report; create+install only with --install)

Idempotent: existing CLAUDE.md / AGENTS.md / settings are preserved unless --force; settings allow-lists
are always merged (union). This script is the must-not-vary part; CLAUDE.md *enrichment* with
project-specific facts is the AI step of the setup-project-ai skill that wraps this.

Usage:
    python scripts/setup_project_ai.py <target_dir> --name "My App" --desc "One-line description"
        [--set KEY=VALUE ...] [--force] [--install] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

def _resolve_harness_dir() -> Path:
    """Locate the harness resource root (templates, settings template, stack map).

    Two supported layouts:
      • agent-sandbox dev:  scripts/setup_project_ai.py  → ../claude-harness/
      • bundled in plugin:  plugin/scripts/setup_project_ai.py → ../  (claude-md/ et al.
        sit directly at the plugin root, with no claude-harness/ subdir).
    Pick the first candidate that actually carries the templates.
    """
    here = Path(__file__).resolve().parent
    for cand in (here.parent / "claude-harness", here.parent):
        if (cand / "claude-md").is_dir() and (cand / "settings.template.json").is_file():
            return cand
    return here.parent / "claude-harness"  # dev default; missing-template error surfaced later


HARNESS_DIR = _resolve_harness_dir()
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache",
             ".ruff_cache", ".pytest_cache", "dist", "build", ".tanstack", ".codex-tmp"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".toml", ".txt",
                 ".yml", ".yaml", ".cfg", ".ini", ".html", ".css", ".env", ".ps1", ".sh"}


# ── helpers ──────────────────────────────────────────────────────────────────
def load_stack_map() -> dict:
    return json.loads((HARNESS_DIR / "stack-map.json").read_text(encoding="utf-8"))


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


def read_deps(target: Path) -> tuple[set[str], set[str]]:
    """Return (python_deps, js_deps) as lowercased package-name sets."""
    py: set[str] = set()
    for fname in ("pyproject.toml", "requirements.txt", "setup.py"):
        fp = target / fname
        if fp.exists():
            text = fp.read_text(encoding="utf-8", errors="ignore").lower()
            py.update(re.findall(r"[a-z0-9][a-z0-9._-]+", text))
    js: set[str] = set()
    for pj in (target / "package.json", target / "frontend" / "package.json"):
        if pj.exists():
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
                js.update(k.lower() for k in {**data.get("dependencies", {}),
                                             **data.get("devDependencies", {})})
            except json.JSONDecodeError:
                pass
    return py, js


def path_exists_any(target: Path, globs: list[str]) -> bool:
    for g in globs:
        if "*" in g:
            if any(p for p in target.glob(g) if not any(s in p.parts for s in SKIP_DIRS)):
                return True
        elif (target / g).exists():
            return True
    return False


def detect_stack(target: Path, stack_map: dict) -> dict:
    py_deps, js_deps = read_deps(target)
    matched: list[dict] = []
    for det in stack_map["detectors"]:
        ok = False
        if det.get("any_path") and path_exists_any(target, det["any_path"]):
            ok = True
        if det.get("any_dep") and any(d in py_deps for d in det["any_dep"]):
            ok = True
        if det.get("any_dep_json") and any(d in js_deps for d in det["any_dep_json"]):
            ok = True
        if ok:
            matched.append(det)
    return {"matched": matched, "py_deps": py_deps, "js_deps": js_deps}


def stack_summary(stack: dict) -> str:
    ids = {d["id"] for d in stack["matched"]}
    parts = []
    if "python-backend" in ids:
        parts.append("Python")
    if "fastapi" in ids:
        parts.append("FastAPI")
    if "pytest" in ids:
        parts.append("pytest")
    if "react-frontend" in ids:
        parts.append("React/Vite")
    return " · ".join(parts) if parts else "general"


def render(text: str, mapping: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        return mapping.get(m.group(1), m.group(0))
    return PLACEHOLDER_RE.sub(repl, text)


# ── steps ────────────────────────────────────────────────────────────────────
def substitute_placeholders(target: Path, mapping: dict[str, str], dry: bool) -> tuple[int, dict[str, list[str]]]:
    """Replace provided keys across text files; report leftover {{TOKENS}} grouped by file."""
    changed = 0
    leftovers: dict[str, list[str]] = {}
    for fp in iter_text_files(target):
        try:
            text = fp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        if "{{" not in text:
            continue
        new = render(text, mapping)
        if new != text and not dry:
            fp.write_text(new, encoding="utf-8")
        if new != text:
            changed += 1
        remaining = sorted(set(PLACEHOLDER_RE.findall(new)))
        if remaining:
            leftovers[str(fp.relative_to(target))] = remaining
    return changed, leftovers


def compose_claude_md(target: Path, stack: dict, ident: dict[str, str], force: bool, dry: bool) -> list[str]:
    cm = HARNESS_DIR / "claude-md"
    written: list[str] = []
    has_stack_md = (target / "STACK.md").exists()
    mapping = {
        "PROJECT_NAME": ident["name"],
        "PROJECT_DESCRIPTION": ident["desc"],
        "STACK_SUMMARY": stack_summary(stack),
        "STACK_REFERENCE_LINE": "Full stack reference: `STACK.md`." if has_stack_md else "",
    }

    def write(rel: str, content: str):
        dest = target / rel
        if dest.exists() and not force:
            written.append(f"skip (exists): {rel}")
            return
        if not dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        written.append(f"write: {rel}")

    write("CLAUDE.md", render((cm / "root.md.tmpl").read_text(encoding="utf-8"), mapping))
    write("AGENTS.md", render((cm / "agents.md.tmpl").read_text(encoding="utf-8"), mapping))

    # folder fragments — only when the target folder exists
    by_target: dict[str, list[str]] = {}
    for det in stack["matched"]:
        tgt = det.get("target")
        if not tgt:
            continue
        by_target.setdefault(tgt, []).extend(det.get("fragments", []))
    for tgt, frags in by_target.items():
        folder = (target / tgt).parent
        if not folder.exists():
            written.append(f"skip (no folder): {tgt}")
            continue
        body = "\n".join((cm / f).read_text(encoding="utf-8") for f in frags)
        write(tgt, render(body, mapping))
    return written


def deploy_dir(src: Path, dest: Path, force: bool, dry: bool) -> list[str]:
    out: list[str] = []
    for fp in sorted(src.glob("*.md")):
        d = dest / fp.name
        if d.exists() and not force:
            out.append(f"skip (exists): {d.name}")
            continue
        if not dry:
            dest.mkdir(parents=True, exist_ok=True)
            d.write_text(fp.read_text(encoding="utf-8"), encoding="utf-8")
        out.append(f"deploy: {d.name}")
    return out


def merge_settings(target: Path, stack: dict, dry: bool) -> str:
    base = json.loads((HARNESS_DIR / "settings.template.json").read_text(encoding="utf-8"))
    allow = list(base["permissions"]["allow"])
    for det in stack["matched"]:
        for a in det.get("settings_allow", []):
            if a not in allow:
                allow.append(a)
    statusline = {"type": "command", "command": "bash .claude/statusline-command.sh"}
    dest = target / ".claude" / "settings.json"
    notes: list[str] = []
    if dest.exists():
        existing = json.loads(dest.read_text(encoding="utf-8"))
        ex_allow = existing.get("permissions", {}).get("allow", [])
        for a in allow:
            if a not in ex_allow:
                ex_allow.append(a)
        existing.setdefault("permissions", {})["allow"] = ex_allow
        # Strip stale hooks block — the claudster plugin owns all hooks via hooks.json.
        # Defining them here too causes double-fire at session start / pre-compact.
        if "hooks" in existing:
            del existing["hooks"]
            notes.append("removed stale hooks block (now owned by claudster plugin)")
        if "statusLine" not in existing:  # never clobber a user's own status line
            existing["statusLine"] = statusline
            notes.append("added status line")
        out = existing
        verb = "merge"
    else:
        base["permissions"]["allow"] = allow
        base["statusLine"] = statusline
        out = base
        verb = "write"
    if not dry:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    suffix = f" [{'; '.join(notes)}]" if notes else ""
    return f"{verb}: .claude/settings.json ({len(allow)} allow rules){suffix}"


def ensure_frontend_test_harness(target: Path, stack: dict, dry: bool) -> list[str]:
    cfg = load_stack_map().get("frontend_test_harness", {})
    js = stack["js_deps"]
    notes: list[str] = []
    if not any(d in js for d in cfg.get("trigger_dep_any", [])):
        return notes  # no vitest → nothing to do
    if any(d in js for d in cfg.get("require_dep_any", [])):
        notes.append("frontend test harness: DOM env already present — ok")
        return notes
    fe = target / "frontend" if (target / "frontend" / "package.json").exists() else target
    pj = fe / "package.json"
    if pj.exists() and not dry:
        data = json.loads(pj.read_text(encoding="utf-8"))
        dev = data.setdefault("devDependencies", {})
        for dep in cfg.get("ensure_dev_deps", []):
            dev.setdefault(dep, "latest")
        pj.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    notes.append(f"frontend test harness: added {cfg.get('ensure_dev_deps')} to devDependencies (run npm install)")
    setup_rel = cfg.get("setup_file", "src/test/setup.ts")
    setup_fp = fe / setup_rel
    if not setup_fp.exists() and not dry:
        setup_fp.parent.mkdir(parents=True, exist_ok=True)
        setup_fp.write_text(
            '// Vitest global setup: jest-dom matchers + DOM cleanup between tests.\n'
            'import "@testing-library/jest-dom/vitest";\n'
            'import { afterEach } from "vitest";\n'
            'import { cleanup } from "@testing-library/react";\n\n'
            'afterEach(() => {\n  cleanup();\n});\n',
            encoding="utf-8",
        )
        notes.append(f"frontend test harness: wrote {setup_rel}")
    notes.append("frontend test harness: ensure vite config uses `vitest/config` with a "
                 "`test` block (environment: jsdom, globals: true, setupFiles: './src/test/setup.ts')")
    return notes


def check_venv(target: Path, install: bool, dry: bool) -> list[str]:
    notes: list[str] = []
    has_py = (target / "pyproject.toml").exists() or (target / "requirements.txt").exists()
    if not has_py:
        return notes
    venv = target / ".venv"
    if venv.exists():
        notes.append("venv: .venv present — ok")
    elif install and not dry:
        import subprocess
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=False)
        notes.append("venv: created .venv (install dev deps: .venv/Scripts/pip install -e .[dev])")
    else:
        notes.append("venv: MISSING — create with `python -m venv .venv` then "
                     "`pip install -e .[dev]` (or re-run with --install)")
    return notes


# Enforced "green before push" gate. Installed into .git/hooks/pre-push. Pure POSIX sh
# so it runs under Git's bundled shell on Windows/Linux/macOS. Auto-skips tools that
# aren't installed; only blocks when a present tool actually fails.
PRE_PUSH_HOOK = r"""#!/usr/bin/env sh
# Managed by claudster setup-project-ai. Delete this file to opt out.
set -eu
echo "[claudster] pre-push quality gate"
fail=0
if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  command -v ruff   >/dev/null 2>&1 && { echo "[gate] ruff check ."; ruff check . || fail=1; }
  command -v mypy   >/dev/null 2>&1 && { echo "[gate] mypy ."; mypy . || fail=1; }
  command -v pytest >/dev/null 2>&1 && { echo "[gate] pytest -q"; pytest -q || fail=1; }
fi
if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
  npm run 2>/dev/null | grep -q " lint"      && { echo "[gate] npm run lint"; npm run lint --silent || fail=1; }
  npm run 2>/dev/null | grep -q " typecheck" && { echo "[gate] npm run typecheck"; npm run typecheck --silent || fail=1; }
  npm run 2>/dev/null | grep -q " test"       && { echo "[gate] npm test"; npm test --silent || fail=1; }
fi
if [ "$fail" -ne 0 ]; then
  echo "[claudster] push BLOCKED — fix the above, or 'git push --no-verify' to override." >&2
  exit 1
fi
echo "[claudster] gate passed — pushing."
"""


def install_git_hooks(target: Path, force: bool, dry: bool) -> list[str]:
    """Install the enforced pre-push quality gate into .git/hooks/pre-push."""
    notes: list[str] = []
    git = target / ".git"
    if not git.exists():
        return ["pre-push gate: no .git (not a git repo) — skipped"]
    if git.is_file():  # worktree/submodule: .git is a pointer file
        return ["pre-push gate: .git is a worktree pointer — skipped (install manually if wanted)"]
    hooks_dir = git / "hooks"
    dest = hooks_dir / "pre-push"
    if dest.exists() and not force:
        managed = "claudster" in dest.read_text(encoding="utf-8", errors="ignore")
        return [f"pre-push gate: exists ({'ours' if managed else 'yours — left intact, use --force to replace'}) — skipped"]
    if not dry:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(PRE_PUSH_HOOK, encoding="utf-8", newline="\n")
        try:
            import os, stat
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except Exception:
            pass
    notes.append("pre-push gate: installed .git/hooks/pre-push (green-before-push enforced)")
    return notes


def deploy_statusline(target: Path, force: bool, dry: bool) -> list[str]:
    """Copy the status-line script into .claude/ so settings.json can reference it."""
    src = HARNESS_DIR / "statusline-command.sh"
    if not src.is_file():
        return []
    dest = target / ".claude" / "statusline-command.sh"
    if dest.exists() and not force:
        return ["status line: .claude/statusline-command.sh present — skipped"]
    if not dry:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    return ["status line: wrote .claude/statusline-command.sh"]


def extract_project_facts(target: Path, stack: dict) -> dict:
    """Mechanically pull the facts the AI enrichment step (skill Step 3) otherwise has to
    hunt for: run/test/build commands, env-var names, CI/deploy workflows, entry points.
    Best-effort — any unreadable source is skipped. NEVER reads a real .env (only *.example),
    and captures variable NAMES only, never values."""
    facts: dict[str, list[str]] = {"commands": [], "env": [], "workflows": [], "entry": []}

    # npm scripts (root + frontend/)
    for pj in (target / "package.json", target / "frontend" / "package.json"):
        if pj.is_file():
            try:
                scripts = json.loads(pj.read_text(encoding="utf-8")).get("scripts", {})
                rel = pj.parent.relative_to(target)
                prefix = "" if str(rel) == "." else f"(in {rel}/) "
                for name in scripts:
                    facts["commands"].append(f"{prefix}npm run {name}")
            except Exception:
                pass

    # python scripts + the obvious test runner
    pp = target / "pyproject.toml"
    if pp.is_file():
        try:
            import tomllib
            data = tomllib.loads(pp.read_text(encoding="utf-8"))
            tables = [data.get("project", {}).get("scripts", {}),
                      data.get("tool", {}).get("poetry", {}).get("scripts", {})]
            for table in tables:
                for name in (table or {}):
                    facts["commands"].append(f"{name}  (pyproject script)")
        except Exception:
            pass
    if pp.is_file() or (target / "requirements.txt").is_file():
        facts["commands"].append("pytest -q   (if pytest configured)")

    # env var NAMES from example files only — never the real .env (it holds secrets)
    for envf in (".env.example", ".env.sample", ".env.template"):
        ef = target / envf
        if ef.is_file():
            try:
                for line in ef.read_text(encoding="utf-8").splitlines():
                    s = line.strip()
                    if s and not s.startswith("#") and "=" in s:
                        nm = s.split("=", 1)[0].strip()
                        if nm and nm == nm.upper() and nm.replace("_", "").isalnum():
                            facts["env"].append(nm)
            except Exception:
                pass
            break

    # CI / deploy workflows
    for wfdir in (".gitea/workflows", ".github/workflows"):
        d = target / wfdir
        if d.is_dir():
            for f in sorted(list(d.glob("*.yml")) + list(d.glob("*.yaml"))):
                facts["workflows"].append(f"{wfdir}/{f.name}")

    # entry points: detected stack folders + common entry files
    for det in stack.get("matched", []):
        tgt = det.get("target")
        if not tgt:
            continue
        folder = (target / tgt).parent
        if folder.exists() and str(folder.relative_to(target)) != ".":
            facts["entry"].append(f"{folder.relative_to(target)}/  ({det.get('id', 'stack')})")
    for cand in ("main.py", "app.py", "manage.py", "src/main.tsx", "src/main.ts",
                 "src/index.tsx", "src/App.tsx"):
        if (target / cand).is_file():
            facts["entry"].append(cand)

    for k, vals in facts.items():
        seen: set[str] = set()
        facts[k] = [v for v in vals if not (v in seen or seen.add(v))]
    return facts


def write_project_facts(target: Path, facts: dict, dry: bool) -> list[str]:
    """Seed .claude/PROJECT-FACTS.md so the AI enrichment step starts from real data."""
    if not any(facts.values()):
        return ["project facts: nothing auto-extractable — skipped"]
    out = [
        "# Project facts — auto-extracted by setup-project-ai",
        "",
        "> Starting point for CLAUDE.md enrichment (skill Step 3). Pulled mechanically from",
        "> package.json / pyproject.toml / .env.example / workflows — **verify, refine, fold the",
        "> right ones into the matching CLAUDE.md (root vs backend/ vs frontend/), then delete this file.**",
        "",
    ]

    def sec(title: str, items: list[str]) -> list[str]:
        return [f"## {title}", "", *[f"- `{i}`" for i in items], ""] if items else []

    out += sec("Commands (run / test / build)", facts["commands"])
    out += sec("Environment variables (names only — values live in your real .env)", facts["env"])
    out += sec("CI / deploy workflows", facts["workflows"])
    out += sec("Entry points / key folders", facts["entry"])
    dest = target / ".claude" / "PROJECT-FACTS.md"
    if not dry:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(out), encoding="utf-8")
    n = sum(len(v) for v in facts.values())
    return [f"project facts: wrote .claude/PROJECT-FACTS.md ({n} facts — fold into the hierarchy, then delete)"]


# ── main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 can't encode → · ✅ ⚠
    ap = argparse.ArgumentParser(description="Deploy the Claude Code harness into a project.")
    ap.add_argument("target", type=Path)
    ap.add_argument("--name", default=None, help="Project name for CLAUDE.md identity")
    ap.add_argument("--desc", default="", help="One-line project description")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="Placeholder substitution, e.g. --set API_PORT_DEV=8099 (repeatable)")
    ap.add_argument("--substitute", action="store_true",
                    help="Apply placeholder substitution across repo files (for fresh-from-template "
                         "projects only). OFF by default — existing projects are scanned/reported, never rewritten.")
    ap.add_argument("--force", action="store_true", help="Overwrite existing CLAUDE.md/AGENTS.md/harness files")
    ap.add_argument("--install", action="store_true", help="Create venv if missing")
    ap.add_argument("--dry-run", action="store_true", help="Report actions without writing")
    args = ap.parse_args()

    target = args.target.resolve()
    if not target.is_dir():
        print(f"ERROR: target not a directory: {target}", file=sys.stderr)
        return 2
    if not HARNESS_DIR.is_dir():
        print(f"ERROR: harness templates not found at {HARNESS_DIR}", file=sys.stderr)
        return 2

    name = args.name or target.name
    mapping: dict[str, str] = {"PROJECT_NAME": name}
    if args.desc:
        mapping["PROJECT_DESCRIPTION"] = args.desc
    for kv in args.set:
        if "=" in kv:
            k, v = kv.split("=", 1)
            mapping[k.strip()] = v.strip()

    stack_map = load_stack_map()
    stack = detect_stack(target, stack_map)
    ident = {"name": name, "desc": args.desc or f"{name} — (fill in: what this project is)."}

    print(f"=== setup-project-ai → {target} {'(dry-run)' if args.dry_run else ''}")
    print(f"Stack detected: {stack_summary(stack)}  [{', '.join(d['id'] for d in stack['matched']) or 'none'}]")

    # Substitution rewrites repo files — only when explicitly requested (fresh-from-template).
    # Otherwise report-only so we never touch an existing project's docs/code.
    apply_sub = args.substitute and not args.dry_run
    sub_changed, leftovers = substitute_placeholders(target, mapping, dry=not apply_sub)
    if args.substitute:
        print(f"\n-- placeholders: substituted in {sub_changed} file(s)")
    else:
        print(f"\n-- placeholders: report-only ({sub_changed} file(s) contain provided keys; "
              f"pass --substitute to apply — intended for fresh template copies, not existing repos)")
    if leftovers:
        print(f"   ⚠ UNRESOLVED placeholders in {len(leftovers)} file(s)"
              f"{' — provide via --set' if args.substitute else ' (informational)'}:")
        seen: set[str] = set()
        for f, toks in sorted(leftovers.items()):
            for t in toks:
                seen.add(t)
            print(f"     {f}: {', '.join(toks)}")
        print(f"   tokens needing values: {', '.join(sorted(seen))}")

    print("\n-- CLAUDE.md hierarchy")
    for line in compose_claude_md(target, stack, ident, args.force, args.dry_run):
        print(f"   {line}")

    print("-- project facts (auto-extracted → seed for enrichment)")
    for line in write_project_facts(target, extract_project_facts(target, stack), args.dry_run):
        print(f"   {line}")

    print("\n-- subagents")
    for line in deploy_dir(HARNESS_DIR / "agents", target / ".claude" / "agents", args.force, args.dry_run):
        print(f"   {line}")
    print("-- commands")
    for line in deploy_dir(HARNESS_DIR / "commands", target / ".claude" / "commands", args.force, args.dry_run):
        print(f"   {line}")

    print("\n-- settings")
    print(f"   {merge_settings(target, stack, args.dry_run)}")

    print("-- status line")
    for line in deploy_statusline(target, args.force, args.dry_run):
        print(f"   {line}")

    print("-- git hooks")
    for line in install_git_hooks(target, args.force, args.dry_run):
        print(f"   {line}")

    fe_notes = ensure_frontend_test_harness(target, stack, args.dry_run)
    if fe_notes:
        print("\n-- frontend test harness")
        for n in fe_notes:
            print(f"   {n}")

    venv_notes = check_venv(target, args.install, args.dry_run)
    if venv_notes:
        print("\n-- python env")
        for n in venv_notes:
            print(f"   {n}")

    print("\n✅ done. Next: review CLAUDE.md hierarchy, then enrich it with project-specific facts "
          "(the setup-project-ai skill's AI step), and run a smoke test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
