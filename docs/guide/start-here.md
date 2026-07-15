# Start here

Welcome. This guide covers the two tools you'll use day to day — **claudster** and **docket** — and the three "model lanes" you can run work on. If you read nothing else, read this page: it's the map everything else hangs off.

## The two tools in one breath

| | **claudster** | **docket** |
|---|---|---|
| What it is | A **Claude Code harness** — a plugin + a pool of skills, subagents, commands, and hooks | A **web task board** (event-sourced Kanban) with an **autonomous multi-agent pipeline** |
| Where you use it | In your **terminal / IDE**, inside a Claude Code session | In your **browser** (and it drives agents on a server) |
| Who it's for | You, coding solo | You + your team — shared, visible, role-gated |
| One-line job | Makes a single Claude Code session smarter and un-loseable | Runs and *watches* whole plan→build→ship pipelines across a repo |

**They are two layers, not two versions of the same thing.** claudster shapes how one agent behaves in a session. docket orchestrates many agent runs and shows everyone the state on a board.

## How they came to be (the 30-second history)

1. **claudster came first.** It solved the pains of working with an AI coding agent in a terminal: sessions lose context, knowledge evaporates, plans drift, and it's easy to do something destructive. So it added a resume doc (`relay.md`), a memory system, plans-as-a-spine, and safety guards.
2. **docket came after.** The terminal is single-user and invisible to your team. docket puts a **shared, multi-user board** over the *same* claudster planning lifecycle, and adds **autonomous orchestration** — it literally spawns claudster's own commands (`/claudster:prd`, `/claudster:feature-plan`, `/claudster:implement`) as headless runs and shows their progress on the board.

So docket doesn't replace claudster — it stands on top of it. If claudster is the engine, docket is the mission control.

## The three model lanes

Separately from the two tools, you have **three "lanes"** — different models for different jobs. Switching between them is just *which command you type*:

| Lane | You run | Engine | When to use |
|---|---|---|---|
| **Primary** | `claude` | Anthropic (your Claude plan) | Your default. Hardest reasoning, architecture, anything high-stakes. |
| **Coding fallback** | `claude-glm` | GLM Coding Plan (subscription) | When Claude quota is capped, or for bulk/mechanical work. |
| **Reviewer** | `/claudster:cross-review` | DeepSeek (pay-per-token) | A cheap second opinion on a diff, from a different vendor, before you commit. |

The one idea that removes all confusion: **the command decides the model and the billing, not the key.** Each command is wired to the right endpoint and reads its key for you. You never juggle keys. Full detail is in the **Providers & keys** tab.

## Which do I reach for?

- **Writing or debugging code, solo, right now?** → claudster, lane = `claude` (or `claude-glm` if you're rate-limited).
- **About to commit a risky diff?** → `/claudster:cross-review` (DeepSeek lane).
- **Want a plan/PRD/implementation to run autonomously and be visible to the team?** → docket, move a card into the pipeline.
- **Just want to see what agents are doing / triage incoming work?** → docket's Board + Command Center.

## Where to go next

- **claudster** tab — install it, the core commands, memory model, and every feature.
- **docket** tab — run the server, add a project, turn on the agent pipeline.
- **Providers & keys** tab — GLM vs DeepSeek, where your keys live, how to switch and future-proof models.
