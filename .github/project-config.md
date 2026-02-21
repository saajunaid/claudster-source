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
