# Pilot Space Architecture Documentation

**Version**: 2.0
**Date**: 2026-01-22
**Status**: Approved for MVP Implementation
**Constitution**: v1.1.0

---

## Table of Contents

- [Overview](#overview)
- [Architecture Style](#architecture-style)
- [Technology Stack](#technology-stack)
- [Architecture Documents](#architecture-documents)
- [Key Design Decisions](#key-design-decisions)
- [Quality Gates](#quality-gates)
- [Performance Targets](#performance-targets)
- [Security Principles](#security-principles)
- [AI QA Retrieval Index](#ai-qa-retrieval-index)
- [Related Documentation](#related-documentation)

---

## Overview

Pilot Space is an AI-augmented SDLC platform implementing a **"Note-First"** workflow where users brainstorm with AI in collaborative documents, and issues emerge naturally from refined thinking. This document provides the architectural blueprint for the MVP implementation.

### Core Differentiator

> **"Think first, structure later"**

| Traditional PM Tools | Pilot Space |
|---------------------|-------------|
| Start with forms → Fill fields → Submit | Start with notes → Write thoughts → AI extracts |
| Structure imposed upfront | Structure emerges from thinking |
| Dashboard as home | **Note Canvas as home** |
| AI bolt-on (autocomplete) | AI embedded (co-writing partner) |

---

## Architecture Style

**Clean Architecture + Domain-Driven Design (DDD) + CQRS-lite**

The system follows Clean Architecture principles with DDD tactical patterns and CQRS-lite for command/query separation:

- **Independence from frameworks**: Business logic doesn't depend on FastAPI or Next.js
- **Testability**: Domain and application layers are pure Python/TypeScript
- **Independence from UI**: The UI can change without affecting business rules
- **Independence from database**: SQLAlchemy is an implementation detail
- **Independence from external services**: LLM providers, GitHub, Slack are adapters

### Layer Dependency Rule

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION                              │
│                    (API, Web, CLI)                               │
├─────────────────────────────────────────────────────────────────┤
│                        APPLICATION                               │
│              (Use Cases: Commands + Queries)                     │
├─────────────────────────────────────────────────────────────────┤
│                          DOMAIN                                  │
│              (Entities, Value Objects, Events)                   │
├─────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                              │
│           (Database, Cache, External Services)                   │
└─────────────────────────────────────────────────────────────────┘

Dependencies point INWARD only (outer layers depend on inner layers)
```

---

## Technology Stack

### Platform: Supabase (Session 2026-01-22)

Pilot Space uses **Supabase** as the unified backend platform, consolidating 10+ services into 3 core services.

| Component | Technology | Purpose |
|-----------|------------|---------|
| Database | PostgreSQL 16+ | Primary database with RLS |
| Vector Store | pgvector (built-in) | Embeddings for RAG |
| Auth | Supabase Auth (GoTrue) | JWT authentication + SAML SSO |
| Storage | Supabase Storage | S3-compatible file storage |
| Queues | Supabase Queues (pgmq) | Async background tasks |
| Scheduler | pg_cron | Database-scheduled jobs |
| Realtime | Supabase Realtime | WebSocket for live updates |

### Backend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | FastAPI | 0.110+ | REST API with OpenAPI docs |
| ORM | SQLAlchemy | 2.0+ | Async database operations |
| Migrations | Alembic | 1.13+ | Database schema versioning |
| Validation | Pydantic | 2.6+ | Request/response validation |
| DI | dependency-injector | 4+ | Dependency injection container |
| AI SDK | Claude Agent SDK | latest | AI agent orchestration |
| Cache | Redis | 7+ | Session cache, AI response cache |
| Search | Meilisearch | 1.6+ | Typo-tolerant full-text search |
| Runtime | Python | 3.12+ | Latest Python features |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | Next.js | 14+ | App Router, Server Components |
| UI Library | React | 18+ | Component framework |
| State | MobX | 6+ | Complex UI state management |
| Server State | TanStack Query | 5+ | API cache and sync |
| Styling | TailwindCSS | 3.4+ | Utility-first CSS |
| Rich Text | TipTap | 2+ | ProseMirror-based editor |
| Language | TypeScript | 5.3+ | Type safety |

### External Services

| Service | Purpose | Integration |
|---------|---------|-------------|
| GitHub | Repository integration | GitHub App |
| Slack | Team notifications | Events API |
| OpenAI | LLM provider (BYOK) | REST API |
| Anthropic | LLM provider (BYOK) | Claude Agent SDK |
| Google | LLM provider (BYOK) | REST API |

---

## Architecture Documents

| Document | Description |
|----------|-------------|
| [Feature-Story Mapping](./feature-story-mapping.md) | 18 user stories mapped to architecture |
| [Backend Architecture](./backend-architecture.md) | FastAPI + Clean Architecture + CQRS-lite |
| [Frontend Architecture](./frontend-architecture.md) | Next.js App Router + MobX |
| [AI Layer](./ai-layer.md) | AI orchestration and 16 agents |
| [**PilotSpace Agent Architecture**](./pilotspace-agent-architecture.md) | **Centralized conversational AI with subagent orchestration** |
| [Claude Agent SDK Architecture](./claude-agent-sdk-architecture.md) | SDK integration patterns |
| [Infrastructure](./infrastructure.md) | Supabase platform, Docker, deployment |
| [Supabase Integration](./supabase-integration.md) | Detailed Supabase patterns |
| [Design Patterns](./design-patterns.md) | Patterns and conventions |
| [Project Structure](./project-structure.md) | Directory layout and conventions |
| [Features Checklist](./FEATURES_CHECKLIST.md) | Implementation tracking |

---

## Key Design Decisions

| ID | Decision | Reference |
|----|----------|-----------|
| DD-001 | FastAPI replaces Django entirely | `docs/DESIGN_DECISIONS.md` |
| DD-002 | BYOK with Claude Agent SDK orchestration | `docs/DESIGN_DECISIONS.md`, `claude-agent-sdk-architecture.md` |
| DD-003 | Critical-only approval for AI actions (Human-in-the-loop) | `docs/DESIGN_DECISIONS.md`, `claude-agent-sdk-architecture.md` |
| DD-004 | MVP integrations: GitHub + Slack only | `docs/DESIGN_DECISIONS.md` |
| DD-005 | Supabase Realtime for state notifications (no co-editing in MVP) | Session 2026-01-22 |
| DD-006 | Unified PR Review (architecture + code + security) | `docs/DESIGN_DECISIONS.md`, `claude-agent-sdk-architecture.md` |
| DD-011 | Provider routing (Claude for code, Gemini for latency, OpenAI for embeddings) | `docs/DESIGN_DECISIONS.md`, `claude-agent-sdk-architecture.md` |
| DD-013 | Note-First, not Ticket-First workflow | `docs/DESIGN_DECISIONS.md` |
| DD-048 | AI confidence tags (Recommended/Default/Current/Alternative) | `docs/DESIGN_DECISIONS.md`, `claude-agent-sdk-architecture.md` |
| - | Supabase platform (Auth, Storage, Queues) | Session 2026-01-22 |
| - | CQRS-lite with Use Case Classes | Session 2026-01-22 |
| - | MobX for frontend state (not Zustand) | Session 2026-01-22 |
| - | SSE for AI streaming (not WebSocket) | research.md |

---

## Quality Gates

All code must pass before merge:

### Backend

```bash
# Run all quality checks
uv run pyright && uv run ruff check && uv run pytest --cov=.
```

| Gate | Tool | Requirement |
|------|------|-------------|
| Type Check | pyright | Strict mode, zero errors |
| Lint | ruff | Zero warnings |
| Test Coverage | pytest-cov | >80% coverage |
| File Size | pre-commit | 700 lines max |

### Frontend

```bash
# Run all quality checks
pnpm lint && pnpm type-check && pnpm test
```

| Gate | Tool | Requirement |
|------|------|-------------|
| Type Check | tsc | Strict mode, zero errors |
| Lint | ESLint | Zero warnings |
| Test Coverage | Jest/Vitest | >80% coverage |
| File Size | custom | 700 lines max |

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| API read (p95) | <500ms | GET operations |
| API write (p95) | <1s | POST/PUT/DELETE |
| Ghost text | <2s | After 500ms typing pause |
| PR review | <5min | Complete AI review |
| Search | <2s | 10K item workspace |
| Note canvas | 60fps | 1000+ blocks |

---

## Security Principles

1. **Authentication**: Supabase Auth (GoTrue) with JWT tokens
2. **Authorization**: Row-Level Security (RLS) + RBAC (Owner/Admin/Member/Guest)
3. **API Security**: Rate limiting (1000 req/min, 100 req/min AI), input validation, CORS
4. **Data Protection**: Encryption at rest, TLS in transit
5. **Secrets**: Supabase Vault for encrypted API key storage
6. **AI Safety**: Human-in-the-loop for critical actions

---

## AI QA Retrieval Index

This index helps AI assistants quickly locate specific information across all architecture documents. Each entry includes document path, section headers, and key topics.

### 📋 Quick Reference by Topic

| Topic | Document | Section | Key Information |
|-------|----------|---------|-----------------|
| **Architecture Style** | [README.md](#architecture-style) | Architecture Style | Clean Architecture + DDD + CQRS-lite patterns |
| **Technology Stack** | [README.md](#technology-stack) | Technology Stack | Backend/Frontend/Platform tech choices |
| **Supabase Platform** | [supabase-integration.md](./supabase-integration.md) | All sections | Auth, DB, Storage, Queues, Realtime integration |
| **Layer Dependencies** | [README.md](#layer-dependency-rule) | Layer Dependency Rule | Dependency flow diagram |
| **CQRS Pattern** | [backend-architecture.md](./backend-architecture.md#cqrs-lite-pattern) | CQRS-lite Pattern | Command/Query separation |
| **AI Agents** | [ai-layer.md](./ai-layer.md) | All sections | 9 primary + 7 helper agents, providers, orchestration |
| **PilotSpace Agent** | [pilotspace-agent-architecture.md](./pilotspace-agent-architecture.md) | All sections | Centralized conversational AI, subagents, skills, chat UI |
| **Frontend State** | [frontend-architecture.md](./frontend-architecture.md#state-management) | State Management | MobX + TanStack Query patterns |
| **Note Canvas** | [frontend-architecture.md](./frontend-architecture.md#tiptap-editor-integration) | TipTap Editor Integration | Block editor, Ghost Text extension |
| **RLS Policies** | [rls-patterns.md](./rls-patterns.md) | All sections | Row-level security patterns |
| **Project Structure** | [project-structure.md](./project-structure.md) | All sections | Directory layout, file organization |
| **Design Patterns** | [design-patterns.md](./design-patterns.md) | All sections | Repository, UoW, Value Objects, etc. |
| **Infrastructure** | [infrastructure.md](./infrastructure.md) | All sections | Docker, deployment, environment config |
| **Feature Mapping** | [feature-story-mapping.md](./feature-story-mapping.md) | All sections | 18 user stories → architecture components |
| **System Diagrams** | [architecture-diagrams.md](./architecture-diagrams.md) | All sections | Mermaid diagrams for all layers |
| **Features Checklist** | [FEATURES_CHECKLIST.md](./FEATURES_CHECKLIST.md) | All sections | Implementation tracking |

---

### 📚 Document-by-Document Index

#### 1. [README.md](./README.md) - Main Overview
**Purpose**: Entry point for architecture documentation

**Sections & Key Topics**:
- **Overview** → Core differentiator: Note-First workflow
- **Architecture Style** → Clean Architecture + DDD + CQRS-lite
- **Layer Dependency Rule** → Dependency flow (inward only)
- **Technology Stack** → Complete tech inventory
  - Platform: Supabase (Auth, DB, Storage, Queues)
  - Backend: FastAPI, SQLAlchemy, Pydantic
  - Frontend: Next.js 14, React 18, MobX, TanStack Query
- **Architecture Documents** → Links to all detail docs
- **Key Design Decisions** → 13 critical decisions (DD-001 to DD-013)
- **Quality Gates** → Type checking, linting, test coverage requirements
- **Performance Targets** → SLA metrics for API, AI, search, UI
- **Security Principles** → Auth, authz, RLS, RBAC, secrets management

**AI Query Examples**:
- "What is the core architecture pattern?" → Architecture Style section
- "What technologies are used?" → Technology Stack section
- "What are the performance requirements?" → Performance Targets section
- "What security measures are in place?" → Security Principles section

---

#### 2. [ai-layer.md](./ai-layer.md) - AI Architecture
**Purpose**: Complete AI capabilities, agents, and provider integration

**Related**: See [claude-agent-sdk-architecture.md](./claude-agent-sdk-architecture.md) for detailed SDK integration patterns.

**Sections & Key Topics**:
- **Overview** → BYOK model (DD-002), streaming-first, human-in-the-loop (DD-003)
- **Layer Diagram** → Orchestration → Agents → Providers → RAG → Infrastructure
- **Directory Structure** → File organization for AI code
- **Core Capabilities** (14 AI Features):
  1. Ghost Text → Real-time typing suggestions (500ms delay)
  2. Issue Extraction → Parse structured issues from notes
  3. PR Review → Automated code review
  4. Task Decomposition → Break epics into subtasks
  5. Duplicate Detection → Semantic similarity search
  6. Issue Enhancement → Auto-suggest labels, priority, acceptance criteria
  7. Documentation Generation → Convert issues to docs
  8. Diagram Generation → Mermaid/PlantUML from descriptions
  9. Context Aggregation → Collect relevant context for issues
  10. Assignee Recommendation → ML-based task assignment
  11. Smart Search → Semantic search across workspace
  12. Sprint Planning → AI-assisted cycle planning
  13. Retrospective Analysis → Analyze cycle performance
  14. Release Notes → Auto-generate from commits
- **AI Agents** → 14 specialized agents with interfaces
- **LLM Providers** → Claude, OpenAI, Google, Azure adapters
- **Provider Selection** → Task-based routing per DD-011 (Claude→code, Gemini→latency, OpenAI→embeddings)
- **RAG Pipeline** → Embedding, chunking, indexing, retrieval
- **Prompt Engineering** → System prompts, templates, versioning
- **Cost Tracking** → Token usage, billing, quotas
- **Rate Limiting** → Per-user, per-workspace limits
- **Caching Strategy** → Redis for AI responses
- **Streaming (SSE)** → Server-sent events for real-time AI
- **Error Handling** → Retries, fallbacks, circuit breaker
- **Testing AI** → Mocks, fixtures, regression tests

**AI Query Examples**:
- "How does Ghost Text work?" → Core Capabilities #1
- "What AI providers are supported?" → LLM Providers section
- "How is cost tracking implemented?" → Cost Tracking section
- "How do I test AI agents?" → Testing AI section

---

#### 3. [architecture-diagrams.md](./architecture-diagrams.md) - Visual Architecture
**Purpose**: Mermaid diagrams for all system components

**Sections & Key Topics**:
- **Table of Contents** → 12 diagram categories
- **System Overview** → High-level architecture diagram
- **Core Philosophy** → Mind map of Note-First principles
- **Clean Architecture Layers** → Layer dependency diagram
- **Frontend Architecture** → Component tree, Note Canvas diagram
- **Backend Architecture** → CQRS-lite flow, DI container
- **AI Layer Architecture** → AI orchestration flow, provider selection
- **Infrastructure & Deployment** → Supabase platform diagram
- **Request Flow** → API lifecycle, SSE streaming
- **Data Model (ERD)** → Entity relationships
- **Authentication & Authorization** → Auth flow, RLS diagram
- **Real-time Collaboration** → WebSocket subscriptions
- **AI Agents Catalog** → Agent responsibilities matrix
- **State Management** → MobX store architecture

**AI Query Examples**:
- "Show me the system architecture" → System Overview section
- "How do layers interact?" → Clean Architecture Layers section
- "What's the data model?" → Data Model (ERD) section
- "How does authentication work?" → Authentication & Authorization section

---

#### 4. [backend-architecture.md](./backend-architecture.md) - Backend Details
**Purpose**: FastAPI backend structure, Clean Architecture implementation

**Sections & Key Topics**:
- **CQRS-lite Pattern** → Command/Query separation without Event Sourcing
- **Layer Architecture** → 5-layer diagram (Presentation, Application, Domain, Infrastructure, AI)
- **Layer Responsibilities** → Detailed role definitions
  1. Presentation Layer → FastAPI routers, schemas, middleware
  2. Application Layer → Use case services (Command/Query)
  3. Domain Layer → Entities, value objects, repository interfaces
  4. Infrastructure Layer → SQLAlchemy repos, external service adapters
  5. AI Layer → Agents, providers, RAG
- **Service Classes** → CreateIssueService, GetIssueService examples
- **Repository Pattern** → Interface + SQLAlchemy implementation
- **Unit of Work** → Transaction coordination
- **Domain Events** → Event publishing and handling
- **Dependency Injection** → Container setup with dependency-injector
- **API Versioning** → /api/v1/ namespace strategy
- **Middleware Stack** → Auth, error handling, rate limiting, CORS, logging
- **Database Migrations** → Alembic workflow
- **Background Jobs** → Supabase Queues (pgmq) + pg_cron
- **Error Handling** → Domain exceptions → HTTP responses
- **Testing Strategy** → Unit, integration, E2E test patterns

**AI Query Examples**:
- "How is CQRS implemented?" → CQRS-lite Pattern section
- "What are the backend layers?" → Layer Architecture section
- "How do repositories work?" → Repository Pattern section
- "How are background jobs handled?" → Background Jobs section

---

#### 5. [design-patterns.md](./design-patterns.md) - Code Patterns
**Purpose**: Reusable design patterns for backend and frontend

**Sections & Key Topics**:
- **Backend Patterns** → 5 patterns
  1. Repository Pattern → Abstract data access
  2. Unit of Work Pattern → Transaction coordination
  3. Service / Payload Pattern → Use case services
  4. Domain Events Pattern → Event-driven architecture
  5. Value Object Pattern → Immutable domain primitives
- **Frontend Patterns** → 5 patterns
  1. Container/Presenter Pattern → Smart vs. dumb components
  2. Compound Components Pattern → Flexible component APIs
  3. Custom Hook Pattern → Reusable React logic
  4. Optimistic Updates Pattern → Instant UI feedback
  5. Render Props / Function as Children → Component composition
- **API Design Conventions** → RESTful endpoints, naming rules
- **Response Format** → Standard JSON structure, pagination
- **Pydantic Schema Conventions** → Request/Response DTO patterns
- **Error Handling Conventions** → Domain exceptions, global handler
- **Testing Conventions** → Unit test, integration test structure
- **Code Quality Rules** → File size limits, naming conventions, import order

**AI Query Examples**:
- "What design patterns are used?" → Backend Patterns / Frontend Patterns
- "How should I structure a service?" → Service / Payload Pattern
- "What's the API response format?" → Response Format section
- "What are the code quality rules?" → Code Quality Rules section

---

#### 6. [feature-story-mapping.md](./feature-story-mapping.md) - User Stories
**Purpose**: Map 18 user stories to architecture components

**Sections & Key Topics**:
- **User Story Priority Overview** → P0, P1, P2, P3 stories
- **P0: Foundation** → US-01: Note-First Collaborative Writing
- **P1: Core Workflow** → US-02 to US-06 (Issues, Labels, Search, Board, Create)
- **P2: Enhanced Features** → US-07 to US-15 (AI, Modules, Cycles, GitHub, Slack, etc.)
- **P3: Supporting Features** → US-16 to US-18 (Team, Automation, Settings)
- **Each Story Includes**:
  - Architecture Components (Frontend, Backend, AI, Realtime)
  - Data Entities (tables, relationships)
  - Key Decisions (technical choices)
  - Acceptance Scenarios (test cases)

**AI Query Examples**:
- "What user stories are in P0?" → User Story Priority Overview
- "How is Note Canvas implemented?" → US-01 section
- "What components handle issue creation?" → US-02 section
- "How does GitHub integration work?" → US-13 section

---

#### 7. [FEATURES_CHECKLIST.md](./FEATURES_CHECKLIST.md) - Implementation Tracking
**Purpose**: Comprehensive feature inventory for tracking progress

**Sections & Key Topics**:
- **Overview** → Implementation roadmap
- **16 Major Categories**:
  1. Database & Persistence → PostgreSQL, pgvector, 18 core entities
  2. Authentication & Authorization → Supabase Auth, RLS, RBAC
  3. Real-Time Collaboration → Supabase Realtime, multi-user editing
  4. Background Jobs & Scheduling → pgmq, pg_cron, Edge Functions
  5. Storage & File Management → Supabase Storage, CDN
  6. AI Layer Architecture → 16 agents, providers, RAG, cost tracking
  7. Frontend Architecture → Next.js, MobX, TanStack Query
  8. Backend Architecture → FastAPI, Clean Architecture, CQRS-lite
  9. External Integrations → GitHub, Slack
  10. Deployment & Infrastructure → Docker, Supabase
  11. Testing Strategy → Unit, integration, E2E, performance
  12. Security → Application, database, auth security
  13. Monitoring & Observability → Logging, metrics, alerting
  14. Performance Targets → API, real-time, database SLAs
  15. Accessibility → WCAG 2.2 AA compliance
  16. Design System → Visual identity, design tokens
- **Implementation Progress Summary** → Progress tracker
- **Next Steps** → Immediate priorities

**AI Query Examples**:
- "What features need implementation?" → All sections
- "What AI agents exist?" → AI Layer Architecture section
- "What are the security requirements?" → Security section
- "What performance targets are defined?" → Performance Targets section

---

#### 8. [frontend-architecture.md](./frontend-architecture.md) - Frontend Details
**Purpose**: Next.js frontend structure, state management, component patterns

**Sections & Key Topics**:
- **Architecture Overview** → 4-layer frontend architecture
- **Next.js App Router Structure** → Route groups, page organization
- **Component Architecture** → Component categories, patterns
- **State Management** → MobX stores + TanStack Query hybrid
  - MobX for: UI state, editor state, real-time state
  - TanStack Query for: Server data, caching, mutations
- **TipTap Editor Integration** → Note Canvas architecture, block editor
- **Ghost Text Extension** → AI typing suggestions
- **SSE Streaming for AI** → Server-sent events implementation
- **API Service Layer** → API client, error handling, interceptors
- **Testing Strategy** → Component tests, hook tests

**AI Query Examples**:
- "How is frontend state managed?" → State Management section
- "How does the Note Canvas work?" → TipTap Editor Integration
- "How does Ghost Text work?" → Ghost Text Extension section
- "How is AI streaming implemented?" → SSE Streaming for AI section

---

#### 9. [infrastructure.md](./infrastructure.md) - Deployment & DevOps
**Purpose**: Docker, Supabase, environment configuration

**Sections & Key Topics**:
- **Service Architecture** → Supabase unified platform diagram
- **Docker Compose Configuration** → Development environment setup
- **Supabase Local Development** → `supabase start` workflow
- **Dockerfiles** → Backend, frontend Dockerfile specs
- **Environment Configuration** → Development environment variables
- **Supabase Background Jobs** → Queue configuration, pg_cron
- **Authentication Flow** → Supabase Auth integration
- **Health Checks** → Backend health endpoint
- **Production Deployment** → Supabase managed vs. self-hosted
- **Scaling Guidelines** → Horizontal/vertical scaling strategies
- **Security Checklist** → Production security requirements

**AI Query Examples**:
- "How do I set up local development?" → Supabase Local Development
- "What's in the Docker setup?" → Docker Compose Configuration
- "How do background jobs work?" → Supabase Background Jobs
- "How do I deploy to production?" → Production Deployment section

---

#### 10. [project-structure.md](./project-structure.md) - Directory Layout
**Purpose**: Complete file and folder organization

**Sections & Key Topics**:
- **Repository Root** → Monorepo structure
- **Backend Structure** → Detailed backend directory tree
  - api/ → Presentation layer (routers, schemas, middleware)
  - application/ → Application layer (services, interfaces)
  - domain/ → Domain layer (entities, repositories, events)
  - infrastructure/ → Infrastructure layer (persistence, external)
  - ai/ → AI layer (agents, providers, RAG)
- **Frontend Structure** → Detailed frontend directory tree
  - app/ → Next.js pages (route groups)
  - components/ → React components
  - stores/ → MobX state stores
  - services/ → API clients
  - hooks/ → Custom React hooks
  - lib/ → Utilities
- **Infrastructure Structure** → Docker, scripts
- **Documentation Structure** → Docs organization
- **Naming Conventions** → File, code, directory naming rules

**AI Query Examples**:
- "Where do I put a new service?" → Backend Structure section
- "Where do components go?" → Frontend Structure section
- "What are the naming conventions?" → Naming Conventions section
- "Where is the AI code?" → Backend Structure → ai/ section

---

#### 11. [rls-patterns.md](./rls-patterns.md) - Row-Level Security
**Purpose**: Database-level authorization patterns

**Sections & Key Topics**:
- **Overview** → RLS as primary authorization mechanism
- **Key Principles** → Defense in depth, workspace isolation
- **RLS Architecture** → Request flow diagram
- **Core Policies** → Workspace isolation, helper functions
- **Issues Table Policies** → SELECT, INSERT, UPDATE, DELETE policies
- **Notes Table Policies** → Note-specific RLS rules
- **Workspace Members Policies** → Member access control
- **RLS Helper Functions** → `auth.uid()`, `auth.user_workspace_ids()`
- **Performance Considerations** → Index optimization for RLS
- **Testing RLS Policies** → Policy test patterns
- **Migration Patterns** → Adding RLS to existing tables
- **Debugging RLS** → Troubleshooting policy issues

**AI Query Examples**:
- "How does RLS work?" → Overview section
- "What are the workspace policies?" → Core Policies section
- "How do I test RLS?" → Testing RLS Policies section
- "How do I debug RLS issues?" → Debugging RLS section

---

#### 12. [supabase-integration.md](./supabase-integration.md) - Supabase Platform
**Purpose**: Comprehensive Supabase integration guide

**Sections & Key Topics**:
- **Executive Summary** → Current vs. Supabase architecture comparison
- **Key Benefits** → Unified platform, real-time, auto-embeddings
- **Trade-Offs** → Enterprise SSO, vendor lock-in considerations
- **Supabase Capabilities Deep Dive** → 10+ capabilities
  1. Database (PostgreSQL 16+)
  2. Vector Database (pgvector + HNSW)
  3. Authentication (GoTrue)
  4. Storage (S3-compatible)
  5. Real-time (Phoenix WebSocket)
  6. Background Jobs (pgmq)
  7. Scheduled Jobs (pg_cron)
  8. Edge Functions (Deno)
  9. Auto-generated APIs (PostgREST, pg_graphql)
  10. Monitoring & Logs
- **Migration Guide** → Step-by-step migration from current stack
- **Code Examples** → Python/TypeScript integration patterns
- **Performance Optimization** → Indexing, caching, connection pooling
- **Cost Analysis** → Pricing breakdown, cost estimation
- **Security Configuration** → RLS, service keys, secrets management

**AI Query Examples**:
- "Why use Supabase?" → Executive Summary section
- "How does Supabase Auth work?" → Supabase Capabilities #3
- "How do I migrate to Supabase?" → Migration Guide section
- "What's the cost?" → Cost Analysis section

---

### 🔍 Common AI Query Patterns

**Architecture Questions**:
- "What architecture pattern is used?" → [README.md](./README.md#architecture-style)
- "How are layers organized?" → [backend-architecture.md](./backend-architecture.md#layer-architecture)
- "What's the frontend architecture?" → [frontend-architecture.md](./frontend-architecture.md#architecture-overview)

**Technology Questions**:
- "What technologies are used?" → [README.md](./README.md#technology-stack)
- "How is the database configured?" → [supabase-integration.md](./supabase-integration.md#database-postgresql-16)
- "What AI providers are supported?" → [ai-layer.md](./ai-layer.md#llm-providers)

**Implementation Questions**:
- "How do I implement a new feature?" → [feature-story-mapping.md](./feature-story-mapping.md)
- "Where do I put new code?" → [project-structure.md](./project-structure.md)
- "What patterns should I use?" → [design-patterns.md](./design-patterns.md)

**Security Questions**:
- "How is security handled?" → [README.md](./README.md#security-principles)
- "How does RLS work?" → [rls-patterns.md](./rls-patterns.md)
- "What auth is used?" → [supabase-integration.md](./supabase-integration.md#authentication-gotrue)

**Deployment Questions**:
- "How do I deploy?" → [infrastructure.md](./infrastructure.md#production-deployment)
- "What's the Docker setup?" → [infrastructure.md](./infrastructure.md#docker-compose-configuration)
- "How do I run locally?" → [infrastructure.md](./infrastructure.md#supabase-local-development)

---

## Related Documentation

### Specifications
- [Feature Specification](../../specs/001-pilot-space-mvp/spec.md) - 18 user stories
- [Implementation Plan](../../specs/001-pilot-space-mvp/plan.md) - Architecture decisions
- [Data Model](../../specs/001-pilot-space-mvp/data-model.md) - Entity definitions
- [UI Design Spec](../../specs/001-pilot-space-mvp/ui-design-spec.md) - UX patterns
- [Technical Research](../../specs/001-pilot-space-mvp/research.md) - Technology evaluations

### Project Standards
- [Constitution](../../.specify/memory/constitution.md) - Core principles and standards
- [Design Decisions](../DESIGN_DECISIONS.md) - Architectural decision records
- [AI Capabilities](../AI_CAPABILITIES.md) - AI feature documentation
- [Dev Patterns](../dev-pattern/README.md) - Development patterns reference
- [Pilot Space Patterns](../dev-pattern/45-pilot-space-patterns.md) - Project-specific patterns
