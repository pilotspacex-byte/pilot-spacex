# Roadmap: Pilot Space

## Milestones

- ✅ **v1.0 Enterprise** — Phases 1–11 (shipped 2026-03-09)
- 🔄 **v1.0-alpha Pre-Production Launch** — Phases 12–18 (in progress)

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

### v1.0-alpha: Pre-Production Launch

- [x] **Phase 12: Onboarding & First-Run UX** — Auto-workspace creation, onboarding checklist, bug fixes, workspace switcher polish (completed 2026-03-09)
- [x] **Phase 13: AI Provider Registry + Model Selection** — Multi-provider BYOK registry (built-in + custom) and per-session model selector (completed 2026-03-10)
- [ ] **Phase 14: Remote MCP Server Management** — Register, auth (Bearer + OAuth), status, and PilotSpaceAgent dynamic wiring
- [ ] **Phase 15: Related Issues** — Semantic similarity suggestions, manual linking, dismissal
- [ ] **Phase 16: Workspace Role Skills** — Admin-configured AI skill generation and role inheritance
- [ ] **Phase 17: Skill Action Buttons** — Custom issue-page buttons bound to skills or MCP tools
- [ ] **Phase 18: Tech Debt Closure** — OIDC E2E, MCP approval wiring, xfail tests, key rotation

## Phase Details

### Phase 12: Onboarding & First-Run UX
**Goal**: A new user who signs up never sees a blank screen — they land in a workspace with guided next steps
**Depends on**: Nothing (standalone UX + bug fixes)
**Requirements**: ONBD-01, ONBD-02, ONBD-03, ONBD-04, ONBD-05, BUG-01, BUG-02, WS-01, WS-02
**Success Criteria** (what must be TRUE):
  1. A brand-new account's first sign-in redirects to a newly created workspace (name derived from email/display name) without any manual setup step
  2. After workspace creation, the user sees an onboarding checklist — not a blank page under any code path
  3. The API key onboarding step shows contextual guidance (where to get a key, format hint) and a "Test connection" button the user can click inline
  4. The skill generation step shows a visible success confirmation when the skill is saved and active
  5. The workspace switcher displays the workspace name and member count; switching lands on the last-visited page for that workspace
**Plans**: 3 plans

Plans:
- [ ] 12-01-PLAN.md — Foundation fixes: BUG-01 workspaceId race + ONBD-01 auto-create workspace
- [ ] 12-02-PLAN.md — Onboarding enrichment: inline API key step, skill save toast, settings links
- [ ] 12-03-PLAN.md — Workspace switcher: member count display + last-visited path tracking

### Phase 13: AI Provider Registry + Model Selection
**Goal**: Workspace admins can configure multiple AI providers and users can choose which model to use per chat session
**Depends on**: Phase 12 (workspace exists; BYOK settings page is the deployment surface)
**Requirements**: AIPR-01, AIPR-02, AIPR-03, AIPR-04, AIPR-05, CHAT-01, CHAT-02, CHAT-03
**Success Criteria** (what must be TRUE):
  1. Admin can configure API keys for pre-defined providers (Anthropic, OpenAI, Kimi, GLM, Gemini) and the status reflects connected / invalid key / unreachable in real time
  2. Admin can register a custom OpenAI-compatible provider by name + base URL + API key, and it appears alongside built-in providers
  3. The model selector in the chat UI lists all models from all configured providers (and only those with valid keys are selectable)
  4. A chat session started with a specific model continues to use that model throughout the session without resetting on navigation
  5. PilotSpaceAgent dispatches the request to the correct provider/model based on the user's selection
**Plans**: 4 plans

Plans:
- [ ] 13-01-PLAN.md — Backend provider expansion: migration 070 + ModelListingService + /models endpoint (AIPR-01, AIPR-02, AIPR-03, AIPR-05)
- [ ] 13-02-PLAN.md — Backend model routing: ai_chat_model_routing.py + ChatRequest.model_override + agent wiring (AIPR-04)
- [ ] 13-03-PLAN.md — Frontend settings expansion: generalize ProviderStatusCard + custom provider form + AISettingsStore model listing (AIPR-01, AIPR-02, AIPR-05)
- [ ] 13-04-PLAN.md — Frontend model selector: ModelSelector component + PilotSpaceStore.selectedModel + sendMessage wiring (CHAT-01, CHAT-02, CHAT-03)

### Phase 14: Remote MCP Server Management
**Goal**: Workspace admins can register external MCP servers and PilotSpaceAgent can dynamically call their tools
**Depends on**: Phase 12 (workspace admin settings surface)
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06
**Success Criteria** (what must be TRUE):
  1. Admin can register a remote MCP server by URL and display name from the workspace settings page
  2. Admin can choose Bearer token auth (token stored encrypted per workspace) or OAuth 2.0 redirect auth (token stored after callback completes)
  3. Each registered server shows a connection status badge (connected / failed / unknown) that reflects its actual reachability
  4. PilotSpaceAgent automatically loads the tools of all registered MCP servers when processing a workspace request (no restart required)
  5. Admin can remove a registered server and it immediately disappears from PilotSpaceAgent's available tool set
**Plans**: 4 plans

Plans:
- [ ] 14-01-PLAN.md — Wave 0 test scaffolds: xfail stubs for all 6 MCP requirements + agent injection + frontend store (MCP-01..06)
- [ ] 14-02-PLAN.md — Backend persistence: migration 071 + WorkspaceMcpServer model + repository + Pydantic schemas (MCP-01, MCP-02, MCP-06)
- [ ] 14-03-PLAN.md — Backend API + agent wiring: CRUD router + OAuth flow + _load_remote_mcp_servers + stream() integration (MCP-01..06)
- [ ] 14-04-PLAN.md — Frontend: MCPServersStore + API client + settings page + server cards + Next.js route (MCP-01..03, MCP-05, MCP-06)

### Phase 15: Related Issues
**Goal**: Users can discover and link related issues through semantic suggestions and manual linking
**Depends on**: Phase 12 (issue detail page exists; knowledge graph populated by existing background job)
**Requirements**: RELISS-01, RELISS-02, RELISS-03, RELISS-04
**Success Criteria** (what must be TRUE):
  1. The issue detail page shows an auto-populated "Related Issues" panel with semantically similar issues ranked by similarity score
  2. Related issues surface their relationship reason (shared note, same project, or semantic similarity score)
  3. User can manually link any issue as related, and that link appears immediately in both linked issues' detail pages
  4. User can dismiss an AI suggestion and it never re-appears for that issue
**Plans**: TBD

### Phase 16: Workspace Role Skills
**Goal**: Workspace admins can configure AI skills at the workspace level that members inherit by role
**Depends on**: Phase 12 (workspace admin settings surface)
**Requirements**: WRSKL-01, WRSKL-02, WRSKL-03, WRSKL-04
**Success Criteria** (what must be TRUE):
  1. Admin can write a role description, trigger AI skill generation, and review the generated skill before it goes live
  2. A skill remains inactive until the admin explicitly approves it — members see no change until approval
  3. Members whose workspace role matches the configured skill automatically have it available without any personal setup
  4. If a user has their own personal skill for the same role, their personal skill takes precedence over the workspace skill
**Plans**: TBD

### Phase 17: Skill Action Buttons
**Goal**: Workspace admins can add custom action buttons to the issue detail page that invoke skills or MCP tools
**Depends on**: Phase 14 (remote MCP tool availability), Phase 16 (workspace role skills available to bind)
**Requirements**: SKBTN-01, SKBTN-02, SKBTN-03, SKBTN-04
**Success Criteria** (what must be TRUE):
  1. Admin can define a named button and bind it to either a workspace skill or a registered remote MCP tool
  2. The button appears on the issue detail page for all workspace members
  3. Clicking the button opens the chat panel with the issue context pre-loaded and the bound skill/tool activated — no manual setup by the user
  4. If the bound skill or tool triggers a destructive action, the AI approval gate fires (requiring human confirmation) before execution proceeds
**Plans**: TBD

### Phase 18: Tech Debt Closure
**Goal**: Known v1.0 gaps are resolved — OIDC E2E verified, MCP approval wiring correct, xfail tests passing, key rotation implemented
**Depends on**: Phase 14 (MCP servers must exist for approval wiring), Phase 12 (OIDC login surface must be stable)
**Requirements**: DEBT-01, DEBT-02, DEBT-03, DEBT-04
**Success Criteria** (what must be TRUE):
  1. The OIDC login flow (Okta/Azure AD/Google Workspace) can be completed end-to-end in a real browser without errors
  2. `issue_relation_server` and `note_content_server` both call `check_approval_from_db()` for every tool execution (no static level bypass)
  3. The two previously-xfail audit API tests pass without skips or workarounds
  4. Key rotation re-encrypts all workspace content keys to the new key without data loss (xfail stub replaced with real implementation)
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Identity & Access | v1.0 | 9/9 | Complete | 2026-03-07 |
| 2. Compliance & Audit | v1.0 | 5/5 | Complete | 2026-03-08 |
| 3. Multi-Tenant Isolation | v1.0 | 8/8 | Complete | 2026-03-08 |
| 4. AI Governance | v1.0 | 10/10 | Complete | 2026-03-08 |
| 5. Operational Readiness | v1.0 | 7/7 | Complete | 2026-03-09 |
| 6. Wire Rate Limiting + SCIM Token | v1.0 | 1/1 | Complete | 2026-03-09 |
| 7. Wire Storage Quota Enforcement | v1.0 | 2/2 | Complete | 2026-03-09 |
| 8. Fix SSO Integration | v1.0 | 1/1 | Complete | 2026-03-09 |
| 9. Login Audit Events | v1.0 | 1/1 | Complete | 2026-03-09 |
| 10. Wire Audit Trail | v1.0 | 1/1 | Complete | 2026-03-09 |
| 11. Fix Rate Limiting Architecture | v1.0 | 1/1 | Complete | 2026-03-09 |
| 12. Onboarding & First-Run UX | v1.0-alpha | 3/3 | Complete | 2026-03-09 |
| 13. AI Provider Registry + Model Selection | v1.0-alpha | 4/4 | Complete | 2026-03-10 |
| 14. Remote MCP Server Management | 3/4 | In Progress|  | - |
| 15. Related Issues | v1.0-alpha | 0/TBD | Not started | - |
| 16. Workspace Role Skills | v1.0-alpha | 0/TBD | Not started | - |
| 17. Skill Action Buttons | v1.0-alpha | 0/TBD | Not started | - |
| 18. Tech Debt Closure | v1.0-alpha | 0/TBD | Not started | - |

---
*v1.0 shipped: 2026-03-09 — 11 phases, 46 plans, 30/30 requirements satisfied*
*v1.0-alpha roadmap created: 2026-03-09 — 7 phases, 39/39 requirements mapped*
