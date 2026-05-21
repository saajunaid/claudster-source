# Handoffs Directory

This directory is reserved for pipeline handoff artifacts that are internal to the agent workflow.

## Current Session Continuation Workflow

For user-facing session continuation, use `/relay`.

Relay creates or updates `relay.md` at the repository root. It does not write new session-continuation files into `.github/handoffs/` by default.

## Plan Amendment Briefs

This directory can host plan amendment briefs written when implementation or debugging reveals incorrect or missing information in an execution plan.

Naming convention:

```text
plan-amendment-YYYY-MM-DD-<topic>.md
```

Lifecycle:

```text
Created  -> an agent finds a plan issue and writes a brief
Active   -> waiting for the planning owner to apply it
Applied  -> renamed to *-APPLIED.md after the plan is updated
Archived -> delete or archive after the work is no longer relevant
```

## Cleanup

Handoff artifacts are temporary workflow files. Keep them only while they are actively needed to route or repair work.
