# 🚀 AI Agents Workflow Cheat Sheet
## Developer Wall Poster Reference

---

# SECTION 1: AGENT TYPES

## Three Types of Agents

| Type | Where | Interaction | Invoke With | Best For |
|------|-------|-------------|-------------|----------|
| **LOCAL** | VS Code Chat | Interactive, real-time | Dropdown selector | Planning, design, interactive coding |
| **BACKGROUND** | Your machine (CLI) | Autonomous, async | `@cli` or "Continue In" | Long tasks while you do other work |
| **CLOUD** | GitHub servers | Autonomous, creates PRs | `@cloud` or assign issue to `copilot` | Team collaboration via PRs |

---

# SECTION 2: YOUR CUSTOM AGENTS (LOCAL)

## Agent → Model → Purpose

### Deep Reasoning (Claude Opus 4.6)
| Agent | Purpose |
|-------|---------|
| **PRD** | Requirements discovery, stakeholder synthesis |
| **Architect** | System design, trade-offs, architecture decisions |
| **Plan** | Strategic planning, technical roadmapping |
| **Debug** | Root-cause analysis, bug fixing, plan amendment briefs |
| **Code Reviewer** | Quality, security, standards review |
| **Security Analyst** | Threat modeling, OWASP review, risk analysis |
| **UX Designer** | UX flows, user goals, business constraints |
| **Prompt Engineer** | Multi-agent workflows, prompt design |
| **UI/UX Designer** | Design systems, visual identity, component specs |

### Multi-File Coding (GPT-5.3-Codex)
| Agent | Purpose |
|-------|---------|
| **Implement** | Full code implementation, refactors |
| **Streamlit Developer** | Streamlit UI, app wiring |
| **Frontend Developer** | HTML/CSS/JS, components |
| **Data Engineer** | ETL pipelines, data integration |
| **SQL Expert** | Query optimization, DB troubleshooting |
| **Tester** | pytest, test strategy, coverage |

### Balanced Speed-Quality (Claude Sonnet 4.6)
| Agent | Purpose |
|-------|--------|
| **DevOps** | CI/CD, Docker, infrastructure |
| **SVG Diagram** | Architecture diagrams, visual docs |
| **Accessibility** | WCAG 2.2 checks, a11y remediation |
| **Project Manager** | Work planning, status tracking |
| **Janitor** | Code cleanup, dead code removal |
| **Mermaid Diagram Specialist** | Flowcharts, sequence diagrams |
| **Mentor** | Teaching, step-by-step explanations |

---

# SECTION 3: CONTEXT RULES

## ✅ Context PRESERVED
- Same chat, switch agents
- Same chat, switch models  
- Use handoff buttons
- AI spawns subagents

## ❌ Context LOST
- New chat (Ctrl+L)
- Close VS Code
- Different workspace

## New Chat Has:
- `copilot-instructions.md`
- `.github/instructions/*.md`
- Files you @mention

---

# SECTION 3.5: SKILLS VS INSTRUCTIONS

## Quick Comparison

| Feature | Instructions | Skills |
|---------|-------------|--------|
| **Location** | `.github/instructions/*.md` | `.github/skills/*/SKILL.md` |
| **Applied** | ✅ **Automatically** via `applyTo` | ❌ **On-demand** (must read) |
| **Purpose** | Rules/standards for file types | Domain-specific workflows |
| **Loaded When** | Working on matching files | Agent reads the skill file |

## Instructions (Auto-Applied)

Instructions have `applyTo` patterns that activate automatically:

```yaml
# In sql.instructions.md
---
applyTo: "**/*.sql"
---
```

| Instruction | Auto-Applies To |
|-------------|-----------------|
| `python.instructions.md` | `**/*.py` |
| `sql.instructions.md` | `**/*.sql` |
| `streamlit.instructions.md` | `**/*.py` |
| `testing.instructions.md` | `**/*test*.py` |
| `docker.instructions.md` | `**/Dockerfile*` |
| `github-actions.instructions.md` | `.github/workflows/*.yml` |

## Skills (Must Request)

Skills are specialized knowledge that agents load when needed:

| Skill | When To Use |
|-------|-------------|
| `context-handoff` | **⚠️ EMERGENCY ONLY** - Unexpected interruption, context exhausted |
| `data-analysis` | Analyzing datasets, creating visualizations |
| `data-loader` | Loading data from files to database |
| `refactoring` | Safely restructuring code |
| `ui-testing` | Creating Playwright/E2E tests |
| `git-commit` | Writing conventional commits |
| `github-issues` | Creating well-structured issues |
| `prd-to-code` | Converting requirements to code |
| `code-explainer` | Explaining complex code |
| `ui-review` | Reviewing UI implementations |

## Prompts (Slash Commands)

Quick actions invoked with `/command`:

| Command | Purpose | Output |
|---------|---------|--------|
| `/plan` | **Create phased execution plan** for multi-session work | `.github/plans/<feature>.md` |
| `/context-handoff` | **Emergency** - Save context when unexpectedly interrupted | `.github/handoffs/YYYY-MM-DD_*.md` |

### Usage

```
/plan add customer search feature    ← Creates phased plan
/plan refactor data services         ← Creates refactor plan
/context-handoff                     ← Emergency handoff (auto-detect mode)
/context-handoff full                ← Force full handoff with documentation
/context-handoff quick               ← Quick handoff (prompt only)
```

## How To Request A Skill

```
# Option 1: Ask agent directly
"First read .github/skills/data-analysis/SKILL.md, then analyze this data"

# Option 2: @mention the skill file
"Apply the patterns from @.github/skills/refactoring/SKILL.md to clean this code"

# Option 3: Agent has built-in guidance (updated agents)
Agents now know which skills to load for specific tasks!
```

---

# SECTION 4: DECISION TREE

```
START: What do you need?

├─► Requirements unclear?
│   └─► Use PRD Agent
│
├─► Need system design?
│   └─► Use Architect Agent
│
├─► Need step-by-step plan?
│   └─► Use Plan Agent
│
├─► Ready to code?
│   └─► Use Implement Agent
│
├─► Bug to fix?
│   └─► Use Debug Agent (Opus 4.6)
│       ├─► Code-only fix? → Debug fixes, done
│       └─► Plan also wrong? → Debug writes amendment brief
│           └─► "Amend Plan" handoff → Plan Agent applies it
│
├─► Long autonomous task?
│   └─► Use @cli (Background)
│
└─► Team collaboration needed?
    └─► Use @cloud (Cloud Agent)
```

---

# SECTION 5: WORKFLOW PATTERNS

## Pattern A: Full Feature Development (Same Chat)

```
┌─────────┐    ┌───────────┐    ┌──────┐    ┌───────────┐    ┌────────┐    ┌──────────┐
│   PRD   │───►│ Architect │───►│ Plan │───►│ Implement │───►│ Tester │───►│ Reviewer │
│Opus 4.6 │    │ Opus 4.6  │    │Opus  │    │GPT-5.3-Cdx│    │Codex   │    │ Opus 4.6 │
└─────────┘    └───────────┘    └──────┘    └───────────┘    └────────┘    └──────────┘
     │              │              │              │              │              │
     └──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
                              SHARED CONTEXT ✅
```

**How**: Use handoff buttons after each response

## Pattern B: Quick Implementation (Skip to What You Need)

```
┌───────────┐    ┌───────────┐
│ Architect │───►│ Implement │
│ Opus 4.6  │    │GPT-5.3-Cdx│
└───────────┘    └───────────┘
```

**When**: You already have clear requirements

## Pattern C: Background Autonomous Task

```
┌──────────────┐         ┌───────────────────┐
│ Local Agent  │ ──@cli──►│ Background Agent  │
│ Create Plan  │         │ Implements Plan   │
└──────────────┘         │ (You do other     │
                         │  work meanwhile)  │
                         └───────────────────┘
```

**When**: Task is well-defined, will take 30+ minutes

## Pattern D: Team Collaboration

```
┌──────────────┐          ┌─────────────┐         ┌────────────┐
│ Local Agent  │ ──@cloud─►│ Cloud Agent │────────►│ GitHub PR  │
│ Design/Plan  │          │ Implements  │         │ Team Review│
└──────────────┘          └─────────────┘         └────────────┘
```

**When**: Need team review, working on shared repo

## Pattern E: Debug Session

```
┌─────────────┐    ┌───────────────┐
│    Debug    │───►│ Code Reviewer │
│  Opus 4.6   │    │   Opus 4.6    │
│ (Deep root  │    │  (If complex) │
│  cause)     │    │               │
└─────────────┘    └───────────────┘
```

**When**: Quick bug fix, escalate if complex

## Pattern G: Implementation Bug → Plan Amendment

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│ Implementation  │     │    Debug     │     │  Plan Agent  │
│ (Codex agent)   │────►│  (Opus 4.6)  │────►│  (Opus 4.6)  │
│                 │     │              │     │              │
│ Spots issue →   │     │ 1. Diagnose  │     │ 1. Read brief│
│ "Debug Issue"   │     │ 2. Fix code  │     │ 2. Apply to  │
│  handoff button │     │ 3. Write     │     │    plan file │
│                 │     │    amendment │     │              │
│                 │     │    brief     │     │              │
└─────────────────┘     └──────────────┘     └──────────────┘
                              │
                              ▼
                      .github/handoffs/
                      plan-amendment-*.md
                      (small file, <20 lines)
```

**When**: Bug during implementation reveals the plan has wrong or missing info
**Key rule**: Debug agent NEVER edits plan files directly — writes a brief, hands off to Plan agent
**Handoff chain**: Implementation → "Debug Issue" → Debug → "Amend Plan" → Plan

## Pattern F: Cross-Domain Collaboration

```
┌───────────┐    ┌────────────┐    ┌─────────────┐
│ Architect │───►│ SQL Expert │───►│Data Engineer│
│ Opus 4.6  │    │   Codex    │    │   Codex     │
│ (Design)  │    │ (Schema)   │    │ (Pipeline)  │
└───────────┘    └────────────┘    └─────────────┘
     │                 │                  │
     └─────────────────┴──────────────────┘
              SHARED CONTEXT ✅ (Same Chat!)
```

**How**: Use handoff buttons to pass work to specialized agents
**When**: Database design, data pipelines, cross-cutting concerns

### Collaboration Tips

| Scenario | Agent Flow | Handoff Button |
|----------|------------|----------------|
| Design DB | Architect → SQL Expert | "Design Database Schema" |
| Build Pipeline | Architect → Data Engineer | "Design Data Pipeline" |
| Build Streamlit UI | Architect/Plan → Streamlit Dev | "Build Streamlit UI" |
| Design UX | Architect/Plan → UX Designer | "Design UX" |
| Build Frontend | UX Designer → Frontend Dev | "Build Frontend" |
| Create Diagram | Architect → SVG Diagram | "Create Diagram" |
| Schema + Pipeline | SQL Expert → Data Engineer | "Create Data Model" |
| Validate Design | SQL Expert → Architect | "Validate Architecture" |
| Security Review | Any → Security Analyst | "Review Security" |
| Code Cleanup | Code Reviewer → Janitor | "Clean Up Code" |
| Deploy | Implement/CR → DevOps | "Deploy" |
| Plan Fix | Debug → Plan Agent | "Amend Plan" |

### Skills in Collaboration

Agents can also leverage **skills** for specialized knowledge:

```
When working on data-related features:
- Architect reads: .github/skills/data-analysis/SKILL.md
- SQL Expert reads: .github/skills/data-loader/SKILL.md
- Both apply patterns from: .github/instructions/sql.instructions.md
```

---

# SECTION 6: INVOCATION QUICK REFERENCE

## Local Agents (Interactive)
```
1. Open Chat (Ctrl+Alt+I)
2. Click agent dropdown (top)
3. Select agent (e.g., "Architect")
4. Type your prompt
5. Use handoff buttons to continue workflow
```

## Background Agent (Autonomous)
```
1. In Local Agent, create detailed plan
2. Type: @cli implement this plan
   OR: Click "Continue In → Background"
3. Agent works in Git worktree
4. Check Sessions view for progress
5. Review changes when done
```

## Cloud Agent (Team PRs)
```
1. In Local Agent, finalize design
2. Type: @cloud implement this
   OR: In GitHub, assign issue to "copilot"
3. Cloud agent creates branch & PR
4. Team reviews PR
5. Merge when approved
```

## Subagents (Automatic)
```
- AI spawns automatically for complex tasks
- Optional explicit: "Use a subagent to analyze X first"
- Results feed back to main agent
```

---

# SECTION 7: BEST PRACTICES

## DO ✅
1. Stay in same chat for related work
2. Use handoff buttons (context preserved)
3. Start with appropriate agent for your clarity level
4. Save important artifacts to files
5. Let AI decide when to use subagents

## DON'T ❌
1. Start new chat mid-workflow (context lost!)
2. Assume new chat knows previous work
3. Use Background for tasks needing real-time feedback
4. Forget to save designs/plans to files

---

# SECTION 8: CONTEXT RECOVERY

## Cold Start a New Chat

### Option 1: Reference Files
```
"Implement auth system as documented in @docs/architecture/auth-design.md"
```

### Option 2: Provide Context
```
"Implement JWT auth. Key files: src/api/auth.py, src/models/user.py
 Requirements: Access tokens, refresh tokens, 24h expiry"
```

### Option 3: Let Agent Gather
```
"Implement the search filters. First analyze src/pages/1_🔍_Search.py
 and src/components/ for existing patterns"
```

---

# SECTION 9: QUICK COMMANDS

| Want To... | Say... |
|------------|--------|
| Start planning | "Create implementation plan for X" |
| Get architecture | "Design the architecture for X" |
| Write code | "Implement X following the design above" |
| Quick debug | "Debug this error: [paste error]" |
| Review code | "Review the implementation above" |
| Write tests | "Write tests for the code above" |
| Research first | "First analyze X, then implement Y" |
| Save artifact | "Save this design to docs/X.md" |
| Background task | "@cli implement this plan" |
| Cloud/team task | "@cloud implement and create PR" |

---

# SECTION 10: VISUAL SUMMARY

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT SELECTION GUIDE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CLARITY LEVEL                              RECOMMENDED AGENT                │
│  ─────────────                              ─────────────────                │
│                                                                              │
│  "I have a vague idea"          ──────────► PRD (Opus 4.6)                  │
│                                                                              │
│  "I have requirements"          ──────────► Architect (Opus 4.6)            │
│                                                                              │
│  "I have a design"              ──────────► Plan (Opus 4.6)                 │
│                                                                              │
│  "I know what to code"          ──────────► Implement (GPT-5.3-Codex)       │
│                                                                              │
│  "I have a bug"                 ──────────► Debug (Opus 4.6)                │
│                                             └─► If plan wrong: "Amend Plan" │
│                                                                              │
│  "Long task, do it async"       ──────────► @cli (Background)               │
│                                                                              │
│  "Need team PR review"          ──────────► @cloud (Cloud Agent)            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTEXT FLOW DIAGRAM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SAME CHAT SESSION                                                          │
│  ┌───────┐   ┌───────────┐   ┌──────┐   ┌───────────┐                      │
│  │  PRD  │──►│ Architect │──►│ Plan │──►│ Implement │  ✅ Context Shared   │
│  └───────┘   └───────────┘   └──────┘   └───────────┘                      │
│                                                                              │
│  NEW CHAT = FRESH START                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                                │
│  │ Previous Chat   │──X──│   New Chat      │  ❌ Context Lost              │
│  │ (design, plan)  │     │ (starts fresh)  │                                │
│  └─────────────────┘     └─────────────────┘                                │
│                                                                              │
│  RECOVERY OPTIONS:                                                          │
│  • @mention files: "See @docs/design.md"                                    │
│  • Paste context: Provide key details                                       │
│  • Let agent search: "First analyze src/..."                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT TYPE COMPARISON                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LOCAL AGENTS (Your Custom Agents)                                          │
│  ├── Interactive, real-time                                                 │
│  ├── Full tool access (MCP, extensions)                                     │
│  ├── Select from dropdown                                                   │
│  └── Best for: Most development tasks                                       │
│                                                                              │
│  BACKGROUND AGENTS (@cli)                                                   │
│  ├── Autonomous, runs in background                                         │
│  ├── Uses Git worktrees (isolated)                                          │
│  ├── Limited tools (no MCP)                                                 │
│  └── Best for: Long tasks, well-defined plans                               │
│                                                                              │
│  CLOUD AGENTS (@cloud)                                                      │
│  ├── Runs on GitHub servers                                                 │
│  ├── Creates branches & PRs                                                 │
│  ├── Team collaboration                                                     │
│  └── Best for: Team review, GitHub issues                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# FOR SVG AGENT: POSTER LAYOUT GUIDE

## Recommended Poster Sections (Left to Right, Top to Bottom)

### Row 1: Header
- Title: "AI Agents Workflow Reference"
- Subtitle: "Developer Quick Guide"

### Row 2: Three Columns
- **Column 1**: Agent Types (Local, Background, Cloud) with icons
- **Column 2**: Decision Tree (When to use which agent)
- **Column 3**: Context Rules (Preserved vs Lost)

### Row 3: Main Workflow
- Full horizontal flow: PRD → Architect → Plan → Implement → Test → Review
- Show handoff arrows between agents
- Color-code by model type

### Row 4: Three Columns
- **Column 1**: Custom Agents List (grouped by model)
- **Column 2**: Invocation Commands (@cli, @cloud, dropdown)
- **Column 3**: Best Practices (Do/Don't)

### Row 5: Footer
- Quick Commands table
- Context Recovery options

## Color Coding
- **Claude Opus 4.6**: Deep Blue (#1E40AF) — Planning, Architecture, Debugging, Code Review (9 agents)
- **GPT-5.3-Codex**: Green (#059669) — Multi-file code generation (6 agents)
- **Claude Sonnet 4.6**: Purple (#7C3AED) — Balanced speed-quality (7 agents)
- **Background Agent**: Orange (#D97706)
- **Cloud Agent**: Sky Blue (#0EA5E9)
- **Primary Red Accent**: #E10A0A

## Icons
- 🧠 Deep Reasoning + Debugging (Opus 4.6)
- ⚡ Balanced (Sonnet)
- 💻 Code-Heavy (Codex)
- ⏳ Background
- ☁️ Cloud
- ✅ Context Preserved
- ❌ Context Lost

