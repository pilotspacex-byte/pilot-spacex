---
phase: quick-260316-phe
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/features/settings/pages/skills-settings-page.tsx
  - frontend/src/features/settings/components/my-skill-card.tsx
  - frontend/src/features/settings/components/template-card.tsx
  - frontend/src/features/settings/components/template-catalog.tsx
  - frontend/src/features/settings/components/skill-generator-modal.tsx
  - frontend/src/features/settings/components/create-template-modal.tsx
  - frontend/src/features/settings/components/edit-template-modal.tsx
  - frontend/src/services/api/user-skills.ts
  - frontend/src/services/api/skill-templates.ts
  - backend/src/pilot_space/api/v1/routers/user_skills.py
  - backend/src/pilot_space/api/v1/routers/skill_templates.py
autonomous: false
requirements: [QUICK-SKILL-INVESTIGATE]

must_haves:
  truths:
    - "Skills settings page loads at /{workspaceSlug}/skills without errors"
    - "User Skills section lists existing user skills (or shows empty state)"
    - "Skill Templates section lists available templates in a filterable grid"
    - "Clicking 'Add Skill' opens the skill generator modal"
    - "Clicking 'Use This' on a template opens generator modal pre-seeded with template"
    - "Admin can create a new skill template via 'Create Template' button"
    - "Admin can edit an existing workspace template via dropdown menu"
    - "Admin can delete a workspace template with confirmation dialog"
    - "User can toggle a skill active/inactive via hover action"
    - "User can delete a skill with confirmation dialog"
  artifacts:
    - path: "frontend/src/features/settings/pages/skills-settings-page.tsx"
      provides: "Main skills settings page with My Skills + Template Catalog"
    - path: "frontend/src/features/settings/components/skill-generator-modal.tsx"
      provides: "AI skill generation modal (form -> generating -> preview -> save)"
    - path: "backend/src/pilot_space/api/v1/routers/user_skills.py"
      provides: "User skill CRUD endpoints"
    - path: "backend/src/pilot_space/api/v1/routers/skill_templates.py"
      provides: "Skill template admin CRUD endpoints"
  key_links:
    - from: "skills-settings-page.tsx"
      to: "/api/v1/{workspace_id}/user-skills"
      via: "useUserSkills TanStack query"
      pattern: "useUserSkills\\(workspaceSlug\\)"
    - from: "template-catalog.tsx"
      to: "/api/v1/{workspace_id}/skill-templates"
      via: "useSkillTemplates TanStack query"
      pattern: "useSkillTemplates\\(workspaceSlug\\)"
    - from: "skill-generator-modal.tsx"
      to: "useCreateUserSkill + useGenerateSkill"
      via: "mutation hooks for personal skill creation"
      pattern: "createUserSkill\\.mutateAsync|createPersonal\\.mutateAsync"
---

<objective>
Validate all Pilot Space skill features (listing, create, read, remove) via browser automation, document issues found, fix any bugs or UI/UX problems, and re-validate fixes.

Purpose: Ensure the skills feature works end-to-end for both regular users and admins — covering user skills CRUD, template catalog browsing, template CRUD (admin), and skill generation flow.
Output: Working, validated skill features with all bugs fixed.
</objective>

<execution_context>
@/Users/tindang/workspaces/tind-repo/pilot-space/.claude/get-shit-done/workflows/execute-plan.md
@/Users/tindang/workspaces/tind-repo/pilot-space/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/features/settings/pages/skills-settings-page.tsx
@frontend/src/features/settings/components/my-skill-card.tsx
@frontend/src/features/settings/components/template-card.tsx
@frontend/src/features/settings/components/template-catalog.tsx
@frontend/src/features/settings/components/skill-generator-modal.tsx
@frontend/src/features/settings/components/create-template-modal.tsx
@frontend/src/features/settings/components/edit-template-modal.tsx
@frontend/src/services/api/user-skills.ts
@frontend/src/services/api/skill-templates.ts
@backend/src/pilot_space/api/v1/routers/user_skills.py
@backend/src/pilot_space/api/v1/routers/skill_templates.py

<interfaces>
<!-- Frontend API hooks -->
From frontend/src/services/api/user-skills.ts:
- useUserSkills(workspaceSlug) -> { data: UserSkill[], isLoading, isError }
- useCreateUserSkill(workspaceSlug) -> mutation({ template_id, experience_description? })
- useUpdateUserSkill(workspaceSlug) -> mutation({ id, data: { is_active?, experience_description? } })
- useDeleteUserSkill(workspaceSlug) -> mutation(id)

From frontend/src/services/api/skill-templates.ts:
- useSkillTemplates(workspaceSlug) -> { data: SkillTemplate[], isLoading, isError }
- useCreateSkillTemplate(workspaceSlug) -> mutation({ name, description, skill_content, icon?, sort_order?, role_type? })
- useUpdateSkillTemplate(workspaceSlug) -> mutation({ id, data: { name?, description?, skill_content?, icon?, is_active? } })
- useDeleteSkillTemplate(workspaceSlug) -> mutation(id)

<!-- UI Path -->
Navigation: http://localhost:3000/{workspaceSlug}/skills
Test user: e2e-test@pilotspace.dev / TestPassword123!
Workspace slug: "workspace"
</interfaces>
</context>

<tasks>

<task type="investigation">
  <name>Task 1: Browser validation of all skill features</name>
  <files>None (investigation only)</files>
  <action>
Use `agent-browser` to systematically validate every skill feature. Test as admin user (e2e-test@pilotspace.dev).

**Pre-requisite:** Ensure dev servers are running (backend port 8000, frontend port 3000).

**Test sequence:**

1. **Login and navigate:**
   - Navigate to http://localhost:3000/workspace/skills
   - Verify page loads without console errors or blank screens
   - Screenshot the initial state

2. **Listing - User Skills section:**
   - Verify "My Skills" section is visible
   - Check if existing skills are displayed or empty state shows
   - Note any rendering issues (truncation, overflow, alignment)

3. **Listing - Template Catalog section:**
   - Verify "Skill Templates" section loads
   - Check if templates render in grid layout (1/2/3 columns responsive)
   - Check filter chips if multiple role types exist
   - Check template card rendering (icon, name, source badge, description, "Use This" button)
   - Note any visual issues

4. **Create - Skill Template (admin):**
   - Click "Create Template" button
   - Fill form: name="Test QA Template", description="Quality assurance skills", content="You are a QA engineer...", icon="" (leave empty to test default)
   - Submit and verify template appears in catalog
   - Screenshot the result

5. **Edit - Skill Template (admin):**
   - On the newly created template, hover to reveal actions dropdown (three-dot menu)
   - Click Edit from dropdown
   - Verify form pre-fills with template data
   - Change description to "Updated QA skills"
   - Save and verify changes reflected

6. **Create - User Skill (via template):**
   - Click "Use This" on a template
   - Verify skill generator modal opens with template name in header
   - Enter experience description (>10 chars): "Senior QA engineer with 5 years of Selenium and Cypress experience"
   - Click Generate and wait for AI generation
   - If AI generation fails (no API key configured), document the error handling
   - If generation succeeds, verify preview step shows content + editable name
   - Save and verify skill appears in "My Skills" section

7. **Create - User Skill (standalone "Add Skill"):**
   - Click "Add Skill" button (no template pre-seeded)
   - Verify generator modal opens without template context
   - Test the mode toggle (For Me / For Workspace) if visible
   - Enter description and attempt generation

8. **Toggle - User Skill active/inactive:**
   - If user skills exist, hover over a skill card
   - Click the power icon to toggle active state
   - Verify toast message and visual state change (opacity)

9. **Delete - User Skill:**
   - Hover over a skill card, click delete (trash icon)
   - Verify confirmation dialog appears with correct skill name
   - Confirm deletion
   - Verify skill removed from list and toast shown

10. **Delete - Skill Template (admin):**
    - On a workspace template (not built-in), open dropdown
    - Click Delete
    - Verify confirmation dialog
    - Confirm deletion
    - Verify template removed from catalog

11. **Edge cases:**
    - Check what happens with very long skill names (truncation)
    - Check empty state when no templates exist
    - Check if built-in templates show lock icon and restricted actions
    - Check "Plugins" and "Action Buttons" tabs are visible for admin

**Document all issues found** in a structured list with:
- Issue ID (SKL-01, SKL-02, ...)
- Description
- Steps to reproduce
- Expected vs actual behavior
- Severity (critical/major/minor/cosmetic)
- Screenshot reference
  </action>
  <verify>
    <automated>echo "Browser validation is manual — check agent-browser output for screenshots and documented issues"</automated>
  </verify>
  <done>All 11 test areas validated, all issues documented with severity and reproduction steps</done>
</task>

<task type="auto">
  <name>Task 2: Fix all issues found during browser validation</name>
  <files>
    frontend/src/features/settings/pages/skills-settings-page.tsx
    frontend/src/features/settings/components/my-skill-card.tsx
    frontend/src/features/settings/components/template-card.tsx
    frontend/src/features/settings/components/template-catalog.tsx
    frontend/src/features/settings/components/skill-generator-modal.tsx
    frontend/src/features/settings/components/create-template-modal.tsx
    frontend/src/features/settings/components/edit-template-modal.tsx
    frontend/src/services/api/user-skills.ts
    frontend/src/services/api/skill-templates.ts
    backend/src/pilot_space/api/v1/routers/user_skills.py
    backend/src/pilot_space/api/v1/routers/skill_templates.py
  </files>
  <action>
For each issue documented in Task 1, implement the fix. Common patterns to watch for based on codebase analysis:

**Likely backend issues:**
- API endpoint returning wrong status codes or missing fields
- RLS context not set before skill queries (must call `set_rls_context` — note skill_templates router does NOT call it for GET)
- Soft-deleted records appearing in listings
- `workspace_id` path param vs `workspaceSlug` mismatch (frontend sends slug, backend expects UUID — check if workspace resolution middleware handles this)

**Likely frontend issues:**
- Console errors from missing data fields or undefined values
- Hover actions not visible or clickable on touch devices (opacity-0 pattern)
- Modal not resetting state properly on close (setTimeout reset race conditions)
- TanStack query cache not invalidating after mutations
- API client path using `workspaceSlug` where backend expects `workspace_id` UUID
- `useGenerateSkill` / `useCreateRoleSkill` from onboarding hooks may have different API contract than user-skills endpoints

**UI/UX patterns to fix if found:**
- Missing loading states during mutations (button should show spinner)
- Missing error boundaries or error messages
- Confirmation dialogs not accessible (missing focus trap, escape handling)
- Cards not responsive on mobile viewports

**For each fix:**
1. Read the relevant source file
2. Apply minimal, targeted fix
3. Verify TypeScript compiles: `cd frontend && pnpm type-check`
4. Verify lint passes: `cd frontend && pnpm lint`

If backend fixes needed:
1. Apply fix
2. Verify: `cd backend && uv run pyright`
3. Verify: `cd backend && uv run ruff check`
  </action>
  <verify>
    <automated>cd /Users/tindang/workspaces/tind-repo/pilot-space/frontend && pnpm type-check && pnpm lint</automated>
  </verify>
  <done>All documented issues fixed, frontend type-check and lint pass, backend pyright and ruff pass (if backend changes made)</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Fixed all skill feature issues found during browser validation — covering listing, create, read, toggle, and delete flows for both user skills and skill templates.</what-built>
  <how-to-verify>
    1. Navigate to http://localhost:3000/workspace/skills
    2. Verify the page loads without errors
    3. Check "My Skills" section displays correctly (cards or empty state)
    4. Check "Skill Templates" section displays template grid
    5. Try creating a template (admin): Click "Create Template", fill form, submit
    6. Try using a template: Click "Use This" on a template, fill experience, generate
    7. Try toggling a skill active/inactive (hover over card, click power icon)
    8. Try deleting a skill (hover, click trash, confirm)
    9. Try deleting a template (dropdown menu, delete, confirm)
    10. Verify all toast notifications appear correctly
  </how-to-verify>
  <resume-signal>Type "approved" if all flows work, or describe remaining issues</resume-signal>
</task>

</tasks>

<verification>
- Skills settings page loads at /workspace/skills without console errors
- User skills CRUD (list, create via template, toggle active, delete) all functional
- Template catalog displays and filters correctly
- Template CRUD (create, edit, delete) works for admin users
- Skill generator modal completes full flow (form -> generate -> preview -> save)
- All confirmation dialogs work correctly
- Toast notifications appear for success/error states
- Frontend quality gates pass (type-check + lint)
</verification>

<success_criteria>
- Zero console errors on the skills settings page
- All CRUD operations for user skills work end-to-end
- All CRUD operations for skill templates work end-to-end (admin)
- Skill generator modal handles both template-seeded and standalone flows
- All UI/UX issues found during browser testing are resolved
- Frontend type-check and lint pass
</success_criteria>

<output>
After completion, create `.planning/quick/260316-phe-investigate-into-current-pilot-space-ski/260316-phe-SUMMARY.md`
</output>
