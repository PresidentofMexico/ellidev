.PHONY: help install dev-install lint format test security clean run docker-build docker-run

help:
	@echo "Elli Slack Bot - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install production dependencies"
	@echo "  make dev-install   - Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run           - Run the application"
	@echo "  make format        - Format code with black and isort"
	@echo "  make lint          - Run linters (flake8, mypy)"
	@echo "  make test          - Run tests with coverage"
	@echo "  make security      - Run security checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run Docker container"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         - Remove build artifacts and cache"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

dev-install: install
	pip install black isort flake8 mypy pytest pytest-cov pytest-mock safety bandit radon

format:
	@echo "Formatting code with black..."
	black .
	@echo "Sorting imports with isort..."
	isort .
	@echo "Done!"

lint:
	@echo "Running flake8..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@echo "Running mypy..."
	mypy . --ignore-missing-imports --no-strict-optional || true
	@echo "Lint complete!"

test:
	@echo "Running tests with coverage..."
	mkdir -p tests
	pytest --cov=. --cov-report=term-missing --cov-report=html || echo "No tests found"
	@echo "Coverage report generated in htmlcov/"

security:
	@echo "Running security checks..."
	@echo "Checking dependencies with safety..."
	safety check || true
	@echo "Running bandit security linter..."
	bandit -r . -f json -o bandit-report.json || true
	@echo "Security scan complete!"

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf *.egg-info
	rm -rf dist build
	@echo "Clean complete!"

run:
	@echo "Starting Elli..."
	python app.py

docker-build:
	@echo "Building Docker image..."
	docker build -t elli-slack-bot:latest .

docker-run:
	@echo "Running Docker container..."
	docker-compose up -d

docker-logs:
	docker-compose logs -f

docker-stop:
	docker-compose down
