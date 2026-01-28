# PilotSpace Validation Makefile
# Systematic test execution following the validation plan

.PHONY: help test-infra test-api test-integration test-e2e test-perf test-validate test-feature-* install-deps

# Default target
help:
	@echo "PilotSpace Test Validation Targets"
	@echo "==================================="
	@echo ""
	@echo "Level 0: Infrastructure Tests (No dependencies)"
	@echo "  make test-infra           Run infrastructure tests (DB, Redis, Meilisearch, Auth, Sandbox)"
	@echo ""
	@echo "Level 1: API Tests (Requires infrastructure)"
	@echo "  make test-api             Run all API tests"
	@echo "  make test-api-sdk-config  Run SDK config API tests"
	@echo "  make test-api-skills      Run skills API tests"
	@echo "  make test-api-chat        Run chat API tests"
	@echo "  make test-api-subagents   Run subagent API tests"
	@echo "  make test-api-sessions    Run session API tests"
	@echo "  make test-api-approvals   Run approval API tests"
	@echo ""
	@echo "Level 2: Integration Tests (Requires API)"
	@echo "  make test-integration     Run frontend-backend integration tests"
	@echo ""
	@echo "Level 3: E2E Tests (Requires integration)"
	@echo "  make test-e2e             Run all E2E tests"
	@echo "  make test-e2e-chat        Run chat flow E2E tests"
	@echo "  make test-e2e-skills      Run skill invocation E2E tests"
	@echo "  make test-e2e-subagents   Run subagent delegation E2E tests"
	@echo "  make test-e2e-approvals   Run approval workflow E2E tests"
	@echo "  make test-e2e-sessions    Run session persistence E2E tests"
	@echo "  make test-e2e-ghost-text  Run ghost text E2E tests"
	@echo ""
	@echo "Level 3: Performance Tests (Requires integration)"
	@echo "  make test-perf            Run performance tests"
	@echo ""
	@echo "Full Validation Suite"
	@echo "  make test-validate        Run all tests sequentially (infra → api → integration → e2e → perf)"
	@echo "  make test-validate-quick  Run all tests in parallel (faster but no dependency order)"
	@echo ""
	@echo "Feature-specific Tests"
	@echo "  make test-feature-chat    Run all chat-related tests (API + E2E)"
	@echo "  make test-feature-skills  Run all skills tests (API + E2E)"
	@echo "  make test-feature-sessions Run all session tests (API + E2E)"
	@echo "  make test-feature-approvals Run all approval tests (API + E2E)"
	@echo ""
	@echo "Quality Gates"
	@echo "  make quality-gates-backend Run pyright + ruff + pytest with coverage"
	@echo "  make quality-gates-frontend Run eslint + type-check + test"
	@echo ""
	@echo "Utilities"
	@echo "  make install-deps         Install all dependencies (backend + frontend)"
	@echo "  make test-results-dir     Create test results directory"

# ============================================================================
# Dependencies
# ============================================================================

install-deps:
	@echo "Installing backend dependencies..."
	cd backend && uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && pnpm install

test-results-dir:
	@mkdir -p test-results

# ============================================================================
# Level 0: Infrastructure Tests
# ============================================================================

test-infra: test-results-dir
	@echo "Running infrastructure tests..."
	cd backend && uv run pytest tests/infrastructure/ -v --tb=short -m infrastructure 2>&1 | tee ../test-results/infra.log
	@echo "Infrastructure test results saved to test-results/infra.log"

# ============================================================================
# Level 1: API Tests
# ============================================================================

test-api: test-results-dir
	@echo "Running all API tests..."
	cd backend && uv run pytest tests/api/ -v --tb=short -m api 2>&1 | tee ../test-results/api.log
	@echo "API test results saved to test-results/api.log"

test-api-sdk-config: test-results-dir
	@echo "Running SDK config API tests..."
	cd backend && uv run pytest tests/api/test_sdk_config.py -v --tb=short -m api 2>&1 | tee ../test-results/api-sdk-config.log

test-api-skills: test-results-dir
	@echo "Running skills API tests..."
	cd backend && uv run pytest tests/api/test_skills.py -v --tb=short -m api 2>&1 | tee ../test-results/api-skills.log

test-api-chat: test-results-dir
	@echo "Running chat API tests..."
	cd backend && uv run pytest tests/api/test_chat.py -v --tb=short -m api 2>&1 | tee ../test-results/api-chat.log

test-api-subagents: test-results-dir
	@echo "Running subagent API tests..."
	cd backend && uv run pytest tests/api/test_subagents.py -v --tb=short -m api 2>&1 | tee ../test-results/api-subagents.log

test-api-sessions: test-results-dir
	@echo "Running session API tests..."
	cd backend && uv run pytest tests/api/test_sessions.py -v --tb=short -m api 2>&1 | tee ../test-results/api-sessions.log

test-api-approvals: test-results-dir
	@echo "Running approval API tests..."
	cd backend && uv run pytest tests/api/test_approvals.py -v --tb=short -m api 2>&1 | tee ../test-results/api-approvals.log

# ============================================================================
# Level 2: Integration Tests
# ============================================================================

test-integration: test-results-dir
	@echo "Running frontend-backend integration tests..."
	cd frontend && pnpm test:integration 2>&1 | tee ../test-results/integration.log
	@echo "Integration test results saved to test-results/integration.log"

# ============================================================================
# Level 3: E2E Tests
# ============================================================================

test-e2e: test-results-dir
	@echo "Running all E2E tests..."
	cd backend && uv run pytest tests/e2e/ -v --tb=short -m e2e 2>&1 | tee ../test-results/e2e.log
	@echo "E2E test results saved to test-results/e2e.log"

test-e2e-chat: test-results-dir
	@echo "Running chat flow E2E tests..."
	cd backend && uv run pytest tests/e2e/test_chat_flow.py -v --tb=short -m e2e 2>&1 | tee ../test-results/e2e-chat.log

test-e2e-skills: test-results-dir
	@echo "Running skill invocation E2E tests..."
	cd backend && uv run pytest tests/e2e/test_skill_invocation.py -v --tb=short -m e2e 2>&1 | tee ../test-results/e2e-skills.log

test-e2e-subagents: test-results-dir
	@echo "Running subagent delegation E2E tests..."
	cd backend && uv run pytest tests/e2e/test_subagent_delegation.py -v --tb=short -m e2e 2>&1 | tee ../test-results/e2e-subagents.log

test-e2e-approvals: test-results-dir
	@echo "Running approval workflow E2E tests..."
	cd backend && uv run pytest tests/e2e/test_approval_workflow.py -v --tb=short -m e2e 2>&1 | tee ../test-results/e2e-approvals.log

test-e2e-sessions: test-results-dir
	@echo "Running session persistence E2E tests..."
	cd backend && uv run pytest tests/e2e/test_session_persistence.py -v --tb=short -m e2e 2>&1 | tee ../test-results/e2e-sessions.log

test-e2e-ghost-text: test-results-dir
	@echo "Running ghost text E2E tests..."
	cd backend && uv run pytest tests/e2e/test_ghost_text_complete.py -v --tb=short -m e2e 2>&1 | tee ../test-results/e2e-ghost-text.log

# ============================================================================
# Level 3: Performance Tests
# ============================================================================

test-perf: test-results-dir
	@echo "Running performance tests..."
	cd backend && uv run pytest tests/performance/ -v --tb=short -m performance --benchmark-only 2>&1 | tee ../test-results/perf.log
	@echo "Performance test results saved to test-results/perf.log"

# ============================================================================
# Full Validation Suite
# ============================================================================

test-validate: test-results-dir
	@echo "Running full validation suite (sequential)..."
	@echo "Step 1/5: Infrastructure tests..."
	$(MAKE) test-infra
	@echo ""
	@echo "Step 2/5: API tests..."
	$(MAKE) test-api
	@echo ""
	@echo "Step 3/5: Integration tests..."
	$(MAKE) test-integration
	@echo ""
	@echo "Step 4/5: E2E tests..."
	$(MAKE) test-e2e
	@echo ""
	@echo "Step 5/5: Performance tests..."
	$(MAKE) test-perf
	@echo ""
	@echo "✅ Full validation suite complete!"
	@echo "Results saved to test-results/"

test-validate-quick: test-results-dir
	@echo "Running full validation suite (parallel)..."
	cd backend && uv run pytest tests/ -v --tb=short -n auto 2>&1 | tee ../test-results/validate-quick.log
	@echo "Quick validation results saved to test-results/validate-quick.log"

# ============================================================================
# Feature-specific Tests
# ============================================================================

test-feature-chat: test-results-dir
	@echo "Running all chat-related tests..."
	cd backend && uv run pytest tests/api/test_chat.py tests/e2e/test_chat_flow.py -v --tb=short 2>&1 | tee ../test-results/feature-chat.log

test-feature-skills: test-results-dir
	@echo "Running all skills tests..."
	cd backend && uv run pytest tests/api/test_skills.py tests/e2e/test_skill_invocation.py -v --tb=short 2>&1 | tee ../test-results/feature-skills.log

test-feature-sessions: test-results-dir
	@echo "Running all session tests..."
	cd backend && uv run pytest tests/api/test_sessions.py tests/e2e/test_session_persistence.py -v --tb=short 2>&1 | tee ../test-results/feature-sessions.log

test-feature-approvals: test-results-dir
	@echo "Running all approval tests..."
	cd backend && uv run pytest tests/api/test_approvals.py tests/e2e/test_approval_workflow.py -v --tb=short 2>&1 | tee ../test-results/feature-approvals.log

# ============================================================================
# Quality Gates
# ============================================================================

quality-gates-backend:
	@echo "Running backend quality gates..."
	cd backend && uv run pyright && uv run ruff check && uv run pytest --cov=.
	@echo "✅ Backend quality gates passed!"

quality-gates-frontend:
	@echo "Running frontend quality gates..."
	cd frontend && pnpm lint && pnpm type-check && pnpm test
	@echo "✅ Frontend quality gates passed!"
