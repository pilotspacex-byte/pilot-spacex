# Phase 17: Skill Action Buttons - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Workspace admins can define custom action buttons on the issue detail page, each bound to a workspace skill (role skill or plugin skill) or a registered remote MCP tool. Clicking a button opens the chat panel with the issue context pre-loaded and the bound skill/tool activated. Destructive actions go through the existing AI approval gate (DD-003).

This phase does NOT include: per-project button scoping, role-based button visibility filtering, button analytics, or inline (non-chat) execution of skills.

</domain>

<decisions>
## Implementation Decisions

### Button Placement & Layout
- Horizontal action bar above the editor content area, below the issue header/title
- Max 3 buttons visible; overflow into a "More" dropdown (Lucide `MoreHorizontal` icon)
- Visual: shadcn/ui `Button` with `variant="secondary"` and `size="sm"`, optional Lucide icon + text label
- Action bar hidden when no buttons are defined for the workspace (no empty container)

### Admin Configuration UX
- New "Action Buttons" tab or subsection inside Settings → Skills page (alongside Workspace Skills and Plugins tabs)
- "Add Button" opens a form: name (required), icon (optional Lucide icon picker or text input), binding type (Skill or MCP Tool), then a dropdown to select the target
- Skill dropdown lists: active workspace role skills (WorkspaceRoleSkill where is_active=true) + active installed plugin skills (WorkspacePlugin where is_active=true)
- MCP Tool dropdown lists: tools from registered MCP servers (WorkspaceMcpServer) — display as "ServerName / ToolName"
- Drag-and-drop reordering via `sort_order` integer column
- Admin can toggle buttons active/inactive without deleting

### Chat Activation Behavior
- Clicking a button always starts a **new chat session** (never reuses existing)
- Issue context pre-loaded via `PilotSpaceStore.setIssueContext()` (issueId, projectId, title, description)
- Bound skill/tool activated via `PilotSpaceStore.setActiveSkill(skillName, args)`
- Auto-generated initial prompt sent immediately: "Run [Button Name] on this issue"
- Chat panel opens if not already open

### Button Visibility & Ordering
- All workspace members see all defined action buttons (no role-based filtering)
- Display order determined by admin-defined `sort_order` (ascending)
- Buttons with is_active=false are hidden from issue page but visible (greyed) in admin config

### Data Model
- New `SkillActionButton` model extending `WorkspaceScopedModel`
- Columns: `name` (String 100), `icon` (String 50, nullable), `binding_type` (Enum: SKILL, MCP_TOOL), `binding_id` (UUID, nullable — references skill/plugin/MCP server), `binding_metadata` (JSONB — stores tool_name for MCP, skill_name and source for skills), `sort_order` (Integer, default 0), `is_active` (Boolean, default true)
- Partial unique index on (workspace_id, name) WHERE is_deleted = false — prevents duplicate button names
- RLS policies: workspace isolation + service_role bypass (standard pattern)

### Plugin Action Button Wiring
- When a plugin includes action_button definitions in its metadata, installing the plugin auto-creates SkillActionButton rows
- Uninstalling/deactivating a plugin deactivates its associated action buttons
- Plugin-sourced buttons have `binding_metadata.source = "plugin"` and `binding_metadata.plugin_id` for traceability

### Claude's Discretion
- Exact Lucide icon picker implementation (simple text input vs visual picker)
- Drag-and-drop library choice for reordering (or simple up/down arrows)
- Exact initial prompt wording template
- Error handling when bound skill/tool no longer exists (show disabled button with tooltip)
- Migration number (next sequential after current head)

</decisions>

<specifics>
## Specific Ideas

- Button bar should feel lightweight — not a toolbar, more like GitHub's issue action links
- "More" overflow should use shadcn/ui DropdownMenu for consistency
- When a bound skill/MCP tool is deleted or deactivated, the button should show as disabled with a tooltip explaining why, not silently disappear

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PilotSpaceStore.setActiveSkill(skill, args)`: Already supports activating a skill in chat context
- `PilotSpaceStore.setIssueContext()`: Already injects issue context into chat sessions
- `ChatView` component with `initialPrompt` prop: Auto-sends first message on mount
- `WorkspaceScopedModel`: Base model with workspace_id FK, soft-delete, timestamps
- `Button` (shadcn/ui): Existing secondary/sm variants for action buttons
- `DropdownMenu` (shadcn/ui): For "More" overflow menu
- Settings → Skills page: Existing tab structure (Workspace Skills, Plugins) to extend

### Established Patterns
- MobX store + TanStack Query: Admin config uses MobX store for UI state, TanStack for server data
- Direct instantiation for services (not DI container): Follow SCIM/related-issues/plugins pattern
- JSONB for flexible metadata: WorkspacePlugin.references uses same pattern
- Workspace-scoped encrypted storage: Existing pattern for API keys and GitHub PAT

### Integration Points
- Issue detail page (`app/(workspace)/[workspaceSlug]/issues/[issueId]/page.tsx`): Add action bar component
- Settings → Skills page: Add Action Buttons tab/section
- `role_skill_materializer.py`: No changes needed — action buttons don't affect agent materialization
- Plugin install service: Extend to auto-create SkillActionButton rows from plugin metadata
- WorkspaceMcpServer: Query for available tools to populate binding dropdown

</code_context>

<deferred>
## Deferred Ideas

- Per-project button scoping (show different buttons per project) — future phase
- Role-based button visibility (only show certain buttons to certain roles) — future phase
- Inline execution (run skill without opening chat panel) — future phase
- Button usage analytics (track which buttons are clicked most) — future phase

</deferred>

---

*Phase: 17-skill-action-buttons*
*Context gathered: 2026-03-11*
