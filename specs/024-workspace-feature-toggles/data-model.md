# Data Model: Workspace Feature Toggles

**Feature Branch**: `024-workspace-feature-toggles`
**Created**: 2026-03-18

---

## Storage: JSONB in `workspace.settings`

No new database tables or migrations required. Feature toggles are stored in the existing `workspace.settings` JSONB column under the key `feature_toggles`.

### JSONB Structure

```json
{
  "ai_features": { ... },              // Existing AI feature toggles
  "feature_toggles": {                  // NEW — Sidebar feature toggles
    "notes": true,
    "issues": false,
    "projects": false,
    "members": true,
    "docs": false,
    "skills": true,
    "costs": false,
    "approvals": false
  },
  "default_llm_provider": "...",        // Existing
  "default_embedding_provider": "...",  // Existing
  "ai_cost_limit_usd": 100.0           // Existing
}
```

---

## Backend Schema: `WorkspaceFeatureToggles`

Pydantic schema that validates and provides defaults for feature toggles.

```python
class WorkspaceFeatureToggles(BaseSchema):
    """Workspace-level sidebar feature toggles.

    Controls which sidebar modules are visible and accessible
    to all members of the workspace.
    """
    notes: bool = Field(default=True, description="Notes module")
    issues: bool = Field(default=False, description="Issue tracker module")
    projects: bool = Field(default=False, description="Project management module")
    members: bool = Field(default=True, description="Member directory module")
    docs: bool = Field(default=False, description="Documentation module")
    skills: bool = Field(default=True, description="AI Skills module")
    costs: bool = Field(default=False, description="AI cost tracking module")
    approvals: bool = Field(default=False, description="AI approval workflow module")
```

### Update Schema

```python
class WorkspaceFeatureTogglesUpdate(BaseSchema):
    """Partial update for feature toggles. Only provided fields are updated."""
    notes: bool | None = None
    issues: bool | None = None
    projects: bool | None = None
    members: bool | None = None
    docs: bool | None = None
    skills: bool | None = None
    costs: bool | None = None
    approvals: bool | None = None
```

---

## Frontend Type: `WorkspaceFeatureToggles`

```typescript
interface WorkspaceFeatureToggles {
  notes: boolean;
  issues: boolean;
  projects: boolean;
  members: boolean;
  docs: boolean;
  skills: boolean;
  costs: boolean;
  approvals: boolean;
}

// Defaults (used when API returns null/undefined)
const DEFAULT_FEATURE_TOGGLES: WorkspaceFeatureToggles = {
  notes: true,
  issues: false,
  projects: false,
  members: true,
  docs: false,
  skills: true,
  costs: false,
  approvals: false,
};
```

---

## Feature-to-Sidebar Mapping

| Feature Key  | Sidebar Path | Section | NavItem `featureKey` |
|-------------|-------------|---------|---------------------|
| `notes`     | `/notes`    | Main    | `notes`             |
| `issues`    | `/issues`   | Main    | `issues`            |
| `projects`  | `/projects` | Main    | `projects`          |
| `members`   | `/members`  | Main    | `members`           |
| `docs`      | `/docs`     | Main    | `docs`              |
| `skills`    | `/skills`   | AI      | `skills`            |
| `costs`     | `/costs`    | AI      | `costs`             |
| `approvals` | `/approvals`| AI      | `approvals`         |

Non-toggleable: `Home` (path: ``), `Chat` (path: `chat`), `Settings` (path: `settings`).

---

## Feature-to-AI Mapping

### Skill → Feature Module

| Skill Name | Feature Module(s) |
|-----------|-------------------|
| summarize | notes |
| create-note-from-chat | notes |
| generate-digest | notes |
| improve-writing | notes |
| extract-issues | issues |
| enhance-issue | issues |
| find-duplicates | issues |
| recommend-assignee | issues, members |
| decompose-tasks | projects |
| generate-pm-blocks | projects |
| speckit-pm-guide | projects |
| sprint-planning | projects |
| generate-diagram | docs |
| adr-lite | docs |
| generate-code | docs |

### MCP Server → Feature Module

| MCP Server | Feature Module |
|-----------|---------------|
| note_server | notes |
| note_content_server | notes |
| note_query_server | notes |
| ownership_server | notes |
| issue_server | issues |
| issue_relation_server | issues |
| project_server | projects |
| comment_server | (always enabled — cross-cutting) |
| github_server | (always enabled — cross-cutting) |
| interaction_server | (always enabled — cross-cutting) |

### Multi-Module Skill Rule

Skills with multiple `feature_module` values are disabled only when **ALL** listed modules are toggled off. If any one module is enabled, the skill remains available.

Example: `recommend-assignee` has `feature_module: [issues, members]`. It is disabled only when both `issues=false` AND `members=false`.

---

## State Transitions

Feature toggles have a simple boolean state — no complex transitions:

```
Enabled ←→ Disabled
```

Toggling a feature:
1. Does NOT delete or modify underlying data
2. Does NOT affect data created while the feature was enabled
3. Re-enabling restores full access to all prior data
