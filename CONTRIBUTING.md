# Contributing to ETF Holdings

Thank you for your interest in contributing to ETF Holdings! This document provides guidelines for contributing to the project.

## Quick Start

**For detailed development setup and tools, see [DEVELOPMENT.md](DEVELOPMENT.md).**

```bash
# Quick setup
git clone <repository-url>
cd etf_holdings
make install-dev
make setup-precommit
```

## Ways to Contribute

- 🐛 **Report bugs** - Open an issue with reproduction steps
- ✨ **Suggest features** - Propose new functionality
- 📝 **Improve documentation** - Fix typos, add examples
- 🔧 **Submit code** - Bug fixes and new features
- 🧪 **Add tests** - Improve test coverage
- 🎨 **Add ETF support** - Map new ETF families

## Code Standards

All contributions must follow our code quality standards:

- ✅ **Black** formatted (line length: 88)
- ✅ **isort** organized imports
- ✅ **flake8** compliant
- ✅ **bandit** security checked
- ✅ **Tests** included for new features
- ✅ **Documentation** updated

**These are automatically enforced by pre-commit hooks and GitHub Actions.**

For tool details and configuration, see [DEVELOPMENT.md](DEVELOPMENT.md).

## Contribution Workflow

### 1. Branch Naming Convention

Use descriptive prefixes:

```
feature/your-feature-name    # New features
fix/bug-description          # Bug fixes
docs/what-you-changed        # Documentation
refactor/what-you-refactored # Code refactoring
test/what-you-test           # Test additions
```

### 2. Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

[optional body]

[optional footer]
```

**Types:**

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Code style/formatting
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks
- `ci` - CI/CD changes

**Example:**

```
feat: add country normalization for geographic analysis

Implements ISO 3166-1 alpha-2 normalization to ensure consistent
country data across all ETF data sources.

Closes #123
```

### 3. Pull Request Checklist

Before submitting:

- [ ] Code follows project style (automatic via pre-commit)
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Branch is up-to-date with main
- [ ] Commit messages follow convention
- [ ] PR description is clear and complete

**GitHub Actions will automatically verify code quality, tests, and security.**

## Common Contributions

### Adding New ETF Support

**To add a new ETF family:**

1. Find the CIK and Series ID (see `discover_etf.py`)
2. Add mapping to `KNOWN_ETF_CIKS` in `etf_holdings.py`
3. Test: `python -c "from etf_holdings import get_etf_holdings; print(get_etf_holdings('TICKER'))"`
4. Add test case to `test_etf_holdings.py`
5. Update README.md supported ETFs list
6. Submit PR with test results

**Example PR:** *"feat: add support for XYZ ETF family (10 new tickers)"*

### Adding Analysis Features

**For new analysis tools:**

1. Create new module (e.g., `analyze_sector_exposure.py`)
2. Follow existing pattern (see `analyze_geographic_dispersion.py`)
3. Add CLI interface with argparse
4. Include caching where appropriate
5. Write tests for core logic
6. Create documentation in README.md
7. Add usage examples

**Example PR:** *"feat: add sector exposure analysis tool"*

### Improving Documentation

**Documentation updates are always welcome:**

- Fix typos or unclear explanations
- Add usage examples
- Improve code comments
- Expand troubleshooting guides
- Add diagrams or screenshots

**No need for extensive testing for docs-only changes.**

## Review Process

### What to Expect

1. **Automated checks** - GitHub Actions runs within ~5 minutes
2. **Maintainer review** - Usually within 1-3 days
3. **Feedback cycle** - Address comments, push updates
4. **Approval & merge** - Once approved and checks pass

### Review Criteria

**Code Reviews Focus On:**

- ✅ Functionality - Does it work as intended?
- ✅ Tests - Are edge cases covered?
- ✅ Documentation - Is it clear how to use?
- ✅ Performance - Any obvious bottlenecks?
- ✅ Security - Any potential vulnerabilities?
- ✅ Maintainability - Is the code clear and well-structured?

**We don't nitpick style** - automated tools handle that!

## Getting Help

**Before Opening an Issue:**

1. Check [README.md](README.md) and [DEVELOPMENT.md](DEVELOPMENT.md)
2. Search [existing issues](../../issues)
3. Look at [example code](example.py)

**When Asking for Help:**

- Include error messages and stack traces
- Provide minimal reproduction code
- Specify your environment (OS, Python version)
- Show what you've already tried

**Response Times:**

- Bug reports: 1-3 days
- Feature requests: 1 week
- Questions: 1-2 days

We're a small team - patience appreciated! 🙏

## Recognition

**Contributors are recognized in:**

- Git commit history
- Release notes for significant contributions
- Project README (for major features)

## Code of Conduct

### Our Pledge

We're committed to providing a welcoming and inspiring community for all.

**We expect:**

- ✅ Respectful communication
- ✅ Constructive feedback
- ✅ Focus on what's best for the project
- ✅ Empathy and kindness

**We don't tolerate:**

- ❌ Harassment or discriminatory language
- ❌ Trolling or insulting comments
- ❌ Publishing private information
- ❌ Unprofessional conduct

### Reporting Issues

If you experience unacceptable behavior, please report it by opening a confidential issue or emailing the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

## Summary

**Quick Contribution Steps:**

1. Fork and clone the repository
2. Set up development environment: `make install-dev`
3. Create a feature branch: `git checkout -b feature/my-feature`
4. Make your changes (code + tests + docs)
5. Run checks: `make pre-commit && make test`
6. Commit with conventional format
7. Push and create a pull request
8. Respond to feedback

**For detailed technical reference, see [DEVELOPMENT.md](DEVELOPMENT.md).**

Thank you for contributing to ETF Holdings! 🎉
