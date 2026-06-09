# dev.to Post — Ready to Publish

**Title:** I type one sentence. 24 AI agents do the rest. Here's how.

**Tags:** `vscode` `ai` `github` `productivity`

---

<!-- PASTE BELOW THIS LINE INTO DEV.TO EDITOR -->

> ⚡ **Early access / beta** — shipping updates daily. Things move fast. Jump in now and grow with it.

---

Most AI coding tools give you a smart assistant.

You ask. It answers. You ask again. It answers again.

There's no *process*. No structure. No handoffs. Just you, manually steering an LLM through every decision from idea to shipped feature — one prompt at a time.

**What if you didn't have to steer at all?**

---

## 🎬 Watch the pipeline run

> 📸 *[GIF: intent typed into @Orchestrator → routes to @prd → PRD writes itself → pipeline-state.json updates in real-time → next agent auto-opens]*

That's not a demo environment. That's just VS Code + GitHub Copilot + junai installed.

---

## The idea: a real engineering process, run by AI

**junai** is a 24-agent pipeline inside VS Code. Every stage of your delivery lifecycle has a dedicated specialist agent. The Orchestrator routes between them. State is tracked in a plain-text file in your repo.

```
Intent → PRD → Architecture → Plan → Implement → Test → Review → Shipped ✅
    ↑ every stage has a specialist, every transition is logged, every gate is explicit
```

You describe what you want to build. The pipeline figures out what needs to happen and who handles each part — automatically.

---

## 🤖 Autopilot: sign off once, watch it go

> 📸 *[GIF: autopilot mode — pipeline-state.json updating on disk, next agent auto-opening in Copilot chat, handoff prompt firing, no mouse clicks]*

Switch to **autopilot mode** and junai's watcher monitors `pipeline-state.json` in real-time. The moment a stage completes:

1. Reads the routing decision
2. **Automatically opens the correct specialist agent**
3. **Sends the handoff prompt** — the next agent starts immediately

No copy-paste. No "now go tell the architect agent...". It just *goes* — until it hits a decision that genuinely needs you.

You sign off the intent once. The pipeline runs the rest.

---

## 24 specialists. Right model for the right job.

| Agent | Model | Why |
|-------|-------|-----|
| Orchestrator, Architect, Anchor | Claude Opus | Highest-stakes reasoning |
| Code Reviewer, Debug | Claude Sonnet | Judgment over generation |
| Implement, Tester, SQL, Frontend | GPT-5.3-Codex | Pure code output |
| Diagrams, UI/UX | Gemini Pro | Visual + design |

---

## 9 MCP tools — pipeline control from chat

> *"Where are we?"* → `get_pipeline_status`
> *"Skip this stage"* → `skip_stage`
> *"Who handles testing?"* → `get_agent_for_stage`

---

## 3 modes for 3 situations

| Mode | What it does |
|------|-------------|
| 🎛️ **supervised** | You approve every gate — full control |
| 🤝 **assisted** | AI recommends, you decide |
| 🤖 **autopilot** | Sign off the intent once. Pipeline runs itself. |

---

## Try it in 60 seconds

1. Open VS Code (GitHub Copilot required — the one you already pay for)
2. Search **junai** in Extensions, or → [install from marketplace](https://marketplace.visualstudio.com/items?itemName=junai-labs.junai)
3. Open Copilot Chat → type `@Orchestrator` → describe what you want to build

The agent pool lives in `.github/` — portable across machines, shareable across teams.

---

## ⚠️ This is moving fast

junai is in **active beta**. Features ship *daily*. The core pipeline is stable and production-tested, but rough edges exist.

If something breaks — [open an issue](https://github.com/saajunaid/junai-vscode/issues). Fixes land same day or next. Early adopters shape what this becomes.

---

**→ [junai on VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=junai-labs.junai)**
**→ [GitHub](https://github.com/saajunaid/junai-vscode)**

<!-- PASTE ABOVE THIS LINE INTO DEV.TO EDITOR -->

---

## GIFs to record before publishing

1. **Pipeline GIF** — type an intent to `@Orchestrator`, watch it route to `@prd`, PRD generates, `pipeline-state.json` updates live. ~15 sec.
2. **Autopilot GIF** — pipeline mid-run, state file updating, extension auto-opening next agent, prompt firing, no clicks. ~10 sec.

Recommended tool: [ShareX](https://getsharex.com/) (free, Windows) — record as GIF or MP4, then upload directly to dev.to editor.
