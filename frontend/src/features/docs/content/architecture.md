# System Architecture

PilotSpace follows a **5-layer Clean Architecture** with CQRS-lite services, dependency injection, and repository pattern.

## Layer Overview

```text
┌─────────────────────────────────────────────┐
│  Clients: Browser (3000), CLI, Mobile       │
├─────────────────────────────────────────────┤
│  Frontend: Next.js App Router               │
│  MobX (UI) + TanStack Query (Server State)  │
│  shadcn/ui + TipTap Editor (26 extensions)  │
├─────────────────────────────────────────────┤
│  API Gateway: FastAPI Presentation Layer     │
│  20+ routers, middleware pipeline, SSE       │
├─────────────────────────────────────────────┤
│  Application: 38+ CQRS-lite Services        │
│  Service.execute(Payload) → Result          │
├─────────────────────────────────────────────┤
│  AI Orchestration: PilotSpaceAgent          │
│  33 MCP tools, provider routing, approvals  │
├─────────────────────────────────────────────┤
│  Domain: 12 core entities, business rules   │
├─────────────────────────────────────────────┤
│  Infrastructure: PostgreSQL, Redis, Search  │
│  18 repositories, 89 Alembic migrations     │
└─────────────────────────────────────────────┘
```

## Frontend Architecture

### State Management (DD-065)

**Golden Rule**: MobX for UI state, TanStack Query for server state. Never store API data in MobX.

```text
RootStore (singleton)
├── auth: AuthStore         — Session lifecycle
├── ui: UIStore             — Sidebar, theme, modals
├── workspace: WorkspaceStore
├── notes: NoteStore        — Editor dirty state, auto-save
├── issues: IssueStore      — Filters, sorting
├── cycles: CycleStore
├── ai: AIStore             — Hub for 11 AI sub-stores
│   ├── pilotSpace: PilotSpaceStore  — Unified agent
│   ├── ghostText: GhostTextStore    — Inline suggestions
│   ├── approval: ApprovalStore      — Human-in-the-loop
│   └── cost: CostStore              — Token usage
└── onboarding: OnboardingStore
```

### Component Patterns

- All MobX-consuming components **must** wrap with `observer()`
- Named function expressions for stack traces: `observer(function MyComponent() {...})`
- TanStack Query hooks for data fetching: `useQuery`, `useMutation`, `useInfiniteQuery`
- Cursor-based pagination with `CursorPage<T>`

### API Client Layer

- **Axios** with interceptors for auth (Bearer token) and error handling (RFC 7807)
- 15 API clients across domains (issues, notes, cycles, AI, integrations, etc.)
- Rate limit handling: 429 → toast with retry-after
- Token refresh: 401 → attempt refresh → redirect to `/login` on failure

## Backend Architecture

### Presentation Layer (API)

- **20+ FastAPI routers** organized by domain
- **Middleware pipeline**: RequestContext → ExceptionHandler → RateLimiter → AuthMiddleware
- **Error handling**: All errors return RFC 7807 Problem Details (`application/problem+json`)
- **Pydantic v2 schemas** for request validation and response serialization

### Application Layer (Services)

```python
# CQRS-lite pattern: explicit payloads, typed results
class CreateIssueService:
    async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult:
        # Validate → Create → Activity log → Return
```

**38+ services** across 9 domains:

- Issue (6), Note (10), Cycle (5), AI Context (3), Integration (4)
- Onboarding (3), Homepage (3), Memory (4), Role/Skill services

### Domain Layer

**12 core entities**: Issue, Note, State, Cycle, Module, Activity, Workspace, Project, Label, AIContext, AISession, WorkspaceMember.

**Key business rules**:

- Issue state machine: Backlog → Todo → In Progress → In Review → Done
- Cycle-state constraints: In Progress/Review requires active cycle
- Sequence IDs: Race-safe auto-increment per project (PS-1, PS-2)

### Infrastructure Layer

- **PostgreSQL 16**: 35 SQLAlchemy models, pgvector (embeddings), pgmq (message queue)
- **Redis 7**: Session cache (30-min TTL), rate limiting, AI response cache
- **Meilisearch**: Full-text search with typo tolerance
- **18 repositories**: BaseRepository[T] with cursor pagination, eager loading, soft delete
- **89 Alembic migrations**: Schema evolution with async-to-sync driver conversion

### Dependency Injection (DD-064)

```text
InfraContainer (DB, auth, repos, clients)
  └── SkillContainer (AI skill providers)
      └── PluginContainer (plugins/seeding)
          └── Container (38+ services + AI infra)
```

- **Factory providers**: New instance per request (services, repos)
- **Singleton providers**: Shared instances (config, engine, agent, circuit breakers)
- **SessionDep**: Every route using DI services must declare `session: SessionDep`

## Security Architecture

### Authentication

- **Supabase Auth** (default): HS256 HMAC JWT, GoTrue-managed
- **AuthCore** (optional): RS256 RSA, self-hosted microservice

### Row-Level Security (3 layers)

1. **Middleware**: Sets `app.current_user_id`, `app.current_workspace_id` session vars
2. **PostgreSQL RLS policies**: `USING (workspace_id = current_setting('app.current_workspace_id'))`
3. **Application**: Explicit `workspace_id` filter in all repository queries

### Rate Limiting

- Standard endpoints: 1000 req/min
- AI endpoints: 100 req/min
- Redis-backed sliding window counters

## DevOps

- **Docker Compose**: Local dev (backend, frontend, Redis, Meilisearch, migrations)
- **Kubernetes + Helm**: Enterprise deployment (3 backend replicas, 2 frontend, HPA)
- **GitHub Actions CI/CD**: Linting, type-check, tests, CodeQL security scanning
- **Quality gates**: 80% coverage, 700-line file limit, prek pre-commit hooks
