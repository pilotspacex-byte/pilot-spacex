# Pilot Space MVP Implementation Plan

**Version**: 1.0.0
**Date**: 2026-02-01
**Branch**: `005-conversational-agent-arch`
**Architecture Grade**: B+ (83/100)
**Current State**: 75-80% MVP complete

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Implementation Status](#current-implementation-status)
3. [Phase 1: Foundation & SDK Integration](#phase-1-foundation--sdk-integration)
4. [Phase 2: Skill Migration](#phase-2-skill-migration)
5. [Phase 3: Backend Consolidation](#phase-3-backend-consolidation)
6. [Phase 4: Frontend Architecture](#phase-4-frontend-architecture)
7. [Phase 5: Integration & Testing](#phase-5-integration--testing)
8. [Phase 6: Polish & Refinement](#phase-6-polish--refinement)
9. [Critical Path](#critical-path)
10. [Risk Register](#risk-register)
11. [Quality Gates per Phase](#quality-gates-per-phase)
12. [Dependency Map](#dependency-map)
13. [ROI Analysis](#roi-analysis)

---

## Executive Summary

The Pilot Space MVP implements a **centralized conversational agent architecture** migrating from 13 siloed agents to 1 orchestrator + 3 subagents + 8 skills. The implementation follows a 6-phase plan with 152+ tasks across 20.5 weeks.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Total Tasks** | 152 + 21 critical = 173 |
| **Completed** | ~130 (75-80%) |
| **Remaining** | ~43 tasks |
| **Timeline (remaining)** | 4-6 weeks focused effort |
| **Backend LOC** | 69,435 lines Python |
| **Frontend LOC** | 60,010 lines TypeScript |
| **Database Migrations** | 19 applied |
| **Backend Tests** | 113 tests |
| **Frontend Tests** | 23 tests |
| **Architecture Grade** | B+ (83/100) |

### What's Done

- Backend API: 20 routers, complete REST API
- Infrastructure: Database (19 migrations), Redis, Meilisearch, Supabase Auth
- AI Layer: Claude SDK integration, MCP tools, session management, cost tracking
- Frontend: 25 ChatView components, MobX stores, TipTap editor scaffold
- Application Services: CQRS-lite pattern across all domains

### What Remains (Critical Path)

1. Ghost Text feature (frontend TipTap extension + SSE streaming)
2. Margin Annotations UI (positioning, real-time sync)
3. Issue Extraction Approval Modal (preview, diff, bulk ops)
4. Note MCP Tools E2E testing (all 6 tools)
5. PilotSpaceStore wiring (MobX → API → SSE)
6. E2E test coverage (>80%)
7. Security audit (RLS, session binding, GDPR)

---

## Current Implementation Status

### Backend Status (by Layer)

| Layer | Module | Status | Completion |
|-------|--------|--------|------------|
| **API** | 20 routers (workspaces, projects, issues, notes, ai_chat, ai_sessions, ai_approvals, ai_extraction, ai_annotations, ai_costs, ai_pr_review, ai_configuration, cycles, integrations, auth, webhooks, debug) | Production-ready | 95% |
| **Application** | Service Classes (note, issue, cycle, ai_context, integration, annotation, discussion) | Production-ready | 90% |
| **Domain** | Entities, value objects, domain services | Complete | 95% |
| **Infrastructure** | Database (26 models, 17 repos, 19 migrations), Redis, Auth, Queue, Search | Complete | 95% |
| **AI** | PilotSpaceAgent, SDK config, session handler, permission handler, hooks | Functional | 85% |
| **AI Tools** | Note tools (6), search tools, database tools, GitHub tools, MCP server | Skeleton + partial | 70% |
| **AI Providers** | Provider selector, mock generators, factory | Complete | 90% |
| **AI Infrastructure** | Cost tracker, key storage, rate limiter, approval, resilience | Complete | 90% |
| **AI Workers** | Conversation worker, queue processing | Functional | 80% |
| **Spaces** | Workspace sync, note markdown files | Functional | 85% |

### Frontend Status (by Feature)

| Feature | Components | Status | Completion |
|---------|------------|--------|------------|
| **Note Editor** | TipTap extensions (8), editor hooks, toolbar | Scaffold + partial | 65% |
| **Ghost Text** | Extension skeleton, service | Skeleton | 30% |
| **Margin Annotations** | Extension skeleton, list component | Skeleton | 25% |
| **Issue Extraction** | Panel skeleton, approval modal skeleton | Skeleton | 30% |
| **ChatView** | 25 components (complete tree) | Production-ready | 95% |
| **Issue Features** | AI context panel, conversation, prompts | Functional | 75% |
| **Cycle/Sprint** | Board, burndown, velocity, rollover | Scaffold | 60% |
| **GitHub Integration** | PR review, commits, branches | Functional | 75% |
| **Approval Queue** | Card, detail modal, list | Functional | 80% |
| **Cost Dashboard** | Summary, charts, table | Scaffold | 50% |
| **MobX Stores** | 12 stores (Root, Workspace, Auth, UI, AI, etc.) | Functional | 80% |
| **API Services** | 9 API clients | Complete | 90% |
| **UI Components** | 25 shadcn/ui components | Complete | 95% |

### Test Coverage

| Area | Tests | Coverage | Target |
|------|-------|----------|--------|
| Backend Unit | 80+ | ~60% | >80% |
| Backend Integration | 20+ | ~40% | >80% |
| Backend E2E | 13 (scaffolds) | ~20% | >80% |
| Frontend Unit | 15+ | ~30% | >80% |
| Frontend Integration | 8+ | ~20% | >80% |
| Frontend E2E | Playwright configured | ~5% | >80% |

---

## Phase 1: Foundation & SDK Integration

**Duration**: 3.5 weeks (core) + 1.5 weeks (critical additions)
**Status**: ~85% complete
**Remaining**: Error handling, cost optimization validation, security hardening

### P1: Core SDK Configuration (MOSTLY DONE)

| Task ID | Task | Status | DoD |
|---------|------|--------|-----|
| P1-001 | Claude Agent SDK configuration (`ai/sdk/config.py`) | ✅ Done | SDK initializes with BYOK keys |
| P1-002 | Session handler (`ai/sdk/session_handler.py`) | ✅ Done | Multi-turn conversations work |
| P1-003 | Permission handler (`ai/sdk/permission_handler.py`) | ✅ Done | `canUseTool` callback blocks critical actions |
| P1-004 | Hooks system (`ai/sdk/hooks.py`) | ✅ Done | PreToolUse/PostToolUse hooks fire |
| P1-005 | Session store (`ai/sdk/session_store.py`) | ✅ Done | Sessions persist to PostgreSQL |
| P1-006 | Provider selector (`ai/providers/provider_selector.py`) | ✅ Done | Routes tasks to correct provider per DD-011 |

### P1: Error Handling & Resilience (REMAINING)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P1-007 | Circuit breaker for LLM providers | ✅ Done | `ai/infrastructure/resilience.py` exists | 5-failure threshold, 60s recovery |
| P1-008 | Retry with exponential backoff | ✅ Done | Uses `tenacity` library | 3 retries, 1-10s wait |
| P1-009 | SSE abort controller | ⬜ TODO | Backend AbortController terminates streams | Client disconnect → cleanup within 5s |
| P1-010 | Offline message queue | ⬜ TODO | Messages queued when API unavailable | Queue depth visible in admin, auto-retry |
| P1-011 | Rate limit handling for AI endpoints | ✅ Done | 100 req/min per workspace | 429 response with retry-after header |

### P1: Cost Optimization (REMAINING)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P1-012 | Prompt caching (`cache_control: ephemeral`) | ⬜ TODO | System prompts cached across requests | Verify 63% cost reduction in logs |
| P1-013 | Context window management | ⬜ TODO | Prune at 50k tokens, preserve recent 10 msgs | Token count logged per request |
| P1-014 | Token budget enforcement | ⬜ TODO | `max_tokens=4096` per request | Budget exceeded → graceful stop |
| P1-015 | Cost tracking per request | ✅ Done | `ai/infrastructure/cost_tracker.py` | Per-user and per-workspace totals |

### P1: Database Schema (DONE)

| Task ID | Task | Status | DoD |
|---------|------|--------|-----|
| P1-016 | ChatSession model | ✅ Done | Migration 020 applied |
| P1-017 | ChatMessage model | ✅ Done | Stores role, content, tool_calls JSONB |
| P1-018 | TokenUsage model | ✅ Done | Tracks prompt/completion/cached tokens |
| P1-019 | Session security (IP binding, 24h TTL) | ⬜ TODO | IP hash stored, expired sessions cleaned |

---

## Phase 2: Skill Migration

**Duration**: 2 weeks
**Status**: ~70% complete
**Remaining**: Skill validation, testing, structured output schemas

### P2: Skill Implementation

| Task ID | Skill | Status | DoD | Acceptance Criteria |
|---------|-------|--------|-----|---------------------|
| P2-001 | `extract-issues` | ✅ Done | Identifies actionable items from notes | Returns structured JSON with title, description, priority, confidence |
| P2-002 | `enhance-issue` | ✅ Done | Improves issue title/description | Generates acceptance criteria, suggests labels |
| P2-003 | `improve-writing` | ✅ Done | Enhances text clarity and style | Preserves user voice, returns markdown |
| P2-004 | `summarize` | ✅ Done | Multi-format content summarization | Supports bullet, executive, detailed formats |
| P2-005 | `find-duplicates` | ⬜ TODO | Vector search for similar issues | Returns candidates with similarity >70%, ranked |
| P2-006 | `recommend-assignee` | ⬜ TODO | Expertise-based assignment | Considers workload balance, historical assignments |
| P2-007 | `decompose-tasks` | ✅ Done | Break features into subtasks | Generates Claude Code prompts per task |
| P2-008 | `generate-diagram` | ✅ Done | Mermaid/C4 diagram generation | Valid Mermaid syntax, renders in frontend |

### P2: Skill Infrastructure

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P2-009 | Skill registry (`ai/skills/registry.py`) | ✅ Done | Auto-discovers skills from `.claude/skills/` | Loads metadata at startup |
| P2-010 | Skill validation | ⬜ TODO | Validates YAML frontmatter + markdown body | Invalid skills logged with clear error |
| P2-011 | Structured output schemas | ⬜ TODO | JSON Schema for each skill output | Schema validation on every skill response |

---

## Phase 3: Backend Consolidation

**Duration**: 4 weeks
**Status**: ~80% complete
**Remaining**: Note MCP tools E2E, subagent streaming, SSE transform pipeline

### P3: PilotSpaceAgent (MOSTLY DONE)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P3-001 | PilotSpaceAgent orchestrator | ✅ Done | `ai/agents/pilotspace_agent.py` | Routes to skills and subagents |
| P3-002 | Unified `/api/v1/ai/chat` endpoint | ✅ Done | Single POST endpoint with SSE | Handles skill invocation, subagent spawn, natural language |
| P3-003 | Intent parsing | ✅ Done | Detects `\skill`, `@agent`, free text | Correct routing in >90% of test cases |
| P3-004 | Context aggregation | ✅ Done | Builds context from note/issue/project | Context passed to all skill/subagent invocations |

### P3: MCP Note Tools (CRITICAL - REMAINING)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P3-005 | `update_note_block` E2E | ⬜ TODO | Replace/append block content in TipTap | Block ID preserved, SSE event emitted, frontend updates |
| P3-006 | `enhance_text` E2E | ⬜ TODO | Improve clarity without meaning change | Original block preserved for undo, diff available |
| P3-007 | `summarize_note` E2E | ⬜ TODO | Read full note with block structure | Returns markdown with block IDs |
| P3-008 | `extract_issues` E2E | ⬜ TODO | Create linked issues from blocks | Issues created in DB, NoteIssueLink records, inline badges |
| P3-009 | `create_issue_from_note` E2E | ⬜ TODO | Create single linked issue | Issue linked to source block |
| P3-010 | `link_existing_issues` E2E | ⬜ TODO | Search and link existing issues | Meilisearch integration returns ranked results |

### P3: Subagent Refactoring

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P3-011 | PRReviewAgent as subagent | ✅ Done | Spawned by PilotSpaceAgent via `Task` tool | Streams review output via SSE |
| P3-012 | AIContextAgent as subagent | ✅ Done | Multi-turn context building | Aggregates docs, code, similar issues |
| P3-013 | DocGeneratorAgent as subagent | ✅ Done | Long-form documentation generation | Progress tracking via task panel |

### P3: SSE Transform Pipeline

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P3-014 | `transform_sdk_message()` | ⬜ TODO | SDK message → Frontend SSE event | 8 event types mapped correctly |
| P3-015 | Content update events | ⬜ TODO | Note block changes → `content_update` SSE | Frontend editor receives and applies updates |

---

## Phase 4: Frontend Architecture

**Duration**: 4.5 weeks (core) + 0.5 weeks (optimistic updates)
**Status**: ~60% complete (ChatView done, store wiring remaining)
**Remaining**: PilotSpaceStore wiring, Ghost Text, Margin Annotations, Issue Extraction UI

### P4: Store Architecture (CRITICAL)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P4-001 | PilotSpaceStore wiring to API | ⬜ TODO | Store actions call backend endpoints | `sendMessage()` → POST /ai/chat → SSE updates store |
| P4-002 | SSE event handler mapping | ⬜ TODO | 8 event types → store mutations | `message_start`, `text_delta`, `tool_use`, `tool_result`, `task_progress`, `approval_request`, `message_stop`, `error` |
| P4-003 | Optimistic update pattern | ⬜ TODO | PendingOperations map with rollback | Show message immediately, replace on server response |
| P4-004 | Error reconciliation | ⬜ TODO | Handle 409, 429, 500, 503 errors | Specific UI feedback per error type |

### P4: Ghost Text Feature (CRITICAL)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P4-005 | Complete `GhostTextExtension.ts` | ⬜ TODO | TipTap extension renders ghost text at 40% opacity | Appears after 500ms typing pause |
| P4-006 | SSE streaming integration | ⬜ TODO | Connect to ghost text SSE endpoint | Character-by-character streaming |
| P4-007 | Keyboard handling | ⬜ TODO | Tab = full accept, → = word-by-word, Esc = dismiss | All three actions work reliably |
| P4-008 | Context window | ⬜ TODO | Send current block + 3 previous + sections summary | Max 2000 char context window |
| P4-009 | Word boundary handling (DD-067) | ⬜ TODO | Stop at natural sentence/paragraph boundaries | Max 100-150 char suggestions |

### P4: Margin Annotations (CRITICAL)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P4-010 | Annotation card component | ⬜ TODO | Displays AI suggestion with confidence badge | Supports suggestion, improvement, question, reference types |
| P4-011 | Vertical stacking positioning | ⬜ TODO | Annotations align with source blocks | No overlapping, smooth scroll sync |
| P4-012 | Real-time sync via SSE | ⬜ TODO | New annotations appear without refresh | Backend emits event, store updates, UI renders |
| P4-013 | Accept/dismiss actions | ⬜ TODO | User can apply or ignore suggestions | Applied suggestions update note block |

### P4: Issue Extraction UI (CRITICAL)

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P4-014 | Issue preview modal | ⬜ TODO | Shows extracted issue with editable fields | Title, description, priority, type all editable |
| P4-015 | Diff visualization | ⬜ TODO | Shows what text was extracted as source | Rainbow border highlights source block |
| P4-016 | Bulk approve/reject | ⬜ TODO | Select multiple issues for batch action | Checkboxes + "Approve All" / "Reject All" buttons |
| P4-017 | Inline issue badges | ⬜ TODO | `[PS-42]` badge appears in note after creation | Clicking badge opens issue detail |

### P4: Note Canvas Integration

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P4-018 | Wire all TipTap extensions | ⬜ TODO | All 8 extensions registered and functional | Ghost text, annotations, issue extraction, mentions, slash commands |
| P4-019 | Auto-save with conflict detection | ⬜ TODO | 2s debounce save with version check | Last-write-wins with conflict notification |
| P4-020 | Virtual scroll (1000+ blocks) | ⬜ TODO | @tanstack/react-virtual integration | 60fps scroll with 1000+ blocks |
| P4-021 | Auto-generated TOC | ⬜ TODO | Click-to-scroll + highlight sync | Updates on heading changes |

### P4: Remaining UI Pages

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P4-022 | Settings: AI Configuration page | ⬜ TODO | BYOK key entry with validation | Real-time key validation, secure storage |
| P4-023 | Settings: Integration setup | ⬜ TODO | GitHub/Slack connection UI | OAuth flow, webhook configuration |
| P4-024 | Cycle velocity/burndown binding | ⬜ TODO | Charts render with real data | Recharts integration with TanStack Query |
| P4-025 | Cost dashboard chart binding | ⬜ TODO | Cost trends + agent breakdown | Date range filtering, export CSV |

---

## Phase 5: Integration & Testing

**Duration**: 2.5 weeks (testing) + 0.5 weeks (security audit)
**Status**: ~15% complete
**Remaining**: E2E tests, performance testing, security audit

### P5: E2E Test Suites (CRITICAL)

| Task ID | Test | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P5-001 | Skill invocation via ChatView | ⬜ TODO | User types `\extract-issues` → issues created | Full flow: input → skill → output → UI update |
| P5-002 | Subagent invocation (streaming) | ⬜ TODO | User types `@code-reviewer` → streaming review | Progress visible in TaskPanel |
| P5-003 | Approval flow (extract → approve → create) | ⬜ TODO | AI extracts issues → user approves → DB persists | Rejection returns to conversation |
| P5-004 | Session resumption | ⬜ TODO | User returns to previous conversation | Context preserved across page reload |
| P5-005 | Task tracking (progress updates) | ⬜ TODO | Task status updates in real-time | Pending → In Progress → Completed visible |
| P5-006 | Error recovery (network failure) | ⬜ TODO | Network drops → reconnect → resume | Exponential backoff, max 3 attempts |

### P5: Backend Integration Tests

| Task ID | Test | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P5-007 | Note MCP tools integration | ⬜ TODO | All 6 tools work with real database | Block IDs preserved, SSE events emitted |
| P5-008 | GitHub webhook processing | ⬜ TODO | PR open → review → comment posted | Auto-post review to GitHub |
| P5-009 | Cycle velocity calculation | ⬜ TODO | Completed issues → velocity metric | Fibonacci-based story points |
| P5-010 | Duplicate detection accuracy | ⬜ TODO | Known duplicates detected at >70% | Threshold tuning with test dataset |

### P5: Frontend Integration Tests

| Task ID | Test | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P5-011 | Ghost text acceptance flow | ⬜ TODO | Pause → suggestion → Tab/→/Esc | All three keyboard actions tested |
| P5-012 | Margin annotation interaction | ⬜ TODO | Annotation appears → user accepts/dismisses | Note block updates correctly |
| P5-013 | Issue extraction from note | ⬜ TODO | Select text → extract → approve → badge appears | Bidirectional link created |
| P5-014 | SSE streaming reliability | ⬜ TODO | Long-running stream doesn't drop | Heartbeat detection, auto-reconnect |

### P5: Performance Testing

| Task ID | Test | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P5-015 | API read latency (p95) | ⬜ TODO | GET operations < 500ms | Measured with 100 concurrent users |
| P5-016 | API write latency (p95) | ⬜ TODO | POST/PUT/DELETE < 1s | Measured with 50 concurrent users |
| P5-017 | Ghost text response time | ⬜ TODO | Suggestion appears < 2s | Measured from pause to render |
| P5-018 | Note canvas 1000+ blocks | ⬜ TODO | Smooth scroll at 60fps | Virtual scroll handles 2000 blocks |

### P5: Security Audit

| Task ID | Task | Status | DoD | Acceptance Criteria |
|---------|------|--------|-----|---------------------|
| P5-019 | RLS policy verification | ⬜ TODO | All tables enforce workspace isolation | Cross-workspace query returns 0 rows |
| P5-020 | Session security | ⬜ TODO | Cryptographic IDs, IP binding, 24h expiry | Stolen session from different IP → rejected |
| P5-021 | Prompt injection defense | ⬜ TODO | Input sanitization on all AI endpoints | Known injection patterns blocked |
| P5-022 | API key encryption audit | ⬜ TODO | Supabase Vault AES-256-GCM verified | Keys never in logs, never in plaintext |
| P5-023 | GDPR user deletion | ⬜ TODO | Cascading delete removes all user data | Verify no orphaned records |
| P5-024 | Data retention policy | ⬜ TODO | 30-day cleanup for expired sessions | Automated cron job runs nightly |

---

## Phase 6: Polish & Refinement

**Duration**: 4 weeks (post-MVP, can run in parallel with MVP release)
**Status**: Not started
**Priority**: Post-MVP enhancement

### P6: UI/UX Refinement

| Task ID | Task | Priority |
|---------|------|----------|
| P6-001 | Loading skeletons for all pages | High |
| P6-002 | Empty state designs (no issues, no notes) | High |
| P6-003 | Message reactions (thumbs up/down for AI) | Medium |
| P6-004 | Copy-to-clipboard for AI outputs | Medium |
| P6-005 | Toast notification system | High |
| P6-006 | Error boundary components | High |

### P6: Animations

| Task ID | Task | Priority |
|---------|------|----------|
| P6-007 | Message entrance animation | Medium |
| P6-008 | Streaming cursor blink | Low |
| P6-009 | Task progress animation | Medium |
| P6-010 | Approval overlay slide-in | Medium |
| P6-011 | Ghost text fade-in | Low |
| P6-012 | Issue badge insertion animation | Low |

### P6: Accessibility (WCAG 2.2 AA)

| Task ID | Task | Priority |
|---------|------|----------|
| P6-013 | Screen reader support for ChatView | High |
| P6-014 | Keyboard navigation for all AI components | High |
| P6-015 | Focus management on modal open/close | High |
| P6-016 | ARIA labels for streaming content | Medium |
| P6-017 | High contrast mode support | Medium |
| P6-018 | Touch target sizes (44x44px minimum) | Medium |

### P6: Performance Optimization

| Task ID | Task | Priority |
|---------|------|----------|
| P6-019 | Message list virtualization | High |
| P6-020 | Pagination for long conversations | High |
| P6-021 | React.memo for message components | Medium |
| P6-022 | Lazy loading for AI panel | Medium |
| P6-023 | Image/attachment lazy loading | Low |
| P6-024 | Bundle size optimization (<200KB gzipped) | Medium |

### P6: Advanced Features (Post-MVP)

| Task ID | Task | Priority |
|---------|------|----------|
| P6-025 | Conversation search | Medium |
| P6-026 | Export conversation as markdown | Low |
| P6-027 | Conversation templates | Low |
| P6-028 | Analytics dashboard (AI usage) | Medium |
| P6-029 | Dark mode for all AI components | Medium |
| P6-030 | Mobile responsive layout | Low |

---

## Critical Path

```
P1: SDK Config (DONE)
    ↓
P1: Error Handling (P1-009, P1-010) → P3: SSE Transform (P3-014, P3-015)
    ↓
P2: Skill Migration (P2-005, P2-006, P2-010, P2-011)
    ↓
P3: Note MCP Tools E2E (P3-005 through P3-010) ← CRITICAL BLOCKER
    ↓
P4: PilotSpaceStore Wiring (P4-001, P4-002)
    ↓
P4: Ghost Text (P4-005 through P4-009) ← CRITICAL BLOCKER
    ↓
P4: Margin Annotations (P4-010 through P4-013)
    ↓
P4: Issue Extraction UI (P4-014 through P4-017)
    ↓
P4: Note Canvas Integration (P4-018 through P4-021)
    ↓
P5: E2E Tests (P5-001 through P5-006)
    ↓
P5: Security Audit (P5-019 through P5-024)
    ↓
MVP RELEASE
```

### Parallel Tracks

**Track A (Backend)**: P1-009/010 → P3-005:010 → P3-014/015 → P5-007:010
**Track B (Frontend)**: P4-001:004 → P4-005:009 → P4-010:017 → P4-018:025
**Track C (Testing)**: P5-001:006 (starts after Track A + B converge)
**Track D (Security)**: P5-019:024 (can start anytime, independent)

### Milestone Dates (Estimated)

| Milestone | Target | Dependencies |
|-----------|--------|--------------|
| Note MCP Tools E2E complete | Week 1 | P3-005 through P3-010 |
| Ghost Text feature complete | Week 2 | P4-005 through P4-009 |
| Store wiring + SSE complete | Week 2 | P4-001, P4-002 |
| Margin Annotations complete | Week 3 | P4-010 through P4-013 |
| Issue Extraction UI complete | Week 3 | P4-014 through P4-017 |
| Note Canvas fully integrated | Week 4 | P4-018 through P4-021 |
| E2E tests passing (>80%) | Week 5 | P5-001 through P5-014 |
| Security audit complete | Week 5 | P5-019 through P5-024 |
| **MVP Release** | **Week 6** | All above |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Ghost text latency > 2s | Medium | High | Use Gemini Flash, implement local caching |
| Claude SDK breaking changes | Low | Critical | Pin version, integration test suite |
| SSE streaming drops | Medium | Medium | Heartbeat detection, auto-reconnect with backoff |
| RLS policy gaps | Low | Critical | Automated policy verification tests |
| Token budget overruns | Medium | Medium | Hard limits + alerts at 90% |
| TipTap extension conflicts | Medium | High | Isolated extension testing, priority ordering |
| Note block ID corruption | Low | Critical | ContentConverter unit tests, block ID preservation tests |
| GitHub API rate limiting | Medium | Low | Exponential backoff, request queuing |

---

## Quality Gates per Phase

### Phase 1-3 (Backend)
```bash
# Run before any P1-P3 PR merge
uv run pyright && uv run ruff check && uv run pytest --cov=. -v
# Coverage must be >80% for changed files
# No new pyright errors
# No ruff warnings
```

### Phase 4 (Frontend)
```bash
# Run before any P4 PR merge
pnpm lint && pnpm type-check && pnpm test
# Coverage must be >80% for changed files
# No TypeScript strict errors
# No ESLint warnings
```

### Phase 5 (Integration)
```bash
# Run full E2E suite
pnpm test:e2e
# All E2E tests pass
# Performance SLOs met (p95 latency targets)
# Security audit checklist complete
```

### Pre-Release Gate
- [ ] All Phase 1-5 tasks completed
- [ ] Backend test coverage > 80%
- [ ] Frontend test coverage > 80%
- [ ] E2E test suite passes (6 critical paths)
- [ ] Security audit: RLS, sessions, GDPR, injection defense
- [ ] Performance: API p95 < 500ms, ghost text < 2s, 1000+ block canvas at 60fps
- [ ] No files > 700 lines
- [ ] No TODOs or placeholders in production paths
- [ ] All design decisions (DD-001 through DD-088) validated

---

## Dependency Map

### External Dependencies

| Dependency | Required By | Version | Risk |
|------------|-------------|---------|------|
| Claude Agent SDK | All AI features | >=1.0,<2.0 | Medium (new SDK) |
| Anthropic Python SDK | Backend AI | Latest | Low |
| OpenAI Python SDK | Embeddings | Latest | Low |
| google-generativeai | Ghost text | Latest | Low |
| TipTap | Note editor | 2.x | Low |
| MobX | Frontend state | 6.x | Low |
| TanStack Query | Server state | 5.x | Low |
| Supabase Auth | Authentication | Latest | Low |
| Redis | Caching | 7.x | Low |
| Meilisearch | Search | 1.6+ | Low |

### Internal Dependencies (Task)

```
P1-009 (SSE abort) → P3-014 (SSE transform)
P2-005 (find-duplicates) → P4-017 (duplicate detection UI)
P3-005:010 (Note MCP tools) → P4-014:017 (Issue extraction UI)
P3-014:015 (SSE transform) → P4-002 (SSE event handler)
P4-001 (Store wiring) → P4-005:025 (all frontend features)
P4-005:021 (all Note Canvas) → P5-001:006 (E2E tests)
```

---

## ROI Analysis

### Investment vs. Avoided Cost

| Category | Investment | Avoided Tech Debt | Ongoing Benefit |
|----------|-----------|-------------------|-----------------|
| Error Handling (P1-009:010) | 3 days | $50K | Emergency retrofit prevention |
| Cost Optimization (P1-012:014) | 2 days | $60K | $4.5K/year token savings |
| Database Schema (P1-016:019) | 2.5 days | $40K | Schema migration avoidance |
| Optimistic Updates (P4-003:004) | 2 days | $20K | State corruption debugging |
| Security Audit (P5-019:024) | 2.5 days | TBD | GDPR compliance |
| **TOTAL** | **12 days** | **$170K+** | **7-10x ROI** |

### Architecture Grade Improvement

| Area | Before | After | Delta |
|------|--------|-------|-------|
| SDK Integration | 70% | 95% | +25% |
| Error Handling | 40% | 90% | +50% |
| Cost Management | 30% | 85% | +55% |
| Frontend Store | 60% | 90% | +30% |
| Security | 50% | 85% | +35% |
| **Overall** | **B (78)** | **A- (90+)** | **+12+** |

---

## Task Execution Order (Optimized for Parallelism)

### Week 1: Backend Critical Path + Frontend Foundation
**Track A (Backend)**:
- P1-009: SSE abort controller
- P1-012: Prompt caching
- P3-005: `update_note_block` E2E
- P3-006: `enhance_text` E2E

**Track B (Frontend)**:
- P4-001: PilotSpaceStore wiring to API
- P4-002: SSE event handler mapping
- P4-005: Complete GhostTextExtension

### Week 2: Core Features
**Track A (Backend)**:
- P3-007: `summarize_note` E2E
- P3-008: `extract_issues` E2E
- P3-009: `create_issue_from_note` E2E
- P3-010: `link_existing_issues` E2E
- P3-014: SSE transform pipeline

**Track B (Frontend)**:
- P4-006: Ghost text SSE streaming
- P4-007: Ghost text keyboard handling
- P4-008: Ghost text context window
- P4-010: Annotation card component
- P4-011: Annotation positioning

### Week 3: Integration Features
**Track A (Backend)**:
- P2-005: `find-duplicates` skill
- P2-010: Skill validation
- P1-013: Context window management

**Track B (Frontend)**:
- P4-012: Annotation real-time sync
- P4-014: Issue preview modal
- P4-015: Diff visualization
- P4-016: Bulk approve/reject
- P4-018: Wire all TipTap extensions

### Week 4: Canvas Completion + Remaining UI
**Track A (Backend)**:
- P1-014: Token budget enforcement
- P2-006: `recommend-assignee` skill
- P3-015: Content update events

**Track B (Frontend)**:
- P4-019: Auto-save with conflict detection
- P4-020: Virtual scroll
- P4-021: Auto-generated TOC
- P4-022: Settings AI Configuration
- P4-024: Cycle velocity/burndown binding

### Week 5: Testing
**Track A (E2E)**:
- P5-001 through P5-006: All E2E test suites
- P5-007 through P5-010: Backend integration tests

**Track B (Performance + Security)**:
- P5-015 through P5-018: Performance testing
- P5-019 through P5-024: Security audit

### Week 6: Final Validation + Release
- Fix any failing tests
- Address security audit findings
- Final quality gate check
- Documentation update
- MVP Release

---

## Appendix: Design Decision References

Key decisions governing this implementation:

| DD | Decision | Impact on Plan |
|----|----------|----------------|
| DD-002 | BYOK model | Key storage in P1, validation in P4-022 |
| DD-003 | Critical-only approval | Approval flow in P4-014:017, P5-003 |
| DD-006 | Unified PR review | PRReviewAgent in P3-011 |
| DD-011 | Provider routing | Provider selector in P1-006 |
| DD-013 | Note-First workflow | Note canvas in P4-018:021 |
| DD-048 | Confidence tags | Skill output schemas in P2-011 |
| DD-058 | Claude SDK modes | SDK config in P1-001 |
| DD-064 | CQRS-lite | Service pattern in all backend tasks |
| DD-065 | MobX stores | Store architecture in P4-001:004 |
| DD-066 | SSE streaming | SSE transform in P3-014:015, P4-002 |
| DD-067 | Ghost text behavior | Ghost text feature in P4-005:009 |
| DD-086 | Centralized agent | PilotSpaceAgent in P3-001 |
| DD-087 | Skill system | Skill migration in P2-001:011 |
| DD-088 | MCP tool registry | Note tools in P3-005:010 |

---

*Document Version: 1.0.0*
*Last Updated: 2026-02-01*
*Author: Pilot Space Architecture Team*
