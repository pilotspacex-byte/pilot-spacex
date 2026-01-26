# E2E Test Suite for AI Features (T095-T098)

## Overview

This directory contains end-to-end tests for the four main AI streaming features in Pilot Space:

- **T095**: Ghost Text Suggestions (SSE streaming)
- **T096**: AI Context Generation (5-phase streaming)
- **T097**: PR Review (5-aspect streaming)
- **T098**: Issue Extraction with Approval Flow

## Test Structure

```
tests/e2e/ai/
├── conftest.py                    # Shared fixtures (client, auth, test data)
├── test_ghost_text_e2e.py        # T095: Ghost text streaming tests
├── test_ai_context_e2e.py        # T096: AI context generation tests
├── test_pr_review_e2e.py         # T097: PR review streaming tests
└── test_issue_extraction_e2e.py  # T098: Issue extraction + approval tests
```

## Test Coverage

### T095: Ghost Text E2E (`test_ghost_text_e2e.py`)

Tests the ghost text suggestion streaming endpoint at `POST /api/v1/notes/{note_id}/ghost-text`.

**Test Cases:**
1. `test_full_ghost_text_flow` - Verify complete SSE streaming flow with token events
2. `test_ghost_text_latency` - Verify P95 latency < 2s requirement
3. `test_ghost_text_streaming_endpoint_exists` - Verify endpoint registration
4. `test_ghost_text_handles_errors` - Verify error handling for missing workspace ID
5. `test_ghost_text_validation` - Verify request validation (empty context)

**Expected Behavior:**
- Endpoint: `POST /api/v1/notes/{note_id}/ghost-text`
- Request body: `{ "context": str, "cursor_position": int }`
- Response: SSE stream with `token`, `done`, and `error` events
- Performance: P95 latency < 2s

### T096: AI Context Generation E2E (`test_ai_context_e2e.py`)

Tests the AI context streaming endpoint at `POST /api/v1/issues/{issue_id}/ai-context/stream`.

**Test Cases:**
1. `test_full_ai_context_flow` - Verify all 5 phases complete
2. `test_ai_context_includes_claude_code_prompt` - Verify Claude Code prompt in output
3. `test_ai_context_get_endpoint` - Test GET endpoint for retrieving existing context
4. `test_ai_context_handles_missing_issue` - Verify error handling for non-existent issue
5. `test_ai_context_latency` - Verify completion within 60s
6. `test_ai_context_progress_updates` - Verify progress/phase events

**Expected Behavior:**
- Endpoint: `POST /api/v1/issues/{issue_id}/ai-context/stream`
- Response: SSE stream with 5 phases:
  1. Analysis
  2. Related Docs
  3. Tasks
  4. Code Search
  5. Summary
- Final event includes Claude Code prompt and context data

### T097: PR Review E2E (`test_pr_review_e2e.py`)

Tests the PR review streaming endpoint at `POST /api/v1/ai/repos/{repo_id}/prs/{pr_number}/review`.

**Test Cases:**
1. `test_full_pr_review_flow` - Verify review job creation and status polling
2. `test_pr_review_streaming_results` - Test queue-based async processing
3. `test_pr_review_handles_large_prs` - Test file prioritization for large PRs
4. `test_pr_review_requires_authentication` - Verify auth requirement
5. `test_pr_review_validation` - Test request validation
6. `test_pr_review_status_polling` - Test status endpoint
7. `test_pr_review_result_structure` - Verify 5-aspect result structure

**Expected Behavior:**
- Endpoint: `POST /api/v1/ai/repos/{repo_id}/prs/{pr_number}/review`
- Request body: `{ "repository": str, "force_refresh": bool }`
- Response: SSE stream with 5 aspects:
  1. Architecture
  2. Security
  3. Quality
  4. Performance
  5. Documentation
- Token usage and cost tracking included

### T098: Issue Extraction E2E (`test_issue_extraction_e2e.py`)

Tests the issue extraction endpoint at `POST /api/v1/notes/{note_id}/extract-issues` and approval flow.

**Test Cases:**
1. `test_extraction_creates_approval_request` - Verify extraction creates approval (DD-003)
2. `test_approval_creates_issues` - Verify approval creates issues
3. `test_rejection_does_not_create_issues` - Test rejection flow
4. `test_extraction_with_confidence_tags` - Verify confidence tags (DD-048)
5. `test_approval_list_endpoint` - Test listing approvals
6. `test_approval_detail_endpoint` - Test getting approval details
7. `test_approval_expiration` - Test expired approval handling
8. `test_extraction_progress_events` - Verify progress events
9. `test_partial_approval_selection` - Test selecting specific issues to create

**Expected Behavior:**
- Extraction endpoint: `POST /api/v1/notes/{note_id}/extract-issues`
- Response: SSE stream with `progress`, `issue`, and `complete` events
- Each issue includes confidence tags: `recommended`, `default`, `current`, `alternative`
- Approval required before issue creation (DD-003)
- Approval endpoint: `POST /api/v1/notes/{note_id}/extract-issues/approve`

## Fixtures

### `e2e_client`
AsyncClient for making HTTP requests to the FastAPI app.

### `auth_headers`
Authentication headers including:
- `X-Workspace-ID`: Demo workspace ID
- `X-Anthropic-API-Key`: Test Anthropic key
- `X-Google-API-Key`: Test Google key
- `X-OpenAI-API-Key`: Test OpenAI key

### `test_note`
Mock Note object with TipTap content.

### `test_issue`
Mock Issue object for AI context generation tests.

### `test_repo`
Mock Repository object for PR review tests.

### `test_pr`
Mock Pull Request object.

### `test_approval`
Mock Approval request object.

## Running Tests

### Run all E2E tests:
```bash
uv run pytest tests/e2e/ai/ -v
```

### Run specific test file:
```bash
uv run pytest tests/e2e/ai/test_ghost_text_e2e.py -v
```

### Run specific test:
```bash
uv run pytest tests/e2e/ai/test_ghost_text_e2e.py::TestGhostTextE2E::test_full_ghost_text_flow -v
```

### Run with coverage:
```bash
uv run pytest tests/e2e/ai/ --cov=pilot_space.api.v1.routers --cov-report=term-missing
```

## Known Issues

### 1. DI Container Initialization
**Issue**: Tests fail with "DI container not initialized" error.

**Fix**: The `conftest.py` has been updated to initialize the container in `app.state` before creating the test client.

### 2. IssueExtractorAgent Constructor
**Issue**: `IssueExtractorAgent` requires `key_storage` parameter but container registers it with `deps_base`.

**Fix Required**: Update `backend/src/pilot_space/container.py` line 273:
```python
# Before
orchestrator.register_agent(
    AgentName.ISSUE_EXTRACTOR,
    IssueExtractorAgent(**deps_base),  # ❌ Missing key_storage
)

# After
orchestrator.register_agent(
    AgentName.ISSUE_EXTRACTOR,
    IssueExtractorAgent(**deps_with_key),  # ✅ Includes key_storage
)
```

### 3. Endpoint Path Corrections
**Status**: Fixed ✅

The following endpoint paths were corrected:
- Ghost text: `/api/v1/ai/ghost-text` → `/api/v1/notes/{note_id}/ghost-text`
- AI context: `/api/v1/issues/{issue_id}/ai-context/regenerate` → `/api/v1/issues/{issue_id}/ai-context/stream`
- Issue extraction: `/api/v1/ai/notes/{note_id}/extract-issues` → `/api/v1/notes/{note_id}/extract-issues`

## Integration with CI/CD

These E2E tests should be run:
1. On every PR to main/master
2. Before deployment to staging/production
3. As part of nightly regression suite

### Quality Gates

All E2E tests must pass before merge:
- ✅ No failures
- ✅ No skipped tests (unless explicitly marked)
- ✅ Performance assertions met (latency requirements)
- ✅ SSE streaming behavior verified

## Next Steps

1. **Fix Container Bug**: Update `container.py` to pass `deps_with_key` to `IssueExtractorAgent`
2. **Database Setup**: Add test database fixtures for full E2E testing
3. **Mock Provider**: Configure mock AI provider for consistent test responses
4. **Performance Baselines**: Establish baseline metrics for latency tests
5. **CI Integration**: Add E2E tests to GitHub Actions workflow

## Related Documentation

- **Architecture**: `/docs/architect/ai-layer.md`
- **API Spec**: `/specs/001-pilot-space-mvp/spec.md`
- **Design Decisions**: `/docs/DESIGN_DECISIONS.md` (DD-003, DD-048, DD-066)
- **Frontend Integration**:
  - `/frontend/src/stores/ai/GhostTextStore.ts`
  - `/frontend/src/stores/ai/MarginAnnotationStore.ts`
  - `/frontend/src/stores/ai/PRReviewStore.ts`
