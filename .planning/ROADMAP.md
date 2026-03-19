# Roadmap: Pilot Space

## Milestones

- ✅ **v1.0 Enterprise** — Phases 1–11 (shipped 2026-03-09)
- ✅ **v1.0-alpha Pre-Production Launch** — Phases 12–23 (shipped 2026-03-12)
- ✅ **v1.0.0-alpha2 Notion-Style Restructure** — Phases 24–29 (shipped 2026-03-12)
- 🚧 **v1.1.0 MCP Platform Hardening** — Phases 30–35 (in progress)

## Phases

<details>
<summary>✅ v1.0 Enterprise (Phases 1–11) — SHIPPED 2026-03-09</summary>

- [x] Phase 1: Identity & Access (9/9 plans) — completed 2026-03-07
- [x] Phase 2: Compliance & Audit (5/5 plans) — completed 2026-03-08
- [x] Phase 3: Multi-Tenant Isolation (8/8 plans) — completed 2026-03-08
- [x] Phase 4: AI Governance (10/10 plans) — completed 2026-03-08
- [x] Phase 5: Operational Readiness (7/7 plans) — completed 2026-03-09
- [x] Phase 6: Wire Rate Limiting + SCIM Token (1/1 plans) — completed 2026-03-09
- [x] Phase 7: Wire Storage Quota Enforcement (2/2 plans) — completed 2026-03-09
- [x] Phase 8: Fix SSO Integration (1/1 plans) — completed 2026-03-09
- [x] Phase 9: Login Audit Events (1/1 plans) — completed 2026-03-09
- [x] Phase 10: Wire Audit Trail (1/1 plans) — completed 2026-03-09
- [x] Phase 11: Fix Rate Limiting Architecture (1/1 plans) — completed 2026-03-09

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.0-alpha Pre-Production Launch (Phases 12–23) — SHIPPED 2026-03-12</summary>

- [x] Phase 12: Onboarding & First-Run UX (3/3 plans) — completed 2026-03-09
- [x] Phase 13: AI Provider Registry + Model Selection (4/4 plans) — completed 2026-03-10
- [x] Phase 14: Remote MCP Server Management (4/4 plans) — completed 2026-03-10
- [x] Phase 15: Related Issues (3/3 plans) — completed 2026-03-10
- [x] Phase 16: Workspace Role Skills (4/4 plans) — completed 2026-03-10
- [x] Phase 17: Skill Action Buttons (2/2 plans) — completed 2026-03-11
- [x] Phase 18: Tech Debt Closure (3/3 plans) — completed 2026-03-11
- [x] Phase 19: Skill Registry & Plugin System (4/4 plans) — completed 2026-03-11
- [x] Phase 20: Skill Template Catalog (4/4 plans) — completed 2026-03-11
- [x] Phase 21: Documentation & Verification Closure (2/2 plans) — completed 2026-03-12
- [x] Phase 22: Integration Safety — Session & OAuth2 UI (2/2 plans) — completed 2026-03-12
- [x] Phase 23: Tech Debt Sweep (2/2 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.0-alpha-ROADMAP.md`

</details>

<details>
<summary>✅ v1.0.0-alpha2 Notion-Style Restructure (Phases 24–29) — SHIPPED 2026-03-12</summary>

- [x] Phase 24: Page Tree Data Model (2/2 plans) — completed 2026-03-12
- [x] Phase 25: Tree API & Page Service (2/2 plans) — completed 2026-03-12
- [x] Phase 26: Sidebar Tree & Navigation (3/3 plans) — completed 2026-03-12
- [x] Phase 27: Project Hub & Issue Views (2/2 plans) — completed 2026-03-12
- [x] Phase 28: Visual Design Refresh (2/2 plans) — completed 2026-03-12
- [x] Phase 29: Responsive Layout & Drag-and-Drop (3/3 plans) — completed 2026-03-12

Full archive: `.planning/milestones/v1.0.0-alpha2-ROADMAP.md`

</details>

### 🚧 v1.1.0 MCP Platform Hardening (In Progress)

**Milestone Goal:** Make the MCP layer production-ready — fix the critical allowed_tools bug, harden infrastructure (transport, SSRF, server cap), deliver OAuth refresh lifecycle, extend DD-003 approval to remote tools, wire observability, and ship a browsable MCP server catalog with one-click install.

- [ ] **Phase 30: MCP Critical Bug Fix** — Patch allowed_tools so Claude can invoke remote MCP tools
- [ ] **Phase 31: MCP Infrastructure Hardening** — SSE/HTTP transport, health-check gating, server cap, SSRF hardening, encryption enforcement
- [x] **Phase 32: OAuth Refresh Flow** — Refresh token storage, auto-refresh before session load, expiry tracking in UI (completed 2026-03-19)
- [ ] **Phase 33: Remote MCP Approval Framework** — DD-003 wiring, per-server approval config, ChatView inline cards, auto-confirm policy
- [ ] **Phase 34: MCP Observability** — Audit trail for tool invocations, MCP usage visible in AI dashboard
- [ ] **Phase 35: MCP Server Catalog** — Browsable catalog with one-click install, versioned entries, official seeds

## Phase Details

### Phase 30: MCP Critical Bug Fix
**Goal**: Remote MCP tools are callable by Claude — the allowed_tools gap is closed
**Depends on**: Nothing (critical bug fix, first phase)
**Requirements**: MCPI-01
**Success Criteria** (what must be TRUE):
  1. A registered remote MCP tool invoked by Claude during a chat session executes successfully rather than being silently skipped
  2. The PilotSpaceAgent session load includes remote tool identifiers in allowed_tools using wildcard patterns matching the server namespace
  3. Existing MCP server registration and connection flows are unaffected
**Plans**: 1 plan
Plans:
- [ ] 30-01-PLAN.md — Fix _build_stream_config wildcard patterns + unit tests

### Phase 31: MCP Infrastructure Hardening
**Goal**: The MCP transport layer is robust — HTTP + SSE supported, failed servers skipped on load, per-workspace server cap enforced, SSRF rebinding blocked, and production encryption key required
**Depends on**: Phase 30
**Requirements**: MCPI-02, MCPI-03, MCPI-04, MCPI-05, MCPI-06
**Success Criteria** (what must be TRUE):
  1. An admin can register an MCP server with either SSE or HTTP transport type and it connects successfully
  2. A server whose last_status is "failed" does not block or delay session load for other tools
  3. Attempting to register an 11th MCP server in a workspace returns a clear error message stating the limit has been reached
  4. A DNS rebinding attack against a registered MCP server URL is blocked at connect time, not just at registration time
  5. Starting the application in production without ENCRYPTION_KEY set causes an immediate startup failure with a clear error message
**Plans**: 4 plans
Plans:
- [ ] 31-01-PLAN.md — DB migration + transport_type model/schema (MCPI-02 schema)
- [ ] 31-02-PLAN.md — SSRF extraction + _load_remote_mcp_servers hardening (MCPI-02 logic + MCPI-03 + MCPI-05)
- [ ] 31-03-PLAN.md — Server cap enforcement in repository + router (MCPI-04)
- [ ] 31-04-PLAN.md — Startup encryption key enforcement in main.py lifespan (MCPI-06)

### Phase 32: OAuth Refresh Flow
**Goal**: OAuth-authenticated MCP servers stay connected across token expiry — refresh tokens are stored, used automatically before session load, and expiry state is visible to the workspace admin
**Depends on**: Phase 31
**Requirements**: MCPO-01, MCPO-02, MCPO-03
**Success Criteria** (what must be TRUE):
  1. After completing OAuth authorization for an MCP server, the refresh token is persisted alongside the access token in the database
  2. When a session loads and the stored access token is expired, it is silently refreshed using the refresh token without user intervention
  3. The MCP server status UI shows token expiry state (e.g., "expires in 2 hours" or "expired") alongside the connection badge
**Plans**: 3 plans
Plans:
- [ ] 32-01-PLAN.md — DB migration 092 + ORM columns + OAuth callback refresh token storage (MCPO-01)
- [ ] 32-02-PLAN.md — _refresh_oauth_token helper + expiry check in _load_remote_mcp_servers (MCPO-02)
- [ ] 32-03-PLAN.md — token_expires_at in response schema + MCPServer TS type + ExpiryBadge UI (MCPO-03)

### Phase 33: Remote MCP Approval Framework
**Goal**: Remote MCP tool invocations are subject to the same DD-003 human approval controls as built-in AI actions — workspace admins can configure per-server approval policies and users see inline approval cards in ChatView
**Depends on**: Phase 31
**Requirements**: MCPA-01, MCPA-02, MCPA-03, MCPA-04
**Success Criteria** (what must be TRUE):
  1. Invoking a remote MCP tool routes through the existing `can_use_tool` approval check rather than executing unconditionally
  2. A workspace admin can set a remote MCP server to "require approval" or "auto-approve" mode from the server management UI
  3. When a tool invocation requires approval, ChatView renders an inline card showing the tool name, server name, and input preview before execution proceeds
  4. When the workspace/role policy allows auto-confirm, remote MCP tools execute without interrupting the chat flow
**Plans**: 3 plans
Plans:
- [ ] 33-01-PLAN.md — Migration 093 + ORM McpApprovalMode + PATCH endpoint + ActionType.REMOTE_MCP_TOOL (MCPA-02 schema)
- [ ] 33-02-PLAN.md — Extend create_can_use_tool_callback + _build_stream_config wiring (MCPA-01, MCPA-04)
- [ ] 33-03-PLAN.md — MCPServersStore + API client + MCPServerCard Switch toggle (MCPA-02, MCPA-03)

### Phase 34: MCP Observability
**Goal**: Every remote MCP tool invocation leaves an auditable trail and appears in the workspace AI usage dashboard
**Depends on**: Phase 33
**Requirements**: MCPOB-01, MCPOB-02
**Success Criteria** (what must be TRUE):
  1. After a remote MCP tool executes, an entry appears in the immutable audit log recording the tool name, server, hashed input, and duration
  2. The workspace AI cost/usage dashboard includes a MCP tools section showing per-server and per-tool invocation counts
**Plans**: TBD

### Phase 35: MCP Server Catalog
**Goal**: Workspace admins can browse a curated catalog of MCP servers, install one with a single click, receive update notifications when newer versions are available, and find context7 and GitHub MCP pre-seeded as official entries
**Depends on**: Phase 34
**Requirements**: MCPC-01, MCPC-02, MCPC-03, MCPC-04
**Success Criteria** (what must be TRUE):
  1. An admin can open the MCP catalog, see a list of entries with name, description, transport type, and auth type, and filter or browse without leaving the settings UI
  2. Clicking "Install" on a catalog entry registers the MCP server in the workspace with connection fields pre-filled from the catalog definition
  3. When a newer catalog entry version is available for an installed server, the server list shows an update notification the admin can act on
  4. The seeded catalog includes context7 and GitHub MCP as official entries visible on first load of a new workspace
**Plans**: TBD

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1–11 | v1.0 | 46/46 | Complete | 2026-03-09 |
| 12–23 | v1.0-alpha | 37/37 | Complete | 2026-03-12 |
| 24–29 | v1.0.0-alpha2 | 14/14 | Complete | 2026-03-12 |
| 30. MCP Critical Bug Fix | v1.1.0 | 0/1 | Planned | - |
| 31. MCP Infrastructure Hardening | v1.1.0 | 2/4 | In Progress | - |
| 32. OAuth Refresh Flow | v1.1.0 | 3/3 | Complete | 2026-03-19 |
| 33. Remote MCP Approval Framework | 1/3 | In Progress|  | - |
| 34. MCP Observability | v1.1.0 | 0/? | Not started | - |
| 35. MCP Server Catalog | v1.1.0 | 0/? | Not started | - |

**Total to date: 35 phases, 108+ plans across 4 milestones**

---
*v1.0 shipped: 2026-03-09 — 11 phases, 46 plans, 30/30 requirements*
*v1.0-alpha shipped: 2026-03-12 — 12 phases, 37 plans, 39/39 requirements + 7 gap closure items*
*v1.0.0-alpha2 shipped: 2026-03-12 — 6 phases, 14 plans, 17/17 requirements*
*v1.1.0 roadmap created: 2026-03-19 — 6 phases, 19/19 requirements mapped*
