---
phase: quick-260317-hms
plan: 01
subsystem: ai-providers
tags: [workspace-llm, provider-routing, byok, refactor]
dependency_graph:
  requires: []
  provides: [resolve_workspace_llm_config, WorkspaceLLMConfig, workspace-aware-extraction, workspace-aware-intent, workspace-aware-skill-gen]
  affects: [pilot_space.ai.providers, pilot_space.application.services.extraction, pilot_space.application.services.intent, pilot_space.application.services.role_skill]
tech_stack:
  added: []
  patterns: [shared-helper, workspace-override, backward-compatible-parameter]
key_files:
  created:
    - backend/tests/unit/services/test_workspace_provider_resolution.py
  modified:
    - backend/src/pilot_space/ai/providers/provider_selector.py
    - backend/src/pilot_space/ai/providers/__init__.py
    - backend/src/pilot_space/application/services/extraction/extract_issues_service.py
    - backend/src/pilot_space/application/services/intent/detection_service.py
    - backend/src/pilot_space/application/services/role_skill/generate_role_skill_service.py
    - backend/tests/unit/services/test_extraction_service.py
    - backend/tests/unit/services/test_role_skill_services.py
decisions:
  - "workspace_override uses lazy import SecureKeyStorage inside resolve_workspace_llm_config; tests patch pilot_space.ai.infrastructure.key_storage.SecureKeyStorage to intercept"
  - "WorkspaceLLMConfig is a frozen dataclass in provider_selector.py (colocation with resolver avoids circular imports)"
  - "test_rate_limit_enforced fixed to use _RATE_LIMIT_MAX constant (was hardcoded 5, actual limit is 30)"
metrics:
  duration: ~35 minutes
  completed: 2026-03-17
  tasks_completed: 3
  files_changed: 8
---

# Phase quick-260317-hms Plan 01: Migrate Provider Settings to Workspace Level Summary

**One-liner:** Extracted shared `resolve_workspace_llm_config` helper and `WorkspaceLLMConfig` dataclass from `GenerateRoleSkillService._resolve_llm_provider`, unified all 3 AI services (extraction, intent detection, skill generation) to use workspace-configured LLM provider, model, and base_url via `ProviderSelector.workspace_override`.

## What Was Built

### Task 1: Shared workspace LLM resolution helper (TDD)

**Files:** `provider_selector.py`, `test_workspace_provider_resolution.py`

Added to `provider_selector.py`:
- `WorkspaceLLMConfig` frozen dataclass: `provider`, `api_key`, `base_url`, `model_name`
- `base_url` field added to `ProviderConfig` (optional, defaults to None - backward compatible)
- `resolve_workspace_llm_config(session, workspace_id)` async function: 4-step resolution
  1. Workspace `default_llm_provider` setting + SecureKeyStorage key
  2. Any other configured LLM provider in the workspace
  3. App-level `ANTHROPIC_API_KEY` env var
  4. `None` (caller handles gracefully)
- `workspace_override` parameter on `ProviderSelector.select_with_config()`: when provided with `model_name`, overrides static routing table model while preserving circuit breaker logic
- Exported `WorkspaceLLMConfig` and `resolve_workspace_llm_config` from `__all__` and `providers/__init__.py`

13 new tests in `test_workspace_provider_resolution.py` covering:
- Default provider resolution with key found
- None workspace_id fallback to app key
- Fallback to any LLM provider when default has no key
- App-level Anthropic key fallback
- None when no config found anywhere
- `workspace_override` model replacement, base_url passthrough, and backward compatibility

### Task 2: Migrate 3 services

**ExtractIssuesService** (`extract_issues_service.py`):
- Removed `_resolve_api_key` method (60 lines)
- `_call_llm` now calls `resolve_workspace_llm_config` → returns `None` early if no config
- `AsyncAnthropic(api_key=ws_config.api_key, base_url=ws_config.base_url or None)`
- Provider-aware timeout: Ollama 90s, others 60s
- `ResilientExecutor.execute(provider=ws_config.provider, ...)` for correct circuit breaker tracking

**IntentDetectionService** (`detection_service.py`):
- Removed `_resolve_api_key` method
- Same migration pattern; Ollama 90s, others 30s

**GenerateRoleSkillService** (`generate_role_skill_service.py`):
- Removed `_resolve_llm_provider` method (65 lines of duplicated logic)
- `_try_generate_via_ai` now uses shared `resolve_workspace_llm_config` + `workspace_override`

**Test updates:**
- `test_extraction_service.py`: replaced `patch.object(service, "_resolve_api_key")` with `patch("...resolve_workspace_llm_config")`
- `test_role_skill_services.py`: added `mock_no_llm_config` autouse fixture to both test classes (prevents real API calls when app key is in env)
- Fixed `test_rate_limit_enforced`: used `_RATE_LIMIT_MAX` constant instead of hardcoded 5 (pre-existing bug revealed by proper mocking)

### Task 3: Quality gates

- `ruff check`: 0 warnings
- `pyright`: 0 errors
- All provider selector tests pass (42 tests)
- All workspace resolution tests pass (13 tests)
- All extraction service tests pass
- All intent service tests pass
- Role skill tests pass except pre-existing `test_create_rejects_duplicate_role_type` (SQLite raises IntegrityError instead of ValueError — pre-existing, unrelated)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_rate_limit_enforced hardcoded limit mismatch**
- **Found during:** Task 2
- **Issue:** Test expected rate limit error after 5 generations but `_RATE_LIMIT_MAX = 30`. Was masked by real API call failure.
- **Fix:** Updated test to iterate `_RATE_LIMIT_MAX` times using the constant
- **Files modified:** `tests/unit/services/test_role_skill_services.py`
- **Commit:** efe3ef26

**2. [Rule 2 - Missing] Tests needed mock_no_llm_config autouse fixture**
- **Found during:** Task 2
- **Issue:** `TestGenerateRoleSkillService` and `TestGenerateRoleSkillAI` were making real API calls after migration because app-level Anthropic key exists in env. Tests expect `template-v1` model (template fallback).
- **Fix:** Added `@pytest.fixture(autouse=True)` `mock_no_llm_config` to both test classes patching `resolve_workspace_llm_config` to return `None`
- **Files modified:** `tests/unit/services/test_role_skill_services.py`
- **Commit:** efe3ef26

**3. [Rule 3 - Blocking] detect-secrets flagged mock API key strings in test file**
- **Found during:** Task 1 commit
- **Issue:** Mock API key strings like `"sk-ant-test-key"` triggered pre-commit `detect-secrets` hook
- **Fix:** Added `# pragma: allowlist secret` comments to all mock API key strings in test file
- **Files modified:** `tests/unit/services/test_workspace_provider_resolution.py`
- **Commit:** 1a798d05

## Self-Check: PASSED

All source and test files confirmed on disk. All 3 task commits (1a798d05, efe3ef26, da3c5101) confirmed in git log.
