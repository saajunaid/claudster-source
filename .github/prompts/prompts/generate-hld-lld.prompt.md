---
mode: agent
description: "Generate a professional enterprise-grade HLD or LLD document from the project's living Architecture.md"
tools: ['codebase', 'search', 'fetch']
---

# Generate Architecture Document (HLD / LLD)

Create a formal, enterprise-grade architecture deliverable from our living documentation.

## Instructions

1. **Load the architecture document skill**: Read `.github/skills/docs/architecture-document/SKILL.md`
2. **Read the living architecture doc**: Read `docs/Architecture.md` completely
3. **Read project config**: Read `.github/project-config.md` for org name, tech stack, branding
4. **Follow the Generation Workflow** in the skill (Steps 1-5)
5. **Ask me**: HLD, LLD, or both? DOCX, PPTX, or both?

## Quick Triggers

- "Generate HLD" → Full High-Level Design document
- "Generate LLD" → Full Low-Level Design document  
- "Generate HLD for {component}" → Scoped to one subsystem
- "Architecture deck" → Executive summary PPTX
