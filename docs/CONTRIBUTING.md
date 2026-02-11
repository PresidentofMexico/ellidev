# Contributing to Elli

Thank you for your interest in contributing to Elli! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** and clone it locally
2. **Copy `.env.example` to `.env`** and fill in your Slack credentials
3. **Install dependencies**: `make dev-install` or `pip install -r requirements.txt`
4. **Read the documentation**: Review [README.md](README.md) and [AGENTS.md](AGENTS.md)

## Development Workflow

### 1. Create a Branch

Create a new branch for your work:

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or changes
- `chore/` - Maintenance tasks

### 2. Make Your Changes

- Follow the coding guidelines in [AGENTS.md](AGENTS.md)
- Write clean, readable code with type hints
- Add comments for complex logic
- Update documentation as needed

### 3. Test Your Changes

```bash
# Format your code
make format

# Run linters
make lint

# Run tests (when available)
make test

# Run security checks
make security
```

### 4. Update AGENTS.md Breadcrumbs

**IMPORTANT**: Update the breadcrumbs section in [AGENTS.md](AGENTS.md) with context about your changes:

```markdown
#### YYYY-MM-DD | [Your Name/Agent] | [Area Modified]
- **Agent**: [Your identifier]
- **Changes**: [What you changed]
- **Files Modified**: [List of files]
- **Files Created**: [List of new files]
- **Breaking Changes**: [Any breaking changes]
- **Notes**: [Additional context]
```

This helps other developers and AI agents understand recent changes and avoid conflicts.

### 5. Commit Your Changes

Follow conventional commits format:

```bash
git commit -m "feat(workflows): add Jira integration workflow"
git commit -m "fix(listeners): resolve duplicate message bug"
git commit -m "docs(readme): update installation instructions"
```

Commit types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes

### 6. Push and Create a Pull Request

```bash
git push origin your-branch-name
```

Then create a pull request on GitHub:
- Use the PR template provided
- Link related issues
- Describe your changes clearly
- Mark the checklist items

## Code Guidelines

### Python Style

- Follow **PEP 8** style guide
- Use **type hints** for all functions
- Maximum line length: **100 characters**
- Use **docstrings** for all public functions/classes

### Security

- **NEVER** hardcode secrets or credentials
- Use `os.environ.get()` for all sensitive values
- Keep `.env` file out of version control
- Review dependencies for vulnerabilities

### Architecture

- **Listeners** (`/listeners/`) - Event routing only, no business logic
- **Workflows** (`/workflows/`) - Business logic and Slack interactions
- **Services** (`/services/`) - External API integrations

### Testing (When Implemented)

- Write tests for new features
- Aim for >80% code coverage on business logic
- Mock external API calls
- Test edge cases and error handling

## Pull Request Process

1. **Create PR** using the template
2. **Update AGENTS.md** breadcrumbs
3. **Ensure CI passes** (linting, tests, security checks)
4. **Request review** from maintainers
5. **Address feedback** and make changes as requested
6. **Merge** once approved (squash and merge preferred)

## CI/CD Pipeline

All PRs must pass:
- ✅ Code formatting (Black, isort)
- ✅ Linting (Flake8, MyPy)
- ✅ Security checks (Safety, Bandit)
- ✅ Tests (when implemented)
- ✅ PR validation (title format, description)

## Project Structure

```
/elli
├── app.py                  # Entry point
├── /listeners              # Event routing
│   ├── messages.py         # Regex-based triggers
│   └── mentions.py         # AI fallback
├── /workflows              # Business logic
│   └── salesforce.py       # Salesforce workflow
└── /services               # External integrations
    ├── ai_service.py       # LLM client
    └── sf_client.py        # Salesforce client
```

## Common Tasks

### Adding a New Workflow

1. Create workflow file in `/workflows/your_workflow.py`
2. Add listener in `/listeners/messages.py`
3. Update AGENTS.md breadcrumbs
4. Test locally
5. Create PR

### Adding a New External Service

1. Create service client in `/services/your_service.py`
2. Add credentials to `.env.example`
3. Add dependencies to `requirements.txt`
4. Update AGENTS.md breadcrumbs
5. Document usage in README.md

### Updating Dependencies

1. Add package to `requirements.txt` with version
2. Test locally: `pip install -r requirements.txt`
3. Run security check: `make security`
4. Document why dependency is needed in PR

## Questions or Issues?

- **Documentation**: Check [README.md](README.md) and [AGENTS.md](AGENTS.md)
- **Issues**: Open a GitHub issue with details
- **Discussions**: Use GitHub Discussions for questions

## Code of Conduct

- Be respectful and professional
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Elli! 🚀
