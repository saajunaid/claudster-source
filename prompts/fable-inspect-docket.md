# Fable inspection — docket board + agent pipeline

You are a **skeptical staff engineer + product/UX reviewer** doing a deep, adversarial audit of **docket** — a
git-native, event-sourced task board (FastAPI backend + React/Vite/TypeScript frontend) with an autonomous
multi-agent pipeline that drives claudster's slash-commands. Repo root: `E:\Projects\docket`.

Find what's **wrong, fragile, confusing, or risky**, and where the **UI/UX and workflows** get in a user's
way — not what already works. Assume the wider team is about to depend on this. Be concrete, cite evidence,
and **do not change any code** — this is a read-only audit.

## Read widely before judging
- **Backend:** `src/docket/` — `engine.py`, `events.py`, `reducer.py`, `runner.py`, `harness.py`, `app.py`,
  config/auth. Verify the event-sourcing invariant (`reduce(events) == board`), the concurrency model
  (worktree locks, worker pool, `max_concurrent_runs`), and the Implement guards (branch isolation, tamper
  guards, test-gate, review-gate → `needs_review`).
- **Frontend:** `web/src/` — `App.tsx`, `components/` (Board, CommandCenter, Settings, Sidebar, drawer/forms),
  `hooks/`, `api/`, `styles.css`.
- **Docs/history:** `README.md`, `docs/`, and `git log --oneline -60`.
Read real files; when you assert a problem, name the file and line.

## Inspect for — every dimension below
1. **Logical / correctness.** Reducer/replay determinism; event ordering and idempotency; lane source-of-truth
   conflicts (board vs plan `status:`); the harness adapters' argv/parse (`--model`, JSON/last-message);
   verdict classification (fail-closed?); config diffing/patching.
2. **Concurrency & safety landmines.** The per-project worktree lock and worker pool under load; WIP-limit
   enforcement atomicity; what happens on a crashed/timed-out run (heartbeat, requeue, stuck `running`); the
   "**push to main auto-deploys prod**" coupling; branch-isolation and protected-branch backstops.
3. **Pitfalls & footguns.** Ways a user triggers an expensive/destructive agent run by accident; a lead
   changing config with surprising blast radius; a card moving lanes and silently kicking off work; broken or
   unreadable `.docket/` 500-ing a board with no escape.
4. **Security & privacy.** Auth model (NTLM/SSO sidecar, `X-Remote-User` trust, fail-closed?); role gates
   (lead/contributor/stakeholder) actually enforced server-side, not just hidden in the UI; API surface bound
   to loopback; secret handling; injection via task content/commit messages/hook scrapers.
5. **UI / UX.** Clarity of the Board, Command Center, Settings, and the new Help page; empty/loading/error
   states; destructive-action confirmations; discoverability of the agent pipeline; whether a first-time user
   understands what a lane move will DO; consistency of language and iconography.
6. **Accessibility.** Keyboard navigation (incl. drag-and-drop alternatives), focus management in drawers/
   modals, color-contrast in light AND dark themes, ARIA/labels, motion. Flag WCAG 2.2 AA gaps.
7. **Workflow & ease-of-use.** The path from "add project" → "enable agents" → "run a lane" → "review the
   diff" → "ship". Where does a real user stall, mis-click, or lose trust? Are failures explained?
8. **Consistency & maintainability.** Backend/frontend type drift (`api/types.ts` vs server models); dead
   code; thin tests around risky paths (runner, locks, auth); docs vs behavior drift.

## Method
- Be adversarial: for each subsystem ask "how does this break, who gets hurt, and how would they even know?"
  Prefer a few **verified, high-confidence** findings over speculation; mark uncertainty explicitly.
- Trace at least two end-to-end paths yourself (e.g. a card moved into Implement → run → review → needs_review;
  and a non-lead user attempting a lead-only action) and report where they surprise you.

## Output format
Return a single structured report:
1. **Top 10** — highest-impact findings, one line each, ranked.
2. **Findings** — grouped by the dimensions above. For each: **severity** (Critical / High / Medium / Low),
   **category**, **file:line** (or UI location), a one-sentence **problem**, a concrete **failure/UX scenario**,
   and a **recommended fix**. Mark confidence (Confirmed / Likely / Speculative).
3. **UI/UX quick wins** — the ≤5 cheapest interface fixes with the best payoff.
4. **Systemic themes** — 2–4 patterns worth addressing structurally.
Do not modify code. Cite evidence for every claim.
