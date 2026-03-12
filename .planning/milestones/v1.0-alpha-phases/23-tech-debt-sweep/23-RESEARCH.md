# Phase 23: Tech Debt Sweep - Research

**Researched:** 2026-03-12
**Domain:** Code quality, dead code removal, test fixes, UI cosmetics
**Confidence:** HIGH

## Summary

Phase 23 addresses 7 discrete tech debt items spanning backend API key testing, dead code, stale test references, soft-delete verification, UI badge color, file size compliance, and frontend validation expansion. All items are well-scoped, isolated changes with minimal cross-cutting risk.

The primary challenge is Task 6 (refactor `ai_chat.py` below 700 lines) since the file is exactly at the 700-line limit and already has one extracted helper (`_chat_attachments.py`). The remaining tasks are surgical fixes requiring no architectural changes.

**Primary recommendation:** Tackle all 7 items in a single plan since they are independent, small changes. Group by backend/frontend for efficient quality gate runs.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AIPR-05 | Multi-provider BYOK registry cosmetic completeness | Tasks 1 and 7 — extend `_test_provider_api_key` and `validateKey` to cover kimi/glm/custom providers |
| code quality | Dead code, stale tests, file size, badge color | Tasks 2-6 — remove dead file, fix test assertions, verify delete behavior, fix badge color, refactor ai_chat.py |
</phase_requirements>

## Standard Stack

No new libraries needed. All changes use existing project stack.

### Core (existing)
| Library | Purpose | Relevant To |
|---------|---------|-------------|
| FastAPI + httpx | Backend API testing | Tasks 1, 3, 4 |
| openai (Python SDK) | OpenAI-compatible key testing for kimi/glm/custom | Task 1 |
| Vitest + React Testing Library | Frontend component tests | Tasks 5, 7 |
| MobX | AISettingsStore | Task 7 |
| shadcn/ui Badge | Plugin card UI | Task 5 |

## Architecture Patterns

### Task-by-Task Technical Analysis

#### Task 1: Fix `_test_provider_api_key` for kimi/glm/custom providers

**Current state:** `_test_provider_api_key()` in `ai_configuration.py` (line 539) handles ANTHROPIC, OPENAI, and GOOGLE only. Returns `False, "Unknown provider"` for KIMI, GLM, CUSTOM.

**LLMProvider enum** (in `models/ai_configuration.py`):
```python
class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    KIMI = "kimi"
    GLM = "glm"
    CUSTOM = "custom"
```

**Fix pattern:** KIMI, GLM, and CUSTOM providers are all OpenAI-compatible (per DD project context: "Multi-provider registry with custom OpenAI-compat"). Use the same `openai.AsyncOpenAI` client with a custom `base_url` parameter. The `AIConfiguration` model stores `base_url` for custom providers.

**Key insight:** The `_test_provider_api_key` function currently receives only `(provider, api_key)`. For kimi/glm/custom, it also needs the `base_url` from the configuration. The caller at line 517 has access to the full `config` object. Change signature to pass `base_url` or the full config.

**Known base URLs:**
- Kimi: `https://api.moonshot.cn/v1`
- GLM: `https://open.bigmodel.cn/api/paas/v4`
- Custom: user-configured `base_url` from `AIConfiguration`

**File:** `backend/src/pilot_space/api/v1/routers/ai_configuration.py` (637 lines, room for additions)

#### Task 2: Remove dead `schemas/mcp_server.py`

**Current state:** `backend/src/pilot_space/api/v1/schemas/mcp_server.py` (117 lines). Contains `WorkspaceMcpServerCreate`, `WorkspaceMcpServerUpdate`, `WorkspaceMcpServerResponse`, etc.

**Verification:** No imports found in the codebase. The MCP server router uses inline schemas (schemas defined in the router file itself, as is the project pattern for Phase 14+ routers).

**Action:** Delete file. Verify no `__init__.py` barrel exports reference it.

#### Task 3: Fix stale `item["issue_id"]` in test_related_issues.py

**Current state:** Lines 165 and 427 reference `item["id"]` (not `item["issue_id"]` as stated in the roadmap). Looking at the actual test:
- Line 165: `issue_ids_in_result = [item["id"] for item in data]` -- this is correct for the current `RelatedSuggestion` schema which has field `id`.
- Line 427: same pattern -- also correct for the current schema.

**Finding:** The roadmap description may be outdated -- the test appears to have already been fixed, OR the field name in the schema was changed. The `RelatedSuggestion` Pydantic model has `id: UUID` field. The test uses `item["id"]` which matches. The planner should verify this is a no-op or if there's a different stale reference.

#### Task 4: Verify DELETE relation endpoint soft-delete vs hard-delete

**Current state:** The `delete_issue_relation` endpoint (line 311 in `related_issues.py`) calls `await link_repo.delete(link)` with no `hard=True` flag.

**BaseRepository.delete()** (in `repositories/base.py`): defaults to soft-delete (`entity.is_deleted = True`). Hard delete requires explicit `hard=True`.

**IssueLink model** extends `WorkspaceScopedModel` which extends `BaseModel` which includes `SoftDeleteMixin` (has `is_deleted` and `deleted_at` fields).

**Conclusion:** The endpoint already performs soft-delete. The docstring says "Soft-delete an issue relation link" which is correct. The summary label in the router also says "Delete (soft-delete) an issue relation." This task is a **verification only** -- no code change needed unless the team decides hard-delete is preferred for links (since links are lightweight join records, not primary entities).

**Recommendation:** Document that soft-delete is the current (correct) behavior. If hard-delete is desired for link records, change to `await link_repo.delete(link, hard=True)`.

#### Task 5: Fix Update Available badge color (blue -> orange)

**Current state:** In `plugin-card.tsx` (line 68-74):
```tsx
{group.hasUpdate && (
  <Badge
    variant="outline"
    className="border-blue-500/20 bg-blue-500/10 text-blue-400 text-[10px] px-1.5 py-0 h-5"
    data-testid="badge-update"
  >
```

Also in `plugin-detail-sheet.tsx` (line 54-58):
```tsx
{group.hasUpdate && (
  <Button
    size="sm"
    variant="outline"
    className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
```

**Per spec:** The UI design spec uses orange/amber for "action available" signals (see `ui-component-specs-daily-routine.md` line 241: "Orange/yellow signal 'action available' not 'something is wrong'"). The project convention for update/action-needed badges uses amber (`#D9853F`).

**Fix:** Replace `blue-500` with `amber-500` (or `orange-500`) in both files. Use Tailwind amber classes:
- Badge: `border-amber-500/20 bg-amber-500/10 text-amber-400`
- Button: `border-amber-500/30 text-amber-400 hover:bg-amber-500/10`

**Test impact:** `plugin-card.test.tsx` exists and may assert badge classes. Update test expectations.

#### Task 6: Refactor `ai_chat.py` below 700-line limit

**Current state:** Exactly 700 lines. Already has `_chat_attachments.py` (71 lines) extracted. Also has `ai_chat_model_routing.py` as a separate helper.

**Structure analysis needed:** The file contains:
- Schema definitions (ChatContext, ChatRequest, ChatResponse, etc.)
- SSE streaming logic
- Session/history management
- Message persistence
- The main chat endpoint

**Refactor strategy:** Extract one of these concerns:
1. **Schemas** to a separate `schemas/ai_chat.py` or `_chat_schemas.py` -- likely 50-80 lines of Pydantic models
2. **Session/history helpers** to `_chat_history.py`
3. **SSE event formatting** to `_chat_sse.py`

**Safest extraction:** Move Pydantic schemas (ChatContext, ChatRequest, ChatResponse, etc.) to `_chat_schemas.py`. These are pure data classes with no runtime dependencies on the router logic.

#### Task 7: Extend `AISettingsStore.validateKey` for all provider types

**Current state:** `validateKey` (line 180-191 in `AISettingsStore.ts`) only handles `'anthropic'` and `'openai'`:
```typescript
validateKey(provider: 'anthropic' | 'openai', key: string): boolean {
    if (key.length < 10) return false;
    switch (provider) {
      case 'anthropic': return key.startsWith('sk-ant-');
      case 'openai': return key.startsWith('sk-');
      default: return false;
    }
}
```

**Fix:** Expand type union and add cases for google, kimi, glm, custom:
- `google`: Google AI keys start with `AIza` (39 chars)
- `kimi`: Moonshot keys -- accept any key >= 10 chars (no known public prefix)
- `glm`: GLM/ZhipuAI keys -- accept any key >= 10 chars
- `custom`: Any key >= 10 chars (OpenAI-compatible, no prefix constraint)

**Impact:** Also update callers -- `api-key-form.tsx`, `ApiKeySetupStep.tsx`, and `useOnboardingActions.ts` reference `validateKey`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI-compatible key testing | Custom HTTP client for kimi/glm | `openai.AsyncOpenAI(base_url=...)` | Already used for openai; compatible with all OpenAI-compat providers |

## Common Pitfalls

### Pitfall 1: ai_configuration.py line count after Task 1
**What goes wrong:** Adding 3 new test functions (kimi, glm, custom) could push `ai_configuration.py` beyond 700 lines.
**Current state:** 637 lines. Adding ~30 lines for a shared `_test_openai_compatible_key(api_key, base_url)` is safe.
**How to avoid:** Reuse the openai test logic with a parameterized base_url rather than 3 separate functions.

### Pitfall 2: Missing base_url in _test_provider_api_key signature
**What goes wrong:** kimi/glm/custom providers need a base_url but the current function only takes `(provider, api_key)`.
**How to avoid:** Pass the full `config` object or add an optional `base_url` parameter. The caller already has the config.

### Pitfall 3: Plugin card test assertions on class names
**What goes wrong:** Changing badge color classes breaks existing test snapshots.
**How to avoid:** Check `plugin-card.test.tsx` for class-based assertions and update them.

### Pitfall 4: ai_chat.py circular imports after schema extraction
**What goes wrong:** Extracting schemas that import from the router module creates circular imports.
**How to avoid:** Schemas should only import from `schemas/base.py` and domain types, never from the router.

## Code Examples

### Task 1: Shared OpenAI-compatible key test
```python
# Source: existing _test_openai_key pattern in ai_configuration.py
async def _test_openai_compatible_key(
    api_key: str, base_url: str
) -> tuple[bool, str]:
    """Test an OpenAI-compatible API key (kimi, glm, custom)."""
    import openai

    try:
        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        await client.models.list()
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except openai.PermissionDeniedError:
        return False, "API key lacks required permissions"
    except openai.RateLimitError:
        return True, "API key is valid (rate limited)"
    except openai.APIError as e:
        return False, f"API error: {e.message}"
    else:
        return True, "API key is valid"
```

### Task 5: Badge color fix
```tsx
// Source: project UI spec — amber for "action available"
{group.hasUpdate && (
  <Badge
    variant="outline"
    className="border-amber-500/20 bg-amber-500/10 text-amber-400 text-[10px] px-1.5 py-0 h-5"
    data-testid="badge-update"
  >
    Update
  </Badge>
)}
```

### Task 7: Extended validateKey
```typescript
// Source: existing AISettingsStore.ts pattern
validateKey(provider: string, key: string): boolean {
    if (key.length < 10) return false;
    switch (provider) {
      case 'anthropic': return key.startsWith('sk-ant-');
      case 'openai': return key.startsWith('sk-');
      case 'google': return key.startsWith('AIza');
      case 'kimi':
      case 'glm':
      case 'custom':
        return true; // No known prefix constraint
      default:
        return true; // Allow unknown providers with length check only
    }
}
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest + pytest-asyncio |
| Framework (frontend) | Vitest + React Testing Library |
| Config file (backend) | `backend/pyproject.toml` |
| Config file (frontend) | `frontend/vitest.config.ts` |
| Quick run command (backend) | `cd backend && uv run pytest tests/unit/routers/test_ai_configuration.py tests/api/test_related_issues.py -x -q` |
| Quick run command (frontend) | `cd frontend && pnpm test -- --run src/features/settings/components/__tests__/plugin-card.test.tsx src/features/settings/pages/__tests__/ai-settings-page.test.tsx` |
| Full suite command | `make quality-gates-backend && make quality-gates-frontend` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AIPR-05-a | kimi/glm/custom key testing | unit | `cd backend && uv run pytest tests/unit/routers/test_ai_configuration.py -x -q` | Yes (extend) |
| AIPR-05-b | validateKey all providers | unit | `cd frontend && pnpm test -- --run src/features/settings/pages/__tests__/ai-settings-page.test.tsx` | Yes (extend) |
| CQ-01 | Dead file removed | manual | `test ! -f backend/src/pilot_space/api/v1/schemas/mcp_server.py` | N/A |
| CQ-02 | Test assertions correct | unit | `cd backend && uv run pytest tests/api/test_related_issues.py -x -q` | Yes |
| CQ-03 | Soft-delete verified | unit | `cd backend && uv run pytest tests/api/test_related_issues.py -x -q` | Yes (verify) |
| CQ-04 | Badge color orange | unit | `cd frontend && pnpm test -- --run src/features/settings/components/__tests__/plugin-card.test.tsx` | Yes (update) |
| CQ-05 | ai_chat.py < 700 lines | manual | `wc -l backend/src/pilot_space/api/v1/routers/ai_chat.py` | N/A |

### Sampling Rate
- **Per task commit:** Relevant test file(s) for the changed module
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. New test cases will be added to existing test files.

## Open Questions

1. **Task 3: Are test assertions actually stale?**
   - What we know: Lines 165 and 427 use `item["id"]` which matches the current `RelatedSuggestion` schema's `id` field.
   - What's unclear: The roadmap says "Fix stale `item["issue_id"]`" but the actual code uses `item["id"]` which appears correct.
   - Recommendation: Verify at implementation time. If already correct, mark as no-op.

2. **Task 4: Should issue links use hard-delete instead of soft-delete?**
   - What we know: Current behavior is soft-delete (correct per docstring).
   - What's unclear: Whether the product intent is to permanently remove links (they're lightweight join records).
   - Recommendation: Keep soft-delete (current behavior). Add a test that verifies it. Only switch to hard-delete if explicitly requested.

3. **Task 1: Provider base URLs for kimi/glm**
   - What we know: Kimi uses `api.moonshot.cn/v1`, GLM uses `open.bigmodel.cn/api/paas/v4`.
   - What's unclear: Whether these are stored in `AIConfiguration.base_url` or if they need to be hardcoded defaults.
   - Recommendation: Check if the model has `base_url` field populated for kimi/glm configs. If not, add known defaults in the test function with a fallback.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all 7 affected files
- `backend/src/pilot_space/api/v1/routers/ai_configuration.py` -- lines 539-637
- `backend/src/pilot_space/api/v1/routers/related_issues.py` -- full file (335 lines)
- `backend/src/pilot_space/infrastructure/database/repositories/base.py` -- delete() method
- `backend/src/pilot_space/infrastructure/database/base.py` -- SoftDeleteMixin
- `frontend/src/stores/ai/AISettingsStore.ts` -- validateKey() method
- `frontend/src/features/settings/components/plugin-card.tsx` -- badge classes
- `specs/001-pilot-space-mvp/ui-design-spec.md` -- color conventions

### Secondary (MEDIUM confidence)
- Known Moonshot/ZhipuAI base URLs from provider documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all existing tools
- Architecture: HIGH - all changes are isolated, well-understood code
- Pitfalls: HIGH - identified from direct code inspection
- Task 3 accuracy: MEDIUM - roadmap description may not match current code state

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable codebase, no external dependency changes)
