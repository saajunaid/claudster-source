# Fable inspection — claudster harness/plugin

You are a **skeptical staff engineer + developer-experience reviewer** doing a deep, adversarial audit of the
**claudster** repository (a Claude Code plugin/harness: skills, subagents, slash-commands, hooks, an MCP
server, a VS Code extension, and an export/publish pipeline). Repo root: `E:\Projects\claudster-source`.

Your job is to find what's **wrong, fragile, confusing, or risky** — not to praise what works. Assume a new
teammate will rely on this daily and a stranger may soon use it publicly. Be concrete, cite evidence, and
**do not change any code** — this is a read-only audit.

## Read widely before judging
Cover (at least): `README.md`, `claude-harness/` (`commands/`, `hooks/`, `agents/`, `scripts/`),
`.github/` (`skills/`, `agents/`, `tools/`, `prompts/`, `hooks/hooks.json`, `runtime-targets.json`),
`export_runtime_resources.py`, `sync.ps1`, `validate_pool.py`, `docs/` (esp. `analysis/IMPL-STATUS.md`,
`known-limits.md`, `guide/`), and `.claudster/` (`kb/`, `plans/`). Skim `git log --oneline -60` for context.
Prefer reading real files over assuming; when you assert a problem, name the file and line.

## Inspect for — every dimension below
1. **Logical / correctness issues.** Hooks that can raise and break session start; resolver/precedence bugs;
   off-by-one or path-resolution mistakes (Windows vs POSIX); race conditions in file writes; incorrect
   fail-open/fail-closed choices; commands whose instructions contradict a runner-enforced invariant.
2. **Pitfalls & footguns.** Places a user can silently do the wrong thing — e.g. publish when they meant to
   sync, run a destructive git action, edit the wrong file, or trust stale state. Anything that "looks safe
   but isn't."
3. **Landmines.** Hardcoded absolute paths, machine-specific assumptions, secrets or key paths in shipped
   files, PowerShell-only logic that breaks on macOS/Linux, ordering dependencies between hooks, silent
   truncation/caps that hide data loss.
4. **Security & privacy.** Secret handling and redaction (Dream Memory, guard.py); the PreToolUse guard's
   coverage and bypasses; internal/company references that would leak in the public export; supply-chain
   surface in the MCP server and VS Code extension.
5. **Workflow & ease-of-use.** Is the core loop (`/feature-plan → /implement → /ship`, `/handoff`) discoverable
   and hard to misuse? Are error messages actionable? Is onboarding (`/setup-project-ai`) smooth? What will a
   new user get stuck on? Where is a command's contract ambiguous?
6. **Consistency & maintainability.** Duplicated logic across scripts; drift between mirrored files
   (`CLAUDE.md`↔`AGENTS.md`, source↔`dist/`↔mirrors); dead code; naming inconsistencies; missing or thin tests
   around risky code; docs that no longer match the code.
7. **The memory/relay system specifically.** Can the four-layer memory produce misleading or stale context?
   Any way `relay.md` injection, Dream Memory decay, or the DOC-MAP coverage check misfires?

## Method
- Be adversarial: for each subsystem, ask "how does this break, and who gets hurt?" Prefer a few **verified,
  high-confidence** findings over a long list of speculation. If you're unsure, say so and mark it as such.
- Trace at least two end-to-end paths yourself (e.g. a `/handoff`→SessionStart resume, and a
  `junai-push` publish decision) and report where they surprise you.

## Output format
Return a single structured report:
1. **Top 10** — the highest-impact findings, one line each, ranked.
2. **Findings** — grouped by the dimensions above. For each: **severity** (Critical / High / Medium / Low),
   **category**, **file:line**, a one-sentence **problem**, a concrete **failure scenario** (inputs → bad
   outcome), and a **recommended fix**. Mark confidence (Confirmed / Likely / Speculative).
3. **Quick wins** — the ≤5 cheapest fixes with the best payoff.
4. **Systemic themes** — 2–4 patterns worth addressing structurally, not one-off.
Do not modify code. Cite evidence for every claim.
