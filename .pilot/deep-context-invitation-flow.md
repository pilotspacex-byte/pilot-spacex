# Deep Context Report: Invitation Member Flow

**Generated**: 2026-03-25
**Detected Stack**: Python/FastAPI + TypeScript/Next.js, PostgreSQL, Supabase Auth, SQLAlchemy async, MobX + TanStack Query
**Scope**: ~25 files, ~40 symbols analyzed
**Risk Summary**: 3 DANGER, 5 WATCH, 2 UNKNOWN

## 0. Stack & Architecture
- **Languages**: Python 3.12, TypeScript 5.x
- **Frameworks**: FastAPI (backend), Next.js App Router (frontend)
- **Databases**: PostgreSQL via Supabase (local docker)
- **Queues/Events**: pgmq (not used by invitation flow)
- **Architecture style**: Modular monolith, Clean Architecture 5-layer, CQRS-lite

---

## 1. Complete Flow Trace

### Flow A: Admin Invites Member (Sender Side)

```
Frontend                                    Backend
────────────────────────────────────────    ────────────────────────────────────────
1. MembersPage
   └─ InviteMemberDialog (dialog form)
      └─ workspaceStore.inviteMember()
         └─ workspacesApi.inviteMember()
            POST /workspaces/{id}/members   → workspace_invitations.py:add_workspace_member()
            {email, role: "MEMBER"}            └─ workspace_service.invite_member()
                                                  ├─ user_repo.get_by_email()
                                                  │   ├─ EXISTS → workspace_repo.add_member() → immediate
                                                  │   └─ NOT EXISTS → invitation_repo.create() → pending
                                                  └─ returns InviteMemberResult
                                               └─ Router maps to WorkspaceMemberResponse | InvitationResponse
         └─ queryClient.invalidateQueries()
            ├─ workspaceMembersKeys
            └─ workspaceInvitationsKeys
```

### Flow B: Invited User Signs Up & Auto-Accepts (Receiver Side)

```
Frontend                                    Backend
────────────────────────────────────────    ────────────────────────────────────────
1. User signs up via Supabase Auth
   (login page — /login with signup mode)

2. ANY first authenticated API request      → FastAPI Depends() chain
   (e.g. GET /workspaces)                     └─ SyncedUserId dependency
                                                 └─ ensure_user_synced() [auth.py:331]
                                                    ├─ user_repo.get_by_id_scalar()
                                                    │   └─ NOT FOUND → create User
                                                    ├─ invitation_repo.get_pending_by_email(email)
                                                    │   └─ Returns unexpired PENDING invitations
                                                    └─ FOR EACH pending invitation:
                                                       ├─ workspace_repo.add_member(workspace_id, user_id, role)
                                                       ├─ invitation_repo.mark_accepted(invitation_id)
                                                       └─ (non-fatal: exceptions logged, not raised)
                                                    └─ session.commit()

3. WorkspaceGuard validates access          → GET /workspaces/{slug}
   └─ Now has membership → renders workspace
```

### Flow C: Admin Lists/Cancels Invitations

```
Frontend                                    Backend
────────────────────────────────────────    ────────────────────────────────────────
MembersPage (Invitations tab, admin-only)
├─ useWorkspaceInvitations()                → GET /workspaces/{id}/invitations
│  └─ apiClient.get()                         └─ WorkspaceInvitationService.list_invitations()
│                                                ├─ workspace_repo.get_with_members() (eager load)
│                                                ├─ check admin/owner role
│                                                └─ invitation_repo.get_by_workspace()
│
└─ useCancelInvitation()                    → DELETE /workspaces/{id}/invitations/{inv_id}
   └─ apiClient.delete()                      └─ WorkspaceInvitationService.cancel_invitation()
                                                  ├─ workspace_repo.get_with_members()
                                                  ├─ check admin/owner role
                                                  ├─ invitation_repo.cancel()
                                                  └─ verify invitation.workspace_id matches (H-5 security)
```

---

## 2. Runtime Coupling

| Source | Target | Mechanism | Risk |
|--------|--------|-----------|------|
| `container.py:534` | `WorkspaceInvitationService` | DI Factory provider | [SAFE] |
| `container.py:525` | `WorkspaceService` (invite_member) | DI Factory provider | [SAFE] |
| `api/v1/dependencies.py` | `WorkspaceInvitationServiceDep` | FastAPI Depends + DI | [SAFE] |
| `auth.py:331` ensure_user_synced | `InvitationRepository`, `WorkspaceRepository` | Direct instantiation (NOT DI) | [WATCH] — bypasses container |
| `auth.py:331` SyncedUserId | 50+ route handlers | FastAPI Depends chain | [WATCH] — trigger point for auto-accept runs on EVERY first request for new users |
| `workspace_invitations.py:32` router | `main.py` router registration | `include_router` | [SAFE] |

**Notes**: `ensure_user_synced` creates its own `InvitationRepository` and `WorkspaceRepository` directly from the session rather than using the DI container. This is intentional (it's a dependency itself, can't use container providers), but means any future middleware/interceptors on the repository layer won't apply here.

---

## 3. Data & Side-Effects

| Operation | Table/Key | Type | Idempotent? | Risk |
|-----------|-----------|------|-------------|------|
| `invite_member` (existing user) | `workspace_members` | WRITE (INSERT) | No — ConflictError on dup | [SAFE] |
| `invite_member` (new user) | `workspace_invitations` | WRITE (INSERT) | No — ConflictError on dup pending | [SAFE] |
| `ensure_user_synced` | `users` | WRITE (INSERT) | Yes — IntegrityError caught | [SAFE] |
| `ensure_user_synced` | `workspace_members` | WRITE (INSERT per invitation) | No — exception swallowed | [WATCH] |
| `ensure_user_synced` | `workspace_invitations` | UPDATE (status→accepted) | Yes — only updates PENDING | [SAFE] |
| `list_invitations` | `workspace_invitations` | READ | N/A | [SAFE] |
| `cancel_invitation` | `workspace_invitations` | UPDATE (status→cancelled) | Yes — only updates PENDING | [SAFE] |

**Transaction Boundaries**:
- `invite_member`: Within request session (auto-commit via middleware)
- `ensure_user_synced`: **Explicit `session.commit()`** at line 412 — this is OUTSIDE the normal middleware transaction. If the user creation succeeds but an invitation auto-accept fails, the user is still committed and the failed invitation stays PENDING (graceful degradation).

**No email sending**: There is NO email notification system for invitations. The dialog says "They will receive an email with instructions" but **no email is actually sent**. [DANGER]

---

## 4. Cross-System Contracts

| Provider | Consumer | Contract | Schema Match? | Risk |
|----------|----------|----------|--------------|------|
| `POST /workspaces/{id}/members` | `workspacesApi.inviteMember()` | Request: `{email, role}` | **DRIFT** — backend `InvitationCreateRequest` has `suggested_sdlc_role` field, frontend doesn't send it | [WATCH] |
| `POST /workspaces/{id}/members` | `workspacesApi.inviteMember()` | Response: `WorkspaceMemberResponse \| InvitationResponse` | **MISMATCH** — frontend always expects `WorkspaceMember` type, but backend may return `InvitationResponse` for pending invitations | [DANGER] |
| `GET /workspaces/{id}/invitations` | `useWorkspaceInvitations()` | Response: `InvitationResponse[]` | **DRIFT** — frontend `WorkspaceInvitation` type has `invitedById`/`invitedByName` (camelCase) but backend returns `invited_by` (UUID only, no name) | [DANGER] |
| `DELETE /workspaces/{id}/invitations/{id}` | `useCancelInvitation()` | 204 No Content | Match | [SAFE] |
| Supabase Auth signup | `ensure_user_synced` | JWT with `email` claim | Match | [SAFE] |

**Breaking Issues**:
1. **POST /members response type mismatch**: `workspacesApi.inviteMember()` calls `transformWorkspaceMember()` on the response, but when backend creates a pending invitation, it returns `InvitationResponse` (different shape: `id`, `email`, `role`, `status`, `invited_by`, `expires_at`). The `transformWorkspaceMember` function expects `userId`, `fullName`, `avatarUrl`, `joinedAt` — all absent from `InvitationResponse`. This will result in a member object with `undefined` fields being added to MobX store.

2. **GET /invitations field name mismatch**: Frontend `WorkspaceInvitation` interface expects `invitedById` and `invitedByName`, but backend `InvitationResponse` returns `invited_by` (UUID) and has no inviter name field. The `apiClient` likely uses camelCase transformation which would map `invited_by` → `invitedBy` (not `invitedById`).

---

## 5. Operational Context

| Requirement | Value | Source | Risk |
|-------------|-------|--------|------|
| Auth | Supabase JWT required for all endpoints | `CurrentUser` / `SyncedUserId` deps | [SAFE] |
| Role | Admin/Owner required for invite/list/cancel | Service-layer checks | [SAFE] |
| DB | `invitation_status` enum type | Migration 022 | [SAFE] |
| DB | `workspace_role` enum (shared with members) | Pre-existing | [SAFE] |
| Unique constraint | `uq_workspace_invitations_pending` on `(workspace_id, email)` | Model + Migration | [WATCH] — constraint is on ALL statuses, not just PENDING; re-inviting after cancellation will fail |
| Expiry | 7 days from creation | `_default_expires_at()` | [SAFE] |
| No cron | No job to mark expired invitations | N/A | [WATCH] — `is_expired` property checks at read time, but `status` stays PENDING in DB |

---

## 6. Pattern Rules & Mismatches

| Rule | Status | Detail |
|------|--------|--------|
| AppError hierarchy for domain errors | COMPLIANT | Uses `ConflictError`, `NotFoundError`, `ForbiddenError` |
| Empty string routes `""` not `"/"` | VIOLATION | Invitation router uses `"/{workspace_id}/members"` (correct prefix-based) |
| Service raises, router doesn't catch | COMPLIANT | Router lets exceptions propagate to global handler |
| SessionDep in route signature | COMPLIANT | All routes declare `session: SessionDep` |
| Response model on endpoints | COMPLIANT | All have `response_model` |
| Role sent uppercase to backend | COMPLIANT | `workspacesApi.inviteMember` does `role.toUpperCase()` |
| CQRS-lite pattern | PARTIAL | `invite_member` is on `WorkspaceService` (not `WorkspaceInvitationService`) for "API compat" |

**Stale References**:
- `InviteMemberDialog` description says "They will receive an email with instructions" — no email system exists
- `UniqueConstraint` name says `_pending` but covers all statuses

---

## 7. Ownership & Stability

| File | Last Modified | Change Freq | Test Coverage | Stability |
|------|--------------|-------------|---------------|-----------|
| `workspace_invitation.py` (model) | Feb 2026 | Low | Has unit tests | Stable |
| `invitation_repository.py` | Feb 2026 | Low | `test_invitation_repository.py` | Stable |
| `workspace_invitation.py` (service) | Feb 2026 | Low | Tested via workspace tests | Stable |
| `workspace_invitations.py` (router) | Feb 2026 | Low | `test_workspace_members_api.py` | Stable |
| `auth.py` (ensure_user_synced) | Feb 2026 | Medium | `test_ensure_user_synced.py` | Active |
| `invite-member-dialog.tsx` | Feb 2026 | Low | No dedicated tests | Stable |
| `use-workspace-invitations.ts` | Feb 2026 | Low | No tests | Stable |
| `members-page.tsx` | Mar 2026 | Medium | `members-page.test.tsx` | Active |
| `WorkspaceStore.ts` | Mar 2026 | High | `WorkspaceStore.test.ts` | Active |
| `workspace-guard.tsx` | Feb 2026 | Low | No tests | Stable |

---

## Implementation Checklist (from DANGER and WATCH items)

- [ ] **[DANGER] No email sending**: Invitation creates DB record but sends no email. Need to implement email notification (Supabase Edge Functions, SMTP, or queue-based) or remove misleading UI copy
- [ ] **[DANGER] POST /members response mismatch**: Frontend `inviteMember()` always expects `WorkspaceMember` shape but backend returns `InvitationResponse` for pending invitations. Fix: either handle both response types in frontend, or make backend always return a consistent shape
- [ ] **[DANGER] GET /invitations field name mismatch**: Frontend `WorkspaceInvitation.invitedById` / `invitedByName` don't match backend `InvitationResponse.invited_by` (UUID only). Fix: align field names and add inviter name to response
- [ ] **[WATCH] UniqueConstraint blocks re-invitation**: `uq_workspace_invitations_pending` is on `(workspace_id, email)` without status filter — cancelled/expired invitations block new invitations to same email. Fix: make constraint partial (PENDING only) or soft-delete old invitations before creating new ones
- [ ] **[WATCH] No expiry cron job**: Expired invitations stay as `status=PENDING` in DB forever. `is_expired` property checks time at read, but `get_pending_by_email` already filters by `expires_at > now()`. Low priority but creates data noise
- [ ] **[WATCH] ensure_user_synced bypasses DI**: Creates repositories directly. Any future AOP/middleware on repository layer won't apply to auto-accept flow
- [ ] **[WATCH] No invitation acceptance page**: There's no dedicated `/accept-invite` or `/signup?invite=TOKEN` page. Invited users must independently find the app, sign up, and `ensure_user_synced` handles the rest silently. No guided onboarding for invited users
- [ ] **[WATCH] suggested_sdlc_role unused by frontend**: Backend supports `suggested_sdlc_role` on `InvitationCreateRequest` but frontend never sends it

---

## Graph Updates

New edges discovered for `.pilot/deep-context.yaml`:
- `workspace_invitations.router` → `WorkspaceService.invite_member` (HTTP endpoint → service)
- `workspace_invitations.router` → `WorkspaceInvitationService` (HTTP endpoint → service)
- `ensure_user_synced` → `InvitationRepository.get_pending_by_email` (auto-accept on signup)
- `ensure_user_synced` → `WorkspaceRepository.add_member` (auto-accept on signup)
- `InviteMemberDialog` → `WorkspaceStore.inviteMember` → `workspacesApi.inviteMember` → `POST /workspaces/{id}/members`
- `useWorkspaceInvitations` → `GET /workspaces/{id}/invitations`
- `useCancelInvitation` → `DELETE /workspaces/{id}/invitations/{id}`
- `MembersPage` → `InviteMemberDialog` + `useWorkspaceInvitations` + `useCancelInvitation`
- `WorkspaceGuard` → blocks access until `ensure_user_synced` has run (via any SyncedUserId endpoint)
