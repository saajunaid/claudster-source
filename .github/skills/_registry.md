# Skills Registry

> **123 skills** across 10 categories — full reconciliation against disk state (`vmie/` excluded).  
> Load a skill by reading its `SKILL.md`. See `project-config.md` for project-specific placeholder values.

---

## Skills by Category

### Cloud

| Skill | Path | When to Use |
|-------|------|-------------|
| AWS Agentic AI | `cloud/aws-agentic-ai/` | Building agentic AI systems on AWS Bedrock AgentCore (Gateway, Runtime, Memory, Identity) |
| AWS CDK Development | `cloud/aws-cdk-development/` | Building cloud infrastructure as code with AWS CDK in TypeScript/Python |
| AWS Cost Operations | `cloud/aws-cost-operations/` | AWS cost optimization, monitoring, and operational best practices |
| AWS Serverless EDA | `cloud/aws-serverless-eda/` | Event-driven architectures using Lambda, API Gateway, SQS, SNS, Step Functions |
| AI Agent on Cloudflare | `cloud/building-ai-agent-on-cloudflare/` | Building stateful AI agents on Cloudflare Workers with WebSockets and tool integration |
| MCP Server on Cloudflare | `cloud/building-mcp-server-on-cloudflare/` | Building remote MCP servers on Cloudflare Workers with OAuth authentication |

### Coding

| Skill | Path | When to Use |
|-------|------|-------------|
| Anchor Review | `coding/anchor-review/` | Single-model adversarial review with 3-lens analysis and confidence scoring |
| API Client Patterns | `coding/api-client-patterns/` | Typed fetch wrappers, TanStack Query, tRPC, and OpenAPI codegen |
| API Design | `coding/api-design/` | REST/GraphQL API design — naming, pagination, versioning, error responses, OpenAPI |
| Architecture Design | `coding/architecture-design/` | Designing system architecture with C4 diagrams and layered patterns |
| Backend Development | `coding/backend-development/` | Backend API development patterns and microservices |
| Backend-to-Frontend Handoff | `coding/backend-to-frontend-handoff/` | Generating API handoff docs for frontend integration |
| Caching Patterns | `coding/caching-patterns/` | Caching strategies for Streamlit/FastAPI applications |
| Codebase Audit | `coding/codebase-audit/` | Auditing unfamiliar codebases — 20 audit areas, 6-step method, findings report |
| Code Explainer | `coding/code-explainer/` | Explaining code with diagrams and analogies |
| Code Review | `coding/code-review/` | Performing code reviews for quality, security, and performance |
| Error Handling | `coding/error-handling/` | Error hierarchies, retry logic, error boundaries, and logging strategies |
| FastAPI Dev | `coding/fastapi-dev/` | Building FastAPI backends with standard patterns |
| JavaScript/TypeScript | `coding/javascript-typescript/` | JS/TS development patterns and best practices |
| LLM Application Dev | `coding/llm-application-dev/` | Building LLM-powered applications with prompt engineering and RAG |
| MCP Builder | `coding/mcp-builder/` | Building MCP (Model Context Protocol) servers |
| Observability | `coding/observability/` | Structured logging, distributed tracing, metrics, health checks, and error tracking |
| Python | `coding/python/` | Python development patterns and best practices |
| Refactoring | `coding/refactoring/` | Safe code refactoring while maintaining behavior |
| Security Review | `coding/security-review/` | Security review using OWASP Top 10 + cloud security best practices |
| SQL | `coding/sql/` | Writing optimized SQL queries (database-agnostic) |

### Data

| Skill | Path | When to Use |
|-------|------|-------------|
| Data Analysis | `data/data-analysis/` | Analyzing datasets with 5-phase methodology |
| Data Loader | `data/data-loader/` | Loading data from Excel, JSON, CSV into databases |
| Data Validation | `data/data-validation/` | Data quality checks, Pydantic validation, SQL constraints, and data contracts |
| Database Design | `data/database-design/` | Designing database schemas |
| DB Testing | `data/db-testing/` | Testing database connectivity and queries |
| Schema Migration | `data/schema-migration/` | Migrating app data access layer between schema versions (mapping, parity testing, query translation) |

### DevOps

| Skill | Path | When to Use |
|-------|------|-------------|
| Changelog Generator | `devops/changelog-generator/` | Generating changelogs from git commits |
| CI/CD Pipeline | `devops/ci-cd-pipeline/` | Pipeline design for GitHub Actions and Azure DevOps — quality gates, environments, caching |
| Deploy Local | `devops/deploy-local/` | Commit on dev, push to Gitea, monitor prod pull/build/deploy, and remediate CI/CD failures end-to-end |
| GitHub CLI | `devops/gh-cli/` | GitHub CLI operations (PRs, issues, releases, actions) |
| Git Commit | `devops/git-commit/` | Writing conventional commit messages |
| Monorepo | `devops/monorepo/` | pnpm workspaces + Turborepo for monorepo CI/CD and shared packages |
| Windows Deployment | `devops/windows-deployment/` | Deploy FastAPI + React/Vite apps to Windows Server with NSSM, nginx reverse proxy, and Gitea |
| Using Git Worktrees | `devops/using-git-worktrees/` | Managing parallel branches with git worktrees |

### Docs

| Skill | Path | When to Use |
|-------|------|-------------|
| Architecture Document | `docs/architecture-document/` | Generating enterprise-grade HLD/LLD documents from Architecture.md |
| Code Documentation | `docs/code-documentation/` | Writing API docs, README files, and inline comments |
| Doc Co-authoring | `docs/doc-coauthoring/` | Collaborative document editing workflow |
| Documentation Analyzer | `docs/documentation-analyzer/` | Analyzing codebases and generating documentation |
| DOCX | `docs/document-skills/docx/` | Word documents with tracked changes and OOXML |
| PDF | `docs/document-skills/pdf/` | PDF manipulation with pypdf, pdfplumber, reportlab |
| PPTX | `docs/document-skills/pptx/` | PowerPoint creation/editing with html2pptx |
| XLSX | `docs/document-skills/xlsx/` | Spreadsheets with financial model standards |
| Naming Analyzer | `docs/naming-analyzer/` | Suggesting better variable, function, and class names |
| PRD to Code | `docs/prd-to-code/` | Converting PRDs to application code (6-phase process) |
| Technical Writing | `docs/technical-writing/` | READMEs, API docs, ADRs, runbooks, and developer guides |
| Writing Plans | `docs/writing-plans/` | Creating phased execution plans before implementation |

### Frontend

| Skill | Path | When to Use |
|-------|------|-------------|
| Algorithmic Art | `frontend/algorithmic-art/` | Generating p5.js algorithmic artwork with seeded randomness |
| Artifacts Builder | `frontend/artifacts-builder/` | Building multi-component HTML artifacts (React, Tailwind, shadcn) |
| Banner Design | `frontend/banner-design/` | Banners for social media, ads, website heroes, and print (22 styles, multi-platform) |
| Brand Design | `frontend/brand-design/` | Logo generation (55 styles), corporate identity program, icon design, social photos |
| Brand Guidelines | `frontend/brand-guidelines/` | Applying brand colors and typography consistently |
| Brand Voice | `frontend/brand-voice/` | Brand voice, visual identity, messaging frameworks, and brand consistency |
| Canvas Design | `frontend/canvas-design/` | Creating canvas-based visual art in PNG and PDF |
| CSS Architecture | `frontend/css-architecture/` | Design token hierarchy, Tailwind config, CSS Modules, responsive and animation patterns |
| Design System Tokens | `frontend/design-system-tokens/` | Three-layer token architecture (primitive → semantic → component), CSS variables, spacing/typography scales |
| Frontend Design | `frontend/frontend-design/` | Production-grade frontend interfaces |
| Mockup | `frontend/mockup/` | Framework-aware UI mockups with feasibility checks |
| Next.js App Router | `frontend/nextjs-app-router/` | Next.js 13+ App Router, Server Components, Server Actions, Route Handlers |
| Premium React | `frontend/premium-react/` | High-quality animated React UIs with Framer Motion, GSAP, and Tailwind |
| React Best Practices | `frontend/react-best-practices/` | Modern React hooks, component patterns, and state management |
| Responsive Mobile Native | `frontend/responsive-mobile-native/` | Converting desktop web apps to mobile-native feel: breakpoints, navigation transformation, PWA setup, touch rules, bottom sheets |
| React Dev | `frontend/react-dev/` | Type-safe React 18-19 patterns and TypeScript integration |
| React useEffect | `frontend/react-useeffect/` | When NOT to use Effect — official React best practices |
| shadcn/Radix | `frontend/shadcn-radix/` | shadcn/ui component system, Radix primitives, theming, and form patterns |
| Slides | `frontend/slides/` | Strategic HTML presentations with Chart.js, design tokens, and copywriting formulas |
| Streamlit Animate | `frontend/streamlit-animate/` | Enterprise-safe animations and micro-interactions for Streamlit apps |
| Streamlit Dev | `frontend/streamlit-dev/` | Production Streamlit dashboards with caching and theming |
| Theme Factory | `frontend/theme-factory/` | Creating and managing UI themes with pre-set color/font combos |
| UI Review | `frontend/ui-review/` | Reviewing UI against design, WCAG 2.2 AA, and brand guidelines |
| UI Styling Patterns | `frontend/ui-styling-patterns/` | shadcn/ui + Tailwind CSS utility styling, accessible components, dark mode, and canvas visuals |
| UI/UX Intelligence | `frontend/ui-ux-intelligence/` | Data-backed design decisions: 161 color palettes, 57 font pairings, 99 UX guidelines, 25 chart types |
| UX Design | `frontend/ux-design/` | Designing user experiences with brand color system and accessibility standards |
| Warm Editorial UI | `frontend/warm-editorial-ui/` | Warm editorial design system — cream surfaces, Syne + DM Sans typography, multi-layer shadows, generous radius |
| Webapp Development | `frontend/webapp-development/` | End-to-end web application development workflow |
| Word Cloud | `frontend/word-cloud/` | Generate static or animated word clouds from text/files with theming and shape masking |

### Testing

| Skill | Path | When to Use |
|-------|------|-------------|
| Component Testing | `testing/component-testing/` | Vitest + Testing Library for React component unit and integration testing |
| Performance Testing | `testing/performance-testing/` | Load testing, benchmarking, and profiling with Locust, k6, pytest-benchmark |
| Playwright | `testing/playwright/` | Browser automation and E2E testing with auto-detection |
| TDD Workflow | `testing/tdd-workflow/` | Red-green-refactor cycle for test-driven development |
| Test Strategy | `testing/test-strategy/` | Test planning, risk-based prioritisation, coverage goals, and test pyramids |
| UI Testing | `testing/ui-testing/` | Automated Playwright UI tests for Streamlit and web apps |

### Workflow

| Skill | Path | When to Use |
|-------|------|-------------|
| Agent MD Refactor | `workflow/agent-md-refactor/` | Refactoring bloated agent instruction files to follow progressive disclosure principles |
| Agent Orchestration | `workflow/agent-orchestration/` | End-to-end multi-agent pipeline from spec to production |
| Asking Questions | `workflow/asking-questions/` | When and how to ask clarifying questions before implementing |
| Best Practices | `workflow/best-practices/` | Transform vague prompts into optimised AI prompts |
| Brainstorming | `workflow/brainstorming/` | Structured ideation before implementing features or changes |
| Context Curator | `workflow/context-curator/` | Compress and prioritise codebase context before feeding reasoning agents |
| Context Handoff | `workflow/context-handoff/` | Preserving context between sessions (emergency handoff) |
| Developer Growth | `workflow/developer-growth-analysis/` | Analyzing coding patterns and curating personalized learning resources |
| File Organizer | `workflow/file-organizer/` | Organizing files, finding duplicates, suggesting structure |
| Game-Changing Features | `workflow/game-changing-features/` | Finding 10x product opportunities and high-leverage improvements |
| Golden Plan | `workflow/golden-plan/` | Comprehensive, evidence-gated implementation plans for large builds (8+ phases, full-stack, complex data binding) |
| Intent Writer | `workflow/intent-writer/` | Structuring freetext ideas into formal Intent Documents for the agent pipeline |
| Onboard Project | `workflow/onboard-project/` | Bootstrapping AI configuration (copilot-instructions.md, project-config.md) |
| Pipeline State | `workflow/pipeline-state/` | Reading and writing `.github/pipeline-state.json` for pipeline tracking |
| Receiving Code Review | `workflow/receiving-code-review/` | Processing code review feedback with technical rigor |
| Requesting Code Review | `workflow/requesting-code-review/` | Verifying work and preparing it for review before merging |
| Verification Loop | `workflow/verification-loop/` | Systematic lint, test, type-check, and review cycle |
| Data Contract Pipeline | `workflow/data-contract-pipeline/` | Build/audit typed data pipelines from source to frontend with drift detection |
| Preflight | `workflow/preflight/` | Plan-vs-codebase validation — verifies API contracts, types, fields, dependencies, and paths before implementation |

### Media

| Skill | Path | When to Use |
|-------|------|-------------|
| Draw.io | `media/draw-io/` | .drawio XML editing, PNG conversion, layout adjustment, and AWS icons |
| Excalidraw | `media/excalidraw/` | Brand-themed Excalidraw diagrams for documentation |
| Image Enhancer | `media/image-enhancer/` | Improving screenshot quality — resolution, sharpness, contrast |
| Mermaid Diagrams | `media/mermaid-diagrams/` | Class, sequence, flowchart, ERD, C4, state, and gantt diagrams |
| NotebookLM | `media/notebooklm/` | Querying Google NotebookLM for source-grounded answers |
| PlantUML | `media/plantuml/` | Brand-themed PlantUML diagrams for documentation |
| Slack GIF Creator | `media/slack-gif-creator/` | Creating animated GIFs optimized for Slack |
| SVG Create | `media/svg-create/` | Brand-themed SVG diagrams with accessible design |
| Video Downloader | `media/video-downloader/` | Downloading and processing video for offline viewing |
| YouTube Transcript | `media/youtube-transcript/` | Extracting YouTube captions and subtitles |

### Productivity

| Skill | Path | When to Use |
|-------|------|-------------|
| Competitive Ads | `productivity/competitive-ads-extractor/` | Extracting and analyzing competitor ads from ad libraries |
| Content Research | `productivity/content-research-writer/` | Researching and writing high-quality content with citations |
| Domain Brainstormer | `productivity/domain-name-brainstormer/` | Brainstorming creative domain names and checking availability |
| GitHub Issues | `productivity/github-issues/` | Writing well-structured GitHub issues with acceptance criteria |
| Internal Comms | `productivity/internal-comms/` | Writing status reports, newsletters, and incident reports |
| Invoice Organizer | `productivity/invoice-organizer/` | Organizing invoices and receipts for tax preparation |
| Jira Issues | `productivity/jira-issues/` | Creating and managing Jira tickets from natural language |
| Job Application | `productivity/job-application/` | Preparing tailored cover letters and job applications |
| Lead Research | `productivity/lead-research-assistant/` | Identifying high-quality leads for business development |
| Meeting Insights | `productivity/meeting-insights-analyzer/` | Analyzing meeting notes and transcripts for patterns and feedback |
| Raffle Winner | `productivity/raffle-winner-picker/` | Random winner selection from lists and spreadsheets |
