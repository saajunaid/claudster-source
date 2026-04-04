# Agent Reference Card

> **22 Custom Agents** across 3 model tiers — print this page for a quick desk reference.
> Updated: 2026-02-19

---

## Claude Opus 4.6 — Deep Reasoning (9 agents)

| Agent | Purpose | Hands Off To | Skills Loaded | Instructions Used |
|-------|---------|-------------|---------------|-------------------|
| **PRD** | Requirements discovery, stakeholder synthesis | Architect, Planner | prd-to-code, documentation-analyzer, github-issues | — |
| **Architect** | System design, trade-offs, architecture decisions | Planner, Implement, PRD, SQL Expert, Data Engineer, Streamlit Dev, SVG Diagram, UX Designer | sql, data-analysis, draw-io, context-handoff | sql, security, performance-optimization, code-review |
| **Planner** | Strategic planning, technical roadmapping (read-only) | Implement, Architect, PRD, Streamlit Dev, Data Engineer, SQL Expert, Prompt Engineer, UX Designer | writing-plans, documentation-analyzer, code-explainer | python, portability, code-review |
| **Code Reviewer** | Quality, security, standards review | Implement, Security Analyst, Janitor, DevOps | refactoring, code-explainer, documentation-analyzer, security-review | code-review, security, python, portability, performance-optimization |
| **Debug** | Root-cause analysis, bug fixing, Planner amendment briefs | Tester, Code Reviewer, Security Analyst, Planner | db-testing, code-explainer, refactoring | testing, python, security |
| **Security Analyst** | Threat modeling, OWASP review, risk analysis | Implement, Architect | security-review | security, code-review, sql, python, performance-optimization |
| **UX Designer** | UX flows, user goals, business constraints (JTBD) | Streamlit Dev, Accessibility, Frontend Dev | ui-review, mockup, frontend-design, brand-guidelines, theme-factory, ui-testing | accessibility, frontend, streamlit |
| **UI/UX Designer** | Design systems, visual identity, component specs | UX Designer, Frontend Dev, Accessibility, Architect | — | — |
| **Prompt Engineer** | Multi-agent workflows, prompt design | Implement, Code Reviewer | documentation-analyzer, code-explainer, intent-writer | — |

## GPT-5.3-Codex — Multi-File Coding (6 agents)

| Agent | Purpose | Hands Off To | Skills Loaded | Instructions Used |
|-------|---------|-------------|---------------|-------------------|
| **Implement** | Full code implementation, refactoring, shipping | Code Reviewer, Tester, Debug, Security Analyst, Planner, DevOps, Prompt Engineer | streamlit-dev, sql, refactoring, code-explainer, data-analysis, git-commit, ui-review, svg-create | security, portability, code-review |
| **Streamlit Developer** | Streamlit UI, app wiring, component integration | Code Reviewer, Tester, Accessibility, Debug | streamlit-dev, ui-review, refactoring, data-analysis, sql | streamlit, plotly-charts, accessibility, frontend, portability, code-review |
| **Frontend Developer** | HTML, CSS, JS, components & pages | Code Reviewer, Accessibility, Debug | ui-review, ui-testing | frontend, accessibility, streamlit, portability, code-review |
| **Data Engineer** | ETL pipelines, data integration | SQL Expert, Security Analyst, Architect, Tester, Debug | data-analysis, data-loader, db-testing | sql, python, testing, security, code-review |
| **SQL Expert** | Query optimization, DB troubleshooting | Data Engineer, Security Analyst, Architect, Tester, Debug | sql, data-analysis, db-testing | sql, mssql-dba, sql-stored-procedures, performance-optimization, python, security, code-review |
| **Tester** | pytest, test strategy, coverage analysis | Debug, Code Reviewer | ui-testing, tdd-workflow, verification-loop, playwright, code-explainer | testing, playwright, python, code-review |

## Claude Sonnet 4.6 — Balanced Speed-Quality (7 agents)

| Agent | Purpose | Hands Off To | Skills Loaded | Instructions Used |
|-------|---------|-------------|---------------|-------------------|
| **DevOps** | CI/CD, Docker, infrastructure | Security Analyst | git-commit, changelog-generator, gh-cli | docker, github-actions, shell, performance-optimization, security, portability |
| **Accessibility** | WCAG 2.2 audit, a11y remediation | Implement, UX Designer, Tester | ui-review, ui-testing | accessibility, frontend, streamlit |
| **Janitor** | Code cleanup, dead code removal | Code Reviewer, Debug | refactoring, security-review, code-explainer | code-review, performance-optimization, python, portability |
| **Mentor** | Teaching, step-by-step explanations | Implement, Debug | code-explainer, documentation-analyzer, refactoring | — |
| **Project Manager** | Work planning, status tracking, GitHub issues | PRD, Planner | github-issues, gh-cli, git-commit, documentation-analyzer | — |
| **SVG Diagram** | Architecture diagrams, visual documentation | Architect | svg-create | — |
| **Mermaid Diagram** | Flowcharts, sequence diagrams, ERDs | Architect | — | — |

---

## Main Pipeline Flow

```
PRD ──► Architect ──► Planner ──► Implement ──► Tester ──► Code Reviewer ──► ✅ DONE
 ◄─iterate──►          ◄─iterate──►                               │
                                            │                      ├──► Security Analyst
                                            ├──► Debug ──► Planner    ├──► DevOps
                                            └──► Tester            └──► Janitor
```

## Specialist Branches

| Branch | Flow | Triggered From |
|--------|------|----------------|
| **UX/Frontend** | UX Designer → Frontend Dev → Accessibility | Architect, Planner |
| **Streamlit** | Streamlit Dev → Accessibility | Architect, Planner |
| **Data** | SQL Expert ↔ Data Engineer | Architect |
| **Security** | Security Analyst → Implement | Code Reviewer |
| **Ops** | DevOps → Security Analyst | Code Reviewer, Implement |
| **Debug** | Debug → Planner (amend) | Implement |

## Prompts (Slash Commands)

| Command | Purpose | Wires To |
|---------|---------|----------|
| `/planner` | Create phased execution plan | Planner agent + writing-plans skill |
| `/code-review` | Start code review | Code Reviewer agent |
| `/tdd` | Test-driven development | Tester agent + tdd-workflow skill |
| `/verify` | Verify implementation | Tester agent + verification-loop skill |
| `/test-coverage` | Analyze test coverage | Tester agent |
| `/pytest-coverage` | pytest coverage report | Tester agent |
| `/sql-optimization` | Optimize SQL queries | SQL Expert agent |
| `/sql-review` | Review SQL code | SQL Expert agent |
| `/dockerfile` | Create/review Dockerfile | DevOps agent |
| `/performance-optimization` | Performance audit | UX Designer / Code Reviewer |
| `/review-and-refactor` | Review + refactor pass | Code Reviewer / Janitor |
| `/generate-hld-lld` | Enterprise HLD/LLD docs | architecture-document skill |
| `/context-handoff` | Emergency context save | context-handoff skill |
| `/adr` | Architecture Decision Record | Project Manager |

## 7 Universal Protocols (All Agents)

| # | Protocol | Rule |
|---|----------|------|
| 1 | **Scope Boundary** | Stay in your lane — don't do other agents' work |
| 2 | **Artifact Output** | Write to `agent-docs/{your-folder}/` |
| 3 | **Chain-of-Origin** | Preserve `intent_id` across handoffs |
| 4 | **Approval Gates** | Pause before destructive operations |
| 5 | **Escalation** | Escalate blockers to human or appropriate agent |
| 6 | **Bootstrap Check** | Read `project-config.md` first |
| 7 | **Context Priority** | Chat → Files → Skills → Instructions |
