# claudster-source

Public authoring home for **claudster** — the Claude Code plugin (`claudster` + `claudster-extras`),
its MCP server (`junai-mcp`), the shared skill/agent pool, and the build machinery that publishes them.

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

## Provenance
This repo was extracted from a larger internal monorepo so that the publishable source lives on its own,
cleanly separated from private/internal content. See [`MIGRATION.md`](./MIGRATION.md) for the extraction
record.
