# Settings Module

_For project overview, see main `CLAUDE.md` and `frontend/CLAUDE.md`_

## Purpose

Workspace configuration with strict role-based access control: workspace general settings, member management, AI provider configuration (BYOK), user profile, and AI skills.

**Design Decisions**: DD-061 (Supabase Auth + RLS), DD-065 (state split), DD-088 (MCP tools)

---

## Pages & Routes

| Route                    | Page                         | Purpose                                      |
| ------------------------ | ---------------------------- | -------------------------------------------- |
| `/settings`              | `workspace-general-page.tsx` | Name, slug, description, delete (owner-only) |
| `/settings/profile`      | `profile-settings-page.tsx`  | Display name, avatar, email                  |
| `/settings/members`      | `members-settings-page.tsx`  | Invite, remove, change roles                 |
| `/settings/ai-providers` | `ai-settings-page.tsx`       | API keys, feature toggles, provider status   |
| `/settings/skills`       | `skills-settings-page.tsx`   | Role-based AI skills (max 3 per workspace)   |

---

## Key Components

- **APIKeyForm**: Manage Anthropic + OpenAI keys (encrypted via Supabase Vault)
- **MemberRow**: Single member with role selector
- **InviteMemberDialog**: Email + role selection
- **AIFeatureToggles**: 5 switches (ghost text, annotations, context, extraction, PR review)
- **DeleteWorkspaceDialog**: Confirmation with exact name entry (owner-only)
- **SkillCard**: Display skill with edit/regenerate/remove

---

## Permission Model

| Role   | Workspace  | Members               | AI Settings | Skills    | Delete |
| ------ | ---------- | --------------------- | ----------- | --------- | ------ |
| Owner  | Full       | Manage all            | Full        | Full      | Yes    |
| Admin  | Full       | Manage (except owner) | Full        | Full      | No     |
| Member | Read/Write | View                  | View/toggle | Full      | No     |
| Guest  | Read-only  | View                  | View        | No access | No     |

Permission checks: `workspaceStore.isAdmin` (admin OR owner), `workspaceStore.isOwner` (owner only). Backend enforces via RLS policies.

---

## State Management

**MobX Stores**:

- `rootStore.ai.settings` (AISettingsStore): settings, isLoading, isSaving, loadSettings, saveSettings, validateKey
- `rootStore.workspace` (WorkspaceStore): currentUserRole, isAdmin, isOwner, updateMemberRole, removeMember, inviteMember
- `rootStore.auth` (AuthStore): user, updateProfile

**TanStack Query Hooks**: `useWorkspaceSettings()`, `useUpdateWorkspaceSettings()`, `useWorkspaceMembers()`, `useWorkspaceInvitations()`, `useRoleSkills()`. Stale time: 60 seconds.

---

## Functionality

**Workspace General**: Edit name/slug/description (admin+), view metadata (all), delete with name confirmation (owner). Slug validation: `^[a-z0-9]+(?:-[a-z0-9]+)*$`.

**Members**: List sorted by role hierarchy. Admin+ can change roles (except owner/self), remove (except owner/self), transfer ownership (owner-only), invite by email.

**AI Providers**: Status cards per provider, API key input with validation (Anthropic: `sk-ant-*`, OpenAI: `sk-*`, min 10 chars), 5 feature toggles. See `ai-settings-page.tsx`.

**Profile**: Display name (editable), avatar and email (read-only).

**Skills**: Max 3 per workspace. Create from template + AI generation, edit with word count, regenerate from description, reset/remove.

---

## Related Documentation

- `docs/architect/rls-patterns.md`
- `docs/dev-pattern/45-pilot-space-patterns.md`
