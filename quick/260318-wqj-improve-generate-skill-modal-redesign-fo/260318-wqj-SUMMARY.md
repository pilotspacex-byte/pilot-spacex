---
quick_task: 260318-wqj
subsystem: skills
tags: [skills, ai-generation, tags, usage, modal-redesign, prompt-extraction]
dependency_graph:
  requires: []
  provides: [tags-usage-on-skills, skill-generation-prompt-module, skill-add-modal-tags-usage]
  affects: [role-skills, user-skills, workspace-role-skills, skill-add-modal, skill-card]
tech_stack:
  added: [skill_generation.py prompt module, skill-add-modal-parts.tsx]
  patterns: [prompt-module extraction, TagChipInput chip UI, AI response field forwarding]
key_files:
  created:
    - backend/alembic/versions/090_add_tags_and_usage_to_skills.py
    - backend/src/pilot_space/ai/prompts/skill_generation.py
    - frontend/src/features/settings/components/skill-add-modal-parts.tsx
  modified:
    - backend/src/pilot_space/infrastructure/database/models/user_skill.py
    - backend/src/pilot_space/infrastructure/database/models/user_role_skill.py
    - backend/src/pilot_space/infrastructure/database/models/workspace_role_skill.py
    - backend/src/pilot_space/api/v1/schemas/user_skill.py
    - backend/src/pilot_space/api/v1/schemas/role_skill.py
    - backend/src/pilot_space/api/v1/schemas/workspace_role_skill.py
    - backend/src/pilot_space/application/services/role_skill/generate_role_skill_service.py
    - backend/src/pilot_space/api/v1/routers/role_skills.py
    - backend/src/pilot_space/ai/prompts/__init__.py
    - frontend/src/services/api/user-skills.ts
    - frontend/src/services/api/workspace-role-skills.ts
    - frontend/src/services/api/role-skills.ts
    - frontend/src/features/settings/components/skill-add-modal.tsx
    - frontend/src/features/settings/components/skill-card.tsx
decisions:
  - Extract prompt builder into dedicated ai/prompts/skill_generation.py module for testability and reuse
  - Export MAX_TAGS/MAX_TAG_LENGTH/AI_MIN_CHARS constants from parts file to enable test access
  - Split skill-add-modal.tsx into modal + parts file to stay under 700-line limit
  - Use optional chaining on suggestedTags/suggestedUsage from AI response (backend may return null on fallback paths)
metrics:
  duration: ~3.5h
  completed: "2026-03-18"
  tasks_completed: 2
  files_changed: 26
---

# Quick Task 260318-wqj: Add Tags+Usage to Skill System, Redesign Modal

One-liner: Extended skill system with tags (JSON array) and usage (text) fields across all 3 skill tables, extracted AI prompt to a dedicated module, and redesigned SkillAddModal with chip-based tag input and usage textarea backed by AI suggestions.

## Tasks Completed

### Task 1: Backend — Tags+Usage, Prompt Extraction

**Alembic migration 090**: Added `tags` (JSON, `server_default='[]'`) and `usage` (Text, nullable) columns to `user_skills`, `user_role_skills`, and `workspace_role_skills`.

**SQLAlchemy models**: Added `tags: Mapped[list[str]]` and `usage: Mapped[str | None]` columns to all 3 models.

**Prompt module**: Extracted `_build_generation_prompt` inline function from `generate_role_skill_service.py` into `backend/src/pilot_space/ai/prompts/skill_generation.py` with:
- `SKILL_GENERATION_PROMPT_TEMPLATE` — requests 4-key JSON: `skill_content`, `suggested_role_name`, `suggested_tags` (3-8 short ability tags), `suggested_usage` (1-2 sentence description)
- `build_skill_generation_prompt(role_type, display_name, ...) -> str`

**Service updates**: `GenerateRoleSkillResult` dataclass extended with `suggested_tags`/`suggested_usage`; `_parse_ai_response` returns 5-tuple; `_extract_tags()` static method added for robust tag extraction from AI response.

**Schema updates**: All request/response schemas (`RoleSkillResponse`, `GenerateRoleSkillResponse`, `UserSkillSchema`, `UserSkillCreate`, `UserSkillUpdate`, `WorkspaceRoleSkillResponse`) updated with `tags`/`usage` fields.

**Test DDL**: 4 conftest/test files updated with `tags TEXT DEFAULT '[]'` and `usage TEXT` DDL columns. Fixed 5-tuple unpacking in service and parse tests. Fixed `MagicMock` spec in router tests.

**Commits**: `8def2af5`

### Task 2: Frontend — API Types, Modal Redesign, Skill Card

**API types**: Added `tags: string[]` and `usage: string | null` to `UserSkill`, `WorkspaceRoleSkill`, `RoleSkill`; added `suggestedTags`/`suggestedUsage` to `GenerateSkillResponse`; added `tags`/`usage` to create/update payloads.

**SkillAddModal redesign**:
- Manual tab: Added usage textarea (500-char limit with counter) and `TagChipInput` (chip-based, Enter/comma to add, Backspace removes last, max 20 tags × 30 chars)
- AI Preview step: Added usage textarea (pre-filled from `suggestedUsage`) and tag chips (pre-filled from `suggestedTags`, editable)
- `handleManualSave` and `handleAiSave` now pass `tags`/`usage` to `createUserSkill.mutateAsync`
- Extracted `TagChipInput`, `AiFormStep`, `GeneratingStep`, `AiPreviewStep` to `skill-add-modal-parts.tsx` to stay under 700-line limit

**SkillCard**: Added usage text display below content and tag chips row with `Tag` icon.

**Test fixes**: Updated 5 existing test files to include `tags`/`usage` in mock objects. Added 3 new tests in `skill-add-modal.test.tsx`.

**Commits**: `d854919c`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Multiple test DDL files missing new columns**
- **Found during:** Task 1 test execution
- **Issue:** `CREATE TABLE IF NOT EXISTS` in test conftest files silently skips recreation, leaving tables without new `tags`/`usage` columns → `sqlite3.OperationalError`
- **Fix:** Added `tags TEXT DEFAULT '[]'` and `usage TEXT` to DDL in 4 files: `tests/unit/services/conftest.py`, `tests/unit/ai/agents/conftest.py`, `tests/unit/repositories/test_user_skill_repository.py`, `tests/unit/repositories/test_role_skill_repository.py`
- **Commit:** `8def2af5`

**2. [Rule 1 - Bug] MagicMock spec validation failure in router tests**
- **Found during:** Task 1 test execution
- **Issue:** `MagicMock(spec=UserSkill)` auto-generates `MagicMock` objects for new `tags`/`usage` attributes; Pydantic v2 rejects `MagicMock` as invalid string/list input
- **Fix:** Explicitly set `skill.tags = []` and `skill.usage = None` in `_make_skill()` helper in `test_user_skills_router.py`
- **Commit:** `8def2af5`

**3. [Rule 3 - Blocking] skill-add-modal.tsx exceeded 700-line limit**
- **Found during:** Task 2 pre-commit hook
- **Issue:** Adding usage/tags UI to modal pushed file to 873 lines, failing `check-frontend-file-size` hook
- **Fix:** Extracted `TagChipInput`, `AiFormStep`, `GeneratingStep`, `AiPreviewStep` into new `skill-add-modal-parts.tsx` (352 lines); main modal reduced to 551 lines
- **Files created:** `frontend/src/features/settings/components/skill-add-modal-parts.tsx`
- **Commit:** `d854919c`

**4. [Rule 2 - Missing] Existing test mock objects missing new required fields**
- **Found during:** Task 2 TypeScript type check
- **Issue:** 5 existing test files had `RoleSkill`, `UserSkill`, `WorkspaceRoleSkill`, `GenerateSkillResponse` mock objects without `tags`/`usage`/`suggestedTags`/`suggestedUsage` → TypeScript errors
- **Fix:** Added missing fields to mock objects in `OnboardingChecklist.test.tsx`, `SkillGenerationWizard.test.tsx`, `useRoleSkillActions.test.ts`, `workspace-skill-card.test.tsx`, `user-skills.test.ts`
- **Commit:** `d854919c`

## Self-Check: PASSED

- FOUND: backend/alembic/versions/090_add_tags_and_usage_to_skills.py
- FOUND: backend/src/pilot_space/ai/prompts/skill_generation.py
- FOUND: frontend/src/features/settings/components/skill-add-modal-parts.tsx
- FOUND: commit 8def2af5
- FOUND: commit d854919c
