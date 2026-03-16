# Quick Task 260316-phe: Skill Feature Investigation & Fixes

## Task
Investigate Pilot Space skill features (listing, create, read, remove), validate via browser, fix issues.

## Issues Found & Fixed

| ID | Description | Severity | Fix | Commit |
|----|-------------|----------|-----|--------|
| SKL-01 | Template icons rendered Lucide names as text | Major | Added ICON_MAP in template-card.tsx | 16cccc06 |
| SKL-02 | Save & Activate 500 — lazy="raise" on UserSkill.template | Critical | Added selectinload in create path | 16cccc06 |
| SKL-03 | Toggle inactive removed skill from list (is_active filter) | Major | Removed is_active filter from get_by_user_workspace | 16cccc06 |
| SKL-04 | Delete template dialog duplicated "Template" | Cosmetic | Changed to `Delete "X"?` format | 16cccc06 |
| SKL-05 | Toggle/delete failed — same lazy="raise" root cause | Critical | Added get_by_id_with_template with selectinload | 16cccc06 |
| SKL-06 | Toggle active/inactive didn't update UI instantly | Major | Added optimistic updates to useUpdateUserSkill/useDeleteUserSkill | f01d76a0 |
| SKL-08 | Skill templates invisible — missing set_rls_context() | Critical | Added set_rls_context to all skill_templates router endpoints | f01d76a0 |

## Issues Noted (Not Fixed — Out of Scope)

| ID | Description | Severity | Notes |
|----|-------------|----------|-------|
| SKL-07 | Workspace switcher only shows 1 workspace | Major | Broader issue, not skill-specific |
| SKL-09 | "AI features disabled" banner persists after configuring Ollama | Minor | Likely checks at different scope (user-level vs workspace-level) |

## Files Changed

### Backend
- `backend/src/pilot_space/api/v1/routers/skill_templates.py` — Added set_rls_context() to all 4 endpoints
- `backend/src/pilot_space/api/v1/routers/user_skills.py` — (commit 16cccc06)
- `backend/src/pilot_space/infrastructure/database/repositories/user_skill_repository.py` — (commit 16cccc06)

### Frontend
- `frontend/src/services/api/user-skills.ts` — Optimistic updates for toggle/delete mutations
- `frontend/src/features/settings/components/template-card.tsx` — Icon mapping (commit 16cccc06)
- `frontend/src/features/settings/pages/skills-settings-page.tsx` — (commit 16cccc06)

## Validation Summary

All features validated via browser automation (agent-browser):
- Page load: Skills page loads at /{workspaceSlug}/skills
- Template catalog: Displays templates with icons, badges, filter chips
- Create template: Admin can create workspace templates
- Create skill: "Use This" → fill experience → Generate → Save & Activate
- Toggle active/inactive: Instant visual update (green/grey dot, opacity)
- Delete skill: Confirmation dialog → instant removal from list
- Delete template: Confirmation dialog with correct wording
