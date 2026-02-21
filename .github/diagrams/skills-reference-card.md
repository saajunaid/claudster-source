# Skills Reference Card

> **88 Skills** across 11 categories — on-demand knowledge that agents load when needed.
> Updated: 2026-02-19

---

## How Skills Work

```
Skills are NOT auto-applied. An agent reads a SKILL.md file when its task matches.

  Location:   .github/skills/{category}/{name}/SKILL.md
  Invoke:     "Read .github/skills/coding/sql/SKILL.md first, then optimize this query"
  Or:         @mention the SKILL.md file in chat
  Or:         Agents auto-load skills listed in their "Skills" section
```

---

## Coding (14 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Architecture Design** | `coding/architecture-design/` | Layered patterns, Mermaid C4 diagrams, SQL Server data platform | — |
| **Backend Development** | `coding/backend-development/` | Backend API design, microservices patterns, TDD | — |
| **Caching Patterns** | `coding/caching-patterns/` | Caching strategies for Streamlit and FastAPI applications | Streamlit Dev |
| **Code Explainer** | `coding/code-explainer/` | Explain code with diagrams, analogies, walkthroughs | Code Reviewer, Debug, Implement, Janitor, Mentor, Plan, Prompt Engineer, Tester |
| **Code Review** | `coding/code-review/` | Automated code review for quality, security, performance | — |
| **FastAPI Dev** | `coding/fastapi-dev/` | Build FastAPI backends with standard patterns and testing | — |
| **JavaScript/TypeScript** | `coding/javascript-typescript/` | JS/TS development with ES6+, Node.js, React | — |
| **LLM Application Dev** | `coding/llm-application-dev/` | Building apps with LLMs — prompt engineering, RAG patterns | — |
| **MCP Builder** | `coding/mcp-builder/` | Guide for creating MCP servers for LLM tool integration | — |
| **Python** | `coding/python/` | Modern Python 3.12+, Django, FastAPI, async patterns | — |
| **Refactoring** | `coding/refactoring/` | Safely refactor code while maintaining behavior | Code Reviewer, Debug, Implement, Janitor, Mentor, Streamlit Dev |
| **Security Review** | `coding/security-review/` | OWASP security review workflow, code scanning | Code Reviewer, Janitor, Security Analyst |
| **SQL** | `coding/sql/` | Optimized SQL with performance, NULL handling, security | Architect, Implement, SQL Expert, Streamlit Dev |
| **Webapp Development** | `coding/webapp-development/` | End-to-end web app development with brand theming | — |

## Data (4 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Data Analysis** | `data/data-analysis/` | Systematic 5-phase dataset analysis and insight generation | Architect, Data Engineer, Implement, SQL Expert, Streamlit Dev |
| **Data Loader** | `data/data-loader/` | Load data from Excel, JSON, CSV into databases | Data Engineer |
| **Database Design** | `data/database-design/` | Schema design, optimization, migration patterns | — |
| **DB Testing** | `data/db-testing/` | Test, debug, and validate database connectivity and queries | Data Engineer, Debug, SQL Expert |

## DevOps (4 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Changelog Generator** | `devops/changelog-generator/` | Auto-create user-facing changelogs from git commits | DevOps |
| **Git Commit** | `devops/git-commit/` | Conventional commit messages following the standard | DevOps, Implement, Project Manager |
| **GitHub CLI** | `devops/gh-cli/` | GitHub CLI operations — issues, PRs, releases | DevOps, Project Manager |
| **Using Git Worktrees** | `devops/using-git-worktrees/` | Isolated git worktrees with smart directory selection | — |

## Docs (7 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Architecture Document** | `docs/architecture-document/` | Generate enterprise-grade HLD/LLD documents (DOCX/PPTX) | — (via `/generate-hld-lld` prompt) |
| **Code Documentation** | `docs/code-documentation/` | API docs, README files, inline comments, tech guides | — |
| **Doc Co-authoring** | `docs/doc-coauthoring/` | Structured workflow for co-authoring documentation | — |
| **Documentation Analyzer** | `docs/documentation-analyzer/` | Analyze codebases, explain functionality, generate docs | Code Reviewer, Mentor, Plan, PRD, Project Manager, Prompt Engineer |
| **Naming Analyzer** | `docs/naming-analyzer/` | Suggest better variable, function, and class names | — |
| **PRD to Code** | `docs/prd-to-code/` | Transform PRD documents into working code (6-phase) | PRD |
| **Writing Plans** | `docs/writing-plans/` | Multi-step task planning before touching code | Plan |

## Frontend (12 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Brand Guidelines** | `frontend/brand-guidelines/` | Apply brand colors and typography consistently | UX Designer |
| **Canvas Design** | `frontend/canvas-design/` | Create visual art in PNG and PDF documents | — |
| **Frontend Design** | `frontend/frontend-design/` | Production-grade frontend interfaces with high quality | UX Designer |
| **Mockup** | `frontend/mockup/` | Framework-aware UI mockups with feasibility checks | Architect, UX Designer |
| **React Best Practices** | `frontend/react-best-practices/` | Modern React hooks, component patterns, state mgmt | — |
| **React Dev** | `frontend/react-dev/` | Type-safe React 18-19 patterns, generic components | — |
| **React useEffect** | `frontend/react-useeffect/` | When NOT to use Effect — official best practices | — |
| **Streamlit Dev** | `frontend/streamlit-dev/` | Production Streamlit dashboards with caching, theming | Implement, Streamlit Dev |
| **Streamlit Animate** | `frontend/streamlit-animate/` | Enterprise-safe animations — hover effects, skeletons | — |
| **Theme Factory** | `frontend/theme-factory/` | 10 pre-set themes with colors/fonts for slides, docs | UX Designer |
| **UI Review** | `frontend/ui-review/` | Review UI against design, WCAG 2.2 AA, brand guidelines | Accessibility, Frontend Dev, Implement, Streamlit Dev, UX Designer |
| **UX Design** | `frontend/ux-design/` | Brand color system and accessibility standards | — |

## Media (12 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Algorithmic Art** | `media/algorithmic-art/` | p5.js algorithmic art with seeded randomness | — |
| **Artifacts Builder** | `media/artifacts-builder/` | Multi-component HTML artifacts (React, Tailwind, shadcn) | — |
| **Draw.io** | `media/draw-io/` | .drawio XML editing, PNG conversion, layout adjustment | Architect |
| **Excalidraw** | `media/excalidraw/` | Brand-themed Excalidraw diagrams | — |
| **Image Enhancer** | `media/image-enhancer/` | Improve screenshot quality — resolution, sharpness | — |
| **Mermaid Diagrams** | `media/mermaid-diagrams/` | Class, sequence, flowchart, ERD, C4, state, gantt | — |
| **NotebookLM** | `media/notebooklm/` | Query Google NotebookLM for source-grounded answers | — |
| **PlantUML** | `media/plantuml/` | Brand-themed PlantUML diagrams | — |
| **SVG Create** | `media/svg-create/` | Brand-themed SVG diagrams with accessible design | Implement, SVG Diagram |
| **Slack GIF Creator** | `media/slack-gif-creator/` | Animated GIFs optimized for Slack constraints | — |
| **Video Downloader** | `media/video-downloader/` | Download videos for offline viewing/editing | — |
| **YouTube Transcript** | `media/youtube-transcript/` | Extract YouTube captions/subtitles | — |

## Productivity (11 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Competitive Ads** | `productivity/competitive-ads-extractor/` | Extract/analyze competitor ads from ad libraries | — |
| **Content Research** | `productivity/content-research-writer/` | High-quality content with research and citations | — |
| **Domain Brainstormer** | `productivity/domain-name-brainstormer/` | Creative domain name ideas + availability check | — |
| **GitHub Issues** | `productivity/github-issues/` | Well-structured GitHub issues with labels, acceptance criteria | PRD, Project Manager |
| **Internal Comms** | `productivity/internal-comms/` | Status reports, newsletters, incident reports | — |
| **Invoice Organizer** | `productivity/invoice-organizer/` | Organize invoices and receipts for tax prep | — |
| **Jira Issues** | `productivity/jira-issues/` | Create/manage Jira issues from natural language | — |
| **Job Application** | `productivity/job-application/` | Tailored cover letters and applications | — |
| **Lead Research** | `productivity/lead-research-assistant/` | Identify high-quality leads for business development | — |
| **Meeting Insights** | `productivity/meeting-insights-analyzer/` | Analyze meeting transcripts for patterns and feedback | — |
| **Raffle Winner** | `productivity/raffle-winner-picker/` | Random winner selection from lists/spreadsheets | — |

## Testing (4 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Playwright** | `testing/playwright/` | Complete browser automation with auto-detection | Tester |
| **QA Regression** | `testing/qa-regression/` | Reusable regression test suites — login, dashboard, users | — |
| **TDD Workflow** | `testing/tdd-workflow/` | Red-green-refactor cycle for test-driven development | Tester |
| **UI Testing** | `testing/ui-testing/` | Automated Playwright UI tests for Streamlit/web apps | Accessibility, Frontend Dev, Tester, UX Designer |

## Workflow (11 skills)

| Skill | Path | Description | Used By |
|-------|------|-------------|---------|
| **Asking Questions** | `workflow/asking-questions/` | Clarify requirements before implementing | — |
| **Best Practices** | `workflow/best-practices/` | Transform vague prompts into optimized AI prompts | — |
| **Context Handoff** | `workflow/context-handoff/` | Preserve context between sessions (emergency) | Architect, Implement |
| **File Organizer** | `workflow/file-organizer/` | Organize files, find duplicates, suggest structure | — |
| **Intent Writer** | `workflow/intent-writer/` | Structure freetext ideas into formal Intent Documents | Prompt Engineer |
| **Onboard Project** | `workflow/onboard-project/` | Bootstrap AI config — copilot-instructions, project-config | — (via `/onboarding` prompt) |
| **Receiving Code Review** | `workflow/receiving-code-review/` | Process code review feedback with technical rigor | — |
| **Requesting Code Review** | `workflow/requesting-code-review/` | Verify work before merging | — |
| **Skill Creator** | `workflow/skill-creator/` | Guide for creating new skills | — |
| **Verification Loop** | `workflow/verification-loop/` | Lint, test, type-check, review cycle | Tester |
| **Writing Skills** | `workflow/writing-skills/` | Create, edit, verify skills before deployment | — |

---

## Additional Skill Categories (Not Scoped to Core Pipeline)

These categories contain specialized or external skills. See `_registry.md` for full details:

| Category | Skills | Purpose |
|----------|--------|---------|
| **Document Skills** | docx, pptx, pdf, xlsx generators | Generate formatted documents |
| **AWS** | agentic-ai, cdk, cost-ops, serverless-eda | AWS-specific patterns |
| **Cloudflare** | ai-agent, mcp-server | Edge computing patterns |
| **Brainstorming** | brainstorming | Structured ideation |
| **Game-Changing Features** | game-changing-features | Feature innovation |
| **Meta** | agent-md-refactor | Agent file maintenance |

---

## Quick Stats

| Metric | Count |
|--------|-------|
| Total skills | 88 |
| Categories | 11 core + 6 additional |
| Skills used by agents | 28 |
| Skills available on-demand | 60 |
| Skills per agent (avg) | 3-4 |
| Most-referenced skill | code-explainer (8 agents) |
