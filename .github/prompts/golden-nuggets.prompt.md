---
description: "Extract tribal knowledge Gold Nuggets from the codebase and write them to the correct destination — hub file, instruction files, or runbooks"
mode: agent
tools: ['codebase', 'editFiles', 'search']
---

# /golden-nuggets — Extract & Capture Project Gold Nuggets

Scan the codebase and write newly discovered tribal knowledge to the appropriate AI documentation file. This is a maintenance task — run it after a major feature, sprint, or onboarding session to keep AI context up to date.

---

## Step 1 — Detect the tech stack (silent)

Before extracting, identify: primary language/runtime, framework(s), hosting model, DB/storage layer, test framework, CI/CD pipeline, and any unique infrastructure (queues, caches, vector stores, auth layers, embedded frontends, etc.). Use this to shape which categories are relevant in Step 2. Skip categories that don't apply.

---

## Step 2 — Extract Gold Nuggets

Before scanning, list any `*.instructions.md` files found in `.github/instructions/` and note their `applyTo` patterns — this tells you which categories already have a dedicated home so you can route to them in Step 3 rather than the hub.

Scan the full codebase. For each category below, extract only what is **not already captured** in the existing documentation.

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

**[Operational Procedures]** *(skip if no runbooks directory exists)*
Step-by-step procedures that a developer or operator follows at runtime: service restart sequences, deployment decision trees, incident checklists, environment verification steps, rollback procedures, port conflict resolution, connectivity tests. Extract only procedures not already covered in an existing runbook.

---

## Step 3 — Route each nugget

Modern projects split AI context across multiple files. The hub file (`copilot-instructions.md`) should stay lean — it is loaded in every session and grows expensive if bloated. Route each nugget to the most specific appropriate destination before falling back to the hub.

**Instruction file** (`*.instructions.md` in `.github/instructions/`)
Domain conventions, framework patterns, component rules, anything scoped to a file type or feature area. Before writing a nugget to the hub, check whether an instruction file already exists with a matching `applyTo` glob. If one exists, write there. If an instruction file clearly *should* exist for this area but doesn't, create it with an appropriate `applyTo` pattern.

**Runbook** (`docs/runbooks/` or equivalent operational docs directory)
Operational procedures: incident checklists, restart sequences, deployment steps, connectivity tests, anything a human follows step-by-step during an incident or release. Write to an existing runbook if one covers the topic, or create a new one with a descriptive filename.

**Hub file** (`copilot-instructions.md`)
Core project context that applies globally to every file and every session: architecture overview, data sources, key commands, key files table, top-level conventions. Write here only if the nugget is genuinely global and does not belong in a more specific file.

> **Fallback rule**: If no instruction files or runbooks directory exist in the project, write everything to the hub file as before.

---

## Step 4 — Write rules

**Write directly — no confirmation needed:**
- New nuggets not mentioned anywhere in the existing documentation.
- Additional detail that expands an existing entry without contradicting it.
- Append new content under the most relevant existing section header, or add a new section if no suitable header exists.

**STOP and ask before writing:**
- The existing documentation states a rule or pattern, but the codebase shows it has changed or is no longer accurate. State clearly: what the file says, what the code shows, and your proposed resolution. Wait for confirmation before proceeding.
- A documented rule appears to have been intentionally worked around in several places. Flag it — do not silently overwrite institutional decisions.

**Never do:**
- Do not delete or rewrite existing sections.
- Do not remove Commands, pipeline, CI, deployment, or Key Files sections or any content within them.
- Do not reduce existing detail — only add.
- Do not add detail to a hub-file section that has been delegated to an instruction file or runbook. Instead, ensure the hub contains a pointer to the correct file and stop. Adding content to both creates drift.

---

## Step 5 — Write session log

When all writes are complete, write the following block to `docs/gold-nuggets-log.md` — create the file if it doesn't exist, or prepend the new entry at the top if it does.

Do not append the log to the hub file — it inflates the hub over time and clutters agent context.

```
## Gold Nuggets Session — {today's date}

### Added
- {Destination file} → {Section} → {one-line summary of what was added}
- ...

### Conflicts flagged
- {What the file said} vs {what the code shows} — {resolution confirmed by user}
- None (if no conflicts)

### Skipped (nothing new found)
- {Category name}
- ...

> Review and archive or delete this file once changes have been verified.
```

---

## Quick reference

```
/golden-nuggets                  ← Full extraction across all categories
/golden-nuggets chat widget      ← Focus on a specific area
/golden-nuggets environment      ← Focus on hosting/env config only
/golden-nuggets ops              ← Focus on operational procedures / runbooks only
```
