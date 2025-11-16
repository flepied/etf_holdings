.PHONY: help install install-dev test lint format clean pre-commit setup-precommit sync

# Detect if uv is available
UV := $(shell command -v uv 2> /dev/null)
ifdef UV
    PIP := uv pip
    RUN := uv run
else
    PIP := pip
    RUN :=
endif

help:  ## Show this help message
	@echo "ETF Holdings - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

sync:  ## Sync dependencies using uv (recommended)
ifdef UV
	uv sync --all-extras
	uv run pre-commit install
	@echo "✅ Dependencies synced with uv!"
else
	@echo "⚠️  uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
	@echo "Falling back to pip..."
	$(MAKE) install-dev
endif

install:  ## Install package in production mode
	$(PIP) install -e .

install-dev:  ## Install package with development dependencies
	$(PIP) install -e ".[dev]"
	$(RUN) pre-commit install

setup-precommit:  ## Setup pre-commit hooks
	$(PIP) install pre-commit
	$(RUN) pre-commit install
	@echo "✅ Pre-commit hooks installed!"

test:  ## Run tests
	$(RUN) pytest -v

test-cov:  ## Run tests with coverage
	$(RUN) pytest --cov=. --cov-report=html --cov-report=term

lint:  ## Run linting checks
	$(RUN) black --check .
	$(RUN) isort --check-only .
	$(RUN) flake8 .
	$(RUN) bandit -r . -c pyproject.toml

format:  ## Format code with black and isort
	$(RUN) black .
	$(RUN) isort .

pre-commit:  ## Run pre-commit hooks on all files
	$(RUN) pre-commit run --all-files

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .uv/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete

clean-cache:  ## Clean ETF holdings cache
	$(RUN) python cache_manager.py clear
	@echo "✅ ETF holdings cache cleared"

analyze-geo:  ## Run geographic dispersion analysis (example)
	$(RUN) python analyze_geographic_dispersion.py AIQ --top 10

analyze-overlap:  ## Run portfolio overlap analysis (example)
	$(RUN) python analyze_portfolio.py VTI SPY --top 10

example:  ## Run example script
	$(RUN) python example.py

.DEFAULT_GOAL := help
