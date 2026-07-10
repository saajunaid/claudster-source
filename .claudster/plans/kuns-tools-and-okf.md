---
type: plan
status: draft
feature: kuns-tools-and-okf
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-10T00:00:00Z
Creating Model: claude-opus-4-8
---

# Kun's remaining tools + OKF-lite — decide-and-finish the Pass-1 adoptions

## Where this comes from
`docs/analysis/pass1-foundations.md` (2026-07-03) already contains the **verified** analysis: six parallel
deep-reads over fresh clones of all six kunchenguid repos + web verification of OKF/LLM-Wiki. The verdicts
were recorded in `docs/analysis/DECISIONS.md` and roadmapped (Pass 1 Phases 4–5, `ROADMAP.md` C-1) —
**but Phases 4 and 5 were never implemented** (verified 2026-07-10: KB notes carry no frontmatter, the
`/kb` command has no OKF mandate, `using-git-worktrees/SKILL.md` has no treehouse reference, no axi note
exists in `.claudster/kb/`). This plan finishes the job. **Read `pass1-foundations.md` Phases 4–5
(≈ lines 520–570) before starting — they carry the detailed specs; this doc is the executable index.**

## The verdict table (KEEP / DISCARD — user asked for this explicitly)
| Tool | Verdict | Why (from the verified analysis) |
|---|---|---|
| **lavish-axi** | ✅ KEEP — already adopted | The interview/visual-refine transport; wired into docket A5 and the prd/plan flows. Done. |
| **treehouse** | ✅ KEEP — adopt as *optional runtime dep* | Worktree manager; junction/copy-based so Windows-safe. Wire as a *reference* from the `using-git-worktrees` skill; user installs it themselves. Never vendored, never required. |
| **OKF** | ✅ KEEP — **OKF-lite** only | Full conformance needs only frontmatter (`type` is the sole required field). DOC-MAP already *is* OKF's `index.md` in spirit. **Skip** the raw/+wiki/ restructure entirely. |
| **no-mistakes** | ❌ DISCARD | Duplicates claudster's existing review lane (code-review skill/agent + docket's review gate). Revisit only if a pre-push AI gate is ever wanted. |
| **gnhf** | ❌ DISCARD (watch) | An autonomous loop-owner driving `claude -p` — overlaps docket's runner/autopilot role. Revisit only if unattended overnight loops become a need docket doesn't meet. |
| **firstmate** | ❌ DISCARD | ~27k LOC bash, hard tmux dependency, tracked git symlinks (confirmed broken on a default Windows checkout), `/tmp`, POSIX `ps` — WSL2-only, and 3 weeks old at analysis time. Fails platform + maturity tests. |
| **LLM-Wiki** | ❌ DISCARD | The raw/+wiki restructure fails the solo-user test; DOC-MAP + KB notes already cover the need. |

Nothing above needs re-litigating — the analysis was evidence-based (file citations + fresh clones). The
work below is only the two ✅ adoptions that were never landed.

## Phases

### Phase 1 — OKF-lite frontmatter on KB notes + the mandate
**Spec:** `pass1-foundations.md` § "Phase 4 — KB OKF-lite" (schema block: `type` required;
`title`, `description`, `tags`, `timestamp` recommended).
**Touches:** `.claudster/kb/harness-memory.md` (migrate — currently the ONLY body note),
`claude-harness/commands/kb.md`, the knowledge-transfer agent/skill (locate:
`Glob **/knowledge-transfer*` — mandate goes wherever new-note authoring is instructed),
`scripts/check_doc_coverage.py` ONLY IF the spec's Phase 4 says the checker validates frontmatter
(re-read it; the 2026-07 analysis said the checker never parses note bodies — if so, add validation as a
new `--check` rule guarded by tests, or leave the checker alone if the spec kept it out of scope).
**Implement:**
- Add frontmatter to `harness-memory.md`: `type: kb-note`, `title`, `description` (one line),
  `tags`, `timestamp` (its git creation date — `git log --follow --format=%aI -- <file> | tail -1`).
  **DOC-MAP.md is NOT a note — leave it untouched** (it is the index).
- `kb.md` + knowledge-transfer instructions: one paragraph mandating the frontmatter block on every NEW
  `.claudster/kb/*.md` note, with the schema inline.
- Tests (`scripts/tests/` — follow the existing test style there): a test that every `.claudster/kb/*.md`
  except `DOC-MAP.md` starts with `---` and declares `type:`; a test that `kb.md` contains the mandate text.
**Exit gate:** full suite green; `python scripts/check_doc_coverage.py --check` exit 0; `/kb` smoke
(run the command body's steps manually) still reports in-sync.
**Commit:** `feat(kb): OKF-lite frontmatter — migrated note + mandate + guard tests`

### Phase 2 — treehouse wiring (reference-only) + axi principles note
**Spec:** `pass1-foundations.md` § "Phase 5 — External adoptions".
**Touches:** `.github/skills/workflow/using-git-worktrees/SKILL.md`,
`.claudster/kb/axi-principles.md` (new, WITH the Phase-1 frontmatter).
**Implement:**
- `using-git-worktrees`: add a short "With treehouse (optional)" section — what it adds over raw
  `git worktree` (per the analysis: junction/copy-based worktree management, Windows-safe), the install
  pointer (`npx`/`install.ps1` per its README — verify the current install command from the treehouse
  README at implementation time, do not trust this line), and an explicit "the skill works WITHOUT it"
  sentence. Never vendor code.
- `axi-principles.md`: distil the axi principles the analysis adopted (source: the lavish-axi
  README/docs — re-read at implementation time) into a one-page KB note; link it from DOC-MAP via
  `python scripts/check_doc_coverage.py --reindex`.
**Exit gate:** full suite + `validate_pool.py` + `--check` all green; DOC-MAP row for the new note exists.
**Commit:** `feat(adopt): treehouse referenced from worktrees skill; axi principles KB note`

### Phase 3 — Close the loop
**Touches:** `docs/analysis/ROADMAP.md`, `docs/analysis/IMPL-STATUS.md`, `docs/analysis/DECISIONS.md`.
**Implement:** mark ROADMAP C-1 / Pass-1 Phases 4–5 done with commit hashes; append a dated IMPL-STATUS
section stating the verdict table above is now the implemented reality (KEEPs landed, DISCARDs recorded);
publish with bare `junai-push`.
**Exit gate:** junai-push reports the version bump.
**Commit:** `docs: pass-1 adoptions complete — OKF-lite + treehouse/axi landed, skips recorded`

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\kuns-tools-and-okf.md AND
docs/analysis/pass1-foundations.md (Phases 4–5 sections) fully, then execute the plan autonomously in
E:\Projects\claudster-source. Rules: the verdict table is settled — do not re-evaluate the tools; where
this plan says "verify at implementation time" (treehouse install command, axi source docs), verify by
reading the actual upstream README rather than assuming; TDD for the new guard tests; full suite
(python -m pytest -q --import-mode=importlib) + validate_pool.py + check_doc_coverage.py --check after
each phase; commit per phase, only your files; update this plan's phases with ✅ + hash. Bare junai-push
in Phase 3 is allowed (never -Publish). Never ask a question the plan or the cited analysis answers.
```
