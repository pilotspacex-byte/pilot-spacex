# Requirements: Pilot Space

**Defined:** 2026-03-09
**Milestone:** v1.0-alpha — Pre-Production Launch
**Core Value:** Enterprise teams can adopt AI-augmented SDLC workflows without sacrificing data sovereignty, compliance, or human control — AI accelerates without replacing human judgment.

## v1 Requirements

### Onboarding

- [x] **ONBD-01**: New user's first sign-in auto-creates a workspace (name derived from email/display name — no extra step)
- [x] **ONBD-02**: After workspace creation, user lands on onboarding checklist — never an empty page
- [x] **ONBD-03**: API key setup step includes inline guidance (where to get key, format hint, test connection button)
- [x] **ONBD-04**: Role + skill generation step shows clear success confirmation when skill is saved and active
- [x] **ONBD-05**: Each onboarding step links directly to the relevant settings action

### Bug Fixes

- [x] **BUG-01**: Skill wizard "Save and Accept" resolves `workspaceId` to UUID before API call (no slug fallback → 422)
- [x] **BUG-02**: Sign-up empty page fixed — new accounts redirected to workspace creation flow, not blank screen

### Workspace

- [x] **WS-01**: Workspace switcher shows workspace metadata (name, member count)
- [x] **WS-02**: Workspace switch lands user on last visited page within that workspace

### Related Issues

- [ ] **RELISS-01**: Issue detail shows auto-suggested related issues (semantic similarity via knowledge graph)
- [ ] **RELISS-02**: User can manually link/unlink issues as related from the issue detail page
- [ ] **RELISS-03**: Related issues surface connections via shared notes, same project, and semantic similarity score
- [ ] **RELISS-04**: User can dismiss AI suggestions (dismissed suggestions don't re-appear)

### Workspace Role Skills

- [ ] **WRSKL-01**: Workspace admin writes a role description; AI generates a workspace-level skill for that role
- [ ] **WRSKL-02**: Admin reviews and approves AI-generated skill before it becomes active for the workspace
- [ ] **WRSKL-03**: Members with a matching role automatically inherit the workspace-level skill
- [ ] **WRSKL-04**: User's personal skill overrides workspace skill if both exist for the same role

### Skill Action Buttons

- [ ] **SKBTN-01**: Workspace admin can define custom action buttons for the issue detail page
- [ ] **SKBTN-02**: Each button is named and bound to a skill or remote MCP tool (e.g. "Push to Figma", "Sync to Jira")
- [ ] **SKBTN-03**: Clicking a button triggers ChatAI with the issue context pre-loaded and the bound skill/tool activated
- [ ] **SKBTN-04**: Button execution respects AI approval policy (destructive actions require human confirmation)

### Remote MCP

- [x] **MCP-01**: Workspace owner/admin can register a remote MCP server by URL + display name
- [x] **MCP-02**: Bearer token authentication — token stored securely per workspace
- [x] **MCP-03**: OAuth 2.0 redirect authentication — token stored per workspace after callback
- [x] **MCP-04**: Registered remote servers are dynamically available to PilotSpaceAgent (hot-loaded per workspace)
- [x] **MCP-05**: Owner/admin can view connection status (connected / failed / unknown) per registered server
- [x] **MCP-06**: Owner/admin can remove a remote MCP server

### AI Chat Model Selection

- [x] **CHAT-01**: User can select the AI model for a chat session from models available in their workspace
- [x] **CHAT-02**: Selected model persists per workspace session (doesn't reset on navigation)
- [x] **CHAT-03**: Model selector is disabled if no valid API key is configured for that provider

### AI Provider Registry

- [x] **AIPR-01**: Workspace admin can configure API keys for pre-defined providers (Anthropic, OpenAI, Kimi, GLM, Gemini, and others with known base URLs)
- [x] **AIPR-02**: Workspace admin can register a custom provider by name + OpenAI-compatible base URL + API key
- [x] **AIPR-03**: All configured providers and their available models are surfaced in the model selector
- [x] **AIPR-04**: PilotSpaceAgent routes requests to the selected provider/model via Claude Agent SDK-compatible interface
- [x] **AIPR-05**: Provider status shows connected / invalid key / unreachable per configured provider

### Tech Debt

- [ ] **DEBT-01**: OIDC login flow verified end-to-end in browser (closes AUTH-02 gap from v1.0)
- [ ] **DEBT-02**: `issue_relation_server` + `note_content_server` use `check_approval_from_db()` (closes AIGOV-01 gap)
- [ ] **DEBT-03**: Async HTTP client fixture added — 2 xfail audit API tests now passing
- [ ] **DEBT-04**: Key rotation re-encryption implemented (replaces xfail stub from v1.0 Phase 03)

## v2 Requirements

### Notifications

- **NOTF-01**: User receives in-app notification when a related issue is auto-linked
- **NOTF-02**: Admin receives notification when a workspace skill is ready for review

### Advanced MCP

- **MCP-07**: MCP server tool discovery — list available tools from a registered remote server
- **MCP-08**: Per-tool enable/disable for registered MCP servers

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time collaborative editing | Significant infra investment, not core to launch |
| Mobile-specific features | Desktop-first for developer workflows |
| GitLab integration | GitHub-first; GitLab in subsequent milestone |
| Built-in LLM hosting (Ollama) | BYOK is sufficient; self-hosting adds ops burden |
| AI Studio custom agent builder | Built-in agents sufficient for current scale |
| Workspace-to-workspace issue linking | Cross-tenant complexity; single-workspace focus for v1.0-alpha |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ONBD-01 | Phase 12 | Complete |
| ONBD-02 | Phase 12 | Complete |
| ONBD-03 | Phase 12 | Complete |
| ONBD-04 | Phase 12 | Complete |
| ONBD-05 | Phase 12 | Complete |
| BUG-01 | Phase 12 | Complete |
| BUG-02 | Phase 12 | Complete |
| WS-01 | Phase 12 | Complete |
| WS-02 | Phase 12 | Complete |
| AIPR-01 | Phase 13 | Complete |
| AIPR-02 | Phase 13 | Complete |
| AIPR-03 | Phase 13 | Complete |
| AIPR-04 | Phase 13 | Complete |
| AIPR-05 | Phase 13 | Complete |
| CHAT-01 | Phase 13 | Complete |
| CHAT-02 | Phase 13 | Complete |
| CHAT-03 | Phase 13 | Complete |
| MCP-01 | Phase 14 | Complete |
| MCP-02 | Phase 14 | Complete |
| MCP-03 | Phase 14 | Complete |
| MCP-04 | Phase 14 | Complete |
| MCP-05 | Phase 14 | Complete |
| MCP-06 | Phase 14 | Complete |
| RELISS-01 | Phase 15 | Pending |
| RELISS-02 | Phase 15 | Pending |
| RELISS-03 | Phase 15 | Pending |
| RELISS-04 | Phase 15 | Pending |
| WRSKL-01 | Phase 16 | Pending |
| WRSKL-02 | Phase 16 | Pending |
| WRSKL-03 | Phase 16 | Pending |
| WRSKL-04 | Phase 16 | Pending |
| SKBTN-01 | Phase 17 | Pending |
| SKBTN-02 | Phase 17 | Pending |
| SKBTN-03 | Phase 17 | Pending |
| SKBTN-04 | Phase 17 | Pending |
| DEBT-01 | Phase 18 | Pending |
| DEBT-02 | Phase 18 | Pending |
| DEBT-03 | Phase 18 | Pending |
| DEBT-04 | Phase 18 | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 — traceability complete after roadmap creation (39/39 mapped)*
