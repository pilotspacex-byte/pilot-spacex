# Tasks: User Management

**Feature**: User Management
**Branch**: `008-user-management`
**Created**: 2026-02-03
**Source**: `specs/008-user-management/`
**Author**: Tin Dang

---

## Phase 1: Foundation

### Backend Infrastructure

- [ ] T001 Create WorkspaceInvitation model in `backend/src/pilot_space/infrastructure/database/models/workspace_invitation.py`
  - Fields: id, workspace_id (FK), email, role, invited_by (FK), status enum (pending/accepted/expired/cancelled), expires_at, accepted_at
  - Indexes: (workspace_id, email) UNIQUE WHERE status='pending', (email, status), (workspace_id, status)
  - Source: plan.md Data Model, FR-016

- [ ] T002 Create Alembic migration for workspace_invitations table in `backend/alembic/versions/`
  - Include RLS policy: workspace_invitation_isolation (admin-only access scoped by workspace)
  - Source: FR-031

- [ ] T003 [P] Create InvitationRepository in `backend/src/pilot_space/infrastructure/database/repositories/invitation_repository.py`
  - Methods: create, get_by_id, get_by_workspace, get_pending_by_email, cancel, mark_accepted, mark_expired, exists_pending
  - Source: FR-016, US3

- [ ] T004 [P] Add InvitationResponse and InvitationCreateResponse schemas in `backend/src/pilot_space/api/v1/schemas/workspace.py`
  - InvitationResponse: id, email, role, status, invited_by, expires_at, created_at
  - InvitationCreateResponse: invitation_id, email, role, status, expires_at (for pending) OR WorkspaceMemberResponse (for immediate add)
  - Source: plan.md API Contracts

- [ ] T004a Fix role pattern mismatch in `backend/src/pilot_space/api/v1/schemas/workspace.py`
  - Change `WorkspaceMemberCreate.role` pattern from `^(admin|member|viewer)$` to `^(admin|member|guest)$`
  - Change `WorkspaceMemberUpdate.role` pattern from `^(admin|member|viewer)$` to `^(admin|member|guest)$`
  - Update docstring from "viewer" to "guest" to match WorkspaceRole enum
  - Source: WorkspaceRole enum uses GUEST not VIEWER, cross-artifact review finding #4

**Checkpoint**: Invitation model and repository ready. Schema role validation matches enum. Migration runs clean. `uv run pyright` passes.

---

## Phase 2: US1 — Reliable Authentication (P1)

**Goal**: Fix auth callback, remove dead endpoints, fix OWNER role assignment.
**Verify**: Sign up, OAuth login, token auto-refresh, logout all work end-to-end.

### Backend

- [ ] T005 Fix workspace creation to assign OWNER role in `backend/src/pilot_space/api/v1/routers/workspaces.py`
  - Change `WorkspaceRole.ADMIN` to `WorkspaceRole.OWNER` in `create_workspace` endpoint (line ~244)
  - Source: FR-007, RD-006

- [ ] T006 Remove 501 placeholder endpoints in `backend/src/pilot_space/api/v1/routers/auth.py`
  - Remove `auth_callback` (POST /callback) and `refresh_token` (POST /refresh)
  - Keep: login, get_current_user_profile, update_current_user_profile, logout
  - Source: RD-002

- [ ] T007 [P] Remove unused schemas in `backend/src/pilot_space/api/v1/schemas/auth.py`
  - Remove AuthCallbackRequest, RefreshTokenRequest (no longer used by any endpoint)
  - Remove from __all__ exports
  - Source: RD-002

### Frontend

- [ ] T008 Fix OAuth callback page in `frontend/src/app/(auth)/callback/page.tsx`
  - Replace setTimeout redirect with proper Supabase session detection via `supabase.auth.getSession()`
  - On valid session → redirect to `/`. On no session → redirect to `/login` with error
  - Source: FR-002, RD-001

- [ ] T009 Add session expiry redirect in `frontend/src/stores/AuthStore.ts`
  - In `onAuthStateChange`, when event is `TOKEN_REFRESHED` with null session, redirect to `/login`
  - Ensure `SIGNED_OUT` event clears state and redirects
  - Source: FR-004

### Tests

- [ ] T010 [P] Write unit tests for OWNER role fix in `backend/tests/unit/test_workspace_creation.py`
  - Test: workspace creation assigns OWNER role to creator
  - Test: created workspace has exactly one OWNER member
  - Source: FR-007

- [ ] T011 [P] Write unit test for auth router in `backend/tests/unit/test_auth_router.py`
  - Test: /callback and /refresh endpoints no longer exist (404)
  - Test: /me, /me PATCH, /logout still work
  - Source: RD-002

**Checkpoint**: Auth flow works end-to-end. OAuth callback properly detects session. Dead endpoints removed. OWNER role assigned on workspace creation. Quality gates: `uv run pyright && uv run ruff check && uv run pytest`

---

## Phase 3: US2 — User Profile Management (P2)

**Goal**: Users can view and edit their profile (name, avatar) from a settings page.
**Verify**: Navigate to profile settings, update name, see it reflected in sidebar.

### Frontend

- [ ] T012 Create profile settings route in `frontend/src/app/(workspace)/[workspaceSlug]/settings/profile/page.tsx`
  - Import and render ProfileSettingsPage component
  - Source: FR-008, RD-007

- [ ] T013 Create ProfileSettingsPage component in `frontend/src/features/settings/pages/profile-settings-page.tsx`
  - Display: email (read-only), full_name (editable), avatar (editable with upload)
  - Use AuthStore for read/write, `updateProfile()` for save
  - Error state: show toast on failure, preserve unsaved changes
  - WCAG: keyboard nav, ARIA labels, focus management
  - Source: FR-008 through FR-012, US2

- [ ] T014 [P] Add settings navigation links in `frontend/src/app/(workspace)/[workspaceSlug]/settings/page.tsx`
  - Add sidebar links: General, Members, Profile, AI Providers (existing), Integrations (existing)
  - Highlight current route
  - Source: RD-007

### Tests

- [ ] T015 Write unit tests for ProfileSettingsPage in `frontend/src/__tests__/settings/profile-settings-page.test.tsx`
  - Test: renders email as read-only
  - Test: submits name update and shows success
  - Test: handles save failure gracefully
  - Source: US2 acceptance scenarios

**Checkpoint**: Profile page works. Users can view and update their display name. Quality gates: `pnpm lint && pnpm type-check && pnpm test`

---

## Phase 4a: US3 — Workspace Member Invitation Backend (P2)

**Goal**: Backend invitation logic — service, endpoints, auto-accept on signup.
**Verify**: POST /members creates invitation or adds immediately, GET /invitations lists pending, DELETE cancels.

### Backend

- [ ] T016 Create WorkspaceService in `backend/src/pilot_space/application/services/workspace.py`
  - Method: `invite_member(workspace_id, email, role, invited_by)` → checks if user exists → adds immediately OR creates invitation
  - Uses UserRepository.get_by_email() + WorkspaceRepository.add_member() or InvitationRepository.create()
  - Validates: not already a member, no duplicate pending invitation
  - Source: FR-014, FR-015, FR-016

- [ ] T017 Implement POST /workspaces/{id}/members in `backend/src/pilot_space/api/v1/routers/workspaces.py`
  - Replace 501 placeholder with actual implementation using WorkspaceService
  - Return WorkspaceMemberResponse (existing user) or InvitationCreateResponse (pending)
  - Source: plan.md API Contract Endpoint 1

- [ ] T018 Implement GET /workspaces/{id}/invitations in `backend/src/pilot_space/api/v1/routers/workspaces.py`
  - List pending/expired/cancelled invitations for workspace
  - Admin-only access check
  - Source: plan.md API Contract Endpoint 2

- [ ] T019 Implement DELETE /workspaces/{id}/invitations/{invitation_id} in `backend/src/pilot_space/api/v1/routers/workspaces.py`
  - Cancel pending invitation (set status to cancelled)
  - Admin-only access check, 404 if not found or already accepted
  - Source: plan.md API Contract Endpoint 3

- [ ] T020 Extend ensure_user_synced for auto-accept invitations in `backend/src/pilot_space/dependencies.py`
  - After user creation/sync, query InvitationRepository.get_pending_by_email()
  - For each pending invitation: add as workspace member, mark invitation accepted
  - Source: FR-016, RD-004

- [ ] T020a Add ownership transfer validation guard in `backend/src/pilot_space/api/v1/routers/workspaces.py`
  - In `update_workspace_member` endpoint: if new role is OWNER, validate current user is OWNER, demote current OWNER to ADMIN
  - Prevent setting OWNER role via invitation (only via explicit transfer)
  - Ensure workspace always has exactly one OWNER
  - Source: FR-017, US4 acceptance scenario #6

### Tests

- [ ] T026 [P] Write unit tests for WorkspaceService in `backend/tests/unit/test_workspace_service.py`
  - Test: invite existing user → adds immediately
  - Test: invite non-existing user → creates pending invitation
  - Test: invite already-member → returns 409
  - Test: invite with duplicate pending → returns 409
  - Source: US3 acceptance scenarios

- [ ] T027 [P] Write integration tests for invitation endpoints in `backend/tests/integration/test_workspace_members.py`
  - Test: POST /members with existing user email
  - Test: POST /members with unknown email
  - Test: GET /invitations returns pending list
  - Test: DELETE /invitations cancels invitation
  - Test: non-admin gets 403
  - Test: ownership transfer demotes previous owner
  - Test: non-owner cannot transfer ownership
  - Source: plan.md API Contracts, US4 #6

**Checkpoint**: Invitation backend complete. All 3 endpoints implemented. Auto-accept on signup. Ownership transfer guarded. Quality gates: `uv run pyright && uv run ruff check && uv run pytest`

---

## Phase 4b: US3+US4 — Members Settings Frontend (P2)

**Goal**: Frontend members settings page with invite, role management, and member removal.
**Verify**: Admin invites member (dialog), changes role (dropdown), removes member (confirm). Non-admin sees read-only.

### Frontend

- [ ] T021 Create members settings route in `frontend/src/app/(workspace)/[workspaceSlug]/settings/members/page.tsx`
  - Import and render MembersSettingsPage
  - Source: FR-013

- [ ] T022 Create MembersSettingsPage component in `frontend/src/features/settings/pages/members-settings-page.tsx`
  - Display: member list (avatar, name, email, role badge, joined date), pending invitations section
  - Admin actions: invite button, role dropdown (admin/member/guest — no owner in dropdown), remove button
  - Non-admin: read-only view (action buttons hidden)
  - Source: FR-013, FR-014, FR-017 through FR-021, US3, US4

- [ ] T023 [P] Create MemberRow component in `frontend/src/features/settings/components/member-row.tsx`
  - Renders single member row: avatar, name, email, role badge
  - Admin view: role dropdown (Select), remove button (with confirm)
  - Owner row: shows "Transfer ownership" action instead of role dropdown
  - Non-admin view: role as text badge only
  - Source: US4

- [ ] T024 [P] Create InviteMemberDialog component in `frontend/src/features/settings/components/invite-member-dialog.tsx`
  - Dialog: email input, role select (admin/member/guest), submit button
  - Validation: email format, handles 409 (already member)
  - Source: FR-014, US3

- [ ] T025 [P] Create useWorkspaceInvitations hook in `frontend/src/features/settings/hooks/use-workspace-invitations.ts`
  - TanStack Query: GET /workspaces/{id}/invitations
  - Mutation: DELETE /workspaces/{id}/invitations/{id} (cancel)
  - Source: FR-016

### Tests

- [ ] T028 [P] Write unit tests for MembersSettingsPage in `frontend/src/__tests__/settings/members-settings-page.test.tsx`
  - Test: renders member list
  - Test: admin sees action buttons, non-admin does not
  - Test: invite dialog opens and submits
  - Test: owner row shows transfer action
  - Source: US3, US4

**Checkpoint**: Full invitation flow works end-to-end. Admin invites by email, existing users added immediately, pending invitations trackable. Auto-accept on signup verified. Quality gates: `pnpm lint && pnpm type-check && pnpm test`

---

## Phase 5: US5 — Workspace General Settings (P3)

**Goal**: Admins can edit workspace name/description/slug and delete workspace.
**Verify**: Rename workspace, change slug (URL updates), delete with confirmation.

### Frontend

- [ ] T029 Create WorkspaceGeneralPage component in `frontend/src/features/settings/pages/workspace-general-page.tsx`
  - Display: workspace name (editable), slug (editable with uniqueness check), description (editable)
  - Metadata: creation date, member count, project count (read-only)
  - Danger zone: delete workspace button
  - Non-admin: read-only mode
  - Source: FR-022 through FR-026, US5

- [ ] T030 [P] Create DeleteWorkspaceDialog component in `frontend/src/features/settings/components/delete-workspace-dialog.tsx`
  - Confirmation: type workspace name to confirm
  - Calls DELETE /workspaces/{id}, redirects to workspace list on success
  - Source: FR-024

- [ ] T031 [P] Create useWorkspaceSettings hook in `frontend/src/features/settings/hooks/use-workspace-settings.ts`
  - TanStack Query: GET /workspaces/{id} for current workspace data
  - Mutation: PATCH /workspaces/{id} for updates
  - Mutation: DELETE /workspaces/{id} for deletion
  - Optimistic update on name/description change
  - Source: FR-022, FR-023

- [ ] T032 Update settings route page in `frontend/src/app/(workspace)/[workspaceSlug]/settings/page.tsx`
  - Render WorkspaceGeneralPage as the default settings view
  - Source: RD-007

### Tests

- [ ] T033 Write unit tests for WorkspaceGeneralPage in `frontend/src/__tests__/settings/workspace-general-page.test.tsx`
  - Test: admin can edit name and save
  - Test: slug validation shows error on duplicate
  - Test: delete requires typing workspace name
  - Test: non-admin sees read-only view
  - Source: US5 acceptance scenarios

**Checkpoint**: Workspace settings page works. Admin can rename, change slug, and delete workspace. Non-admin sees read-only.

---

## Phase 6: US6 — Password Reset (P3)

**Goal**: Users can reset forgotten passwords via email link.
**Verify**: Request reset, receive email, click link, set new password, login with new password.

### Frontend

- [ ] T034 Create forgot password page in `frontend/src/app/(auth)/forgot-password/page.tsx`
  - Form: email input, submit button
  - Uses AuthStore.resetPassword() (already exists)
  - Shows same success message regardless of email existence (FR-029)
  - Link from login page: "Forgot password?"
  - Source: FR-027, FR-029, US6

- [ ] T035 Create reset password page in `frontend/src/app/(auth)/reset-password/page.tsx`
  - Supabase handles token verification from URL hash
  - Form: new password, confirm password
  - Uses `supabase.auth.updateUser({ password })` on submit
  - On success: redirect to login with success message
  - On expired link: show error with "Request new reset" link
  - Source: FR-028, FR-030, US6

- [ ] T036 Add "Forgot password?" link to login page in `frontend/src/app/(auth)/login/page.tsx`
  - Add link below password field pointing to `/auth/forgot-password`
  - Source: US6

### Tests

- [ ] T037 [P] Write unit tests for forgot password page in `frontend/src/__tests__/auth/forgot-password.test.tsx`
  - Test: submits email and shows success
  - Test: shows same message for non-existent email
  - Source: FR-029

- [ ] T038 [P] Write unit tests for reset password page in `frontend/src/__tests__/auth/reset-password.test.tsx`
  - Test: submits new password
  - Test: password mismatch shows error
  - Test: expired link shows error with retry link
  - Source: US6 acceptance scenarios

**Checkpoint**: Password reset flow works end-to-end. Email enumeration prevented.

---

## Phase Final: Polish

- [ ] T039 Run full quickstart validation (all 4 scenarios from plan.md)
- [ ] T040 [P] Verify test coverage >80% for new code: `uv run pytest --cov=. && pnpm test -- --coverage`
- [ ] T041 [P] Verify file size limits — all new files under 700 lines
- [ ] T042 [P] Verify RLS policies work via integration tests — cross-workspace invitation isolation
- [ ] T043 Run full quality gates: `uv run pyright && uv run ruff check && uv run pytest --cov=. && pnpm lint && pnpm type-check && pnpm test`
- [ ] T044 Export settings pages index in `frontend/src/features/settings/pages/index.ts` and `frontend/src/features/settings/components/index.ts`

**Checkpoint**: Feature complete. All quality gates pass. All quickstart scenarios verified. >80% coverage.

---

## Dependencies

### Phase Order

```
Phase 1 (Foundation) → Phase 2 (US1: Auth) → Phase 3 (US2: Profile) ──────────┐
                                              Phase 4a (Members Backend) ──┐   │
                                              Phase 4b (Members Frontend) ←┘ ←─┘ → Phase 5 (US5: Settings)
                                              Phase 6 (US6: Password) ← independent after Phase 2
                                              → Phase Final (Polish)
```

### Story Independence

- [x] US2 (Profile) and US3+US4 (Members Backend) can run in parallel after Phase 2 (different files, no shared deps)
- [x] Phase 4b (Members Frontend) depends on Phase 4a (backend endpoints must exist) but can run in parallel with Phase 3 (Profile)
- [x] US6 (Password Reset) can run in parallel with US2/US3 (only depends on Phase 2 auth fixes)
- [x] US5 (Settings) depends on Phase 4b (shares settings navigation and members page layout)

### Within Each Story

```
Tests (write alongside) → Models → Repositories → Services → Endpoints → Components
```

### Parallel Opportunities

| Phase | Parallel Group | Tasks |
|-------|---------------|-------|
| Phase 1 | Model + Schemas | T003, T004, T004a (after T001) |
| Phase 2 | Tests | T010, T011 |
| Phase 3 | N/A | Sequential (small phase) |
| Phase 4a | Backend tests | T026, T027 |
| Phase 4b | Frontend components | T023, T024, T025 |
| Phase 4b | Frontend tests | T028 |
| Phase 5 | Frontend components | T030, T031 |
| Phase 6 | Tests | T037, T038 |
| Cross-phase | Phase 3 ∥ Phase 4a ∥ Phase 6 | Independent after Phase 2 |

---

## Execution Strategy

### Selected: Option B — Incremental

```
Foundation → US1 (Auth) → Deploy → US2 + US3-backend + US6 parallel → Deploy → US3-frontend + US5 → Polish → Deploy
```

Deploy after Phase 2 to validate auth fixes in production. Then ship invitation backend, profile, and password reset in parallel. Members frontend and settings page next (depend on backend endpoints and settings navigation). Polish last.

---

## Validation Checklists

### Coverage Completeness

- [x] Every user story from spec.md has a task phase (6 stories → Phases 2-6)
- [x] Every entity from data-model.md has a creation task (T001 WorkspaceInvitation)
- [x] Every endpoint from contracts/ has an implementation task (T017, T018, T019 + existing)
- [x] Every quickstart scenario has a validation task (T039)
- [x] Setup and Polish phases included

### Task Quality

- [x] Task IDs sequential (T001-T044) with sub-IDs (T004a, T020a) for review-driven additions
- [x] Each task has exact file path
- [x] Each task starts with imperative verb
- [x] One responsibility per task
- [x] `[P]` markers only where tasks are truly independent
- [x] `[USn]` markers implied via phase grouping (each phase = one story)

### Dependency Integrity

- [x] No circular dependencies
- [x] Phase order enforced: Foundation → Auth → Stories → Polish
- [x] Within-story order: Models → Repos → Services → Endpoints → Components
- [x] Cross-story shared entities placed in Foundation phase (WorkspaceInvitation)
- [x] Each phase has a checkpoint statement

### Execution Readiness

- [x] Any developer can pick up any task and execute without questions
- [x] File paths match plan.md project structure exactly
- [x] Quality gate commands specified in Polish phase
- [x] Execution strategy selected with rationale (Incremental — deploy after auth fixes)
