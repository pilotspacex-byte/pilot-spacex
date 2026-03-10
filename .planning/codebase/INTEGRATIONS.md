# External Integrations

**Analysis Date:** 2026-03-07

## APIs & External Services

**AI Providers (BYOK — Bring Your Own Key):**
- Anthropic Claude — primary reasoning, PR review, AI context, code generation
  - SDK/Client: `anthropic >=0.40.0` (Python)
  - Auth: `ANTHROPIC_API_KEY` env var (workspace-level keys via Vault take precedence)
  - Models used: `claude-opus-4-5` (complex), `claude-sonnet-4` (standard), `claude-3-5-haiku` (fast)
  - Provider file: `backend/src/pilot_space/ai/providers/provider_selector.py`

- OpenAI — embeddings only
  - SDK/Client: `openai >=1.55.0`
  - Auth: `OPENAI_API_KEY` env var (workspace-level BYOK)
  - Model: `text-embedding-3-large` (semantic search, RAG)

- Google Gemini — ghost text (latency-sensitive tasks <2.5s)
  - SDK/Client: `google-generativeai >=0.8.0`
  - Auth: `GOOGLE_API_KEY` env var (workspace-level BYOK)
  - Model: `gemini-2.0-flash`

**Claude Agent SDK:**
- In-process MCP tool execution and skill orchestration
  - SDK/Client: `claude-agent-sdk >=0.1.0,<1.0`
  - Orchestrator: `backend/src/pilot_space/ai/agents/pilotspace_agent.py`
  - 33 MCP tools across 6 servers: `backend/src/pilot_space/ai/mcp/`

**GitHub (OAuth + Webhooks):**
- GitHub REST API v3 — repo listing, commit/PR linking, AI PR review, webhook management
  - SDK/Client: Custom `GitHubClient` using `httpx` (`backend/src/pilot_space/integrations/github/client.py`)
  - Auth: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` (OAuth App), `GITHUB_WEBHOOK_SECRET` (HMAC-SHA256)
  - OAuth callback: `/api/v1/integrations/github/callback`
  - Webhook endpoint: `/api/v1/webhooks/github`

**Google Drive (OAuth):**
- Google Drive integration for document attachments
  - Auth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
  - Frontend URL used for OAuth callback construction via `FRONTEND_URL`
  - Router: `ai_drive_router` in `backend/src/pilot_space/main.py`

## Data Storage

**Databases:**
- PostgreSQL 16 (via self-hosted Supabase stack)
  - Connection: `DATABASE_URL` env var (format: `postgresql+asyncpg://...`)
  - Client/ORM: SQLAlchemy 2.0 async with asyncpg driver
  - Session: `backend/src/pilot_space/infrastructure/database/engine.py`
  - Pool: default size 5, max overflow 10, timeout 30s
  - Extensions: pgvector (similarity search), pgmq (queue), pg_cron (scheduled jobs), logical replication
  - RLS enforced on all 35 models via `app.current_user_id` session variable

- AuthCore PostgreSQL (optional, separate from Supabase's Postgres)
  - Only active when `AUTH_PROVIDER=authcore` and `--profile authcore` Docker profile
  - Docker image: `postgres:16-alpine`, `authcore-postgres-data` volume

**Vector Storage:**
- pgvector extension on PostgreSQL — semantic search embeddings
  - Client: `pgvector >=0.3.6` Python package
  - Used by: knowledge graph, semantic note/issue search

**Queue:**
- pgmq (PostgreSQL Message Queue) via Supabase public RPC wrappers
  - Client: `backend/src/pilot_space/infrastructure/queue/supabase_queue.py`
  - Queue names: `AI_LOW`, `AI_NORMAL`, `NOTIFICATIONS` (defined in `backend/src/pilot_space/infrastructure/queue/models.py`)
  - Workers: DigestWorker, MemoryWorker, NotificationWorker (started in `backend/src/pilot_space/main.py` lifespan)

**File Storage:**
- Supabase Storage API (S3-compatible local filesystem backend in dev, extensible to S3)
  - SDK/Client: `storage3 >=0.8.0` (Python backend), `@supabase/supabase-js` (frontend)
  - Auth env vars: `ANON_KEY`, `SERVICE_ROLE_KEY`
  - Image transformation via imgproxy sidecar

**Caching:**
- Redis 7 (Alpine)
  - Connection: `REDIS_URL` env var (default: `redis://localhost:6379/0`)
  - Client: `redis >=5.2.0` async
  - Implementation: `backend/src/pilot_space/infrastructure/cache/redis.py`
  - TTLs: session cache 30min, AI context 24h, AI response (prompt hash) 7d, rate limit 1min

**Search:**
- Meilisearch 1.6
  - Connection: `MEILISEARCH_URL` + `MEILISEARCH_API_KEY`
  - Client: `meilisearch >=0.31.0`
  - Implementation: `backend/src/pilot_space/infrastructure/search/meilisearch.py`
  - Indexes: issues, notes, pages — all workspace-scoped

## Authentication & Identity

**Auth Provider (primary):**
- Supabase Auth (GoTrue v2.164.0)
  - Implementation: JWT validation via `SUPABASE_JWT_SECRET`, RLS enforcement
  - Backend auth: `backend/src/pilot_space/infrastructure/auth/supabase_auth.py`
  - Frontend auth: `@supabase/supabase-js ^2.49.0`
  - JWT algorithm: HS256
  - MFA: enabled by default

**Auth Provider (alternative):**
- AuthCore — custom self-hosted auth service (RS256 JWT)
  - Switchable via `AUTH_PROVIDER=authcore` env var
  - Config: `AUTHCORE_PUBLIC_KEY` (PEM RSA public key), `AUTHCORE_URL`
  - Docker service: `authcore` container (port 8001), requires `--profile authcore`
  - Source: `authcore/` directory in monorepo root

**API Key Encryption (BYOK storage):**
- Supabase Vault — workspace-level AI provider keys stored encrypted (AES-256-GCM)
  - Implementation: `backend/src/pilot_space/infrastructure/encryption.py`
  - `VAULT_ENC_KEY` env var required in Supabase stack

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Datadog, Rollbar integration found)

**Logs:**
- structlog >=24.4.0 — structured JSON logging on backend
- Configuration: `backend/src/pilot_space/infrastructure/logging.py`
- Log level: `LOG_LEVEL` env var (default: INFO)

**Analytics (optional):**
- Logflare (Supabase Analytics) — available via `--profile analytics` Docker profile
- Connects to `_analytics` PostgreSQL schema

**AI Cost Tracking:**
- Custom `CostTracker` — per-request token usage + USD cost logged to PostgreSQL
  - Implementation: `backend/src/pilot_space/ai/infrastructure/cost_tracker.py`
  - Budget alerts triggered at 90% of workspace limit

## CI/CD & Deployment

**Hosting:**
- Frontend: Docker standalone Next.js image (multi-stage, `frontend/Dockerfile`)
- Backend: Python/Uvicorn Docker image (`backend/Dockerfile`)
- Database stack: self-hosted Supabase via `infra/supabase/docker-compose.yml`

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI, CircleCI config found)
- Quality gates defined in `Makefile`: `make quality-gates-backend`, `make quality-gates-frontend`

## Environment Configuration

**Required backend env vars:**
- `DATABASE_URL` — PostgreSQL async connection string
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — public Supabase anon key
- `SUPABASE_SERVICE_KEY` — server-side service role key
- `SUPABASE_JWT_SECRET` — JWT validation secret (must match GoTrue config)
- `REDIS_URL` — Redis connection
- `MEILISEARCH_URL` + `MEILISEARCH_API_KEY`
- `ENCRYPTION_KEY` — Fernet key for BYOK API key storage

**Optional backend env vars:**
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` — default BYOK fallback
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_CALLBACK_URL`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `AI_FAKE_MODE=true` — skip external AI calls in development
- `AUTH_PROVIDER=authcore` — switch to AuthCore for JWT validation

**Secrets location:**
- Backend: `backend/.env` (copy from `backend/.env.example`)
- Frontend: `frontend/.env.local` (copy from `frontend/.env.example`)
- Supabase stack: `infra/supabase/.env` (separate)

## Webhooks & Callbacks

**Incoming:**
- GitHub webhooks: `POST /api/v1/webhooks/github` — receives push, pull_request, pull_request_review, issue_comment events
  - Signature verification: HMAC-SHA256 via `X-Hub-Signature-256` header (verified before payload parsing)
  - Handler: `backend/src/pilot_space/integrations/github/webhooks.py`
  - Deduplication: in-memory LRU cache on `X-GitHub-Delivery` header (max 10,000 entries)

**Outgoing:**
- GitHub: OAuth token exchange (POST to `https://github.com/login/oauth/access_token`)
- GitHub API: REST API v3 calls for repo listing, commit/PR data, webhook registration
- GitHub: Post review comments via PR Review Subagent
- AI Providers: Anthropic, OpenAI, Google (via BYOK, through `ResilientExecutor` with exponential backoff)

## Realtime

**Supabase Realtime (WebSocket subscriptions):**
- Supabase Realtime v2.33.58 — database change subscriptions
- Frontend client: `@supabase/supabase-js` (includes realtime support)
- RLS mode: changes filtered by RLS policies (slot: `supabase_realtime_rls`)

**SSE Streaming:**
- Backend: FastAPI `StreamingResponse` — AI chat, ghost text, PR review stream to frontend
- Frontend: consumes SSE events via Vercel AI SDK (`ai ^6.0.50`) and custom hooks
- Event types: `text_delta`, `tool_use`, `content_update`, `task_progress`, `approval_request`

---

*Integration audit: 2026-03-07*
