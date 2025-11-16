# GitHub Configuration

This directory contains GitHub-specific configuration files for the ETF Holdings
project.

## Workflows

### Pre-commit Checks (`workflows/pre-commit.yml`)

Runs on every pull request and push to main/develop branches.

**What it does:**

- Runs all pre-commit hooks (Black, isort, flake8, bandit, markdownlint, etc.)
- Ensures code quality before merging
- Shows diff on failure for easy debugging

**Status Badge:**

[![Pre-commit Checks](https://github.com/flepied/etf_holdings/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/flepied/etf_holdings/actions/workflows/pre-commit.yml)

### Continuous Integration (`workflows/ci.yml`)

Comprehensive CI pipeline that runs on pull requests and pushes.

**Jobs:**

1. **Test** - Run tests on Python 3.8, 3.10, 3.12, 3.14
   - Installs dependencies
   - Runs pytest with coverage
   - Uploads coverage to Codecov

2. **Lint** - Code quality checks
   - Black formatting check
   - isort import sorting check
   - flake8 linting
   - bandit security scan

3. **Build** - Package build verification
   - Builds wheel and source distribution
   - Validates package with twine
   - Uploads build artifacts

**Status Badge:**

[![CI](https://github.com/flepied/etf_holdings/actions/workflows/ci.yml/badge.svg)](https://github.com/flepied/etf_holdings/actions/workflows/ci.yml)

## Issue Templates

### Bug Report (`ISSUE_TEMPLATE/bug_report.md`)

Template for reporting bugs with:

- Bug description
- Reproduction steps
- Expected vs actual behavior
- Code examples
- Environment details

### Feature Request (`ISSUE_TEMPLATE/feature_request.md`)

Template for requesting new features with:

- Feature description
- Problem statement
- Proposed solution
- Use case examples
- Priority level

## Pull Request Template

Template for creating pull requests with:

- Description of changes
- Type of change checklist
- Testing checklist
- Pre-commit verification checklist

## Dependabot

Automatic dependency updates configured for:

- Python packages (weekly on Mondays)
- GitHub Actions (weekly on Mondays)

## Troubleshooting

### Workflows Not Running

1. Check GitHub Actions is enabled: Settings → Actions → General
2. Verify workflow files are in `.github/workflows/`
3. Check for YAML syntax errors

### Pre-commit Failures

Run locally to debug:

```bash
make pre-commit
# Or
pre-commit run --all-files
```

### Test Failures

Run tests locally:

```bash
make test
# Or
pytest -v
```

### Coverage Upload Fails

- Public repos: No token needed
- Private repos: Add `CODECOV_TOKEN` to repository secrets

## Maintenance

### Updating Workflows

When updating workflow files:

1. Make changes locally
2. Validate YAML syntax
3. Test with a pull request
4. Merge after verification

### Updating Dependencies

Dependabot will automatically create PRs for:

- Python package updates
- GitHub Actions version updates

Review and merge these PRs regularly.

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit CI](https://pre-commit.ci/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
