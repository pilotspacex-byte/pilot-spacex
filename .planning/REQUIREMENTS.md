# Requirements: Pilot Space — v1.1.0 MCP Platform Hardening

**Defined:** 2026-03-19
**Core Value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control — AI accelerates without replacing human judgment.

## v1.1.0 Requirements

Requirements for MCP platform hardening. Each maps to roadmap phases.

### MCP Infrastructure

- [ ] **MCPI-01**: Remote MCP tools are added to `allowed_tools` with wildcard patterns so Claude can invoke them (critical bug — tools load but can't be called)
- [x] **MCPI-02**: Remote MCP servers support both SSE and HTTP transport types per Claude Agent SDK guidelines
- [x] **MCPI-03**: Failed MCP servers (last_status="failed") are skipped at session load to prevent timeout blocking
- [x] **MCPI-04**: Per-workspace MCP server cap (max 10) enforced with clear error when limit reached
- [x] **MCPI-05**: DNS re-validation at connect time prevents TOCTOU/rebinding SSRF bypass
- [x] **MCPI-06**: Application refuses to start without valid ENCRYPTION_KEY in production environments

### MCP OAuth

- [ ] **MCPO-01**: OAuth refresh token stored alongside access token (new DB column + Alembic migration)
- [x] **MCPO-02**: Expired OAuth tokens auto-refreshed before session load using stored refresh token
- [ ] **MCPO-03**: Token expiry tracked (expires_at column) and surfaced in MCP server status UI

### MCP Approval

- [x] **MCPA-01**: Remote MCP tool invocations route through DD-003 `can_use_tool` approval framework
- [x] **MCPA-02**: Workspace admins can configure auto-approve/require-approval per remote MCP server
- [x] **MCPA-03**: ChatView displays inline approval cards for remote MCP tool calls (tool name, server name, input preview)
- [x] **MCPA-04**: Auto-confirm setting per workspace/role respected — tools auto-execute when policy allows

### MCP Observability

- [x] **MCPOB-01**: Remote MCP tool invocations logged to immutable audit trail (tool name, server, input hash, duration)
- [x] **MCPOB-02**: MCP tool usage visible in workspace AI cost/usage dashboard

### MCP Catalog

- [ ] **MCPC-01**: Browsable MCP server catalog with official/community entries (name, description, transport, auth type)
- [ ] **MCPC-02**: One-click install from catalog registers server in workspace with pre-filled config
- [ ] **MCPC-03**: Catalog entries are versioned with update notifications when newer versions available
- [ ] **MCPC-04**: Seeded catalog includes context7 and GitHub MCP as official entries

## Future Requirements

Deferred to subsequent milestones. Tracked but not in current roadmap.

### MCP Advanced

- **MCPA-ADV-01**: Remote MCP server tool sandboxing (isolated execution environment)
- **MCPA-ADV-02**: MCP server marketplace with community ratings and reviews
- **MCPA-ADV-03**: Custom MCP server development toolkit (SDK + testing harness)
- **MCPA-ADV-04**: Cross-workspace MCP server sharing (org-level catalog)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Custom MCP protocol extensions | Standard MCP spec compliance only — no proprietary extensions |
| MCP server hosting (managed) | BYOK philosophy — users bring their own MCP servers |
| Bidirectional MCP (server→client) | Claude Agent SDK is client-only; server push not supported |
| Real-time MCP server monitoring (WebSocket) | Polling-based status checks sufficient for current scale |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MCPI-01 | Phase 30 | Pending |
| MCPI-02 | Phase 31 | Complete |
| MCPI-03 | Phase 31 | Complete |
| MCPI-04 | Phase 31 | Complete |
| MCPI-05 | Phase 31 | Complete |
| MCPI-06 | Phase 31 | Complete — 31-04 |
| MCPO-01 | Phase 32 | Pending |
| MCPO-02 | Phase 32 | Complete |
| MCPO-03 | Phase 32 | Pending |
| MCPA-01 | Phase 33 | Complete |
| MCPA-02 | Phase 33 | Complete |
| MCPA-03 | Phase 33 | Complete |
| MCPA-04 | Phase 33 | Complete |
| MCPOB-01 | Phase 34 | Complete |
| MCPOB-02 | Phase 34 | Complete |
| MCPC-01 | Phase 35 | Pending |
| MCPC-02 | Phase 35 | Pending |
| MCPC-03 | Phase 35 | Pending |
| MCPC-04 | Phase 35 | Pending |

**Coverage:**
- v1.1.0 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation (all 19 requirements mapped)*
