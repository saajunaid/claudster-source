# Prompt — Harden the headless `/prd` + `/feature-plan` convention against terse input

**Why:** the live demo (2026-07-04) found that a card with only a short title and **no description** made
headless `claude -p "/claudster:prd …"` **ask scoping questions instead of writing the PRD** — so the run
failed. That terse one-liner IS the core OLID use case ("post a one-line idea"), so the headless
convention must NEVER interview, even on a bare title. See IMPL-STATUS.md "CRITICAL FINDING".

**Nature of this fix:** it is prompt-engineering. The durable code work (wording + a content-lint test)
can be done unattended, but the REAL proof is a live `claude -p` run against a title-only card — which an
unattended session cannot do (no live claude; the change isn't in the installed plugin until published).
So the unattended session does the edit + lint test + commit, and STOPS; the live validation
(publish 1.3.16 → re-run the terse-input smoke → zero questions + artifact) is a human/reviewer follow-up.

**How to run:** root at `E:\Projects\claudster-source`; Opus 4.8; auto-accept; continue on the existing
`feat/agentic-pipeline` branch. claudster-only (no docket).

---

## PROMPT (paste below this line)

You are hardening claudster's headless-mode convention so a headless `/prd` / `/feature-plan` NEVER
interviews — even when the card is a bare one-line title with no description. This is claudster-only,
continuing the existing `feat/agentic-pipeline` branch. Do NOT touch docket. Do NOT publish. Do NOT run a
live `claude -p` (the change can't be validated live until it's published — that's a human follow-up).

### Read first
- `E:\Projects\claudster-source\docs\analysis\IMPL-STATUS.md` — the "CRITICAL FINDING" (headless `/prd`
  interviews on terse input) and the observed failure text.
- `claude-harness/commands/prd.md` — the existing `## Headless mode` section (added in A3).
- `claude-harness/commands/feature-plan.md` — its headless section (add one if absent, matching prd.md).

### The fix
Rewrite/strengthen the `## Headless mode` section in BOTH `prd.md` and `feature-plan.md` so that, when the
invocation contains the `HEADLESS RUN RULES` marker, the agent:
1. **NEVER asks a question, under any circumstances** — not even when the input is a single terse line
   with no description. Explicitly prohibit the observed failure ("do not respond with a list of scoping
   questions"). Asking is ALWAYS wrong in this mode; a draft with open questions is ALWAYS correct.
2. Treats a **bare title as sufficient input**: infer a reasonable, conventional interpretation of the
   feature, make explicit best-effort assumptions, and write the COMPLETE artifact anyway.
3. Records EVERY assumption and unresolved decision under `## Open questions` (or `[TECH-DECISION OPEN]`
   inline) — the section may be long; that is expected and good.
4. **Always writes the artifact file and ends with the fenced json highlights block** — never ends its
   turn with questions or a request for more info as the final message.
Keep the interactive (non-headless) path and the frontmatter template UNCHANGED. Only the headless branch
changes. Make the wording unambiguous and imperative (the model must not be able to read it as "ask if
unsure").

### Content-lint test (the only thing automatable here)
Add a small test (e.g. in `scripts/tests/` or a new `test_headless_convention.py`) asserting that BOTH
`prd.md` and `feature-plan.md` contain a `## Headless mode` section whose text includes the hard
never-ask guarantees (assert on key phrases you write, e.g. "never ask", "bare title", "Open questions",
"always write the artifact"). This is a guard against the section being weakened later — it does NOT
prove model behavior (that needs the live smoke below).

### Validation gate (what you CAN run)
- `python -m pytest scripts/tests/ claude-harness/hooks/tests/` (use `C:\Python\python.exe` if the venv
  lacks pytest) → all green incl. the new lint test.
- `python validate_pool.py` and `python validate_pool.py --profile claude` → OK (the golden-plan/skill
  markers must stay intact; if a marker trips, adjust placement not the marker).
- `python export_runtime_resources.py` → 0, and confirm the strengthened section appears in
  `dist/runtime-resources/claude/plugin/commands/prd.md`.

### Commit + stop
Commit: `fix(claudster): headless /prd + feature-plan never interview on terse input (OLID)`.
Then append a short section to `docs/analysis/IMPL-STATUS.md` describing the change and the REMAINING
human validation (below), and run the branch/commit report addendum (both repos) as in
`.claudster/prompts/agentic-pipeline-impl.md`. Do NOT publish.

### Human follow-up (OUT of scope for this run — state it clearly in the handoff)
1. `. .\sync.ps1; junai-push` → plugin **1.3.16** (mirror sync + bump; no MCP/VS Code release), then
   update the installed plugin.
2. Re-run the terse-input smoke: a title-only card (no description) through headless `/claudster:prd`
   must produce `.claudster/prd/<slug>.md` with **zero questions** and everything under `## Open
   questions`. This is the real proof the fix works.

Begin by reading the CRITICAL FINDING in IMPL-STATUS.md and the two command files, then make the edits.
