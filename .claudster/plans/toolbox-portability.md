---
type: plan
status: implemented (Phases 1-4 done; Phase 2 live-validated 2026-07-23; Phase 5 optional/unstarted; remaining tail: codex re-login + bundles/ mirror publish)
feature: toolbox-portability
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-20T00:00:00Z
Creating Model: claude-fable-5
---

# Toolbox portability — claudster in any coding harness

## Goal
One canonical toolbox (`.github/` source), consumable from any coding agent — Claude Code (plugin,
already shipped), **Codex CLI** and **Antigravity** first, then any AGENTS.md-reading harness — with a
one-command public install per project.

## Decisions (settled 2026-07-20)
- **Mental model confirmed:** one canonical source + per-harness export shapes. Never fork the toolbox.
- **Two layers, ported differently:**
  - *Knowledge layer* (skills, instructions, prompts, agent briefs — markdown): ships to EVERY harness.
  - *Execution layer* (hooks, slash commands, subagents): Claude Code native. **Knowledge-first now,
    MCP as the portable execution layer later** (Phase 5) — `junai-mcp` travels to any MCP-capable
    harness, but only after Track 0's shell-exec gating lands (it hardens the very tool we'd expose).
- **First validation targets:** Codex CLI **and** Antigravity (both, to prove the recipe generalizes).
- **Distribution:** hosted on GitHub in the existing `junai` repo (same `junai-push` flow, MIT-licensed).
  Bundles published under `bundles/<target>/`; installer script `claudster-init` in the same repo.
- **Sequencing:** plan now; implementation starts after the Track 0 claudster-mediums pass
  (`docs/analysis/fable-remediation-status.md`) is done.
  *Update 2026-07-21: the claudster-side mediums are ALL done — this plan is clear to start. Sole
  coordination gate: the docket re-audit session (see relay) owns `export_runtime_resources.py`,
  `validate_pool.py`, `sync.ps1`, and the remediation tracker while it runs — don't edit those
  concurrently; running the exporter and editing `runtime-targets.json` is fine.*

## Current state (verified 2026-07-20; re-verified 2026-07-21)
**Re-verification deltas (2026-07-21):**
- The `.github/tools/` pipeline-runner + mcp-server were RETIRED (59e68bf) — the codex target never
  referenced them, so this plan is unaffected. Do NOT confuse that retired mcp-server with `junai-mcp`
  (the PyPI package under `vscode-extensions/junai/src/junai_mcp/`) — junai-mcp survives and is Phase 5's
  subject.
- The exporter is now fail-closed on phantom skills (d391e9f). The codex roster was checked against
  `.github/skills/` on 2026-07-21: 94 skills, zero phantoms — a codex re-export will not trip it.
- junai-mcp shell-exec is gated (opt-in env + arg-array exec + allowlist, verified in `server.py`) —
  **Phase 5's blocker is cleared.**
- `codex-cli 0.137.0` still installed; still unauthenticated (HUMAN prereq unchanged).
- `.github/runtime-targets.json`: 6 targets (copilot, ptarmigan, liffey, **codex**, claude, claude-extras),
  all exported by `export_runtime_resources.py` from canonical `.github/`.
- Codex target defined (skills → `.agents/skills/`, `AGENTS.md` from
  `claude-harness/claude-md/agents.md.tmpl`, `.codex/config.toml.example`) — **built, never live-tested**,
  and `dist/runtime-resources/` currently has NO codex build (needs re-export).
- `.claudster/plans/codex-integration.md` exists: Phase 1 (probe CLI contract, no auth) and Phase 3
  (live-validate the bundle, needs `codex login`) are the codex half of THIS plan — do not duplicate.
- `codex-cli 0.137.0` installed on this box; NOT authenticated (blocked on OpenAI subscription — HUMAN).
- Antigravity: nothing exists yet — no contract doc, no target, unknown discovery mechanism.
- Claude Code + Copilot targets: proven in production. They are the reference, untouched by this plan.

## Prerequisites (HUMAN)
- OpenAI subscription + `codex login` (blocks codex live validation only; probe phase needs none).
- Antigravity installed on this box (blocks antigravity probe).

## Phases

### Phase 1 — Codex: probe + live-validate the existing bundle  ✅ DONE (84874a3, 2026-07-21)
> Probed contract: `docs/analysis/codex-cli-contract.md`. Skills root was WRONG (.agents/skills →
> `.codex/skills`); 2 pool skills had fence-wrapped frontmatter (silently skipped by codex) — fixed.
> Offline validation via `codex debug prompt-input`: AGENTS.md injected, 94/94 skills visible.
> **Remaining (HUMAN): `codex logout && codex login` (refresh token revoked), then one real
> `codex exec` running a skill workflow.**
Execute `.claudster/plans/codex-integration.md` **Phases 1 and 3 only** (the CLI-contract probe and the
live bundle validation; its Phases 2/4/5 are cross-review/docket work, out of scope here).
Re-export first: `python export_runtime_resources.py --profile codex`.
**Rule:** never trust remembered flags/paths — probe `codex --help` and its skills-discovery docs; fix
`runtime-targets.json` mappings as found (e.g. if `.agents/skills/` is wrong for the installed version).
**Exit gate:** codex demonstrably loads the exported AGENTS.md and executes one skill's workflow in a
scratch repo; findings + any mapping fixes recorded in `docs/analysis/codex-cli-contract.md`.
**Commit:** `fix(export): codex bundle validated live`

### Phase 2 — Antigravity: probe → target → validate  ✅ DONE + LIVE-VALIDATED (63a84c2 → aa2eaa0, 2026-07-23)
> Two-surface story: IDE 1.107 probe (2026-07-21) found `.claude/skills/`; the **agy CLI v1.1.5
> (Antigravity 2.0 harness, installed 2026-07-23) uses `.agents/skills/`** — target switched to the
> CLI contract (aa2eaa0). **Live validation PASSED headless** (`agy -p --new-project` from a
> bundle-seeded repo): AGENTS.md read (6 Laws), bundle skills discovered, `git-commit` skill
> workflow executed correctly. No IDE eyeball step needed. Gotchas (project binding, permission
> auto-deny, --sandbox hang) recorded in the contract doc.
**Goal:** repeat the Phase-1 recipe on a second harness, from zero.
**Implement:**
1. Probe (no code): where does Antigravity look for project context/rules/skills? (AGENTS.md support?
   rules dir? MCP config location?) Record verbatim findings in
   `docs/analysis/antigravity-contract.md` — probed from the installed product + official docs, not memory.
2. Add an `antigravity` target to `runtime-targets.json` mirroring the codex target's shape, adjusted to
   the probed discovery paths. Skills roster = same as codex.
3. Export → copy into a scratch repo → confirm it loads the conventions and executes one skill workflow.
**Exit gate:** same as Phase 1, for antigravity; contract doc exists.
**Commit:** `feat(export): antigravity target, probed and validated live`

### Phase 3 — Generalize: the "new harness" checklist  ✅ DONE (fa23b16, 2026-07-21)
**Goal:** turn two data points into the repeatable recipe.
**Implement:** `docs/guide/porting-to-a-harness.md` — the 5-step loop (probe discovery contract → add
target → export → live-validate one skill → record contract doc), with the codex and antigravity contract
docs as worked examples. Note explicitly which harnesses converge on AGENTS.md so future targets start
from that assumption *and still probe it*.
**Exit gate:** doc exists; a third harness (e.g. opencode) could be added by following it verbatim.
**Commit:** `docs: porting claudster to a new harness — the repeatable recipe`

### Phase 4 — Public distribution: bundles + `claudster-init` installer  ✅ DONE (586f8d1, 2026-07-21)
> Installer + 10 TDD tests + README section shipped; smoke-tested against both real bundles
> (262/261 files, idempotent re-run). **Deferred: wiring `bundles/<target>/` into the junai-push
> mirror sync — `sync.ps1` is owned by the concurrent docket re-audit session; do it when that
> session closes.** Until then GitHub-mode 404s and `--from <checkout>` is the working path.
**Goal:** one-command install per project, hosted in the `junai` GitHub repo.
**Touches:** `sync.ps1`/publish flow, new `scripts/claudster_init.py`, `scripts/tests/test_claudster_init.py`.
**Implement:**
- Publish `dist/runtime-resources/<target>/` for codex + antigravity (+ copilot) into the junai repo as
  `bundles/<target>/` via the existing `junai-push` sync (respect the content-based denylist; verify
  leak-free with `git grep` like the 84f662f pass).
- `claudster_init.py`: `claudster-init --target codex|antigravity|copilot [--from <local checkout>]`.
  Default source = GitHub tarball of the junai repo (`codeload.github.com/.../tar.gz/refs/heads/main`),
  `--from` for offline/local use. Copies the bundle into the CWD project; idempotent — re-running updates
  in place; refuses to overwrite files the user has locally modified without `--force` (hash manifest).
  Cross-platform (Windows-first — no POSIX-isms).
- README (`## Installing outside Claude Code`) documents the one-liner, e.g.
  `pipx run --spec <github-url> claudster-init --target codex` or download-and-run.
**TDD:** stub the download (local tarball fixture); test target selection, idempotent re-run,
modified-file protection, unknown-target failure.
**Exit gate:** from a clean scratch repo on this box, one command installs the codex bundle from GitHub
and codex uses it (spot-check). Full suite + `validate_pool.py` green.
**Commit:** `feat(dist): claudster-init — one-command toolbox install for any harness`

### Phase 5 (later, optional) — MCP as the portable execution layer
**Blocked on:** ~~Track 0 item 1 (junai-mcp shell-exec gating)~~ — shipped 2026-07-20 (191b80d); unblocked.
**Goal:** the execution-layer value that CAN travel: expose `junai-mcp` to codex + antigravity via their
probed MCP config formats (`.codex/config.toml`, antigravity's equivalent per its contract doc); ship
example config stanzas in each bundle. No reimplementing hooks/subagents — MCP only.
**Exit gate:** one junai-mcp tool invoked from inside each harness.
**Commit:** `feat(mcp): junai-mcp wired into codex + antigravity bundles`

## Non-goals (the over-complication traps — do not do these)
- No forked per-harness copies of skills; `.github/` stays the only source of truth.
- No reimplementation of Claude Code hooks/subagents/slash-commands in other harnesses.
- No N×N adapter matrix: harness #3+ goes through the Phase-3 checklist, not a bespoke project.
- No new hosting infrastructure: the junai GitHub repo is the distribution point.

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\toolbox-portability.md fully, then execute it
autonomously in E:\Projects\claudster-source. Phase 1 delegates to codex-integration.md Phases 1+3.
Rules: probe every harness contract live — never trust remembered flags or paths; TDD for all code
(Phase 4); full suite after each phase (python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q
--import-mode=importlib && python validate_pool.py); commit per phase, only files the phase touched;
update this plan's phases with ✅ + hash. If a HUMAN prerequisite (codex login / antigravity install)
is missing, complete every unblocked phase and mark the blocked one blocked-on-human. junai-push (bare)
allowed after commits; the bundle publish in Phase 4 must pass the leak-free git grep check first.
```
