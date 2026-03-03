---
description: "Extract tribal knowledge Gold Nuggets from the codebase and write them directly into .github/copilot-instructions.md"
mode: agent
tools: ['codebase', 'editFiles', 'search']
---

# /golden-nuggets — Extract & Capture Project Gold Nuggets

Scan the codebase and write newly discovered tribal knowledge directly into `.github/copilot-instructions.md`. This is a maintenance task — run it after a major feature, sprint, or onboarding session to keep the AI context file up to date.

---

## Step 1 — Detect the tech stack (silent)

Before extracting, identify: primary language/runtime, framework(s), hosting model, DB/storage layer, test framework, CI/CD pipeline, and any unique infrastructure (queues, caches, vector stores, auth layers, embedded frontends, etc.). Use this to shape which categories are relevant in Step 2. Skip categories that don't apply.

---

## Step 2 — Extract Gold Nuggets

Scan the full codebase. For each category below, extract only what is **not already captured** in the existing `.github/copilot-instructions.md`.

**[Environment]**
Non-obvious hosting and setup: environment variable loading order, config file precedence, local dev vs. production differences, reverse proxy or IIS rules, self-signed certs, auth handshakes (Windows Auth, AD, OAuth), port/CORS configuration for multi-service architectures.

**[Architecture]**
Non-obvious service wiring: startup sequence that fails silently if changed, DI registration rules, multi-process or multi-service co-existence, unique initialisation logic, caching layer rules (TTL, invalidation, shared vs. per-user).

**[UI / Embedded Frontend]** *(skip if not applicable)*
Widget lifecycle and integration rules: iframe injection patterns, postMessage bridge contracts (message shapes, origin handling), z-index and positioning rules, state management across page transitions, known bug fixes that must not be reverted.

**[Data & Query Patterns]**
Query composition rules not already documented, ORM or adapter quirks, cross-DB or cross-schema access patterns, connection pooling gotchas, migration rules, anything about externalization of queries (e.g. YAML-based query stores).

**[Test & CI Patterns]**
Fixture setup, mock patterns for external dependencies, test isolation requirements, known flaky test causes, CI pipeline commands and flags that must not be changed, E2E test sequencing rules.

**[Critical Rules]**
Coding standards enforced by convention (not linter), naming patterns, import conventions, DRY enforcement zones, logging conventions, security rules (no secrets in code, auth patterns), feature flag wiring.

---

## Step 3 — Write rules

**Write directly — no confirmation needed:**
- New nuggets not mentioned anywhere in the existing file.
- Additional detail that expands an existing entry without contradicting it.
- Append new content under the most relevant existing section header, or add a new section if no suitable header exists.

**STOP and ask before writing:**
- The existing file states a rule or pattern, but the codebase shows it has changed or is no longer accurate. State clearly: what the file says, what the code shows, and your proposed resolution. Wait for confirmation before proceeding.
- A documented rule appears to have been intentionally worked around in several places. Flag it — do not silently overwrite institutional decisions.

**Never do:**
- Do not delete or rewrite existing sections.
- Do not remove Commands, pipeline, CI, deployment, or Key Files sections or any content within them.
- Do not reduce existing detail — only add.

---

## Step 4 — Write session log

When all writes are complete, append the following block at the bottom of `.github/copilot-instructions.md`:

```
## Gold Nuggets Session Log — {today's date}

### Added
- {Section} → {one-line summary of what was added}
- ...

### Conflicts flagged
- {What the file said} vs {what the code shows} — {resolution confirmed by user}
- None (if no conflicts)

### Skipped (nothing new found)
- {Category name}
- ...

> This log section can be deleted after review.
```

---

## Quick reference

```
/golden-nuggets                  ← Full extraction across all categories
/golden-nuggets chat widget      ← Focus on a specific area
/golden-nuggets environment      ← Focus on hosting/env config only
```
