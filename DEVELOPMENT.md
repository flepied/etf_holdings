# Development Guide

## Quick Start

### 1. Setup Development Environment

#### Using uv (recommended - fastest)

```bash
# Clone and enter directory
git clone <repository-url>
cd etf_holdings

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync --all-extras
```

#### Using traditional pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with dev dependencies
make install-dev

# Or manually:
pip install -e ".[dev]"
```

### 2. Install Pre-commit Hooks

```bash
make setup-precommit
```

This will install and configure:

- Black (code formatting)
- isort (import sorting)
- flake8 (linting)
- bandit (security checks)
- YAML/JSON validators
- Trailing whitespace removal
- And more...

## Common Commands

### Using Makefile

```bash
make help              # Show all available commands
make install           # Install package
make install-dev       # Install with dev dependencies
make test              # Run tests
make test-cov          # Run tests with coverage
make lint              # Run linting checks
make format            # Format code
make pre-commit        # Run pre-commit on all files
make clean             # Clean build artifacts
make clean-cache       # Clear ETF cache
```

### Manual Commands (using uv)

```bash
# Format code
uv run black .
uv run isort .

# Run linting
uv run flake8 .
uv run bandit -r . -c pyproject.toml

# Run tests
uv run pytest -v
uv run pytest --cov=. --cov-report=html

# Run pre-commit hooks
uv run pre-commit run --all-files
```

### Manual Commands (traditional)

```bash
# Format code
black .
isort .

# Run linting
flake8 .
bandit -r . -c pyproject.toml

# Run tests
pytest -v
pytest --cov=. --cov-report=html

# Run pre-commit hooks
pre-commit run --all-files
```

## Code Quality Tools

### Black (Code Formatter)

- **Line length**: 88 characters
- **Target**: Python 3.8+
- **Config**: `pyproject.toml`

```bash
# Format all files
black .

# Check without modifying
black --check .

# Format specific file
black etf_holdings.py
```

### isort (Import Organizer)

- **Profile**: black-compatible
- **Config**: `pyproject.toml`

```bash
# Sort imports
isort .

# Check only
isort --check-only .
```

### flake8 (Linter)

- **Max line length**: 88
- **Max complexity**: 15
- **Config**: `pyproject.toml`

```bash
# Lint all files
flake8 .

# Lint specific file
flake8 etf_holdings.py
```

### bandit (Security Scanner)

- **Excludes**: tests/
- **Config**: `pyproject.toml`

```bash
# Scan all files
bandit -r . -c pyproject.toml

# Scan with verbose output
bandit -r . -c pyproject.toml -v
```

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit. They ensure:

✅ No trailing whitespace
✅ Files end with newline
✅ YAML/JSON is valid
✅ Code is formatted (Black)
✅ Imports are sorted (isort)
✅ Code passes linting (flake8)
✅ No security issues (bandit)
✅ No secrets committed (detect-secrets)

### Bypassing Hooks

**Not recommended**, but if needed:

```bash
# Skip all hooks (use sparingly!)
git commit --no-verify -m "message"

# Skip specific hook
SKIP=flake8 git commit -m "message"
```

### Updating Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Re-install hooks
pre-commit install
```

## Testing

### Running Tests

```bash
# All tests
pytest

# Verbose output
pytest -v

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest test_etf_holdings.py

# Specific test function
pytest test_etf_holdings.py::test_normalize_country
```

### Writing Tests

Example test structure:

```python
import pytest
from country_normalizer import normalize_country

def test_normalize_us_variations():
    """Test US country code variations."""
    test_cases = ["US", "USA", "United States"]

    for variation in test_cases:
        code, name = normalize_country(variation)
        assert code == "US"
        assert name == "United States"

def test_invalid_country():
    """Test invalid country input."""
    code, name = normalize_country("INVALID")
    assert code == "UNKNOWN"
```

## Code Style Guidelines

### General Principles

- **PEP 8** compliance (enforced by flake8)
- **Type hints** where appropriate
- **Docstrings** for public functions/classes
- **DRY** (Don't Repeat Yourself)
- **KISS** (Keep It Simple, Stupid)

### Docstring Format

```python
def normalize_country(country_input: str) -> tuple:
    """
    Normalize a country name or code to ISO alpha-2 code and full name.

    Args:
        country_input: Country name, code, or variation

    Returns:
        Tuple of (iso_code, full_name), e.g. ("US", "United States")
        Returns ("UNKNOWN", "Unknown") if country cannot be normalized

    Examples:
        >>> normalize_country("USA")
        ("US", "United States")
        >>> normalize_country("United Kingdom")
        ("GB", "United Kingdom")
    """
    # Implementation here
```

### Import Organization (isort)

```python
# Standard library
import json
import logging
from datetime import datetime
from pathlib import Path

# Third-party
import pandas as pd
import requests
from lxml import etree

# Local
from country_normalizer import normalize_country
from etf_holdings import get_etf_holdings
```

## Configuration Files

### pyproject.toml

Central configuration for:

- Black formatting
- isort import sorting
- flake8 linting
- bandit security
- pytest testing
- coverage reporting

### .pre-commit-config.yaml

Defines pre-commit hooks:

- Versions of tools
- Hook configurations
- Exclusions

### .gitignore

Excludes:

- Python cache files
- Virtual environments
- Build artifacts
- IDE files
- Test outputs

## Troubleshooting

### Pre-commit Hook Failures

**Problem**: Hook fails on commit

**Solution**:

```bash
# Run hooks manually to see detailed errors
pre-commit run --all-files

# Fix issues and try again
make format
git add .
git commit -m "message"
```

### Import Errors

**Problem**: Module not found

**Solution**:

```bash
# Ensure package is installed in editable mode
pip install -e .

# Check your virtual environment is activated
which python  # Should show .venv path
```

### Black/isort Conflicts

**Problem**: Black and isort disagree

**Solution**: The configuration uses `--profile black` for isort, which should prevent conflicts. If issues persist:

```bash
# Update isort
pip install --upgrade isort

# Run both formatters
black .
isort .
```

## Contributing Workflow

1. **Create branch**

   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes**
   - Write code
   - Add tests
   - Update docs

3. **Format and lint**

   ```bash
   make format
   make lint
   ```

4. **Test**

   ```bash
   make test
   ```

5. **Commit** (pre-commit hooks run automatically)

   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

6. **Push and create PR**

   ```bash
   git push origin feature/your-feature
   ```

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [pre-commit Documentation](https://pre-commit.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [PEP 8 Style Guide](https://pep8.org/)

---

**Need help?** Check [CONTRIBUTING.md](CONTRIBUTING.md) or open an issue!
