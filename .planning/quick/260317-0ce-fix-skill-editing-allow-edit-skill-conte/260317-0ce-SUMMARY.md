---
phase: quick
plan: 260317-0ce
subsystem: skills
tags: [skills, ai-parser, user-skills, frontend, migration]
dependency_graph:
  requires: []
  provides:
    - skill_name stored per user skill (backend + DB)
    - robust AI response JSON extraction via regex
    - editable skill preview in generator modal
    - expandable skill cards with inline SkillEditor
  affects:
    - backend/src/pilot_space/application/services/role_skill/generate_role_skill_service.py
    - backend/src/pilot_space/infrastructure/database/models/user_skill.py
    - frontend/src/features/settings/components/skill-generator-modal.tsx
    - frontend/src/features/settings/components/my-skill-card.tsx
tech_stack:
  added: []
  patterns:
    - Regex JSON extraction fallback for AI responses
    - Expandable card with local expanded/editing state
key_files:
  created:
    - backend/alembic/versions/088_add_skill_name_to_user_skills.py
    - backend/tests/unit/test_parse_ai_response.py
  modified:
    - backend/src/pilot_space/application/services/role_skill/generate_role_skill_service.py
    - backend/src/pilot_space/infrastructure/database/models/user_skill.py
    - backend/src/pilot_space/infrastructure/database/repositories/user_skill_repository.py
    - backend/src/pilot_space/application/services/user_skill/create_user_skill_service.py
    - backend/src/pilot_space/api/v1/schemas/user_skill.py
    - backend/src/pilot_space/api/v1/routers/user_skills.py
    - frontend/src/services/api/user-skills.ts
    - frontend/src/services/api/user-skills.test.ts
    - frontend/src/features/settings/components/skill-generator-modal.tsx
    - frontend/src/features/settings/components/my-skill-card.tsx
    - frontend/src/features/settings/pages/skills-settings-page.tsx
decisions:
  - Remove preview prop from PreviewStep — replaced fully by editableContent state
  - skill_name is nullable Text column so existing rows are unaffected without migration
  - Keep regex extraction as second attempt (after direct json.loads) to preserve fast-path
metrics:
  duration: "~13 minutes"
  completed_date: "2026-03-17"
  tasks_completed: 2
  files_changed: 11
---

# Quick Task 260317-0ce: Fix Skill Editing — Allow Edit Skill Content Summary

**One-liner:** Regex JSON extraction from AI responses, nullable skill_name column + migration, editable preview textarea, expandable MySkillCard with inline SkillEditor.

## What Was Built

### Task 1: Backend — AI Parser Fix + skill_name

**AI response parser** (`generate_role_skill_service.py`): Added `import re` and a second JSON extraction attempt using `re.search(r'\{[\s\S]*\}', text)`. When AI wraps JSON in explanatory text like "Here is your skill: {...} Hope this helps!", the regex finds the JSON object and parses it. The fast path (direct `json.loads`) is preserved; regex is only tried when that fails. Only genuine non-JSON markdown falls through to the raw markdown fallback.

**UserSkill model**: Added `skill_name: Mapped[str | None]` with `nullable=True`.

**Migration 088**: Adds `skill_name TEXT NULL` column to `user_skills`. Revises `087_drop_role_type_unique_constraint`. Single head confirmed.

**Repository, Service, Schemas, Router**:
- `UserSkillRepository.create`: new `skill_name: str | None = None` parameter
- `CreateUserSkillService.create`: new `skill_name: str | None = None` parameter, threaded through to repository
- `UserSkillSchema`: added `skill_name: str | None = None`
- `UserSkillCreate`: added `skill_name: str | None = Field(...)` with max_length=200
- `UserSkillUpdate`: added `skill_content` and `skill_name` fields (enables content + name editing via PATCH)
- Router `create_user_skill`: passes `body.skill_name` to service

**Unit tests** (6): test_parse_valid_json, test_parse_json_in_markdown_fences, test_parse_json_embedded_in_text, test_parse_pure_markdown_no_json, test_parse_empty_response_returns_none, test_parse_too_short_response_returns_none — all pass.

### Task 2: Frontend — Editable Preview + Expandable Card

**user-skills.ts**: Added `skill_name` to `UserSkill`, `UserSkillCreate`, and `UserSkillUpdate`. Added `skill_content` to `UserSkillUpdate`.

**SkillGeneratorModal**: Added `editableContent` state initialized when preview is set. `PreviewStep` now renders a `<Textarea>` instead of a read-only `<pre>`. Word count reflects live edits to `editableContent`. `handleSave` always passes `editableContent` as `skill_content` and `editableName` as `skill_name`. Removed unused `preview` prop from `PreviewStep` interface.

**MySkillCard**: Rewritten as expandable card. Click on the header row toggles `expanded` state. When expanded + not editing: shows content in `<pre>` with an Edit button. When expanded + editing: renders `<SkillEditor>` inline. Hover actions now include a Pencil icon button that sets both `expanded=true` and `editing=true`. `displayName` prioritizes `skill.skill_name > template_name > 'Custom Skill'`. New `onEdit` prop in interface.

**SkillsSettingsPage**: Added `handleEditSkill` that calls `updateUserSkill.mutate` with the skill updates. Wired to `MySkillCard`'s `onEdit` prop. Delete dialog title updated to use `skill_name ?? template_name ?? 'Custom'`.

## Commits

| Hash | Message |
|------|---------|
| `066fd9a5` | feat(260317-0ce): fix AI parser + add skill_name to backend |
| `6ae5ed4a` | feat(260317-0ce): frontend skill editing — editable preview, skill_name, expandable cards |

## Deviations from Plan

None — plan executed exactly as written.

The only minor deviation was removing `preview` from `PreviewStep` props (per plan the parent still passes it, but since PreviewStep no longer uses it at all, removing the prop entirely was cleaner than keeping an unused parameter). TypeScript confirmed this was safe.

## Self-Check

### Files exist:
- backend/alembic/versions/088_add_skill_name_to_user_skills.py: FOUND
- backend/tests/unit/test_parse_ai_response.py: FOUND
- frontend/src/features/settings/components/my-skill-card.tsx: FOUND

### Commits exist:
- 066fd9a5: FOUND
- 6ae5ed4a: FOUND

## Self-Check: PASSED
