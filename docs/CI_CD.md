# CI/CD Pipeline Documentation

## Overview

The Elli project uses GitHub Actions for Continuous Integration and Continuous Deployment. This document describes the CI/CD pipeline, workflows, and deployment process.

## Pipeline Architecture

```
┌─────────────────┐
│   Code Push     │
└────────┬────────┘
         │
         ├──────────────────────────────────┬──────────────────┐
         │                                  │                  │
    ┌────▼────┐                      ┌─────▼─────┐     ┌─────▼──────┐
    │   CI    │                      │ PR Checks │     │ Dependency │
    │Pipeline │                      │           │     │   Review   │
    └────┬────┘                      └───────────┘     └────────────┘
         │
         ├──────────────┬──────────────┬──────────────┐
         │              │              │              │
    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐    ┌────▼────┐
    │  Lint   │    │  Test   │   │Security │    │Validate │
    └────┬────┘    └────┬────┘   └────┬────┘    └────┬────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                        │
                   ┌────▼────┐
                   │   CD    │
                   │Pipeline │
                   └────┬────┘
                        │
                ┌───────┴────────┐
                │                │
         ┌──────▼──────┐  ┌──────▼────────┐
         │   Staging   │  │  Production   │
         │ Deployment  │  │  Deployment   │
         └─────────────┘  └───────────────┘
```

## GitHub Actions Workflows

### 1. CI Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs:**

#### Lint
- Runs code formatters (Black, isort)
- Runs linters (Flake8)
- Runs type checker (MyPy)
- Checks code complexity and style compliance

#### Test
- Sets up Python 3.11 environment
- Installs dependencies
- Runs pytest with coverage
- Uploads coverage report to Codecov

#### Security
- Runs Safety (dependency vulnerability scanner)
- Runs Bandit (security issue scanner)
- Generates security reports

#### Validate
- Validates Python syntax
- Checks configuration files
- Validates dependencies

### 2. CD Pipeline (`cd.yml`)

**Triggers:**
- Push to `main` branch → Staging deployment
- Git tags matching `v*` → Production deployment

**Jobs:**

#### Deploy to Staging
- Runs on push to `main`
- Installs dependencies
- Runs smoke tests
- Deploys to staging environment
- Sends notifications

#### Deploy to Production
- Runs on version tags (`v1.0.0`, `v2.1.3`, etc.)
- Requires manual approval via GitHub Environments
- Runs comprehensive smoke tests
- Deploys to production
- Creates GitHub release
- Sends notifications

#### Rollback
- Manual workflow dispatch
- Reverts to previous version
- Requires approval

### 3. PR Checks (`pr-checks.yml`)

**Triggers:**
- Pull request opened, synchronized, or reopened

**Jobs:**

#### PR Validation
- Validates PR title format (conventional commits)
- Checks PR description exists
- Identifies breaking changes
- Detects new dependencies
- Checks file sizes

#### Code Quality
- Calculates code complexity (radon)
- Generates maintainability index
- Comments quality report on PR

#### Size Check
- Checks PR size (lines changed)
- Warns if PR is too large (>500 lines)

### 4. Dependency Review (`dependency-review.yml`)

**Triggers:**
- Pull requests that modify `requirements.txt`

**Jobs:**
- Reviews dependency changes
- Checks for vulnerabilities (pip-audit)
- Checks for incompatible licenses
- Fails on moderate+ severity issues

## Environment Configuration

### GitHub Secrets Required

#### Staging Environment
- `STAGING_SLACK_BOT_TOKEN` - Slack bot token for staging
- `STAGING_SLACK_APP_TOKEN` - Slack app token for staging

#### Production Environment
- `PROD_SLACK_BOT_TOKEN` - Slack bot token for production
- `PROD_SLACK_APP_TOKEN` - Slack app token for production

#### Optional (for future integrations)
- `CODECOV_TOKEN` - For coverage reporting
- `DOCKER_USERNAME` - For container registry
- `DOCKER_PASSWORD` - For container registry
- `AWS_ACCESS_KEY_ID` - For AWS deployments
- `AWS_SECRET_ACCESS_KEY` - For AWS deployments

### GitHub Environments

Configure these in repository settings:

**Staging**
- Protection rules: None (auto-deploy)
- URL: `https://staging.elli.example.com`

**Production**
- Protection rules: Required reviewers (1+)
- URL: `https://elli.example.com`
- Deployment branch: Tags matching `v*`

## Local CI Testing

### Run All Checks Locally

```bash
# Install development dependencies
make dev-install

# Format code
make format

# Run linters
make lint

# Run tests
make test

# Run security checks
make security
```

### Run Individual Checks

```bash
# Code formatting
black --check .
isort --check-only .

# Linting
flake8 .

# Type checking
mypy . --ignore-missing-imports

# Security
safety check
bandit -r .

# Tests
pytest --cov=. --cov-report=term-missing
```

## Docker Build and Deploy

### Local Docker Testing

```bash
# Build image
make docker-build
# or
docker build -t elli-slack-bot:latest .

# Run container
make docker-run
# or
docker-compose up -d

# View logs
docker-compose logs -f

# Stop container
docker-compose down
```

### Production Docker Deployment

The CD pipeline will handle Docker builds in production. For manual deployment:

```bash
# Build with tag
docker build -t elli-slack-bot:v1.0.0 .

# Push to registry
docker tag elli-slack-bot:v1.0.0 your-registry/elli:v1.0.0
docker push your-registry/elli:v1.0.0

# Deploy (example for Kubernetes)
kubectl set image deployment/elli elli=your-registry/elli:v1.0.0
```

## Deployment Strategies

### Staging Deployment (Automatic)

1. Developer merges PR to `main`
2. CI pipeline runs all checks
3. If checks pass, CD pipeline deploys to staging
4. Smoke tests run against staging
5. Notification sent to team

### Production Deployment (Manual Trigger)

1. Create and push version tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
2. CD pipeline triggered
3. Requires manual approval (GitHub Environment)
4. Comprehensive smoke tests run
5. Deploys to production
6. Creates GitHub release
7. Notification sent to team

### Rollback Procedure

1. Go to Actions tab in GitHub
2. Select "CD Pipeline" workflow
3. Click "Run workflow"
4. Select "rollback" job
5. Approve rollback in production environment
6. Previous version restored

## Monitoring and Alerting

### Health Checks

Docker containers include health checks:
```yaml
healthcheck:
  interval: 30s
  timeout: 3s
  retries: 3
```

### Logging

Logs are persisted in:
- Docker: `./logs` volume mount
- Cloud: Configure cloud-specific logging (CloudWatch, Stackdriver, etc.)

### Recommended Monitoring

1. **Application Monitoring**
   - Uptime monitoring (Pingdom, UptimeRobot)
   - APM (New Relic, Datadog, Sentry)

2. **Infrastructure Monitoring**
   - Container health (Docker/Kubernetes health checks)
   - Resource usage (CPU, memory)
   - Network metrics

3. **Slack Bot Monitoring**
   - Message processing time
   - Error rates
   - API call success rates

## Troubleshooting CI/CD

### Common Issues

#### 1. CI Pipeline Fails on Linting

**Problem:** Black or isort formatting issues

**Solution:**
```bash
make format
git add .
git commit -m "style: format code"
git push
```

#### 2. Security Check Fails

**Problem:** Vulnerable dependency detected

**Solution:**
```bash
# Check specific vulnerability
safety check --json

# Update vulnerable package
pip install --upgrade package-name

# Update requirements.txt
pip freeze > requirements.txt
```

#### 3. Tests Fail

**Problem:** Test failures in CI

**Solution:**
```bash
# Run tests locally
make test

# Debug specific test
pytest tests/test_specific.py -v

# Check environment variables
cat .env.example
```

#### 4. Deployment Fails

**Problem:** Deployment to staging/production fails

**Solution:**
1. Check GitHub Actions logs
2. Verify secrets are configured
3. Check environment variables
4. Verify deployment target is accessible

### Debug CI Pipeline

Enable debug logging:
1. Go to repository Settings → Secrets
2. Add `ACTIONS_STEP_DEBUG` with value `true`
3. Re-run workflow

## Best Practices

### 1. Branch Protection

Configure in repository settings:
- Require PR reviews (1+ approvals)
- Require status checks to pass
- Require branches to be up to date
- Include administrators

### 2. Semantic Versioning

Use semantic versioning for tags:
- `v1.0.0` - Major release (breaking changes)
- `v1.1.0` - Minor release (new features)
- `v1.1.1` - Patch release (bug fixes)

### 3. Commit Messages

Follow conventional commits:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### 4. PR Size

Keep PRs manageable:
- Small PRs (<300 lines) get faster reviews
- Break large features into multiple PRs
- Use feature flags for incremental rollout

### 5. Testing in CI

- Run tests on every PR
- Maintain >80% code coverage
- Mock external dependencies
- Use test fixtures

## Future Enhancements

### Planned Improvements

1. **Automated Testing**
   - Add unit tests
   - Add integration tests
   - Add end-to-end tests

2. **Performance Testing**
   - Load testing
   - Response time monitoring

3. **Advanced Deployment**
   - Blue-green deployments
   - Canary releases
   - Feature flags

4. **Enhanced Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alert management

5. **Infrastructure as Code**
   - Terraform for cloud resources
   - Kubernetes manifests
   - Helm charts

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**Last Updated:** 2026-01-14
**Maintained By:** DevOps Team
