# claudster-source

Public authoring home for **claudster** — the Claude Code plugin (`claudster` + `claudster-extras`),
its MCP server (`junai-mcp`), the shared skill/agent pool, and the build machinery that publishes them.

> **Status: Phase 0 skeleton (empty).** Source has not been migrated yet. This repo was created as the
> target of a planned extraction from the `agent-sandbox` monorepo. Until Phase 1 runs, the live source
> still lives in `agent-sandbox`; do not author here yet.

## Why this repo exists
`agent-sandbox` mixes **public publishable source** (pool + harness + build machinery) with **private
content** (proprietary `vmie/` skills, internal plans, experiments). That co-location is why the publish
pipeline needs a bolt-on "purge private content" step — the path where a proprietary file once leaked.
This repo will hold **only public, publishable source**, making the public/private separation structural:
nothing to purge, because nothing private is here.

## Migration
The extraction is **Option A2**: public source → here; private content → a new private repo; `agent-sandbox`
retired. Plan + phase tracker: `agent-sandbox/.claudster/plans/extract-claudster-to-own-repo.md`.
Move-list and Phase-0 baseline: see [`MIGRATION.md`](./MIGRATION.md).

Migration is staged so a full publish is verified working after every phase. A2 and the lighter A1 are
identical through Phase 4; only the final decommission step differs.
