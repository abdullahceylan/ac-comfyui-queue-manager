.PHONY: help install install-dev format lint check test clean setup-hooks

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -e ".[dev]"

setup-hooks: ## Install pre-commit hooks
	pre-commit install
	pre-commit install --hook-type commit-msg

format: ## Format code with ruff
	ruff format .
	ruff check --fix .

lint: ## Lint code with ruff
	ruff check .

check: ## Run all checks (lint + format check)
	ruff check .
	ruff format --check .

test: ## Run tests (placeholder for future implementation)
	@echo "Tests will be implemented in future tasks"

clean: ## Clean up cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

ci: check ## Run CI checks
	@echo "All checks passed!"