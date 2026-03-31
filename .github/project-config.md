# Project Configuration

Copy this file to your project's `.github/` folder. Set the profile and you're done.

---

## Step 1: Set Your Profile

| Setting | Value |
|---------|-------|
| **profile** | `` |

> **For profiled projects:** Set `profile` to the matching profile name below. Agents will use that profile's values for all `<PLACEHOLDER>` tokens.
>
> **For new projects:** Set `profile` to blank, then fill in Step 2 with your project values.

### Which profile strategy should I use?

- **Best default:** `org-project` (e.g. `org1-telecom-ops`) for stable, real projects
- **Use stack profiles** (e.g. `streamlit-mssql-enterprise`) for quick starts, prototypes, and new teams
- Prefer profiles that reflect **long-lived business context** over temporary experiments

### Available profile options (quick copy)

**Project/stack profiles:**

`streamlit-mssql-enterprise`, `streamlit-postgres-analytics`, `fastapi-postgres-service`, `fastapi-mssql-internal-api`, `react-node-saas`, `react-fastapi-vite-mssql`, `nextjs-postgres-saas`, `data-pipeline-python-mssql`, `data-pipeline-python-snowflake`, `ml-training-python-pytorch`, `mcp-server-python`, `vscode-extension-typescript`, `telecom-appointment-intelligence`

**Organization profiles (dummy names):**

`org1-telecom-ops`, `org2-finance-ops`, `org3-healthcare-ops`

To set one quickly, replace this row value:

`| **profile** | `` |`

with, for example:

`| **profile** | `telecom-appointment-intelligence` |`

---

## Step 2: Project Values (only if profile is blank)

| Placeholder | Your Value |
|-------------|------------|
| `<ORG_NAME>` | |
| `<BRAND_PRIMARY>` | |
| `<BRAND_DARK>` | |
| `<BRAND_LIGHT>` | |
| `<DB_TYPE>` | |
| `<DEPLOY_ENV>` | |
| `<LOGGING_LIB>` | |
| `<SHARED_LIBS>` | |

---

## Step 3: Project Structure

Describe your project's directory layout so agents don't guess:

```
src/
├── main entry point
├── pages or views
├── components
├── services
└── tests
```

---

## Step 4: Key Conventions

| Convention | Value |
|------------|-------|
| Query config file | *(path to external SQL query file, e.g. `src/queries.yaml`)* |
| App entry command | *(e.g. `streamlit run src/Home.py`)* |
| Test command | *(e.g. `pytest tests/ --tb=short -q`)* |
| Lint command | *(e.g. `ruff check src/`)* |

---

## Profile Definitions

Add project profiles here. Each profiled project adds its own section.

<!--
### my-project

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | My Organisation |
| `<BRAND_PRIMARY>` | #FF0000 |
| `<BRAND_DARK>` | #1A1A1A |
| `<BRAND_LIGHT>` | #F8F8F8 |
| `<DB_TYPE>` | PostgreSQL |
| `<DEPLOY_ENV>` | AWS ECS |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | libs/core |
-->

### streamlit-mssql-enterprise

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Enterprise Team |
| `<BRAND_PRIMARY>` | #1F6FEB |
| `<BRAND_DARK>` | #111827 |
| `<BRAND_LIGHT>` | #F9FAFB |
| `<DB_TYPE>` | SQL Server |
| `<DEPLOY_ENV>` | Streamlit |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### streamlit-postgres-analytics

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Analytics Team |
| `<BRAND_PRIMARY>` | #0EA5E9 |
| `<BRAND_DARK>` | #0B2545 |
| `<BRAND_LIGHT>` | #F9FAFB |
| `<DB_TYPE>` | PostgreSQL |
| `<DEPLOY_ENV>` | Streamlit |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### fastapi-postgres-service

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Platform Team |
| `<BRAND_PRIMARY>` | #0EA5E9 |
| `<BRAND_DARK>` | #0F172A |
| `<BRAND_LIGHT>` | #F8FAFC |
| `<DB_TYPE>` | PostgreSQL |
| `<DEPLOY_ENV>` | FastAPI |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### fastapi-mssql-internal-api

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Internal Platform |
| `<BRAND_PRIMARY>` | #2563EB |
| `<BRAND_DARK>` | #1E293B |
| `<BRAND_LIGHT>` | #F8FAFC |
| `<DB_TYPE>` | SQL Server |
| `<DEPLOY_ENV>` | FastAPI |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### react-node-saas

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Product Team |
| `<BRAND_PRIMARY>` | #7C3AED |
| `<BRAND_DARK>` | #1F2937 |
| `<BRAND_LIGHT>` | #F9FAFB |
| `<DB_TYPE>` | PostgreSQL |
| `<DEPLOY_ENV>` | React + Node |
| `<LOGGING_LIB>` | pino |
| `<SHARED_LIBS>` | packages/shared |

### react-fastapi-vite-mssql

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Internal Team |
| `<BRAND_PRIMARY>` | #2563EB |
| `<BRAND_DARK>` | #1E293B |
| `<BRAND_LIGHT>` | #F8FAFC |
| `<DB_TYPE>` | SQL Server |
| `<DEPLOY_ENV>` | React + FastAPI |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

#### Stack Details

| Component | Technology |
|-----------|-----------|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Routing | TanStack Router |
| State | React Query (server), Zustand (client) |
| Components | shadcn/ui (Radix primitives) |
| Backend API | FastAPI, uvicorn |
| ORM | SQLAlchemy (async), aioodbc |
| Migrations | Alembic |
| Auth | JWT + bcrypt (local SQLite user store) |
| Database | SQL Server (MSSQL) |
| Dependency mgmt | pyproject.toml (Python), package.json (JS) |

#### Key Conventions

| Convention | Value |
|------------|-------|
| Query config file | N/A — SQL via SQLAlchemy ORM or repository layer |
| App entry (backend) | `uvicorn src.api.main:app --reload` |
| App entry (frontend) | `cd frontend && npm run dev` |
| Test command | `pytest tests/` |
| Lint command | `ruff check src/` |

### nextjs-postgres-saas

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Product Team |
| `<BRAND_PRIMARY>` | #4F46E5 |
| `<BRAND_DARK>` | #111827 |
| `<BRAND_LIGHT>` | #F9FAFB |
| `<DB_TYPE>` | PostgreSQL |
| `<DEPLOY_ENV>` | Next.js |
| `<LOGGING_LIB>` | pino |
| `<SHARED_LIBS>` | packages/shared |

### data-pipeline-python-mssql

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Data Engineering |
| `<BRAND_PRIMARY>` | #0F766E |
| `<BRAND_DARK>` | #134E4A |
| `<BRAND_LIGHT>` | #F0FDFA |
| `<DB_TYPE>` | SQL Server |
| `<DEPLOY_ENV>` | Python Batch |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### data-pipeline-python-snowflake

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Data Engineering |
| `<BRAND_PRIMARY>` | #06B6D4 |
| `<BRAND_DARK>` | #164E63 |
| `<BRAND_LIGHT>` | #ECFEFF |
| `<DB_TYPE>` | Snowflake |
| `<DEPLOY_ENV>` | Python Batch |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### ml-training-python-pytorch

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | ML Team |
| `<BRAND_PRIMARY>` | #F97316 |
| `<BRAND_DARK>` | #7C2D12 |
| `<BRAND_LIGHT>` | #FFF7ED |
| `<DB_TYPE>` | PostgreSQL |
| `<DEPLOY_ENV>` | Python + GPU |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### mcp-server-python

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | AI Platform |
| `<BRAND_PRIMARY>` | #7C3AED |
| `<BRAND_DARK>` | #2E1065 |
| `<BRAND_LIGHT>` | #F5F3FF |
| `<DB_TYPE>` | SQLite |
| `<DEPLOY_ENV>` | MCP Server |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### vscode-extension-typescript

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Developer Tools |
| `<BRAND_PRIMARY>` | #2563EB |
| `<BRAND_DARK>` | #1E3A8A |
| `<BRAND_LIGHT>` | #EFF6FF |
| `<DB_TYPE>` | N/A |
| `<DEPLOY_ENV>` | VS Code Extension |
| `<LOGGING_LIB>` | console |
| `<SHARED_LIBS>` | src/shared |

### telecom-appointment-intelligence

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Telecom Operations |
| `<BRAND_PRIMARY>` | #5A2D82 |
| `<BRAND_DARK>` | #3B022A |
| `<BRAND_LIGHT>` | #F8F9FA |
| `<DB_TYPE>` | SQL Server |
| `<DEPLOY_ENV>` | FastAPI + React + Docker Compose |
| `<LOGGING_LIB>` | structlog |
| `<SHARED_LIBS>` | backend/app/shared |

### org1-telecom-ops

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Org1 |
| `<BRAND_PRIMARY>` | #E30613 |
| `<BRAND_DARK>` | #3B022A |
| `<BRAND_LIGHT>` | #F8F9FA |
| `<DB_TYPE>` | SQL Server |
| `<DEPLOY_ENV>` | Enterprise |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

#### Optional Palette Tokens (Org1)

Primary Colors:
- Plum `#5A2D82`
- Red `#E30613`
- White `#FFFFFF`
- Black `#000000`
- Gray `#7D7D7D`

Secondary Colors:
- Light Gray `#D9D9D9`
- Dark Gray `#4A4A4A`
- Light Red `#F28B82`
- Dark Red `#B71C1C`
- Bright Red `#A61A07`
- Light Plum `#B39DDB`
- Dark Plum `#3B022A`

Additional page-level colors extracted from a representative enterprise Streamlit page set:
- `#1F2937`, `#6B7280`, `#E5E7EB`, `#DBEAFE`, `#EDE9FE`, `#FEE2E2`, `#FEF3C7`
- `#374151`, `#1E40AF`, `#5B21B6`, `#991B1B`, `#92400E`, `#2563EB`, `#DC2626`, `#D97706`

### org2-finance-ops

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Org2 |
| `<BRAND_PRIMARY>` | #1D4ED8 |
| `<BRAND_DARK>` | #1E293B |
| `<BRAND_LIGHT>` | #F8FAFC |
| `<DB_TYPE>` | PostgreSQL |
| `<DEPLOY_ENV>` | Enterprise |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |

### org3-healthcare-ops

#### Core Placeholders

| Placeholder | Value |
|-------------|-------|
| `<ORG_NAME>` | Org3 |
| `<BRAND_PRIMARY>` | #0F766E |
| `<BRAND_DARK>` | #134E4A |
| `<BRAND_LIGHT>` | #F0FDFA |
| `<DB_TYPE>` | SQL Server |
| `<DEPLOY_ENV>` | Enterprise |
| `<LOGGING_LIB>` | loguru |
| `<SHARED_LIBS>` | src/shared |
