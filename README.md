# claudster-source

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Public authoring home for **claudster** — the Claude Code plugin (`claudster` + `claudster-extras`),
its MCP server (`junai-mcp`), the shared skill/agent pool, and the build machinery that publishes them.

## Install claudster (as a Claude Code user)

claudster ships as a Claude Code plugin from the marketplace mirror `saajunaid/junai` (built by this
repo — see [Publishing](#publishing)):

```bash
claude plugin install claudster@claudster
```

That installs the core plugin (lean subagents, TDD commands, the core skill tier, hooks, a
`CLAUDE.md` generator). Optionally add the long-tail skill library (disabled by default — zero
always-on context cost until enabled):

```bash
claude plugin install claudster-extras@claudster   # one-time
claude plugin enable  claudster-extras              # when you need the breadth
```

See `docs/guide/start-here.md` for the toolchain map and `docs/guide/claudster.md` for every
command/skill/hook this plugin provides.

## Installing outside Claude Code (codex, Antigravity, …)

The toolbox's knowledge layer (skills + AGENTS.md conventions) works in any harness. Per-harness
bundles are produced by the exporter and installed into a project with `claudster-init`:

```bash
# from a local claudster-source checkout (uses dist/runtime-resources/<target>)
python scripts/claudster_init.py --target codex        --dest C:\path\to\project
python scripts/claudster_init.py --target antigravity  --dest C:\path\to\project

# or fetch the published bundles from GitHub (once bundles/ are published to saajunaid/junai)
python scripts/claudster_init.py --target codex
```

Safe by design: a sha256 manifest tracks what the installer wrote; re-runs update only unmodified
files, and anything you edited locally is reported as a conflict, never overwritten (use `--force`
to override). Each harness's discovery contract (where skills/AGENTS.md must live and why) is probed,
not assumed — see `docs/guide/porting-to-a-harness.md` to add a new harness in five steps.

## Quickstart (contributing to claudster-source itself)

This repo is the **authoring** source, not the installed plugin — clone it to build/test/publish the
bundles, not to use claudster in another project (use the Install step above for that).

```bash
git clone <this repository's clone URL>
cd claudster-source
python -m venv .venv
.venv/Scripts/pip install pytest fastmcp   # .venv/bin/pip on macOS/Linux

# Run the test suite
.venv/Scripts/python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q

# Validate the pool (frontmatter, roster consistency, privacy denylist, ...)
.venv/Scripts/python validate_pool.py
```

Both should pass clean on a fresh checkout. See `docs/guide/start-here.md` for the wider toolchain
context (claudster + its companion project, docket) and `## Publishing` below for how a change here
reaches the marketplace mirror.

## What's here
- **`.github/`** — the pool: skills, agents, prompts, instructions, tools, recipes, and the build
  manifest (`runtime-targets.json`).
- **`claude-harness/`** — the claudster plugin's agents, commands, hooks, and CLAUDE.md fragments.
- **`scripts/`** — `setup_project_ai.py`, `usage_review.py`, and the test suite.
- Build/validate machinery: `export_runtime_resources.py`, `validate_pool.py`, `validate_agents.py`,
  `sync.ps1`.

## Publishing
`export_runtime_resources.py` generates the plugin bundles into `dist/runtime-resources/`;
`sync.ps1`'s `junai-push` / `junai-release` sync the pool into the distribution mirrors and (opt-in)
publish the plugin, the MCP (PyPI), and the VS Code extension (Marketplace). Run `validate_pool.py`
(including `--profile claude` / `--profile claude-extras` for the shipped plugin bundles) and the test
suite (`python -m pytest scripts/tests`) as the quality gates.

**`junai-push` (default, no flags) is a mirror sync only — it does NOT publish.** It auto-bumps the
`claudster` / `claudster-extras` plugin version whenever the exported bundle content changed and pushes
the pool to the marketplace mirror repo (`saajunaid/junai`, checked out at `vscode-extensions/junai/`).
A release (MCP → PyPI, extension → Marketplace) fires **only when you pass `-Publish`**. This inverts
the old auto-publish default: PyPI is permanent (no unpublish), and a plugin-only session must never
trip an accidental release.

- **Plugin-only change → plain `junai-push`.** Bumps the plugin manifest version and pushes the mirror
  commit; no MCP/VS Code republish.
- **Full publish (MCP + VS Code intentionally changed too) → `junai-push -Publish`** (or `junai-release`
  directly once the mirror is already pushed). A **SHA256 content-diff gate** inside `junai-release`
  skips any target whose *source* is unchanged since the last successful publish (markers:
  `.last-published-mcp.sha256` / `.last-published-ext.sha256`), so even an intentional `-Publish`
  never re-uploads an identical MCP/extension. Use `junai-release -Force` to bypass the gate.
- **`-NoPublish` is deprecated** — publish is now off by default, so the flag is a silent no-op kept
  only for back-compat.
- **`claudster-source` (this repo, the authoring home) and the marketplace mirror (`saajunaid/junai`)
  are separate git remotes.** `junai-push` commits and pushes the mirror repo only — it does not push
  `claudster-source` itself; commit and `git push` this repo separately.
- **`dist/` ACL landmine (Windows).** If an earlier run happened under an elevated shell, files under
  `dist/runtime-resources/claude/.claude-plugin/` can end up owned by `BUILTIN\Administrators`. A later
  *non-elevated* `export_runtime_resources.py` (invoked by `junai-push`) then fails with a
  `PermissionError` inside `ensure_clean_dir`, **and** the mirror sync reports "no changes to commit" using
  the stale pre-failure content — a failure that looks like success. Fix: from an elevated shell run
  `Remove-Item -Recurse -Force dist`, then re-run `junai-push` non-elevated.

## Provenance
This repo was extracted from a larger internal monorepo so that the publishable source lives on its own,
cleanly separated from private/internal content. See [`MIGRATION.md`](./MIGRATION.md) for the extraction
record.

## License
[MIT](./LICENSE) — see the `LICENSE` file. The published plugin bundles (`claudster` /
`claudster-extras`) carry the same license in their manifests.
