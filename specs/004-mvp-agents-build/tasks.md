# Tasks: MVP AI Agents Build with Claude Agent SDK

**Source**: `/specs/004-mvp-agents-build/`
**Required**: plan.md, spec.md
**Optional**: research.md, data-model.md, contracts/, quickstart.md
**Generated**: 2026-01-25

---

## Task Format

```
- [ ] [ID] [P?] [Story?] Description with exact file path
```

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable (different files, no dependencies) |
| `[USn]` | User story label (Phase 3+ only) |

---

## Phase 1: Setup → [P1-T001-T005](tasks/P1-T001-T005.md)

Project initialization and SDK infrastructure setup.

- [ ] T001 Install claude-agent-sdk dependency in backend/pyproject.toml with version constraint >=1.0,<2.0 → [P1-T001-T005](tasks/P1-T001-T005.md)
- [ ] T002 Verify SDK installation with import test: `from claude_agent_sdk import query, ClaudeSDKClient` → [P1-T001-T005](tasks/P1-T001-T005.md)
- [ ] T003 [P] Create ai/tools/__init__.py module initialization → [P1-T001-T005](tasks/P1-T001-T005.md)
- [ ] T004 [P] Create ai/infrastructure/__init__.py module initialization → [P1-T001-T005](tasks/P1-T001-T005.md)
- [ ] T005 [P] Create ai/session/__init__.py module initialization → [P1-T001-T005](tasks/P1-T001-T005.md)

**Checkpoint**: SDK installed and module structure ready.

---

## Phase 2: Foundational - Database Migrations → [P2-T006-T010](tasks/P2-T006-T010.md)

Database schema for AI infrastructure (blocked by: none).

- [ ] T006 Create Alembic migration for workspace_api_keys table in backend/alembic/versions/xxx_add_workspace_api_keys.py → [P2-T006-T010](tasks/P2-T006-T010.md)
- [ ] T007 Create Alembic migration for ai_approval_requests table in backend/alembic/versions/xxx_add_ai_approval_requests.py → [P2-T006-T010](tasks/P2-T006-T010.md)
- [ ] T008 Create Alembic migration for ai_cost_records table in backend/alembic/versions/xxx_add_ai_cost_records.py → [P2-T006-T010](tasks/P2-T006-T010.md)
- [ ] T009 Create Alembic migration for ai_sessions table in backend/alembic/versions/xxx_add_ai_sessions.py → [P2-T006-T010](tasks/P2-T006-T010.md)
- [ ] T010 Run migrations and verify tables created: `uv run alembic upgrade head` → [P2-T006-T010](tasks/P2-T006-T010.md)

**Checkpoint**: Database schema ready for AI infrastructure.

---

## Phase 3: Foundational - Infrastructure Services → [P3-T011-T016](tasks/P3-T011-T016.md)

Core infrastructure services for AI layer (blocked by: T006-T010).

- [ ] T011 Implement SecureKeyStorage class in backend/src/pilot_space/ai/infrastructure/key_storage.py with Supabase Vault encryption (DD-002) → [P3-T011-T016](tasks/P3-T011-T016.md)
- [ ] T012 Implement ApprovalService class in backend/src/pilot_space/ai/infrastructure/approval.py with action classification (DD-003) → [P3-T011-T016](tasks/P3-T011-T016.md)
- [ ] T013 [P] Implement CostTracker class in backend/src/pilot_space/ai/infrastructure/cost_tracker.py with provider pricing → [P3-T011-T016](tasks/P3-T011-T016.md)
- [ ] T014 [P] Implement SessionManager class in backend/src/pilot_space/ai/session/session_manager.py with Redis storage → [P3-T011-T016](tasks/P3-T011-T016.md)
- [ ] T015 [P] Refactor ProviderSelector class in backend/src/pilot_space/ai/providers/provider_selector.py with DD-011 routing table → [P3-T011-T016](tasks/P3-T011-T016.md)
- [ ] T016 [P] Implement CircuitBreaker and retry in backend/src/pilot_space/ai/infrastructure/resilience.py → [P3-T011-T016](tasks/P3-T011-T016.md)

**Checkpoint**: Infrastructure services ready for agent integration.

---

## Phase 4: Foundational - MCP Tools → [P4-T017-T033](tasks/P4-T017-T033.md)

MCP tool definitions for agent data access (blocked by: T003).

- [ ] T017 Create MCP server factory in backend/src/pilot_space/ai/tools/mcp_server.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T018 Implement get_issue_context tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T019 [P] Implement get_note_content tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T020 [P] Implement get_project_context tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T021 [P] Implement find_similar_issues tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T022 [P] Implement get_workspace_members tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T023 [P] Implement get_page_content tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T024 [P] Implement get_cycle_context tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T025 Implement semantic_search tool in backend/src/pilot_space/ai/tools/search_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T026 [P] Implement search_codebase tool in backend/src/pilot_space/ai/tools/search_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T027 Implement get_pr_details tool in backend/src/pilot_space/ai/tools/github_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T028 [P] Implement get_pr_diff tool in backend/src/pilot_space/ai/tools/github_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T029 [P] Implement search_code_in_repo tool in backend/src/pilot_space/ai/tools/github_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T030 Implement create_note_annotation write tool in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T031 [P] Implement create_issue write tool (requires approval) in backend/src/pilot_space/ai/tools/database_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T032 [P] Implement post_pr_comment write tool in backend/src/pilot_space/ai/tools/github_tools.py → [P4-T017-T033](tasks/P4-T017-T033.md)
- [ ] T033 Register all tools in MCP server factory in backend/src/pilot_space/ai/tools/mcp_server.py → [P4-T017-T033](tasks/P4-T017-T033.md)

**Checkpoint**: 15 MCP tools available for agents (12 read-only, 3 write).

---

## Phase 5: Foundational - SDK Base & Orchestrator → [P5-T034-T037](tasks/P5-T034-T037.md)

SDK-based agent foundation (blocked by: T011-T017).

- [ ] T034 Create SDKBaseAgent abstract class in backend/src/pilot_space/ai/agents/sdk_base.py with _build_options helper → [P5-T034-T037](tasks/P5-T034-T037.md)
- [ ] T035 Create SDKOrchestrator class in backend/src/pilot_space/ai/sdk_orchestrator.py integrating all infrastructure → [P5-T034-T037](tasks/P5-T034-T037.md)
- [ ] T036 Update DI container in backend/src/pilot_space/container.py with new providers → [P5-T034-T037](tasks/P5-T034-T037.md)
- [ ] T037 Create SSE streaming helper in backend/src/pilot_space/api/v1/routers/ai.py (create_sse_stream function) → [P5-T034-T037](tasks/P5-T034-T037.md)

**Checkpoint**: SDK orchestrator ready, agents can be registered.

---

## Phase 6: User Story 1 - AI Context Generation (P1) 🎯 MVP → [T038-T043](tasks/T038-T043.md)

**Goal**: Developer gets comprehensive AI context for issue understanding with Claude Code prompts
**Verify**: Create issue → Request AI context → See streaming analysis with implementation guide

### Implementation

- [ ] T038 [US1] Migrate AIContextAgent to ClaudeSDKClient multi-turn in backend/src/pilot_space/ai/agents/ai_context_agent.py → [T038-T043](tasks/T038-T043.md)
- [ ] T039 [US1] Update prompts/ai_context.py with multi-turn system prompt in backend/src/pilot_space/ai/prompts/ai_context.py → [T038-T043](tasks/T038-T043.md)
- [ ] T040 [US1] Implement SSE endpoint POST /ai/issues/{issue_id}/context in backend/src/pilot_space/api/v1/routers/ai.py → [T038-T043](tasks/T038-T043.md)
- [ ] T041 [US1] Register AIContextAgent in SDKOrchestrator.agents dict in backend/src/pilot_space/ai/sdk_orchestrator.py → [T038-T043](tasks/T038-T043.md)
- [ ] T042 [P] [US1] Unit test AIContextAgent multi-turn in backend/tests/unit/ai/agents/test_ai_context_agent.py → [T038-T043](tasks/T038-T043.md)
- [ ] T043 [P] [US1] Integration test AI context endpoint in backend/tests/integration/ai/test_ai_context_endpoint.py → [T038-T043](tasks/T038-T043.md)

**Checkpoint**: US1 complete - AI context generation works with streaming phases.

---

## Phase 7: User Story 2 - Ghost Text Suggestions (P1) 🎯 MVP → [T044-T049](tasks/T044-T049.md)

**Goal**: Developer receives real-time text completions while writing notes (<2s latency)
**Verify**: Type in note → Pause 500ms → See ghost text suggestion → Tab to accept

### Architecture Decision: Claude Agent SDK with Haiku

Per DD-011 routing update, GhostTextAgent now uses Claude Agent SDK with `claude-3-5-haiku-20241022` model:
- **Rationale**: Unified SDK architecture, Haiku provides <1s latency for short completions
- **Model**: `claude-3-5-haiku-20241022` (fastest Claude model)
- **Max tokens**: 50 (short suggestions)
- **Timeout**: 2000ms hard limit
- **Fallback**: Return empty suggestion on timeout (graceful degradation)

### Implementation

- [ ] T044 [US2] Migrate GhostTextAgent to SDK query() with claude-3-5-haiku in backend/src/pilot_space/ai/agents/ghost_text_agent.py (includes: streaming via SDK async iterator, timeout handling with graceful degradation) → [T044-T049](tasks/T044-T049.md)
- [ ] T045 [US2] Update prompts/ghost_text.py for SDK format (50 token max) in backend/src/pilot_space/ai/prompts/ghost_text.py → [T044-T049](tasks/T044-T049.md)
- [ ] T046 [US2] Implement SSE endpoint POST /ai/notes/{note_id}/ghost-text in backend/src/pilot_space/api/v1/routers/ai.py → [T044-T049](tasks/T044-T049.md)
- [ ] T047 [US2] Register GhostTextAgent in SDKOrchestrator in backend/src/pilot_space/ai/sdk_orchestrator.py → [T044-T049](tasks/T044-T049.md)
- [ ] T048 [P] [US2] Unit test GhostTextAgent streaming in backend/tests/unit/ai/agents/test_ghost_text_agent.py → [T044-T049](tasks/T044-T049.md)
- [ ] T049 [P] [US2] Performance test ghost text <2s latency (p95) in backend/tests/performance/test_ghost_text_latency.py → [T044-T049](tasks/T044-T049.md)

**Checkpoint**: US2 complete - Ghost text appears within 2s of pause.

---

## Phase 8: User Story 3 - PR Review (P1) 🎯 MVP → [T050-T055](tasks/T050-T055.md)

**Goal**: Team lead gets unified AI PR review covering 5 aspects (DD-006)
**Verify**: Link GitHub repo → Create PR → Request AI review → See comprehensive analysis

### Implementation

- [ ] T050 [US3] Implement PRReviewAgent with SDK query() in backend/src/pilot_space/ai/agents/pr_review_agent.py → [T050-T055](tasks/T050-T055.md)
- [ ] T051 [US3] Create prompts/pr_review.py with 5-aspect system prompt (DD-006) in backend/src/pilot_space/ai/prompts/pr_review.py → [T050-T055](tasks/T050-T055.md)
- [ ] T052 [US3] Implement SSE endpoint POST /ai/prs/{pr_number}/review in backend/src/pilot_space/api/v1/routers/ai.py → [T050-T055](tasks/T050-T055.md)
- [ ] T053 [US3] Register PRReviewAgent in SDKOrchestrator in backend/src/pilot_space/ai/sdk_orchestrator.py → [T050-T055](tasks/T050-T055.md)
- [ ] T054 [P] [US3] Unit test PRReviewAgent with mock PR diff in backend/tests/unit/ai/agents/test_pr_review_agent.py → [T050-T055](tasks/T050-T055.md)
- [ ] T055 [P] [US3] Integration test PR review endpoint in backend/tests/integration/ai/test_pr_review_endpoint.py → [T050-T055](tasks/T050-T055.md)

**Checkpoint**: US3 complete - PR review generates 5-aspect analysis.

---

## Phase 9: User Story 4 - Issue Extraction (P2) → [P9-T056-T061](tasks/P9-T056-T061.md)

**Goal**: Developer extracts actionable issues from note content with confidence tags
**Verify**: Write note → Click Extract Issues → See issues with Recommended/Default/Alternative tags

### Implementation

- [ ] T056 [US4] Migrate IssueExtractorAgent to SDK query() in backend/src/pilot_space/ai/agents/issue_extractor_agent.py → [P9-T056-T061](tasks/P9-T056-T061.md)
- [ ] T057 [US4] Update prompts/issue_extraction.py with confidence tag output (DD-048) in backend/src/pilot_space/ai/prompts/issue_extraction.py → [P9-T056-T061](tasks/P9-T056-T061.md)
- [ ] T058 [US4] Implement SSE endpoint POST /ai/notes/{note_id}/extract-issues in backend/src/pilot_space/api/v1/routers/ai.py → [P9-T056-T061](tasks/P9-T056-T061.md)
- [ ] T059 [US4] Integrate approval flow for extracted issues in backend/src/pilot_space/ai/sdk_orchestrator.py → [P9-T056-T061](tasks/P9-T056-T061.md)
- [ ] T060 [P] [US4] Unit test IssueExtractorAgent with confidence tags in backend/tests/unit/ai/agents/test_issue_extractor_agent.py → [P9-T056-T061](tasks/P9-T056-T061.md)
- [ ] T061 [P] [US4] Integration test issue extraction with approval in backend/tests/integration/ai/test_issue_extraction_endpoint.py → [P9-T056-T061](tasks/P9-T056-T061.md)

**Checkpoint**: US4 complete - Issues extracted with confidence tags, approval required for creation.

---

## Phase 10: User Story 5 - Workspace AI Settings (P2) → [P10-T062-T066](tasks/P10-T062-T066.md)

**Goal**: Admin configures BYOK API keys and AI features for workspace
**Verify**: Open settings → Enter API keys → Save → See validation feedback

### Implementation

- [ ] T062 [US5] Implement GET /workspaces/{id}/ai/settings endpoint in backend/src/pilot_space/api/v1/routers/workspaces.py → [P10-T062-T066](tasks/P10-T062-T066.md)
- [ ] T063 [US5] Implement PUT /workspaces/{id}/ai/settings endpoint with key validation in backend/src/pilot_space/api/v1/routers/workspaces.py → [P10-T062-T066](tasks/P10-T062-T066.md)
- [ ] T064 [US5] Create Pydantic schemas WorkspaceAISettings, WorkspaceAISettingsUpdate in backend/src/pilot_space/api/v1/schemas/workspace.py → [P10-T062-T066](tasks/P10-T062-T066.md)
- [ ] T065 [P] [US5] Unit test key storage encryption in backend/tests/unit/ai/infrastructure/test_key_storage.py → [P10-T062-T066](tasks/P10-T062-T066.md)
- [ ] T066 [P] [US5] Integration test workspace AI settings in backend/tests/integration/ai/test_workspace_ai_settings.py → [P10-T062-T066](tasks/P10-T062-T066.md)

**Checkpoint**: US5 complete - API keys encrypted, validated, and feature toggles working.

---

## Phase 11: User Story 6 - Margin Annotations (P2) → [P11-T067-T072](tasks/P11-T067-T072.md)

**Goal**: Developer views AI suggestions in note margin
**Verify**: Focus note block → See annotations in right margin → Click for details

### Implementation

- [ ] T067 [US6] Migrate MarginAnnotationAgent to SDK query() in backend/src/pilot_space/ai/agents/margin_annotation_agent.py → [P11-T067-T072](tasks/P11-T067-T072.md)
- [ ] T068 [US6] Update prompts/margin_annotation.py for SDK format in backend/src/pilot_space/ai/prompts/margin_annotation.py → [P11-T067-T072](tasks/P11-T067-T072.md)
- [ ] T069 [US6] Implement SSE endpoint POST /ai/notes/{note_id}/annotations in backend/src/pilot_space/api/v1/routers/ai.py → [P11-T067-T072](tasks/P11-T067-T072.md)
- [ ] T070 [US6] Register MarginAnnotationAgent in SDKOrchestrator in backend/src/pilot_space/ai/sdk_orchestrator.py → [P11-T067-T072](tasks/P11-T067-T072.md)
- [ ] T071 [P] [US6] Unit test MarginAnnotationAgent in backend/tests/unit/ai/agents/test_margin_annotation_agent.py → [P11-T067-T072](tasks/P11-T067-T072.md)
- [ ] T072 [P] [US6] Integration test annotation endpoint in backend/tests/integration/ai/test_margin_annotation_endpoint.py → [P11-T067-T072](tasks/P11-T067-T072.md)

**Checkpoint**: US6 complete - Margin annotations generated with confidence scores.

---

## Phase 12: User Story 7 - Approval Queue (P3) → [P12-T073-T078](tasks/P12-T073-T078.md)

**Goal**: Admin reviews and resolves pending AI approval requests
**Verify**: Trigger approval-required action → Check queue → Approve → See action executed

### Implementation

- [ ] T073 [US7] Implement GET /ai/approvals endpoint with filtering in backend/src/pilot_space/api/v1/routers/ai.py → [P12-T073-T078](tasks/P12-T073-T078.md)
- [ ] T074 [US7] Implement POST /ai/approvals/{id}/resolve endpoint in backend/src/pilot_space/api/v1/routers/ai.py → [P12-T073-T078](tasks/P12-T073-T078.md)
- [ ] T075 [US7] Create Pydantic schemas AIApprovalRequest, ApprovalResolution in backend/src/pilot_space/api/v1/schemas/ai.py → [P12-T073-T078](tasks/P12-T073-T078.md)
- [ ] T076 [US7] Implement approval expiration cron job in backend/src/pilot_space/infrastructure/jobs/expire_approvals.py → [P12-T073-T078](tasks/P12-T073-T078.md)
- [ ] T077 [P] [US7] Unit test ApprovalService in backend/tests/unit/ai/infrastructure/test_approval_service.py → [P12-T073-T078](tasks/P12-T073-T078.md)
- [ ] T078 [P] [US7] Integration test approval flow in backend/tests/integration/ai/test_approval_flow.py → [P12-T073-T078](tasks/P12-T073-T078.md)

**Checkpoint**: US7 complete - Approval queue functional with expiration.

---

## Phase 13: Supporting Agents (P2) → [P13-T079-T090](tasks/P13-T079-T090.md)

Additional agents for enhanced AI capabilities (blocked by: T034-T037).

### Conversation Agent

- [ ] T079 [P] Migrate ConversationAgent to ClaudeSDKClient multi-turn in backend/src/pilot_space/ai/agents/conversation_agent.py → [P13-T079-T090](tasks/P13-T079-T090.md)
- [ ] T080 [P] Implement SSE endpoint POST /ai/conversation in backend/src/pilot_space/api/v1/routers/ai.py → [P13-T079-T090](tasks/P13-T079-T090.md)

### Documentation Agent

- [ ] T081 [P] Implement DocGeneratorAgent with SDK query() in backend/src/pilot_space/ai/agents/doc_generator_agent.py → [P13-T079-T090](tasks/P13-T079-T090.md)
- [ ] T082 [P] Create prompts/doc_generation.py in backend/src/pilot_space/ai/prompts/doc_generation.py → [P13-T079-T090](tasks/P13-T079-T090.md)

### Task Decomposer Agent

- [ ] T083 [P] Implement TaskDecomposerAgent with SDK query() in backend/src/pilot_space/ai/agents/task_decomposer_agent.py → [P13-T079-T090](tasks/P13-T079-T090.md)
- [ ] T084 [P] Create prompts/task_decomposition.py in backend/src/pilot_space/ai/prompts/task_decomposition.py → [P13-T079-T090](tasks/P13-T079-T090.md)

### Diagram Generator Agent

- [ ] T085 [P] Implement DiagramGeneratorAgent with SDK query() in backend/src/pilot_space/ai/agents/diagram_generator_agent.py → [P13-T079-T090](tasks/P13-T079-T090.md)
- [ ] T086 [P] Create prompts/diagram_generation.py in backend/src/pilot_space/ai/prompts/diagram_generation.py → [P13-T079-T090](tasks/P13-T079-T090.md)

### Issue Enhancement Agents

- [ ] T087 [P] Migrate IssueEnhancerAgent to SDK query() in backend/src/pilot_space/ai/agents/issue_enhancer_agent.py → [P13-T079-T090](tasks/P13-T079-T090.md)
- [ ] T088 [P] Migrate AssigneeRecommenderAgent to SDK query() in backend/src/pilot_space/ai/agents/assignee_recommender_agent.py → [P13-T079-T090](tasks/P13-T079-T090.md)
- [ ] T089 [P] Migrate DuplicateDetectorAgent to SDK query() in backend/src/pilot_space/ai/agents/duplicate_detector_agent.py → [P13-T079-T090](tasks/P13-T079-T090.md)

### Register All Agents

- [ ] T090 Register all supporting agents in SDKOrchestrator in backend/src/pilot_space/ai/sdk_orchestrator.py → [P13-T079-T090](tasks/P13-T079-T090.md)

**Checkpoint**: All 12 agents migrated and registered.

---

## Phase 14: Cost Tracking (P2) → [P14-T091-T094](tasks/P14-T091-T094.md)

AI usage analytics endpoints (blocked by: T013).

- [ ] T091 Implement GET /ai/costs/summary endpoint in backend/src/pilot_space/api/v1/routers/ai.py → [P14-T091-T094](tasks/P14-T091-T094.md)
- [ ] T092 Create Pydantic schema CostSummaryResponse in backend/src/pilot_space/api/v1/schemas/ai.py → [P14-T091-T094](tasks/P14-T091-T094.md)
- [ ] T093 [P] Unit test CostTracker aggregation in backend/tests/unit/ai/infrastructure/test_cost_tracker.py → [P14-T091-T094](tasks/P14-T091-T094.md)
- [ ] T094 [P] Integration test cost tracking endpoint in backend/tests/integration/ai/test_cost_tracking.py → [P14-T091-T094](tasks/P14-T091-T094.md)

**Checkpoint**: Cost analytics available per workspace/user/agent.

---

## Phase 15: Polish & Cleanup → [P15-T095-T110](tasks/P15-T095-T110.md)

Cross-cutting concerns and final cleanup.

### E2E Tests

- [ ] T095 [P] E2E test ghost text flow in backend/tests/e2e/ai/test_ghost_text_e2e.py → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T096 [P] E2E test AI context flow in backend/tests/e2e/ai/test_ai_context_e2e.py → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T097 [P] E2E test PR review flow in backend/tests/e2e/ai/test_pr_review_e2e.py → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T098 [P] E2E test issue extraction + approval flow in backend/tests/e2e/ai/test_issue_extraction_e2e.py → [P15-T095-T110](tasks/P15-T095-T110.md)

### Security Audit

- [ ] T099 Security audit: verify API keys never logged in backend/src/pilot_space/ai/ (grep for key patterns) → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T100 Security audit: verify approval bypass impossible for ALWAYS_REQUIRE_APPROVAL actions → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T101 Security audit: verify RLS policies on ai_* tables → [P15-T095-T110](tasks/P15-T095-T110.md)

### Performance Benchmarks

- [ ] T102 [P] Benchmark ghost text latency <2s (p95) in backend/tests/performance/test_latency_benchmarks.py → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T103 [P] Benchmark AI context <30s (p95) in backend/tests/performance/test_latency_benchmarks.py → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T104 [P] Benchmark SSE first token <1s in backend/tests/performance/test_latency_benchmarks.py → [P15-T095-T110](tasks/P15-T095-T110.md)

### Cleanup

- [ ] T105 Remove deprecated ai/orchestrator.py (replaced by sdk_orchestrator.py) → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T106 Remove deprecated ai/agents/base.py (replaced by sdk_base.py) → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T107 Update ai/__init__.py exports for new structure → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T108 Run quality gates: `uv run ruff check . && uv run pyright && uv run pytest --cov=pilot_space.ai` → [P15-T095-T110](tasks/P15-T095-T110.md)

### Documentation

- [ ] T109 [P] Update quickstart.md with final agent patterns → [P15-T095-T110](tasks/P15-T095-T110.md)
- [ ] T110 [P] Verify API contracts match implementation in specs/004-mvp-agents-build/contracts/ → [P15-T095-T110](tasks/P15-T095-T110.md)

**Checkpoint**: Feature complete, all quality gates pass, >80% coverage.

---

## Dependencies

### Phase Order

```
Setup (1) → Migrations (2) → Infrastructure (3) → MCP Tools (4) → SDK Base (5)
         ↓
    User Stories (6-12) can run in parallel after Phase 5
         ↓
    Supporting Agents (13) → Cost Tracking (14) → Polish (15)
```

### User Story Independence

- Each user story can start after Phase 5 (SDK Base) completes
- US1-US3 (P1) form MVP - prioritize these first
- US4-US7 (P2-P3) can run in parallel with each other

### Within Each Story

1. Agent implementation before endpoint
2. Prompts before agent (if updating)
3. Unit tests after implementation
4. Integration tests after endpoint

### Critical Path (MVP)

```
T001-T005 (Setup) → T006-T010 (Migrations) → T011-T016 (Infrastructure)
    → T017-T033 (MCP Tools) → T034-T037 (SDK Base)
    → T038-T043 (US1: AI Context) ← PRIMARY MVP
    → T044-T049 (US2: Ghost Text) ← PRIMARY MVP
    → T050-T055 (US3: PR Review) ← PRIMARY MVP
```

### Parallel Opportunities

Tasks marked `[P]` in the same phase can run concurrently:

```bash
# Phase 3 Infrastructure (parallel group)
T013 CostTracker | T014 SessionManager | T015 ProviderSelector | T016 Resilience

# Phase 4 MCP Tools (parallel group 1)
T019-T024 Database tools (after T018)

# Phase 4 MCP Tools (parallel group 2)
T025-T029 Search + GitHub tools

# Phase 13 Supporting Agents (all parallel)
T079-T089 All agent migrations

# Phase 15 E2E Tests (all parallel)
T095-T098 All E2E tests
```

---

## Implementation Strategy

### MVP First (Recommended)

1. **Phase 1-5**: Foundation (T001-T037)
2. **Phase 6**: US1 AI Context (T038-T043) - core value proposition
3. **Phase 7**: US2 Ghost Text (T044-T049) - Note-First differentiator
4. **Phase 8**: US3 PR Review (T050-T055) - developer productivity
5. **Deploy MVP** - validate with users
6. **Phase 9-15**: Remaining features

### Incremental Delivery

| Milestone | Tasks | Value Delivered |
|-----------|-------|-----------------|
| M1: Infrastructure | T001-T037 | SDK foundation ready |
| M2: AI Context MVP | T038-T043 | Issue understanding with Claude Code prompts |
| M3: Ghost Text MVP | T044-T049 | Real-time writing assistance |
| M4: PR Review MVP | T050-T055 | Unified code review |
| M5: Full P1 | T056-T066 | Issue extraction, workspace settings |
| M6: Full Feature | T067-T110 | All agents, approval queue, analytics |

---

## Notes

### Agent SDK Usage

- **All agents** use Claude Agent SDK (`query()` or `ClaudeSDKClient`) - unified architecture
- **GhostTextAgent**: SDK `query()` with `claude-3-5-haiku-20241022` for <2s latency (50 token max)
- **AIContextAgent**: SDK `ClaudeSDKClient` for multi-turn context building with MCP tools
- **PRReviewAgent**: SDK `query()` with `claude-opus-4-5` for comprehensive code analysis
- **IssueExtractorAgent**: SDK `query()` with `claude-sonnet-4` for extraction with confidence tags
- **MarginAnnotationAgent**: SDK `query()` with `claude-sonnet-4` for block suggestions

### Design Decisions

- Human approval required for issue creation (DD-003)
- SSE streaming for all AI responses (DD-066)
- Confidence tags (Recommended/Default/Alternative) for extracted suggestions (DD-048)
- API keys encrypted with Supabase Vault (DD-002)
- Provider routing per DD-011 (updated):
  - Code analysis → Claude Opus 4.5
  - General tasks → Claude Sonnet 4
  - Latency-sensitive → Claude Haiku (unified SDK, no Gemini)
  - Embeddings → OpenAI text-embedding-3-large (non-SDK)

### Frontend Architecture

- **State Management**: MobX stores for all AI features
- **SSE Handling**: Custom hooks with abort controller and reconnection
- **TipTap Extensions**: GhostText, MarginAnnotation as editor plugins
- **Real-time Updates**: Supabase subscriptions for approval queue

---

## Phase 16: Frontend Foundation - SSE & API Infrastructure → [P16-T111-T120](tasks/P16-T111-T120.md)

Frontend infrastructure for AI integration (blocked by: T037 SSE helper).

### SSE Client Utilities

- [ ] T111 Create SSE client utility in frontend/src/lib/sse-client.ts with reconnection and error handling → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T112 Create useSSEStream React hook in frontend/src/hooks/use-sse-stream.ts with abort controller → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T113 [P] Create AI API client in frontend/src/services/ai-api.ts with typed endpoints → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T114 [P] Create AI error types in frontend/src/types/ai-errors.ts matching backend exceptions → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T114a Implement abort controller for SSE cancellation in frontend/src/hooks/use-sse-stream.ts (FR-022 coverage) → [P16-T111-T120](tasks/P16-T111-T120.md)

### MobX AI Stores

- [ ] T115 Create AIStore root store in frontend/src/stores/ai-store.ts with agent state management → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T116 [P] Create GhostTextStore in frontend/src/stores/ghost-text-store.ts with debouncing → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T117 [P] Create AIContextStore in frontend/src/stores/ai-context-store.ts with session management → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T118 [P] Create ApprovalStore in frontend/src/stores/approval-store.ts with pending queue → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T119 [P] Create AISettingsStore in frontend/src/stores/ai-settings-store.ts for workspace config → [P16-T111-T120](tasks/P16-T111-T120.md)
- [ ] T120 Register AI stores in RootStore in frontend/src/stores/root-store.ts → [P16-T111-T120](tasks/P16-T111-T120.md)

**Checkpoint**: Frontend AI infrastructure ready for components.

---

## Phase 17: Frontend - Ghost Text Integration (US2) 🎯 MVP → [P17-T121-T131](tasks/P17-T121-T131.md)

**Goal**: Ghost text appears in note editor with Tab to accept
**Verify**: Type → Pause 500ms → See gray suggestion → Tab accepts → Esc dismisses

### TipTap Extension

- [ ] T121 [US2] Create GhostTextExtension TipTap extension in frontend/src/components/editor/extensions/ghost-text-extension.ts → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T122 [US2] Implement ghost text decoration plugin in frontend/src/components/editor/plugins/ghost-text-decoration.ts → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T123 [US2] Add keyboard handlers (Tab accept, Esc dismiss) in frontend/src/components/editor/extensions/ghost-text-extension.ts → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T124 [US2] Implement cursor position tracking for context in frontend/src/components/editor/extensions/ghost-text-extension.ts → [P17-T121-T131](tasks/P17-T121-T131.md)

### Store Integration

- [ ] T125 [US2] Implement GhostTextStore.requestSuggestion() with 500ms debounce in frontend/src/stores/ghost-text-store.ts → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T126 [US2] Implement GhostTextStore SSE streaming consumer in frontend/src/stores/ghost-text-store.ts → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T127 [US2] Add suggestion caching (last 10 contexts) in frontend/src/stores/ghost-text-store.ts → [P17-T121-T131](tasks/P17-T121-T131.md)

### Component Integration

- [ ] T128 [US2] Integrate GhostTextExtension in NoteEditor in frontend/src/features/notes/components/note-editor.tsx → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T129 [US2] Add ghost text toggle in editor toolbar in frontend/src/features/notes/components/editor-toolbar.tsx → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T130 [P] [US2] Unit test GhostTextStore in frontend/src/stores/__tests__/ghost-text-store.test.ts → [P17-T121-T131](tasks/P17-T121-T131.md)
- [ ] T131 [P] [US2] Component test GhostTextExtension in frontend/src/components/editor/extensions/__tests__/ghost-text-extension.test.ts → [P17-T121-T131](tasks/P17-T121-T131.md)

**Checkpoint**: US2 Frontend complete - Ghost text works in note editor.

---

## Phase 18: Frontend - AI Context Integration (US1) 🎯 MVP → [P18-T132-T142](tasks/P18-T132-T142.md)

**Goal**: Issue detail shows AI context panel with streaming analysis
**Verify**: Open issue → Click "Generate AI Context" → See streaming phases → Copy Claude Code prompt

### Components

- [ ] T132 [US1] Create AIContextPanel component in frontend/src/features/issues/components/ai-context-panel.tsx → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T133 [US1] Create AIContextStreaming component with phase indicators in frontend/src/features/issues/components/ai-context-streaming.tsx → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T134 [US1] Create ClaudeCodePromptCard with copy button in frontend/src/features/issues/components/claude-code-prompt-card.tsx → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T135 [US1] Create AIContextSidebar for issue detail in frontend/src/features/issues/components/ai-context-sidebar.tsx → [P18-T132-T142](tasks/P18-T132-T142.md)

### Store Integration

- [ ] T136 [US1] Implement AIContextStore.generateContext() SSE handler in frontend/src/stores/ai-context-store.ts → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T137 [US1] Implement AIContextStore session management in frontend/src/stores/ai-context-store.ts → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T138 [US1] Add context caching per issue in frontend/src/stores/ai-context-store.ts → [P18-T132-T142](tasks/P18-T132-T142.md)

### Page Integration

- [ ] T139 [US1] Integrate AIContextSidebar in IssueDetailPage in frontend/src/features/issues/pages/issue-detail-page.tsx → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T140 [US1] Add "Generate AI Context" button in issue header in frontend/src/features/issues/components/issue-header.tsx → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T141 [P] [US1] Unit test AIContextStore in frontend/src/stores/__tests__/ai-context-store.test.ts → [P18-T132-T142](tasks/P18-T132-T142.md)
- [ ] T142 [P] [US1] Component test AIContextPanel in frontend/src/features/issues/components/__tests__/ai-context-panel.test.tsx → [P18-T132-T142](tasks/P18-T132-T142.md)

**Checkpoint**: US1 Frontend complete - AI context panel works on issue detail.

---

## Phase 19: Frontend - PR Review Integration (US3) 🎯 MVP → [P19-T143-T153](tasks/P19-T143-T153.md)

**Goal**: PR detail shows AI review with 5-aspect analysis
**Verify**: Open PR → Click "Request AI Review" → See streaming review → View per-file comments

### Components

- [ ] T143 [US3] Create PRReviewPanel component in frontend/src/features/github/components/pr-review-panel.tsx → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T144 [US3] Create PRReviewStreaming component with aspect sections in frontend/src/features/github/components/pr-review-streaming.tsx → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T145 [US3] Create ReviewAspectCard (Architecture/Security/Quality/Performance/Docs) in frontend/src/features/github/components/review-aspect-card.tsx → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T146 [US3] Create PRReviewCostBadge with usage display in frontend/src/features/github/components/pr-review-cost-badge.tsx → [P19-T143-T153](tasks/P19-T143-T153.md)

### Store Integration

- [ ] T147 [US3] Create PRReviewStore in frontend/src/stores/pr-review-store.ts → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T148 [US3] Implement PRReviewStore.requestReview() SSE handler in frontend/src/stores/pr-review-store.ts → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T149 [US3] Add review caching per PR in frontend/src/stores/pr-review-store.ts → [P19-T143-T153](tasks/P19-T143-T153.md)

### Page Integration

- [ ] T150 [US3] Integrate PRReviewPanel in PRDetailPage in frontend/src/features/github/pages/pr-detail-page.tsx → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T151 [US3] Add "Request AI Review" button in PR header in frontend/src/features/github/components/pr-header.tsx → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T152 [P] [US3] Unit test PRReviewStore in frontend/src/stores/__tests__/pr-review-store.test.ts → [P19-T143-T153](tasks/P19-T143-T153.md)
- [ ] T153 [P] [US3] Component test PRReviewPanel in frontend/src/features/github/components/__tests__/pr-review-panel.test.tsx → [P19-T143-T153](tasks/P19-T143-T153.md)

**Checkpoint**: US3 Frontend complete - PR review panel works on PR detail.

---

## Phase 20: Frontend - Issue Extraction Integration (US4) → [P20-T154-T164](tasks/P20-T154-T164.md)

**Goal**: Note shows extracted issues with confidence tags and approval flow
**Verify**: Write note → Click "Extract Issues" → See issues with tags → Approve to create

### Components

- [ ] T154 [US4] Create IssueExtractionPanel component in frontend/src/features/notes/components/issue-extraction-panel.tsx → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T155 [US4] Create ExtractedIssueCard with confidence tag badge in frontend/src/features/notes/components/extracted-issue-card.tsx → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T156 [US4] Create ConfidenceTagBadge (Recommended/Default/Alternative) in frontend/src/components/ui/confidence-tag-badge.tsx → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T157 [US4] Create IssueExtractionApprovalModal in frontend/src/features/notes/components/issue-extraction-approval-modal.tsx → [P20-T154-T164](tasks/P20-T154-T164.md)

### Store Integration

- [ ] T158 [US4] Create IssueExtractionStore in frontend/src/stores/issue-extraction-store.ts → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T159 [US4] Implement IssueExtractionStore.extractIssues() SSE handler in frontend/src/stores/issue-extraction-store.ts → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T160 [US4] Implement approval flow integration in frontend/src/stores/issue-extraction-store.ts → [P20-T154-T164](tasks/P20-T154-T164.md)

### Page Integration

- [ ] T161 [US4] Add "Extract Issues" button in NoteEditor toolbar in frontend/src/features/notes/components/editor-toolbar.tsx → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T162 [US4] Integrate IssueExtractionPanel in NotePage in frontend/src/features/notes/pages/note-page.tsx → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T163 [P] [US4] Unit test IssueExtractionStore in frontend/src/stores/__tests__/issue-extraction-store.test.ts → [P20-T154-T164](tasks/P20-T154-T164.md)
- [ ] T164 [P] [US4] Component test IssueExtractionPanel in frontend/src/features/notes/components/__tests__/issue-extraction-panel.test.tsx → [P20-T154-T164](tasks/P20-T154-T164.md)

**Checkpoint**: US4 Frontend complete - Issue extraction with approval works.

---

## Phase 21: Frontend - Margin Annotations Integration (US6) → [P21-T165-T177](tasks/P21-T165-T177.md)

**Goal**: Note blocks show AI suggestions in right margin
**Verify**: Focus block → See margin annotations → Click for details → Apply suggestion

### TipTap Extension

- [ ] T165 [US6] Create MarginAnnotationExtension TipTap extension in frontend/src/components/editor/extensions/margin-annotation-extension.ts → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T166 [US6] Implement annotation positioning plugin in frontend/src/components/editor/plugins/annotation-positioning.ts → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T167 [US6] Add annotation click handlers in frontend/src/components/editor/extensions/margin-annotation-extension.ts → [P21-T165-T177](tasks/P21-T165-T177.md)

### Components

- [ ] T168 [US6] Create MarginAnnotationList component in frontend/src/features/notes/components/margin-annotation-list.tsx → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T169 [US6] Create AnnotationCard with type icon in frontend/src/features/notes/components/annotation-card.tsx → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T170 [US6] Create AnnotationDetailPopover in frontend/src/features/notes/components/annotation-detail-popover.tsx → [P21-T165-T177](tasks/P21-T165-T177.md)

### Store Integration

- [ ] T171 [US6] Create MarginAnnotationStore in frontend/src/stores/margin-annotation-store.ts → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T172 [US6] Implement MarginAnnotationStore.fetchAnnotations() in frontend/src/stores/margin-annotation-store.ts → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T173 [US6] Implement block→annotation mapping in frontend/src/stores/margin-annotation-store.ts → [P21-T165-T177](tasks/P21-T165-T177.md)

### Page Integration

- [ ] T174 [US6] Integrate MarginAnnotationExtension in NoteEditor in frontend/src/features/notes/components/note-editor.tsx → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T175 [US6] Add margin annotation sidebar in NotePage in frontend/src/features/notes/pages/note-page.tsx → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T176 [P] [US6] Unit test MarginAnnotationStore in frontend/src/stores/__tests__/margin-annotation-store.test.ts → [P21-T165-T177](tasks/P21-T165-T177.md)
- [ ] T177 [P] [US6] Component test MarginAnnotationList in frontend/src/features/notes/components/__tests__/margin-annotation-list.test.tsx → [P21-T165-T177](tasks/P21-T165-T177.md)

**Checkpoint**: US6 Frontend complete - Margin annotations visible and interactive.

---

## Phase 22: Frontend - Workspace AI Settings (US5) → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Goal**: Admin configures BYOK API keys and AI features
**Verify**: Open settings → Enter keys → Save → See validation → Toggle features

### Components

- [ ] T178 [US5] Create AISettingsPage in frontend/src/features/settings/pages/ai-settings-page.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T179 [US5] Create APIKeyForm component with validation in frontend/src/features/settings/components/api-key-form.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T180 [US5] Create APIKeyInput with show/hide toggle in frontend/src/features/settings/components/api-key-input.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T181 [US5] Create AIFeatureToggles component in frontend/src/features/settings/components/ai-feature-toggles.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T182 [US5] Create ProviderStatusCard with health indicator in frontend/src/features/settings/components/provider-status-card.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Store Integration

- [ ] T183 [US5] Implement AISettingsStore.loadSettings() in frontend/src/stores/ai-settings-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T184 [US5] Implement AISettingsStore.saveSettings() with validation in frontend/src/stores/ai-settings-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T185 [US5] Implement AISettingsStore.validateKey() per provider in frontend/src/stores/ai-settings-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Page Integration

- [ ] T186 [US5] Add AI Settings link in WorkspaceSettings navigation in frontend/src/features/settings/pages/workspace-settings-page.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T187 [P] [US5] Unit test AISettingsStore in frontend/src/stores/__tests__/ai-settings-store.test.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T188 [P] [US5] Component test APIKeyForm in frontend/src/features/settings/components/__tests__/api-key-form.test.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Checkpoint**: US5 Frontend complete - Workspace AI settings fully functional.

---

## Phase 23: Frontend - Approval Queue (US7) → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Goal**: Admin reviews and resolves pending AI approval requests
**Verify**: Trigger approval action → See in queue → Approve → Action executes

### Components

- [ ] T189 [US7] Create ApprovalQueuePage in frontend/src/features/settings/pages/approval-queue-page.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T190 [US7] Create ApprovalRequestCard component in frontend/src/features/settings/components/approval-request-card.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T191 [US7] Create ApprovalDetailModal with payload preview in frontend/src/features/settings/components/approval-detail-modal.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T192 [US7] Create ApprovalActionButtons (Approve/Reject) in frontend/src/features/settings/components/approval-action-buttons.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Store Integration

- [ ] T193 [US7] Implement ApprovalStore.loadPending() in frontend/src/stores/approval-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T194 [US7] Implement ApprovalStore.approve() / reject() in frontend/src/stores/approval-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T195 [US7] Add real-time updates via Supabase subscription in frontend/src/stores/approval-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Page Integration

- [ ] T196 [US7] Add Approval Queue link in WorkspaceSettings in frontend/src/features/settings/pages/workspace-settings-page.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T197 [US7] Add pending approval badge in sidebar navigation in frontend/src/components/layout/sidebar-navigation.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T198 [P] [US7] Unit test ApprovalStore in frontend/src/stores/__tests__/approval-store.test.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T199 [P] [US7] Component test ApprovalQueuePage in frontend/src/features/settings/pages/__tests__/approval-queue-page.test.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Checkpoint**: US7 Frontend complete - Approval queue with real-time updates.

---

## Phase 24: Frontend - Cost Dashboard → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Goal**: Admin views AI usage costs per workspace
**Verify**: Open cost dashboard → See usage by agent/user/day → Export data

### Components

- [ ] T200 Create AICostDashboardPage in frontend/src/features/settings/pages/ai-cost-dashboard-page.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T201 Create CostSummaryCard component in frontend/src/features/settings/components/cost-summary-card.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T202 Create CostByAgentChart (bar chart) in frontend/src/features/settings/components/cost-by-agent-chart.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T203 Create CostByUserTable with sorting in frontend/src/features/settings/components/cost-by-user-table.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T204 Create CostTrendChart (line chart) in frontend/src/features/settings/components/cost-trend-chart.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Store Integration

- [ ] T205 Create CostDashboardStore in frontend/src/stores/cost-dashboard-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T206 Implement CostDashboardStore.loadSummary() in frontend/src/stores/cost-dashboard-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T207 Implement date range filtering in frontend/src/stores/cost-dashboard-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Page Integration

- [ ] T208 Add Cost Dashboard link in WorkspaceSettings in frontend/src/features/settings/pages/workspace-settings-page.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T209 [P] Unit test CostDashboardStore in frontend/src/stores/__tests__/cost-dashboard-store.test.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T210 [P] Component test AICostDashboardPage in frontend/src/features/settings/pages/__tests__/ai-cost-dashboard-page.test.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Checkpoint**: Cost dashboard functional with charts and export.

---

## Phase 25: Frontend - Conversation Agent UI → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Goal**: User has multi-turn conversation with AI assistant
**Verify**: Open AI chat → Send message → See streaming response → Continue conversation

### Components

- [ ] T211 Create AIConversationPanel component in frontend/src/features/ai/components/ai-conversation-panel.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T212 Create ConversationMessageList in frontend/src/features/ai/components/conversation-message-list.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T213 Create ConversationMessage (user/assistant) in frontend/src/features/ai/components/conversation-message.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T214 Create ConversationInput with send button in frontend/src/features/ai/components/conversation-input.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T215 Create ConversationStreamingIndicator in frontend/src/features/ai/components/conversation-streaming-indicator.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Store Integration

- [ ] T216 Create ConversationStore in frontend/src/stores/conversation-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T217 Implement ConversationStore.sendMessage() SSE handler in frontend/src/stores/conversation-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T218 Implement conversation history management in frontend/src/stores/conversation-store.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

### Page Integration

- [ ] T219 Create AIConversationPage in frontend/src/features/ai/pages/ai-conversation-page.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T220 Add AI Chat link in global navigation in frontend/src/components/layout/global-navigation.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T221 [P] Unit test ConversationStore in frontend/src/stores/__tests__/conversation-store.test.ts → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)
- [ ] T222 [P] Component test AIConversationPanel in frontend/src/features/ai/components/__tests__/ai-conversation-panel.test.tsx → [P22-P25-T178-T222](tasks/P22-P25-T178-T222.md)

**Checkpoint**: Conversation UI with streaming and history.

---

## Phase 26: Frontend E2E Tests → [P26-T223-T236](tasks/P26-T223-T236.md)

End-to-end tests for all AI features (blocked by: all frontend phases).

### Ghost Text E2E

- [ ] T223 [P] E2E test ghost text suggestion appears in frontend/tests/e2e/ai/ghost-text.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T224 [P] E2E test Tab accepts ghost text in frontend/tests/e2e/ai/ghost-text.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T225 [P] E2E test Esc dismisses ghost text in frontend/tests/e2e/ai/ghost-text.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)

### AI Context E2E

- [ ] T226 [P] E2E test AI context panel opens in frontend/tests/e2e/ai/ai-context.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T227 [P] E2E test AI context streaming phases in frontend/tests/e2e/ai/ai-context.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T228 [P] E2E test Claude Code prompt copy in frontend/tests/e2e/ai/ai-context.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)

### PR Review E2E

- [ ] T229 [P] E2E test PR review panel opens in frontend/tests/e2e/ai/pr-review.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T230 [P] E2E test PR review 5 aspects displayed in frontend/tests/e2e/ai/pr-review.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)

### Issue Extraction E2E

- [ ] T231 [P] E2E test issue extraction panel in frontend/tests/e2e/ai/issue-extraction.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T232 [P] E2E test confidence tags display in frontend/tests/e2e/ai/issue-extraction.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T233 [P] E2E test approval modal flow in frontend/tests/e2e/ai/issue-extraction.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)

### Settings E2E

- [ ] T234 [P] E2E test API key save/validate in frontend/tests/e2e/ai/ai-settings.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T235 [P] E2E test feature toggles in frontend/tests/e2e/ai/ai-settings.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)
- [ ] T236 [P] E2E test approval queue in frontend/tests/e2e/ai/approval-queue.spec.ts → [P26-T223-T236](tasks/P26-T223-T236.md)

**Checkpoint**: All E2E tests pass with 80%+ coverage.

---

## Phase 27: Frontend Polish & Cleanup → [P27-T237-T247](tasks/P27-T237-T247.md)

Final frontend cleanup and integration validation.

### Quality Gates

- [ ] T237 Run frontend quality gates: `pnpm lint && pnpm type-check && pnpm test` → [P27-T237-T247](tasks/P27-T237-T247.md)
- [ ] T238 Verify all AI stores registered in RootStore in frontend/src/stores/root-store.ts → [P27-T237-T247](tasks/P27-T237-T247.md)
- [ ] T239 Verify all AI routes in app router in frontend/src/app/ → [P27-T237-T247](tasks/P27-T237-T247.md)

### Accessibility

- [ ] T240 [P] Audit ghost text keyboard navigation (WCAG 2.2 AA) → [P27-T237-T247](tasks/P27-T237-T247.md)
- [ ] T241 [P] Audit AI panels screen reader compatibility → [P27-T237-T247](tasks/P27-T237-T247.md)
- [ ] T242 [P] Audit approval modal focus management → [P27-T237-T247](tasks/P27-T237-T247.md)

### Performance

- [ ] T243 [P] Profile ghost text debounce efficiency → [P27-T237-T247](tasks/P27-T237-T247.md)
- [ ] T244 [P] Profile SSE memory usage on long streams → [P27-T237-T247](tasks/P27-T237-T247.md)
- [ ] T245 [P] Verify bundle size impact of AI features → [P27-T237-T247](tasks/P27-T237-T247.md)

### Documentation

- [ ] T246 [P] Document AI store patterns in frontend/src/stores/README.md → [P27-T237-T247](tasks/P27-T237-T247.md)
- [ ] T247 [P] Document TipTap extension patterns in frontend/src/components/editor/README.md → [P27-T237-T247](tasks/P27-T237-T247.md)

**Checkpoint**: Frontend complete, all quality gates pass.

---

## Phase 28: Legacy Code Cleanup & Migration → [P28-T248-T312](tasks/P28-T248-T312.md)

Clean up all legacy AI code after SDK migration is complete (blocked by: T108 quality gates pass).

### 28.1 Delete Legacy Agent Base Classes

- [ ] T248 Archive backend/src/pilot_space/ai/agents/base.py to backend/src/pilot_space/ai/_archive/base.py.bak → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T249 Delete backend/src/pilot_space/ai/agents/base.py after verifying no imports remain → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T250 [P] Update all agent __init__.py exports to use sdk_base.py in backend/src/pilot_space/ai/agents/__init__.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T251 [P] Remove BaseAgent imports from all test files in backend/tests/unit/ai/agents/ → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.2 Delete Legacy Direct Provider Implementations

- [ ] T252 Archive old ghost_text_agent.py (Gemini direct) to backend/src/pilot_space/ai/_archive/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T253 Delete backend/src/pilot_space/ai/agents/ghost_text_agent.py (old Gemini version) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T254 [P] Remove `google.generativeai` from pyproject.toml dependencies → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T255 [P] Remove `import google.generativeai` from any remaining files (grep verification) → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.3 Delete Legacy Orchestrator

- [ ] T256 Archive backend/src/pilot_space/ai/orchestrator.py to backend/src/pilot_space/ai/_archive/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T257 Delete backend/src/pilot_space/ai/orchestrator.py after sdk_orchestrator.py is primary → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T258 Update all imports from `orchestrator` to `sdk_orchestrator` in backend/src/pilot_space/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T259 [P] Update DI container to remove old orchestrator provider in backend/src/pilot_space/container.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T260 [P] Remove `get_orchestrator()` function calls, replace with `get_sdk_orchestrator()` → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.4 Delete Legacy Mock Provider

- [ ] T261 Archive backend/src/pilot_space/ai/providers/mock.py to backend/src/pilot_space/ai/_archive/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T262 Delete backend/src/pilot_space/ai/providers/mock.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T263 [P] Delete all mock generators in backend/src/pilot_space/ai/providers/mock_generators/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T264 [P] Create SDK-compatible test fixtures in backend/tests/fixtures/ai/ → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.5 Clean Up Legacy Prompt Templates

- [ ] T265 Archive all old prompt files to backend/src/pilot_space/ai/_archive/prompts/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T266 [P] Delete backend/src/pilot_space/ai/prompts/ghost_text.py (old string template) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T267 [P] Delete backend/src/pilot_space/ai/prompts/margin_annotation.py (old string template) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T268 [P] Delete backend/src/pilot_space/ai/prompts/issue_extraction.py (old string template) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T269 [P] Delete backend/src/pilot_space/ai/prompts/issue_enhancement.py (old string template) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T270 [P] Delete backend/src/pilot_space/ai/prompts/ai_context.py (old string template) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T271 [P] Delete backend/src/pilot_space/ai/prompts/pr_review.py (old string template) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T272 Verify all prompts migrated to SDK tool format in backend/src/pilot_space/ai/tools/ → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.6 Clean Up Legacy Agent Implementations

These agents had direct `anthropic` imports that are now replaced by SDK:

- [ ] T273 [P] Remove direct `import anthropic` from conversation_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T274 [P] Remove direct `import anthropic` from issue_extractor_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T275 [P] Remove direct `import anthropic` from margin_annotation_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T276 [P] Remove direct `import anthropic` from issue_enhancer_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T277 [P] Remove direct `import anthropic` from duplicate_detector_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T278 [P] Remove direct `import anthropic` from pr_review_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T279 [P] Remove direct `import anthropic` from ai_context_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T280 [P] Remove direct `import anthropic` from commit_linker_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T281 [P] Remove direct `import anthropic` from assignee_recommender_agent.py → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.7 Clean Up Legacy Infrastructure

- [ ] T282 Delete in-memory RateLimiter class from old orchestrator.py (now Redis-based) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T283 [P] Remove PROVIDER_ROUTING dict (SDK handles routing) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T284 [P] Remove DEFAULT_MODELS dict (SDK has model selection) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T285 [P] Update AgentContext to minimal SDK context wrapper in backend/src/pilot_space/ai/context.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T286 [P] Remove AgentResult[OutputT] class (SDK uses message types) → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.8 Clean Up Legacy Telemetry

- [ ] T287 Update AIProvider enum to remove deprecated providers in backend/src/pilot_space/ai/telemetry.py → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T288 [P] Update TOKEN_COSTS dict for Claude Opus 4.5 and Haiku pricing → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T289 [P] Remove Gemini-specific token cost entries → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T290 [P] Update AIOperation enum to match SDK tool names → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.9 Clean Up Legacy Dependencies

- [ ] T291 Remove unused `google-generativeai` from backend/pyproject.toml → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T292 [P] Verify `anthropic` is only used via claude-agent-sdk (not direct) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T293 [P] Remove any `tenacity` usage replaced by SDK retry (if applicable) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T294 Run `uv pip check` to verify no broken dependencies → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.10 Clean Up Frontend Legacy Code (if any)

- [ ] T295 [P] Remove any direct AI API calls bypassing stores in frontend/src/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T296 [P] Clean up unused AI-related types that don't match new SDK responses → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T297 [P] Remove deprecated SSE event types if changed → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.11 Clean Up Tests

- [ ] T298 Delete tests for deleted classes (BaseAgent, old GhostTextAgent) in backend/tests/ → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T299 [P] Update test imports to use sdk_base instead of base → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T300 [P] Remove mock provider tests, replace with SDK fixture tests → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T301 [P] Update integration tests to use sdk_orchestrator → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.12 Documentation Cleanup

- [ ] T302 Remove outdated AI architecture docs referencing direct provider calls → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T303 [P] Update CLAUDE.md AI section with SDK patterns → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T304 [P] Update docs/architect/ai-layer.md to reflect SDK architecture → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T305 [P] Archive old architecture docs to docs/_archive/ → [P28-T248-T312](tasks/P28-T248-T312.md)

### 28.13 Final Verification

- [ ] T306 Run grep for "google.generativeai" - should return 0 results → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T307 [P] Run grep for "from pilot_space.ai.agents.base import" - should return 0 results → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T308 [P] Run grep for "from pilot_space.ai.orchestrator import" - should return 0 results → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T309 [P] Run grep for "MockProvider" - should return 0 results (outside _archive) → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T310 Verify _archive directory is in .gitignore or removed before production → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T311 Run full test suite: `uv run pytest --cov=pilot_space.ai` → [P28-T248-T312](tasks/P28-T248-T312.md)
- [ ] T312 Run quality gates: `uv run ruff check . && uv run pyright` → [P28-T248-T312](tasks/P28-T248-T312.md)

**Checkpoint**: All legacy code removed, SDK is sole AI implementation.

---

## Phase 29: Post-Migration Optimization → [P29-T313-T331](tasks/P29-T313-T331.md)

Optimize SDK implementation after cleanup (blocked by: T312 quality gates pass).

### 29.1 Performance Optimization

- [ ] T313 [P] Profile ghost text latency with SDK, ensure <2s p95 → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T314 [P] Profile AI context generation, ensure <30s p95 → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T315 [P] Profile PR review, ensure <60s for PRs <1000 lines → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T316 [P] Optimize SDK tool schemas for minimal token usage → [P29-T313-T331](tasks/P29-T313-T331.md)

### 29.2 Cost Optimization

- [ ] T317 [P] Analyze token usage per agent type → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T318 [P] Tune max_tokens settings per tool for cost efficiency → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T319 [P] Implement response caching for repeated queries → [P29-T313-T331](tasks/P29-T313-T331.md)

### 29.3 Resilience Testing

- [ ] T320 [P] Test circuit breaker with SDK client failures → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T321 [P] Test rate limiter with Redis under load → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T322 [P] Test session expiration handling → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T323 [P] Test approval expiration handling → [P29-T313-T331](tasks/P29-T313-T331.md)

### 29.4 Security Hardening

- [ ] T324 Audit API key handling - verify never logged → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T325 [P] Audit SDK tool inputs for injection vulnerabilities → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T326 [P] Verify RLS policies on ai_* tables → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T327 [P] Penetration test approval bypass attempts → [P29-T313-T331](tasks/P29-T313-T331.md)

### 29.5 Monitoring Setup

- [ ] T328 [P] Add SDK operation metrics to telemetry dashboard → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T329 [P] Add cost tracking alerts for high-spend workspaces → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T330 [P] Add circuit breaker state monitoring → [P29-T313-T331](tasks/P29-T313-T331.md)
- [ ] T331 [P] Add session count monitoring → [P29-T313-T331](tasks/P29-T313-T331.md)

**Checkpoint**: SDK implementation optimized and hardened.

---

## Updated Dependencies

### Phase Order (Updated)

```
Backend Foundation (1-5) → Backend User Stories (6-12) → Backend Supporting (13-15)
                        ↓
Frontend Foundation (16) → Frontend MVP (17-19) → Frontend Features (20-25) → Frontend E2E (26-27)
                                                                                      ↓
                                                            Legacy Cleanup (28) → Optimization (29)
```

### Cleanup Phase Dependencies

```
T108 (Quality gates pass)
    → T248-T264 (Delete legacy base, orchestrator, mock)
    → T265-T272 (Delete legacy prompts)
    → T273-T281 (Clean agent provider imports)
    → T282-T297 (Clean infrastructure & frontend)
    → T298-T305 (Clean tests & docs)
    → T306-T312 (Final verification)
        → T313-T331 (Optimization)
```

### Parallel Cleanup Groups

```
# Phase 28.2-28.3 (Delete legacy files - parallel after archive)
T252-T255 | T256-T260 | T261-T264

# Phase 28.6 (Clean agent imports - all parallel)
T273 | T274 | T275 | T276 | T277 | T278 | T279 | T280 | T281

# Phase 28.11-28.12 (Tests & docs - parallel)
T298-T301 | T302-T305

# Phase 29 (Optimization - all parallel within groups)
T313-T316 | T317-T319 | T320-T323 | T324-T327 | T328-T331
```

### Frontend Phase Dependencies

```
T111-T120 (Phase 16: FE Foundation)
    ↓
T121-T131 (Phase 17: Ghost Text) ← blocked by T044-T049 (Backend US2)
T132-T142 (Phase 18: AI Context) ← blocked by T038-T043 (Backend US1)
T143-T153 (Phase 19: PR Review) ← blocked by T050-T055 (Backend US3)
    ↓
T154-T164 (Phase 20: Issue Extraction) ← blocked by T056-T061 (Backend US4)
T165-T177 (Phase 21: Margin Annotations) ← blocked by T067-T072 (Backend US6)
T178-T188 (Phase 22: AI Settings) ← blocked by T062-T066 (Backend US5)
T189-T199 (Phase 23: Approval Queue) ← blocked by T073-T078 (Backend US7)
    ↓
T200-T210 (Phase 24: Cost Dashboard) ← blocked by T091-T094 (Backend Cost)
T211-T222 (Phase 25: Conversation) ← blocked by T079-T080 (Backend Conversation)
    ↓
T223-T236 (Phase 26: E2E Tests)
T237-T247 (Phase 27: Polish)
```

### Critical Path (Full Stack MVP)

```
Backend: T001-T037 → T038-T055 (US1-US3)
                ↓
Frontend: T111-T120 → T121-T153 (Ghost Text + AI Context + PR Review)
                ↓
E2E: T223-T230 (MVP E2E tests)
```

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 331 |
| **Phase 1-5 (Backend Setup)** | 37 |
| **Phase 6-15 (Backend Features)** | 73 |
| **Phase 16 (Frontend Foundation)** | 10 |
| **Phase 17-19 (Frontend MVP)** | 33 |
| **Phase 20-25 (Frontend Features)** | 69 |
| **Phase 26-27 (Frontend E2E/Polish)** | 25 |
| **Phase 28 (Legacy Cleanup)** | 65 |
| **Phase 29 (Post-Migration Optimization)** | 19 |
| **Parallelizable Tasks** | 178 (54%) |
| **MVP Scope (Backend + Frontend)** | 96 tasks (T001-T055 + T111-T153) |
| **Backend Tasks** | 110 + 65 cleanup + 19 optimization = 194 |
| **Frontend Tasks** | 137 |

### Task Categories

| Category | Tasks | Description |
|----------|-------|-------------|
| **New Implementation** | T001-T110 | SDK infrastructure, agents, MCP tools |
| **Frontend Integration** | T111-T247 | Stores, components, E2E tests |
| **Legacy Cleanup** | T248-T312 | Delete/archive deprecated code |
| **Optimization** | T313-T331 | Performance, cost, security |

### Legacy Files to Remove

| File Type | Count | Impact |
|-----------|-------|--------|
| Agent implementations | 10 files | Direct provider API calls |
| Prompt templates | 6 files | String-based templates |
| Mock providers | 11 files | Old mock generator pattern |
| Orchestrator | 1 file | Custom orchestration |
| Base classes | 1 file | BaseAgent[InputT, OutputT] |
| **Total** | **29 files** | ~6,000 lines removed |

### New Files Created

| File Type | Count | Purpose |
|-----------|-------|---------|
| SDK orchestrator | 1 file | Claude SDK client wrapper |
| SDK base | 1 file | Agent base with telemetry |
| MCP tools | 15 files | Database, GitHub, Search tools |
| Infrastructure | 4 files | Key storage, approval, cost, session |
| Frontend stores | 10 files | MobX AI stores |
| Frontend components | 40+ files | AI UI components |
| **Total** | **70+ files** | Full SDK implementation |
