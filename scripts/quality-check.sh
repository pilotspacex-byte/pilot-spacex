#!/usr/bin/env bash
#
# quality-check.sh - Comprehensive quality gate script for Pilot Space
#
# Runs linting, type checking, and tests for backend (Python) and frontend (TypeScript).
# All checks must pass before code can be merged.
#
# Usage:
#   ./scripts/quality-check.sh              # Run all checks
#   ./scripts/quality-check.sh --backend-only    # Run backend checks only
#   ./scripts/quality-check.sh --frontend-only   # Run frontend checks only
#   ./scripts/quality-check.sh --ci              # CI mode (no color, machine-readable)
#   ./scripts/quality-check.sh --parallel        # Run backend and frontend in parallel
#   ./scripts/quality-check.sh --fix             # Auto-fix linting issues where possible
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#   2 - Script error (missing dependencies, invalid arguments)
#

set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

# Default flags
RUN_BACKEND=true
RUN_FRONTEND=true
CI_MODE=false
PARALLEL_MODE=false
FIX_MODE=false
VERBOSE=false

# Track failures
BACKEND_LINT_STATUS=0
BACKEND_TYPE_STATUS=0
BACKEND_TEST_STATUS=0
FRONTEND_LINT_STATUS=0
FRONTEND_TYPE_STATUS=0
FRONTEND_TEST_STATUS=0

# Timing
START_TIME=$(date +%s)

# ==============================================================================
# Color Output
# ==============================================================================

setup_colors() {
    if [[ "${CI_MODE}" == "true" ]] || [[ ! -t 1 ]]; then
        RED=""
        GREEN=""
        YELLOW=""
        BLUE=""
        CYAN=""
        BOLD=""
        DIM=""
        RESET=""
    else
        RED="\033[0;31m"
        GREEN="\033[0;32m"
        YELLOW="\033[0;33m"
        BLUE="\033[0;34m"
        CYAN="\033[0;36m"
        BOLD="\033[1m"
        DIM="\033[2m"
        RESET="\033[0m"
    fi
}

# ==============================================================================
# Logging Functions
# ==============================================================================

log_header() {
    echo ""
    echo -e "${BOLD}${BLUE}=== $1 ===${RESET}"
    echo ""
}

log_step() {
    echo -e "${CYAN}>>> $1${RESET}"
}

log_success() {
    echo -e "${GREEN}[PASS]${RESET} $1"
}

log_failure() {
    echo -e "${RED}[FAIL]${RESET} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${RESET} $1"
}

log_info() {
    echo -e "${DIM}$1${RESET}"
}

log_ci() {
    if [[ "${CI_MODE}" == "true" ]]; then
        echo "::$1::$2"
    fi
}

# ==============================================================================
# Utility Functions
# ==============================================================================

print_usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Pilot Space Quality Gate Script

Options:
    --backend-only     Run only backend (Python) checks
    --frontend-only    Run only frontend (TypeScript) checks
    --ci               CI mode: no colors, machine-readable output
    --parallel         Run backend and frontend checks in parallel
    --fix              Auto-fix linting issues where possible
    --verbose          Show detailed output from all commands
    -h, --help         Show this help message

Examples:
    $(basename "$0")                      # Run all checks
    $(basename "$0") --backend-only       # Backend only
    $(basename "$0") --ci --parallel      # CI with parallel execution
    $(basename "$0") --fix                # Run with auto-fix enabled

Exit Codes:
    0    All checks passed
    1    One or more checks failed
    2    Script error
EOF
}

check_dependencies() {
    local missing=()

    if [[ "${RUN_BACKEND}" == "true" ]]; then
        if ! command -v uv &> /dev/null; then
            missing+=("uv (Python package manager)")
        fi
    fi

    if [[ "${RUN_FRONTEND}" == "true" ]]; then
        if ! command -v pnpm &> /dev/null; then
            missing+=("pnpm (Node package manager)")
        fi
        if ! command -v node &> /dev/null; then
            missing+=("node (Node.js runtime)")
        fi
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${RED}Error: Missing required dependencies:${RESET}"
        for dep in "${missing[@]}"; do
            echo "  - ${dep}"
        done
        exit 2
    fi
}

format_duration() {
    local seconds=$1
    if [[ ${seconds} -lt 60 ]]; then
        echo "${seconds}s"
    else
        local minutes=$((seconds / 60))
        local remaining_seconds=$((seconds % 60))
        echo "${minutes}m ${remaining_seconds}s"
    fi
}

# ==============================================================================
# Backend Checks
# ==============================================================================

run_backend_checks() {
    log_header "Backend Quality Gates (Python)"

    if [[ ! -d "${BACKEND_DIR}" ]]; then
        log_failure "Backend directory not found: ${BACKEND_DIR}"
        return 1
    fi

    cd "${BACKEND_DIR}"

    # Check if virtual environment exists
    if [[ ! -d ".venv" ]]; then
        log_warning "Virtual environment not found. Running 'uv sync'..."
        uv sync --dev
    fi

    local backend_start=$(date +%s)

    # Ruff linting
    log_step "Running ruff check..."
    log_ci "group" "Backend Linting (ruff)"

    local ruff_cmd="uv run ruff check ."
    if [[ "${FIX_MODE}" == "true" ]]; then
        ruff_cmd="uv run ruff check . --fix"
    fi

    if ${ruff_cmd}; then
        BACKEND_LINT_STATUS=0
        log_success "Ruff linting passed"
    else
        BACKEND_LINT_STATUS=1
        log_failure "Ruff linting failed"
    fi
    log_ci "endgroup" ""

    # Pyright type checking
    log_step "Running pyright..."
    log_ci "group" "Backend Type Checking (pyright)"

    if uv run pyright; then
        BACKEND_TYPE_STATUS=0
        log_success "Pyright type checking passed"
    else
        BACKEND_TYPE_STATUS=1
        log_failure "Pyright type checking failed"
    fi
    log_ci "endgroup" ""

    # Pytest
    log_step "Running pytest..."
    log_ci "group" "Backend Tests (pytest)"

    local pytest_args="--cov=src/pilot_space --cov-report=term-missing"
    if [[ "${CI_MODE}" == "true" ]]; then
        pytest_args="${pytest_args} --cov-report=xml"
    fi
    if [[ "${VERBOSE}" == "true" ]]; then
        pytest_args="${pytest_args} -v"
    else
        pytest_args="${pytest_args} -q"
    fi

    if uv run pytest ${pytest_args}; then
        BACKEND_TEST_STATUS=0
        log_success "Pytest tests passed"
    else
        BACKEND_TEST_STATUS=1
        log_failure "Pytest tests failed"
    fi
    log_ci "endgroup" ""

    local backend_end=$(date +%s)
    local backend_duration=$((backend_end - backend_start))
    log_info "Backend checks completed in $(format_duration ${backend_duration})"

    cd "${PROJECT_ROOT}"
}

# ==============================================================================
# Frontend Checks
# ==============================================================================

run_frontend_checks() {
    log_header "Frontend Quality Gates (TypeScript)"

    if [[ ! -d "${FRONTEND_DIR}" ]]; then
        log_failure "Frontend directory not found: ${FRONTEND_DIR}"
        return 1
    fi

    cd "${FRONTEND_DIR}"

    # Check if node_modules exists
    if [[ ! -d "node_modules" ]]; then
        log_warning "node_modules not found. Running 'pnpm install'..."
        pnpm install --frozen-lockfile
    fi

    local frontend_start=$(date +%s)

    # ESLint
    log_step "Running lint..."
    log_ci "group" "Frontend Linting (ESLint)"

    local lint_cmd="pnpm lint"
    if [[ "${FIX_MODE}" == "true" ]]; then
        lint_cmd="pnpm lint:fix"
    fi

    if ${lint_cmd}; then
        FRONTEND_LINT_STATUS=0
        log_success "ESLint linting passed"
    else
        FRONTEND_LINT_STATUS=1
        log_failure "ESLint linting failed"
    fi
    log_ci "endgroup" ""

    # TypeScript type checking
    log_step "Running type-check..."
    log_ci "group" "Frontend Type Checking (tsc)"

    if pnpm type-check; then
        FRONTEND_TYPE_STATUS=0
        log_success "TypeScript type checking passed"
    else
        FRONTEND_TYPE_STATUS=1
        log_failure "TypeScript type checking failed"
    fi
    log_ci "endgroup" ""

    # Vitest
    log_step "Running tests..."
    log_ci "group" "Frontend Tests (vitest)"

    local test_cmd="pnpm test"
    if [[ "${CI_MODE}" == "true" ]]; then
        test_cmd="pnpm test:coverage"
    fi

    if ${test_cmd}; then
        FRONTEND_TEST_STATUS=0
        log_success "Vitest tests passed"
    else
        FRONTEND_TEST_STATUS=1
        log_failure "Vitest tests failed"
    fi
    log_ci "endgroup" ""

    local frontend_end=$(date +%s)
    local frontend_duration=$((frontend_end - frontend_start))
    log_info "Frontend checks completed in $(format_duration ${frontend_duration})"

    cd "${PROJECT_ROOT}"
}

# ==============================================================================
# Summary Report
# ==============================================================================

print_summary() {
    local end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))

    log_header "Quality Gate Summary"

    echo ""
    printf "%-25s %s\n" "Check" "Status"
    printf "%-25s %s\n" "-------------------------" "------"

    if [[ "${RUN_BACKEND}" == "true" ]]; then
        if [[ ${BACKEND_LINT_STATUS} -eq 0 ]]; then
            printf "%-25s ${GREEN}%s${RESET}\n" "Backend Lint (ruff)" "PASS"
        else
            printf "%-25s ${RED}%s${RESET}\n" "Backend Lint (ruff)" "FAIL"
        fi

        if [[ ${BACKEND_TYPE_STATUS} -eq 0 ]]; then
            printf "%-25s ${GREEN}%s${RESET}\n" "Backend Types (pyright)" "PASS"
        else
            printf "%-25s ${RED}%s${RESET}\n" "Backend Types (pyright)" "FAIL"
        fi

        if [[ ${BACKEND_TEST_STATUS} -eq 0 ]]; then
            printf "%-25s ${GREEN}%s${RESET}\n" "Backend Tests (pytest)" "PASS"
        else
            printf "%-25s ${RED}%s${RESET}\n" "Backend Tests (pytest)" "FAIL"
        fi
    fi

    if [[ "${RUN_FRONTEND}" == "true" ]]; then
        if [[ ${FRONTEND_LINT_STATUS} -eq 0 ]]; then
            printf "%-25s ${GREEN}%s${RESET}\n" "Frontend Lint (ESLint)" "PASS"
        else
            printf "%-25s ${RED}%s${RESET}\n" "Frontend Lint (ESLint)" "FAIL"
        fi

        if [[ ${FRONTEND_TYPE_STATUS} -eq 0 ]]; then
            printf "%-25s ${GREEN}%s${RESET}\n" "Frontend Types (tsc)" "PASS"
        else
            printf "%-25s ${RED}%s${RESET}\n" "Frontend Types (tsc)" "FAIL"
        fi

        if [[ ${FRONTEND_TEST_STATUS} -eq 0 ]]; then
            printf "%-25s ${GREEN}%s${RESET}\n" "Frontend Tests (vitest)" "PASS"
        else
            printf "%-25s ${RED}%s${RESET}\n" "Frontend Tests (vitest)" "FAIL"
        fi
    fi

    echo ""
    log_info "Total time: $(format_duration ${total_duration})"
    echo ""

    # Calculate overall status
    local total_failures=$((
        BACKEND_LINT_STATUS + BACKEND_TYPE_STATUS + BACKEND_TEST_STATUS +
        FRONTEND_LINT_STATUS + FRONTEND_TYPE_STATUS + FRONTEND_TEST_STATUS
    ))

    if [[ ${total_failures} -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}All quality gates passed!${RESET}"
        if [[ "${CI_MODE}" == "true" ]]; then
            echo "::notice::All quality gates passed"
        fi
        return 0
    else
        echo -e "${RED}${BOLD}${total_failures} quality gate(s) failed!${RESET}"
        if [[ "${CI_MODE}" == "true" ]]; then
            echo "::error::${total_failures} quality gate(s) failed"
        fi
        return 1
    fi
}

# ==============================================================================
# Parallel Execution
# ==============================================================================

run_parallel() {
    log_header "Running Quality Gates in Parallel"

    local backend_log=$(mktemp)
    local frontend_log=$(mktemp)
    local backend_pid=""
    local frontend_pid=""

    trap "rm -f ${backend_log} ${frontend_log}" EXIT

    if [[ "${RUN_BACKEND}" == "true" ]]; then
        (run_backend_checks) > "${backend_log}" 2>&1 &
        backend_pid=$!
        log_info "Started backend checks (PID: ${backend_pid})"
    fi

    if [[ "${RUN_FRONTEND}" == "true" ]]; then
        (run_frontend_checks) > "${frontend_log}" 2>&1 &
        frontend_pid=$!
        log_info "Started frontend checks (PID: ${frontend_pid})"
    fi

    # Wait for backend
    if [[ -n "${backend_pid}" ]]; then
        if wait "${backend_pid}"; then
            log_success "Backend checks completed"
        else
            log_failure "Backend checks failed"
        fi
        echo ""
        cat "${backend_log}"
    fi

    # Wait for frontend
    if [[ -n "${frontend_pid}" ]]; then
        if wait "${frontend_pid}"; then
            log_success "Frontend checks completed"
        else
            log_failure "Frontend checks failed"
        fi
        echo ""
        cat "${frontend_log}"
    fi
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backend-only)
                RUN_BACKEND=true
                RUN_FRONTEND=false
                shift
                ;;
            --frontend-only)
                RUN_BACKEND=false
                RUN_FRONTEND=true
                shift
                ;;
            --ci)
                CI_MODE=true
                shift
                ;;
            --parallel)
                PARALLEL_MODE=true
                shift
                ;;
            --fix)
                FIX_MODE=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                print_usage
                exit 2
                ;;
        esac
    done

    # Setup colors after parsing CI flag
    setup_colors

    echo -e "${BOLD}Pilot Space Quality Gate${RESET}"
    echo -e "${DIM}Running quality checks for backend and frontend${RESET}"
    echo ""

    # Check dependencies
    check_dependencies

    # Change to project root
    cd "${PROJECT_ROOT}"

    # Run checks
    if [[ "${PARALLEL_MODE}" == "true" ]]; then
        run_parallel
    else
        if [[ "${RUN_BACKEND}" == "true" ]]; then
            run_backend_checks
        fi

        if [[ "${RUN_FRONTEND}" == "true" ]]; then
            run_frontend_checks
        fi
    fi

    # Print summary and exit
    print_summary
}

main "$@"
