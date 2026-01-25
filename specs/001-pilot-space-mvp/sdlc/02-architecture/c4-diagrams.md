# C4 Architecture Diagrams

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This document provides C4 model diagrams for Pilot Space MVP, covering System Context (L1), Container (L2), and Component (L3) levels.

---

## Level 1: System Context Diagram

Shows Pilot Space and its relationships with users and external systems.

```mermaid
C4Context
    title System Context Diagram - Pilot Space

    Person(developer, "Developer", "Writes code, creates PRs, uses AI context")
    Person(pm, "Product Manager", "Captures requirements, tracks sprints")
    Person(lead, "Tech Lead", "Reviews architecture, plans tasks")

    System(pilotspace, "Pilot Space", "AI-augmented SDLC platform with Note-First workflow")

    System_Ext(github, "GitHub", "Source code, PRs, commits")
    System_Ext(slack, "Slack", "Team notifications, commands")
    System_Ext(anthropic, "Anthropic API", "Claude for code review, task decomposition")
    System_Ext(google, "Google AI", "Gemini Flash for ghost text")
    System_Ext(openai, "OpenAI API", "Embeddings for semantic search")

    Rel(developer, pilotspace, "Uses", "HTTPS")
    Rel(pm, pilotspace, "Uses", "HTTPS")
    Rel(lead, pilotspace, "Uses", "HTTPS")

    Rel(pilotspace, github, "Syncs PRs, commits", "REST API")
    Rel(pilotspace, slack, "Sends notifications", "Events API")
    Rel(pilotspace, anthropic, "AI requests", "REST API")
    Rel(pilotspace, google, "AI requests", "REST API")
    Rel(pilotspace, openai, "Embedding requests", "REST API")

    Rel(github, pilotspace, "Webhooks", "HTTPS")
    Rel(slack, pilotspace, "Commands", "HTTPS")
```

### External System Interfaces

| System | Direction | Purpose | Protocol |
|--------|-----------|---------|----------|
| **GitHub** | Bidirectional | PR sync, commit linking, AI review posting | REST API, Webhooks |
| **Slack** | Bidirectional | Notifications, `/pilot` commands, link unfurl | Events API |
| **Anthropic** | Outbound | Claude for agentic tasks (PR review, decomposition) | REST API |
| **Google AI** | Outbound | Gemini Flash for low-latency tasks (ghost text) | REST API |
| **OpenAI** | Outbound | Embeddings for semantic search | REST API |

---

## Level 2: Container Diagram

Shows the major containers (applications/services) within Pilot Space.

```mermaid
C4Container
    title Container Diagram - Pilot Space

    Person(user, "User", "Developer, PM, or Tech Lead")

    Container_Boundary(pilotspace, "Pilot Space") {
        Container(frontend, "Frontend", "Next.js 14, React 18, MobX", "Single-page application with Note Canvas, Issue Board, and AI features")
        Container(backend, "Backend API", "FastAPI, Python 3.12", "REST API with CQRS-lite pattern, AI orchestration")
        Container(workers, "Background Workers", "Supabase Edge Functions", "Async job processing for AI tasks")
    }

    Container_Boundary(supabase, "Supabase Platform") {
        ContainerDb(postgres, "PostgreSQL 16", "Database", "Primary data store with RLS, pgvector")
        Container(auth, "Supabase Auth", "GoTrue", "Authentication, JWT tokens, SSO")
        Container(storage, "Supabase Storage", "S3-compatible", "File uploads, attachments")
        Container(queues, "Supabase Queues", "pgmq", "Background job queue")
        Container(realtime, "Supabase Realtime", "Phoenix", "WebSocket for live updates")
    }

    Container(redis, "Redis", "Cache", "AI response cache, sessions")
    Container(meilisearch, "Meilisearch", "Search Engine", "Typo-tolerant full-text search")

    System_Ext(github, "GitHub", "Source code, PRs")
    System_Ext(slack, "Slack", "Team communication")
    System_Ext(llm, "LLM Providers", "Anthropic, Google, OpenAI")

    Rel(user, frontend, "Uses", "HTTPS")
    Rel(frontend, backend, "API calls", "REST/SSE")
    Rel(frontend, realtime, "Subscribes", "WebSocket")
    Rel(frontend, auth, "Auth flow", "HTTPS")

    Rel(backend, postgres, "Reads/Writes", "SQL")
    Rel(backend, auth, "Validates tokens", "HTTPS")
    Rel(backend, storage, "File operations", "S3 API")
    Rel(backend, queues, "Enqueues jobs", "SQL")
    Rel(backend, redis, "Caches", "Redis Protocol")
    Rel(backend, meilisearch, "Indexes/Searches", "REST")
    Rel(backend, llm, "AI requests", "REST API")

    Rel(workers, queues, "Polls jobs", "SQL")
    Rel(workers, postgres, "Updates data", "SQL")
    Rel(workers, llm, "AI requests", "REST API")

    Rel(backend, github, "API calls", "REST")
    Rel(github, backend, "Webhooks", "HTTPS")
    Rel(backend, slack, "Notifications", "Events API")
    Rel(slack, backend, "Commands", "HTTPS")
```

### Container Descriptions

| Container | Technology | Purpose | Scaling |
|-----------|------------|---------|---------|
| **Frontend** | Next.js 14, React 18, MobX | User interface, Note Canvas, Issue Board | CDN, static hosting |
| **Backend API** | FastAPI, Python 3.12 | REST API, AI orchestration, business logic | Horizontal (containers) |
| **Background Workers** | Supabase Edge Functions | Async AI tasks, webhooks, scheduled jobs | Auto-scaled |
| **PostgreSQL** | PostgreSQL 16 + pgvector | Primary database, embeddings | Supabase managed |
| **Supabase Auth** | GoTrue | Authentication, SSO | Supabase managed |
| **Supabase Storage** | S3-compatible | File attachments | Supabase managed |
| **Supabase Queues** | pgmq | Background job queue | Supabase managed |
| **Supabase Realtime** | Phoenix | Live updates | Supabase managed |
| **Redis** | Redis 7 | Caching, sessions | Managed service |
| **Meilisearch** | Meilisearch 1.6 | Full-text search | Managed service |

---

## Level 3: Component Diagram - Backend

Shows components within the Backend API container.

```mermaid
C4Component
    title Component Diagram - Backend API

    Container_Boundary(backend, "Backend API") {
        Component(routers, "API Routers", "FastAPI", "HTTP endpoints for all resources")
        Component(schemas, "Pydantic Schemas", "Pydantic v2", "Request/response validation")
        Component(middleware, "Middleware", "FastAPI", "Auth, rate limiting, CORS, logging")

        Component(services, "Service Layer", "Python", "CQRS-lite command/query handlers")
        Component(domain, "Domain Layer", "Python", "Entities, value objects, business rules")
        Component(repositories, "Repositories", "SQLAlchemy", "Data access abstraction")

        Component(orchestrator, "AI Orchestrator", "Python", "Task routing, provider selection")
        Component(agents, "AI Agents", "Claude Agent SDK", "PR review, ghost text, decomposition")
        Component(providers, "LLM Providers", "Python", "Claude, Gemini, OpenAI adapters")
        Component(rag, "RAG Pipeline", "Python", "Embeddings, chunking, retrieval")

        Component(github_int, "GitHub Integration", "Python", "PR sync, webhooks, review posting")
        Component(slack_int, "Slack Integration", "Python", "Notifications, commands")
    }

    ContainerDb(postgres, "PostgreSQL", "Database")
    Container(redis, "Redis", "Cache")
    Container(queues, "Supabase Queues", "Job Queue")
    System_Ext(llm, "LLM Providers", "External")

    Rel(routers, schemas, "Validates with")
    Rel(routers, middleware, "Uses")
    Rel(routers, services, "Calls")

    Rel(services, domain, "Uses")
    Rel(services, repositories, "Queries/Commands")
    Rel(services, orchestrator, "AI tasks")

    Rel(repositories, postgres, "SQL")
    Rel(services, redis, "Caches")
    Rel(services, queues, "Enqueues")

    Rel(orchestrator, agents, "Routes to")
    Rel(orchestrator, providers, "Selects")
    Rel(agents, providers, "Uses")
    Rel(agents, rag, "Context")
    Rel(providers, llm, "API calls")

    Rel(services, github_int, "Integration")
    Rel(services, slack_int, "Integration")
```

### Backend Component Responsibilities

| Component | Layer | Responsibility |
|-----------|-------|----------------|
| **API Routers** | Presentation | HTTP endpoint definitions, OpenAPI docs |
| **Pydantic Schemas** | Presentation | Request/response validation and serialization |
| **Middleware** | Presentation | Cross-cutting: auth, rate limiting, CORS, logging |
| **Service Layer** | Application | CQRS command/query handlers, use case orchestration |
| **Domain Layer** | Domain | Business entities, value objects, domain events |
| **Repositories** | Infrastructure | Data access, query building, transaction management |
| **AI Orchestrator** | AI | Task classification, provider routing, session management |
| **AI Agents** | AI | Domain-specific AI capabilities (PR review, ghost text) |
| **LLM Providers** | AI | Provider adapters (Claude SDK, OpenAI, Gemini) |
| **RAG Pipeline** | AI | Embedding, chunking, vector search |
| **GitHub Integration** | Integration | PR sync, commit linking, review posting |
| **Slack Integration** | Integration | Notifications, slash commands |

---

## Level 3: Component Diagram - Frontend

Shows components within the Frontend container.

```mermaid
C4Component
    title Component Diagram - Frontend

    Container_Boundary(frontend, "Frontend") {
        Component(pages, "Next.js Pages", "App Router", "Route definitions, layouts")
        Component(features, "Feature Modules", "React", "Notes, Issues, Cycles, Pages")

        Component(note_canvas, "Note Canvas", "TipTap", "Block editor with ghost text, annotations")
        Component(issue_board, "Issue Board", "React", "Kanban board, issue list, detail view")
        Component(ai_panel, "AI Panel", "React", "AI suggestions, context, streaming")
        Component(command_palette, "Command Palette", "React", "Fuzzy search, navigation")
        Component(graph_view, "Knowledge Graph", "Sigma.js", "Entity relationship visualization")

        Component(ui_lib, "UI Library", "shadcn/ui", "Base components, design tokens")
        Component(mobx_stores, "MobX Stores", "MobX", "UI state, selection, filters")
        Component(tanstack, "TanStack Query", "React Query", "Server state, caching, mutations")
        Component(api_client, "API Client", "Axios/Fetch", "REST API integration")
        Component(sse_client, "SSE Client", "EventSource", "AI streaming responses")
        Component(realtime, "Realtime Client", "Supabase JS", "WebSocket subscriptions")
    }

    Container(backend, "Backend API", "FastAPI")
    Container(auth, "Supabase Auth", "GoTrue")

    Rel(pages, features, "Renders")
    Rel(features, note_canvas, "Includes")
    Rel(features, issue_board, "Includes")
    Rel(features, ai_panel, "Includes")
    Rel(features, command_palette, "Includes")
    Rel(features, graph_view, "Includes")

    Rel(features, ui_lib, "Uses")
    Rel(features, mobx_stores, "Observes")
    Rel(features, tanstack, "Queries")

    Rel(tanstack, api_client, "Uses")
    Rel(ai_panel, sse_client, "Streams from")
    Rel(features, realtime, "Subscribes")

    Rel(api_client, backend, "REST")
    Rel(sse_client, backend, "SSE")
    Rel(realtime, backend, "WebSocket")
    Rel(pages, auth, "Auth flow")
```

### Frontend Component Responsibilities

| Component | Category | Responsibility |
|-----------|----------|----------------|
| **Next.js Pages** | Routing | App Router pages, layouts, error boundaries |
| **Feature Modules** | Features | Domain-specific UI (notes, issues, cycles) |
| **Note Canvas** | Editor | TipTap-based block editor with AI extensions |
| **Issue Board** | Feature | Kanban board, list view, detail panel |
| **AI Panel** | Feature | AI suggestions, streaming responses, context |
| **Command Palette** | Navigation | Global search, quick actions |
| **Knowledge Graph** | Visualization | Sigma.js entity relationships |
| **UI Library** | Components | Design system, base components |
| **MobX Stores** | State | UI-only state (selection, filters, modals) |
| **TanStack Query** | State | Server state, caching, optimistic updates |
| **API Client** | Data | REST API integration, error handling |
| **SSE Client** | Streaming | AI response streaming |
| **Realtime Client** | Sync | Live updates via WebSocket |

---

## Data Flow Diagrams

### Ghost Text Request Flow

```mermaid
sequenceDiagram
    participant User
    participant NoteCanvas
    participant SSEClient
    participant Backend
    participant Orchestrator
    participant Gemini

    User->>NoteCanvas: Types in editor
    NoteCanvas->>NoteCanvas: Wait 500ms pause
    NoteCanvas->>SSEClient: Request ghost text (context)
    SSEClient->>Backend: POST /api/v1/ai/ghost-text (SSE)
    Backend->>Orchestrator: Route to low-latency provider
    Orchestrator->>Gemini: Stream completion request
    Gemini-->>Orchestrator: Streaming tokens
    Orchestrator-->>Backend: Buffer word boundaries
    Backend-->>SSEClient: SSE events (word by word)
    SSEClient-->>NoteCanvas: Update ghost text
    NoteCanvas-->>User: Display faded suggestion
    User->>NoteCanvas: Press Tab to accept
    NoteCanvas->>NoteCanvas: Insert suggestion
```

### PR Review Flow

```mermaid
sequenceDiagram
    participant GitHub
    participant Backend
    participant Queue
    participant Worker
    participant Claude
    participant Backend2 as Backend

    GitHub->>Backend: Webhook: PR opened
    Backend->>Queue: Enqueue PR review job
    Queue-->>Worker: Poll job
    Worker->>Claude: PR review request (agentic)
    Claude->>Claude: Analyze files, check patterns
    Claude-->>Worker: Review results
    Worker->>Backend2: Save review to database
    Worker->>GitHub: Post review comments
    Worker->>Backend2: Send notification
```

---

## References

- [docs/architect/README.md](../../../../docs/architect/README.md) - Architecture overview
- [docs/architect/architecture-diagrams.md](../../../../docs/architect/architecture-diagrams.md) - Additional diagrams
- [docs/architect/backend-architecture.md](../../../../docs/architect/backend-architecture.md) - Backend details
- [docs/architect/frontend-architecture.md](../../../../docs/architect/frontend-architecture.md) - Frontend details
