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

```markdown
![Pre-commit Checks](https://github.com/OWNER/REPO/actions/workflows/pre-commit.yml/badge.svg)
```

### Continuous Integration (`workflows/ci.yml`)

Comprehensive CI pipeline that runs on pull requests and pushes.

**Jobs:**

1. **Test** - Run tests on Python 3.8, 3.9, 3.10, 3.11, 3.12
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

```markdown
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
```

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

## Setting Up

### 1. Enable GitHub Actions

GitHub Actions should be automatically enabled for your repository.

### 2. Add Status Badges

Add these badges to your main README.md:

```markdown
[![Pre-commit](https://github.com/OWNER/REPO/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/pre-commit.yml)
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/OWNER/REPO)
```

Replace `OWNER/REPO` with your GitHub username and repository name.

### 3. Configure Codecov (Optional)

1. Sign up at [codecov.io](https://codecov.io)
2. Enable your repository
3. Add `CODECOV_TOKEN` to repository secrets (if private repo)

### 4. Branch Protection Rules

Recommended branch protection settings for `main`:

- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass before merging
  - `pre-commit`
  - `test (3.11)` or all Python versions
  - `lint`
  - `build`
- ✅ Require branches to be up to date before merging
- ✅ Include administrators

### 5. Dependabot Configuration

Update `.github/dependabot.yml` reviewers:

```yaml
reviewers:
  - "your-github-username"
```

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
