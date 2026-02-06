# Implementation Plan: User Management

**Feature**: User Management
**Branch**: `008-user-management`
**Created**: 2026-02-03
**Spec**: `specs/008-user-management/spec.md`
**Author**: Tin Dang

---

## Summary

User management feature completing auth flows, profile editing, member invitation/role management, workspace settings, and password reset. The technical approach delegates authentication to the Supabase client SDK (already configured), fixes backend gaps (OWNER role, invitation endpoint), adds an Invitation model, and builds 4 new frontend settings pages using existing MobX + TanStack Query patterns.

---

## Technical Context

| Attribute | Value |
|-----------|-------|
| **Language/Version** | Python 3.12+, TypeScript 5.3+ |
| **Primary Dependencies** | FastAPI 0.110+, Next.js 14+, SQLAlchemy 2.0 async, Supabase JS SDK |
| **Storage** | PostgreSQL 16+ with RLS |
| **Testing** | pytest + pytest-asyncio (backend), Vitest (frontend) |
| **Target Platform** | Web (browser + Linux server) |
| **Project Type** | Web (frontend + backend) |
| **Performance Goals** | <200ms P95 API response for member CRUD, <2s profile save |
| **Constraints** | RLS multi-tenant isolation, 700-line file limit, >80% test coverage |
| **Scale/Scope** | 5-100 members per workspace |

---

## Constitution Gate Check

### Technology Standards Gate

- [x] Language/Framework matches constitution mandates (FastAPI, Next.js, SQLAlchemy)
- [x] Database choice aligns with constitution constraints (PostgreSQL 16+ with RLS)
- [x] Auth approach follows constitution requirements (Supabase Auth + RLS per DD-061)
- [x] Architecture patterns match (CQRS-lite, Repository, Clean Architecture per DD-064)

### Simplicity Gate

- [x] Using minimum number of projects/services (no new services — extends existing backend/frontend)
- [x] No future-proofing or speculative features (no SCIM, no LDAP, no SSO beyond OAuth)
- [x] No premature abstractions (invitation is a simple model, not an event-sourced workflow)

### Quality Gate

- [x] Test strategy defined with coverage target (>80%)
- [x] Type checking enforced (pyright backend, TypeScript strict frontend)
- [x] File size limits respected (700 lines max)
- [x] Linting configured (ruff backend, eslint frontend)

---

## Research Decisions

| Question | Options Evaluated | Decision | Rationale |
|----------|-------------------|----------|-----------|
| **RD-001**: Auth delegation model — should OAuth callback and token refresh be server-side or client-side? | A) Server-side (backend POST /auth/callback exchanges code for tokens), B) Client-side Supabase SDK (frontend handles all auth, backend only validates JWT) | **B) Client-side Supabase SDK** | Already implemented: `supabase.ts` has `autoRefreshToken: true`, `detectSessionInUrl: true`. AuthStore uses `supabase.auth.signInWithOAuth()`, `supabase.auth.refreshSession()`. Backend 501 endpoints are unnecessary. Aligns with DD-061. |
| **RD-002**: Backend 501 auth endpoints — remove or keep? | A) Remove dead endpoints, B) Keep as documentation, C) Implement server-side as alternative | **A) Remove dead endpoints** | Dead code violates "no placeholders" rule. OAuth callback, token refresh, and password reset are fully handled by Supabase client SDK. Backend `/auth/me` (GET/PATCH) and `/auth/logout` remain. |
| **RD-003**: Invitation model — new entity or extend WorkspaceMember with status? | A) New `WorkspaceInvitation` entity, B) Add `status` column to `WorkspaceMember` | **A) New WorkspaceInvitation entity** | Invitations have different lifecycle (expiry, cancellation) and don't require a user_id (invited email may not have an account yet). Mixing concerns in WorkspaceMember adds complexity. FR-016. |
| **RD-004**: Invitation acceptance — automatic on signup or manual accept? | A) Auto-accept pending invitations on signup, B) Require manual accept via UI | **A) Auto-accept on signup** | Simplest flow: user signs up → `ensure_user_synced` checks for pending invitations → auto-adds to workspace. No extra UI needed. FR-016. |
| **RD-005**: Password reset — backend endpoint or client-side Supabase? | A) Backend endpoint, B) Client-side `supabase.auth.resetPasswordForEmail()` | **B) Client-side Supabase** | AuthStore already has `resetPassword()` method using Supabase SDK. Only need frontend UI (forgot password link + reset page). FR-027 through FR-030. |
| **RD-006**: Owner role fix — rename ADMIN to OWNER on workspace create, or add separate migration? | A) Fix workspace creation to use OWNER role, B) Migrate existing ADMIN entries to OWNER | **A) Fix workspace creation** | The `WorkspaceRole.OWNER` enum value already exists in the model. Only the `create_workspace` router incorrectly uses `WorkspaceRole.ADMIN`. Simple fix. FR-007. |
| **RD-007**: Frontend settings layout — tabs or separate pages? | A) Single settings page with tab navigation, B) Separate `/settings/*` routes | **B) Separate routes** | Matches existing pattern (`/settings`, `/settings/integrations` already exist). Keeps each page under 700 lines. Pages: `/settings` (general), `/settings/members`, `/settings/profile`. |

---

## Requirements-to-Architecture Mapping

| FR | Requirement | Technical Approach | Components |
|----|------------|-------------------|------------|
| FR-001 | Email/password auth | Supabase client SDK `signInWithPassword()` (exists in AuthStore) | `frontend/src/stores/AuthStore.ts`, `frontend/src/app/(auth)/login/page.tsx` |
| FR-002 | OAuth auth (GitHub) | Supabase client SDK `signInWithOAuth()` (exists in AuthStore) | `AuthStore`, callback page |
| FR-003 | Auto refresh tokens | Supabase SDK `autoRefreshToken: true` (exists in supabase.ts) | `frontend/src/lib/supabase.ts` |
| FR-004 | Redirect on expired session | AuthStore `onAuthStateChange` SIGNED_OUT event → redirect | `AuthStore`, auth layout |
| FR-005 | Logout | Supabase `signOut()` (exists) + backend no-op (exists) | `AuthStore`, `/auth/logout` |
| FR-006 | Auto-create user on first auth | `ensure_user_synced` dependency (exists in dependencies.py) | `backend/.../dependencies.py` |
| FR-007 | Assign OWNER role on workspace create | Fix `create_workspace` to use `WorkspaceRole.OWNER` | `backend/.../routers/workspaces.py` |
| FR-008 | View profile | New profile settings page reading from AuthStore + backend `/auth/me` | `frontend/.../settings/pages/profile-settings-page.tsx` |
| FR-009 | Update display name | AuthStore `updateProfile()` (exists) + backend `PATCH /auth/me` (exists) | `AuthStore`, `frontend/.../settings/pages/profile-settings-page.tsx` |
| FR-010 | Update avatar | AuthStore `updateProfile()` + Supabase Storage upload | `AuthStore`, profile page |
| FR-011 | Email read-only | Frontend renders email field as disabled | Profile page |
| FR-012 | Persist profile within 2s | Existing `PATCH /auth/me` + Supabase `updateUser()` | Backend auth router, AuthStore |
| FR-013 | View member list | Existing `GET /workspaces/{id}/members` + new Members page | `frontend/.../settings/pages/members-settings-page.tsx` |
| FR-014 | Invite by email | Implement `POST /workspaces/{id}/members` (currently 501) | `backend/.../routers/workspaces.py`, invitation service |
| FR-015 | Add existing users immediately | Invitation service checks UserRepository, adds via WorkspaceRepository | `backend/.../services/workspace.py` |
| FR-016 | Record pending invitations | New WorkspaceInvitation model + repository | `backend/.../models/workspace_invitation.py`, `backend/.../repositories/invitation_repository.py` |
| FR-017 | Change member role | Existing `PATCH /workspaces/{id}/members/{uid}` (works). Ownership transfer: if new role is OWNER, guard validates current user is OWNER, demotes previous OWNER to ADMIN. Role dropdown excludes OWNER — transfer is explicit. | Members page, existing backend endpoint |
| FR-018 | Remove members | Existing `DELETE /workspaces/{id}/members/{uid}` (works) | Members page, existing backend endpoint |
| FR-019 | Prevent removing last admin | Existing check in `remove_workspace_member` (works) | Existing backend logic |
| FR-020 | Non-admin read-only view | Frontend conditionally renders action buttons based on role | Members page |
| FR-021 | Self-removal | Existing endpoint supports self-removal (checks `is_self`) | Members page |
| FR-022 | Update workspace name/desc | Existing `PATCH /workspaces/{id}` (works) | `frontend/.../settings/pages/workspace-general-page.tsx` |
| FR-023 | Update workspace slug | Existing `PATCH /workspaces/{id}` + `slug_exists` validation | General settings page, existing backend |
| FR-024 | Delete workspace with confirmation | Existing `DELETE /workspaces/{id}` + new confirmation UI | General settings page |
| FR-025 | Soft-delete | Existing `BaseRepository.delete()` (soft-delete pattern) | Existing backend |
| FR-026 | Non-admin read-only settings | Frontend conditionally renders edit controls based on role | General settings page |
| FR-027 | Request password reset | AuthStore `resetPassword()` (exists) + new UI | `frontend/.../app/(auth)/forgot-password/page.tsx` |
| FR-028 | Reset link 1h expiry | Supabase Auth handles expiry natively | Supabase config |
| FR-029 | No email enumeration | Supabase returns same response regardless of email existence | Supabase default behavior |
| FR-030 | Set new password via link | Supabase `updateUser()` on reset callback page | `frontend/.../app/(auth)/reset-password/page.tsx` |
| FR-031 | Workspace isolation | RLS policies on workspace_members + workspace_invitations | Alembic migration |
| FR-032 | Role-based permissions | Frontend role checks + backend admin-only guards (existing) | Workspace router, frontend pages |
| FR-033 | Log auth events | Supabase Auth audit log (built-in) + application-level logging (existing) | Backend logger, Supabase |

---

## Story-to-Component Matrix

| User Story | Backend Components | Frontend Components | Data Entities |
|------------|-------------------|--------------------|--------------  |
| US1: Reliable Auth | Remove 501 endpoints, fix OWNER role in workspace creation | Fix callback page (Supabase `detectSessionInUrl`), add auth redirect on session expiry | User (exists) |
| US2: Profile Mgmt | `PATCH /auth/me` (exists), `PATCH /auth/me` avatar (exists) | New `profile-settings-page.tsx`, extend AuthStore | User (exists) |
| US3: Member Invitation | New invitation service, implement `POST /members`, new InvitationRepository, auto-accept in `ensure_user_synced` | New `members-settings-page.tsx`, new `useWorkspaceInvitations` hook | WorkspaceInvitation (new) |
| US4: Role Management | Existing endpoints (PATCH/DELETE members) | Members page role dropdown, remove button, role-based UI guards | WorkspaceMember (exists) |
| US5: Workspace Settings | Existing endpoints (PATCH/DELETE workspace) | New `workspace-general-page.tsx`, delete confirmation dialog | Workspace (exists) |
| US6: Password Reset | None (Supabase handles) | New `forgot-password/page.tsx`, new `reset-password/page.tsx` | None |

---

## Data Model

### WorkspaceInvitation (NEW)

**Purpose**: Tracks pending invitations for users who may not yet have an account.
**Source**: FR-016, US3

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK, auto-generated | |
| workspace_id | UUID | FK(workspaces.id), NOT NULL | Workspace being joined |
| email | VARCHAR(255) | NOT NULL | Invited email address |
| role | ENUM(workspace_role) | NOT NULL, default 'member' | Intended role upon acceptance |
| invited_by | UUID | FK(users.id), NOT NULL | Admin who sent invite |
| status | ENUM(pending/accepted/expired/cancelled) | NOT NULL, default 'pending' | Invitation state |
| expires_at | TIMESTAMP | NOT NULL | Default: created_at + 7 days |
| accepted_at | TIMESTAMP | NULL | When invitation was accepted |
| created_at | TIMESTAMP | NOT NULL, default NOW | |
| updated_at | TIMESTAMP | NOT NULL, auto-update | |
| is_deleted | BOOLEAN | NOT NULL, default false | Soft delete |

**Relationships**:
- Belongs to Workspace (N:1)
- Belongs to User (invited_by, N:1)

**Indexes**:
- (workspace_id, email) UNIQUE WHERE status = 'pending' — prevent duplicate pending invites
- (email, status) — lookup pending invitations for a user on signup
- (workspace_id, status) — list invitations per workspace
- (expires_at) WHERE status = 'pending' — cleanup expired invitations

**RLS Policy**:
```sql
CREATE POLICY workspace_invitation_isolation ON workspace_invitations
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid() AND role IN ('owner', 'admin')
    ));
```

### Existing Entities (Modifications)

**WorkspaceMember**: Fix workspace creation to assign `OWNER` role instead of `ADMIN`. Fix `WorkspaceMemberCreate` and `WorkspaceMemberUpdate` schema role patterns from `^(admin|member|viewer)$` to `^(admin|member|guest)$` to match `WorkspaceRole` enum.

**User**: No schema changes. Extend `ensure_user_synced` to auto-accept pending invitations.

---

## API Contracts

### Endpoint 1: POST /api/v1/workspaces/{workspace_id}/members

**Auth**: Required (Bearer), Admin role
**Source**: FR-014, FR-015, FR-016, US3

**Request**:

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| email | string | Yes | Valid email, 1-255 chars |
| role | string | Yes | One of: admin, member, guest |

**Response (201 — existing user added)**:

| Field | Type | Description |
|-------|------|-------------|
| user_id | UUID | Added user's ID |
| email | string | User email |
| full_name | string? | Display name |
| avatar_url | string? | Avatar |
| role | string | Assigned role |
| joined_at | datetime | Membership creation time |

**Response (201 — invitation created for new user)**:

| Field | Type | Description |
|-------|------|-------------|
| invitation_id | UUID | Invitation ID |
| email | string | Invited email |
| role | string | Intended role |
| status | string | "pending" |
| expires_at | datetime | Invitation expiry |

**Errors**:

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | Invalid email format or role value |
| 403 | FORBIDDEN | Current user is not workspace admin |
| 404 | NOT_FOUND | Workspace does not exist |
| 409 | CONFLICT | User is already a member or has pending invitation |

### Endpoint 2: GET /api/v1/workspaces/{workspace_id}/invitations

**Auth**: Required (Bearer), Admin role
**Source**: FR-016, US3

**Response (200)**:

| Field | Type | Description |
|-------|------|-------------|
| items | InvitationResponse[] | List of invitations |

Each InvitationResponse:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Invitation ID |
| email | string | Invited email |
| role | string | Intended role |
| status | string | pending/accepted/expired/cancelled |
| invited_by | UUID | Inviter user ID |
| expires_at | datetime | Expiry timestamp |
| created_at | datetime | Creation timestamp |

### Endpoint 3: DELETE /api/v1/workspaces/{workspace_id}/invitations/{invitation_id}

**Auth**: Required (Bearer), Admin role
**Source**: US3 Acceptance Scenario 5

**Response (204)**: No content

**Errors**:

| Status | Code | When |
|--------|------|------|
| 403 | FORBIDDEN | Not workspace admin |
| 404 | NOT_FOUND | Invitation not found or already accepted |

### Existing Endpoints (No Changes Needed)

- `GET /api/v1/auth/me` — Get user profile (works)
- `PATCH /api/v1/auth/me` — Update profile (works)
- `POST /api/v1/auth/logout` — Logout (works)
- `GET /api/v1/workspaces/{id}/members` — List members (works)
- `PATCH /api/v1/workspaces/{id}/members/{uid}` — Update role (works)
- `DELETE /api/v1/workspaces/{id}/members/{uid}` — Remove member (works)
- `PATCH /api/v1/workspaces/{id}` — Update workspace (works)
- `DELETE /api/v1/workspaces/{id}` — Delete workspace (works)

### Endpoints to Remove

- `POST /api/v1/auth/callback` — 501 placeholder (Supabase client handles)
- `POST /api/v1/auth/refresh` — 501 placeholder (Supabase client handles)

---

## Project Structure

```text
specs/008-user-management/
├── spec.md
├── plan.md              # This file
├── checklists/
│   └── requirements.md
└── tasks.md             # Next phase

backend/src/pilot_space/
├── api/v1/
│   ├── routers/
│   │   └── workspaces.py              # EDIT: Fix OWNER role, implement invitation endpoint
│   └── schemas/
│       ├── auth.py                     # EDIT: Remove unused callback/refresh schemas
│       └── workspace.py               # EDIT: Add InvitationResponse schema
├── infrastructure/database/
│   ├── models/
│   │   └── workspace_invitation.py    # NEW: Invitation SQLAlchemy model
│   └── repositories/
│       └── invitation_repository.py   # NEW: Invitation repository
├── application/services/
│   └── workspace.py                   # NEW: WorkspaceService (invitation logic)
└── dependencies.py                    # EDIT: Extend ensure_user_synced for auto-accept

backend/tests/
├── unit/
│   └── test_workspace_service.py      # NEW: Invitation service tests
└── integration/
    └── test_workspace_members.py      # NEW: Member management integration tests

frontend/src/
├── app/(auth)/
│   ├── callback/page.tsx              # EDIT: Fix OAuth callback with Supabase
│   ├── forgot-password/page.tsx       # NEW: Forgot password form
│   └── reset-password/page.tsx        # NEW: Reset password form
├── app/(workspace)/[workspaceSlug]/settings/
│   ├── page.tsx                       # EDIT: Workspace general settings
│   ├── members/page.tsx               # NEW: Members management page
│   └── profile/page.tsx               # NEW: User profile settings
├── features/settings/
│   ├── pages/
│   │   ├── workspace-general-page.tsx # NEW: General settings component
│   │   ├── members-settings-page.tsx  # NEW: Members management component
│   │   └── profile-settings-page.tsx  # NEW: Profile settings component
│   └── components/
│       ├── member-row.tsx             # NEW: Member list row
│       ├── invite-member-dialog.tsx   # NEW: Invitation dialog
│       └── delete-workspace-dialog.tsx # NEW: Delete confirmation
└── features/settings/hooks/
    ├── use-workspace-invitations.ts   # NEW: TanStack Query hook
    └── use-workspace-settings.ts      # NEW: TanStack Query hook

frontend/src/__tests__/
├── settings/
│   ├── profile-settings-page.test.tsx # NEW
│   ├── members-settings-page.test.tsx # NEW
│   └── workspace-general-page.test.tsx # NEW
```

**Structure Decision**: Follows existing feature-folder pattern. Settings pages live under `features/settings/pages/` (matching `ai-settings-page.tsx` precedent). New backend service follows CQRS-lite per DD-064.

---

## Quickstart Validation

### Scenario 1: Full Auth Flow (Happy Path)

1. Start fresh browser, navigate to `/login`
2. Click "Sign up", enter name/email/password, submit
3. Verify redirect to workspace creation or default workspace
4. Close browser tab, re-open app
5. **Verify**: User is still logged in (session persisted via Supabase)
6. Wait for token to expire (or manually clear access token)
7. **Verify**: App auto-refreshes token, no redirect to login

### Scenario 2: Invite and Join Workspace

1. Login as workspace admin, navigate to `/settings/members`
2. Click "Invite member", enter email, select role "member", submit
3. **Verify**: Invitation appears in members list with "Pending" badge
4. Open incognito window, sign up with the invited email
5. **Verify**: After signup, the workspace appears in workspace list
6. Navigate to the workspace
7. **Verify**: User has "member" role, cannot access admin settings

### Scenario 3: Role Change and Removal

1. Login as admin, navigate to `/settings/members`
2. Change a member's role from "member" to "admin"
3. **Verify**: Role badge updates immediately
4. Remove a different member
5. **Verify**: Member disappears from list
6. Try removing yourself (last admin)
7. **Verify**: Error message "Cannot remove the only admin"

### Scenario 4: Password Reset

1. Navigate to `/login`, click "Forgot password"
2. Enter registered email, submit
3. **Verify**: Success message shown (regardless of email existence — no enumeration)
4. Check email, click reset link
5. Enter new password, submit
6. **Verify**: Redirected to login, can sign in with new password

---

## Complexity Tracking

No constitution gate violations. All gates pass.

---

## Validation Checklists

### Architecture Completeness

- [x] Every FR from spec has a row in Requirements-to-Architecture Mapping (33/33)
- [x] Every user story maps to backend + frontend components (6/6)
- [x] Data model covers all spec entities with fields, relationships, indexes (1 new + 2 modified)
- [x] API contracts cover all user-facing interactions (3 new + 8 existing + 2 removed)
- [x] Research documents each decision with 2+ alternatives (7 decisions)

### Constitution Compliance

- [x] Technology standards gate passed
- [x] Simplicity gate passed
- [x] Quality gate passed
- [x] No violations to document

### Traceability

- [x] Every technical decision references FR-NNN or constitution article
- [x] Every contract references the user story it serves
- [x] Every data entity references the spec entity it implements
- [x] Project structure matches constitution architecture patterns

### Plan Quality

- [x] No `[NEEDS CLARIFICATION]` remaining
- [x] Performance constraints have concrete targets (<200ms P95, <2s profile save)
- [x] Security documented (RLS policy for invitations, role-based guards, email enumeration prevention)
- [x] Error handling strategy defined per endpoint
- [x] File creation order specified (models → repos → services → endpoints → frontend)
