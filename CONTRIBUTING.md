# Contributing to Argo Subscription Management System

Thank you for your interest in contributing! This document outlines the process and guidelines for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Commit Messages](#commit-messages)

---

## Code of Conduct

Be respectful, constructive, and inclusive. Harassment or discrimination of any kind will not be tolerated.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/sbms.git
   cd sbms
   ```
3. Set up the development environment per [README.md](README.md).
4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Branch Naming

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New feature | `feature/plan-downgrades` |
| `bugfix/` | Bug fix | `bugfix/invoice-void-race` |
| `docs/` | Documentation | `docs/api-examples` |
| `refactor/` | Code refactoring | `refactor/invoice-service` |
| `test/` | Test additions | `test/payment-allocations` |

### Before Committing

- [ ] All backend tests pass: `pytest -q`
- [ ] All frontend tests pass: `npm test`
- [ ] Frontend lint passes: `npm run lint`
- [ ] Production build succeeds: `npm run build`
- [ ] No `.db`, `.env`, or `node_modules` files staged

## Code Style

### Python (Backend)

- Follow [PEP 8](https://pep8.org/)
- Use type hints where practical
- Maximum line length: 100 characters
- Docstrings for all public functions and classes
- Use `ruff` or `black` for formatting if available

```python
# Good
def calculate_mrr(subscriptions: list[Subscription], currency: str) -> int:
    """Return the monthly recurring revenue in minor units."""
    return sum(...)
```

### TypeScript / React (Frontend)

- Follow the existing project conventions
- Prefer functional components with hooks
- Use explicit TypeScript types for props and state
- Prefix event handlers with `handle` (e.g., `handleSubmit`)

```typescript
// Good
interface DashboardProps {
  metrics: SummaryMetrics;
}

export function Dashboard({ metrics }: DashboardProps) {
  const [loading, setLoading] = useState(false);
  // ...
}
```

## Pull Request Process

1. **Update documentation** if your change affects setup, API, or behavior.
2. **Add tests** for new features and bug fixes.
3. **Ensure CI passes** — run the full test suite locally.
4. **Fill out the PR template** (description, changes, testing steps).
5. **Request review** from at least one maintainer.
6. **Address feedback** promptly and respectfully.
7. Squash commits if requested before merge.

### PR Checklist

- [ ] Description clearly explains what changed and why
- [ ] Related issue linked (if applicable)
- [ ] Screenshots attached for UI changes
- [ ] Tests added or updated
- [ ] No breaking changes without migration notes

## Issue Reporting

### Bug Reports

Include:
- **Environment:** OS, Python/Node version, browser
- **Steps to reproduce** (numbered list)
- **Expected behavior**
- **Actual behavior**
- **Error messages / stack traces**
- **Screenshots** if UI-related

### Feature Requests

Include:
- **Use case** — who benefits and how?
- **Proposed solution**
- **Alternatives considered**
- **Willingness to contribute** — are you able to implement this?

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring |
| `test` | Adding or fixing tests |
| `chore` | Maintenance, deps, build |

### Examples

```
feat(subscriptions): add prorated plan downgrades

fix(invoices): prevent negative totals on void

docs(api): add payment attempt examples
```

---

## Questions?

Open a [Discussion](https://github.com/keikoocatalasan/sbms/discussions) or reach out via issue. We're happy to help!

---

<p align="center">
  <sub>Thank you for contributing to Argo!</sub>
</p>
