# MCP Tools System - Pilot Space AI Layer

**For AI layer overview, see parent [ai/README.md](../README.md)**

---

## Overview

33 tools across 6 servers enabling PilotSpaceAgent to interact with platform data. All tools return operation payloads (never mutate directly) and enforce RLS workspace isolation.

---

## Tool Servers

| Server | Count | Purpose | Key Tools |
|--------|-------|---------|-----------|
| `note_server` | 9 | Note writing/mutation | write_to_note, update_note_block, extract_issues, create_issue_from_note, link_existing_issues, enhance_text, summarize_note, search_notes, create_note |
| `note_content_server` | 5 | Block-level operations | search_note_content, insert_block, remove_block, remove_content, replace_content |
| `issue_server` | 4 | Issue CRUD | get_issue, search_issues, create_issue, update_issue |
| `issue_relation_server` | 6 | Issue relations + state | link_issue_to_note, unlink_issue_from_note, link_issues, unlink_issues, add_sub_issue, transition_issue_state |
| `project_server` | 5 | Project management | get_project, search_projects, create_project, update_project, update_project_settings |
| `comment_server` | 4 | Comment management | create_comment, update_comment, search_comments, get_comments |
| **Total** | **33** | | |

---

## Tool Categories by RLS Scope

- **Note Tools** (14): Scope: note + workspace. No cross-note linking via tools.
- **Issue Tools** (10): Scope: issue + workspace. Cross-issue and issue-to-note relations within workspace.
- **Project Tools** (5): Scope: project + workspace. Project deletion cascades.
- **Comment Tools** (4): Scope: comment + parent (issue/note) + workspace. Always tied to parent entity.

---

## Tool Execution Flow

1. User intent -> PilotSpaceAgent routes to MCP tool
2. Tool validates + returns operation payload: `{"status": "pending_apply", ...}`
3. `transform_sdk_message()` converts payload to SSE `content_update` event
4. Frontend `useContentUpdates()` hook processes event -> TipTap/API mutation

### Operation Payload Contract

| Status | Meaning | Next Step |
|--------|---------|-----------|
| `pending_apply` | Ready for frontend application | SSE `content_update` event |
| `pending_approval` | Requires human approval (DD-003) | SSE `approval_request` event |

Tool implementation pattern: See any server file (e.g., `note_server.py:update_note_block`)

---

## RLS Enforcement (3 Layers)

1. **Context**: `get_workspace_context()` retrieves current workspace from request context
2. **Application**: Explicit `workspace_id` filter in all repository calls
3. **Database**: PostgreSQL RLS policies via session variables

See [infrastructure/auth/README.md](../../infrastructure/auth/README.md) for full RLS architecture.

---

## Approval Classification (DD-003)

| Category | Approval | Tool Examples |
|----------|----------|---------------|
| Non-destructive | Auto-execute | get_issue, search_issues, search_notes, get_project |
| Content creation | Configurable | create_issue, create_comment, extract_issues, write_to_note |
| Destructive | Always required | unlink_issue_from_note, unlink_issues |

Classification logic: See `sdk/permission_handler.py:PermissionHandler`

---

## Adding a New MCP Tool

1. Create handler with `@tool` decorator in relevant server file (e.g., `mcp/note_server.py`)
2. Return operation payload: `{"status": "pending_apply", ...}`
3. Export tool name in server's `TOOL_NAMES` list
4. Add to `pilotspace_agent.py` ALL_TOOL_NAMES
5. Add to PilotSpaceAgent system prompt (tool categories section)
6. Test: `pytest tests/ai/mcp/test_<server>.py`
7. Verify RLS: workspace scoping + explicit filter

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Tool not returning payload | Return JSON `{"status": "pending_apply", ...}` |
| Missing RLS context | Always call `get_workspace_context()` + explicit filter |
| Approval not awaited | Return `{"status": "pending_approval"}` + wait for user |
| Blocking I/O in tools | Use `loop.run_in_executor()` for file I/O |
| Tool not registered | Add to ALL_TOOL_NAMES in `pilotspace_agent.py` |

---

## Key Files

| File | Purpose |
|------|---------|
| `note_server.py` | 9 note tools |
| `note_content_server.py` | 5 block-level tools |
| `issue_server.py` | 4 issue CRUD tools |
| `issue_relation_server.py` | 6 relation tools |
| `project_server.py` | 5 project tools |
| `comment_server.py` | 4 comment tools |
| `registry.py` | Tool registry management |

---

## Related Documentation

- **AI Layer Parent**: [ai/README.md](../README.md)
- **Agents**: [agents/README.md](../agents/README.md)
- **Providers**: [providers/README.md](../providers/README.md)
- **RLS Security**: [infrastructure/auth/README.md](../../infrastructure/auth/README.md)
- **Design Decisions**: DD-088 (MCP tool registry), DD-003 (approval workflow)
