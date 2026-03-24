---
description: "Plan mode - analyze requirements and create plans before implementation (no code until approved)"
applyTo: "**"
priority: 100
---

# Plan Mode Instructions

These instructions apply when the user enters "plan mode", "requirements mode", or provides raw requirements that need analysis before implementation.

## Trigger Conditions

Activate plan mode when the user:

- Says "plan mode", "planning mode", or "requirements mode"
- Says "I need to build...", "We need a system that...", "Create a project for..."
- Provides vague or high-level requirements
- Asks for help with a new feature without specific details
- Says "help me understand what we need"

## Plan Mode Behavior

### DO NOT

- ❌ Write code immediately
- ❌ Make assumptions about requirements
- ❌ Skip the clarification phase
- ❌ Provide implementation details before understanding the problem
- ❌ Generate files without user confirmation

### DO

- ✅ Ask clarifying questions first
- ✅ Confirm understanding before proceeding
- ✅ Break down complex requirements into components
- ✅ Identify missing information
- ✅ Propose a plan before execution
- ✅ Wait for user approval at each phase

## Plan Mode Workflow

### Phase 1: Discovery (Required)

When user provides requirements, respond with:

```
I'm in plan mode. Before we start building, let me understand the requirements fully.

**What I understood:**
{summarize what you understood}

**Questions I need answered:**
1. {specific question about scope}
2. {specific question about users}
3. {specific question about data}
4. {specific question about constraints}

**Missing information:**
- {what's not clear}

Please answer these questions, or let me know if my understanding is correct.
```

### Phase 2: Confirmation

After gathering information:

```
**Requirements Summary:**

| Aspect | Details |
|--------|---------|
| Goal | {one sentence} |
| Users | {who will use this} |
| Data Sources | {where data comes from} |
| Key Features | {main capabilities} |
| Constraints | {timeline, tech, compliance} |

**Proposed Approach:**
1. {step 1}
2. {step 2}
3. {step 3}

**Recommended Agents:**
- PRD agent - To generate formal PRD
- Architect agent - To design the system
- Implement (or other relevant) agent - For implementation

Does this look correct? Should I proceed with generating the PRD?
```

### Phase 3: Handoff

Once confirmed, guide to appropriate agent:

```
Great! Let's proceed with the formal documentation.

**Next Step:** I recommend using the PRD agent to generate a detailed Product Requirements Document.

You can say (in Cursor: @prd, or in any IDE: invoke the PRD agent with):
> Generate a PRD for {summarized requirements}

Or I can help you draft the initial PRD here. What would you prefer?
```

## Integration with Existing Agents

*(In Cursor, @agent names switch to that agent; in other IDEs, load the agent's instructions and invoke the same workflow.)*

### With PRD Agent

When the PRD agent is invoked, it should:
1. Check if plan mode analysis was done
2. If not, enter discovery phase first
3. If yes, use gathered information to generate PRD

### With Planner agent

The Planner agent already follows "Think First, Code Later" philosophy. Plan mode instructions reinforce this across ALL agents.

### With Architect Agent

Before architecture work, verify:
1. Is there a PRD? → If no, recommend @prd first
2. Are requirements clear? → If no, enter plan mode
3. Has scope been confirmed? → If no, ask for confirmation

## Example Scenarios

### Scenario 1: Vague Request

**User**: "I need a complaints dashboard"

**Response (Plan Mode)**:
```
I'm entering plan mode to understand your requirements fully.

**What I understood:**
You need a dashboard related to complaints.

**Questions:**
1. What type of complaints? (Customer, internal, regulatory?)
2. Who will use this dashboard? (Managers, analysts, team leads?)
3. Where does complaints data come from? (SQL Server, Pega, ServiceNow?)
4. What insights do you need? (Trends, agent performance, SLAs?)
5. Any timeline or compliance requirements?

Please provide more details so I can help you plan effectively.
```

### Scenario 2: Clear Request

**User**: "Create a Streamlit dashboard that shows customer complaint trends from our SQL Server complaints table, for use by the complaints team managers"

**Response (Confirm Mode)**:
```
Clear requirements! Let me confirm my understanding:

**Requirements Summary:**
| Aspect | Details |
|--------|---------|
| Goal | Customer complaint trends dashboard |
| Users | Complaints team managers |
| Data Source | SQL Server (complaints table) |
| Tech Stack | Streamlit |
| Key Features | Trend visualization |

**Questions to finalize:**
1. What time periods? (Daily, weekly, monthly?)
2. What metrics matter most? (Volume, resolution time, categories?)
3. Need filtering capabilities? (By agent, category, date?)

Once confirmed, I'll recommend the PRD agent to formalize this into a PRD.
```

## Exiting Plan Mode

Plan mode ends when:
- User says "exit plan mode" or "let's start coding"
- User has confirmed requirements and approved the approach
- A PRD has been generated and approved
- User explicitly requests implementation

When exiting, summarize:

```
Exiting plan mode. Here's what we established:

**Project**: {name}
**PRD Location**: docs/prd/prd.md
**Next Steps**: 
1. Architect agent for system design
2. SQL Expert agent for database schema
3. Streamlit Developer agent for UI

Ready to start implementing!
```
