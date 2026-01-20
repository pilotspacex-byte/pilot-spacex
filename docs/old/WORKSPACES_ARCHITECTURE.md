# Workspaces Feature - Comprehensive Architecture Documentation

## Overview

The Workspaces feature is the foundational multi-tenancy layer in Plane that enables organizations to create isolated collaboration spaces. Each workspace is an autonomous unit with its own members, projects, cycles, modules, and settings. Workspaces implement role-based access control, invite workflows, and member management capabilities.

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Endpoints](#api-endpoints)
3. [Business Logic & RBAC](#business-logic--rbac)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow](#data-flow)
6. [Security & Permissions](#security--permissions)

---

## Data Models

### Workspace Model

**File**: `apps/api/plane/db/models/workspace.py`

```python
class Workspace(BaseModel):
    name = CharField(max_length=80)
    logo = TextField(blank=True, null=True)
    logo_asset = ForeignKey(FileAsset, null=True)
    owner = ForeignKey(User)
    slug = SlugField(max_length=48, unique=True)
    organization_size = CharField(max_length=20)
    timezone = CharField(default="UTC")
    background_color = CharField(default=get_random_color)
```

**Key Properties**:
- `logo_url`: Computed property returning logo_asset URL or logo string
- **Soft Delete Support**: Appends epoch timestamp to slug on deletion

**Constraints**:
- Slug must not be in `RESTRICTED_WORKSPACE_SLUGS`
- Name length: 1-80 characters
- Slug length: 1-48 characters

### WorkspaceMember Model

```python
class WorkspaceMember(BaseModel):
    workspace = ForeignKey(Workspace, CASCADE)
    member = ForeignKey(User, CASCADE)
    role = PositiveSmallIntegerField(choices=ROLE_CHOICES, default=5)
    company_role = TextField(null=True)
    view_props = JSONField(default=get_default_props)
    default_props = JSONField(default=get_default_props)
    issue_props = JSONField(default=get_issue_props)
    is_active = BooleanField(default=True)
    getting_started_checklist = JSONField(default=dict)
    tips = JSONField(default=dict)
    explored_features = JSONField(default=dict)
```

**Role Constants**:
```python
ROLE_CHOICES = (
    (20, "Admin"),      # Full workspace control
    (15, "Member"),     # Can create/edit projects and issues
    (5, "Guest"),       # Read-only access
)
```

### WorkspaceMemberInvite Model

```python
class WorkspaceMemberInvite(BaseModel):
    workspace = ForeignKey(Workspace, CASCADE)
    email = CharField(max_length=255)
    accepted = BooleanField(default=False)
    token = CharField(max_length=255)  # JWT token
    message = TextField(null=True)
    responded_at = DateTimeField(null=True)
    role = PositiveSmallIntegerField(choices=ROLE_CHOICES, default=5)
```

**JWT Token Structure**:
```python
{
    "email": email,
    "timestamp": datetime.now().timestamp()
}
# Encoded with settings.SECRET_KEY using HS256
```

### Related Models

- **Team**: Groups of workspace members for bulk operations
- **WorkspaceTheme**: Custom workspace themes
- **WorkspaceUserProperties**: Per-user view preferences
- **WorkspaceHomePreference**: Home widget configuration
- **WorkspaceUserPreference**: Sidebar pin preferences

---

## API Endpoints

### Workspace CRUD

**Base Path**: `/api/workspaces/`

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/workspaces/` | Authenticated | List user's workspaces |
| POST | `/workspaces/` | Authenticated | Create new workspace |
| GET | `/workspaces/{slug}/` | Member/Admin | Get workspace details |
| PATCH | `/workspaces/{slug}/` | Admin | Update workspace settings |
| DELETE | `/workspaces/{slug}/` | Admin | Soft-delete workspace |

### Member Management

**Base Path**: `/api/workspaces/{slug}/members/`

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/members/` | Any member | List workspace members |
| GET | `/members/{id}/` | Any member | Get member details |
| PATCH | `/members/{id}/` | Admin | Update member role |
| DELETE | `/members/{id}/` | Admin | Remove member |
| POST | `/members/leave/` | Any member | Leave workspace |

**Update Member Role Logic**:
- Cannot update own role
- If demoting to Guest (role=5), all project roles downgraded
- Requesting user must have higher or equal role

### Invitation Workflow

**Base Path**: `/api/workspaces/{slug}/invitations/`

| Method | Path | Permission | Purpose |
|--------|------|------------|---------|
| GET | `/invitations/` | Admin | List pending invites |
| POST | `/invitations/` | Admin | Bulk invite users |
| GET | `/invitations/{id}/` | Admin | Get invite details |
| PATCH | `/invitations/{id}/` | Admin | Update invite |
| DELETE | `/invitations/{id}/` | Admin | Revoke invite |
| POST | `/invitations/{id}/join/` | Invited user | Accept/decline invite |

**Invite Users Request**:
```json
{
  "emails": [
    { "email": "alice@example.com", "role": 15 },
    { "email": "bob@example.com", "role": 5 }
  ]
}
```

**Invite Logic**:
1. Validate all email addresses
2. Check no target users already members
3. Verify inviter role >= all invitee roles
4. Create `WorkspaceMemberInvite` records
5. Enqueue `workspace_invitation` email task

---

## Business Logic & RBAC

### Role-Based Access Control

**File**: `apps/api/plane/app/permissions/workspace.py`

| Role | Level | Permissions |
|------|-------|-------------|
| **Admin** | 20 | Create/edit workspaces, invite members, manage roles, delete |
| **Member** | 15 | Create projects, create/edit issues, invite to projects |
| **Guest** | 5 | Read-only access to projects they're added to |

**Permission Classes**:

```python
class WorkSpaceBasePermission:
    # POST: Anyone authenticated can create
    # GET/SAFE: All members can view
    # PUT/PATCH: Admin or Member can update
    # DELETE: Only Admin can delete

class WorkspaceEntityPermission:
    # GET/SAFE: Any active member can view
    # Modifications: Admin or Member only

class WorkspaceOwnerPermission:
    # Only Admin (role=20) can access
```

### Workspace Seeding

When workspace is created, `workspace_seed` task initializes:
1. Default states (Backlog, Todo, In Progress, Done)
2. Default project (optional)
3. Default labels
4. System configurations

### Invitation Flow

```
Admin invites user@example.com
    ↓
Create WorkspaceMemberInvite
    ├─ Generate JWT token
    └─ Store with role and workspace
    ↓
Send email with invitation link
    ↓
User clicks link and signs up/logs in
    ↓
POST /invitations/{id}/join/ with acceptance
    ↓
If Accepted:
    ├─ Create/activate WorkspaceMember
    ├─ Set role from invite
    └─ Set last_workspace_id
```

---

## Frontend Architecture

### TypeScript Types

**File**: `packages/types/src/workspace.ts`

```typescript
interface IWorkspace {
  readonly id: string;
  readonly owner: IUser;
  name: string;
  logo_url: string | null;
  readonly total_members: number;
  readonly slug: string;
  organization_size: string;
  role: number;  // User's role in this workspace
  timezone: string;
}

interface IWorkspaceMember {
  id: string;
  member: IUserLite;
  role: EUserWorkspaceRoles;
  is_active?: boolean;
}

interface IWorkspaceMemberInvitation {
  accepted: boolean;
  email: string;
  id: string;
  role: TUserPermissions;
  token: string;
  workspace: {
    id: string;
    logo_url: string;
    name: string;
    slug: string;
  };
}

enum EUserWorkspaceRoles {
  ADMIN = 20,
  MEMBER = 15,
  GUEST = 5,
}
```

### Workspace Service

**File**: `apps/web/core/services/workspace.service.ts`

```typescript
class WorkspaceService extends APIService {
  // Workspaces
  async userWorkspaces(): Promise<IWorkspace[]>
  async getWorkspace(workspaceSlug: string): Promise<IWorkspace>
  async createWorkspace(data: Partial<IWorkspace>): Promise<IWorkspace>
  async updateWorkspace(workspaceSlug: string, data): Promise<IWorkspace>
  async deleteWorkspace(workspaceSlug: string): Promise<any>

  // Members
  async fetchWorkspaceMembers(workspaceSlug: string): Promise<IWorkspaceMember[]>
  async updateWorkspaceMember(workspaceSlug, memberId, data): Promise<IWorkspaceMember>
  async deleteWorkspaceMember(workspaceSlug, memberId): Promise<any>

  // Invitations
  async inviteWorkspace(workspaceSlug, data): Promise<any>
  async joinWorkspace(workspaceSlug, invitationId, data): Promise<any>
  async workspaceInvitations(workspaceSlug): Promise<IWorkspaceMemberInvitation[]>
}
```

### MobX Stores

#### Workspace Root Store

**File**: `apps/web/core/store/workspace/index.ts`

```typescript
interface IWorkspaceRootStore {
  // Observables
  loader: boolean;
  workspaces: Record<string, IWorkspace>;
  navigationPreferencesMap: Record<string, IWorkspaceSidebarNavigation>;

  // Computed
  currentWorkspace: IWorkspace | null;
  workspacesCreatedByCurrentUser: IWorkspace[] | null;

  // Actions
  fetchWorkspaces(): Promise<IWorkspace[]>;
  createWorkspace(data: Partial<IWorkspace>): Promise<IWorkspace>;
  updateWorkspace(workspaceSlug: string, data): Promise<IWorkspace>;
  deleteWorkspace(workspaceSlug: string): Promise<void>;
}
```

#### Workspace Member Store

**File**: `apps/web/core/store/member/workspace/workspace-member.store.ts`

```typescript
interface IWorkspaceMemberStore {
  // Observables
  workspaceMemberMap: Record<string, Record<string, IWorkspaceMembership>>;
  workspaceMemberInvitations: Record<string, IWorkspaceMemberInvitation[]>;

  // Computed
  workspaceMemberIds: string[] | null;
  memberMap: Record<string, IWorkspaceMembership> | null;

  // Actions
  fetchWorkspaceMembers(workspaceSlug: string): Promise<IWorkspaceMember[]>;
  fetchWorkspaceMemberInvitations(workspaceSlug): Promise<IWorkspaceMemberInvitation[]>;
  updateMember(workspaceSlug, userId, data): Promise<void>;
  removeMemberFromWorkspace(workspaceSlug, userId): Promise<void>;
  inviteMembersToWorkspace(workspaceSlug, data): Promise<void>;
}
```

---

## Data Flow

### Initialization Flow

```
User opens app
    ↓
WorkspaceRootStore.fetchWorkspaces()
    ↓ GET /api/users/me/workspaces/
    ↓
Populate workspaces observable
    ├─ workspaceRoot.workspaces[id] = workspace
    └─ Set currentWorkspace based on URL slug
    ↓
WorkspaceMemberStore.fetchWorkspaceMembers(slug)
    ↓ GET /api/workspaces/{slug}/members/
    ↓
Populate memberMap
```

### Workspace Switching Flow

```
User clicks workspace in sidebar
    ↓
Router.setWorkspaceSlug(slug)
    ↓
UI re-renders with new workspaceSlug
    ↓
Effect triggers:
    ├─ Fetch members for new workspace
    ├─ Fetch sidebar preferences
    └─ Fetch projects, cycles, modules
```

### Inviting User Flow

```
Admin fills invite form
    ↓
WorkspaceMemberStore.inviteMembersToWorkspace()
    ↓
WorkspaceService.inviteWorkspace()
    ↓ POST /api/workspaces/{slug}/invitations/
    ↓
Backend:
    ├─ Validates emails
    ├─ Creates WorkspaceMemberInvite records
    └─ Enqueues email task
    ↓
Frontend:
    ├─ Fetch invitations list
    └─ Show confirmation toast
```

### Member Joining Flow

```
Invited user receives email
    ↓
User clicks link
    ↓
InvitationAcceptModal
    ↓
WorkspaceService.joinWorkspace()
    ↓ POST /api/workspaces/{slug}/invitations/{id}/join/
    ↓
Backend:
    ├─ Creates/activates WorkspaceMember
    ├─ Sets user.last_workspace_id
    └─ Tracks event
    ↓
Frontend:
    ├─ Add workspace to store
    └─ Redirect to workspace
```

---

## Security & Permissions

### Permission Hierarchy

```
Workspace Owner (Implicit Admin)
├─ Full workspace control
├─ Edit workspace settings
├─ Delete workspace
├─ Invite/remove members
└─ Access all projects

Admin (role=20)
├─ Invite/remove members
├─ Assign roles
├─ Create projects
└─ Full project access

Member (role=15)
├─ Create projects
├─ Invite to projects
└─ Project-scoped access

Guest (role=5)
└─ Read-only project access
```

### Invite Token Security

```python
token = jwt.encode(
    {
        "email": email_dict,
        "timestamp": datetime.now().timestamp()
    },
    settings.SECRET_KEY,
    algorithm="HS256"
)
```

### Validation Rules

**Invite Operations**:
- Cannot invite users with higher role than inviter
- Cannot invite existing members
- Email addresses must be valid
- Cannot delete accepted invites

**Member Operations**:
- Cannot change own role
- Cannot remove higher-role members
- Cannot remove sole admin
- Cannot remove sole project admin

---

## State Management & Caching

### Observable State Structure

```typescript
// WorkspaceRootStore
{
    workspaces: {
        "workspace-1-id": { ... },
        "workspace-2-id": { ... }
    },
    navigationPreferencesMap: {
        "eng-team": { "issues": { is_pinned: true }, ... }
    }
}

// MemberRootStore
{
    workspace: {
        workspaceMemberMap: {
            "eng-team": {
                "user-1-id": { role: 20, is_active: true },
                "user-2-id": { role: 15, is_active: true }
            }
        },
        workspaceMemberInvitations: {
            "eng-team": [
                { email: "alice@...", role: 15, ... }
            ]
        }
    }
}
```

### Optimistic Updates

```typescript
const beforeUpdateData = clone(this.workspaceMemberMap[slug][userId]);
try {
    // Optimistic update
    runInAction(() => {
        set(this.workspaceMemberMap, [slug, userId, "role"], newRole);
    });
    // API call
    await this.workspaceService.updateWorkspaceMember(...);
} catch (error) {
    // Revert on failure
    runInAction(() => {
        set(this.workspaceMemberMap, [slug, userId], beforeUpdateData);
    });
    throw error;
}
```

---

## File Reference Map

| Component | File Path |
|-----------|-----------|
| Models | `apps/api/plane/db/models/workspace.py` |
| Backend Views | `apps/api/plane/app/views/workspace/` |
| Member Views | `apps/api/plane/app/views/workspace/member.py` |
| Invite Views | `apps/api/plane/app/views/workspace/invite.py` |
| Permissions | `apps/api/plane/app/permissions/workspace.py` |
| Frontend Service | `apps/web/core/services/workspace.service.ts` |
| Workspace Store | `apps/web/core/store/workspace/index.ts` |
| Member Store | `apps/web/core/store/member/workspace/workspace-member.store.ts` |
| Types | `packages/types/src/workspace.ts` |
