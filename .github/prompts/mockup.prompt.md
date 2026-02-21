---
mode: agent
description: "Generate a UI mockup for a feature before implementation"
tools: ['editFiles', 'createFiles', 'codebase']
---

# Generate UI Mockup

Create a visual mockup or wireframe for a new feature before implementation begins.

## Instructions

1. Read `project-config.md` to understand the framework, brand colors, and UI conventions
2. Load the mockup skill: `.github/skills/frontend/mockup/SKILL.md`
3. If an Intent Document exists in `agent-docs/intents/`, read it first to understand the goal
4. Ask: **What feature or screen do you want to mock up?**

## Workflow

1. Gather requirements (what the screen should show, who uses it, key interactions)
2. Create the mockup as an SVG or HTML file
3. Save to `agent-docs/ux/mockups/<feature-name>-mockup.<ext>`
4. Update `agent-docs/ARTIFACTS.md` with the new artifact
5. Present the mockup for review before implementation

## Handoff

Once approved, hand off to **UX Designer** for review or **Frontend Developer** / **Streamlit Developer** for implementation.
