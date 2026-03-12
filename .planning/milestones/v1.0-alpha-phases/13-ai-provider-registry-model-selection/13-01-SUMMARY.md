---
phase: 13-ai-provider-registry-model-selection
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, alembic, byok, provider-registry, model-listing, kimi, glm, openai-compat]

requires:
  - phase: 04-ai-governance
    provides: AIConfiguration model, SecureKeyStorage, LLMProvider enum, ai_configurations table
  - phase: 13-ai-provider-registry-model-selection
    provides: Phase plan with AIPR-01..05 requirements and interfaces specification

provides:
  - Migration 070 — kimi/glm/custom enum values + base_url/display_name columns on ai_configurations
  - LLMProvider enum extended with KIMI, GLM, CUSTOM values
  - SecureKeyStorage.VALID_PROVIDERS expanded to 6 providers
  - AIConfigurationCreate schema with base_url + display_name + model_validator for custom provider
  - AIConfigurationResponse includes base_url and display_name
  - ModelListingService.list_models_for_workspace() with per-provider failure isolation
  - ProviderModel dataclass and ModelListResponse/ProviderModelItem schemas
  - GET /ai/configurations/models endpoint returning models from all active providers

affects:
  - 13-02-model-override (uses LLMProvider extended enum + AIConfiguration.base_url)
  - 13-03-provider-ui (uses ModelListResponse + ProviderModelItem schemas + GET /models)
  - frontend model selection features

tech-stack:
  added: []
  patterns:
    - Per-provider failure isolation — each provider fetched independently; exceptions return fallback models with is_selectable=False
    - Module-level asyncio.Lock for genai.configure() thread safety in model listing
    - Module-level imports for patchable dependencies in tests (not lazy function imports)
    - model_validator on AIConfigurationCreate enforces base_url required when provider=custom

key-files:
  created:
    - backend/alembic/versions/070_extend_ai_config_custom_provider.py
    - backend/src/pilot_space/ai/providers/model_listing.py
  modified:
    - backend/src/pilot_space/infrastructure/database/models/ai_configuration.py
    - backend/src/pilot_space/ai/infrastructure/key_storage.py
    - backend/src/pilot_space/api/v1/schemas/ai_configuration.py
    - backend/src/pilot_space/api/v1/routers/ai_configuration.py
    - backend/tests/unit/ai/test_model_listing.py
    - backend/tests/unit/routers/test_ai_configuration.py

key-decisions:
  - "model_listing.py imports AIConfigurationRepository at module level (not lazily) to enable unittest.mock.patch with simple module path"
  - "ModelListingService uses its own _google_model_listing_lock rather than importing _google_api_lock from router (avoids cross-module private access)"
  - "Anthropic _fetch_anthropic_models returns hardcoded fallback — Anthropic models.list() requires beta header not in stable SDK"
  - "base_url required for custom provider validated via Pydantic model_validator(mode=after) on AIConfigurationCreate"
  - "VALID_PROVIDERS expanded to 6 values in SecureKeyStorage — kimi/glm/custom now accepted for key storage and validation"

patterns-established:
  - "Per-provider exception isolation: wrap each provider fetch in try/except; on failure return _FALLBACK_MODELS[provider] with is_selectable=False"
  - "OpenAI-compat pattern: kimi/glm/custom all use AsyncOpenAI(api_key=X, base_url=Y) with provider-specific default URLs"

requirements-completed: [AIPR-01, AIPR-02, AIPR-03, AIPR-05]

duration: 28min
completed: "2026-03-09"
---

# Phase 13 Plan 01: Provider Registry + Model Listing Summary

**Extended BYOK registry with Kimi/GLM/custom OpenAI-compat providers via migration 070 + ModelListingService with per-provider failure isolation exposed via GET /ai/configurations/models**

## Performance

- **Duration:** 28 min
- **Started:** 2026-03-09T16:31:13Z
- **Completed:** 2026-03-09T16:58:50Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Migration 070 adds kimi/glm/custom enum values + base_url/display_name columns to ai_configurations table
- ModelListingService aggregates models from all active providers with per-provider exception isolation
- GET /ai/configurations/models endpoint returns 200 with ModelListResponse even when some providers are unreachable (degraded mode)
- All 13 test cases pass (XPASS) covering schema validation, model aggregation, and failure isolation

## Task Commits

Each task was committed atomically (previous session committed Tasks 1-3 before this execution):

1. **Task 1: Wave-0 test scaffolds** - `5e7e088f` (test)
2. **Task 2: Migration 070 + model/schema/key_storage** - `2babb859` (feat, bundled in docs commit)
3. **Task 3: ModelListingService + /models endpoint** - `2babb859` (feat, bundled in docs commit)

**Note:** Previous session completed all backend Tasks 2-3 and committed them. This execution verified implementation correctness and confirmed all 13 tests pass.

## Files Created/Modified

- `backend/alembic/versions/070_extend_ai_config_custom_provider.py` - Migration adding kimi/glm/custom enum values + base_url/display_name columns
- `backend/src/pilot_space/ai/providers/model_listing.py` - ModelListingService with per-provider failure isolation, hardcoded fallbacks, and OpenAI-compat support
- `backend/src/pilot_space/infrastructure/database/models/ai_configuration.py` - LLMProvider enum extended (KIMI, GLM, CUSTOM), base_url + display_name columns
- `backend/src/pilot_space/ai/infrastructure/key_storage.py` - VALID_PROVIDERS expanded to 6 values
- `backend/src/pilot_space/api/v1/schemas/ai_configuration.py` - AIConfigurationCreate/Response extended, ModelListResponse + ProviderModelItem added
- `backend/src/pilot_space/api/v1/routers/ai_configuration.py` - GET /models endpoint, ModelListResponse import, base_url/display_name in create/response
- `backend/tests/unit/ai/test_model_listing.py` - 6 tests for ModelListingService
- `backend/tests/unit/routers/test_ai_configuration.py` - 7 tests for schema validation + /models endpoint

## Decisions Made

- **module-level imports for patchability**: AIConfigurationRepository imported at module level in model_listing.py so tests can patch `pilot_space.ai.providers.model_listing.AIConfigurationRepository` directly
- **separate Google lock**: ModelListingService uses `_google_model_listing_lock` rather than importing `_google_api_lock` from router to avoid cross-module private attribute access (pyright reportPrivateUsage)
- **hardcoded Anthropic fallback**: Anthropic's `/models` endpoint requires a beta header; returning the fallback list avoids auth-dependent behavior in model listing
- **model_validator for custom provider**: Pydantic `model_validator(mode="after")` on AIConfigurationCreate enforces `base_url` required when `provider=CUSTOM`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Renamed `_google_api_lock` to `google_api_lock` in router (reverted)**
- **Found during:** Task 3 (model_listing.py creation)
- **Issue:** pyright `reportPrivateUsage` error when importing `_google_api_lock` from router
- **Fix:** Used a separate module-level lock `_google_model_listing_lock` in model_listing.py instead of importing the router's private lock
- **Files modified:** backend/src/pilot_space/ai/providers/model_listing.py
- **Verification:** pyright 0 errors

**2. [Rule 1 - Bug] Lazy imports replaced with module-level imports**
- **Found during:** Task 3 test verification
- **Issue:** Tests patched `pilot_space.ai.providers.model_listing.AIConfigurationRepository` but lazy function imports don't create module attributes — patch target was missing
- **Fix:** Moved AIConfigurationRepository and decrypt_api_key imports to module level
- **Files modified:** backend/src/pilot_space/ai/providers/model_listing.py
- **Verification:** All 6 test_model_listing.py tests now XPASS

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- Previous session committed Tasks 1-3 before this execution started (including schema changes, migration, and ModelListingService). This execution verified the implementation was correct and all tests pass.
- prek pre-commit hooks had stash/restore conflicts due to multiple unstaged files from previous session. Resolved by staging all modified files before commit.

## User Setup Required

None - no external service configuration required. The migration must be applied when the database is available: `cd backend && alembic upgrade head`

## Next Phase Readiness

- Backend provider registry fully extended for Kimi, GLM, and custom OpenAI-compatible providers
- ModelListingService ready for consumption by frontend model selector (Plan 13-03)
- GET /ai/configurations/models endpoint returns live + fallback models with status indicators
- Plan 13-02 (model override routing) can use the extended LLMProvider enum and AIConfiguration.base_url

---
*Phase: 13-ai-provider-registry-model-selection*
*Completed: 2026-03-09*
