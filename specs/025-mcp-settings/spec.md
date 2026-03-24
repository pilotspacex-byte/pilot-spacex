# MCP Settings Redevelopment

**Version**: 1.0.0
**Status**: Draft
**Author**: AI-generated
**Date**: 2026-03-19

---

## Executive Summary

Redevelop the MCP (Model Context Protocol) settings experience so workspace administrators can manage MCP server connections in one unified interface. Users can add servers that connect to remote HTTP endpoints (SSE/StreamableHTTP) or that are launched locally via NPX or UVX commands. Configuration can be seeded quickly by importing a JSON config file or entered field-by-field through a guided form.

---

## Clarifications

### Session 2026-03-19

- Q: When editing a saved server, how should previously-saved header/env secret values behave? → A: Show a masked placeholder `••••••••`; admin must retype to change it — no plaintext reveal option.
- Q: When importing a JSON config that contains a server name already existing in the workspace, what should happen? → A: Skip conflicting entries, import the rest, and show a post-import summary listing any skipped names.
- Q: How is server "Active/Inactive" status determined? → A: Background polling on a schedule (every 30–60s); the page reflects the latest result automatically.
- Q: Is enable/disable an explicit admin action, or is status purely derived from connectivity polling? → A: Status is an explicit enum — `Enabled` (polling healthy), `Disabled` (admin action), `Unhealthy` (server reachable but returning errors), `Unreachable` (connection failed/timeout), `Config Error` (invalid configuration detected).
- Q: What is the connection test timeout before showing failure? → A: 10 seconds.

---

## Business Context

### Problem Statement

The current MCP settings workflow lacks sufficient flexibility:

1. **No support for remote MCP servers** — users cannot point the platform to an SSE or StreamableHTTP endpoint.
2. **No first-class NPX / UVX support** — servers launched via package-manager commands require manual workarounds.
3. **No bulk-import path** — onboarding teams must configure each server individually, which slows adoption.
4. **No unified server status view** — operators cannot see active/inactive status, transport type, or last connection state at a glance.

### Solution

A redesigned MCP Settings page with:
- A full-page server list (table view) with filtering and status indicators.
- A "New MCP Server" dialog with two entry modes: **Import JSON** and **Form Configuration**.
- Per-server row actions: edit, test connection, enable/disable, delete.

### Goals

| Goal | Description |
|------|-------------|
| Unified management | Single page to view, add, edit, and remove all MCP server configurations |
| Flexible connectivity | Support remote (SSE/StreamableHTTP) and local (NPX/UVX/stdio) server types |
| Fast onboarding | Import an existing Claude/Cursor/VS Code JSON config to bootstrap all servers at once |
| Operational visibility | Real-time Active/Inactive status visible per server without navigating away |

---

## Users & Actors

| Actor | Description |
|-------|-------------|
| Workspace Admin | Manages MCP server configurations for the whole workspace; primary user of this feature |
| Workspace Member | May view the server list (read-only) depending on permission level |

---

## User Scenarios & Testing

### Scenario 1 — View installed MCP servers

**Given** I am a Workspace Admin on the MCP Settings page
**When** the page loads
**Then** I see a table listing all configured MCP servers with columns: Server Name, Type, URL / Command, Transport, Status, Actions
**And** each row shows a status indicator: green "Enabled", grey "Disabled", amber "Unhealthy", red "Unreachable", or red warning "Config Error"
**And** I can filter the list by type (All Types, Remote, NPX, UVX) and by status (All Status, Enabled, Disabled, Unhealthy, Unreachable, Config Error)
**And** a server count is shown in the footer ("Showing N of M servers")

### Scenario 2 — Add a remote MCP server via Import JSON

**Given** I click "New MCP" on the server list page
**When** the "Add New MCP Server" dialog opens with the "Import JSON" tab active
**Then** I see a JSON text area pre-populated with a skeleton `{ "mcpServers": { ... } }` structure
**And** I can paste or type a valid JSON config (Claude, Cursor, or VS Code MCP format)
**Or** I click "Upload File" to load a config file from disk
**When** the JSON is valid
**Then** a "Detected Servers" preview section appears below the editor showing each parsed server as a card with its name, URL/command, and transport badge
**And** a confirmation line reads "Valid JSON — N server entries detected"
**And** the footer "Import & Add Servers" button becomes active
**When** I click "Import & Add Servers"
**Then** all detected servers whose names do not already exist in the workspace are saved and appear in the server list
**And** any server names that conflict with existing entries are skipped, and a summary message lists the skipped names
**And** I can optionally click "Validate" to check the JSON before importing

### Scenario 3 — Add a server via Form Configuration

**Given** I open the "Add New MCP Server" dialog and click the "Form Configuration" tab
**When** the form is visible
**Then** I fill in:
- **Server Name** (text, required) — e.g. `my-remote-server`
- **Server Type** (select: Remote MCP (SSE), NPX, UVX) — determines which other fields appear
- **Server URL / Command** (text, required) — URL for remote; command for NPX/UVX
- **Transport** (select: SSE, stdio, StreamableHTTP)
- **Headers / Authentication** — key-value pairs, each with a delete button; "Add Header" adds a new row
- **Environment Variables** — key-value pairs; "Add Variable" adds a new row
- **Command Arguments (for NPX/UVX)** — additional CLI arguments, visible only when type is NPX or UVX
**And** I can click "Test Connection" to verify the server is reachable before saving
**When** I click "Save Configuration"
**Then** the new server is saved and appears in the server list

### Scenario 4 — Edit an existing server

**Given** I see a server row in the table
**When** I click the edit action on that row
**Then** the "Add New MCP Server" dialog opens pre-filled with that server's current values
**And** I can update any field and save

### Scenario 5 — Test a server connection

**Given** I want to verify a server is reachable
**When** I click "Test Connection" in the form dialog or the test action in the table row
**Then** a connection attempt is made
**And** I receive clear feedback: success (connected, latency shown) or failure (error message with guidance)

### Scenario 6 — Remove a server

**Given** I see a server row in the table
**When** I click the delete action
**Then** a confirmation prompt appears before any deletion takes place
**And** on confirmation the server is removed from the list

### Scenario 7 — JSON parse feedback

**Given** I am on the Import JSON tab
**When** I enter invalid JSON
**Then** an inline error message describes the parse problem
**And** the "Import & Add Servers" button remains disabled until the JSON is valid

---

## Functional Requirements

### FR-01 — Server List Page

| ID | Requirement |
|----|-------------|
| FR-01-1 | The MCP Settings page displays all configured servers in a table with columns: Server Name, Type, URL / Command, Transport, Status, Actions |
| FR-01-2 | Each row shows an icon indicating connection type (globe for Remote, terminal for NPX, code for UVX) |
| FR-01-3 | Status column displays one of five states per server, each with a distinct visual indicator: **Enabled** (green dot), **Disabled** (grey dot, admin-controlled), **Unhealthy** (amber dot — reachable but returning errors), **Unreachable** (red dot — connection failed or timed out), **Config Error** (red warning icon — invalid configuration); statuses are refreshed automatically via background polling every 30–60 seconds |
| FR-01-4 | The list supports filtering by Type (All Types, Remote, NPX, UVX) and by Status (All Status, Enabled, Disabled, Unhealthy, Unreachable, Config Error) |
| FR-01-5 | A search box allows filtering servers by name or URL/command substring |
| FR-01-6 | A "Sort" control is available to reorder the list |
| FR-01-7 | A footer shows the count of displayed vs. total servers |
| FR-01-8 | Each row has an Actions cell containing at minimum: edit, test connection, enable/disable toggle, and delete |

### FR-07 — Enable / Disable Server

| ID | Requirement |
|----|-------------|
| FR-07-1 | An admin can explicitly **disable** a server from the row actions; a disabled server is not polled and is excluded from active MCP routing |
| FR-07-2 | A disabled server can be **re-enabled** from the row actions; upon re-enabling, polling resumes immediately and the status updates within 30–60 seconds |
| FR-07-3 | Disabling a server does **not** delete its configuration |
| FR-07-4 | The status transitions are: `Enabled` ↔ `Disabled` (admin action); `Enabled` → `Unhealthy` / `Unreachable` / `Config Error` (polling result); resolving the underlying issue and refreshing returns status to `Enabled` |
| FR-01-9 | A "Refresh" button reloads server statuses without a full page reload |
| FR-01-10 | A "New MCP" primary button opens the Add New MCP Server dialog |

### FR-02 — Add / Edit Server Dialog

| ID | Requirement |
|----|-------------|
| FR-02-1 | The dialog has two tabs: "Import JSON" and "Form Configuration" |
| FR-02-2 | The dialog can be dismissed via a close (×) button or "Cancel" action |
| FR-02-3 | The dialog title reads "Add New MCP Server" (or "Edit MCP Server" when editing) |
| FR-02-4 | The footer always shows a "Cancel" button and a primary action button ("Import & Add Servers" or "Save Configuration") |

### FR-03 — Import JSON Tab

| ID | Requirement |
|----|-------------|
| FR-03-1 | A monospace text area accepts JSON in Claude, Cursor, or VS Code MCP config formats |
| FR-03-2 | A "Upload File" ghost button allows loading a `.json` file from disk |
| FR-03-3 | An info line reads: "Supports Claude, Cursor, and VS Code MCP config formats" |
| FR-03-4 | On valid JSON input, a "Detected Servers" preview renders each server as a card showing name, URL/command, and transport badge |
| FR-03-5 | A validation summary shows: "Valid JSON — N server entries detected" (green check icon) or an error description |
| FR-03-6 | A "Validate" button in the footer triggers an explicit validation pass |
| FR-03-7 | "Import & Add Servers" is disabled until JSON is valid and at least one server is detected |
| FR-03-8 | Importing adds all detected servers to the workspace and closes the dialog; if a detected server name already exists in the workspace, that entry is **skipped** (not overwritten) and a post-import summary lists every skipped name so the admin can take manual action |

### FR-04 — Form Configuration Tab

| ID | Requirement |
|----|-------------|
| FR-04-1 | Required fields: Server Name, Server Type, Server URL / Command |
| FR-04-2 | Server Type options: Remote MCP (SSE), NPX, UVX |
| FR-04-3 | Transport field defaults to SSE for Remote type and stdio for NPX/UVX types |
| FR-04-4 | Transport options: SSE, stdio, StreamableHTTP |
| FR-04-5 | Headers / Authentication section: dynamic key-value rows; "Add Header" appends a new row; each row has a delete (trash) icon |
| FR-04-6 | Environment Variables section: dynamic key-value rows; "Add Variable" appends a new row; each row has a delete icon |
| FR-04-7 | Command Arguments field is shown only when Server Type is NPX or UVX |
| FR-04-8 | A "Test Connection" ghost button in the footer attempts to reach the configured endpoint and shows inline feedback |
| FR-04-9 | "Save Configuration" is disabled until all required fields are filled |
| FR-04-10 | On save, the server is persisted and appears in the server list |
| FR-04-11 | When editing a server, previously saved header and env-var values render as masked placeholders (`••••••••`); the admin must retype a value to change it — no plaintext reveal option is provided |

### FR-05 — Connection Testing

| ID | Requirement |
|----|-------------|
| FR-05-1 | Connection test initiates an attempt to reach the configured server with a **10-second timeout** |
| FR-05-2 | On success (within 10 seconds), the user sees a success indicator with measured latency |
| FR-05-3 | On failure or timeout (after 10 seconds), the user sees an error message with actionable guidance (e.g., "Check URL / firewall settings") |
| FR-05-4 | Connection test is non-destructive and does not save the configuration |

### FR-06 — Delete Server

| ID | Requirement |
|----|-------------|
| FR-06-1 | Deleting a server requires explicit confirmation before the record is removed |
| FR-06-2 | A deleted server is removed from the list immediately after confirmation |

---

## Key Entities

| Entity | Attributes |
|--------|------------|
| MCPServer | id, workspace_id, name, server_type (remote \| npx \| uvx), url_or_command, transport (sse \| stdio \| streamable_http), headers (key-value map), env_vars (key-value map), command_args (string), status (enabled \| disabled \| unhealthy \| unreachable \| config_error), created_at, updated_at |

---

## UI / UX Notes

> Based on UI mockup in `/temp/mockup-mcp.pen` (frames: `m4cmm`, `pb2KK`, `e27ty`)

- **Server list** uses a full-width data table with a dark sidebar navigation showing: General (Dashboard, Servers, Connections) and Configuration (Import Config — highlighted in gold, Remote MCP, NPX Commands, UVX Commands) and System (Logs, Settings).
- **Type badges**: "Remote" (default/gold), "NPX" (outline), "UVX" (secondary/grey).
- **Status indicators**: green dot (Enabled), grey dot (Disabled), amber dot (Unhealthy), red dot (Unreachable), red warning icon (Config Error).
- **Dialog width**: 720px, height: 780px, with corner radius 12 and layered drop shadows.
- **JSON editor** uses JetBrains Mono 12px with a bordered background panel.
- **Detected server cards** show a colored icon container (filled primary for Remote, muted for NPX/UVX) plus name, URL, and transport badge.
- **Form Configuration** tab organizes fields in two-column rows for Name+Type and URL+Transport; Headers and Env Vars each have their own labeled section with "Add" buttons.

---

## Scenario 8 — Agent uses a workspace MCP tool

**Given** a workspace admin has configured and enabled an MCP server (e.g. a remote SSE or NPX command server)
**When** a workspace member sends a chat message that would benefit from one of that server's tools
**Then** the PilotSpace AI agent automatically loads that server's config from the database
**And** the agent connects to the MCP server and invokes the appropriate tool
**And** the tool result is incorporated into the agent's response
**And** servers that are `Disabled`, `is_deleted=True`, or have decryption failures are silently excluded

---

## FR-08 — Agent MCP Config Loading

| ID | Requirement |
|----|-------------|
| FR-08-1 | On each chat request, the agent fetches all `is_enabled=True`, `is_deleted=False` MCP servers for the workspace and merges them into the SDK session's server map alongside built-in servers |
| FR-08-2 | For `server_type=remote` + `transport=sse`: builds `McpSSEServerConfig { type: "sse", url, headers }` — bearer token and custom headers injected |
| FR-08-3 | For `server_type=remote` + `transport=streamable_http`: builds `McpHttpServerConfig { type: "http", url, headers }` |
| FR-08-4 | For `server_type=npx` or `uvx` + `transport=stdio`: builds `McpStdioServerConfig { type: "stdio", command, args, env }` — env vars decrypted and injected |
| FR-08-5 | A server whose `auth_token_encrypted` fails decryption is skipped and a WARNING is logged; other servers in the same workspace are unaffected |
| FR-08-6 | A server with `is_enabled=False` is excluded from the agent's MCP server map (not polled and not connected) |
| FR-08-7 | The agent's built-in MCP servers (note, issue, project, etc.) take precedence; workspace server names use the key pattern `{server_type}_{server_id}` to avoid collisions |
| FR-08-8 | End-to-end: when the agent session includes a workspace MCP server, the agent can invoke that server's tools and receive results within the normal tool-use flow |

---

## Out of Scope

- Real-time server log streaming (covered by the Logs section, separate feature)
- Per-member MCP permission controls (covered by role-based access, separate feature)
- Workspace-level MCP usage metering or billing

---

## Assumptions

1. MCP server configurations are workspace-scoped, not per-user.
2. The JSON import format follows the `{ "mcpServers": { "<name>": { ... } } }` schema used by Claude Desktop, Cursor, and VS Code Copilot.
3. Transport options are: `sse`, `stdio`, `streamable_http`. Default for remote is `sse`; default for NPX/UVX is `stdio`.
4. Connection testing is a best-effort reachability check (e.g., HTTP HEAD or handshake attempt); it does not validate tool schemas.
5. Sensitive header/env values (e.g., API keys) are stored encrypted at rest. After saving, these values are **never transmitted back to the client in plaintext**. On edit, they render as a masked placeholder (`••••••••`); the admin must retype the value to replace it. There is no "reveal" option.
6. Pagination or infinite scroll is applied when the server list exceeds 25 entries.
7. Only workspace admins can create, edit, or delete MCP servers; members have read-only visibility.

---

## Success Criteria

| Criterion | Metric |
|-----------|--------|
| Configuration speed | Workspace admin can add a fully configured MCP server in under 2 minutes |
| Bulk import | A valid JSON config with 10 servers is parsed and imported in under 5 seconds |
| Connection test feedback | Test result (success or failure) is shown within 10 seconds; the test times out and reports failure if no response is received within 10 seconds |
| Error clarity | 100% of JSON parse errors and connection failures include a human-readable description |
| Status accuracy | Server status (one of: Enabled, Disabled, Unhealthy, Unreachable, Config Error) is determined by background polling every 30–60 seconds; the list reflects real connectivity within 60 seconds of a state change without requiring a manual refresh |
| Zero data loss | No existing MCP server configurations are lost during migration from the old settings UI |
| Agent MCP tool use | A workspace member can chat with the agent and it invokes a tool from a registered, enabled MCP server; result appears in the response |
| Agent isolation | Disabled or soft-deleted MCP servers are never connected to by the agent |

---

## Dependencies

| Dependency | Description |
|------------|-------------|
| MCP connectivity layer | Backend service capable of initiating SSE/StreamableHTTP connections and spawning NPX/UVX processes |
| Workspace auth & permissions | Role check to restrict write operations to admins |
| Existing MCP config schema | Must be backward-compatible with any configs stored by the prior settings implementation |
