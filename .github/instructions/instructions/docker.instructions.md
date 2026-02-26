---
description: 'Docker and containerization best practices'
applyTo: '**/Dockerfile, **/Dockerfile.*, **/*.dockerfile, **/docker-compose*.yml, **/compose*.yml'
---

# Docker & Containerization Instructions

Best practices for creating optimized, secure, and efficient Docker images for applications.

## Core Principles

### 1. Immutability
- Build new images for every change
- Never modify running containers
- Use semantic versioning for image tags
- Avoid `latest` tag in production

### 2. Efficiency
- Minimize image size
- Optimize layer caching
- Use multi-stage builds
- Remove unnecessary dependencies

### 3. Security
- Run as non-root user
- Scan for vulnerabilities
- Use minimal base images
- Don't store secrets in images

### 4. Portability
- Design images to run consistently across environments (local, cloud, on-premise)
- Externalize all environment-specific config via environment variables
- Use multi-platform base images when targeting multiple architectures (ARM, x86)
- Include all dependencies explicitly; don't rely on host system packages

### 5. Isolation
- Run a single primary process per container
- Use container networking for inter-container communication (not host networking)
- Use named volumes for persistent data rather than bind mounts when possible

## Dockerfile Template

### Python Application (FastAPI)
```dockerfile
# ============================================
# Stage 1: Build
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 2: Production
# ============================================
FROM python:3.11-slim AS production

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Update PATH for user-installed packages
ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser main.py .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Streamlit Application
```dockerfile
# ============================================
# Stage 1: Build
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# Stage 2: Production
# ============================================
FROM python:3.11-slim AS production

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Copy dependencies
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy application
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## Docker Compose Template

```yaml
version: '3.8'

services:
  # FastAPI Backend
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: app-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s
    restart: unless-stopped
    networks:
      - app-network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M

  # Streamlit Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    container_name: app-frontend
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://api:8000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  # Ollama LLM Service
  ollama:
    image: ollama/ollama:latest
    container_name: app-llm
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/root/.ollama
    restart: unless-stopped
    networks:
      - app-network
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G

networks:
  app-network:
    driver: bridge

volumes:
  ollama-models:
```

## Layer Optimization

### Order Instructions by Change Frequency
```dockerfile
# Least frequently changed (cached)
FROM python:3.11-slim AS builder

# System dependencies (rarely change)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (change with requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (changes frequently - put last)
COPY . .
```

### Combine RUN Commands
```dockerfile
# ❌ Bad: Multiple layers
RUN apt-get update
RUN apt-get install -y python3
RUN apt-get install -y curl
RUN apt-get clean

# ✅ Good: Single layer with cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

## CMD and ENTRYPOINT

```dockerfile
# Use ENTRYPOINT for the executable, CMD for default arguments
ENTRYPOINT ["python", "main.py"]
CMD ["--config", "prod.conf"]

# For simple cases, CMD alone is sufficient
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ✅ Always use exec form (JSON array) for proper signal handling
CMD ["python", "main.py"]

# ❌ Avoid shell form - wraps in /bin/sh, breaks signal handling
CMD python main.py
```

## Environment Variables for Configuration

```dockerfile
# Set sensible defaults, allow runtime overrides
ENV APP_ENV=production
ENV PORT=8000
ENV LOG_LEVEL=info

# Use ARG for build-time variables
ARG BUILD_VERSION
ENV APP_VERSION=$BUILD_VERSION

# ❌ Never hardcode secrets
ENV API_KEY=secret123

# ✅ Read from environment at runtime
# docker run -e API_KEY=$MY_KEY myimage
```
Validate required environment variables at application startup to fail fast on missing config.

## Security Best Practices

### 1. Use Non-Root User
```dockerfile
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser
USER appuser
```

### 2. Don't Store Secrets
```dockerfile
# ❌ Never do this
ENV DATABASE_PASSWORD=secret123

# ✅ Pass at runtime
# docker run -e DATABASE_PASSWORD=$DB_PASS myimage
```
Secrets added to any image layer remain in the image history even if deleted in later layers. Use runtime secrets management (Docker Secrets, Kubernetes Secrets, HashiCorp Vault).

### 3. Scan for Vulnerabilities
```bash
# Using Docker Scout
docker scout cves myimage:tag

# Using Trivy
trivy image myimage:tag

# Lint Dockerfiles with Hadolint
docker run --rm -i hadolint/hadolint < Dockerfile
```
Integrate `hadolint` (Dockerfile linting) and `Trivy` or `Snyk Container` (image scanning) into your CI pipeline. Fail builds on critical vulnerabilities.

### 4. Image Signing & Verification
```bash
# Sign an image with Cosign
cosign sign --key cosign.key myregistry.com/myapp:v1.0.0

# Verify an image
cosign verify --key cosign.pub myregistry.com/myapp:v1.0.0
```
Use Docker Content Trust or Cosign to cryptographically sign images. Enforce policies that prevent running unsigned images in production.

### 5. Limit Capabilities & Read-Only Filesystems
```bash
# Drop all capabilities, add only what's needed
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myimage

# Read-only root filesystem
docker run --read-only --tmpfs /tmp myimage

# Prevent privilege escalation
docker run --security-opt=no-new-privileges myimage
```

### 6. Use .dockerignore
```dockerignore
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
.pytest_cache
.mypy_cache
.venv
venv

# IDE
.vscode
.idea

# Build
dist
build
*.egg-info

# Secrets
.env
*.pem
*.key

# Documentation
docs
*.md
!README.md
```

## Health Checks

```dockerfile
# HTTP health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Script health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python /app/healthcheck.py || exit 1
```

## Build Commands

```bash
# Build with tag
docker build -t my-app:1.0.0 .

# Build with build args
docker build --build-arg VERSION=1.0.0 -t my-app:1.0.0 .

# Build multi-platform
docker buildx build --platform linux/amd64,linux/arm64 -t my-app:1.0.0 .

# Build specific stage
docker build --target builder -t my-app:builder .
```

## Logging & Monitoring

- Write logs to `STDOUT`/`STDERR` (not files) for container log aggregation
- Use structured logging (JSON) for better parsing and analysis
- Integrate with log aggregators (Fluentd, Logstash, Loki) and monitoring tools (Prometheus, Grafana)
- Set up log rotation and retention policies to manage storage costs

## Persistent Storage

```yaml
services:
  database:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```
- Use Docker Volumes or Kubernetes Persistent Volumes for data that must survive container restarts
- Never store persistent data inside the container's writable layer
- Implement backup and disaster recovery procedures for persistent data

## Networking Best Practices

```yaml
services:
  web:
    networks:
      - frontend
      - backend
  api:
    networks:
      - backend
  database:
    networks:
      - backend

networks:
  frontend:
  backend:
    internal: true  # No external access
```
- Create separate networks for different application tiers
- Use `internal: true` for networks that should not have external access
- Rely on container DNS for service discovery instead of hardcoded IPs

## Debugging

```bash
# Run interactive shell
docker run -it my-app:1.0.0 /bin/bash

# Check logs
docker logs my-app

# Inspect container
docker inspect my-app

# View resource usage
docker stats my-app

# Analyze image layers for size optimization
docker history my-app:1.0.0
```

## Troubleshooting

### Large Image Size
- Review layers with `docker history <image>` for unnecessary files
- Implement multi-stage builds; use a smaller base image
- Optimize `RUN` commands and clean up temp files in the same layer

### Slow Builds
- Order instructions from least to most frequent change for better cache hits
- Use `.dockerignore` to exclude irrelevant files from build context
- Use `docker build --no-cache` to debug cache-related issues

### Container Not Starting
- Verify `CMD` and `ENTRYPOINT` instructions
- Check `docker logs <container_id>` for error output
- Ensure all runtime dependencies exist in the final image stage
- Check resource limits are not too restrictive

### Permission Issues
- Verify file ownership matches the `USER` defined in the Dockerfile
- Check mounted volume permissions on the host
- Ensure the non-root user has access to necessary directories

## Best Practices Checklist

- [ ] Use multi-stage builds
- [ ] Run as non-root user
- [ ] Use specific base image versions (not `latest` in production)
- [ ] Order instructions by change frequency
- [ ] Combine RUN commands and clean up in same layer
- [ ] Use .dockerignore
- [ ] Use exec form for CMD/ENTRYPOINT
- [ ] Externalize configuration via environment variables
- [ ] Include health checks
- [ ] Set resource limits (CPU, memory)
- [ ] Scan for vulnerabilities (Trivy, Docker Scout)
- [ ] Lint Dockerfiles (Hadolint)
- [ ] Sign production images (Cosign, Docker Content Trust)
- [ ] Drop unnecessary Linux capabilities
- [ ] Don't store secrets in image layers
- [ ] Log to STDOUT/STDERR
- [ ] Use named volumes for persistent data

## Project Defaults

> Read `project-config.md` to resolve placeholder values. The profile defines container names, image tags, and service configurations.
