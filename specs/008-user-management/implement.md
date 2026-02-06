# Implementation Guide: User Management

**Feature**: 008 — User Management
**Branch**: `008-user-management`
**Created**: 2026-02-03
**Source Artifacts**: `spec.md`, `plan.md`, `tasks.md`
**Author**: Tin Dang

---

## Context Loading Protocol

Before writing any code, load and internalize these artifacts in order:

1. **Read `specs/008-user-management/spec.md`**
   - 33 functional requirements (FR-001 through FR-033)
   - 6 user stories with 22 acceptance scenarios (Given/When/Then)
   - 8 edge cases
   - 5 key entities: User, Workspace, Membership, Invitation, AuthEvent
   - Priority levels: P1 (Auth), P2 (Profile + Members), P3 (Settings + Reset)

2. **Read `specs/008-user-management/plan.md`**
   - 7 research decisions (RD-001 through RD-007)
   - Requirements-to-Architecture mapping (33 FRs → components)
   - Story-to-Component matrix (6 stories → backend + frontend)
   - Data model: WorkspaceInvitation (new), WorkspaceMember (fix), User (extend)
   - API contracts: 3 new endpoints, 8 existing, 2 removed
   - Project structure with exact file paths

3. **Read `specs/008-user-management/tasks.md`**
   - 44 tasks (T001–T044) across 7 phases
   - Phase order: Foundation → Auth → Profile → Members Backend → Members Frontend → Settings → Password Reset → Polish
   - `[P]` markers for parallel-safe tasks
   - Checkpoint statements per phase

---

## Codebase Key Facts

These are verified facts about the existing codebase that affect implementation decisions.

### Backend

| Fact | Location | Impact |
|------|----------|--------|
| `WorkspaceRole` enum has `OWNER`, `ADMIN`, `MEMBER`, `GUEST` values | `models/workspace_member.py` | Role dropdown must use these exact values |
| `create_workspace` assigns `WorkspaceRole.ADMIN` (bug) | `routers/workspaces.py:~244` | T005 fixes to `WorkspaceRole.OWNER` |
| `POST /workspaces/{id}/members` returns 501 | `routers/workspaces.py:~446-497` | T017 replaces with real implementation |
| `POST /auth/callback` returns 501 | `routers/auth.py:66-93` | T006 removes (Supabase client handles) |
| `POST /auth/refresh` returns 501 | `routers/auth.py:96-120` | T006 removes (Supabase client handles) |
| `ensure_user_synced` creates User on first JWT auth | `dependencies.py:227-266` | T020 extends for auto-accept invitations |
| `WorkspaceMemberCreate.role` pattern uses `viewer` not `guest` | `schemas/workspace.py` | T004a fixes to match enum |
| `BaseRepository` has `delete()` with soft-delete pattern | `repositories/base.py` | Workspace deletion uses this |
| Services follow CQRS-lite: `Service.execute(Payload) → Result` | `application/services/` | New WorkspaceService follows same pattern |
| Repositories extend `BaseRepository[T]` with async SQLAlchemy | `repositories/base.py` | InvitationRepository follows same pattern |

### Frontend

| Fact | Location | Impact |
|------|----------|--------|
| `AuthStore` has `resetPassword()`, `updateProfile()`, `signInWithOAuth()` | `stores/AuthStore.ts` | Profile page and password reset use these directly |
| `supabase.ts` has `autoRefreshToken: true`, `detectSessionInUrl: true` | `lib/supabase.ts` | OAuth callback and token refresh are client-side |
| Callback page is a placeholder (2s timeout redirect) | `app/(auth)/callback/page.tsx` | T008 fixes with proper Supabase session detection |
| Login page has toggle between login/signup modes | `app/(auth)/login/page.tsx` | T036 adds "Forgot password?" link |
| `useWorkspaceMembers` hook exists | `features/issues/hooks/use-workspace-members.ts` | Members page reuses this hook |
| `WorkspaceStore` has `inviteMember()`, `removeMember()`, `updateMemberRole()` | `stores/WorkspaceStore.ts` | Members page uses these methods |
| Settings pages live in `features/settings/pages/` | `features/settings/pages/ai-settings-page.tsx` | New pages follow same pattern |
| Settings routes: `/settings` (general), `/settings/integrations` | `app/(workspace)/[workspaceSlug]/settings/` | Add `/settings/members`, `/settings/profile` |
| `apiClient` adds JWT via interceptor, handles 401 → signOut | `services/api/client.ts` | All API calls auto-authenticated |
| `apiClient` uses RFC 7807 Problem Details for errors | `services/api/client.ts` | Error handling follows same pattern |

---

## Task Execution Protocol

For each task T{NNN}, execute these steps:

### Step 1: Pre-Implementation Verification

- Confirm all blocking tasks (earlier T{NNN}s without `[P]`) are complete
- Confirm the target file path from `tasks.md` matches `plan.md` project structure
- Confirm the entity/service/endpoint being built is defined in `plan.md`
- If ANY mismatch exists between spec, plan, and tasks — STOP and flag it

### Step 2: Write Tests First (if task is in Tests section)

- Derive test cases directly from `spec.md` acceptance scenarios (Given/When/Then)
- Map each test to the FR-NNN it validates
- Include edge cases from `spec.md` Edge Cases section
- Include error cases from `plan.md` API contract error tables
- Verify tests FAIL before implementation exists (TDD red phase)

### Step 3: Implement the Component

- Follow the exact file path specified in T{NNN}
- Match the data model exactly (field names, types, constraints from `plan.md` Data Model)
- Match API contracts exactly (routes, schemas, status codes from `plan.md` API Contracts)
- Apply patterns from `plan.md` Research Decisions
- Respect constraints: 700-line file limit, >80% test coverage, no TODOs/placeholders

### Step 4: Validate Against Spec

- [ ] Every FR-NNN mapped to this component (from `plan.md` mapping table) is satisfied
- [ ] Every acceptance scenario (Given/When/Then) from `spec.md` passes
- [ ] Every error code from API contracts is handled
- [ ] Entity fields match data model exactly (names, types, constraints, indexes)
- [ ] Performance targets met: <200ms P95 API response, <2s profile save

### Step 5: Run Quality Gates

**Backend**:
```bash
uv run pyright && uv run ruff check && uv run pytest --cov=.
```

**Frontend**:
```bash
pnpm lint && pnpm type-check && pnpm test
```

### Step 6: Checkpoint Validation

- If this task completes a phase, verify the phase Checkpoint statement from `tasks.md`
- If the checkpoint references quickstart scenarios, run them
- Mark T{NNN} as complete only after all gates pass

---

## Phase Execution Details

### Phase 1: Foundation (T001–T004a)

**Goal**: WorkspaceInvitation model, migration, repository, schemas ready.

**Dependency Graph**:
```
T001 (Model) ──────────┐
T002 (Migration) ←──────┤
                        ├──> T003 [P] (Repository)
                        ├──> T004 [P] (Schemas)
                        └──> T004a [P] (Fix role pattern)
```

**T001 — WorkspaceInvitation Model**

File: `backend/src/pilot_space/infrastructure/database/models/workspace_invitation.py`

Pattern: Follow existing model conventions from `models/workspace_member.py`.

Requirements:
- Fields: id (UUID PK), workspace_id (FK), email (VARCHAR 255), role (ENUM), invited_by (FK), status (ENUM: pending/accepted/expired/cancelled), expires_at, accepted_at, created_at, updated_at, is_deleted
- Indexes: (workspace_id, email) UNIQUE WHERE status='pending', (email, status), (workspace_id, status), (expires_at) WHERE status='pending'
- Relationships: Workspace (N:1), User/invited_by (N:1)
- Source: plan.md Data Model, FR-016

Register model in `models/__init__.py`.

**T002 — Alembic Migration**

File: `backend/alembic/versions/{auto}_add_workspace_invitations.py`

Requirements:
- Create `workspace_invitations` table with all fields and indexes
- Add RLS policy: `workspace_invitation_isolation` — admin-only access scoped by workspace membership
- Source: FR-031

```sql
CREATE POLICY workspace_invitation_isolation ON workspace_invitations
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    ));
```

**T003 — InvitationRepository** `[P]`

File: `backend/src/pilot_space/infrastructure/database/repositories/invitation_repository.py`

Pattern: Extend `BaseRepository[WorkspaceInvitation]` following `workspace_repository.py`.

Methods:
- `create(invitation)` — inherited from BaseRepository
- `get_by_id(id)` — inherited
- `get_by_workspace(workspace_id, status_filter?)` — list invitations
- `get_pending_by_email(email)` — find all pending invitations for an email
- `cancel(invitation_id)` — set status to 'cancelled'
- `mark_accepted(invitation_id)` — set status to 'accepted', accepted_at = now
- `mark_expired(invitation_id)` — set status to 'expired'
- `exists_pending(workspace_id, email)` — check for duplicate

Register in `repositories/__init__.py`.

**T004 — Invitation Schemas** `[P]`

File: `backend/src/pilot_space/api/v1/schemas/workspace.py` (edit existing)

Add:
- `InvitationResponse`: id, email, role, status, invited_by, expires_at, created_at
- `InvitationCreateRequest`: email (valid email, 1-255 chars), role (admin|member|guest)
- `InvitationCreateResponse`: Union type — either WorkspaceMemberResponse (immediate add) or InvitationResponse (pending)

Source: plan.md API Contracts

**T004a — Fix Role Pattern** `[P]`

File: `backend/src/pilot_space/api/v1/schemas/workspace.py` (edit existing)

Change:
- `WorkspaceMemberCreate.role` pattern: `^(admin|member|viewer)$` → `^(admin|member|guest)$`
- `WorkspaceMemberUpdate.role` pattern: `^(admin|member|viewer)$` → `^(admin|member|guest)$`
- Update docstrings from "viewer" to "guest"

**Phase 1 Checkpoint**: Invitation model and repository ready. Schema role validation matches enum. Migration runs clean. `uv run pyright` passes.

---

### Phase 2: US1 — Reliable Authentication (T005–T011)

**Goal**: Fix auth callback, remove dead endpoints, fix OWNER role.

**Dependency Graph**:
```
Backend (sequential):
T005 (Fix OWNER role) ──> T006 (Remove 501s) ──> T007 [P] (Remove schemas)

Frontend (parallel with backend):
T008 (Fix callback) ──┐
T009 (Session expiry) ─┤
                       └──> Tests
Tests [P]:
T010 (OWNER test) ──┐
T011 (Auth router) ──┘
```

**T005 — Fix OWNER Role**

File: `backend/src/pilot_space/api/v1/routers/workspaces.py`

Change at line ~244 in `create_workspace`:
```python
# Before:
WorkspaceRole.ADMIN
# After:
WorkspaceRole.OWNER
```

Source: FR-007, RD-006

**T006 — Remove 501 Endpoints**

File: `backend/src/pilot_space/api/v1/routers/auth.py`

Remove:
- `auth_callback` function (POST /callback, lines 66-93)
- `refresh_token` function (POST /refresh, lines 96-120)

Keep: `login`, `get_current_user_profile`, `update_current_user_profile`, `logout`

Source: RD-002

**T007 — Remove Unused Schemas** `[P]`

File: `backend/src/pilot_space/api/v1/schemas/auth.py`

Remove: `AuthCallbackRequest`, `RefreshTokenRequest` classes and `__all__` exports.

Source: RD-002

**T008 — Fix OAuth Callback Page**

File: `frontend/src/app/(auth)/callback/page.tsx`

Current: Placeholder with 2-second setTimeout redirect.

Replace with:
```typescript
// 1. Check for session via supabase.auth.getSession()
// 2. If session exists → redirect to '/'
// 3. If no session → check URL hash for error
// 4. On error → redirect to '/login' with error query param
// 5. Loading state: show spinner while detecting session
```

Use `supabase.auth.onAuthStateChange` to detect when Supabase processes the OAuth callback URL hash (enabled by `detectSessionInUrl: true`).

Source: FR-002, RD-001

**T009 — Session Expiry Redirect**

File: `frontend/src/stores/AuthStore.ts`

In `onAuthStateChange` handler:
- When event is `TOKEN_REFRESHED` with null session → redirect to `/login`
- Ensure `SIGNED_OUT` event clears all state and redirects
- Handle `INITIAL_SESSION` for page load recovery

Source: FR-004

**T010 — OWNER Role Tests** `[P]`

File: `backend/tests/unit/test_workspace_creation.py`

Tests:
- `test_workspace_creation_assigns_owner_role` — FR-007
- `test_workspace_has_exactly_one_owner_after_creation` — FR-007

**T011 — Auth Router Tests** `[P]`

File: `backend/tests/unit/test_auth_router.py`

Tests:
- `test_callback_endpoint_removed` — 404 on POST /callback
- `test_refresh_endpoint_removed` — 404 on POST /refresh
- `test_me_endpoint_exists` — 200 on GET /me
- `test_logout_endpoint_exists` — 200 on POST /logout

**Phase 2 Checkpoint**: Auth flow works end-to-end. OAuth callback properly detects session. Dead endpoints removed. OWNER role assigned on workspace creation. Quality gates pass.

---

### Phase 3: US2 — User Profile Management (T012–T015)

**Goal**: Profile settings page for name and avatar editing.

**Dependency Graph**:
```
T012 (Route) ──> T013 (Page component) ──> T014 [P] (Settings nav)
                                           T015 (Tests)
```

**T013 — ProfileSettingsPage**

File: `frontend/src/features/settings/pages/profile-settings-page.tsx`

Pattern: Follow `ai-settings-page.tsx` structure.

Requirements:
- Display email (read-only disabled input) — FR-011
- Display name (editable text input) — FR-009
- Avatar (display + upload button) — FR-010
- Save button calls `AuthStore.updateProfile()` — FR-012
- Error state: toast on failure, preserve unsaved form changes — US2 #4
- WCAG 2.2 AA: keyboard nav, ARIA labels, focus management — SC-008

Data source: `AuthStore.user` for read, `AuthStore.updateProfile()` for write.

**T014 — Settings Navigation** `[P]`

File: `frontend/src/app/(workspace)/[workspaceSlug]/settings/page.tsx`

Add sidebar links: General, Members, Profile, AI Providers (existing), Integrations (existing). Highlight current route. Follow existing layout patterns.

Source: RD-007

**Phase 3 Checkpoint**: Profile page works. Users can view and update display name. Quality gates pass.

---

### Phase 4a: US3 — Member Invitation Backend (T016–T020a, T026–T027)

**Goal**: Backend invitation service, endpoints, auto-accept on signup.

**Dependency Graph**:
```
T016 (WorkspaceService) ──> T017 (POST /members)
                            T018 (GET /invitations)
                            T019 (DELETE /invitations/{id})
                            T020 (Auto-accept in ensure_user_synced)
                            T020a (Ownership transfer guard)
                            T026 [P] (Service tests)
                            T027 [P] (Integration tests)
```

**T016 — WorkspaceService**

File: `backend/src/pilot_space/application/services/workspace.py`

Pattern: CQRS-lite service per DD-064.

Method `invite_member(workspace_id, email, role, invited_by)`:
1. Check if email belongs to existing user via `UserRepository.get_by_email()`
2. If exists: check not already a member → `WorkspaceRepository.add_member()` → return WorkspaceMemberResponse
3. If not exists: check no duplicate pending invitation → `InvitationRepository.create()` → return InvitationResponse
4. Conflicts: already-member → 409, duplicate-pending → 409

Source: FR-014, FR-015, FR-016

**T017 — POST /workspaces/{id}/members**

File: `backend/src/pilot_space/api/v1/routers/workspaces.py`

Replace the 501 placeholder (lines ~446-497) with:
- Parse `InvitationCreateRequest` body
- Admin-only guard (check role in workspace_members)
- Call `WorkspaceService.invite_member()`
- Return 201 with appropriate response type

Errors: 400 (validation), 403 (not admin), 404 (workspace not found), 409 (already member or pending)

Source: plan.md API Contract Endpoint 1

**T018 — GET /workspaces/{id}/invitations**

File: `backend/src/pilot_space/api/v1/routers/workspaces.py`

New endpoint:
- Admin-only guard
- `InvitationRepository.get_by_workspace(workspace_id)`
- Return list of `InvitationResponse`

Source: plan.md API Contract Endpoint 2

**T019 — DELETE /workspaces/{id}/invitations/{invitation_id}**

File: `backend/src/pilot_space/api/v1/routers/workspaces.py`

New endpoint:
- Admin-only guard
- `InvitationRepository.cancel(invitation_id)`
- Return 204 No Content
- 404 if not found or already accepted

Source: plan.md API Contract Endpoint 3

**T020 — Auto-Accept Invitations on Signup**

File: `backend/src/pilot_space/dependencies.py`

Extend `ensure_user_synced` (lines 227-266):
```python
# After user creation/sync:
invitation_repo = InvitationRepository(session=session)
pending = await invitation_repo.get_pending_by_email(email)
for invitation in pending:
    # Add user as workspace member with intended role
    await workspace_repo.add_member(
        workspace_id=invitation.workspace_id,
        user_id=current_user.user_id,
        role=invitation.role,
    )
    await invitation_repo.mark_accepted(invitation.id)
await session.commit()
```

Source: FR-016, RD-004

**T020a — Ownership Transfer Guard**

File: `backend/src/pilot_space/api/v1/routers/workspaces.py`

In `update_workspace_member` endpoint:
- If new role is `OWNER`: validate current user is OWNER, demote current OWNER to ADMIN
- Prevent setting OWNER via invitation (only via explicit transfer)
- Ensure workspace always has exactly one OWNER

Source: FR-017, US4 acceptance scenario #6

**Phase 4a Checkpoint**: Invitation backend complete. All 3 endpoints implemented. Auto-accept on signup. Ownership transfer guarded. Quality gates pass.

---

### Phase 4b: US3+US4 — Members Settings Frontend (T021–T025, T028)

**Goal**: Members page with invite dialog, role management, removal.

**Dependency Graph**:
```
T021 (Route) ──> T022 (MembersSettingsPage)
                 T023 [P] (MemberRow)
                 T024 [P] (InviteMemberDialog)
                 T025 [P] (useWorkspaceInvitations hook)
                 T028 [P] (Tests)
```

**T022 — MembersSettingsPage**

File: `frontend/src/features/settings/pages/members-settings-page.tsx`

Pattern: Follow `ai-settings-page.tsx` layout. Use `useWorkspaceMembers` (existing) + `useWorkspaceInvitations` (new T025).

Sections:
1. **Active Members** — list of `MemberRow` components sorted by role hierarchy then join date
2. **Pending Invitations** — list with cancel buttons (admin only)
3. **Invite Button** — opens `InviteMemberDialog` (admin only)

Role-based rendering:
- Admin: sees role dropdown (admin/member/guest — no owner), remove button, invite button
- Owner: sees "Transfer ownership" action on their own row
- Non-admin: read-only view, action buttons hidden

Source: FR-013, FR-014, FR-017 through FR-021, US3, US4

**T023 — MemberRow** `[P]`

File: `frontend/src/features/settings/components/member-row.tsx`

Props: `member: WorkspaceMember`, `currentUserRole: string`, `onRoleChange`, `onRemove`, `onTransferOwnership`

Renders: avatar, name, email, role badge, joined date. Admin view: role `<Select>`, remove button. Non-admin: role as text badge.

**T024 — InviteMemberDialog** `[P]`

File: `frontend/src/features/settings/components/invite-member-dialog.tsx`

Dialog with: email input (validated), role select (admin/member/guest), submit button. Handle 409 conflict error (already member).

Use `WorkspaceStore.inviteMember()` for the API call.

**T025 — useWorkspaceInvitations Hook** `[P]`

File: `frontend/src/features/settings/hooks/use-workspace-invitations.ts`

Pattern: Follow `use-workspace-members.ts` TanStack Query pattern.

```typescript
// Query: GET /workspaces/{id}/invitations
// Mutation: DELETE /workspaces/{id}/invitations/{id}
// queryKey: ['workspaces', workspaceId, 'invitations']
// staleTime: 60_000
```

**Phase 4b Checkpoint**: Full invitation flow works end-to-end. Admin invites by email. Existing users added immediately. Pending invitations trackable. Quality gates pass.

---

### Phase 5: US5 — Workspace General Settings (T029–T033)

**Goal**: General settings page with workspace editing and deletion.

**Dependency Graph**:
```
T029 (WorkspaceGeneralPage) ──> T030 [P] (DeleteWorkspaceDialog)
                                T031 [P] (useWorkspaceSettings hook)
                                T032 (Update settings route)
                                T033 (Tests)
```

**T029 — WorkspaceGeneralPage**

File: `frontend/src/features/settings/pages/workspace-general-page.tsx`

Sections:
1. **General Info** — name (editable), slug (editable with uniqueness validation), description (editable)
2. **Metadata** — creation date, member count, project count (read-only)
3. **Danger Zone** — delete workspace button (opens `DeleteWorkspaceDialog`)
4. Non-admin: all fields read-only, no danger zone

Use `useWorkspaceSettings` hook (T031) for data + mutations.

Source: FR-022 through FR-026, US5

**T030 — DeleteWorkspaceDialog** `[P]`

File: `frontend/src/features/settings/components/delete-workspace-dialog.tsx`

Confirmation pattern: user types workspace name to confirm. Calls `DELETE /workspaces/{id}`. On success: redirect to workspace list.

Source: FR-024

**Phase 5 Checkpoint**: Workspace settings page works. Admin can rename, change slug, delete. Non-admin sees read-only.

---

### Phase 6: US6 — Password Reset (T034–T038)

**Goal**: Forgot/reset password flow via Supabase.

**Dependency Graph**:
```
T034 (Forgot password page) ──┐
T035 (Reset password page) ───┤
T036 (Login page link) ───────┤
                               └──> T037 [P], T038 [P] (Tests)
```

**T034 — Forgot Password Page**

File: `frontend/src/app/(auth)/forgot-password/page.tsx`

Form: email input, submit button. Uses `AuthStore.resetPassword(email)` (already exists). Shows same success message regardless of email existence (FR-029 — no enumeration).

**T035 — Reset Password Page**

File: `frontend/src/app/(auth)/reset-password/page.tsx`

Supabase handles token verification from URL hash. Form: new password, confirm password. Uses `supabase.auth.updateUser({ password })`. On success: redirect to login. On expired: show error with "Request new reset" link.

**T036 — Login Page Link**

File: `frontend/src/app/(auth)/login/page.tsx`

Add "Forgot password?" link below password field, pointing to `/auth/forgot-password`.

**Phase 6 Checkpoint**: Password reset flow works end-to-end. Email enumeration prevented.

---

### Phase Final: Polish (T039–T044)

```
T039  Run full quickstart validation (4 scenarios from plan.md)
T040  Verify test coverage >80%: uv run pytest --cov=. && pnpm test -- --coverage
T041  Verify file size limits — all new files under 700 lines
T042  Verify RLS policies via integration tests — cross-workspace isolation
T043  Full quality gates: uv run pyright && uv run ruff check && uv run pytest --cov=. && pnpm lint && pnpm type-check && pnpm test
T044  Export settings pages/components index files
```

---

## Traceability Requirements

Every implementation decision must be traceable:

| Code Element | Must Reference |
|-------------|---------------|
| Model/Entity fields | `plan.md` Data Model section |
| API endpoint route + method | `plan.md` API Contracts section |
| Service method | `plan.md` Requirements-to-Architecture mapping |
| Test case | `spec.md` acceptance scenario (Given/When/Then) |
| Error handling | `plan.md` API Contract error tables |
| Architecture pattern | `plan.md` Research Decisions (RD-001 through RD-007) |

If you cannot trace a piece of code to an artifact, it should not exist.
If an artifact requires something not yet implemented, flag it as a gap.

---

## Error Recovery Protocol

| Problem | Action |
|---------|--------|
| **Spec-Plan mismatch** — Plan says X, spec says Y | STOP. Flag the conflict with both artifact locations. Do NOT guess. |
| **Missing detail** — Task references entity not in plan | Check if it's in another task's scope. If truly missing, flag as gap. |
| **Test failure after implementation** — Tests from spec don't pass | Fix implementation to match spec. Never modify tests to match broken code. |
| **Quality gate failure** — Lint/type/test failure | Fix in current task. Do NOT defer to a later task. |
| **File size approaching 700 lines** | Extract to a new module following `plan.md` project structure patterns. |

---

## Parallel Execution Map

```
Phase 1 ═══════════════════════════════════════════════
  T001 → T002 → T003 [P] + T004 [P] + T004a [P]

Phase 2 ═══════════════════════════════════════════════
  Backend: T005 → T006 → T007 [P]
  Frontend: T008 + T009 (parallel with backend)
  Tests: T010 [P] + T011 [P]

                    ┌─── Phase 3 (Profile) ───────────
                    │    T012 → T013 → T014 [P]
                    │    T015 (tests)
                    │
Phase 2 complete ───┼─── Phase 4a (Members BE) ──────
                    │    T016 → T017 → T018 → T019
                    │    T020, T020a
                    │    T026 [P] + T027 [P]
                    │
                    └─── Phase 6 (Password Reset) ───
                         T034 + T035 + T036
                         T037 [P] + T038 [P]

Phase 4a complete ──┬─── Phase 4b (Members FE) ──────
                    │    T021 → T022
                    │    T023 [P] + T024 [P] + T025 [P]
                    │    T028 [P]
                    │
Phase 4b complete ──┴─── Phase 5 (Settings) ─────────
                         T029 → T030 [P] + T031 [P]
                         T032, T033

All phases ─────────── Phase Final (Polish) ──────────
                         T039 → T040 → T041 → T042 → T043 → T044
```

**Critical Path**: T001 → T002 → T005 → T006 → T016 → T017 → T022 → T029 → T039 → T043

---

## Output Format Per Task

For each T{NNN} completed, produce:

```
## T{NNN}: {task description}

### Files Modified/Created
- {exact/path/file.ext} — {what was done}

### Requirements Satisfied
- FR-{NNN}: {brief description} ✓

### Tests
- {test_name}: {what it validates} — PASS/FAIL

### Quality Gates
- Lint: PASS/FAIL
- Type check: PASS/FAIL
- Tests: PASS/FAIL ({N}/{N} passing)
- File size: {N} lines (limit: 700)

### Next Task
- T{NNN+1}: {description} — ready/blocked by T{NNN}
```

---

## Self-Evaluation Framework

After completing each task, rate confidence (0-1):

1. **Spec Fidelity**: Does implementation match `spec.md` requirements exactly?
2. **Plan Compliance**: Does code follow `plan.md` architecture and patterns?
3. **Contract Accuracy**: Do endpoints match API contract definitions exactly?
4. **Test Coverage**: Are all acceptance scenarios covered?
5. **Quality Gates**: Do all gates pass clean?
6. **Traceability**: Can every code element trace to an artifact?
7. **Edge Cases**: Are edge/error cases from spec/contracts handled?
8. **Performance**: Does implementation meet performance goals from plan.md?
9. **Maintainability**: Is code clean, well-structured, and documented?
10. **Constitution Adherence**: Does code respect all constitution rules?
11. **Integration Readiness**: Is code ready to integrate with other components?

If any score < 0.9, refine before marking the task complete.

IMPORTANT: You can update tasks.md to reflect changes in task order or parallelization as needed. Then implement missing tasks per this guide.
