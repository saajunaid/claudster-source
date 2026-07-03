# Pass 1 — Claudster Foundations

**Scope:** claudster itself (repo `E:\Projects\claudster-source`) — multi-harness portability (A), knowledge model (B), external tool adoption (C), health/streamlining + internal plugin-vs-harness architecture (E), onboarding (G). Packaging, docket integration, and the ClaudsterOS webUI are explicitly **Pass 2's** — the only intentional overlap is the plugin-vs-harness stance, stated crisply below for consistency-checking.

**Method:** six parallel deep-read investigations over the actual codebase (export pipeline, MCP server + pipeline-runner, onboarding scripts, KB machinery), fresh clones of all six kunchenguid repos, and web verification of OKF, LLM-Wiki, the harness landscape, and the `skills` CLI. Every material claim below carries a file citation or a source URL. Analysis date: 2026-07-03. Baseline: plugin v1.3.14, junai-mcp 0.2.26, suite 242 tests passing.

**Executive summary.** Claudster should stay a **plugin-first pool→export system and grow an MCP control seam, not become a standalone harness**. The audit found the seam is ~85% built already: the FastMCP server (`junai-mcp`) imports the pipeline-runner in-process, a proven `claude -p` subprocess recipe already exists in-repo, ~94% of skill bodies are headless-safe, and the interview commands already contain the structural escape hatches a no-interview mode needs. What's missing is five small, concrete additions (a plugin `.mcp.json`, a `run_skill_headless` tool, a lifecycle-event emitter, a headless input contract, and a packaging fix). The knowledge verdict is **OKF-lite**: adopt OKF-conformant YAML frontmatter (~1–5 files, near-zero cost) and keep the flat KB + DOC-MAP index — the raw/+wiki/ split would rework ~16 symbols in `check_doc_coverage.py`, ~43 tests, and every provisioned downstream repo, for a KB that currently holds **one note**. From Kun's suite: adopt `lavish-axi` (runtime `npx`, the interview transport Pass 2 needs) and `treehouse`; take `axi` as principles only; skip the rest on this Windows host. Before any of this ships, fix the two publish-discipline landmines: `junai-push` auto-releases to PyPI (permanent) whenever keys exist, and the shipped Claude plugin bundle — the actual 1.3.x product — has **no validator at all**.

## Headline verdicts

- **Plugin vs harness (E3):** **(a) plugin-first**, exported to more hosts, **plus an MCP control seam** for external triggerability. Do **not** build a standalone harness — the pipeline-runner + MCP server already provide the orchestration brain without owning an agent loop. Seam readiness for Pass 2: **high** (5 gap items, all small; detailed in E and PRD Phase 1).
- **Knowledge (B):** **OKF-lite** — add OKF-conformant frontmatter (`type` + recommended fields) to KB notes and mandate it for new ones; keep the flat `.claudster/kb/` layout and the DOC-MAP table index (which already plays the role of OKF's `index.md`). **Skip** the raw/+wiki/ restructure. Adopt Karpathy's *lint* workflow ideas into `/kb` later, optionally.
- **Adopt/skip (C):** **ADOPT** `lavish-axi` (runtime dep via `npx -y lavish-axi`; skill name is `lavish`; needs a one-time Windows spike) and `treehouse` (optional worktree backend; first-class Windows). **ADOPT-AS-PRINCIPLES** `axi` (guidance doc; no SDK dependency; do **not** build our own TOON CLI now). **ADOPT-AS-CHANNEL** `npx skills add` (verify + register; `.github/skills/` is already a discovery prefix — likely zero code). **SKIP** `no-mistakes` (overlaps the review lane; heavy), `gnhf` (watch; overlaps autopilot), `firstmate` (tmux/symlinks — WSL2-only, 3 weeks old).
- **"Pi" identity (A):** **Mario Zechner's `pi` coding agent** (repo formerly `badlogic/pi-mono`, now `earendil-works/pi`; MIT; tens of thousands of stars; weekly releases). Minimal-by-design, full Agent Skills support, TypeScript extensions instead of shell hooks, **no MCP by design**. Inflection's Pi ruled out (no coding CLI). Harness order: Codex → opencode → Gemini → pi.
- **Onboarding (G):** persona A (Claude Code) works but takes 9–10 manual steps → target 3; persona B (Copilot-only) degrades along a now-documented list (no runtime hooks, no `/ship`, no CLAUDE.md generator, no telemetry); persona C (Gemini-only) is **fully blocked** — no target exists. Build the Gemini target **on demand**, not speculatively.
- **Top health fixes (E):** (1) `junai-push` defaults to full publish — invert it; (2) the shipped claude/claude-extras bundles have zero validation — add a `--profile claude` lane; (3) the plugin dist omits `dream_memory.py`/`dream_capture.py`/`claudster_config.py`, so the documented Dream Memory layer is **silently inert in every field repo** — ship the scripts or retire the claim.

---

# Part 1 — Decision Document

## Workstream A — Multi-harness portability + OSS publishing

### A.1 Compatibility matrix

Current state first: `runtime-targets.json` defines **six** targets, not four — `copilot`, `ptarmigan`, `liffey`, `codex`, `claude`, `claude-extras` (`.github/runtime-targets.json:8,26,203,402,464,543`). A **Codex lite target already exists** (skills + `AGENTS.md` + `.codex/config.toml.example`), which the planning brief under-counted. The junai-vscode extension is fed from the `copilot` target (full pool) via `vscode-extensions/junai-vscode/scripts/bundle-pool.js`.

Externally verified capability matrix (mid-2026 docs; source URLs in `docs/analysis/` research trail):

| Capability | Codex CLI | Gemini CLI | opencode | pi (earendil-works) |
|---|---|---|---|---|
| Lifecycle hooks | **Native, near-identical to CC**: shell-command hooks, JSON stdin/stdout, exit 2 = block; `hooks.json` in `~/.codex/` or `<repo>/.codex/` (SessionStart, PreToolUse, PostToolUse, PreCompact, Stop, …) | **Native**: shell hooks in `.gemini/settings.json` (SessionStart/End, Before/AfterTool, Before/AfterModel, …) | Native but **JS/TS plugins**, not shell (`.opencode/plugins/`; `tool.execute.before/after`, session events) | Native but **TS extensions** (`.pi/extensions/`; `tool_call` gate, `session_start`, context rewrite) |
| MCP config | `[mcp_servers.<name>]` in `~/.codex/config.toml`; `codex mcp add` | `mcpServers` in `settings.json` | `"mcp"` key in `opencode.json` | **Absent by design** — wrap MCP as CLI tools |
| Skills (SKILL.md) | Native, agentskills.io standard; `.agents/skills` | Native (stable ~v0.26); `.gemini/skills/` | Native; reads `.opencode/skills/`, **`.claude/skills/`**, `.agents/skills/` | Native; `.pi/skills/`, `.agents/skills/`, npm skills |
| Commands/prompts | Markdown in `~/.codex/prompts/` | **TOML** in `.gemini/commands/` (`{{args}}`, `!{shell}`) | Markdown `command/` dirs, `$ARGUMENTS` | Markdown slash-command templates |
| AGENTS.md | Native, first-class | Configurable (`context.fileName` flip; GEMINI.md default) | Native default | Native, hierarchical |
| Headless | `codex exec "<prompt>"` | `gemini -p "<prompt>"` | `opencode run` + `opencode serve` (HTTP) | JSON-stream/RPC + TS SDK |

**What ports as-is vs needs an adapter:**
- **Skills port as-is** everywhere. The ecosystem converged on the Agent Skills spec; `.agents/skills/` is read natively by Codex, opencode, and pi. Our pool skills already carry conformant `name`+`description` frontmatter (validated by `validate_pool.py`).
- **AGENTS.md ports as-is** (setup already emits it — `scripts/setup_project_ai.py:154-192`); Gemini needs one settings flip.
- **Hooks are the real seam.** All five claudster handlers are stdlib-Python, JSON-on-stdin, fail-open (`claude-harness/hooks/*.py`) — the *logic* is portable. Codex and Gemini speak the same shell-command JSON protocol → adapter = an event-name-mapped `hooks.json` per harness (small). opencode and pi need a ~20-line JS/TS shim that shells out to the same Python handlers.
- **Commands need per-harness transforms** (markdown→TOML for Gemini; markdown→prompts for Codex — the manifest's `transforms` machinery exists but is currently unused dead code, `export_runtime_resources.py:197-287,569-583`; Gemini support would finally use it).
- **MCP ports to three** (TOML for Codex, JSON for Gemini/opencode) and **degrades to a CLI wrapper for pi**.

### A.2 Symlinks (Kun) vs build/export/copy (claudster)

**Keep the copy/export pipeline.** Head-to-head:

| | Symlink model (Kun / `skills` CLI) | Copy/export (claudster) |
|---|---|---|
| Freshness | Always fresh (one canonical copy) | Stale until next `junai-push` (health issue #3) |
| Windows | The `skills` CLI actually uses **directory junctions** on win32 with copy-fallback (`installer.ts:254`) — no admin needed. Raw symlinks (firstmate's tracked symlinks) break on default Windows checkouts — confirmed in our clone | Native, no privilege issues |
| Curation | None — whole skill or nothing | Per-target rosters (`included_skills`), tiering (core 40 / extras 99), leak scan (`export_runtime_resources.py:697-715`) |
| Versioning | None | Versioned, auditable bundles; marketplace-publishable |
| Transforms | Impossible (same bytes everywhere) | Possible (flattening, registry pruning, future md→TOML) |

The symlink model is a **consumer-side install optimization**; claudster is a **producer**. Its curation tiers, per-target rosters, transforms, and marketplace packaging are exactly what symlinks can't do. Verdict: **no change** — and note the two models compose: consumers can `npx skills add saajunaid/junai` (junction-based) *from* our copied pool without us changing anything.

### A.3 OSS-publishing gaps; adopt `npx skills add`?

Already have: MIT, GitHub, PyPI (`junai-mcp`), VS Code Marketplace ×3, Claude Code marketplace mirror. Gaps, in value order:

1. **`npx skills add saajunaid/junai` almost certainly already works** — the Vercel `skills` CLI scans `.github/skills/` as a discovery prefix (`src/blob.ts` known prefixes) and fetches via the GitHub tree API without cloning. **Adopt as a distribution channel: verify once, document in README, submit to skills.sh.** Near-zero engineering; reaches ~72 harnesses.
2. **No CI on any repo** — the only validation is local (`junai-push` lanes). A GitHub Action running `pytest` + `validate_pool.py` + `check_doc_coverage.py --check` on push is table stakes for OSS credibility.
3. **The shipped plugin bundle has no validator** (health #2) — an OSS consumer's first artifact is the least-checked one. Fixed in PRD Phase 0.
4. Skippable: npm packaging of an installer (see G.3 — defer), docs site, GitHub Releases for the pool.

### A.4 Phased harness order (given E's plugin-first verdict)

1. **Codex — harden the existing target** (it already ships skills + AGENTS.md + config example, and the junai MCP wiring is documented: `claude-harness/config.toml.example:20-34`). Add: hooks adapter (`.codex/hooks.json` mapping our five handlers — Codex's event model is near-identical), prompts export. Cheapest, and Codex is the #2 harness by adoption.
2. **opencode — nearly free**: it natively reads `.claude/skills/` and `.agents/skills/` and speaks MCP JSON. Deliverable is documentation + a ~20-line JS hook shim. Do it opportunistically.
3. **Gemini CLI — on demand** (persona C is blocked today, but no Gemini-only consumer exists yet; see risk flags). Needs a real target: GEMINI.md (or `context.fileName` flip), `.gemini/skills/`, commands md→TOML transform (finally uses the dormant `transforms` machinery), MCP settings snippet.
4. **pi — skills-only, last.** Skills export lands free via `.agents/skills/`; hooks would need TS extensions and MCP needs CLI wrappers. Serve it via the `npx skills add` channel rather than a dedicated target until demand exists.

Dependency on E: none of this waits on a restructure — plugin-first means exports proceed as today. The one ordering constraint: **Phase 0 publish-safety ships before any new target**, because every target addition rides `junai-push`.

## Workstream B — Knowledge/governance: OKF vs LLM-Wiki vs Kun's minimal-memory vs hybrid

### B.1 OKF, verified

OKF is real and **much less prescriptive than assumed**: "Open Knowledge Format" v0.1 (Draft), Google Cloud, announced 2026-06-12, spec at `GoogleCloudPlatform/knowledge-catalog/okf/SPEC.md`. Requirements: YAML frontmatter on every non-reserved `.md` where **only `type` is required** (producer-defined values); recommended `title`, `description`, `resource`, `tags`, `timestamp`; reserved `index.md`/`log.md` conventions; bundle-absolute links; **no prescribed directory layout** — the raw/+wiki/ split is Karpathy's LLM-Wiki pattern (gist, 2026-04-03), not an OKF mandate. No SDK, no validator tooling published.

This dissolves the assumed trade-off: **full OKF conformance does not require restructuring the KB.**

Migration cost, measured against the actual code:
- **Light (frontmatter + keep DOC-MAP): ~1–5 files.** The KB currently holds exactly **one note** (`.claudster/kb/harness-memory.md`) plus the index. `check_doc_coverage.py` never parses note bodies — governance is glob-existence + link-presence (`GOVERNED_GLOBS`, link regex `\]\(([^)]+\.md)\)`) — so frontmatter is invisible to it. Only optional hardening: teach `extract_docmap_entries` to strip a leading `---` block (~3 lines + 2 tests).
- **Heavy (raw/+wiki/ + new index): ~22–25 files + the downstream fleet.** `GOVERNED_GLOBS` and `kb_note_rows` are non-recursive — subdirs make the gate go **silently blind**; a restructure reworks ~16 of the checker's ~25 symbols (the entire reindex/prune half), ~35/58 tests in `test_check_doc_coverage.py` + 5 in `test_setup_claudster.py` + 3 hook tests, 7 command/agent/template files, 2 hooks, 4 setup/gate/packaging files — **and every repo `setup_project_ai.py` ever provisioned carries a copied checker + old-format DOC-MAP with no auto-update channel.**

### B.2 vs Kun's minimal-memory model

Kun's model (~27-line global memory, per-repo collective-learning file, Skills for progressive disclosure) is already structurally covered: cross-repo layer = Claude Code's native auto-memory (zero claudster code); per-repo learning = KB + relay; progressive disclosure = DOC-MAP's "router, not summary" design + `context: fork` skills. Where the four-layer model does **not** earn its keep:

- **Dream Memory is the weak layer, and it's currently a false claim in the field.** ~630 LoC (`dream_memory.py` 417 + `dream_capture.py` 215) + two test files, to auto-capture two LLM-free fact kinds (errored Bash, red→green) that substantially overlap relay.md at SessionStart. Worse: the shipped plugin dist (`dist/runtime-resources/claude/plugin/scripts/` — 3 files) **omits** `dream_memory.py`, `dream_capture.py`, and `claudster_config.py`; the hooks import them fail-open, so the layer is silently inert in every plugin-installed repo. The four-layer model is a **two-layer model in the field** (relay + KB; cross-repo is host-native). The dream→KB promotion loop is prose in `knowledge-transfer.md:80-86`, not code.
- Relay + KB clearly earn their keep (cheap, high-signal, gated). Cross-repo is free.

**Decision on Dream Memory:** ship the three missing scripts (3 lines in `runtime-targets.json` — PRD Phase 1), because the code exists, is fail-open, and the fix also un-breaks the `[dream_memory]` config section the docs promise. Set an explicit sunset test: if `/usage-review` shows no surfaced dream facts influencing sessions within ~2 months, retire the layer rather than build the promotion loop.

### B.3 Verdict: **OKF-lite** (named hybrid)

- Add OKF-conformant frontmatter (`type` required; `title`, `description`, `tags`, `timestamp` recommended) to the existing note and mandate it in `kb.md` + `knowledge-transfer.md` for new notes. This buys the interop/coupling key (Pass 2 can key on `type:`/`feature:` frontmatter) at near-zero cost.
- Keep the flat layout, the DOC-MAP table, and the deterministic reindex/prune machinery — they are this repo's hardened, tested asset (58 tests, anchor-passed this quarter).
- DOC-MAP already *is* OKF's `index.md` in spirit (curated links + one-line descriptions, progressive disclosure). Do not rename or reshape it; if strict OKF conformance ever matters externally, emitting an `index.md` view from DOC-MAP is a ~30-line generator, decidable later.
- Skip raw/. There are no immutable source documents to quarantine — the KB is already the "wiki" half. Revisit only if the KB grows ingestion of external raw material.
- Optional later: a `/kb lint` pass borrowing Karpathy's lint workflow (contradictions, stale claims, orphans) — flagged as nice-to-have, not scheduled.

**Solo-user test:** the KB has one note. Any migration heavier than frontmatter fails the "worth it?" test outright; OKF-lite passes because it costs an afternoon and creates the external coupling key Pass 2 wants.

## Workstream C — Kun's tool suite: adopt / vendor / skip

All six repos cloned and read from source (scratchpad clones, 2026-07-03). All are MIT (© 2026 Kun Chen) — no license conflicts with MIT anywhere in the suite. Two default-on telemetry endpoints exist in the stack: `a.kunchenguid.com` (lavish-axi; opt out `LAVISH_AXI_TELEMETRY=0`) and `add-skill.vercel.sh` (the `skills` CLI; opt out `DISABLE_TELEMETRY`/`DO_NOT_TRACK`).

**Naming correction that Pass 2 must know:** `kunchenguid/lavish` is a **rename-redirect to `lavish-axi`** — there is no separate "lavish" product. The npm package `lavish` is unrelated abandonware. The real npm package is **`lavish-axi`** (v0.1.35, published 2026-07-02); the **skill it ships is named `lavish`** (`skills/lavish/SKILL.md`), hence `/lavish` in Claude Code. Treat "lavish" = skill/brand, "lavish-axi" = repo/package/binary.

### Per-tool verdicts

**`axi` — ADOPT AS PRINCIPLES; skip the SDK; do NOT build our own TOON CLI now.**
It's a spec + SDK + benchmarks, not a tool: 10 agent-ergonomic-CLI principles canonically expressed as a skill (`.agents/skills/axi/SKILL.md`), plus `axi-sdk-js` (~1,890 LOC TS, Node ≥20, single dep `@toon-format/toon`). TOON = YAML-ish scalars + tabular collections with CSV-like rows; the ~40% token-savings figure is the TOON project's claim, while axi's own benchmarks measure end-to-end task cost (gh-axi $0.050 vs GitHub MCP $0.148 over 425 runs). Harness-agnostic (hooks installer covers CC/Codex/opencode, Windows npm-shim aware). 1,283 stars, active. **Application to claudster:** the `junai` CLI + pipeline-runner already follow most axi principles (single-line JSON, nonzero-on-error); converting output to TOON is premature optimization for a solo user whose token bill isn't dominated by CLI output. Vendor nothing; write a one-page principles note in `.github/agent-docs/` citing axi, apply opportunistically when touching CLI output. Tier: agent-docs (guidance), not a shipped dependency.

**`lavish-axi` — ADOPT (runtime dependency via `npx -y lavish-axi`; no vendoring). This is the clear call Pass 2 needs.**
~9,100 LOC ESM JS (Node ≥22; express 5, chokidar, open, axi-sdk-js). Mechanics, verified from source: the CLI health-checks `http://127.0.0.1:4387`, spawns a detached background Express server if absent (logs to `~/.lavish-axi/server.log`, state in `~/.lavish-axi/state.json`), keys sessions by canonical absolute HTML-file path, opens the browser at `/session/<key>`, serves the artifact in an iframe with an injected annotation SDK + automated layout audit, live-reloads via chokidar+SSE. `lavish-axi poll <file>` is an **indefinite HTTP long-poll** (stdout reserved for the final TOON response; stderr heartbeats so harnesses don't think it hung) returning queued `prompts` / `layout_warnings` / `ended`; queued feedback survives poll death — re-running is always safe. `--agent-reply` pushes agent text into the browser chat. Native form controls + `window.lavish.queuePrompt()` make an HTML questionnaire + poll loop work as designed — **viable as docket's interview transport**.
- Harness assumptions: none in the core loop (plain CLI + localhost HTTP); optional hooks installer covers 4 harnesses.
- **Windows caveat (one-time spike required before Pass 2 depends on it):** core loop is portable Node, but `src/cli.js:828` says "lavish-axi isn't shipped for Windows today" — the stale-port recovery path shells out to `lsof`/`ps` (unix-only). Happy path should work; a stuck server on :4387 needs a manual `taskkill`. Verify once on this host.
- Health: MIT, 1,447 stars, pushed same-day (2026-07-03). Skill is generated + CI drift-checked and instructs `npx -y lavish-axi` (no global install).
- **Tier:** `claudster-extras` now (a thin skill/pointer that defers to `npx skills add kunchenguid/lavish-axi --skill lavish` or vendors the generated SKILL.md); promote to core when the docket integration lands. **Upstream sync: runtime-npx** — never vendor the JS; optionally pin `npx lavish-axi@<version>` in the skill text.

**`no-mistakes` — SKIP (revisit only if a pre-push AI gate is wanted).**
Go (~110k LOC), the most mature of the suite (5,032 stars). A local git gate: push to a `no-mistakes` remote → daemon validates in a disposable worktree (intent→rebase→review→test→document→lint→push→PR) before forwarding. Harness-agnostic (drives claude/codex/copilot/opencode/rovodev/pi/ACP headlessly — note it uses `claude -p --output-format stream-json --dangerously-skip-permissions`, corroborating our Phase-1 invocation recipe). Windows binaries released, but the installer script is unix-only. **Why skip:** it's a whole-workflow commitment that duplicates claudster's review lane (code-reviewer agent + pre-push quality gates + `/ship`); running both would double-review every push. Solo-user test: fails — the existing gates already fill this slot.

**`gnhf` — SKIP / WATCH.**
TS CLI (~11k LOC, deps only commander+js-yaml): ralph-style overnight loop — branch, inject `notes.md`, spawn an agent headless, commit on success / `git reset --hard` on failure, abort after 3 consecutive failures. Genuinely Windows-aware (SetThreadExecutionState, `taskkill /T /F`, `where` resolution). 2,838 stars but quietest of the active set (last push 2026-06-10). **Why skip:** overlaps the pipeline-runner's autopilot mode + `run_plan`/`fast_track_from_plan` (already built, `pipeline_runner.py`). If overnight unattended loops become a real need, trial gnhf before building anything — it's low-risk — but don't adopt speculatively.

**`firstmate` — SKIP on this host.**
Clone-and-inhabit bash template (~27k LOC bash, 117KB AGENTS.md): tmux windows + treehouse worktrees per autonomous "crewmate". **Effectively non-viable on native Windows**: hard tmux dependency, tracked git symlinks (confirmed broken in our default-Windows clone), `/tmp`, POSIX `ps`. WSL2-only, and the repo is 3 weeks old (created 2026-06-12). Fails both the platform test and the maturity test.

**`treehouse` — ADOPT (optional runtime dependency).**
Go CLI (~10k LOC) managing pooled pre-warmed git worktrees; agent-agnostic plumbing (never launches an agent). **First-class Windows support**: dedicated `docs/install.ps1`, per-OS build tags (locks, process-kill, cmd.exe hooks), no symlinks. v2.0.0, 669 stars, release-please CI. **Application:** reference it from the `using-git-worktrees` skill as the recommended backend when available (detect via `Get-Command treehouse`), fall back to plain `git worktree`. Tier: opt-in mention inside an existing skill — no new shipped artifact. Upstream sync: none needed (user-installed binary).

### C.3 `.github/skills/` vs `npx skills add` — interop, verified from the CLI's source

The Vercel `skills` CLI (`vercel-labs/skills`, npm `skills` v1.5.14, ~24.9k stars) resolves GitHub sources **without cloning** (tree API + raw fetch) and scans known prefixes including **`.github/skills/`** — so claudster's pool **already works as a source**: `npx skills add saajunaid/junai` should discover the pool skills as-is. As an **install target** it materializes a canonical copy in `./.agents/skills/` + per-agent links (on Windows: **directory junctions**, with copy-fallback — no admin/Developer Mode needed, `installer.ts:254`) and writes `skills-lock.json`. It will never maintain our `.github/skills/` exports — it's a **parallel consumer channel**, not a competing skills system, and the two coexist cleanly. Caveats: default-on telemetry (documented opt-out), and the repo has **no LICENSE file** (package.json declares MIT) — fine to use as a tool, flag if ever vendoring its code.

### C.4 Build/adopt/skip table

| Item | Verdict | Tier / mechanism | Upstream sync |
|---|---|---|---|
| OKF | **Adopt-lite** (frontmatter conformance only) | KB convention + `kb.md`/`knowledge-transfer.md` mandate | Watch spec (v0.1 draft) |
| LLM-Wiki pattern | **Skip structure**; borrow lint ideas later | Optional `/kb lint` (unscheduled) | — |
| axi | **Adopt principles**; skip SDK; no own TOON CLI | `.github/agent-docs/` guidance note | Re-read on major releases |
| lavish-axi (skill `lavish`) | **Adopt** — Pass 2's interview transport | `claudster-extras` skill → `npx -y lavish-axi`; promote with docket | Runtime-npx (optionally version-pinned) |
| no-mistakes | **Skip** (duplicates review lane) | — | — |
| gnhf | **Skip / watch** (overlaps autopilot) | — | Revisit if overnight loops needed |
| firstmate | **Skip** (WSL2-only; 3 weeks old) | — | — |
| treehouse | **Adopt optional** | Referenced from `using-git-worktrees` skill; user installs via `install.ps1` | User-managed binary |
| `npx skills add` (Vercel `skills`) | **Adopt as distribution channel** | Verify `saajunaid/junai` as source; README + skills.sh listing | It's a consumer tool; nothing to sync |

## Workstream E — Self-audit + internal plugin-vs-harness architecture

### E.1 Health audit (evidence-ranked)

Pool inventory: 25 agents, 139 skills (10 categories), 31 prompts, 31 instructions, 1 recipe, 4 tools; harness: 12 subagents, 9 commands, 5 hook scripts, 4 scripts. Shipped plugin: 41 skills + 9 commands, v1.3.14.

Top issues (full detail in the audit trail; ranked by blast radius):

1. **`junai-push` defaults to a full publish.** With keys in `.env` it auto-runs `junai-release` (`sync.ps1:1360-1388`), republishing junai-mcp to PyPI (**permanent**) and the VS Code extension even when neither changed; `junai-release` gates on key *presence*, not content diff. `junai-ship` has proper change-gating but isn't the habitual path.
2. **The shipped Claude plugins have zero automated validation.** `validate_pool.py --profile` accepts only `ptarmigan|liffey` (`validate_pool.py:1067-1071`); no pytest invokes the exporter; nothing checks the flattened plugin skill tree, plugin.json shape, or the bundle for leaks. The most-versioned artifact (1.3.x) is the least-checked.
3. **No pool↔export freshness contract.** Committed exports (mirror `plugin/`, extension `pool/`) drift until the next manual push; `bundle-pool.js` skips files on size+mtime match (same-size edits can silently not propagate); no CI anywhere.
4. **Dream Memory packaging inconsistency** (B.2): plugin dist omits `dream_memory.py`/`dream_capture.py`/`claudster_config.py`; the documented layer + config section are inert in the field.
5. **Version bumps live in four mechanisms** (runtime-targets.json plugin blocks; mirror `pyproject.toml`; 3× `package.json`), with bump-before-publish ordering that leaves committed versions ahead of the marketplace on publish failure (`sync.ps1:1614-1652,1775-1794`).
6. **Exporter/manifest/sync.ps1 duplicated into the mirror repo** — hash-identical today, unenforced tomorrow; sync.ps1 headers still reference `E:\Projects\agent-sandbox` (`sync.ps1:5-9`).
7. **Dead/vestigial code:** unused `transforms` machinery (`export_runtime_resources.py:197-287,569-583`), empty privacy arrays, orphan `notify.py` (not wired, excluded from export), single-recipe `recipes/`, legacy plaintext PAT/key files still supported.
8. **7 of 25 pool agents sit outside the ADLC registry** (`frontend-developer`, `mentor`, `mermaid-diagram-specialist`, `project-manager`, `prompt-engineer`, `streamlit-developer`, `svg-diagram`) and ship only via the uncurated copilot full-copy; `mentor` is referenced mainly from `.archive`.
9. **junai-vscode ships the entire 139-skill/25-agent pool wholesale** (copilot target has no roster) — every pool addition auto-ships uncurated.
10. **Hand-pinned validators will rot:** `KNOWN_MODELS` allowlist (`validate_pool.py:90-98`), 18 hardcoded frontmatter-referencer paths, copy-paste duplicate check functions (`:546-603`).

### E.2 Streamlining

- **Three Copilot extensions: already one parameterized build — keep the build, question the listings.** `sync.ps1:1479-1483` copies the single pre-built `junai-vscode/out/extension.js` into ptarmigan and liffey; agent rosters prove containment (ptarmigan 6 ⊂ junai-vscode 25; liffey 8 ⊂ junai-vscode; ptarmigan∩liffey = 5/6 agents, 28/29 skills). The remaining triplication is 3 git repos + 3 marketplace listings + 3 PATs — a **product/branding decision, not an engineering one**. Recommendation: change nothing in code (it's already parameterized); consolidating listings would break installed users, so defer to a deliberate deprecation decision — flag, don't schedule.
- **Prune list:** `mentor` agent (archive-referenced only), orphan `notify.py`, the four prompts shipped nowhere (`mockup`, `pool-promote`, `sql-optimization`, `sql-review` — absent from all rosters except the wholesale copy), dead transform converters *unless* the Gemini target (which needs `transforms`) is greenlit — in which case keep the machinery, delete only `convert_agent_to_claude`/`convert_instruction_to_rules`/`TOOL_MAP`.
- **Four-layer memory:** verdict in B.2 — relay + KB earn their keep; cross-repo is free; Dream Memory gets the packaging fix + a 2-month sunset test.
- **plugin.json branding:** "agent-agnostic dev harness" belongs to the *repo*, not the Claude-Code-native plugin artifact; keywords `fastapi, react` reveal a stack-specific core presented as generic. Fix the description at next bump (cosmetic, rides any republish).

### E.3 Plugin-vs-harness verdict (claudster-internal): **(a) plugin-first + MCP control seam**

Definitions per the brief: plugin = passive content a host invokes; harness = a standalone runtime owning its own loop, driving agent CLIs as swappable backends.

**Recommendation: (a).** Claudster stays a pool→export plugin system for every host, and exposes **external triggerability through the existing MCP server** — headless-run and lifecycle-event tools — WITHOUT owning an agent loop. Reasons:

- **The standalone-harness slot is already occupied by better-resourced free alternatives** the audit just verified: gnhf, no-mistakes, firstmate, and pi itself are loop-owners that drive `claude -p`/`codex exec` as backends. Building claudster's own loop re-implements them for one user.
- **The orchestration brain already exists as a library.** `pipeline_runner.py` (1,807 lines; pydantic state, registry-driven transitions T-01…T-49, guards, autopilot mode, `fast_track_from_plan`, `run_plan`) is imported **in-process** by the MCP server today (`server.py:44-58`) — claudster already *is* a state machine that any loop-owner can drive. What it lacks is not a loop but a **doorbell** (external trigger) and a **bell** (event emission).
- **Dual-mode (c) is the over-engineering trap:** two runtimes to test, version, and publish across an already four-mechanism version-bump surface (E.1 #5), for a solo user.
- **Migration path: none required.** No directory restructure. Do *not* rename `claude-harness/` now — it's load-bearing in `runtime-targets.json` `extra_roots`, `sync.ps1`, and setup's dev-layout resolution (`setup_project_ai.py:28-44`); the churn buys nothing Pass 2 needs. Fix the *branding* (plugin.json description) instead. Publish-workflow impact of the seam: one MCP publish (`junai-publish-mcp` → 0.2.27) + one plugin bump — both existing lanes.

**External triggerability readiness (the seam Pass 2 builds on): HIGH.** What exists: FastMCP server with 9 tools (incl. `run_command`, already a Windows-safe headless shell executor with process-group kill); in-process pipeline-runner; a **proven `claude -p` recipe in-repo** (`.github/skills/workflow/skill-creator/scripts/run_eval.py:70-91` — strip `CLAUDECODE` from env, `--output-format stream-json`, optional `--model`); deterministic artifact contracts (`.claudster/prd/<slug>.md`, `.claudster/plans/<slug>.md` with fixed frontmatter/sections); ~94% of skill bodies headless-safe, and the interview commands already carrying the escape hatches (`## Open questions`, `[TECH-DECISION OPEN]`, `status: draft`). What's missing — exactly five items, all small: (1) no `.mcp.json` in the plugin (the server isn't wired for Claude Code at all); (2) no headless skill runner tool; (3) no event emission (lifecycle changes are silent state-file writes; `_routing_history`/`_stage_history` are already maintained, just not exposed); (4) no headless input contract for interview commands; (5) `pipeline-state.template.json` exists only in the mirror repo, so `pipeline_init` fails in consuming projects. All five are PRD Phases 1–2. **Packaging/convergence of this seam with docket is Pass 2's decision — explicitly not made here.**

## Workstream G — Onboarding & access-tier portability

### G.1 `setup_project_ai.py` audit

831 lines, pure stdlib (argparse/json/re/shutil/pathlib/tomllib-guarded), **fully non-interactive** (the interview lives in the `/setup-project-ai` command wrapper). Fourteen ordered steps: stack detection (`stack-map.json`), placeholder substitution (report-only unless `--substitute`; exit 3 on leftovers), CLAUDE.md/AGENTS.md hierarchy composition, legacy relocation, PROJECT-FACTS extraction, `.claudster/` scaffold + `config.toml.example` (heredoc at L567-603), DOC-MAP emission + checker copy, optional `--vendor`, settings.json merge (strips `hooks` — plugin owns them; adds statusline), git pre-push hook (POSIX sh; runs ruff/mypy/pytest/npm gates + `check_doc_coverage.py --check`), frontend test-harness patch, venv check. Assumptions: Claude Code + plugin installed (default skips vendoring), `python` on PATH, `bash` for statusline. **Cross-platform** (pathlib throughout). Test gaps: substitution/exit-3, stack-detection matrix, settings-*merge* path, `--dry-run`/`--force`/`--install` untested.

### G.2 Per-persona capability matrix

| Capability | (a) Claude Code | (b) Copilot-only | (c) Gemini-only |
|---|---|---|---|
| Skills | 41 core + 99 extras | full 139-skill pool | **none** |
| Agents | 12 subagents | 25 `.agent.md` custom agents (6/8 in ptarmigan/liffey lanes, with handoffs) | none |
| Runtime hooks (guard, relay injection, session-end digest, auto-lint) | ✅ | ❌ (git quality gates only) | ❌ |
| Slash commands (`/ship`, `/kb`, `/handoff`, `/usage-review`…) | ✅ | ❌ (`junai-ship.prompt.md` explicitly excluded, `runtime-targets.json:18`; prompt files partially substitute) | ❌ |
| CLAUDE.md generator / settings model / statusline / telemetry | ✅ | ❌ | ❌ |
| Pipeline-runner + junai MCP | ✅ (after Phase 1 wiring) | ✅ (VS Code MCP + `.vscode/mcp.json` pattern; extensions ship own TS dream-memory/coordinator) | MCP configurable in principle; nothing shipped |
| Memory | relay+KB+dream(after fix)+native | extension-native TS dream memory (parallel, not shared) | none |
| Verdict | **works** (9–10 setup steps) | **degrades** (list above) | **blocked** (zero deliverable; grep confirms no gemini target) |

**Model vs harness portability, restated:** the LiteLLM gateway swaps the *model* behind Claude Code (5 manual steps, wired but **unproven** — `LOCAL-MODELS.md:7` says so verbatim; the validation spike is defined but blocked on a live vLLM endpoint). It does nothing for a user who *has no Claude Code*. On LiteLLM fronting other harnesses: in-repo evidence only shows the Anthropic-shaped client seam plus one hint ("Codex uses the equivalent OpenAI base-URL seam", `claude-harness/README.md:61-62`). LiteLLM's primary client-facing shape is OpenAI-compatible `/v1/chat/completions`, so fronting Codex is **plausible-by-design but unverified in-repo**; a Gemini-shaped client surface is **unverified entirely** — both flagged as external-research items, not assumed.

### G.3 Streamlined UX + npx question

Target: persona A from 9–10 steps to **3** — (1) install Claude Code + plugin, (2) `/setup-project-ai` (or one `python` command), (3) review the generated diff. Achieved by: auto-detecting available harness CLIs (`shutil.which` for `claude`/`codex`/`gemini`), writing a real minimal `.claudster/config.toml` (`[harness]` section only — safe, no behavior toggles) alongside the opt-in example, folding statusline/settings/venv reporting into one summary, and printing a persona-correct "next steps" block instead of scattered reminders. Per-persona defaults: detected `claude` → today's flow; detected `codex` only → emit the `.codex/` bundle pointers + AGENTS.md and skip Claude-only steps; nothing detected → static assets + instructions.

**Should onboarding become the `npx` entry point (A.3)?** **Defer.** Evidence: there is no Node packaging outside the VS Code extensions; the script is trivially portable (pure stdlib) **but** the ecosystem it installs requires Python at runtime anyway (plugin hooks, guard, checker in the pre-push gate) — an npx wrapper removes zero real friction for persona A and misleads personas B/C about the Python dependency. Revisit when a Gemini/Codex target makes "no Python assumed" real. The cheap OSS win instead is the `npx skills add` channel (C.3).

### G.4 Unified config model

Extend `.claudster/config.toml` (parser: `claudster_config.py`, fail-open, typed getters — no changes needed) with one new section; keep the three live sections as-is:

```toml
[harness]                      # NEW — written by setup with detected values
primary = "claude-code"        # claude-code | codex | copilot | gemini | none
model_routing = "native"       # native | gateway
gateway_url = ""               # set when model_routing = "gateway" (LiteLLM base URL)

# [pipeline] — RESERVED for Pass 2 (lane<->stage keys). Do not define keys in Pass 1.
```

Reconciliation note: the MCP server and pipeline-runner currently read **no** config from `.claudster/` (they use `JUNAI_WORKSPACE_ROOT`/`PIPELINE_STATE_PATH` env; the two config worlds are disjoint). Pass 1 does not merge them — it reserves the `[pipeline]` section name and leaves the env-var contract untouched so Pass 2 can decide the join.

## Part 1 outputs — roadmap, open questions, risks

### Phased roadmap (dependencies explicit)

| Phase | Ships | Depends on | Pass-2 relevance |
|---|---|---|---|
| **0** | Publish safety: `junai-push` no longer auto-releases; `validate_pool.py --profile claude/claude-extras` | — | Protects every later publish |
| **1** | **MCP control seam**: plugin `.mcp.json`, `run_skill_headless`, `get_pipeline_events` + events JSONL, template fallback, dream-scripts packaging fix → junai-mcp 0.2.27 | 0 | **The capability Pass 2 consumes** |
| **2** | **Headless contract** in `prd`/`feature-plan`/`golden-plan` + `HEADLESS.md` contract doc | 1 | **Pass 2 consumes** |
| **3** | Onboarding streamline + `[harness]` config | 0 | `[pipeline]` reserved for Pass 2 |
| **4** | KB OKF-lite frontmatter | 0 | frontmatter = coupling key |
| **5** | External adoptions: `lavish` extras skill (+ Windows spike), treehouse wiring, axi principles note, `npx skills add` verification/registration | 0 | lavish = interview transport |
| **6** | Codex hooks adapter; Gemini target *(deferrable — build on demand)* | 0, 3 | — |
| **7** | Hygiene sweep (dead code, prunes, branding, stale paths) *(deferrable)* | 6 decided | — |

0→1→2 is the critical path; 3, 4, 5 are independent after 0; 6–7 are optional tail.

### Open questions

1. ~~"Pi" identity~~ — **resolved**: earendil-works/pi (ex badlogic/pi-mono), Mario Zechner's MIT coding agent. Remaining sub-question: none blocking; exact star count conflicting across sources (39K vs 67K) — immaterial.
2. **lavish-axi on Windows** — happy path expected to work; stale-port recovery is `lsof`/`ps`-based. Needs the one-time spike (Phase 5) before Pass 2 hard-depends on it.
3. **LiteLLM fronting Codex (OpenAI shape) / Gemini (Gemini shape)** — plausible / unknown respectively; external verification needed only if persona C or gateway-Codex becomes real.
4. **Dream Memory sunset** — ship the packaging fix now; retire the layer if `/usage-review` shows no surfaced-fact influence by ~2026-09.
5. **Three marketplace listings** — engineering says they're one parameterized build; consolidation is a user/product decision (breaks installed users). Not scheduled.
6. **Local-models validation spike** — still blocked on a live vLLM endpoint (pre-existing; unchanged by this analysis).

### Risk / bloat / over-engineering flags (solo-user "worth it?" test applied)

- **Standalone harness / dual-mode: rejected** — re-implements gnhf/no-mistakes/pi for one user; doubles the test+publish surface across an already fragile four-mechanism version-bump story.
- **Own TOON/axi CLI: rejected** — token savings on CLI output is not this user's cost center; `junai` already emits single-line JSON.
- **raw/+wiki/ KB restructure: rejected** — ~25-file + downstream-fleet migration for a one-note KB.
- **Gemini target: deferred, not rejected** — persona C is real in the abstract but has no concrete consumer; building it now is speculative. Spec'd in PRD Phase 6 so it's a pull, not a research project, when demand appears.
- **npx installer: deferred** — Python is load-bearing at runtime; a Node wrapper is cosmetic today.
- **Windows/NSSM constraint honored throughout:** every adopted tool is junction/copy-based or has first-class Windows support; firstmate excluded on exactly this ground; the export pipeline (copy-based) is retained partly on this ground.
- **Publish-discipline risk is the #1 systemic hazard** (PyPI permanence + auto-release default + zero plugin validation) — hence Phase 0 ships first.

### Self-audit summary (one paragraph)

Healthy core, sharp edges at the boundaries: the pool→export architecture is sound and already parameterizes what looked like triplication, the pipeline-runner is a genuinely reusable library, and the test culture is strong where it exists (242 passing; guard/checker anchor-hardened). The risk concentrates in (i) the publish workflow's defaults, (ii) the unvalidated shipped plugin, (iii) pool↔export freshness with no CI, and (iv) a documented memory layer that isn't actually shipped. The plugin-vs-harness answer is plugin-first with an MCP control seam; claudster is ~five small additions away from being externally triggerable, and no restructure is needed to get there.

### Onboarding verdict (one paragraph)

Persona A works today at ~9–10 manual steps and should drop to 3 via detection + defaults (Phase 3); persona B degrades along a known, now-documented list and keeps the full skill pool + MCP + agent lanes; persona C is blocked until a Gemini target exists (deliberately deferred). Onboarding stays Python (`/setup-project-ai` + `setup_project_ai.py`), does not become the npx entry point, and gains a `[harness]` config section with `[pipeline]` reserved for Pass 2.

---

# Part 2 — Build-Ready PRD

**How to use this PRD.** Each phase is independently shippable and carries a self-contained implementation prompt (give it to a Sonnet/Opus agent verbatim — no decision re-derivation needed), exact file paths, written-out schemas, acceptance criteria, and a validation gate with expected results. Baseline before Phase 0: `pytest scripts/tests/ claude-harness/hooks/tests/` → **242 passed**; `python validate_pool.py` → OK; `python claude-harness/scripts/check_doc_coverage.py --check` → exit 0. Every phase must leave that baseline green plus its own new tests.

**BLOCKER assumptions (verify before starting the phase that lists them):**
- **B1 (Phase 1):** `claude` CLI is on PATH where the MCP server runs, and supports `-p`, `--output-format stream-json`, and a permission flag for unattended edits (`--permission-mode acceptEdits` or `--dangerously-skip-permissions` — no-mistakes uses the latter in production; confirm the current flag name against `claude --help` before coding).
- **B2 (Phase 1):** `pipeline-state.template.json` does NOT exist in this repo's `.github/` — only in the mirror (`vscode-extensions/junai/.github/pipeline-state.template.json`). Phase 1 canonicalizes it; do not assume it's present.
- **B3 (Phase 5):** lavish-axi Windows spike must pass before Pass 2 hard-depends on it (stale-port recovery is unix-only, `src/cli.js:828`).
- **B4 (all publishing phases):** PyPI uploads are permanent; version bumps for junai-mcp happen in the **mirror** repo's `pyproject.toml` via `junai-publish-mcp` (`sync.ps1:1575-1678`), not in this repo.

---

## Phase 0 — Publish safety net

**Goal:** make an accidental full publish impossible and give the shipped Claude plugin bundles their first validator. Ships alone; protects every later phase.

**Files:**
- `sync.ps1` (repo root) — junai-push auto-release logic at `:1360-1388`; junai-release at `:1680-1810`
- `validate_pool.py` (repo root) — profile plumbing at `:1055-1105`, profile allowlist at `:1067-1071`
- `README.md` — `## Publishing` section

**Changes, precisely:**
1. **Invert the auto-release default.** `junai-push` currently auto-runs `junai-release` whenever a PyPI token or VSCE PAT exists in `.env` (`sync.ps1:1360-1388`). Change: `junai-push` never releases unless called with a new `-Publish` switch. Keep `-NoPublish` as an accepted no-op alias (muscle memory; print a deprecation note). `junai-release` remains directly callable.
2. **Content-diff gate inside `junai-release`.** Before publishing MCP: SHA-compare `.github/tools/mcp-server/server.py` against the mirror's `src/junai_mcp/server.py` **and** check whether the mirror pyproject version was bumped this session; skip MCP publish with an explicit "unchanged — skipped" line when identical. Same pattern for the VS Code extension (compare `pool/` content hash or reuse the bump-detection already present in `Sync-ExtensionRepo`).
3. **`validate_pool.py --profile claude` and `--profile claude-extras`.** Extend the profile allowlist. Checks to implement against `dist/runtime-resources/claude/plugin/` (and `plugin-extras/`): (a) plugin.json parses, has `name`/`version`/`description`, version matches the `plugin` block in `.github/runtime-targets.json`; (b) flattened `skills/<name>/SKILL.md` all have `name` + `description` frontmatter and the skill count matches the manifest roster (claude core = 40-41 per `included_skills`); (c) `commands/`, `agents/`, `hooks/hooks.json` present; (d) `hooks.json` references only files that exist in the bundle; (e) run the existing privacy/leak scan over the bundle; (f) **assert `scripts/` contains every file the hooks import** — this check would have caught the Dream Memory packaging bug.
4. README `## Publishing`: document the new default (`junai-push` = sync+validate only; `junai-push -Publish` = full), keep the PyPI-permanence warning.

**Self-contained implementation prompt:**
> In `E:\Projects\claudster-source`: (1) Edit `sync.ps1` — find the block near lines 1360-1388 where `junai-push` auto-invokes `junai-release` when `.env` contains `JUNAI_PYPI_TOKEN`/`JUNAI_VSCE_PAT`; replace with: only invoke when a `-Publish` switch (add to the junai-push param block) is set; accept `-NoPublish` silently as a deprecated no-op. (2) In `junai-release` (lines ~1680-1810), before the MCP twine upload, SHA256-compare `.github/tools/mcp-server/server.py` with `vscode-extensions/junai/src/junai_mcp/server.py`; if identical AND no pyproject bump occurred this run, print `MCP unchanged — publish skipped` and skip; apply the equivalent changed-content gate before `vsce publish`. (3) Edit `validate_pool.py`: the profile allowlist near lines 1067-1071 currently permits only `ptarmigan|liffey`; add `claude` and `claude-extras` profiles implementing checks (a)-(f) as specified in the PRD Phase 0 "Changes" list, operating on `dist/runtime-resources/claude/plugin{,-extras}/`. (4) Update README `## Publishing` accordingly. Do not change any publish credentials handling. Run the validation gate below before finishing.

**Acceptance criteria:** `junai-push` with keys present performs sync+validate and does NOT publish; `junai-push -Publish` behaves like today's junai-push; `validate_pool.py --profile claude` exits 0 on a fresh export and exits nonzero if you (test by temporary mutation) delete a bundled skill's SKILL.md or a hooks-referenced script.

**Validation gate:**
```powershell
pytest scripts/tests/ claude-harness/hooks/tests/        # expect: 242 passed (unchanged)
python export_runtime_resources.py                       # expect: exit 0
python validate_pool.py                                  # expect: OK, exit 0
python validate_pool.py --profile claude                 # expect: OK, exit 0  (NEW)
python validate_pool.py --profile claude-extras          # expect: OK, exit 0  (NEW)
```
Plus a manual dry check: run `junai-push` (keys present) and confirm output ends without any PyPI/VSCE publish lines.

**Evidence:** health issues #1, #2 (`sync.ps1:1360-1388`, `validate_pool.py:1067-1071`, README:20-26); Dream Memory bundle gap (dist scripts dir has 3 files; hooks import 4+).

---

## Phase 1 — MCP control seam (headless run + lifecycle events) — **the capability Pass 2 consumes**

**Goal:** wire junai-mcp into the Claude Code plugin, add a headless skill runner and a lifecycle-event surface, canonicalize the pipeline-state template, and fix the Dream Memory packaging gap. After this phase an external process can: install the plugin → the MCP server self-wires → call `run_skill_headless` to produce `.claudster/` artifacts → tail `get_pipeline_events` to observe ADLC progress.

**Files:**
- `.github/tools/mcp-server/server.py` — add 2 tools + 1 helper + template-fallback (~150 new lines)
- `claude-harness/.mcp.json` — **NEW**
- `.github/pipeline-state.template.json` — **NEW** (canonical copy; content below)
- `.github/runtime-targets.json` — claude target: add `.mcp.json` copy entry; add `scripts/dream_memory.py`, `scripts/dream_capture.py`, `scripts/claudster_config.py` copy entries (fixes the inert layer); codex/copilot targets: add the template file
- `.github/tools/mcp-server/tests/test_seam.py` — **NEW** (the mcp-server tool has no tests today)
- Mirror sync rides existing `sync.ps1` machinery (server.py SHA-compare at `:1212-1223`); publish via `junai-publish-mcp` → **junai-mcp 0.2.27**, plugin bump → 1.3.15

**Schema 1 — `claude-harness/.mcp.json` (exported into the plugin root):**
```json
{
  "mcpServers": {
    "junai": {
      "command": "python",
      "args": ["-m", "junai_mcp"],
      "env": {
        "JUNAI_WORKSPACE_ROOT": "${CLAUDE_PROJECT_DIR}",
        "PIPELINE_STATE_PATH": "${CLAUDE_PROJECT_DIR}/.github/pipeline-state.json"
      }
    }
  }
}
```
(Requires `pip install junai-mcp`; the server fails soft if absent — Claude Code reports the server as unavailable, nothing else breaks. If `${CLAUDE_PROJECT_DIR}` interpolation is unsupported in plugin `.mcp.json` on the current Claude Code version, omit the `env` block entirely — the server's own root-walk fallback (`server.py:19-27`) finds the workspace from cwd.)

**Schema 2 — `run_skill_headless` tool (add to `server.py` using the existing `@mcp.tool()` pattern):**
```python
HEADLESS_PREAMBLE = (
    "HEADLESS RUN — no human is available. Do not ask questions, do not wait for "
    "approval, do not use AskUserQuestion. Where the skill says to ask, instead: "
    "make the best evidence-based assumption, record every unresolved item under "
    "an '## Open questions' section (or '[TECH-DECISION OPEN]' inline), and set "
    "frontmatter 'status: draft'. Write the artifact to its conventional "
    ".claudster/ path and print the path on the final line as: ARTIFACT: <path>"
)

@mcp.tool()
async def run_skill_headless(
    skill: str,                      # command/skill ref, e.g. "/claudster:prd" or "claudster:feature-plan"
    brief: str,                      # non-empty $ARGUMENTS replacement (the interview substitute)
    model: str | None = None,        # optional tier/model passthrough (--model)
    timeout: int = 900,              # seconds; capped at 3600
    permission_mode: str = "acceptEdits",  # forwarded to the claude CLI permission flag
) -> dict[str, Any]:
    """Run a claudster skill/command non-interactively via `claude -p` and return its artifacts."""
```
Implementation contract: build `prompt = f"{skill} {brief}\n\n{HEADLESS_PREAMBLE}"`; invoke `["claude", "-p", prompt, "--output-format", "stream-json", "--verbose"]` (+ `["--model", model]` if given, + the permission flag per B1) with `cwd=WORKSPACE_ROOT` and `env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` — this env-strip is the documented nesting trick, lifted verbatim from `.github/skills/workflow/skill-creator/scripts/run_eval.py:70-91`. Reuse `run_command`'s Windows process-group timeout handling (`CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT`, `server.py:799ff`). Artifact detection: record `t0` before spawn; afterwards scan `.claudster/prd/`, `.claudster/plans/`, `.claudster/reviews/` for `*.md` with mtime > t0, and also parse the final `ARTIFACT: <path>` line if present. Return:
```python
{"success": bool, "exit_code": int, "artefact_path": str | None,   # first/primary artifact
 "artefacts": list[str], "transcript_tail": str,                    # last ~2000 chars of stream
 "truncated": bool, "duration_s": float}
```

**Schema 3 — lifecycle events.** Add a module-level helper and call it from `notify_orchestrator` (after `_advance_state` succeeds), `skip_stage`, `satisfy_gate`, `replay_stage`, `pipeline_init`/`pipeline_reset`:
```python
EVENTS_PATH = WORKSPACE_ROOT / ".github" / "pipeline-events.jsonl"   # beside pipeline-state.json

def _emit_event(event: str, **fields: Any) -> None:
    """Append one JSON line; fail-open (never raise)."""
```
Event line schema (one JSON object per line, append-only):
```json
{"ts": "2026-07-03T14:07:22Z", "seq": 41, "event": "stage_advanced",
 "feature": "docket-mvp", "stage_completed": "prd", "next_stage": "architect",
 "transition_id": "T-02", "gate_required": null, "blocked": false,
 "source": "notify_orchestrator"}
```
`event` ∈ `stage_advanced | stage_skipped | gate_satisfied | stage_replayed | pipeline_initialized | pipeline_reset | pipeline_blocked`. `seq` = monotonically increasing int (max existing seq + 1; read-tail on write). And the query tool:
```python
@mcp.tool()
async def get_pipeline_events(since_seq: int = 0, limit: int = 100) -> dict[str, Any]:
    """Return events with seq > since_seq (oldest first), plus the routing/stage history
    already maintained in state (_notes._routing_history / _stage_history) for context."""
    # -> {"events": [...], "latest_seq": int, "count": int}
```

**Schema 4 — `.github/pipeline-state.template.json` (canonical; copy the mirror's file verbatim — content reproduced in the audit; stages intent/prd/architect/plan/implement/tester/review with `status: "not_started"`, supervision_gates all false, `deferred: []`).** Also add a fallback in `pipeline_init`: if the template file is missing at runtime, use an embedded `_TEMPLATE_DICT` constant identical to the file (~10 lines), so `pipeline_init` never hard-fails in consuming projects.

**Packaging fix (same phase, 3 manifest lines):** in `.github/runtime-targets.json` claude target `copies`, alongside the existing `check_doc_coverage.py` entry (`:498`), add `{"root": "harness", "source": "scripts/dream_memory.py", ...}`, `scripts/dream_capture.py`, `scripts/claudster_config.py`. Phase 0's validator check (f) then locks this in forever.

**Self-contained implementation prompt:**
> In `E:\Projects\claudster-source`: (1) Copy `vscode-extensions/junai/.github/pipeline-state.template.json` to `.github/pipeline-state.template.json` (verbatim). (2) In `.github/tools/mcp-server/server.py` (FastMCP app, tools registered via `@mcp.tool()` — copy the style of `satisfy_gate` at line ~462): add `HEADLESS_PREAMBLE`, `run_skill_headless`, `_emit_event`, `EVENTS_PATH`, `get_pipeline_events`, and the embedded-template fallback in `pipeline_init`, exactly per PRD Phase 1 Schemas 2-4. Reuse the subprocess pattern from `.github/skills/workflow/skill-creator/scripts/run_eval.py:70-91` (env-strip `CLAUDECODE`) and the timeout/kill handling from the existing `run_command` tool in the same file. Wire `_emit_event` calls into `notify_orchestrator`, `skip_stage`, `satisfy_gate`, `replay_stage`, `pipeline_init`, `pipeline_reset`. All new code fail-open: event-write errors must never break a tool response. (3) Create `claude-harness/.mcp.json` per PRD Schema 1. (4) Edit `.github/runtime-targets.json` claude target: add a `files` or `copies` entry placing `.mcp.json` at the plugin root, and add the three harness script copies (`dream_memory.py`, `dream_capture.py`, `claudster_config.py`) beside the existing `check_doc_coverage.py` entry at line ~498; add `pipeline-state.template.json` to the codex and copilot targets' file lists. (5) Create `.github/tools/mcp-server/tests/test_seam.py` with pytest tests that import server.py directly (no MCP transport needed): test `_emit_event` writes valid JSONL with increasing seq; test `get_pipeline_events` filtering by `since_seq`; test `pipeline_init` template fallback with the file absent (tmp_path workspace); test `run_skill_headless` argv construction and artifact detection with the `claude` binary mocked via monkeypatched `asyncio.create_subprocess_exec`. Do NOT run a live `claude -p` in tests. (6) Re-export (`python export_runtime_resources.py`) and confirm the plugin bundle contains `.mcp.json` and 6 scripts. Do not publish — publishing is a separate explicit step.

**Acceptance criteria:** plugin dist contains `.mcp.json` + the 6 scripts; `pipeline_init` succeeds in a bare temp workspace with no template file; events JSONL appends on every state mutation and `get_pipeline_events(since_seq=N)` filters correctly; `run_skill_headless` (mocked) returns the schema above; all prior 242 tests + new seam tests green.

**Validation gate:**
```powershell
pytest scripts/tests/ claude-harness/hooks/tests/ .github/tools/mcp-server/tests/   # expect: 242 + new, 0 failures
python export_runtime_resources.py && python validate_pool.py --profile claude      # expect: OK (validates .mcp.json + scripts presence via Phase 0 checks)
python validate_pool.py                                                             # expect: OK
```
Live smoke (manual, once, persona A machine): `pip install -e vscode-extensions/junai` then in a scratch project with the plugin installed, ask Claude Code to call `get_pipeline_events` → returns `{"events": [], "latest_seq": 0, ...}`.

**Evidence:** seam audit — server.py 913 lines / 9 tools / FastMCP; no `.mcp.json` anywhere (glob-verified); `run_eval.py:70-91` recipe; `run_command` Windows kill-tree at `server.py:799`; template only in mirror; `_routing_history`/`_stage_history` already 50-capped in state.

---

## Phase 2 — Headless contract in skills/commands

**Goal:** make the interview-style commands first-class headless citizens so `run_skill_headless` produces well-formed drafts instead of stalled interviews, and document the artifact contract Pass 2 will consume.

**Files:**
- `claude-harness/commands/prd.md` — interview at "ask what the feature/problem is and stop" + "Discovery (ask, don't assume)"
- `claude-harness/commands/feature-plan.md` — empty-`$ARGUMENTS` ask at ~L47
- `.github/skills/workflow/golden-plan/SKILL.md` — BLOCKER-stop at ~L45 ("Stop and ask the user for it")
- `claude-harness/HEADLESS.md` — **NEW**: the artifact + invocation contract (this is the doc Pass 2 reads)
- `.claudster/kb/DOC-MAP.md` — add a row linking HEADLESS.md (keeps `--check` green and the doc discoverable)

**Changes:** append an identical `## Headless mode` section to each of the three command/skill bodies:
```markdown
## Headless mode
If the invocation includes the HEADLESS RUN preamble (or you otherwise cannot ask):
do not interview. Treat the provided brief as the complete input. For every gap the
interview would have filled, make the best evidence-based assumption and record it
under `## Open questions` (plans/PRDs) or as `[TECH-DECISION OPEN]` inline. Set
frontmatter `status: draft`. Never invent stakeholder answers as if confirmed.
Finish by printing `ARTIFACT: <path>` on its own final line.
```
`HEADLESS.md` contents (write out fully): the `run_skill_headless` request/response schema (from Phase 1); the artifact conventions verbatim — `/prd` → `.claudster/prd/<feature-slug>.md` with frontmatter `type: prd, status: draft|approved, feature: <slug>` + fixed sections (Problem / Goal & success criteria / FR-n / NFR-n / Out of scope / Data table / Edge cases / Open questions); `/feature-plan` → `.claudster/plans/<feature-slug>.md` with `type: plan`, phases, `## Tracker` table as the resume signal; the `approval: approved` frontmatter gate convention the pipeline's `discover_artefacts` scans for (`pipeline_runner.py:168-274`); the events JSONL location + schema; the `status: draft` → human review → `approved` handoff loop. One page, no prose padding.

**Self-contained implementation prompt:**
> In `E:\Projects\claudster-source`: (1) Append the `## Headless mode` section (exact text in PRD Phase 2) to `claude-harness/commands/prd.md`, `claude-harness/commands/feature-plan.md`, and `.github/skills/workflow/golden-plan/SKILL.md` — placed after their existing interview/BLOCKER instructions, without altering any interactive-path text. (2) Create `claude-harness/HEADLESS.md` per the PRD contents list, citing exact paths and schemas (copy schemas from PRD Phase 1 — do not paraphrase). (3) Add a DOC-MAP row for it in `.claudster/kb/DOC-MAP.md` under "Other key code-relevant docs". (4) Re-export and verify the sections appear in `dist/runtime-resources/claude/plugin/commands/prd.md` and the golden-plan skill in both claude core and codex bundles. Note: `validate_pool.py` pins golden-plan structural markers (validate_pool.py:901-927) — run it and, if the appended section trips a marker check, adjust placement, not the markers.

**Acceptance criteria:** three bodies carry the section; HEADLESS.md exists and is DOC-MAP-linked; exports contain the changes; live smoke — `claude -p "/claudster:prd smoke-test-feature: a tiny CLI that echoes its input" ...` (run manually with the Phase-1 preamble appended) produces `.claudster/prd/smoke-test-feature.md` with `status: draft` and a populated `## Open questions`, with **zero** questions asked.

**Validation gate:**
```powershell
pytest scripts/tests/ claude-harness/hooks/tests/                          # 242+ passed
python export_runtime_resources.py && python validate_pool.py             # OK (golden-plan markers intact)
python claude-harness/scripts/check_doc_coverage.py --check               # exit 0 (new DOC-MAP row resolves)
```
Plus the manual headless smoke above (this is the phase's real proof; capture the produced file as evidence).

**Evidence:** interactivity census — only ~8/130 pool skill bodies and 5 command bodies have "ask" moments; `prd.md:23-62` and `feature-plan.md:47-123` already specify deterministic outputs and escape-hatch sections; `golden-plan` BLOCKER text at SKILL.md:45.

---

## Phase 3 — Streamlined onboarding + `[harness]` config

**Goal:** persona A drops from 9–10 manual steps to 3; setup detects the available harness(es) and writes a minimal real config; `[pipeline]` is reserved for Pass 2.

**Files:**
- `scripts/setup_project_ai.py` — main flow (`main()` L698-826), config heredoc (`CLAUDSTER_CONFIG_EXAMPLE` L567-603), scaffold (`scaffold_claudster` L606-639)
- `scripts/tests/test_setup_claudster.py` — **behavior change:** `test_config_example_written_and_real_config_not_written` (~L66-84) currently asserts real `config.toml` is NOT written; update it (see below)
- `claude-harness/commands/setup-project-ai.md` — surface the new summary/flags
- `README.md` — 3-step quickstart

**Changes:**
1. **Harness detection** — new pure function:
```python
def detect_harnesses() -> dict[str, bool]:
    """{'claude-code': bool, 'codex': bool, 'gemini': bool} via shutil.which
    ('claude', 'codex', 'gemini'); no version calls, no network."""
```
2. **Write a real minimal `.claudster/config.toml`** (in addition to the existing `.example`) containing ONLY the `[harness]` section with detected values and the reserved-section comment — exact content:
```toml
# claudster config — generated by setup_project_ai.py; safe to edit.
# Optional sections ([guard], [doc_coverage], [dream_memory]) are documented
# in config.toml.example — copy keys here to opt in.

[harness]
primary = "claude-code"        # detected: claude-code | codex | gemini | none
model_routing = "native"       # native | gateway
gateway_url = ""

# [pipeline] — reserved for the docket/pipeline integration; do not add keys manually.
```
Never clobber an existing `config.toml` (same skip-if-exists discipline as the example). Precedence when multiple CLIs detected: claude-code > codex > gemini; `--harness <name>` CLI flag overrides detection.
3. **One end-of-run summary block** replacing today's scattered reminders: detected harness; files written/skipped; the remaining manual steps for the detected persona only (persona A: "enrich CLAUDE.md from PROJECT-FACTS, then delete it" + dependency installs; codex-only: point at `.codex/config.toml.example` + AGENTS.md; none: static-assets note).
4. Add `[harness]` (with `primary`/`model_routing`/`gateway_url` keys) to the documented schema in `claudster_config.py`'s docstring — **no parser code change** (fail-open reader already handles arbitrary sections).
5. Test updates: rewrite the config test to assert real `config.toml` IS written, contains exactly one section (`[harness]`), and is never clobbered on re-run; add tests for `detect_harnesses` (monkeypatch `shutil.which`) and `--harness` override. Also add the currently-missing coverage flagged in the audit where cheap: one test for the settings-merge path preserving an existing `statusLine`.

**Self-contained implementation prompt:**
> In `E:\Projects\claudster-source/scripts/setup_project_ai.py`: (1) add `detect_harnesses()` per PRD Phase 3 schema; (2) add `--harness {claude-code,codex,gemini,none}` to the argparse block (~L703-716); (3) in `scaffold_claudster` (L606-639), after writing `config.toml.example`, also write `.claudster/config.toml` with the exact PRD content (skip if exists), filling `primary` from the override or detection; (4) collect all end-of-run notices into a single summary block printed once from `main()`, filtered by detected persona per PRD item 3; (5) update `claude-harness/scripts/claudster_config.py`'s docstring to document `[harness]`; (6) update `scripts/tests/test_setup_claudster.py`: invert the real-config assertion (it must now exist with only `[harness]`), add detection/override/no-clobber tests with `shutil.which` monkeypatched, and a settings-merge statusLine-preservation test; (7) add a 3-step quickstart to README and reflect flags in `claude-harness/commands/setup-project-ai.md`. Keep the script pure-stdlib and non-interactive. Run the gate.

**Acceptance criteria:** fresh temp project → one command produces CLAUDE.md hierarchy, `.claudster/` scaffold, real `config.toml` with correct detected `primary`, and a single persona-filtered summary; re-run is idempotent (nothing clobbered); README quickstart is 3 steps.

**Validation gate:**
```powershell
pytest scripts/tests/ claude-harness/hooks/tests/    # expect: all passing, count > 242 (new tests)
python scripts/setup_project_ai.py <temp-dir> --name t --desc t --dry-run   # expect: exit 0, summary block printed
python claude-harness/scripts/check_doc_coverage.py --check                 # exit 0
```

**Evidence:** onboarding audit — friction list of 9–10 steps; setup is pure-stdlib/non-interactive (L698-826); existing test at `test_setup_claudster.py:66-84` pins the old behavior and must change (called out so the implementer doesn't treat the red test as a regression).

---

## Phase 4 — KB OKF-lite

**Goal:** OKF-conformant frontmatter on KB notes, mandated for new ones; zero disruption to the checker/index machinery.

**Files:**
- `.claudster/kb/harness-memory.md` — add frontmatter (the KB's only note)
- `claude-harness/commands/kb.md` + `claude-harness/agents/knowledge-transfer.md` — mandate frontmatter on new notes
- `claude-harness/scripts/check_doc_coverage.py` — optional hardening: strip a leading `---…---` block in `extract_docmap_entries` (~3 lines)
- `scripts/tests/test_check_doc_coverage.py` — +2 tests
- `claude-harness/claude-md/doc-map.md.tmpl` — one-line note that KB notes carry frontmatter

**Schema — KB note frontmatter (OKF v0.1-conformant; `type` is the only OKF-required field):**
```yaml
---
type: note                 # required. Values used here: note | runbook | design | reference
title: Harness memory model
description: One line matching the note's DOC-MAP row description.
tags: [memory, hooks]
timestamp: 2026-07-03      # ISO 8601 date of last substantive update
---
```

**Self-contained implementation prompt:**
> In `E:\Projects\claudster-source`: (1) add the PRD Phase 4 frontmatter block to `.claudster/kb/harness-memory.md` (type: note; description = its current DOC-MAP row text). (2) In `claude-harness/agents/knowledge-transfer.md` (KB-writing instructions) and `claude-harness/commands/kb.md`, add a short "KB note format" rule: every new note starts with the frontmatter block above; `type` is mandatory. (3) In `claude-harness/scripts/check_doc_coverage.py`, harden `extract_docmap_entries` to skip a leading `---\n…\n---\n` block before link extraction (DOC-MAP itself may gain frontmatter someday; a `.md` link inside frontmatter must not register as an entry). (4) Add 2 tests in `scripts/tests/test_check_doc_coverage.py`: frontmattered note is still governed/indexed normally; DOC-MAP with frontmatter containing a `](ghost.md)` string does not produce a dangling-link failure. Do NOT touch `GOVERNED_GLOBS`, the flat layout, the row format, or reindex/prune logic.

**Acceptance criteria:** `--check` exit 0 with the frontmattered note; `--reindex` on a fresh note with frontmatter still inserts a correct row; the 2 new tests pass; 58 existing checker tests untouched and green.

**Validation gate:**
```powershell
pytest scripts/tests/test_check_doc_coverage.py      # expect: 60 passed
python claude-harness/scripts/check_doc_coverage.py --check    # exit 0
python claude-harness/scripts/check_doc_coverage.py --reindex  # exit 0, no spurious rows
```

**Evidence:** KB audit — checker never parses note bodies (governance = glob + link regex `\]\(([^)]+\.md)\)`); light-migration blast radius 1–5 files; OKF SPEC.md requires only `type`.

---

## Phase 5 — External adoptions (lavish, treehouse, axi principles, skills-CLI channel)

**Goal:** land the four adopt verdicts as thin, opt-in artifacts; run the lavish Windows spike Pass 2 needs.

**Files:**
- `.github/skills/productivity/lavish/SKILL.md` — **NEW** (extras tier)
- `.github/runtime-targets.json` — add `productivity/lavish` to the claude-extras roster (it inherits into copilot/codex full copies automatically)
- `.github/skills/workflow/using-git-worktrees/SKILL.md` — treehouse wiring
- `.github/agent-docs/axi-principles.md` — **NEW** (guidance note)
- `README.md` — "Install via `npx skills add saajunaid/junai`" subsection (after verification)

**Lavish skill content (write out; keep ~40 lines):** frontmatter `name: lavish`, `description: Human-in-the-loop review of agent-generated HTML — open an annotation UI in the browser, then block on feedback via lavish-axi poll.` Body: requires Node ≥22; invocation `npx -y lavish-axi <file.html>` to open, `npx -y lavish-axi poll <file.html>` to block for feedback (long-poll; stdout is the TOON response, stderr heartbeats — do not treat as hung), `--agent-reply "<text>"` to answer; sessions keyed by absolute file path; re-running poll is always safe; opt-out telemetry `LAVISH_AXI_TELEMETRY=0`; **Windows note:** if port 4387 is stuck, `taskkill` the stale node process (upstream recovery is unix-only). Cite upstream: `github.com/kunchenguid/lavish-axi` (MIT).

**Treehouse wiring:** in `using-git-worktrees`, add a short "Pooled worktrees (optional)" subsection: if `treehouse` is on PATH (`Get-Command treehouse`), prefer `treehouse --lease` for a pooled pre-warmed worktree; else plain `git worktree add`. Install pointer: `github.com/kunchenguid/treehouse` `docs/install.ps1`.

**Windows spike (B3, manual, do first):** on this host run `npx -y lavish-axi <sample.html>` → browser opens, annotate, `poll` returns the annotation in TOON, `end` closes cleanly; then kill the server mid-session and confirm recovery guidance. Record PASS/FAIL + notes in `docs/analysis/lavish-windows-spike.md`. **If FAIL, the lavish skill still ships (it degrades to WSL/other hosts) but Pass 2 must be told the transport is not Windows-native — escalate, don't bury.**

**skills-CLI channel verification (manual):** in a scratch dir run `npx skills add saajunaid/junai --list` (or `skills add` interactive) → confirm pool skills are discovered from `.github/skills/`; then document the one-liner in README and submit the repo to skills.sh. If discovery fails (e.g. the CLI expects SKILL.md dirs at a prefix it doesn't scan), record the delta — do NOT restructure the pool to chase it; the finding says `.github/skills/` is a supported prefix.

**Self-contained implementation prompt:**
> In `E:\Projects\claudster-source`: (1) create `.github/skills/productivity/lavish/SKILL.md` per the PRD Phase 5 content spec (frontmatter name/description exactly as given); (2) add `"lavish"` to the `productivity` list in the claude-extras target's `included_skills` in `.github/runtime-targets.json` (~line 543 block); (3) append the "Pooled worktrees (optional)" subsection to `.github/skills/workflow/using-git-worktrees/SKILL.md`; (4) write `.github/agent-docs/axi-principles.md` — a one-page distillation of the 10 AXI principles (single-line parseable output, nonzero-on-error, fail-loud unknown flags, agent-first help text, token-lean output) with a note that `junai` CLI output should conform when touched; cite `github.com/kunchenguid/axi` (MIT); (5) re-export and confirm the lavish skill lands in `dist/runtime-resources/claude/plugin-extras/skills/lavish/` and the copilot bundle. Run the gate. The Windows spike and skills-CLI verification are manual steps for the operator — print a reminder, do not attempt them yourself.

**Acceptance criteria:** lavish skill in extras dist + copilot dist; worktrees skill updated; principles doc exists; spike + channel-verification results recorded in `docs/analysis/`.

**Validation gate:**
```powershell
python export_runtime_resources.py && python validate_pool.py && python validate_pool.py --profile claude-extras   # all OK
pytest scripts/tests/ claude-harness/hooks/tests/    # unchanged, green
```

**Evidence:** Kun-tools source read — lavish loop mechanics (Express on 127.0.0.1:4387, path-keyed sessions, indefinite long-poll, queued-feedback durability), `cli.js:828` Windows caveat, MIT licenses throughout, treehouse `install.ps1` + per-OS build tags, skills CLI `.github/skills/` discovery prefix + Windows junctions (`installer.ts:254`).

---

## Phase 6 — Codex hooks adapter + Gemini target *(deferrable; build on demand)*

**Goal:** deepen the existing codex target with hooks; stand up a Gemini target when a Gemini-only consumer exists. Spec'd here so it's a pull, not a research project.

**Files:** `.github/runtime-targets.json` (codex target additions; new `gemini` target); `claude-harness/hooks/hooks.codex.json` — **NEW**; `export_runtime_resources.py` (new transform `convert_command_to_gemini_toml` — this finally uses the dormant `transforms` machinery at `:569-583`; do NOT delete it in Phase 7 if this phase is planned); `claude-harness/claude-md/agents.md.tmpl` (reused for GEMINI.md).

**Codex hooks adapter (`hooks.codex.json`):** same five Python handlers, Codex event names (near-identical protocol — shell command, JSON stdin, exit-code semantics): PreToolUse→guard.py (matcher on shell/write tools), SessionStart+PreCompact→inject_relay.py, Stop→session_end.py (**note:** session_end's usage digest parses Claude Code's transcript JSONL — in Codex it degrades to nudge-only; the handler is already defensive), PostToolUse→auto_lint.py. Destination: `.codex/hooks.json` in the codex bundle.

**Gemini target sketch:** `workspace_root: ".gemini"`; skills → `.gemini/skills/` (native SKILL.md support, stable since ~v0.26); commands → md→TOML transform (`prompt`/`description` keys, `{{args}}` for `$ARGUMENTS`); GEMINI.md from `agents.md.tmpl`; `settings.json` snippet with `mcpServers.junai` + optional `context.fileName: ["AGENTS.md","GEMINI.md"]`; hooks via Gemini's `settings.json` hook config mapping the same handlers (BeforeTool→guard, SessionStart→inject_relay, SessionEnd→session_end, AfterTool→auto_lint).

**Acceptance criteria / gate:** new target exports clean; `validate_pool.py` extended with a `--profile gemini` roster check mirroring Phase 0's pattern; existing suite green. *(Detailed implementation prompt deliberately omitted — write it when the phase is greenlit, against then-current Gemini CLI docs.)*

---

## Phase 7 — Hygiene sweep *(deferrable)*

**Goal:** remove dead weight and fix misleading surfaces. All items independent; batch or cherry-pick.

| Item | File(s) | Action |
|---|---|---|
| Dead converters | `export_runtime_resources.py:14-23,197-287,569-583` | If Phase 6 is greenlit: keep `transforms` plumbing, delete only `convert_agent_to_claude`/`convert_instruction_to_rules`/`TOOL_MAP`. If not: delete all three + the plumbing. |
| Orphan hook | `claude-harness/hooks/notify.py` | Delete (not wired in hooks.json, excluded from export at `runtime-targets.json:504`). |
| Stale paths | `sync.ps1:5-9` (header), `:2233` (revert message) | Replace `E:\Projects\agent-sandbox` references with claudster-source. |
| Agent prune | `.github/agents/mentor.agent.md` (+ registry check) | Move to `.github/agent-docs/.archive/`; it's referenced almost only from `.archive` already. Leave the other 6 unregistered agents (they ship usefully via copilot). |
| Unshipped prompts | `mockup`, `pool-promote`, `sql-optimization`, `sql-review` `.prompt.md` | Either add to a roster deliberately or archive — decide per prompt; default archive. |
| plugin.json branding | `plugin` block in `.github/runtime-targets.json:470-479` | Description → "claudster — dev harness plugin for Claude Code: lean subagents, TDD commands, tiered skills, CLAUDE.md generator." Drop `agent-agnostic` keyword from the *plugin*; the repo README keeps the multi-harness claim (true at pool level). Rides the next version bump. |
| validate_pool dedup | `validate_pool.py:546-603` | Merge `check_prompts`/`check_prompts_in_dir` copy-paste twins. |
| Legacy secrets | `sync.ps1:32-34` + `vscode.pat` on disk | Remove plaintext PAT/key file support; `.env` only. Delete the stray `vscode.pat`. |

**Gate:** full baseline suite + `validate_pool.py` + a `junai-push` dry sync (no `-Publish`) must stay green after each item.

---

## Global quality gate (run after every phase, before any publish)

```powershell
pytest scripts/tests/ claude-harness/hooks/tests/ .github/tools/pipeline-runner/tests/ .github/tools/mcp-server/tests/
# expect: 0 failures (baseline 242 + phase additions; mcp-server tests exist from Phase 1)
python export_runtime_resources.py                                  # exit 0
python validate_pool.py                                             # OK
python validate_pool.py --profile claude                            # OK (from Phase 0)
python validate_pool.py --profile claude-extras                     # OK (from Phase 0)
python claude-harness/scripts/check_doc_coverage.py --check         # exit 0
git status                                                          # only intended files
```

## Rollback / publish-workflow impact

- **Version-bump map (do not fight it):** plugin versions live in `.github/runtime-targets.json` plugin blocks and are auto-patch-bumped by `junai-push` on content diff; junai-mcp's version lives in the **mirror** repo's `pyproject.toml` (`junai-publish-mcp`); the three VS Code extensions bump their own `package.json`. Phases 1–2 → plugin 1.3.15 + junai-mcp 0.2.27 (one coordinated `junai-push -Publish` after both phases are green — avoid two PyPI releases). Phases 3–5 → plugin-only bumps: `junai-push` (post-Phase-0 semantics: sync+validate) then an explicit publish decision. Phase 0 itself changes no shipped content — no bump.
- **PyPI is permanent:** never publish junai-mcp mid-phase; publish only at phase boundaries after the global gate. If a bad MCP version ships, the recovery is a fixed 0.2.x+1, not deletion.
- **Rollback:** every phase is plain git — `git revert` the phase commit(s), re-run `export_runtime_resources.py`, and (only if a bad version already published) push a fixed follow-up version. The events JSONL and `.mcp.json` are additive; reverting them cannot strand consumer state. The one one-way door in this entire PRD is each PyPI upload.
- **Known interaction:** Phase 0 changes `junai-push` semantics — after it lands, the muscle-memory command publishes nothing. This is the intended safety property; the README runbook update is part of the phase, not optional.

*— End of Pass 1 deliverable. Pass 2 consumes: E.3 (plugin-first + MCP seam verdict), Phase 1–2 schemas (run_skill_headless, events JSONL, HEADLESS.md contract), the `lavish` adopt verdict + naming correction (package `lavish-axi`, skill `lavish`), and the reserved `[pipeline]` config section.*

