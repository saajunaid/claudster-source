---
Original Author: Claude Code
Creation Date: 2026-06-08
---

# JUNAI DEV ECOSYSTEM — WALL CHART

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║              THE JUNAI / CLAUDE CODE DEV ECOSYSTEM                              ║
║              4 layers · 1 agent · many apps                                     ║
╚══════════════════════════════════════════════════════════════════════════════════╝

 LAYER 1 — POOL                    LAYER 2 — HARNESS
 agent-sandbox (local only)        deployed per-project
 ─────────────────────────         ─────────────────────────────────
 skills/       knowledge           CLAUDE.md      identity + rules
 agents/       subagent templates  src/CLAUDE.md  backend rules
 commands/     slash commands      frontend/      frontend rules
 instructions/ always-on rules     tests/         test rules
 prompts/      prompt templates    AGENTS.md      Codex mirror
                                   .claude/       agents + commands
 Publish: junai-push               relay.md       session continuity
   → GitHub (junai repo)
   → MCP v0.2.9 on PyPI            Deploy: /setup-project-ai
   → VS Code v1.2.20               (run once per new project)
   → Claude plugin on GitHub

 LAYER 3 — PLATFORM                LAYER 4 — PROJECTS
 platform-infra                    the apps
 ─────────────────────────         ─────────────────────────────────
 new-vmie-project.ps1              appointment-assist
   → scaffolds FastAPI+React       nps-lens · rev-sight · app-sight
     +MSSQL+Alembic+NSSM
   → auto-runs setup_project_ai    Stack: FastAPI + React/Vite
   → harness from day 1            + shadcn + MSSQL + Alembic
                                   + Gitea CI + NSSM (dev → prod)

══════════════════════════════════════════════════════════════════════════════════

 THE DAILY WORKFLOW
 ─────────────────────────────────────────────────────────────────────────────────

 ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
 │ START       │   │ PLAN        │   │ VALIDATE    │   │ IMPLEMENT   │
 │             │   │             │   │             │   │             │
 │ Read        │ → │ /feature-   │ → │  preflight  │ → │ /tdd        │
 │ relay.md    │   │  plan       │   │  subagent   │   │ <behavior>  │
 │ (auto hook) │   │ → plan file │   │ PASS / FAIL │   │ RED→GREEN   │
 └─────────────┘   └─────────────┘   └─────────────┘   └──────┬──────┘
                                                               │
 ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
 │ CLOSE       │   │ SHIP        │   │ REVIEW      │          │
 │             │   │             │   │             │          │
 │ /handoff    │ ← │ /ship       │ ← │ code-       │ ←────────┘
 │ relay.md    │   │ gates→CI    │   │ reviewer    │
 │ nuggets     │   │ →prod       │   │ subagent    │
 └─────────────┘   └─────────────┘   └─────────────┘

══════════════════════════════════════════════════════════════════════════════════

 KEY COMMANDS                       KEY SUBAGENTS
 ────────────────────────────       ──────────────────────────────────────────
 /feature-plan  plan a feature      preflight         plan validation (pre-code)
 /tdd           red→green→refactor  code-reviewer     diff review (post-code)
 /prd           product req doc     tester            test coverage check
 /ship          commit→CI→prod      security-analyst  security scan (Opus)
 /handoff       end-session relay   debug             root cause analysis
 /agent-log     view run history    anchor            evidence-first verify
 /setup-        deploy harness      sql-expert        query review + opt.
   project-ai   to a new repo       data-engineer     pipeline review
                                    codebase-audit    cross-file pattern scan
                                    knowledge-xfer    update CLAUDE.md docs
                                    ui-design-        screenshot→critique
                                      reviewer        aesthetics/UX/a11y

══════════════════════════════════════════════════════════════════════════════════

 THE PLUGIN — INSTALL ONCE, USE EVERYWHERE
 ─────────────────────────────────────────────────────────────────────────────────
 /plugin marketplace add saajunaid/junai
 /plugin install junai@junai

 Plugin = knowledge (skills + subagents) — global, all sessions
 Harness = context (ports, routes, DB stack) — per-project, run /setup-project-ai

 UPDATE THE PLUGIN: run junai-push from agent-sandbox — auto-publishes everything

══════════════════════════════════════════════════════════════════════════════════

 DESIGN SYSTEM                      SUBAGENT DISPATCH MODEL
 ──────────────────────────         ──────────────────────────────────────────
 warm-editorial-ui = canonical       Subagent = tool-allowlist
   warm cream light / charcoal dark            + method
   Bahnschrift + Plus Jakarta Sans             + return-format contract
   brand red #E10A0A                 Returns only conclusions → main thread
   signal-red accent                 stays clean (context firewall)
   Settings tab for theme toggle
   Icon-only dark/light switch       ~109k subagent tokens → ~2k returned

══════════════════════════════════════════════════════════════════════════════════

 SESSION CONTINUITY SYSTEM
 ─────────────────────────────────────────────────────────────────────────────────
 relay.md          → what's done, what's next, exact resume prompt
 MEMORY.md         → user profile, feedback, project state (across sessions)
 agent-log.jsonl   → subagent verdict history (runtime signal for eval)
 plan files        → durable spine that survives session death

 RESUME A SESSION: paste the resume prompt from relay.md  (or SessionStart hook
 auto-loads it — you may not need to type anything at all)

══════════════════════════════════════════════════════════════════════════════════

 GITEA DEPLOY PIPELINE (per app)
 ─────────────────────────────────────────────────────────────────────────────────
 git push → ci.yml triggers on Gitea runner
   lint_and_test → frontend_checks → deploy_prod → release_metadata → notify

 Prod: Windows Server · NSSM services · CalVer tags · health + version endpoints
 /ship handles the full loop — see skills/devops/deploy-local/SKILL.md for detail

══════════════════════════════════════════════════════════════════════════════════

 WHAT TO DO WHEN STUCK
 ─────────────────────────────────────────────────────────────────────────────────
 Context filling up?    → /compact  then update relay.md
 Session dying?         → /handoff  → resume prompt in next session
 Plan wrong?            → run preflight subagent against it first
 CI broken?             → /ship monitors + classifies failures; use deploy-local skill
 Design looks bad?      → dispatch ui-design-reviewer with the running app URL
 DB query slow?         → dispatch sql-expert with the query + EXPLAIN output
```
