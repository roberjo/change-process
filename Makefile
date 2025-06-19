# Change Process Automation Makefile

.PHONY: help install test lint clean docker-build docker-run docker-test

# Default target
help:
	@echo "Change Process Automation - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  clean       - Clean up generated files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run Docker container"
	@echo "  docker-test  - Run tests in Docker"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy      - Deploy to production"
	@echo "  backup      - Create backup"
	@echo ""
	@echo "Documentation:"
	@echo "  docs        - Generate documentation"

# Development commands
install:
	pip install -r requirements.txt
	pip install -r tests/requirements-test.txt

test:
	python -m pytest tests/ -v --cov=scripts --cov-report=html

lint:
	flake8 scripts/ tests/
	pylint scripts/ tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ htmlcov/ .coverage

# Docker commands
docker-build:
	docker build -t change-process .

docker-run:
	docker run --rm -it --env-file .env change-process

docker-test:
	docker-compose --profile test up --build --abort-on-container-exit

# Docker Compose commands
compose-dev:
	docker-compose --profile dev up --build

compose-test:
	docker-compose --profile test up --build --abort-on-container-exit

# Deployment commands
deploy:
	@echo "Deploying to production..."
	# Add deployment logic here

backup:
	@echo "Creating backup..."
	# Add backup logic here

# Documentation
docs:
	@echo "Generating documentation..."
	# Add documentation generation logic here

# Environment setup
setup-env:
	@echo "Setting up environment..."
	cp scripts/servicenow/.env.template scripts/servicenow/.env
	@echo "Please edit scripts/servicenow/.env with your configuration"

# Quick start
quick-start: setup-env install test
	@echo "Quick start completed successfully!"

# Windows PowerShell specific commands
install-ps:
	python -m pip install -r requirements.txt
	python -m pip install -r tests/requirements-test.txt

test-ps:
	python -m pytest tests/ -v --cov=scripts --cov-report=html

clean-ps:
	Get-ChildItem -Recurse -Include "*.pyc" | Remove-Item -Force
	Get-ChildItem -Recurse -Include "__pycache__" | Remove-Item -Recurse -Force
	Get-ChildItem -Recurse -Include "*.egg-info" | Remove-Item -Recurse -Force
	if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
	if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
	if (Test-Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }
	if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }
	if (Test-Path ".coverage") { Remove-Item -Force ".coverage" } 