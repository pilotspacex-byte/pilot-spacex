# Feature Specification: User Management

**Feature Number**: 008
**Branch**: `008-user-management`
**Created**: 2026-02-03
**Status**: Draft
**Author**: Tin Dang

---

## Problem Statement

**Who**: All Pilot Space users — workspace owners, admins, members, and prospective new users.

**Problem**: Authentication flows are partially implemented (OAuth callback and token refresh return 501), workspace owners cannot invite new team members, users have no UI to manage their profile or workspace settings, and the role hierarchy (owner vs admin) is inconsistently applied. These gaps prevent teams from onboarding, growing, and self-managing their workspaces.

**Impact**: Without functional authentication recovery (token refresh), users lose sessions mid-work. Without member invitation, workspaces are single-user silos — directly blocking the collaborative value proposition. Without profile and settings management, users cannot personalize their experience or configure workspace-level preferences. This undermines adoption for teams of 5-100 members (target scale).

**Success**: A user can sign up, log in (email or OAuth), recover expired sessions, edit their profile, invite teammates by email, manage member roles, and configure workspace settings — all through self-service UI without requiring direct database access or admin intervention.

---

## Stakeholders

| Stakeholder | Role | Interest | Input Needed | Review Point |
|-------------|------|----------|-------------|-------------|
| Tin Dang | Architect / Owner | Security correctness, clean architecture, RLS enforcement | Architecture decisions on auth delegation model | Spec + Plan review |
| Backend Dev | Implementer | Endpoint completeness, Supabase Auth integration, service layer patterns | Supabase Auth SDK capabilities, RLS policy gaps | Pre-plan review |
| Frontend Dev | Implementer | Settings page UX, auth flow reliability, MobX/TanStack patterns | Design system compliance, accessibility reqs | UI wireframe review |
| End Users | Consumer | Reliable login, easy team management, profile editing | Usability feedback on invitation flow | Acceptance test |

---

## User Scenarios & Testing

### User Story 1 — Reliable Authentication (Priority: P1)

A user opens Pilot Space and signs in using email/password or GitHub OAuth. After signing in, the user's session persists across page reloads. When the session token expires, the system silently refreshes it without interrupting the user's work. If the user explicitly logs out, they are returned to the login page and their session is invalidated.

**Why this priority**: Authentication is the gateway to every other feature. Broken OAuth callback and missing token refresh cause hard failures for every user. No other feature works without reliable auth.

**Independent Test**: Can be fully tested by creating an account, logging in via email and OAuth, waiting for token expiry, and verifying automatic session refresh — delivers standalone auth capability.

**Acceptance Scenarios**:

1. **Given** a new user on the login page, **When** they enter a valid email and password and click "Sign In", **Then** they are redirected to their default workspace and see the Notes list.
2. **Given** a new user on the login page, **When** they click "GitHub" OAuth button, **Then** they are redirected to GitHub for authorization, and upon approval, returned to their default workspace.
3. **Given** a user with a valid session whose access token has expired, **When** they make any request, **Then** the system automatically refreshes the token using the refresh token without user interaction.
4. **Given** a user with an expired refresh token, **When** they make any request, **Then** they are redirected to the login page with a message indicating session expiry.
5. **Given** a logged-in user, **When** they click "Logout", **Then** the session is invalidated, local tokens are cleared, and they see the login page.
6. **Given** a new user on the login page, **When** they click "Sign up" and fill in name, email, and password, **Then** an account is created and they are prompted to verify their email (if email confirmation is enabled) or redirected to workspace creation.

---

### User Story 2 — User Profile Management (Priority: P2)

An authenticated user navigates to their profile settings page. They can view their current profile (name, email, avatar) and update their display name and avatar. The email address is read-only (managed by the identity provider). Changes are saved immediately and reflected across the application.

**Why this priority**: Profile management is the foundation for identity within workspaces. Members need recognizable display names and avatars for collaboration features (assignments, mentions, activity logs). Blocked by P1 auth.

**Independent Test**: Can be tested by logging in, navigating to profile settings, changing the display name, and verifying the new name appears in the sidebar and member lists.

**Acceptance Scenarios**:

1. **Given** an authenticated user, **When** they navigate to profile settings, **Then** they see their current email (read-only), display name, and avatar.
2. **Given** a user on the profile settings page, **When** they update their display name and click save, **Then** the name is persisted and displayed across the application within 2 seconds.
3. **Given** a user on the profile settings page, **When** they upload a new avatar image, **Then** the image is stored, the avatar updates in the header and member lists, and the old avatar is no longer displayed.
4. **Given** a user updating their profile, **When** the save request fails due to a network error, **Then** the user sees an error message and their unsaved changes are preserved in the form.

---

### User Story 3 — Workspace Member Invitation (Priority: P2)

A workspace admin opens the Members settings page and invites a new member by entering their email address and selecting a role (member or admin). If the email belongs to an existing Pilot Space user, they are added immediately and see the workspace on their next page load. If the email does not match an existing user, the system records a pending invitation. The invited user receives a notification (or sees the invitation upon signup) and can accept it.

**Why this priority**: Without member invitation, workspaces are single-user silos. This is the core enabler for the 5-100 team member target scale. Blocked by P1 auth for the invited user's account.

**Independent Test**: Can be tested by creating a workspace, inviting a user by email, verifying the member appears in the members list (or as pending), and confirming the invited user can access the workspace.

**Acceptance Scenarios**:

1. **Given** a workspace admin on the Members page, **When** they enter a valid email address and select role "member", **Then** the invitation is sent/recorded and appears in the members list with a "pending" indicator (if user does not yet exist) or the user is added immediately.
2. **Given** an admin inviting an email that already belongs to a workspace member, **When** they submit the invitation, **Then** the system shows an error "User is already a member of this workspace".
3. **Given** a workspace admin, **When** they invite 5 members in quick succession, **Then** all invitations are processed without errors or duplicates.
4. **Given** a pending invitation, **When** the invited user signs up with the matching email and logs in, **Then** they automatically see the workspace in their workspace list.
5. **Given** a workspace admin, **When** they view the members list, **Then** they can distinguish between active members and pending invitations, and can cancel pending invitations.

---

### User Story 4 — Workspace Member Role Management (Priority: P2)

A workspace admin views the members list showing each member's name, email, role, and join date. The admin can change a member's role (owner, admin, member, guest) or remove a member from the workspace. Role changes take effect immediately. The system prevents removing the last owner/admin to avoid orphaned workspaces.

**Why this priority**: Role management enables access control governance. Without it, all members have equal permissions, which violates the RLS security model. Builds on US-3 member invitation.

**Independent Test**: Can be tested by adding multiple members to a workspace, changing roles, verifying permission enforcement (guest cannot edit, admin can manage members), and attempting to remove the last admin.

**Acceptance Scenarios**:

1. **Given** a workspace admin on the Members page, **When** they view the list, **Then** they see each member's avatar, name, email, role badge, and join date, sorted by role hierarchy then join date.
2. **Given** an admin viewing a member row, **When** they change the member's role from "member" to "admin" via the role dropdown (available roles: admin, member, guest), **Then** the role is updated immediately and the member gains admin capabilities on their next request. *Note: The "owner" role is not available in the dropdown — ownership transfer uses a separate explicit flow (see acceptance scenario #6).*
3. **Given** a workspace with a single admin, **When** the admin tries to remove themselves, **Then** the system shows "Cannot remove the only admin from workspace" and blocks the action.
4. **Given** a non-admin member, **When** they navigate to the Members page, **Then** they can see the member list but cannot change roles or remove members (action buttons are hidden or disabled).
5. **Given** an admin, **When** they remove a member, **Then** the member loses access to all workspace resources immediately and the workspace disappears from their workspace list.
6. **Given** a workspace owner, **When** they transfer ownership to another admin, **Then** the new owner gains full control and the previous owner is downgraded to admin.

---

### User Story 5 — Workspace General Settings (Priority: P3)

A workspace admin navigates to workspace general settings where they can update the workspace name, description, and slug. The admin can also view workspace metadata (creation date, member count, project count). Dangerous actions (delete workspace) require explicit confirmation.

**Why this priority**: Workspace settings are essential for long-term workspace lifecycle management but not required for initial team onboarding. Enhancement on top of P2 member management.

**Independent Test**: Can be tested by creating a workspace, navigating to general settings, renaming it, verifying the slug change is reflected in the URL, and testing workspace deletion with confirmation.

**Acceptance Scenarios**:

1. **Given** a workspace admin on general settings, **When** they update the workspace name, **Then** the name is persisted and reflected in the sidebar, header, and workspace list.
2. **Given** a workspace admin updating the slug, **When** the new slug is already taken by another workspace, **Then** the system shows "Slug already in use" and prevents the update.
3. **Given** a workspace admin clicking "Delete workspace", **When** they are prompted to type the workspace name for confirmation, **Then** upon correct confirmation the workspace is soft-deleted and all members lose access.
4. **Given** a non-admin member, **When** they navigate to workspace settings, **Then** they see workspace metadata in read-only mode with no edit controls.

---

### User Story 6 — Password Reset (Priority: P3)

A user who forgot their password clicks "Forgot password" on the login page. The system sends a password reset link to their email address. The user clicks the link, enters a new password, and can immediately log in with the new credentials.

**Why this priority**: Password reset is a standard auth hygiene feature. Without it, users with email/password auth who forget their password are permanently locked out. Not blocking for OAuth-only users.

**Independent Test**: Can be tested by requesting a password reset, receiving the email, clicking the link, setting a new password, and verifying login with the new password works.

**Acceptance Scenarios**:

1. **Given** a user on the login page, **When** they click "Forgot password" and enter their email, **Then** a password reset email is sent within 30 seconds.
2. **Given** a user with a reset email, **When** they click the reset link within 1 hour, **Then** they see a form to enter a new password.
3. **Given** a user with a reset link older than 1 hour, **When** they click it, **Then** they see "Link expired" and can request a new one.
4. **Given** a non-existent email submitted for password reset, **When** the system processes it, **Then** no email is sent but the user sees the same success message (no email enumeration).

---

### Edge Cases

- What happens when a user signs up with an email that already exists? System shows "Account already exists" and suggests login.
- What happens when the OAuth provider is unavailable? User sees an error message suggesting email/password login as fallback.
- What happens when a user is removed from a workspace while actively working? Their next request returns 403, and the frontend redirects to the workspace list with a notification.
- What happens when an admin invites themselves? System shows "You are already a member".
- What happens when a workspace has only one member (the owner) and they leave? System prevents the action — owner must transfer ownership or delete the workspace.
- What happens when two admins simultaneously change the same member's role? Last-write-wins; the second update overwrites the first with a notification to both admins.
- What happens when a user has pending invitations to multiple workspaces? All workspaces appear in their workspace list upon login with the option to accept or decline each.
- What happens when a user tries to set a display name exceeding 255 characters? The form validates and truncates/rejects before submission.

---

## Requirements

### Functional Requirements

**Authentication (Phase 1)**

- **FR-001**: System MUST authenticate users via email/password credentials so that users can access their workspaces without third-party dependencies.
- **FR-002**: System MUST authenticate users via OAuth providers (GitHub) so that users can log in with existing accounts.
- **FR-003**: System MUST automatically refresh expired access tokens using a valid refresh token so that users are not interrupted during active sessions.
- **FR-004**: System MUST redirect users to the login page when both access and refresh tokens are expired so that stale sessions cannot access protected resources.
- **FR-005**: System MUST invalidate the current session upon user-initiated logout so that shared devices are secured.
- **FR-006**: System MUST create a new user record upon first successful authentication so that the user exists in the application database.
- **FR-007**: System MUST assign the "owner" role to the user who creates a workspace so that workspace ownership is unambiguous.

**Profile Management (Phase 2)**

- **FR-008**: Users MUST be able to view their current profile information (email, display name, avatar) so that they can verify their identity.
- **FR-009**: Users MUST be able to update their display name so that they are recognizable to teammates.
- **FR-010**: Users MUST be able to update their avatar image so that their visual identity is consistent across the platform.
- **FR-011**: System MUST display the user's email as read-only so that email changes are managed through the identity provider.
- **FR-012**: System MUST persist profile changes within 2 seconds of submission so that updates feel immediate.

**Member Management (Phase 2)**

- **FR-013**: Workspace admins MUST be able to view the complete member list with name, email, role, and join date so that they understand workspace composition.
- **FR-014**: Workspace admins MUST be able to invite new members by email address so that teams can grow.
- **FR-015**: System MUST add existing users to the workspace immediately upon invitation so that they can start collaborating without delay.
- **FR-016**: System MUST record pending invitations for non-existent users so that they gain access upon signup.
- **FR-017**: Workspace admins MUST be able to change a member's role (owner, admin, member, guest) so that access levels can be adjusted.
- **FR-018**: Workspace admins MUST be able to remove members from the workspace so that departed team members lose access.
- **FR-019**: System MUST prevent removing the last admin/owner from a workspace so that workspaces cannot become orphaned.
- **FR-020**: Non-admin members MUST be able to view the member list in read-only mode so that they know who is on the team.
- **FR-021**: Members MUST be able to remove themselves from a workspace (except the last admin/owner) so that they can leave teams voluntarily.

**Workspace Settings (Phase 3)**

- **FR-022**: Workspace admins MUST be able to update the workspace name and description so that workspace metadata stays current.
- **FR-023**: Workspace admins MUST be able to update the workspace slug with uniqueness validation so that workspace URLs can be changed.
- **FR-024**: Workspace admins MUST be able to delete a workspace with explicit confirmation so that unused workspaces can be cleaned up.
- **FR-025**: System MUST soft-delete workspaces so that accidental deletions can be recovered.
- **FR-026**: Non-admin members MUST see workspace settings in read-only mode so that they understand workspace configuration.

**Password Reset (Phase 3)**

- **FR-027**: Users MUST be able to request a password reset by email so that forgotten passwords do not lock users out.
- **FR-028**: System MUST send password reset links that expire after 1 hour so that stale reset links cannot be used.
- **FR-029**: System MUST NOT reveal whether an email exists in the system during password reset so that email enumeration attacks are prevented.
- **FR-030**: Users MUST be able to set a new password using a valid reset link so that they can regain account access.

**Security (Cross-cutting)**

- **FR-031**: System MUST enforce workspace-level data isolation so that users cannot access resources from workspaces they do not belong to.
- **FR-032**: System MUST enforce role-based permissions so that guests cannot perform write operations and only admins can manage members.
- **FR-033**: System MUST log all authentication events (login, logout, token refresh, password reset) so that security audits are possible.

### Key Entities

- **User**: A person with an account. Key attributes: email (unique), display name, avatar URL, creation timestamp. Relationships: belongs to many Workspaces through Membership.
- **Workspace**: A collaborative container for projects and content. Key attributes: name, slug (unique), description, owner reference, settings, creation timestamp. Relationships: has many Members, has many Projects.
- **Membership**: The relationship between a User and a Workspace. Key attributes: role (owner/admin/member/guest), join timestamp, status (active/pending). Relationships: belongs to one User, belongs to one Workspace. Unique constraint: one membership per user per workspace.
- **Invitation**: A pending request to join a workspace (for users who don't yet exist). Key attributes: email, intended role, expiry timestamp, inviter reference, status (pending/accepted/expired/cancelled). Relationships: belongs to one Workspace.
- **AuthEvent**: A record of authentication activity. Key attributes: event type (login/logout/refresh/reset), user reference, timestamp, IP address, outcome (success/failure). Relationships: belongs to one User. *Note: This is a logical entity fulfilled by Supabase Auth's built-in audit log — no custom table required.*

---

## Success Criteria

- **SC-001**: 95% of users complete the sign-up-to-workspace flow (register, create/join workspace) within 3 minutes on first attempt.
- **SC-002**: Token refresh succeeds transparently in 99.5% of cases without user-visible interruption.
- **SC-003**: Member invitation-to-access latency is under 5 seconds for existing users and under 30 seconds for new signups (excluding email delivery time).
- **SC-004**: System handles 100 concurrent authentication requests without error rate exceeding 0.1%.
- **SC-005**: Zero cross-workspace data leakage incidents confirmed through integration tests covering all member management endpoints.
- **SC-006**: Profile updates reflect across all UI surfaces within 2 seconds of save confirmation.
- **SC-007**: Password reset email delivery completes within 30 seconds of request.
- **SC-008**: All settings pages achieve WCAG 2.2 AA compliance (4.5:1 contrast, keyboard navigable, screen reader compatible).

---

## Constitution Compliance

| Principle | Applies? | How Addressed |
|-----------|----------|--------------|
| I. AI-Human Collaboration | No | User management is non-AI functionality. No approval flows needed. |
| II. Note-First | No | User management is infrastructure, not content workflow. |
| III. Documentation-Third | No | Not applicable to user management. |
| IV. Task-Centric | Yes | Each user story is independently testable and decomposable into tasks. |
| V. Collaboration | Yes | Member invitation and role management are direct enablers of team collaboration. |
| VI. Agile Integration | Yes | Stories are prioritized P1-P3 and fit sprint planning. Phase 1 can ship independently. |
| VII. Notation Standards | No | No diagrams required for user management spec. |

---

## Validation Checklists

### Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Every user story has acceptance scenarios with Given/When/Then
- [x] Every story is independently testable and demo-able
- [x] Edge cases documented for each story
- [x] All entities have defined relationships

### Specification Quality

- [x] Focus is WHAT/WHY, not HOW
- [x] No technology names anywhere in requirements
- [x] Requirements use RFC 2119 keywords (MUST/SHOULD/MAY)
- [x] Success criteria are measurable with numbers/thresholds
- [x] Written for business stakeholders, not developers
- [x] One capability per FR line (no compound requirements)

### Structural Integrity

- [x] Stories prioritized P1 through P3
- [x] Functional requirements numbered sequentially (FR-001 through FR-033)
- [x] Key entities identified with attributes and relationships
- [x] No duplicate or contradicting requirements
- [x] Problem statement clearly defines WHO/PROBLEM/IMPACT/SUCCESS

### Constitution Gate

- [x] All applicable principles checked and addressed
- [x] No violations

---

## Codebase Gap Analysis

The following table maps each phase to existing vs missing implementation, based on the current codebase audit:

| Phase | What Exists | What's Missing |
|-------|------------|----------------|
| **P1: Auth** | User model, SupabaseAuth JWT validation (ES256/HS256), login page (email+GitHub), AuthStore (MobX), `/auth/me` + `/auth/me` PATCH endpoints, `/auth/logout` | OAuth callback (501), token refresh (501), workspace creation assigns ADMIN instead of OWNER, no email verification flow |
| **P2: Profile + Members** | UserRepository (get_by_email, search, get_or_create), WorkspaceMember model with role enum, `GET /workspaces/{id}/members`, `PATCH /workspaces/{id}/members/{uid}`, `DELETE /workspaces/{id}/members/{uid}`, `useWorkspaceMembers` hook | `POST /workspaces/{id}/members` invitation (501), no Invitation entity, no frontend profile page, no frontend members settings page, no pending invitation tracking |
| **P3: Settings + Reset** | WorkspaceUpdate schema, `PATCH /workspaces/{id}`, `DELETE /workspaces/{id}`, AI settings page (frontend) | No frontend workspace general settings page, no password reset flow, no slug-change UI, no workspace deletion confirmation UI |

---

## Next Phase

After this spec passes all checklists:

1. **Proceed to planning** — Use `template-plan.md` to create the implementation plan with architecture decisions, data model changes, and endpoint contracts.
2. **Share for review** — This spec is the alignment artifact for all stakeholders.
3. **Resolve auth delegation model** — Decide whether OAuth callback/token refresh should be server-side or fully delegated to the Supabase client SDK (currently the code comments suggest client-side).
