# Implement — docket web accessibility (WCAG 2.2 AA)

You are a senior frontend + accessibility engineer. Implement the accessibility fixes below in the **docket**
web app. This is an IMPLEMENTATION task (not an audit) — write the code, test it, and verify it in a real
browser. Work in `E:\Projects\docket` (frontend under `web/src/`).

Source of these findings: `E:\Projects\claudster-source\docs\analysis\fable-audit-docket-2026-07-15.md`
(findings **F30–F34**). Read that section first for context.

## Ground rules
- **Branch:** create `feat/a11y` off `main`. **NEVER push docket `main`** — a push to main auto-deploys prod.
- **Don't regress:** the existing web suite must stay green (`cd web; npx vitest run` — currently ~90 tests).
  Run it after each phase.
- **Build must stay clean:** `cd web; npm run build` (tsc + vite) after each phase.
- **Commit per phase** with a clear message; only the files that phase touches.
- **Verify in a browser** (see "Verification" — this is mandatory; unit tests alone don't prove a11y).
- Tests: the suite has no React Testing Library today. If you add component tests, add `@testing-library/react`
  + `@testing-library/user-event` as devDeps; otherwise assert behavior via existing patterns and rely on the
  browser walkthrough. Prefer small, real assertions over none.

## Phase 1 — Keyboard-operable board (F30, WCAG 2.1.1 Keyboard, level A)
Today the Kanban uses only `PointerSensor` and cards are click-only `<article>`s — a card cannot be moved (or
even focused) without a mouse.
- In `web/src/components/Board.tsx`, register `@dnd-kit`'s **`KeyboardSensor`** with
  `sortableKeyboardCoordinates` alongside the existing `PointerSensor`.
- Make each card a **focusable, operable control** (a real `<button>`/`[role=button][tabindex=0]` with an
  accessible name), not a bare `<article onClick>` (`web/src/components/Card.tsx`).
- Provide a **non-drag path to move a card** (dnd keyboard alone is fiddly): a "Move to lane…" menu in the
  card (or drawer) that a keyboard user can operate. This is the primary a11y affordance; keyboard-DnD is a bonus.
**Done when:** you can Tab to a card, open it, and move it between lanes using only the keyboard.
**Commit:** `feat(a11y): keyboard-operable board — KeyboardSensor + focusable cards + move-to-lane menu (F30)`

## Phase 2 — Real dialogs for the drawer & modals (F31, WCAG 4.1.2, 2.4.3, 2.1.2)
The card drawer and bug form are plain `<div>`s with a backdrop `onClick` — no dialog semantics, no focus trap,
no Escape, focus isn't restored.
- `web/src/components/CardDrawer.tsx` and `web/src/components/BugForm.tsx` (and any other overlay):
  - Add `role="dialog"` + `aria-modal="true"` + an `aria-label`/`aria-labelledby`.
  - **Trap focus** within the dialog while open; move focus in on open and **restore it to the invoking element**
    on close.
  - **Escape closes** the dialog; the backdrop click may still close, but keyboard users must have Escape.
  A tiny reusable `useFocusTrap`/`<Dialog>` wrapper is fine (no new dependency required).
**Done when:** opening the drawer traps focus, Escape closes it, and focus returns to the card.
**Commit:** `feat(a11y): dialog semantics + focus trap + Escape + focus restore for drawer/modals (F31)`

## Phase 3 — Visible focus on every control (F32, WCAG 2.4.11/2.4.13)
`web/src/styles.css` sets `outline: none` in several places; most add a box-shadow ring, but controls built as
`<article>`/`<div>` get none.
- Ensure **every interactive element** is a real control (button/link/input) and has a **visible focus
  indicator** meeting the focus-appearance criteria in both light and dark themes. Prefer a single consistent
  `:focus-visible` ring token; remove `outline:none` where nothing replaces it.
**Done when:** tabbing through the whole app shows a clear focus ring on every stop, both themes.
**Commit:** `fix(a11y): consistent visible focus indicators; no unringed focusable controls (F32)`

## Phase 4 — Color & status not by color alone (F33, WCAG 1.4.3 + 1.4.1)
- Verify muted text tokens (`--ink-3` on `--surface-2`, and their dark-theme equivalents) meet **4.5:1** for
  small text; bump the token(s) if not. Check the run-meta, lane-index, and badge uses.
- `data-priority` / `data-severity` currently encode state by **color only** — add a non-color indicator
  (a short text label or a shape/icon) so the state is perceivable without color.
**Done when:** a contrast checker passes the muted pairings, and priority/severity read without color.
**Commit:** `fix(a11y): contrast on muted tokens + non-color priority/severity indicators (F33)`

## Phase 5 — Announce live run updates (F34, WCAG 4.1.3 Status Messages)
The board polls every ~2s but run-state changes (queued→running→needs_review) update silently.
- Add an `aria-live="polite"` region that announces meaningful run-state transitions (e.g. "Run for <task>
  needs review"). Keep it terse and debounced so it doesn't spam.
**Done when:** a screen reader (or the a11y tree) announces a run reaching a terminal/needs-review state.
**Commit:** `feat(a11y): aria-live announcements for agent run-state transitions (F34)`

## Verification (mandatory, before you call it done)
1. `cd web && npm run build` — clean. `npx vitest run` — green.
2. **Keyboard-only walkthrough** (no mouse): Tab to a card → open it → move it to another lane → close with
   Escape (focus returns). Use the `webapp-testing`/`playwright` skill to script this against the dev server
   (`npm run dev`), or do it by hand, and capture a screenshot at desktop + a note of each keyboard step.
3. Spot-check focus rings and priority/severity indicators in **both** light and dark themes.
4. Write a short results note (what you verified, any WCAG criteria still partial) into
   `docs/analysis/` in the docket repo.

## Output
A `feat/a11y` branch with one commit per phase, the build+tests green, and the verification note. Do NOT push
`main`. Summarize what's covered and flag anything left partial (e.g. a criterion needing design input).
