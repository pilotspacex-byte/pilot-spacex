# Changelog

All notable changes to Pilot Space are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/TinDang97/pilot-space/compare/v0.1.0-alpha.2...HEAD
[0.1.0-alpha.2]: https://github.com/TinDang97/pilot-space/compare/0.0.4-fixed...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/TinDang97/pilot-space/compare/0.0.4-fixed...v0.1.0-alpha.1
[0.1.0-alpha.1]: https://github.com/TinDang97/pilot-space/compare/v0.0.4...v0.1.0-alpha.1
[0.0.4]: https://github.com/TinDang97/pilot-space/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/TinDang97/pilot-space/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/TinDang97/pilot-space/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/TinDang97/pilot-space/releases/tag/v0.0.1
