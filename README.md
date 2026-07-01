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
`sync.ps1`'s `junai-push` / `junai-release` sync the pool into the distribution mirrors and publish the
plugin, the MCP (PyPI), and the VS Code extension (Marketplace). Run `validate_pool.py` and the test
suite (`python -m pytest scripts/tests`) as the quality gates.

## Provenance
This repo was extracted from a larger internal monorepo so that the publishable source lives on its own,
cleanly separated from private/internal content. See [`MIGRATION.md`](./MIGRATION.md) for the extraction
record.
