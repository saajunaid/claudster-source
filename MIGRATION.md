# Provenance

`claudster-source` was extracted from a larger internal monorepo so that claudster's **publishable
source** (the skill/agent pool, the plugin harness, the MCP server, and the build machinery) lives on
its own, cleanly separated from private/internal content.

The extraction:
- **preserved git history** for the migrated source (via `git filter-repo` with an explicit, fail-closed
  keep-list — only named public paths were carried over);
- **verified** the build is content-identical to the pre-extraction artifact (the generated plugin tree
  matches byte-for-byte, line-endings aside), and that `validate_pool` + the full test suite pass;
- made privacy **structural** — this repo contains only public source, so there is no private content to
  gate or purge at publish time.

The plugin (`claudster` + `claudster-extras`), the MCP (`junai-mcp`), and the VS Code extension are all
built and published from this repo via `sync.ps1` (`junai-push` / `junai-release`).
