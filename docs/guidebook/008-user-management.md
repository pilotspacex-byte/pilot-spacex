# Guidebook: User Management (Feature 008)

## Overview

User Management provides authentication, profile management, team invitation, role-based access control, workspace settings, and password reset for Pilot Space. It enables teams of 5-100 members to self-service onboard, collaborate, and manage workspace governance.

**Branch**: `008-user-management`
**Spec**: `specs/008-user-management/spec.md` (33 FRs, 6 user stories)
**Priority Phases**: P1 (Auth) -> P2 (Profile + Members) -> P3 (Settings + Reset)

---

## Architecture

### Backend Stack

```text
FastAPI Router -> Service Layer (CQRS-lite) -> Repository -> SQLAlchemy + RLS
```

| Layer | Files | Purpose |
|-------|-------|---------|
| Presentation | `auth.py`, `workspaces.py`, `workspace_members.py`, `workspace_invitations.py` | HTTP endpoints, request validation |
| Application | `workspace.py` (WorkspaceService) | Business logic, invite\_member flow |
| Infrastructure | `invitation_repository.py`, `workspace_repository.py`, `user_repository.py` | Data access, RLS enforcement |
| Domain | `workspace_invitation.py` (142 lines), `workspace_member.py`, `user.py` | Entity definitions, role enums |
| Auth | `dependencies/auth.py` (ensure\_user\_synced) | JWT validation, auto-accept invitations |

### Frontend Stack

```text
Next.js Pages -> MobX Stores (UI) + TanStack Query (server) -> Supabase Auth SDK
```

| Layer | Files | Purpose |
|-------|-------|---------|
| Pages | `login/`, `callback/`, `forgot-password/`, `reset-password/`, `settings/` | Route definitions |
| Features | `settings/pages/`, `settings/components/`, `settings/hooks/` | Domain-specific UI |
| Stores | `AuthStore.ts` (360 lines), `WorkspaceStore.ts` (445 lines) | Auth state, workspace/member state |
| Hooks | `use-workspace-settings.ts`, `use-workspace-invitations.ts` | TanStack Query wrappers |

### Router Registration (main.py)

```text
workspace_invitations_router  -> prefix /api/v1       (router prefix: /workspaces)
workspace_members_router      -> prefix /api/v1/workspaces (router prefix: none)
workspaces_router             -> prefix /api/v1       (router prefix: /workspaces)
```

**Note**: `workspaces.py` and `workspace_members.py` both define GET/PATCH/DELETE member endpoints at the same paths. FastAPI registers the first-mounted route. See [Known Issues](#known-issues) for details.

---

## Authentication Flow (P1)

### Email/Password Login

```text
User -> Login Page -> AuthStore.login()
  -> supabase.auth.signInWithPassword()
  -> onAuthStateChange(SIGNED_IN) -> redirect to workspace
```

**Key files:**

- `frontend/src/app/(auth)/login/page.tsx:1-229` -- Login/signup toggle form
- `frontend/src/stores/AuthStore.ts` -- `login()`, `signup()`, `loginWithOAuth()` methods
- `frontend/src/lib/supabase.ts` -- Supabase client initialization

**Implementation details:**

- Login page toggles between login and signup modes (single page, not separate routes)
- Form validates `!email || !password` before submission
- Error messages use `role="alert"` for screen reader accessibility
- Loading state disables submit button during auth

### OAuth (GitHub)

```text
User -> Login Page -> AuthStore.loginWithOAuth('github')
  -> supabase.auth.signInWithOAuth({ provider: 'github' })
  -> GitHub authorization -> /callback -> session detection -> redirect
```

**Key files:**

- `frontend/src/app/(auth)/callback/page.tsx:1-98` -- OAuth callback handler with 10s timeout
- `frontend/src/stores/AuthStore.ts` -- `loginWithOAuth()` supports `'github' | 'google'` parameter types

**Implementation details:**

- Callback page subscribes to `onAuthStateChange` for `SIGNED_IN` event
- 10-second timeout redirects to login with error if auth state never fires
- Subscription cleanup happens in useEffect return

### Signup

```text
User -> Login Page (signup mode) -> AuthStore.signup(email, password, name)
  -> supabase.auth.signUp({ email, password, options: { data: { full_name } } })
  -> Email confirmation (if enabled) -> Login
```

**Implementation details:**

- Signup sends `full_name` in user metadata via Supabase `signUp()` options
- When `enable_confirmations = true`, user must verify email before login
- On first authenticated API call after signup, `ensure_user_synced` creates local DB user

### Token Refresh

Handled automatically by Supabase client SDK. The `onAuthStateChange` listener captures `TOKEN_REFRESHED` events and updates the session in `AuthStore`.

```typescript
// AuthStore.ts -- onAuthStateChange listener
supabase.auth.onAuthStateChange((event, session) => {
  this.session = session;
  this.user = session ? this.mapSupabaseUser(session.user) : null;
  if (event === 'SIGNED_OUT') {
    window.location.href = '/login';
  }
});
```

### Logout

```text
User -> Avatar Menu -> Sign out -> AuthStore.logout()
  -> supabase.auth.signOut()
  -> onAuthStateChange(SIGNED_OUT) -> hard redirect to /login
```

**Note**: Logout uses `window.location.href` (full page reload) rather than Next.js router navigation. This ensures all client state is cleared.

---

## User Sync and Auto-Accept Invitations

When a user makes their first authenticated API call after signup, `ensure_user_synced` runs as a FastAPI dependency:

```text
JWT arrives -> ensure_user_synced() dependency
  1. Check if user exists in app DB (get_by_id_scalar)
  2. If exists, return user_id immediately
  3. If not, create User from JWT claims (email from token, or placeholder)
  4. Query pending invitations by email (invitation_repo.get_pending_by_email)
  5. For each pending invitation:
     a. workspace_repo.add_member(workspace_id, user_id, role)
     b. invitation_repo.mark_accepted(invitation_id)
  6. session.commit()
```

**Key file:** `backend/src/pilot_space/dependencies/auth.py:303-370`

This implements FR-016 (pending invitations auto-accepted on signup) and US3.4.

**Email fallback**: If JWT lacks an email claim, the placeholder `user-{uuid}@placeholder.local` is used. This means invitation auto-accept will not match for OAuth users with private emails unless Supabase is configured to request email scope.

---

## Profile Management (P2)

### View/Update Profile

**Route:** `/[workspaceSlug]/settings/profile`

| Field | Editable | Source |
|-------|----------|--------|
| Display Name | Yes | `PATCH /auth/me` -> `user.full_name` |
| Email | No (read-only) | Supabase Auth provider |
| Avatar | Synced from auth provider | `user.avatar_url` |

**Key files:**

- `frontend/src/features/settings/pages/profile-settings-page.tsx:1-170` -- Profile UI with avatar initials fallback
- `backend/src/pilot_space/api/v1/routers/auth.py` -- `PATCH /auth/me` endpoint
- `frontend/src/stores/AuthStore.ts` -- `updateProfile()` method

**Implementation details:**

- Avatar displays initials when no image URL exists
- Email field shows hint "Email is managed by your identity provider"
- Save button shows `aria-busy` during submission
- Form hints use `aria-describedby` for accessibility

---

## Member Management (P2)

### Invitation Flow

```text
Admin -> Members Page -> "Invite Member" -> Enter email + role
  -> POST /api/v1/workspaces/{id}/members
    -> workspace_invitations.py router
      -> WorkspaceService.invite_member()
        -> User exists? -> add_member immediately (is_immediate=True)
        -> User absent? -> create WorkspaceInvitation (7-day expiry)
```

**Key files:**

- `frontend/src/features/settings/components/invite-member-dialog.tsx:1-200` -- Email + role form
- `backend/src/pilot_space/api/v1/routers/workspace_invitations.py:61-140` -- POST endpoint (CQRS-lite via WorkspaceService)
- `backend/src/pilot_space/application/services/workspace.py:71-153` -- `invite_member()` with email normalization
- `backend/src/pilot_space/infrastructure/database/repositories/invitation_repository.py:1-162` -- 6 repository methods

**Service logic** (`WorkspaceService.invite_member`):

1. Normalize email: `email.strip().lower()`
2. Check if user exists via `user_repo.get_by_email()`
3. If exists: check `workspace_repo.is_member()`, then `add_member()` immediately
4. If not exists: check `invitation_repo.exists_pending()`, then create `WorkspaceInvitation`
5. Returns `InviteMemberResult(is_immediate, member, invitation)` dataclass

**Error handling**: `ValueError` from service maps to HTTP 409 CONFLICT in router.

### Role Hierarchy

```text
OWNER > ADMIN > MEMBER > GUEST
```

| Role | Can manage members | Can edit content | Can view | Can delete workspace |
|------|-------------------|------------------|----------|---------------------|
| Owner | Yes | Yes | Yes | Yes |
| Admin | Yes | Yes | Yes | No |
| Member | No | Yes | Yes | No |
| Guest | No | No | Yes (assigned items) | No |

**`is_admin` property on WorkspaceMember**: Returns `True` for both ADMIN and OWNER roles. Used consistently in authorization checks across `workspace_invitations.py` router.

### Role Change

```text
Admin -> Members Page -> Role dropdown -> select new role
  -> PATCH /api/v1/workspaces/{id}/members/{user_id} { role: "admin" }
```

**Guard:** Cannot remove the last admin/owner (returns 400).

**Key files:**

- `frontend/src/features/settings/components/member-row.tsx:1-205` -- Role selector with hierarchy-aware permissions, responsive layout
- `backend/src/pilot_space/api/v1/routers/workspace_members.py:142-217` -- PATCH endpoint
- `backend/src/pilot_space/api/v1/routers/workspaces.py:443-532` -- Duplicate PATCH endpoint with ownership transfer guard

**Ownership transfer**: `workspaces.py:503-513` prevents non-owners from setting OWNER role on another member.

### Member Removal

```text
Admin -> Members Page -> More menu -> Remove -> ConfirmActionDialog -> DELETE /workspaces/{id}/members/{user_id}
```

- Self-removal is allowed except for the last admin
- Uses `ConfirmActionDialog` (shadcn/ui AlertDialog) instead of `window.confirm()`
- Admin count check: `sum(1 for m in workspace.members if m.role == ADMIN)`

### Pending Invitations

- Admin-only section below active members list
- Shows email, role, and created date for each pending invitation
- Cancel button with confirmation dialog
- `DELETE /api/v1/workspaces/{id}/invitations/{invitation_id}` cancels invitation

---

## Workspace Settings (P3)

### General Settings

**Route:** `/[workspaceSlug]/settings`

| Field | Validation | Admin-only |
|-------|-----------|------------|
| Workspace Name | Required | Yes (`readOnly` for non-admin) |
| URL Slug | Pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$`, unique | Yes |
| Description | Optional, textarea | Yes |

**Implementation details:**

- Non-admin users see `readOnly` inputs (not `disabled`) -- better for accessibility
- Client-side slug validation with inline error message linked via `aria-describedby`
- Metadata section shows created date, member count, and workspace ID
- "You have unsaved changes" indicator appears when form state differs from server

**Danger Zone (admin only):**

- Delete workspace -- requires typing workspace name to confirm
- Soft-delete via `DELETE /api/v1/workspaces/{id}` (FR-025)
- `delete-workspace-dialog.tsx` handles confirmation and redirect

**Key files:**

- `frontend/src/features/settings/pages/workspace-general-page.tsx:1-313` -- Settings UI with TanStack Query
- `frontend/src/features/settings/components/delete-workspace-dialog.tsx:1-140` -- Type-to-confirm deletion
- `backend/src/pilot_space/api/v1/routers/workspaces.py:292-400` -- PATCH/DELETE workspace

### Settings Layout (Responsive)

All settings pages use a shared layout (`settings/layout.tsx`) with responsive sidebar navigation:

**Desktop (`>= md`):** Fixed `w-56` sidebar with nav sections (Workspace: General, Members, Integrations; Account: Profile, AI Providers) alongside scrollable content area.

**Mobile (`< md`):** Sidebar hidden. A top header bar with hamburger menu icon opens a `Sheet` drawer (slides from left) containing the same navigation items. The sheet closes on nav link click.

```text
Desktop (md+):                    Mobile (<md):
┌─────────┬──────────────┐        ┌──────────────────────┐
│ Sidebar │ Content      │        │ [☰ Settings]         │
│ (w-56)  │              │        ├──────────────────────┤
└─────────┴──────────────┘        │ Content (full width) │
                                  └──────────────────────┘
```

**Responsive patterns applied across all settings pages:**

| Pattern | Mobile | Desktop |
|---------|--------|---------|
| Container padding | `px-4` | `sm:px-6 lg:px-8` |
| Input width | `w-full` | `sm:max-w-md` |
| Member row | Stacks vertically (`flex-col`) | Horizontal (`sm:flex-row`) |
| Header with button | Stacks vertically | `sm:flex-row sm:justify-between` |
| Danger zone | Stacks vertically | `sm:flex-row sm:items-center` |
| Invitation rows | Stacks vertically | `sm:flex-row sm:items-center` |

**Key files:**

- `frontend/src/app/(workspace)/[workspaceSlug]/settings/layout.tsx` -- Shared layout with `SettingsNavContent` component, `Sheet` drawer for mobile
- `frontend/src/features/settings/components/member-row.tsx` -- Grouped avatar+name and role+actions sub-flex for mobile stacking

---

## Password Reset (P3)

### Flow

```text
1. User -> /forgot-password -> enter email -> "Send Reset Link"
   -> AuthStore.resetPassword(email) -> supabase.auth.resetPasswordForEmail()
   -> Same success message regardless of email existence (FR-029, anti-enumeration)

2. User clicks email link -> /reset-password -> Supabase fires PASSWORD_RECOVERY event
   -> Form appears: new password + confirm password
   -> supabase.auth.updateUser({ password }) -> redirect to login

3. Reset links expire after 1 hour (FR-028, Supabase default)
```

**Key files:**

- `frontend/src/app/(auth)/forgot-password/page.tsx:1-176` -- Reset request form
- `frontend/src/app/(auth)/reset-password/page.tsx:1-312` -- Multi-state form (loading/form/success/expired)
- `frontend/src/stores/AuthStore.ts` -- `resetPassword()` method

**Implementation details:**

- Reset password page has 4 states: `loading` (verifying token), `form` (enter password), `success`, `expired`
- 3-second timeout treats unresolved token verification as expired
- Password validation: minimum 8 characters, passwords must match
- Success state auto-redirects to login after 2 seconds

---

## Database Schema

### workspace\_invitations Table

```sql
CREATE TABLE workspace_invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  email VARCHAR NOT NULL,
  role workspace_role NOT NULL DEFAULT 'member',
  invited_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status invitation_status NOT NULL DEFAULT 'pending',
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days'),
  accepted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_deleted BOOLEAN NOT NULL DEFAULT false,
  deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX ix_invitations_email_status ON workspace_invitations(email, status);
CREATE INDEX ix_invitations_workspace_status ON workspace_invitations(workspace_id, status);
CREATE INDEX ix_invitations_expires_at ON workspace_invitations(expires_at);

-- Unique constraint: one pending invitation per workspace per email
CREATE UNIQUE INDEX uq_pending_invitation ON workspace_invitations(workspace_id, email)
  WHERE status = 'pending' AND is_deleted = false;
```

### RLS Policies

```sql
-- Admin/owner can SELECT invitations in their workspace
CREATE POLICY workspace_invitations_select ON workspace_invitations
  FOR SELECT USING (
    workspace_id IN (
      SELECT wm.workspace_id FROM workspace_members wm
      WHERE wm.user_id = auth.uid() AND wm.role IN ('owner', 'admin')
    )
  );
```

**Migration 022** initially used uppercase enum values (`'OWNER'`, `'ADMIN'`) which silently blocked all RLS queries. **Migration 023** fixes this to lowercase (`'owner'`, `'admin'`).

### Migrations

| Migration | Description |
|-----------|-------------|
| `022_workspace_invitations.py` | Create table, indexes, RLS policies |
| `023_fix_invitation_rls_enum_case.py` | Fix enum case sensitivity in RLS policies |

---

## API Endpoints

### Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/auth/login` | No | OAuth redirect URL builder |
| GET | `/api/v1/auth/me` | JWT | Current user profile |
| PATCH | `/api/v1/auth/me` | JWT | Update display name/avatar |
| POST | `/api/v1/auth/logout` | JWT | Invalidate session |

### Members and Invitations

| Method | Path | Auth | Router File | Description |
|--------|------|------|-------------|-------------|
| POST | `/workspaces/{id}/members` | Admin | `workspace_invitations.py` | Invite/add member by email |
| GET | `/workspaces/{id}/members` | Member | `workspace_members.py` / `workspaces.py` | List workspace members |
| PATCH | `/workspaces/{id}/members/{uid}` | Admin | `workspace_members.py` / `workspaces.py` | Update member role |
| DELETE | `/workspaces/{id}/members/{uid}` | Admin/Self | `workspace_members.py` / `workspaces.py` | Remove member |
| GET | `/workspaces/{id}/invitations` | Admin | `workspace_invitations.py` | List pending invitations |
| DELETE | `/workspaces/{id}/invitations/{id}` | Admin | `workspace_invitations.py` | Cancel invitation |

### Workspace Settings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| PATCH | `/api/v1/workspaces/{id}` | Admin | Update name/slug/description |
| DELETE | `/api/v1/workspaces/{id}` | Admin | Soft-delete workspace |

---

## Testing

### Backend Tests (39 passing)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_auth_router.py` | 6 | Auth endpoint registration verification |
| `test_ensure_user_synced.py` | 4 | User creation, auto-accept invitations |
| `test_invitation_repository.py` | 8 | CRUD, duplicate prevention, expiry |
| `test_workspace_creation.py` | 4 | OWNER role assignment on creation |
| `test_workspace_members_api.py` | 12 | List, update role, remove, guards |
| `test_workspace_service.py` | 5 | invite\_member immediate/pending paths |

### Frontend Tests (44 passing)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `forgot-password.test.tsx` | 4 | Form render, validation, submission |
| `reset-password.test.tsx` | 5 | Loading, expired, password validation |
| `profile-settings-page.test.tsx` | 7 | View, update, error handling, read-only email |
| `members-settings-page.test.tsx` | 20 | Role change, remove, invite, cancel, transfer |
| `workspace-general-page.test.tsx` | 8 | Settings, slug validation, delete |

### Running Tests

```bash
# Backend
cd backend && uv run pytest tests/unit/test_auth_router.py \
  tests/unit/test_ensure_user_synced.py \
  tests/unit/test_invitation_repository.py \
  tests/unit/test_workspace_creation.py \
  tests/unit/test_workspace_members_api.py \
  tests/unit/test_workspace_service.py -v

# Frontend
cd frontend && pnpm vitest run \
  src/app/\(auth\)/__tests__/ \
  src/features/settings/ \
  --reporter=verbose
```

---

## Configuration

### Supabase Auth Settings

Located in `frontend/supabase/config.toml`:

```toml
[auth.email]
enable_signup = true
enable_confirmations = true       # Require email verification
double_confirm_changes = true     # Confirm email changes
max_frequency = "1s"              # Rate limit
```

To disable email confirmation for local development, set `enable_confirmations = false`.

### Environment Variables

**Backend** (`.env`):

- `SUPABASE_URL` -- Supabase instance URL
- `SUPABASE_SERVICE_ROLE_KEY` -- Service role key for admin operations
- `APP_ENV` -- `development` enables demo mode fallback

**Frontend** (`.env.local`):

- `NEXT_PUBLIC_SUPABASE_URL` -- Supabase instance URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` -- Anonymous key for client auth

---

## Known Issues

### P0 -- Duplicate Member Routes

**Files**: `workspaces.py:398-590` and `workspace_members.py:95-281`

Both files define GET/PATCH/DELETE for `/workspaces/{id}/members`. FastAPI registers the first-loaded route, causing the second to be shadowed. The `workspaces.py` version includes ownership transfer guards that `workspace_members.py` lacks.

**Impact**: Route shadowing -- only the first-registered handler for each HTTP method+path is active.

**Recommendation**: Remove member endpoints from `workspaces.py` (lines 398-590) and keep only `workspace_members.py` + `workspace_invitations.py` as the member management routers. Add the ownership transfer guard from `workspaces.py:503-513` into `workspace_members.py`.

### P1 -- Race Condition in ensure\_user\_synced

**File**: `dependencies/auth.py:335-348`

Between checking `get_by_id_scalar()` and creating a new User, concurrent requests from the same new user can both see `None` and attempt to INSERT, causing a UNIQUE constraint violation.

**Impact**: First login after signup could fail with 500 if two requests arrive simultaneously.

**Recommendation**: Use `INSERT ... ON CONFLICT DO NOTHING` or catch `IntegrityError` and retry the lookup.

### P1 -- No Error Handling in Auto-Accept Loop

**File**: `dependencies/auth.py:354-360`

The invitation acceptance loop has no try/except. If `add_member()` fails for one invitation (e.g., workspace was deleted), subsequent invitations are not processed and the entire `ensure_user_synced` fails.

**Impact**: A single invalid invitation blocks all auto-accepts for that user.

**Recommendation**: Wrap each iteration in try/except, log failures, and continue processing remaining invitations.

### P2 -- CQRS-lite Violations

**Files**: `auth.py` (PATCH /me), `workspace_members.py` (PATCH/DELETE members)

These endpoints call repository methods directly from the router layer instead of going through a service class with explicit payloads. This bypasses the `Service.execute(Payload) -> Result` pattern established in DD-064.

### P2 -- Admin Role Check in workspace\_members.py

**File**: `workspace_members.py:183`

The PATCH endpoint checks `current_member.role != WorkspaceRole.ADMIN` but does not also check for OWNER. The `is_admin` property (which includes OWNER) is used correctly in `workspace_invitations.py` but not here.

### P3 -- Email Validation

**File**: `api/v1/schemas/workspace.py` (InvitationCreateRequest)

The `email` field uses `str` type instead of Pydantic `EmailStr`. Email format validation relies entirely on the frontend regex `^[^\s@]+@[^\s@]+\.[^\s@]+$`.

---

## Troubleshooting

### "Email not confirmed" on login

Email confirmation is enabled by default. In local development, either:

1. Set `enable_confirmations = false` in `frontend/supabase/config.toml`
2. Confirm via admin API:

```bash
curl -X PUT "http://127.0.0.1:54321/auth/v1/admin/users/{USER_ID}" \
  -H "apikey: <SERVICE_ROLE_KEY>" \
  -H "Authorization: Bearer <SERVICE_ROLE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"email_confirm": true}'
```

### Demo mode shows wrong user

In development (`APP_ENV=development`), the app falls back to the `pilot-space-demo` workspace when the authenticated user has no workspaces. The demo workspace shows the demo user identity, not the real user. Create a workspace for the user to see their real identity.

### Member invitation shows "already a member"

The email is already associated with an active membership. Check `workspace_members` table:

```sql
SELECT * FROM workspace_members
WHERE workspace_id = '<id>' AND is_deleted = false;
```

### Last admin removal blocked

By design (FR-019). The system prevents removing the last admin/owner to avoid orphaned workspaces. Transfer ownership first via the members page, or have another admin remove you.

### OAuth callback stuck on loading

The callback page has a 10-second timeout. If the Supabase auth state change event never fires, the user is redirected to `/login` with an error. Common causes:

- Supabase Auth callback URL misconfigured in Supabase dashboard
- Browser blocking third-party cookies (Supabase auth uses cookies)
- Network issues preventing the OAuth token exchange

### Password reset shows "Link expired" immediately

The reset password page waits 3 seconds for a `PASSWORD_RECOVERY` auth event. If Supabase session detection is slow (e.g., network latency), the page may show "expired" prematurely. The user can click "Request a new reset link" to try again.
