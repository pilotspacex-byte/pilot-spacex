# Phase 17: Skill Action Buttons - Research

**Researched:** 2026-03-11
**Domain:** Full-stack feature — data model, REST API, admin config UI, issue detail page integration, chat activation
**Confidence:** HIGH

## Summary

Phase 17 adds custom action buttons to the issue detail page, bound to workspace skills or MCP tools, that open the chat panel with context pre-loaded. This is a well-scoped CRUD feature that follows established patterns from Phases 14, 16, and 19. The data model (SkillActionButton extending WorkspaceScopedModel), API layer (admin-only CRUD router with direct instantiation), and frontend (TanStack Query hooks + shadcn/ui components) all have direct precedents in the codebase.

The critical integration point is the chat activation flow: `PilotSpaceStore.setActiveSkill()` + `setIssueContext()` + `clearConversation()` + `sendMessage()`. This is already wired and tested — the action button just orchestrates these existing primitives in sequence.

**Primary recommendation:** Follow the WorkspacePlugin/WorkspaceRoleSkill CRUD pattern exactly. New router at `workspace_action_buttons.py`, new model at `skill_action_button.py`, migration 075, new frontend API client + hooks, new "Action Buttons" tab in Settings Skills page, new `ActionButtonBar` component on issue detail page.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Horizontal action bar above editor content area, below issue header/title
- Max 3 buttons visible; overflow into "More" dropdown (Lucide MoreHorizontal)
- Visual: shadcn/ui Button variant="secondary" size="sm", optional Lucide icon + text label
- Action bar hidden when no buttons defined (no empty container)
- New "Action Buttons" tab/subsection in Settings > Skills page
- "Add Button" form: name (required), icon (optional), binding type (Skill/MCP Tool), dropdown to select target
- Skill dropdown lists: active workspace role skills + active installed plugin skills
- MCP Tool dropdown lists: tools from registered MCP servers as "ServerName / ToolName"
- Drag-and-drop reordering via sort_order integer column
- Admin can toggle buttons active/inactive without deleting
- Clicking a button always starts a NEW chat session (never reuses existing)
- Issue context pre-loaded via PilotSpaceStore.setIssueContext()
- Bound skill/tool activated via PilotSpaceStore.setActiveSkill(skillName, args)
- Auto-generated initial prompt sent immediately: "Run [Button Name] on this issue"
- Chat panel opens if not already open
- All workspace members see all defined action buttons (no role-based filtering)
- Display order by admin-defined sort_order (ascending)
- Buttons with is_active=false hidden from issue page, visible (greyed) in admin config
- New SkillActionButton model extending WorkspaceScopedModel
- Columns: name (String 100), icon (String 50, nullable), binding_type (Enum: SKILL, MCP_TOOL), binding_id (UUID, nullable), binding_metadata (JSONB), sort_order (Integer, default 0), is_active (Boolean, default true)
- Partial unique index on (workspace_id, name) WHERE is_deleted = false
- RLS policies: workspace isolation + service_role bypass
- Plugin install auto-creates SkillActionButton rows from plugin metadata
- Uninstalling/deactivating a plugin deactivates its associated action buttons
- Plugin-sourced buttons have binding_metadata.source = "plugin" and binding_metadata.plugin_id

### Claude's Discretion
- Exact Lucide icon picker implementation (simple text input vs visual picker)
- Drag-and-drop library choice for reordering (or simple up/down arrows)
- Exact initial prompt wording template
- Error handling when bound skill/tool no longer exists (show disabled button with tooltip)
- Migration number (next sequential after current head)

### Deferred Ideas (OUT OF SCOPE)
- Per-project button scoping (show different buttons per project)
- Role-based button visibility (only show certain buttons to certain roles)
- Inline execution (run skill without opening chat panel)
- Button usage analytics (track which buttons are clicked most)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SKBTN-01 | Workspace admin can define custom action buttons for the issue detail page | Admin CRUD API + Settings UI tab + SkillActionButton data model |
| SKBTN-02 | Each button is named and bound to a skill or remote MCP tool | binding_type enum (SKILL/MCP_TOOL) + binding_id + binding_metadata JSONB |
| SKBTN-03 | Clicking a button triggers ChatAI with issue context pre-loaded and bound skill/tool activated | PilotSpaceStore.clearConversation() + setIssueContext() + setActiveSkill() + sendMessage() orchestration |
| SKBTN-04 | Button execution respects AI approval policy (destructive actions require human confirmation) | Existing DD-003 approval gate in PilotSpaceAgent — no new code needed, just pass-through |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.x (existing) | SkillActionButton ORM model | Project standard, WorkspaceScopedModel base |
| Alembic | existing | Migration 075 | Project migration chain |
| FastAPI | existing | Admin CRUD endpoints | Project API layer |
| Pydantic | v2 (existing) | Request/response schemas | Project validation standard |
| TanStack Query | v5 (existing) | Server state for buttons | Project frontend data pattern |
| shadcn/ui | existing | Button, DropdownMenu, Tabs, Dialog | Project UI component library |
| MobX | existing | UI state for admin config | Project state management |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Lucide React | existing | Button icons | Icon display on action buttons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Drag-and-drop lib (dnd-kit) | Simple up/down arrow buttons | Up/down arrows simpler, fewer deps, sufficient for max ~10 buttons |
| Visual icon picker component | Text input for Lucide icon name | Text input is simpler; visual picker adds UI complexity for a rare admin action |

**Installation:**
No new dependencies needed. All libraries already in the project.

## Architecture Patterns

### Recommended Project Structure

**Backend:**
```
backend/src/pilot_space/
├── infrastructure/database/models/
│   └── skill_action_button.py          # New model
├── infrastructure/database/repositories/
│   └── skill_action_button_repository.py  # New repository
├── api/v1/routers/
│   └── workspace_action_buttons.py     # New router (admin CRUD)
├── api/v1/schemas/
│   └── skill_action_button.py          # New Pydantic schemas
└── alembic/versions/
    └── 075_add_skill_action_buttons.py # New migration
```

**Frontend:**
```
frontend/src/
├── services/api/
│   └── skill-action-buttons.ts         # API client + TanStack hooks
├── features/settings/components/
│   └── action-buttons-tab-content.tsx  # Admin config tab (observer)
├── features/issues/components/
│   └── action-button-bar.tsx           # Issue detail action bar
```

### Pattern 1: Direct Instantiation Router (not DI)
**What:** Router instantiates services/repositories directly in endpoint functions with lazy imports.
**When to use:** All new workspace-scoped CRUD routers (Phase 14, 16, 19 pattern).
**Example:**
```python
# Source: workspace_plugins.py (Phase 19)
@router.get("", response_model=list[SkillActionButtonResponse])
async def list_action_buttons(
    workspace_id: WorkspaceId, session: DbSession, current_user_id: CurrentUserId
) -> list[SkillActionButtonResponse]:
    await _require_admin(current_user_id, workspace_id, session)
    from pilot_space.infrastructure.database.repositories.skill_action_button_repository import (
        SkillActionButtonRepository,
    )
    repo = SkillActionButtonRepository(session)
    buttons = await repo.get_active_by_workspace(workspace_id)
    return [SkillActionButtonResponse.model_validate(b) for b in buttons]
```

### Pattern 2: TanStack Query + API Client
**What:** Frontend API client with typed functions + TanStack Query hooks for cache management.
**When to use:** All server data fetching/mutation.
**Example:**
```typescript
// Source: workspace-role-skills.ts (Phase 16)
export const actionButtonsApi = {
  getButtons(workspaceId: string): Promise<SkillActionButton[]> {
    return apiClient.get<SkillActionButton[]>(
      `/workspaces/${workspaceId}/action-buttons`
    );
  },
};

export function useActionButtons(workspaceId: string) {
  return useQuery({
    queryKey: ['action-buttons', workspaceId],
    queryFn: () => actionButtonsApi.getButtons(workspaceId),
    enabled: !!workspaceId,
  });
}
```

### Pattern 3: Chat Activation Orchestration
**What:** Sequence of PilotSpaceStore calls to start a new chat with context.
**When to use:** When action button is clicked on issue detail page.
**Example:**
```typescript
// On action button click:
const handleActionButtonClick = (button: SkillActionButton) => {
  const store = aiStore.pilotSpace;
  store.clearConversation();  // Start fresh session
  store.setIssueContext({ issueId });
  store.setActiveSkill(button.binding_metadata.skill_name);
  store.sendMessage(`Run ${button.name} on this issue`);
  setIsChatOpen(true);
};
```

### Pattern 4: Admin-Only Tab in Skills Settings
**What:** New tab component extracted as separate observer() to keep SkillsSettingsPage under 700 lines.
**When to use:** Adding the Action Buttons tab to Settings > Skills.
**Example:**
```typescript
// Source: PluginsTabContent pattern (Phase 19)
// Extract as ActionButtonsTabContent — separate observer() component
// SkillsSettingsPage adds TabsTrigger + TabsContent, delegates to child
```

### Anti-Patterns to Avoid
- **Observer on issue editor content:** ActionButtonBar sits above the editor, NOT inside TipTap. It CAN use observer() since it is outside the IssueEditorContent component tree.
- **DI container wiring for the new router:** Use direct instantiation pattern. Do NOT add to container.py wiring_config.
- **Lazy load in admin form selects:** Skill/MCP tool dropdowns should fetch data eagerly when admin opens the form (not on dropdown open) since the list is small.
- **Inline CRUD in SkillsSettingsPage:** Extract ActionButtonsTabContent as separate component. SkillsSettingsPage is already 623 lines — adding inline CRUD would exceed 700-line limit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Admin role check | Custom middleware | `_require_admin()` helper (copy from workspace_plugins.py) | Proven pattern, consistent error responses |
| RLS policies | Manual SQL | `get_workspace_rls_policy_sql(table_name)` from `rls.py` | Template handles all edge cases |
| Reorder logic | Complex swap algorithm | Simple `sort_order` integer column + bulk PATCH | Integer ordering with gaps (0, 10, 20) avoids cascading updates |
| Chat activation | Custom chat init flow | `clearConversation()` + `setActiveSkill()` + `sendMessage()` | Already implemented and tested in PilotSpaceActions |
| Icon rendering | Custom icon resolver | `lucide-react` dynamic import by name | Lucide already supports icon lookup by string name |

**Key insight:** Every building block already exists. This phase is pure composition of existing patterns + one new CRUD entity.

## Common Pitfalls

### Pitfall 1: SkillsSettingsPage Exceeding 700 Lines
**What goes wrong:** Adding action button CRUD inline pushes the file past the 700-line pre-commit limit.
**Why it happens:** SkillsSettingsPage already has 623 lines with role skills + workspace skills + plugins tab management.
**How to avoid:** Extract `ActionButtonsTabContent` as a separate observer() component (same as `PluginsTabContent` pattern from Phase 19).
**Warning signs:** File over 600 lines before adding new tab content.

### Pitfall 2: Chat Session Not Resetting
**What goes wrong:** Clicking an action button appends to an existing conversation instead of starting fresh.
**Why it happens:** Not calling `clearConversation()` before setting context/skill.
**How to avoid:** Always call `store.clearConversation()` FIRST, then `setIssueContext()`, then `setActiveSkill()`, then `sendMessage()`.
**Warning signs:** Previous chat messages visible after clicking action button.

### Pitfall 3: Stale Binding References
**What goes wrong:** Button bound to a deleted/deactivated skill or MCP server causes runtime error.
**Why it happens:** binding_id references are not FK-constrained (intentionally, to allow soft-delete without cascade).
**How to avoid:** Frontend validates binding exists before sending initial prompt. Show disabled button with tooltip "Bound skill/tool no longer available" when binding is stale.
**Warning signs:** Click on button with no visible effect, or console errors on click.

### Pitfall 4: Plugin Auto-Create Buttons Not Synced
**What goes wrong:** Installing a plugin creates action buttons, but uninstalling doesn't deactivate them.
**Why it happens:** Uninstall service doesn't know about action buttons.
**How to avoid:** Extend `InstallPluginService.uninstall()` to also deactivate associated SkillActionButton rows where `binding_metadata.plugin_id` matches.
**Warning signs:** Orphaned action buttons after plugin uninstall.

### Pitfall 5: Empty Route String
**What goes wrong:** 307 redirect when using `"/"` as route path.
**Why it happens:** FastAPI routing quirk (documented in MEMORY.md).
**How to avoid:** Always use `""` (empty string) for collection root routes.
**Warning signs:** 307 redirect in browser network tab.

### Pitfall 6: Missing SessionDep in Route Signatures
**What goes wrong:** RuntimeError: No session in current context.
**Why it happens:** DI session ContextVar not populated without SessionDep/DbSession parameter.
**How to avoid:** Every route function must declare `session: DbSession` parameter.
**Warning signs:** 500 error on first DB access in the route.

## Code Examples

### Backend: SkillActionButton Model
```python
# Source: Follows WorkspacePlugin pattern (Phase 19)
class BindingType(StrEnum):
    SKILL = "skill"
    MCP_TOOL = "mcp_tool"

class SkillActionButton(WorkspaceScopedModel):
    __tablename__ = "skill_action_buttons"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    binding_type: Mapped[BindingType] = mapped_column(
        Enum(BindingType, name="binding_type", create_type=False,
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    binding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    binding_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"),
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true"),
    )

    __table_args__ = (
        Index("uq_skill_action_buttons_workspace_name",
              "workspace_id", "name", unique=True,
              postgresql_where=text("is_deleted = false")),
        Index("ix_skill_action_buttons_workspace_active",
              "workspace_id", "is_active"),
    )
```

### Backend: Migration 075 RLS
```python
# Source: get_workspace_rls_policy_sql() from rls.py
from pilot_space.infrastructure.database.rls import get_workspace_rls_policy_sql

def upgrade():
    # Create table...
    # Create enum type...
    # Apply RLS
    op.execute(text(get_workspace_rls_policy_sql("skill_action_buttons")))
```

### Frontend: Action Button Bar Component
```typescript
// Source: Composition of existing shadcn/ui components
interface ActionButtonBarProps {
  buttons: SkillActionButton[];
  onButtonClick: (button: SkillActionButton) => void;
}

function ActionButtonBar({ buttons, onButtonClick }: ActionButtonBarProps) {
  if (buttons.length === 0) return null;  // No empty container

  const visible = buttons.slice(0, 3);
  const overflow = buttons.slice(3);

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b">
      {visible.map((btn) => (
        <Button key={btn.id} variant="secondary" size="sm" onClick={() => onButtonClick(btn)}>
          {btn.icon && <DynamicIcon name={btn.icon} className="mr-1.5 h-4 w-4" />}
          {btn.name}
        </Button>
      ))}
      {overflow.length > 0 && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="secondary" size="sm"><MoreHorizontal className="h-4 w-4" /></Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {overflow.map((btn) => (
              <DropdownMenuItem key={btn.id} onClick={() => onButtonClick(btn)}>
                {btn.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
```

### Frontend: Chat Activation Handler
```typescript
// Source: PilotSpaceStore.ts patterns (setActiveSkill, setIssueContext, clearConversation)
const handleActionButtonClick = useCallback((button: SkillActionButton) => {
  const store = aiStore.pilotSpace as {
    clearConversation: () => void;
    setIssueContext: (ctx: { issueId: string } | null) => void;
    setActiveSkill: (skill: string, args?: string) => void;
    sendMessage: (content: string) => Promise<void>;
  };

  // 1. Start fresh chat
  store.clearConversation();
  // 2. Set issue context
  store.setIssueContext({ issueId });
  // 3. Activate bound skill/tool
  const skillName = button.binding_metadata.skill_name || button.binding_metadata.tool_name;
  store.setActiveSkill(skillName);
  // 4. Send auto-prompt
  void store.sendMessage(`Run ${button.name} on this issue`);
  // 5. Ensure chat panel is open
  setIsChatOpen(true);
}, [aiStore.pilotSpace, issueId]);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DI container wiring | Direct instantiation in routes | Phase 14+ | Simpler, no container.py changes |
| Observer everywhere | Observer extracted to child components | Phase 19 | Keeps parent under 700 lines |
| FK constraints to bindings | JSONB metadata with binding_id (no FK) | Phase 19 plugins | Allows soft-delete without cascade issues |

**Deprecated/outdated:**
- None relevant to this phase.

## Open Questions

1. **Lucide Icon Picker Implementation**
   - What we know: Lucide React supports dynamic import by icon name string.
   - What's unclear: Whether to build a visual grid picker or use a simple text input with autocomplete.
   - Recommendation: Use simple text input with validation. A visual picker adds ~200+ lines of UI complexity for a feature admins use once per button. Text input with a link to Lucide icon gallery is sufficient.

2. **Drag-and-Drop vs Up/Down Arrows**
   - What we know: dnd-kit is not currently in the project. Maximum button count is realistically <10.
   - What's unclear: Whether the UX benefit of drag-and-drop justifies adding a dependency.
   - Recommendation: Use simple up/down arrow buttons. No new dependency needed. Achieves the same result for a small list.

3. **Dynamic Lucide Icon Import**
   - What we know: Lucide React tree-shakes by named import. Dynamic import by string name requires either `lucide-react/dynamic` or a lookup map.
   - What's unclear: Whether `lucide-react` ships a dynamic loader.
   - Recommendation: Use a curated icon map (20-30 common icons) with fallback to a generic icon. This avoids loading all 1000+ icons.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + Vitest (frontend) |
| Config file | backend/pyproject.toml + frontend/vitest.config.ts |
| Quick run command | `cd backend && uv run pytest tests/unit/routers/test_workspace_action_buttons.py -x` / `cd frontend && pnpm test -- --run src/services/api/__tests__/skill-action-buttons.test.ts` |
| Full suite command | `make quality-gates-backend && make quality-gates-frontend` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKBTN-01 | Admin CRUD endpoints for action buttons | unit | `cd backend && uv run pytest tests/unit/routers/test_workspace_action_buttons.py -x` | Wave 0 |
| SKBTN-01 | Admin config UI renders and submits | unit | `cd frontend && pnpm test -- --run src/features/settings/components/__tests__/action-buttons-tab-content.test.tsx` | Wave 0 |
| SKBTN-02 | Binding type validation (skill vs MCP tool) | unit | `cd backend && uv run pytest tests/unit/schemas/test_skill_action_button_schemas.py -x` | Wave 0 |
| SKBTN-03 | Action button bar renders on issue page | unit | `cd frontend && pnpm test -- --run src/features/issues/components/__tests__/action-button-bar.test.tsx` | Wave 0 |
| SKBTN-03 | Button click triggers chat activation sequence | unit | `cd frontend && pnpm test -- --run src/features/issues/components/__tests__/action-button-bar.test.tsx` | Wave 0 |
| SKBTN-04 | Approval gate fires for destructive actions | manual-only | Requires live agent + approval policy config | N/A |

### Sampling Rate
- **Per task commit:** `cd backend && uv run pytest tests/unit/routers/test_workspace_action_buttons.py -x && cd frontend && pnpm test -- --run`
- **Per wave merge:** `make quality-gates-backend && make quality-gates-frontend`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/unit/routers/test_workspace_action_buttons.py` -- covers SKBTN-01, SKBTN-02
- [ ] `backend/tests/unit/schemas/test_skill_action_button_schemas.py` -- covers SKBTN-02
- [ ] `frontend/src/services/api/__tests__/skill-action-buttons.test.ts` -- covers API client
- [ ] `frontend/src/features/settings/components/__tests__/action-buttons-tab-content.test.tsx` -- covers SKBTN-01
- [ ] `frontend/src/features/issues/components/__tests__/action-button-bar.test.tsx` -- covers SKBTN-03

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `workspace_plugins.py` router — CRUD pattern, _require_admin, direct instantiation
- Codebase inspection: `WorkspacePlugin` model — WorkspaceScopedModel, JSONB, partial unique index
- Codebase inspection: `WorkspaceRoleSkill` model — WorkspaceScopedModel, is_active, soft-delete
- Codebase inspection: `PilotSpaceStore.ts` — setActiveSkill, setIssueContext, clearConversation, sendMessage
- Codebase inspection: `PilotSpaceActions.ts` — activeSkill consumed on sendMessage, cleared after request
- Codebase inspection: `skills-settings-page.tsx` — Tab structure, Plugins tab pattern (623 lines)
- Codebase inspection: `issue detail page.tsx` — IssueNoteLayout, header/editor composition
- Codebase inspection: `workspace-role-skills.ts` — TanStack Query + apiClient pattern
- Codebase inspection: `rls.py` — get_workspace_rls_policy_sql template

### Secondary (MEDIUM confidence)
- CONTEXT.md locked decisions — validated against codebase patterns

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new dependencies
- Architecture: HIGH — direct precedent in Phase 14/16/19 patterns
- Pitfalls: HIGH — documented from codebase analysis (700-line limit, session reset, empty route)
- Chat activation: HIGH — PilotSpaceStore APIs verified in source code

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable — no external dependencies)
