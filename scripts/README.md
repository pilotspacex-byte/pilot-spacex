# Pilot Space Scripts

This directory contains utility scripts for the Pilot Space project.

## Scripts Overview

| Script | Purpose |
|--------|---------|
| `quality-check.sh` | Comprehensive quality gate runner for CI/CD and local development |

---

## quality-check.sh

Comprehensive quality gate script that runs linting, type checking, and tests for both backend (Python) and frontend (TypeScript) codebases.

### Requirements

- **Backend**: `uv` (Python package manager)
- **Frontend**: `pnpm` and `node` (Node.js 20+)

### Usage

```bash
# Run all checks (backend + frontend)
./scripts/quality-check.sh

# Run backend checks only
./scripts/quality-check.sh --backend-only

# Run frontend checks only
./scripts/quality-check.sh --frontend-only

# CI mode (no colors, machine-readable output)
./scripts/quality-check.sh --ci

# Run checks in parallel
./scripts/quality-check.sh --parallel

# Auto-fix linting issues
./scripts/quality-check.sh --fix

# Combine options
./scripts/quality-check.sh --ci --parallel
./scripts/quality-check.sh --backend-only --fix --verbose
```

### Options

| Option | Description |
|--------|-------------|
| `--backend-only` | Run only backend (Python) checks |
| `--frontend-only` | Run only frontend (TypeScript) checks |
| `--ci` | CI mode: disables colors, adds GitHub Actions annotations |
| `--parallel` | Run backend and frontend checks in parallel |
| `--fix` | Auto-fix linting issues where possible |
| `--verbose, -v` | Show detailed output from all commands |
| `-h, --help` | Show help message |

### Checks Performed

#### Backend (Python)

| Check | Tool | Description |
|-------|------|-------------|
| Linting | `ruff` | Fast Python linter (replaces flake8, isort, etc.) |
| Type Checking | `pyright` | Static type checker for Python |
| Tests | `pytest` | Test runner with coverage reporting |

Commands executed:
```bash
uv run ruff check .
uv run pyright
uv run pytest --cov=src/pilot_space --cov-report=term-missing
```

#### Frontend (TypeScript)

| Check | Tool | Description |
|-------|------|-------------|
| Linting | `ESLint` | JavaScript/TypeScript linter |
| Type Checking | `tsc` | TypeScript compiler (no emit) |
| Tests | `vitest` | Fast unit test framework |

Commands executed:
```bash
pnpm lint
pnpm type-check
pnpm test
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | One or more checks failed |
| `2` | Script error (missing dependencies, invalid arguments) |

### Example Output

```
Pilot Space Quality Gate
Running quality checks for backend and frontend

=== Backend Quality Gates (Python) ===

>>> Running ruff check...
[PASS] Ruff linting passed
>>> Running pyright...
[PASS] Pyright type checking passed
>>> Running pytest...
[PASS] Pytest tests passed
Backend checks completed in 12s

=== Frontend Quality Gates (TypeScript) ===

>>> Running lint...
[PASS] ESLint linting passed
>>> Running type-check...
[PASS] TypeScript type checking passed
>>> Running tests...
[PASS] Vitest tests passed
Frontend checks completed in 8s

=== Quality Gate Summary ===

Check                     Status
------------------------- ------
Backend Lint (ruff)       PASS
Backend Types (pyright)   PASS
Backend Tests (pytest)    PASS
Frontend Lint (ESLint)    PASS
Frontend Types (tsc)      PASS
Frontend Tests (vitest)   PASS

Total time: 20s

All quality gates passed!
```

### CI Integration

#### GitHub Actions

```yaml
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Run Quality Gates
        run: ./scripts/quality-check.sh --ci --parallel
```

#### Pre-commit Hook

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
./scripts/quality-check.sh --fix
```

Or use with pre-commit framework in `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: quality-check
        name: Quality Gates
        entry: ./scripts/quality-check.sh
        language: script
        pass_filenames: false
        always_run: true
```

### Troubleshooting

#### "uv: command not found"

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### "pnpm: command not found"

Install pnpm:
```bash
npm install -g pnpm
# or
corepack enable
corepack prepare pnpm@latest --activate
```

#### Virtual environment not found

The script will automatically run `uv sync --dev` if the backend `.venv` directory is missing.

#### node_modules not found

The script will automatically run `pnpm install --frozen-lockfile` if `node_modules` is missing.

---

## Adding New Scripts

When adding new scripts:

1. Use bash strict mode: `set -euo pipefail`
2. Add comprehensive help with `--help` flag
3. Support `--ci` mode for CI/CD environments
4. Use consistent color output (disabled in CI)
5. Return appropriate exit codes
6. Document in this README

### Script Template

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

print_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Description of what this script does.

Options:
    --ci         CI mode
    -h, --help   Show this help message
EOF
}

main() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --ci) CI_MODE=true; shift ;;
            -h|--help) print_usage; exit 0 ;;
            *) echo "Unknown option: $1"; exit 2 ;;
        esac
    done

    # Script logic here
}

main "$@"
```
