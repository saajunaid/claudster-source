---
description: 'GitHub Actions CI/CD pipeline best practices'
applyTo: '.github/workflows/*.yml, .github/workflows/*.yaml'
---

# GitHub Actions CI/CD Instructions

Comprehensive guide for building robust, secure, and efficient CI/CD pipelines using GitHub Actions.

## Workflow Structure

### Standard Pipeline Template
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ============================================
  # Lint Job
  # ============================================
  lint:
    name: Code Linting
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          
      - name: Install linting tools
        run: pip install ruff mypy
        
      - name: Run Ruff linter
        run: ruff check . --output-format=github
        
      - name: Run type checking
        run: mypy <SOURCE_DIR>/ --ignore-missing-imports

  # ============================================
  # Test Job
  # ============================================
  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
          
      - name: Run tests with coverage
        run: |
          pytest tests/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=test-results.xml
            
      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: false
          
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: test-results.xml

  # ============================================
  # Security Scan Job
  # ============================================
  security:
    name: Security Scanning
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          
      - name: Check for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified

  # ============================================
  # Build Job
  # ============================================
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [test, security]
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}
            
      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ============================================
  # Deploy Job
  # ============================================
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - name: Deploy to staging
        run: echo "Deploying to staging environment"
        # Add actual deployment commands

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://app.example.com
    steps:
      - name: Deploy to production
        run: echo "Deploying to production environment"
        # Add actual deployment commands
```

## Job Best Practices

### Caching Dependencies
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
    cache-dependency-path: |
      requirements.txt
      requirements-dev.txt
```

### Matrix Strategy
```yaml
test:
  strategy:
    matrix:
      python-version: ['3.10', '3.11', '3.12']
      os: [ubuntu-latest, windows-latest]
    fail-fast: false
  runs-on: ${{ matrix.os }}
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
```

### Conditional Execution
```yaml
# Run only on main branch
if: github.ref == 'refs/heads/main'

# Run on PR
if: github.event_name == 'pull_request'

# Run on success
if: success()

# Run on failure
if: failure()

# Run always
if: always()

# Skip if specific files changed
if: ${{ !contains(github.event.head_commit.message, '[skip ci]') }}
```

### Passing Data Between Jobs
```yaml
jobs:
  build:
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - id: version
        run: echo "version=1.0.0" >> "$GITHUB_OUTPUT"

  deploy:
    needs: build
    steps:
      - run: echo "Deploying version ${{ needs.build.outputs.version }}"
```

## Security Best Practices

### Secrets Management
```yaml
# Access secrets
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  
# Use environment-specific secrets
jobs:
  deploy:
    environment: production
    steps:
      - run: echo "Using ${{ secrets.PROD_API_KEY }}"
```

### Permissions (Least Privilege)
```yaml
# Workflow level defaults
permissions:
  contents: read

# Job level override
jobs:
  release:
    permissions:
      contents: write
      packages: write
```

### Pin Actions to SHA
```yaml
# ❌ Risky - can be hijacked
uses: actions/checkout@main

# ✅ Better - major version
uses: actions/checkout@v4

# ✅ Best - full SHA
uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
```

### OIDC for Cloud Authentication
```yaml
# Use OpenID Connect for credential-less cloud auth (no long-lived secrets)
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: us-east-1
```
Use OIDC instead of storing long-lived access keys for AWS, Azure, or GCP. It exchanges a short-lived JWT for temporary cloud credentials.

### Dependency Review & SCA
```yaml
- name: Dependency Review
  uses: actions/dependency-review-action@v4
  if: github.event_name == 'pull_request'
```
Integrate dependency scanning early in the pipeline to catch vulnerable or license-problematic dependencies. Use tools like `dependency-review-action`, Snyk, or Trivy.

### Secret Scanning & Credential Leak Prevention
- Enable GitHub's built-in secret scanning for the repository
- Implement pre-commit hooks with tools like `git-secrets` to prevent credential commits
- Review workflow logs for accidental secret exposure, even with masking
- Never construct secrets dynamically or print them to logs

## Reusable Workflows

### Define Reusable Workflow
```yaml
# .github/workflows/python-test.yml
name: Python Tests

on:
  workflow_call:
    inputs:
      python-version:
        required: true
        type: string
    secrets:
      CODECOV_TOKEN:
        required: false

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}
      - run: pytest tests/
```

### Use Reusable Workflow
```yaml
jobs:
  test:
    uses: ./.github/workflows/python-test.yml
    with:
      python-version: '3.11'
    secrets: inherit
```

## Artifacts and Caching

### Upload Artifacts
```yaml
- name: Upload build artifacts
  uses: actions/upload-artifact@v4
  with:
    name: dist
    path: dist/
    retention-days: 5
```

### Download Artifacts
```yaml
- name: Download build artifacts
  uses: actions/download-artifact@v4
  with:
    name: dist
    path: dist/
```

### Custom Caching
```yaml
- name: Cache pip packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### Fast Checkout (Shallow Clones)
```yaml
# ✅ Default for most CI jobs - only fetch latest commit
- uses: actions/checkout@v4
  with:
    fetch-depth: 1

# Only use fetch-depth: 0 for release tagging or git history analysis
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```
Also set `submodules: false` and `lfs: false` unless explicitly needed to reduce checkout time.

## Integration Testing with Services

```yaml
jobs:
  integration-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
        run: pytest tests/integration/
```

## Performance & Load Testing

Integrate performance tests for critical applications:
```yaml
- name: Run k6 load tests
  uses: grafana/k6-action@v0.3.1
  with:
    filename: tests/load/script.js
    flags: --out json=results.json
    
- name: Check performance thresholds
  run: |
    # Fail if p95 response time exceeds 500ms
    python scripts/check_perf_thresholds.py results.json
```
Run these less frequently (nightly or on release branches) and compare against baselines to detect regressions.

## Advanced Deployment Strategies

### Blue/Green Deployment
Deploy a new version alongside the existing one, then switch traffic completely. Provides instant rollback by switching traffic back.

### Canary Deployment
Roll out to a small subset of users (5-10%) first, monitor error rates and performance, then gradually increase. Use a service mesh (Istio, Linkerd) or ingress controller with traffic splitting.

### Feature Flags / Dark Launch
Deploy code with features hidden behind flags. Decouple deployment from release using tools like LaunchDarkly, Split.io, or Unleash.

### Rollback Strategy
```yaml
- name: Deploy with rollback
  run: |
    kubectl set image deployment/myapp myapp=${{ env.IMAGE_TAG }}
    kubectl rollout status deployment/myapp --timeout=120s || \
      (kubectl rollout undo deployment/myapp && exit 1)
```
- Store previous successful build artifacts for quick recovery
- Implement post-deployment health checks; trigger automatic rollback on failure
- Document rollback runbooks for manual intervention scenarios
- Conduct blameless post-incident reviews to improve resilience

## Workflow Timeouts

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15  # Prevent hung workflows
    steps:
      # ...
```
Always set `timeout-minutes` on long-running jobs to prevent hung workflows from consuming runner minutes.

## PR Automation

### Comment on PR
```yaml
- name: Comment on PR
  uses: actions/github-script@v7
  with:
    script: |
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: '✅ Build successful! Ready for review.'
      })
```

### Auto-merge Dependabot
```yaml
name: Dependabot auto-merge
on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Auto-merge
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Debugging

### Enable Debug Logging
```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

### Troubleshooting Steps
```yaml
- name: Debug info
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "SHA: ${{ github.sha }}"
    echo "Actor: ${{ github.actor }}"
```

## Self-Hosted Runners

Use self-hosted runners for specialized hardware (GPUs), private network access, or cost optimization at high volume. Key considerations:
- Secure and maintain runner infrastructure (hardening, patching, access controls)
- Use runner groups to organize and manage runners
- Plan for auto-scaling with demand
- Restrict network access appropriately

## Observability & Monitoring

- Collect application metrics (Prometheus) and expose them during deployment
- Set up alerts for critical workflow failures and post-deployment anomalies
- Integrate distributed tracing (OpenTelemetry, Jaeger) for microservice architectures
- Add workflow status badges to README for quick CI/CD health visibility

## Checklist

- [ ] Use specific action versions (prefer full SHA)
- [ ] Set minimal permissions (`contents: read` default)
- [ ] Use OIDC for cloud auth where possible
- [ ] Cache dependencies
- [ ] Use secrets for sensitive data
- [ ] Configure concurrency
- [ ] Set `timeout-minutes` on jobs
- [ ] Use `fetch-depth: 1` for checkout
- [ ] Add status checks
- [ ] Use environments for deployment
- [ ] Include security scanning (Trivy, SCA, SAST)
- [ ] Include dependency review on PRs
- [ ] Enable secret scanning on repo
- [ ] Upload test artifacts
- [ ] Implement rollback strategy for deployments
- [ ] Post-deployment health checks
- [ ] Document workflow purpose

## Project Defaults

> Read `project-config.md` to resolve placeholder values.
