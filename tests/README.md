# Elli Tests

This directory contains unit tests and integration tests for the Elli Slack bot.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Test logger
pytest tests/services/test_logger.py

# Test metrics
pytest tests/services/test_metrics.py

# Test RAG service
pytest tests/services/test_rag_service.py
```

### Run Tests with Coverage

```bash
pytest --cov=services --cov=listeners --cov=workflows --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### Run Specific Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── README.md                # This file
└── services/
    ├── __init__.py
    ├── test_logger.py       # Logger service tests
    ├── test_metrics.py      # Metrics service tests
    ├── test_rag_service.py  # RAG service tests
    ├── test_sf_client.py    # Salesforce client tests
    └── test_ai_service.py   # AI service tests
```

## Test Markers

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests for end-to-end flows
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.mock` - Tests that use mock mode

## Shared Fixtures

Available in `conftest.py`:

- `mock_env_no_credentials` - Removes credentials to force mock mode
- `mock_snowflake_connection` - Mock Snowflake connection
- `mock_salesforce_client` - Mock Salesforce client
- `sample_opportunity` - Sample opportunity data
- `sample_rag_chunks` - Sample RAG chunks
- `sample_conversation_history` - Sample conversation history
- `sample_semantic_memories` - Sample semantic memories
- `disable_logging` - Disable logging for tests
- `disable_metrics` - Disable metrics for tests

## Writing New Tests

### Test File Structure

```python
"""
Tests for services/your_service.py

Brief description of what is being tested.
"""

import pytest
from services.your_service import YourService


@pytest.fixture
def your_fixture():
    """Fixture description"""
    return YourService()


class TestYourService:
    """Tests for YourService class"""

    def test_something(self, your_fixture):
        """Test description"""
        result = your_fixture.do_something()
        assert result is not None
```

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use descriptive names that explain what is being tested

### Best Practices

1. **Use fixtures** for common setup
2. **Mock external dependencies** (Snowflake, Salesforce, Slack)
3. **Test both success and failure cases**
4. **Use parametrize** for testing multiple inputs
5. **Keep tests focused** on one thing
6. **Use markers** to categorize tests

## Coverage Goals

- **Minimum**: 70% overall coverage
- **Target**: 80% overall coverage
- **Focus**: Core services should have >90% coverage

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Nightly builds

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running pytest from the project root:

```bash
cd /path/to/Elli
pytest
```

### Missing Dependencies

Install all development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Slow Tests

Skip slow tests during development:

```bash
pytest -m "not slow"
```
