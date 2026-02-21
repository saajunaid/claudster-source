---
description: 'Create an optimized multi-stage Dockerfile for any language or framework'
---

# Multi-Stage Dockerfile

Create an efficient, production-ready multi-stage Dockerfile for the current project.

## Instructions

1. Detect the project's language, framework, and package manager from the codebase.
2. Generate a multi-stage Dockerfile following the best practices below.
3. Also generate a `.dockerignore` file if one doesn't exist.

## Multi-Stage Structure

Organize stages in this order:

```dockerfile
# Stage 1: Dependencies
FROM <base>:<version>-slim AS deps
# Install only production dependencies

# Stage 2: Build
FROM deps AS build
# Install dev dependencies, compile, transpile, etc.

# Stage 3: Runtime
FROM <minimal-base>:<version>-slim AS runtime
# Copy only built artifacts and production deps
# Set non-root user, healthcheck, entrypoint
```

## Best Practices

### Base Images
- Use official, minimal base images (`-slim`, `-alpine`)
- Pin exact version tags for reproducibility (e.g., `python:3.12-slim`, not `python:latest`)
- Consider distroless images for the runtime stage

### Layer Optimization
- Copy dependency manifests first, install deps, then copy source code (maximizes cache)
- Combine related `RUN` commands with `&&` to reduce layers
- Place frequently-changing steps (source code) after stable steps (dependencies)

### Security
- Run as a non-root user in the runtime stage (`USER appuser`)
- Remove build tools and dev dependencies from the final image
- Do not copy secrets, credentials, or `.env` files into the image
- Set restrictive file permissions

### Performance
- Use `HEALTHCHECK` appropriate to the application type
- Set production environment variables (e.g., `NODE_ENV=production`)
- Use `COPY --from=build` to bring only necessary artifacts into runtime
- Use build arguments (`ARG`) for values that vary between environments

## .dockerignore

Generate a `.dockerignore` that excludes at minimum:

```
.git
node_modules
__pycache__
*.pyc
.env
.env.*
dist
build
coverage
.pytest_cache
```

## Output

Provide the Dockerfile with comments explaining each stage and key decisions.
