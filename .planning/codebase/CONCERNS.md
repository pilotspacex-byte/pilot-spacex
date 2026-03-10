# Codebase Concerns

**Analysis Date:** 2026-03-07

---

## Tech Debt

**Alembic Migration Chain Conflict (022 triplicate):**
- Issue: Three files share the `022_` prefix with conflicting `Revises:` lines. `022_multi_context_sessions.py` references `023_fix_invitation_rls_enum_case` as parent (reverse), `022_workspace_invitations.py` references `021_ai_msg_queue_cols`, and `022_workspace_onboarding.py` references `022_multi_context_sessions`. A `027_merge_heads.py` exists to paper over the split.
- Files: `backend/alembic/versions/022_multi_context_sessions.py`, `backend/alembic/versions/022_workspace_invitations.py`, `backend/alembic/versions/022_workspace_onboarding.py`, `backend/alembic/versions/027_merge_heads.py`
- Impact: `alembic heads` shows multiple heads unless `027_merge_heads` is applied. New contributors see a confusing non-linear chain. Adding a migration without verifying `alembic heads` first creates another split.
- Fix approach: Always run `cd backend && alembic heads` before creating migrations. The merge head resolves the current split; do not re-split it.

**RLS Enum Case Mismatch (owner/admin/member vs OWNER/ADMIN/MEMBER):**
- Issue: RLS policies in `rls.py` use UPPERCASE (`'OWNER'`, `'ADMIN'`) but the onboarding model's embedded SQL uses lowercase (`'owner'`, `'admin'`). Known inconsistency documented in CLAUDE.md.
- Files: `backend/src/pilot_space/infrastructure/database/rls.py` (lines 194, 203), `backend/src/pilot_space/infrastructure/database/models/onboarding.py` (line 50)
- Impact: RLS policies that mix case silently allow or block rows depending on which migration ran. Members may be invisible or have wrong access. PostgreSQL enum comparisons are case-sensitive.
- Fix approach: Audit all migrations and model SQL strings for `role IN (...)`. Standardize on UPPERCASE to match `rls.py`. Create a migration to update any stored lowercase values.

**CostTracker and ApprovalService Singletons with `session=None`:**
- Issue: `CostTracker` and `ApprovalService` are constructed as DI singletons with `session=None` in `container/_factories.py`. Any route that calls the agent without injecting a DB session override silently drops cost records and approval persistence.
- Files: `backend/src/pilot_space/container/_factories.py` (lines 180–181), `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py` (comment at line 570)
- Impact: AI usage costs are not persisted for routes that do not explicitly override the session at call time. No error is raised; data is silently lost.
- Fix approach: Document which routes correctly inject session overrides. Consider removing `session=None` fallback and making the missing session a startup error.

**BYOK Env Fallback Bypasses BYOK Enforcement:**
- Issue: `PilotSpaceAgent._get_api_key()`, `pr_review_subagent.py`, and `doc_generator_subagent.py` fall back to `os.getenv("ANTHROPIC_API_KEY")` when no workspace key is found. The platform key silently covers for unconfigured workspaces, violating BYOK (no AI cost pass-through) design contract.
- Files: `backend/src/pilot_space/ai/agents/pilotspace_agent.py` (line 170), `backend/src/pilot_space/ai/agents/subagents/pr_review_subagent.py` (lines 237, 244), `backend/src/pilot_space/ai/agents/subagents/doc_generator_subagent.py` (lines 168, 175)
- Impact: Platform operator absorbs AI costs for workspaces without configured keys. Violates billing model.
- Fix approach: Remove the `ANTHROPIC_API_KEY` env fallback in production. Return a clear error directing the workspace to configure their key. Keep the fallback only for local dev via an explicit `ALLOW_PLATFORM_KEY_FALLBACK=true` flag.

**Costs Page Workspace ID Hardcoded to Slug:**
- Issue: `costs/page.tsx` passes `workspaceSlug` directly as `workspaceId` without resolving it via the store. The cost API expects a UUID, not a slug string.
- Files: `frontend/src/app/(workspace)/[workspaceSlug]/costs/page.tsx` (line 32)
- Impact: Cost dashboard API calls will fail or return wrong data because the request carries a slug string where a UUID is expected.
- Fix approach: Follow the pattern in `notes/page.tsx` — resolve `workspaceStore.currentWorkspace?.id ?? workspaceSlug` and pass the UUID.

**`GraphSearchService` Built Per-Request to Avoid Session Singleton Capture:**
- Issue: `build_graph_search_service_for_session()` was added as a workaround to the `session=None` singleton-capture bug. Instead of fixing the root cause in the DI container, each chat request reconstructs the service including a new `EmbeddingService`.
- Files: `backend/src/pilot_space/ai/agents/pilotspace_stream_utils.py` (lines 564–586)
- Impact: Extra object allocation per request. The underlying root cause (singletons capturing `None` session) is not fixed.
- Fix approach: Refactor `GraphSearchService` and `KnowledgeGraphRepository` to use `Factory` providers rather than `Singleton` in the DI container so sessions are injected per request.

---

## Known Bugs

**Workspace ID Fallback to Slug in Multiple Pages:**
- Symptoms: API calls may receive a slug string where a UUID is expected, causing 404s or data for wrong workspace
- Files: `frontend/src/app/(workspace)/[workspaceSlug]/costs/page.tsx` (line 32), `frontend/src/app/(workspace)/[workspaceSlug]/settings/integrations/page.tsx` (line 264), `frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx` (line 309), `frontend/src/app/(workspace)/[workspaceSlug]/page.tsx` (line 16)
- Trigger: Page loads before `workspaceStore.currentWorkspace` is populated (race condition), or store is not yet hydrated
- Workaround: `costs/page.tsx` has no guard — always sends slug. Other pages use `?? workspaceSlug` which is wrong when store is empty.

**Members Page `joinedAt` — Potential "Invalid Date":**
- Symptoms: `formatJoinDate(member.joinedAt)` calls `new Date(dateStr).toLocaleDateString(...)`. If `joinedAt` is `null`, `undefined`, or a non-standard format, `new Date(null)` returns epoch time, and `new Date(undefined)` returns `"Invalid Date"`.
- Files: `frontend/src/features/members/utils/member-utils.ts` (line 36), `frontend/src/features/settings/components/member-row.tsx` (line 113), `frontend/src/features/members/components/member-card.tsx` (line 78)
- Trigger: Backend returns null or missing `joined_at` for newly-created members or invitations before acceptance
- Workaround: None. `formatJoinDate` has no null guard.

**TipTap + MobX `observer()` Nested `flushSync` Error:**
- Symptoms: `"flushSync was called from inside a lifecycle method"` runtime error in React 19 when `IssueEditorContent` is wrapped with `observer()`.
- Files: `frontend/src/features/issues/components/issue-editor-content.tsx`, `frontend/src/app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`
- Trigger: Adding `observer()` to `IssueEditorContent` — do NOT do this. Documented as constraint.
- Workaround: Component intentionally left as plain (non-observer) component; data flows through `IssueNoteContext` instead of MobX observables.

---

## Security Considerations

**Prompt Injection: Only Structural Patterns Detected, Natural Language Unblocked:**
- Risk: `hooks_lifecycle.py` detects structural injection patterns (angle brackets, backticks) but explicitly does NOT block natural-language injection attempts. User-controlled note content and issue text can influence AI behavior.
- Files: `backend/src/pilot_space/ai/sdk/hooks_lifecycle.py` (line 135), `backend/src/pilot_space/ai/prompts/ghost_text.py` (line 296)
- Current mitigation: Structural pattern detection only. AI context is sandboxed per workspace via MCP server routing.
- Recommendations: Add adversarial test cases. Consider prompt sandboxing at the system prompt boundary.

**RLS Bypassed in AI Endpoints:**
- Risk: AI endpoints use Redis/in-memory state and bypass database-level RLS. If the `workspace_id` claim is not validated independently, cross-workspace data leakage is possible.
- Files: `backend/src/pilot_space/dependencies/auth.py` (line 208)
- Current mitigation: `workspace_id` is resolved from the authenticated JWT before routing MCP calls. MCP servers scope queries by workspace.
- Recommendations: Add integration tests that attempt cross-workspace MCP reads under a valid session for workspace A while requesting workspace B data.

**BYOK Env Fallback Exposes Platform Key:**
- Risk: If `ANTHROPIC_API_KEY` is set in the deployment environment, all workspaces without a configured BYOK key silently use the platform key. No audit log differentiates BYOK usage from platform key usage.
- Files: `backend/src/pilot_space/ai/agents/pilotspace_agent.py` (line 170), `backend/src/pilot_space/ai/agents/subagents/pr_review_subagent.py` (lines 237, 244)
- Current mitigation: None. The fallback is intentional for dev convenience but unguarded in production.
- Recommendations: Gate fallback behind explicit env flag. Log a warning when platform key is used. Enforce BYOK in workspace onboarding.

**Fernet Encryption Key as Single Master Secret:**
- Risk: All BYOK API keys stored in the database are encrypted with a single `ENCRYPTION_KEY` from config. Key rotation requires re-encrypting all stored keys. Key compromise exposes all workspace API keys.
- Files: `backend/src/pilot_space/infrastructure/encryption.py`, `backend/src/pilot_space/config.py` (line 141)
- Current mitigation: Key is stored as `SecretStr` and never logged. Fernet provides authenticated encryption.
- Recommendations: Implement key versioning. Add a key rotation migration path.

---

## Performance Bottlenecks

**Multiple Large Files Approaching or At 700-Line Limit:**
- Problem: Several files have grown to exactly 700 lines (the enforced limit), indicating they contain too much logic. Files at the limit cannot accept new functions without triggering pre-commit rejection.
- Files: `backend/src/pilot_space/api/v1/dependencies.py` (700 lines), `backend/src/pilot_space/ai/agents/pilotspace_agent.py` (700 lines), `backend/src/pilot_space/integrations/github/client.py` (699 lines), `backend/src/pilot_space/api/v1/routers/ai_chat.py` (699 lines), `backend/src/pilot_space/ai/mcp/note_server.py` (699 lines)
- Cause: Features accumulated in single files without refactoring. `pilotspace_agent.py` mixes orchestration, API key resolution, and stream management.
- Improvement path: Extract API key resolution and stream config building into separate modules. Split `ai_chat.py` router into sub-routers by concern.

**Ghost Text and AI Context Rate Limiters Are Redis-Dependent:**
- Problem: Rate limiting for `ghost_text.py`, `issues_ai_context.py`, and `issues_ai_context_streaming.py` degrades gracefully but differently — ghost text returns 503 if Redis is unavailable, while context endpoints allow unlimited requests (returns a warning only).
- Files: `backend/src/pilot_space/api/v1/routers/ghost_text.py` (line 87), `backend/src/pilot_space/api/v1/routers/issues_ai_context.py` (line 70)
- Cause: Inconsistent rate limit failure modes across endpoints.
- Improvement path: Standardize failure mode. Either all endpoints fail open (risky) or all fail closed (returns 503).

**No Rate Limiting on Most API Endpoints:**
- Problem: Rate limiting is applied only to `ghost_text`, `issues_ai_context`, `auth/validate-key`, and GitHub webhooks. All other endpoints (notes, issues, members, projects) have no rate limiting.
- Files: `backend/src/pilot_space/api/v1/routers/` (all routers except those listed)
- Cause: Rate limiting was added per-endpoint reactively, not via middleware.
- Improvement path: Add a global rate limiting middleware using `slowapi` or Redis sliding window keyed on user ID.

---

## Fragile Areas

**TipTap PropertyBlock Extension Guard Plugins:**
- Files: `frontend/src/features/issues/editor/property-block-extension.ts`
- Why fragile: Two ProseMirror plugins prevent deletion and movement of the property block from position 0. Removing or weakening either guard corrupts the structured issue note format. The constraint is only documented in `.claude/rules/tiptap.md` and code comments.
- Safe modification: Read `.claude/rules/tiptap.md` before touching this extension. Never wrap `IssueEditorContent` in `observer()`.
- Test coverage: No unit tests for the guard plugins. Breakage is only detectable at runtime.

**DI Wiring Silent Failure for New `@inject` Modules:**
- Files: `backend/src/pilot_space/container/container.py` (`wiring_config.modules` list)
- Why fragile: New files using `@inject` + `Provide[Container.x]` silently receive default values (often `None`) if the module path is not registered in `wiring_config.modules`. No exception is raised at startup or during testing with SQLite.
- Safe modification: After adding a new file with `@inject`, immediately add it to the wiring list and write a test that exercises the injection.
- Test coverage: DI wiring is not tested in CI. Failures only surface under load or when the specific code path is hit.

**ContextVar Session Pattern Across All Service Calls:**
- Files: `backend/src/pilot_space/dependencies/auth.py` (lines 40, 69–106)
- Why fragile: The DB session is propagated through a `ContextVar` (`_request_session_ctx`). Any new async task spawned via `asyncio.create_task()` or background jobs does NOT inherit the ContextVar, causing `RuntimeError: No session in current context` silently in background paths.
- Safe modification: Background tasks must receive the session as an explicit parameter, not rely on ContextVar inheritance.
- Test coverage: Only covered in integration tests when `TEST_DATABASE_URL` is set to PostgreSQL.

**Knowledge Graph Repository — PostgreSQL-Only Features:**
- Files: `backend/src/pilot_space/infrastructure/database/repositories/knowledge_graph_repository.py` (676 lines), `backend/tests/unit/infrastructure/repositories/test_knowledge_graph_repository.py`
- Why fragile: Uses `pgvector` similarity search, recursive CTEs, and `JSONB` operators. All tests in this module are skipped when `TEST_DATABASE_URL` defaults to SQLite. Changes to repository queries are not caught in unit CI.
- Safe modification: All changes to this repository require a PostgreSQL test instance to validate.
- Test coverage: Effectively 0% in standard CI (SQLite).

**`get_settings()` lru_cache Stale State in Tests:**
- Files: `backend/src/pilot_space/config.py` (line 221), multiple test files
- Why fragile: `@lru_cache` with no `maxsize` argument caches `Settings` indefinitely per process. Tests that modify env vars after first call see stale values. Known gotcha documented in CLAUDE.md.
- Safe modification: Always call `get_settings.cache_clear()` in test fixtures before overriding env vars.
- Test coverage: Several test files do not call `cache_clear`, making them order-dependent.

---

## Scaling Limits

**Supabase pgmq Queue — Single Queue for AI Jobs:**
- Current capacity: Shared `ai_normal` queue for all AI jobs (ghost text, KG population, memory saves, PR review, digests)
- Limit: High-priority ghost text requests queue behind slow KG population jobs. No priority lanes or dead-letter queue visible in `supabase_queue.py`.
- Scaling path: Add separate queues per job type. Route ghost text to a high-priority queue.

**AI Session Storage in Redis:**
- Current capacity: Sessions stored in Redis with no observed TTL enforcement
- Limit: Session count grows unboundedly per user. `list_sessions_for_user()` in `ai/sdk/session_store.py` returns all sessions; large session counts cause slow loads.
- Scaling path: Enforce session TTL on creation. Paginate `list_sessions_for_user()`.

---

## Dependencies at Risk

**`dependency-injector` Container Wiring — Silent Injection Failures:**
- Risk: The `dependency-injector` library's `wiring_config.modules` system silently falls back to defaults when a module is not registered. This is a known limitation of the library, not a bug.
- Impact: New modules added without wiring registration produce no import errors; production routes silently use `None` for injected services.
- Migration plan: Consider adopting explicit FastAPI `Depends()` injection for new services to eliminate silent wiring failures.

**pytest-asyncio Event Loop Scope Mismatch:**
- Risk: `event_loop` fixture is `scope="session"` in `backend/tests/conftest.py` but test fixtures default to `function` scope. pytest-asyncio 0.24+ emits deprecation warnings about this mismatch.
- Impact: Deprecation warnings in CI output. Future pytest-asyncio releases may make this a hard error.
- Migration plan: Migrate to `asyncio_mode = "auto"` and remove the manual `event_loop` fixture, or upgrade all fixtures to `scope="session"`.

---

## Test Coverage Gaps

**All API Routers Except 4 Are Untested:**
- What's not tested: ~55 routers in `backend/src/pilot_space/api/v1/routers/` have no corresponding tests in `backend/tests/routers/`. Only `test_auth_validate_key.py`, `test_implement_context_router.py`, `test_workspace_tasks.py`, and `test_workspace_tasks_actions.py` exist.
- Files: `backend/src/pilot_space/api/v1/routers/` (all files not listed above)
- Risk: API contract regressions are not caught in CI. Authentication/authorization checks on new endpoints are unverified.
- Priority: High

**Knowledge Graph Repository — SQLite Skip:**
- What's not tested: `pgvector` similarity search, recursive CTE traversal, `JSONB` property queries
- Files: `backend/src/pilot_space/infrastructure/database/repositories/knowledge_graph_repository.py`, `backend/tests/unit/infrastructure/repositories/test_knowledge_graph_repository.py`
- Risk: Vector search and graph traversal changes break silently in CI. Only caught in production or with manual PostgreSQL testing.
- Priority: High

**RLS Policies Not Validated in CI:**
- What's not tested: Row-level security policies — whether workspace isolation actually prevents cross-tenant data access
- Files: `backend/alembic/versions/004_rls_policies.py` and subsequent migration files adding RLS
- Risk: A mis-authored RLS policy allows cross-workspace data leakage. SQLite in CI has no RLS, so the policies are never exercised.
- Priority: High

**Frontend — No Tests for Key Pages:**
- What's not tested: `costs/page.tsx`, `notes/page.tsx`, `issues/[issueId]/page.tsx`, `projects/page.tsx` — major feature pages with complex state management have no Vitest unit tests.
- Files: `frontend/src/app/(workspace)/[workspaceSlug]/costs/page.tsx`, `frontend/src/app/(workspace)/[workspaceSlug]/notes/page.tsx`
- Risk: Workspace ID/slug confusion bugs (like the one in `costs/page.tsx`) go undetected.
- Priority: Medium

**TipTap PropertyBlock Guard Plugins:**
- What's not tested: ProseMirror guard plugins that prevent property block deletion and movement
- Files: `frontend/src/features/issues/editor/property-block-extension.ts`
- Risk: A future TipTap upgrade or ProseMirror refactor silently removes guard behavior, corrupting all issue notes.
- Priority: Medium

---

*Concerns audit: 2026-03-07*
