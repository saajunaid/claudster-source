---
description: "Set up a new project from scratch with AI development resources, virtual environment, and project structure"
---

# Project Setup Prompt

## Copy-Paste Template

```
Set up a new project for me:

- Project name: [my-project-name]
- Language/framework: [e.g., Python/Streamlit, Python/FastAPI, Node.js/React]
- Database: [e.g., SQL Server, PostgreSQL, SQLite, none]
- Description: [Brief description of what the project will do]
- Location: [parent folder path where project should be created]

Please:
1. Create the project structure
2. Set up a virtual environment
3. Install base dependencies
4. Add AI resources (agents, instructions, skills)
5. Create starter config files (.env.example, .gitignore)
6. Initialize Git repository
```

## Purpose

Complete guide for setting up a new project from start to finish. Use this prompt to get step-by-step instructions for creating a properly configured project.

## When to Use

- Starting a brand new project
- Setting up your development environment for the first time
- Onboarding to the development framework
- Need a quick reference for setup commands

## Quick Setup Commands

### Create a New Project

```powershell
# Navigate to your project folder (replace with your actual path)
cd <path-to-project>

# Create the project (replace 'my-project' with your project name and path)
.\new-project.ps1 -Name "my-project" -Path "<parent-folder-for-projects>"

# Open in your editor (e.g. VS Code, Cursor)
cd <parent-folder-for-projects>\my-project
code .   # or: cursor .   (depending on your IDE)
```

### Set Up Development Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create environment config
Copy-Item .env.example .env
# Edit .env with your values
```

### Verify Setup

```powershell
# Check AI resources are synced
Get-ChildItem agents -Name

# Check Python environment
python --version
pip list

# Run the app
streamlit run src\app.py
```

## Complete Setup Walkthrough

### Phase 1: One-Time Setup (Per Developer Machine)

These steps only need to be done once:

#### 1.1 Prerequisites

```powershell
# Verify Python (3.11+)
python --version

# Verify Node.js (18+)
node --version

# Verify Git
git --version
```

#### 1.2 Install MCP Servers

```powershell
cd <path-to-mcp-servers>
.\setup-mcp.ps1

# IMPORTANT: Restart VS Code after this
```

#### 1.3 Configure VS Code

Ensure these extensions are installed:
- GitHub Copilot
- Python
- Pylance

---

### Phase 2: Create New Project

#### 2.1 Run Project Script

```powershell
cd <path-to-project-scripts>
.\new-project.ps1 -Name "customer-complaints" -Path "<parent-folder-for-projects>"
```

This creates:
```
E:\Projects\customer-complaints\
├──         # AI resources (17 agents, 14 instructions, etc.)
├── .vscode/          # VS Code settings
├── docs/
│   ├── prd/prd.md    # PRD template
│   └── developer-handbook.md
├── src/
│   ├── app.py        # Streamlit entry point
│   ├── config.py     # Configuration
│   ├── models/       # Data models
│   ├── services/     # Business logic
│   └── utils/        # Utilities
├── tests/            # Test files
├── data/             # Data files
├── sync-ai-resources.ps1
├── requirements.txt
├── .env.example
└── README.md
```

#### 2.2 Set Up Environment

```powershell
cd <parent-folder-for-projects>\customer-complaints
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

#### 2.3 Configure .env

Edit `.env` with your actual values:

```env
# Application
APP_NAME=customer-complaints
DEBUG=True

# Database (MySQL for development)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=customer_complaints

# Streamlit
STREAMLIT_SERVER_PORT=8501
```

---

### Phase 3: Start Development

#### 3.1 Write the PRD

In VS Code Copilot Chat:
```
@prd Create a PRD for a customer complaints analytics dashboard. 
The team needs to track complaint trends, resolution times, and agent performance.
```

Save the output to `docs/prd/prd.md`.

#### 3.2 Design Architecture

```
Ask the Architect agent (or paste architect.agent.md context): "Based on docs/prd/prd.md, design the system architecture."
```

#### 3.3 Start Coding

Use the appropriate agents:
```
@sql-expert Create the database schema for customer complaints
@streamlit-developer Build the main dashboard page
@backend-developer Create the data access layer
```

---

## Checklists

### Pre-Project Checklist

- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] VS Code with GitHub Copilot
- [ ] MySQL 8.0 installed
- [ ] MCP servers configured (one-time)

### Project Creation Checklist

- [ ] Project created with `scripts/new-project.ps1`
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] `.env` configured
- [ ] AI resources verified in ``
- [ ] Git initialized

### Ready to Code Checklist

- [ ] PRD written in `docs/prd/prd.md`
- [ ] Architecture designed
- [ ] Database schema planned
- [ ] First `streamlit run src/app.py` works

---

## Troubleshooting

### "Agent not found" in Copilot

```powershell
# Re-sync AI resources
.\sync-ai-resources.ps1

# Verify they exist
Get-ChildItem agents -Name
```

### Virtual Environment Issues

```powershell
# Remove and recreate
Remove-Item .venv -Recurse -Force
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Streamlit Won't Start

```powershell
# Check you're in the right environment
which python  # Should show .venv path

# Check streamlit is installed
pip show streamlit

# Run with full path
python -m streamlit run src/app.py
```

---

## Related Resources

| Resource | Purpose |
|----------|---------|
| `@project-manager` | Interactive project setup guidance |
| `@plan` | Strategic planning before coding |
| `@prd` | Generate Product Requirements Document |
| `/first-ask` | Comprehensive requirements gathering |
| `developer-handbook.md` | Complete AI resource usage guide |
