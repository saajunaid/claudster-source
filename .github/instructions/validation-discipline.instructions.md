---
description: "Validation discipline — rules for fact-checking, git status verification, and absence confirmation to prevent false positive/negative verdicts"
applyTo: "**"
---

# Validation Discipline

These rules apply whenever an agent is asked to verify, validate, audit, or check the state of files, repositories, or system components. They exist to prevent two classes of error: declaring something missing when it exists, and declaring something clean when it has pending work.

---

## Rule 1 — Confirm Absence With a Text Search

**Never declare a file entry missing based solely on a paginated `read_file` scan.**

`read_file` with line ranges can return truncated or empty results at range boundaries without indicating the file has more content. A "(empty)" return does not mean the target content is absent.

**Required protocol:**
- Before writing any FAIL verdict for a missing entry, run a `grep_search` (or `Select-String`) targeting the specific term.
- An empty `grep_search` result is definitive proof of absence.
- A partial file read is not.

```powershell
# ✅ CORRECT: confirm absence
Select-String -Path "docs\port-registry.md" -Pattern "nps-lens"
# Empty result = entry is absent. Non-empty = entry exists.

# ❌ WRONG: read lines 1-60, see nothing, declare absent
```

---

## Rule 2 — Use the Primary Signal for Git Push Status

**Never infer push status from `git log --oneline -N` decoration text or from `git status`.**

The decorations `(HEAD -> main, origin/main)` in a short log are correct, but verifying by visual inspection under context load is error-prone. Dirty working tree output from `git status` is orthogonal to push status and must not be conflated with unpushed commits.

**Required protocol:**
- Use `git log origin/main..HEAD --oneline` explicitly.
- Empty output = zero unpushed commits. Non-empty = commits to push.
- `git status` and `git diff` answer a different question (uncommitted changes) — do not use them as push-status signals.

```powershell
# ✅ CORRECT: definitive push check
git log origin/main..HEAD --oneline
# Empty = nothing to push

# ❌ WRONG: infer from git status showing modified files
# ❌ WRONG: infer from visual inspection of ref labels in git log -3
```

---

## Rule 3 — Identify the Primary Signal Before Writing a Verdict

For any check, define *before drawing a conclusion* what the primary signal is — the command whose direct output answers the question — and verify against that signal.

Secondary signals (surrounding output, visual inference, nearby data) require explicit cross-checking before being used as evidence.

| Check | Primary signal | Wrong signal |
|-------|---------------|--------------|
| Unpushed commits | `git log origin/main..HEAD` | `git status`, dirty tree |
| Entry exists in file | `grep_search` match/no-match | Paginated file read |
| Port in use | `netstat -ano \| findstr :PORT` | Process list inference |
| File exists | `Test-Path` | Directory listing scan |

---

## Rule 4 — Verify File Paths Before Referencing Them

**Never state or paste a file path in a prompt, handoff, or attachment list unless the path has been verified from the actual workspace tree.**

File paths are easy to subtly invent from summaries (for example, flattening `src/commands/foo.ts` into `src/foo.ts`). This causes avoidable confusion and bad handoffs.

**Required protocol:**
- Before referencing a file path as fact, verify it with a primary signal such as `Get-ChildItem -Recurse`, `file_search`, or `Test-Path`.
- If you only know the filename from a summary or report, treat the folder path as **unknown until verified**.
- When giving attachment lists, use the exact verified path from the workspace, not a reconstructed guess.

```powershell
# ✅ CORRECT: verify the real location before referencing it
Get-ChildItem -Recurse -File src | Select-Object -ExpandProperty FullName
Test-Path "src\commands\ask.ts"

# ❌ WRONG: infer nested path from a summary
# "ask.ts exists, so it must be src\ask.ts"
```

## Anti-Patterns

| Anti-pattern | Correct behaviour |
|---|---|
| Read file in ranges, see nothing, declare FAIL | Run `grep_search` first — no match = absent |
| Dirty `git status` → "unpushed commits" FAIL | `git log origin/main..HEAD` — empty = clean |
| "Probably not there" based on visual scan | Always verify absence with a targeted search before filing a verdict |
| Conflating working tree state with remote sync state | These are orthogonal — check each independently |
| Infer `src/foo.ts` from a filename summary | Verify with `Get-ChildItem`, `file_search`, or `Test-Path` first |
