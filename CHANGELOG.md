# Changelog

All notable changes to Pilot Space are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0-alpha3] - 2026-03-25

### Added

**Multi-Theme System (Phase 46)**
- `ThemeStore` (MobX): 4 modes (light, dark, high-contrast, system) + 8 accent color presets (green, blue, purple, orange, pink, red, teal, indigo)
- Runtime CSS custom property injection via `applyAccentColor()` — overrides `--primary`, `--primary-hover`, `--primary-muted`, `--ring`, `--sidebar-primary`
- Appearance settings page in account section with theme mode, accent color, editor theme, font size, and font family controls
- `ThemeStore` wired into `RootStore`; bidirectional sync between localStorage and server preferences
- `ThemeProvider` (next-themes) integrated into root providers

**Office Suite Preview (Phase 41)**
- Excel renderer: spreadsheet viewer with sheet tabs, cell formatting, and column auto-sizing
- Word renderer: DOCX document viewer with paragraph styles, tables, and images
- PowerPoint renderer: slide viewer with navigation, thumbnails, and full-screen mode
- PPTX slide annotations: per-slide annotation CRUD (`ArtifactAnnotationRepository`, `artifact_annotations` router)
- File artifact upload service: DB-first lifecycle (pending_upload → ready), 10 MB limit, 94-extension allowlist
- Artifact cleanup background job for stale pending records
- Migrations 091–094: `artifacts` table, RLS policies, enum case fix, `WITH CHECK` clauses
- Migrations 096–097: `artifact_annotations` table with RLS and fix

**MCP Workspace Custom Servers**
- Remote + command MCP server registration per workspace with SSRF and command injection validation
- Bulk import from Claude Desktop / Cursor / VS Code JSON config (`ImportMcpServersService`)
- Connection testing with 10s timeout, latency measurement, and status mapping (ENABLED/UNHEALTHY/UNREACHABLE)
- OAuth2 callback handling for MCP server authorization
- MCP server card component with status badge, auth type badge, and action buttons
- `mcp_validation.py` security module: HTTPS enforcement, blocked networks (RFC 1918, loopback, AWS metadata), shell metachar rejection
- Encrypted env vars and auth tokens via `encrypt_kv` / `decrypt_kv`
- Migrations 098–099: `workspace_mcp_servers` redevelopment, admin-only RLS tightening

**Voice Input & Live Transcription**
- ElevenLabs Speech-to-Text integration: `TranscriptionService` with HTTP multipart upload (25 MB limit, 7 MIME types)
- Live transcription WebSocket: `transcription_ws.py` streaming audio to ElevenLabs Scribe Realtime
- SHA-256 transcript caching with configurable TTL to avoid duplicate API calls
- Audio artifact upload to Supabase Storage `voice-recordings` bucket with signed URLs
- STT cost tracking: `stt_pricing.py` calculator ($0.012/min), integrated with `CostTracker`
- BYOK: workspace-scoped ElevenLabs API key via `SecureKeyStorage`
- PCM processor worklet for browser audio capture
- Migration 094: `transcript_cache` table with RLS

**Workspace Feature Toggles**
- Per-workspace sidebar module visibility: notes, issues, projects, cycles, knowledge graph, AI features
- `FeatureToggleService` with admin/owner-only write access, any-member read
- AI skill filtering respects feature toggles (disabled features hide related skills)
- Feature toggle REST API: `GET/PATCH /{workspace_id}/feature-toggles`
- Frontend `AIFeatureToggles` component with prerequisite checks (embedding + LLM required)

**Knowledge Graph Redesign**
- Interactive ReactFlow graph panel with node-type filters (Issues, Notes, PRs, Decisions, Code) and depth slider
- Botanical "Entwined Growth Tree" node aesthetic: seed pods, leaf capsules, buds with tier-based sizing
- 15+ Lucide icon mappings for graph node types
- Workspace overview graph with cross-project relationships
- Empty state handling with regeneration action
- Graph node renderer with Radix tooltips showing metadata (type, timestamp, relationships)
- `NOTE_CHUNK` node type added (migration 096)
- Backend knowledge graph regeneration endpoint

**Medium-Style Editor Enhancements**
- Medium-style TOC sidebar with `#` section mentions in chat
- Single Enter = line break (hard break within block), double Enter = new paragraph (`ParagraphSplitExtension`)
- Paste handler: `\n\n` in pasted text auto-splits into separate paragraphs
- File preview modal with TipTap + Dialog fix (4-layer: stopEvent, state isolation, Radix outside-click, Suspense)
- Video embed support in note editor
- Selection toolbar improvements

**AI Provider Settings Redesign**
- Tabbed provider panel: LLM (default), Embedding, Voice/STT tabs with connection status badges
- Setup progress indicator showing Embedding + LLM configuration state
- Official simple-icons SVGs for provider logos (Anthropic, Google, OpenAI)
- Per-user AI model defaults and `base_url` overrides
- Service-based provider setup for embedding + LLM with validation
- Unified AI providers list view with per-provider config cards

**Settings Modal Migration**
- Settings migrated from full-page routes to responsive modal dialog
- Lazy-loaded settings pages with Suspense + skeleton fallbacks
- Sidebar navigation (desktop) + select dropdown (mobile)
- Role-based access: guests see only Profile + Appearance
- 14 settings pages: General, Features, AI Providers, MCP Servers, Integrations, SSO, Encryption, AI Governance, Audit, Roles, Usage, Billing, Profile, Appearance

**Skill System Enhancements**
- Skill modal redesign with tags, usage fields, and extracted prompt module
- MCP auto-approve execution fix for skill dispatch
- 7 skill feature bug fixes

**Infrastructure & SDK Migration**
- Supabase HTTP calls migrated to `supabase-py` async SDK (`get_supabase_client()` with double-checked locking)
- `AppError` domain exception hierarchy: `NotFoundError` (404), `ForbiddenError` (403), `ConflictError` (409), `ValidationError` (422), `UnauthorizedError` (401), `ServiceUnavailableError` (503)
- Centralized RFC 7807 error handler with domain-specific handlers: `app_error_handler`, `transcription_error_handler`, `feature_toggle_error_handler`, `mcp_server_error_handler`
- UUID sanitization and sensitive key filtering in production error responses
- Env-based model defaults and centralized SDK env builder
- `pgmq_set_vt` public schema wrapper (migration 100)
- Docs migrated to separate private repository (`pilotspace/pilot-space-docs`)

**Other Additions**
- Project CRUD fixes + RAG-powered MCP tools + chunking enhancements
- In-app documentation page
- AI chat issue extraction card with 6 UX improvements
- Provider setup enhancement with workspace LLM routing
- Kanban scroll fade + member card email dedup
- Audit actor resolution + greeting display name fix
- Global pointermove guard for tooltip visibility management
- Free-tier deployment guide (Vercel + Render + Supabase Cloud)

### Changed

- Settings UI moved from dedicated pages to modal dialog with lazy loading
- AI providers page restructured with tabbed layout (LLM / Embedding / Voice)
- Knowledge graph nodes redesigned with botanical aesthetic and tier-based sizing
- Enter key behavior: single Enter = line break, double Enter = new paragraph (was: single Enter = new paragraph)
- Members page: fire-and-forget `refreshMembers` helper replaces blocking fetch
- Design tokens updated in `globals.css` (typography, spacing, colors)
- Removed unused font imports from layout

### Fixed

- Editor page crash when opening file preview (TipTap + Dialog interaction)
- Sidebar collapsed layout and accessibility issues
- Missing cost tracking on all AI call sites (ghost text, extraction, context, PR review)
- Member management: owner self-demotion guard, role case normalization, confirmation dialog
- Migration 093 made no-op (enum already uses UPPERCASE, not lowercase)
- SSE streaming stuck with missing infra debug logging
- Workspace switcher: fetch all workspaces when switcher opens
- Missing `GET /velocity` endpoint causing 422 in cycles
- 7 skill feature issues (execution, display, filtering)
- AI config enum fix, `NoteIssueLink` creation, `linkType` alignment
- Note cards: content preview, hide 0-word count, sort dropdown width
- Login banner: error icon, Terms/Privacy links, icon field helper text
- Hide progress ring/bar at 0%
- Banner localStorage TTL + SSO/Roles/Security page headers for non-admins
- Removed `hover:-translate-y-0.5` causing layout jitter in 5 components
- Resolved 227 preexisting pytest failures and removed e2e from CI
- Alembic migration versioning cleanup and CI workflow update

### Security

- SSRF prevention in MCP server URL validation: HTTPS enforcement, blocked networks (RFC 1918, loopback, link-local, AWS metadata 169.254.169.254)
- Command injection prevention: shell metachar rejection in MCP command package args
- Workspace membership check added to personal page RLS policy
- Per-user AI settings hardening: SSRF prevention, model validation, state preservation
- v1.1 security + accessibility review followup fixes
- MCP RLS tightened to admin-only (migration 099)
- Workspace members RLS index added (migration 095)

## [1.0.0-beta] - 2026-03-09

### Added

**Identity & Access (AUTH-01 through AUTH-07)**
- SAML 2.0 SSO: `SamlAuthProvider`, `SsoService`, `auth_sso.py` router; IdP-initiated and SP-initiated flows
- OIDC SSO: `supabase.auth.signInWithOAuth` integration with `useApplyClaimsRole` post-login claim application
- Custom RBAC: `check_permission()`, `CustomRoleRepository`, `RbacService`; per-resource permission grants, custom role assignment
- Session management: `SessionRecordingMiddleware`, force-terminate single/all sessions, session listing UI
- SCIM 2.0: `ScimService`, `/api/v1/scim/v2/{slug}/*` router, SHA-256 SCIM token generation endpoint
- SSO enforcement: `GET /auth/sso/check-login` pre-login check; workspace-level force-SSO mode
- Role-claim mapping: IdP claim → workspace role with owner-cap guardrail (prevents privilege escalation via IdP misconfiguration)
- SSO settings page, roles settings page, security settings page, and SSO login button UI

**Compliance & Audit (AUDIT-01 through AUDIT-06)**
- Immutable audit log (`AuditLog` model + migration 065): PostgreSQL trigger prevents UPDATE/DELETE; `pg_cron` auto-purge with retention window
- `AuditLogRepository`: cursor-paged keyset (base64 JSON timestamp+id), streaming export via `list_for_export()`
- Audit instrumentation: every create/update/delete on issues, notes, cycles, members, settings, and custom roles writes an audit entry (non-fatal `write_audit_nonfatal` helper)
- AI audit hook: `AuditLogHook` writes DB rows with input, output, model name, token cost, and AI rationale on every AI action
- Audit API: `GET` list (filtered by actor/action/resource/date, cursor-paged), `GET` export (streaming CSV/JSON), `PATCH` retention (OWNER only), immutability enforcement
- Audit settings page with filter UI, read-only table, row expansion, and export buttons
- Login audit events: `user.login` written to audit log on SAML callback and password auth success (AUDIT-01 gap closure)

**Multi-Tenant Isolation (TENANT-01 through TENANT-04)**
- RLS enum case fix (migration 066): policies now consistently use UPPERCASE role values
- Workspace-level BYOK encryption: `workspace_encryption_keys` table (migration 067), AES-256-GCM helpers; key never returned to client via API
- Per-workspace rate limiting: `RateLimitMiddleware` registered at module level with lazy Redis accessor; 429 response on limit breach
- Storage quota enforcement: `_check_storage_quota` / `_update_storage_usage` wired into all 5 write paths (issues create/update, notes create/update, attachments upload); 507 at 100%, `X-Storage-Warning` at 80%
- Super-admin operator dashboard: `GET /admin/workspaces` with workspace health, member activity, and usage stats
- Encryption settings UI, usage settings UI with quota progress bars, admin dashboard frontend

**AI Governance (AIGOV-01 through AIGOV-07)**
- `WorkspaceAIPolicy` model (migrations 068/069): per-role, per-action-type approval thresholds
- `ApprovalService`: four-tier priority (ALWAYS_REQUIRE → owner shortcut → DB policy row → level fallback); wired into 4 MCP servers and all AI skill dispatch paths
- AI approval queue UI: `ApprovalsPage` with pending approvals list, sidebar badge, and `useResolveApproval` mutations
- Full AI audit trail: `actor_type` filter on audit list/export, AI row expansion with model/cost/rationale in audit settings
- AI artifact rollback: `_dispatch_rollback()` for issue/note; frontend rollback button in AI audit log
- BYOK enforcement: `AINotConfiguredError` (503) raised when no valid workspace key; env fallback removed
- AI cost dashboard: token usage by model (existing) + new By Feature tab (`group_by=operation_type`)
- Rationale popovers in `ExtractionReviewPanel` and PR review; `AiNotConfiguredBanner` for owners
- AI governance settings page with policy matrix (per-role switch toggles, optimistic updates)

**Operational Readiness (OPS-01 through OPS-06)**
- Health endpoints: `GET /health/live` (shallow liveness), `GET /health/ready` (parallel DB/Redis/Supabase checks with 2s/5s timeouts)
- Structured logging: `trace_id`, `actor` (`user:{uuid}`), `action` ContextVars via structlog; populated in `AuthMiddleware` per request
- Docker Compose: root `docker-compose.yml` with all services (backend, frontend, Supabase, Redis, Meilisearch); `--profile production` nginx
- Kubernetes Helm chart: `infra/helm/pilot-space/`, `values.yaml`, dual ingress (main 100 rps + AI 10 rps/600s timeout for SSE)
- Backup/restore CLI: `pilot backup create` (pg_dump + Storage API + AES-256-GCM encryption) / `pilot backup restore`; PSBC magic bytes header for file validation
- Zero-downtime upgrade CI: `.github/workflows/upgrade-simulation.yml` with real PostgreSQL 15 service container; accepts `degraded` as valid post-upgrade health outcome

**SSO Gap Closure**
- Normalized all SSO admin endpoints from `workspace_id: UUID` to `workspace_slug: str` (fixes HTTP 422 on all SSO config calls)
- SAML callback now issues Supabase JWT via `generate_link` + `verifyOtp`; frontend `SamlCallbackPage` handles token exchange
- `set_rls_context()` called before `write_audit_nonfatal` in SAML callback (fixes PostgreSQL `app.current_user_id` resolution for audit writes)

**Audit DI Gap Closure**
- `audit_log_repository` wired as `providers.Factory` (per-request) into 10 CRUD service DI factories: `CreateIssueService`, `UpdateIssueService`, `DeleteIssueService`, `CreateNoteService`, `UpdateNoteService`, `DeleteNoteService`, `CreateCycleService`, `UpdateCycleService`, `AddIssueToCycleService`, `RbacService`
- `session_factory` stored on `PilotSpaceAgent` and passed to `PermissionAwareHookExecutor` in `_stream_with_space` — AI audit writes now reach the database

### Fixed

- SAML login loop: callback now issues JWT so login completes end-to-end
- Rate limiting was silently inactive: `RateLimitMiddleware` was registered inside lifespan (stack already frozen); moved to module level with lazy `_resolve_redis()` accessor
- Storage quota: quota helpers were implemented but never called on write paths; wired into all 5 create/update routes
- SCIM token generation endpoint was missing; added `POST /workspaces/{slug}/settings/scim-token`
- RLS enum mismatch: policies used UPPERCASE, some migrations stored lowercase; migration 066 fixes consistency

## [0.1.0-alpha.2] - 2026-02-26

### Added

- Chat context attachments: local file upload (PDF, DOCX, images, code, text) injected as Claude content blocks per conversation turn (Feature 020)
- Google Drive integration: OAuth PKCE flow, Drive file browser, import-as-attachment for Docs/Sheets/Slides with auto-export to PDF/CSV; `GET /ai/drive/auth-url`, `GET /ai/drive/callback`, `GET /ai/drive/files`, `POST /ai/drive/import`, `DELETE /ai/drive/credentials` (Feature 020)
- `DriveOAuthService` with Redis-backed PKCE state for multi-worker deployments; 10-min TTL; in-memory fallback for tests
- Silent token refresh: `DriveFileService` proactively refreshes access token 5 min before expiry; mid-request 401 triggers single retry
- `DriveFilePicker` component with folder navigation, search, and pagination
- `AttachmentButton` with upload progress, retry on failure, and Drive picker integration
- `useAttachments` hook: retry now re-submits original `File` reference stored on attachment state
- Two-phase attachment ownership/expiry check: 403 for not-owned vs 400 for expired (distinct UX errors)
- `drive_file_id` stored on `ChatAttachment` for Drive-sourced files
- Guest restriction enforced at router level for attachment upload and Drive auth URL endpoints

### Fixed

- Raw `httpx.HTTPStatusError` detail redacted from 502 `DRIVE_API_ERROR` responses; error now logged server-side only
- OAuth callback returns `302 RedirectResponse` (not JSON) matching Google's redirect expectation
- Role for Drive auth-url fetched from DB — removed insecure caller-supplied `user_role` query parameter

## [0.1.0-alpha.1] - 2026-02-26

### Added

- Agent wiki documentation covering PilotSpaceAgent orchestrator, subagents, MCP tools, skills, ChatView components, and editor AI extensions
- `ProjectContextHeader` component with navigation tabs (notes, issues) across note and issue detail pages
- GitHub integration: end-to-end webhook sync, MCP tools (6 new tools), PR review panel in issue detail
- ChatView AI commands in issue editor (`/plan`, `/decompose`, `/enhance`, note card links)
- AI implementation plan generation for issues with markdown export
- Terminal streaming view for Claude Code plan execution
- Intent engine service with background job worker
- Block ownership engine with attribution tracking
- Collaboration toolbar with change attribution TipTap extension
- PM blocks capacity fields: `estimate_hours` on issues, `weekly_available_hours` on members
- Note editor enhancements: linking, gutter TOC, issue indicators, project picker
- Landing page with 12 sections and AI interaction demos
- Daily routine contextual AI chat experience
- Tri-view issue management: Board, List, Table with unified filter bar
- 6-layer dynamic prompt assembly for PilotSpaceAgent
- Project list and detail pages with real API integration
- Issue detail 9 UX improvements with note-first redesign

### Changed

- Ghost text migrated from Gemini Flash to Claude Haiku
- Issue detail redesigned with Note-First layout (TipTap note canvas + ChatView tab)
- `NoteCanvasLayout` unwrapped from `observer()` to fix React 19 flushSync conflict

### Fixed

- Resolved 19 API contract mismatches between backend and frontend
- Fixed state blink in collapsed property block view (4 progressive fixes)
- Fixed `AttributeError` on `User.name` in approval endpoints causing 500 errors
- Fixed empty chip display and suggestion loading state in note links
- Fixed `link_type` uppercase serialization mismatch in issue detail
- Fixed 3 webhook and activity bugs in PRReviewSubagent

### Security

- Pre-mutation IDOR checks added to all 6 issue mutation endpoints
- RLS context now enforced before DB query in `require_workspace_member`
- Atomic Redis rate limiters replace TOCTOU in-memory counters in ghost text and AI context
- Fail-closed Redis policy prevents rate limit bypass on infrastructure outage

## [0.0.4] - 2026-02-11

### Added

- PM Note Extensions: 10 block types (RACI, Risk Matrix, ADR, System Diagram, Mermaid, Decision Log, Dashboard, Timeline, Capacity Plan, Checklist)
- Persistent task management with AI decomposition and context export
- Approval & user input UX overhaul with MCP interaction server
- Multi-question wizard with `skipWhen` logic and "Other" option
- Tool call event persistence for session resume rendering
- AI ChatView: 10 design improvements including auto-collapse and block navigation
- Homepage Hub 3-zone layout with recent notes, active issues, and AI activity feed
- Role-skills: MCP tools + 8 role templates (Features 010-011)
- Onboarding: 3-step wizard merged into single two-panel form
- MCP tools expanded from 6 to 27 across 4 categories (notes, issues, projects, workspace)
- `focus_block` SSE event with edit guard and visual feedback
- Note editor: table/list support, linked issues display, line gutter
- Issue extraction: full flow with selection + creation UI

### Changed

- `AIContextSubagent` replaced by `PilotSpaceAgent` delegation (DD-086)
- GhostTextService wired into DI container with BYOK, client pool, ResilientExecutor, CostTracker
- DI container split to resolve circular imports; session store ORM errors fixed
- Auth, workspace, and issues routers migrated to service layer
- RLS enum case corrected in policies (`OWNER`, `ADMIN`, `MEMBER`, `GUEST`)

### Fixed

- Fixed race condition in issue `sequence_id` generation
- Fixed XSS vulnerability in PM block renderer and added error boundary
- Added workspace verification to all AI mutation tools
- Fixed stale error state, type safety, and accessibility issues in ghost text
- Hardened ghost text against prompt injection attacks

## [0.0.3] - 2026-02-06

### Added

- AI chat: thinking blocks, tool call cards, streaming UX
- SSE delta buffer for event reduction (water pumping pattern)
- Multi-context session architecture with resume support
- Compact layout redesign with sidebar controls migration
- AI Context Tab in issue detail with structured SSE sections

### Fixed

- Fixed 3 critical security and persistence issues in the AI layer
- Fixed auto-restore of conversation history when opening a note page
- Fixed `write_to_note` tool, workspace headers, and removed deprecated agent
- Fixed metadata attribute mismatch and null-safety in activity tracking

## [0.0.2] - 2026-02-04

### Added

- PilotSpace Conversational Agent Architecture (Waves 1-8): PilotSpaceAgent orchestrator with skill dispatch
- SSE streaming for all AI interactions
- Claude Agent SDK integration for GhostTextAgent, PRReviewAgent, AIContextAgent
- Session resume: auto-restore conversation history
- MCP tool registry: 6 initial tools (notes/issues)
- Approval queue: backend persistence + frontend queue UI
- AssigneeRecommenderAgent with expertise loading
- MarginAnnotationAgent with SDK
- IssueExtractorAgent with confidence tags

### Changed

- Demo user fallback removed; real Supabase Auth required

### Fixed

- Fixed real-time `StreamEvent` forwarding with deduplication and session leak prevention
- Remediated 17 high-priority security findings across backend and frontend

## [0.0.1] - 2026-01-25

### Added

- Note Canvas with block-based TipTap editor (13 extensions)
- Issue management with state machine (Backlog → Todo → In Progress → In Review → Done)
- Ghost text AI (500ms trigger, Tab accept, Escape dismiss)
- PR Review Agent with GitHub webhook integration
- Margin Annotation Agent
- Issue Extraction with confidence tags
- Approval queue backend
- Cost Dashboard with charts and analytics
- BYOK configuration for Anthropic and Gemini providers
- Workspace multi-tenant isolation with Supabase Row-Level Security
- 21 Alembic database migrations
- SSE streaming for all AI endpoints
- Supabase Auth + JWT middleware
- Redis session cache (30-min sliding TTL)
- Meilisearch full-text search integration
- pgvector 768-dim HNSW embeddings for semantic search

[Unreleased]: https://github.com/TinDang97/pilot-space/compare/v1.0.0-alpha3...HEAD
[1.0.0-alpha3]: https://github.com/TinDang97/pilot-space/compare/v1.0.0-alpha2...v1.0.0-alpha3
[1.0.0-beta]: https://github.com/TinDang97/pilot-space/compare/v0.1.0-alpha.2...v1.0.0-beta
[0.1.0-alpha.2]: https://github.com/TinDang97/pilot-space/compare/0.0.4-fixed...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/TinDang97/pilot-space/compare/0.0.4-fixed...v0.1.0-alpha.1
[0.1.0-alpha.1]: https://github.com/TinDang97/pilot-space/compare/v0.0.4...v0.1.0-alpha.1
[0.0.4]: https://github.com/TinDang97/pilot-space/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/TinDang97/pilot-space/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/TinDang97/pilot-space/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/TinDang97/pilot-space/releases/tag/v0.0.1
