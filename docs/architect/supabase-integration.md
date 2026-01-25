# Supabase Integration Architecture

**Status**: ✅ Adopted (Session 2026-01-22)
**Date**: 2026-01-22
**Decision Type**: Infrastructure Simplification
**Constitution Reference**: v1.1.0 - Technology Standards

---

## Executive Summary

This document proposes replacing the current multi-service infrastructure (PostgreSQL + pgvector + Keycloak + S3/MinIO + custom realtime) with **Supabase** as a unified backend platform. Supabase provides all required capabilities in a single, integrated platform while enabling features previously deferred from MVP (DD-005: real-time collaboration).

### Current Architecture vs Supabase

| Capability | Current Stack | Supabase | Impact |
|------------|--------------|----------|---------|
| **Database** | PostgreSQL 15+ | PostgreSQL 16+ ✅ | Same engine, newer version |
| **Vector DB** | pgvector extension | pgvector built-in ✅ | Native support, HNSW indexing |
| **Authentication** | Keycloak (OIDC) | Supabase Auth (GoTrue) | ⚠️ Enterprise SSO trade-off |
| **Storage** | S3/MinIO | S3-Compatible Storage ✅ | Drop-in replacement |
| **Realtime** | ❌ Deferred (DD-005) | ✅ Built-in WebSocket | **Enable Note collaboration** |
| **Background Jobs** | Celery + RabbitMQ | Supabase Queues (pgmq) + pg_cron | Postgres-native queues |
| **Cron Jobs** | External scheduler | pg_cron built-in ✅ | Schedule directly in DB |
| **Auto Embeddings** | ❌ Manual via Celery | ✅ Edge Functions + Triggers | **Auto-index issues/notes** |
| **REST API** | FastAPI (custom) | Auto-generated + FastAPI | Hybrid approach |
| **GraphQL** | ❌ Not planned | ✅ Built-in (optional) | Bonus capability |
| **Deployment** | Docker Compose (10+ services) | Supabase (1 platform) | 🎯 **Simplified ops** |

### Key Benefits

1. **Unified Platform**: Single service replaces 7+ services (PostgreSQL, pgvector, Keycloak, Redis, MinIO, RabbitMQ, pg_cron)
2. **Enable Real-Time**: Unlock deferred features (DD-005) without additional infrastructure
3. **Automatic Embeddings**: Auto-generate embeddings for issues, notes, documents via Edge Functions + database triggers
4. **Faster Development**: Auto-generated APIs + built-in auth + storage SDK
5. **Cost Optimization**: BYOK pricing + no auth server costs + no message queue costs
6. **Better DX**: Integrated dashboard, migrations, monitoring, job scheduling

### Trade-Offs

| Consideration | Impact | Mitigation |
|---------------|--------|------------|
| **Enterprise SSO** | Keycloak → Supabase Auth loses LDAP/SAML | Use SAML 2.0 SSO (Supabase supports) |
| **Vendor Lock-in** | Supabase-specific | Self-hosted option available |
| **Auth Flexibility** | Less customizable than Keycloak | Row-Level Security (RLS) + custom logic |
| **Learning Curve** | Team learns Supabase patterns | Well-documented, active community |

---

## Supabase Capabilities Deep Dive

### 1. Database (PostgreSQL 16+)

**Features**:
- Full PostgreSQL 16+ with all extensions
- Instant REST and GraphQL APIs (PostgREST + pg_graphql)
- Row-Level Security (RLS) for authorization
- Connection pooling (PgBouncer built-in)
- Point-in-time recovery (PITR)

**Integration with Pilot Space**:
```python
# Current: Direct SQLAlchemy
from sqlalchemy import create_engine

engine = create_async_engine("postgresql+asyncpg://...")

# With Supabase: Same + Auto REST API
from supabase import create_client, Client

supabase: Client = create_client(supabase_url, supabase_key)

# Still use SQLAlchemy for complex queries
engine = create_async_engine(supabase_db_url)

# Use Supabase client for simple CRUD
data = supabase.table("issues").select("*").execute()
```

**Sources**:
- [Supabase Database Features](https://supabase.com/features)
- [PostgreSQL with Supabase](https://supabase.com/)

### 2. Vector Database (pgvector + HNSW)

**Features**:
- Native pgvector extension (same as current architecture)
- HNSW (Hierarchical Navigable Small World) indexing for fast similarity search
- IVFFlat index support
- 3072-dimensional vectors supported (OpenAI text-embedding-3-large compatible)
- Hybrid search (vector + full-text + filtering)

**Implementation for Pilot Space**:
```python
# ai/rag/embedder.py (NO CHANGE - same OpenAI embeddings)
from openai import AsyncOpenAI

embedder = AsyncOpenAI(api_key=user_openai_key)
embedding = await embedder.embeddings.create(
    model="text-embedding-3-large",
    input=text,
    dimensions=3072,
)

# ai/rag/retriever.py (ENHANCED with Supabase RPC)
from supabase import Client

class SupabaseSemanticRetriever:
    def __init__(self, supabase: Client, embedder: Embedder):
        self.supabase = supabase
        self.embedder = embedder

    async def search(
        self,
        query: str,
        project_id: str,
        limit: int = 10,
    ) -> list[RetrievalResult]:
        # Generate embedding
        query_embedding = await self.embedder.embed(query)

        # Use Supabase RPC for vector search
        result = self.supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.78,
                "match_count": limit,
                "project_id": project_id,
            }
        ).execute()

        return [
            RetrievalResult(
                content=row["content"],
                file_path=row["file_path"],
                similarity_score=row["similarity"],
                source_type=row["source_type"],
            )
            for row in result.data
        ]
```

**Database Function (Postgres)**:
```sql
-- Create vector search function
CREATE OR REPLACE FUNCTION match_documents (
  query_embedding vector(3072),
  match_threshold float,
  match_count int,
  project_id uuid
)
RETURNS TABLE (
  id uuid,
  content text,
  file_path text,
  similarity float,
  source_type text
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    content,
    file_path,
    1 - (embedding <=> query_embedding) as similarity,
    source_type
  FROM embeddings
  WHERE project_id = match_documents.project_id
  AND 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Create HNSW index for performance
CREATE INDEX ON embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Sources**:
- [Supabase Vector Database](https://supabase.com/modules/vector)
- [pgvector Integration](https://supabase.com/docs/guides/database/extensions/pgvector)
- [Semantic Search Guide](https://supabase.com/docs/guides/ai/semantic-search)
- [OpenAI Cookbook - Supabase Vector](https://cookbook.openai.com/examples/vector_databases/supabase/semantic-search)

### 3. Authentication (Supabase Auth / GoTrue)

**Features**:
- Email/password, magic links, phone OTP
- Social providers (GitHub, Google, etc.)
- SAML 2.0 SSO for enterprise
- JWT tokens (can integrate with existing FastAPI)
- Row-Level Security (RLS) policies
- Multi-factor authentication (MFA)

**Authentication Flow**:
```typescript
// Frontend: React/Next.js
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Sign in
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password'
})

// Get session
const { data: { session } } = await supabase.auth.getSession()
```

```python
# Backend: FastAPI JWT validation
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from supabase import Client

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client),
):
    """Validate Supabase JWT token."""
    token = credentials.credentials

    try:
        # Verify JWT with Supabase
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

# Use in routes
@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user_id": current_user.id}
```

**Row-Level Security (RLS) for Authorization**:
```sql
-- Enable RLS on issues table
ALTER TABLE issues ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see issues in their workspace
CREATE POLICY "Users see own workspace issues"
ON issues FOR SELECT
USING (
  workspace_id IN (
    SELECT workspace_id
    FROM workspace_members
    WHERE user_id = auth.uid()
  )
);

-- Policy: Only admins can delete issues
CREATE POLICY "Admins can delete issues"
ON issues FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM workspace_members
    WHERE workspace_id = issues.workspace_id
    AND user_id = auth.uid()
    AND role IN ('owner', 'admin')
  )
);
```

**Trade-Off Analysis**:

| Feature | Keycloak | Supabase Auth | Pilot Space Impact |
|---------|----------|---------------|-------------------|
| **OIDC/OAuth2** | ✅ Full support | ✅ Full support | ✅ No change |
| **SAML 2.0** | ✅ Native | ✅ Generic SSO | ✅ Enterprise SSO supported |
| **LDAP/AD** | ✅ Native | ❌ Not supported | ⚠️ **Limitation for enterprise** |
| **Social Logins** | ✅ Via adapters | ✅ Built-in | ✅ Better DX |
| **Multi-tenancy** | ✅ Realms | ✅ RLS policies | ✅ Easier with RLS |
| **Custom UI** | ✅ Fully customizable | ⚠️ Limited | ⚠️ Use custom frontend |
| **Self-hosted** | ✅ Open source | ✅ Open source | ✅ Both support |

**Recommendation**:
- **Use Supabase Auth for MVP** (simpler, faster)
- **Add SAML SSO** for enterprise customers (Supabase supports)
- **Fallback**: Keep Keycloak as optional for enterprises requiring LDAP

**Sources**:
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Keycloak vs Supabase Auth Comparison](https://cloudthrill.ca/supabase-vs-keycloak-saas)
- [IAM Solutions Comparison](https://leancode.co/blog/identity-management-solutions-part-2-the-choice)
- [FastAPI Integration with Supabase Auth](https://dev.to/j0/integrating-fastapi-with-supabase-auth-780)

### 4. Storage (S3-Compatible)

**Features**:
- S3-compatible API (AWS SDK works)
- Resumable uploads (tus protocol)
- Image transformations on-the-fly
- Access control via RLS
- CDN integration

**Implementation**:
```python
# infrastructure/storage/supabase_storage.py
from supabase import Client

class SupabaseStorageClient:
    """S3-compatible storage via Supabase."""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.bucket_name = "pilot-space-uploads"

    async def upload_file(
        self,
        file_path: str,
        file_data: bytes,
        content_type: str,
        user_id: str,
    ) -> str:
        """Upload file to Supabase Storage."""
        # Upload with RLS (user must be authenticated)
        result = self.supabase.storage.from_(self.bucket_name).upload(
            path=f"{user_id}/{file_path}",
            file=file_data,
            file_options={"content-type": content_type}
        )

        # Get public URL
        public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(
            f"{user_id}/{file_path}"
        )

        return public_url

    async def download_file(self, file_path: str) -> bytes:
        """Download file from storage."""
        result = self.supabase.storage.from_(self.bucket_name).download(file_path)
        return result

    async def delete_file(self, file_path: str) -> None:
        """Delete file from storage."""
        self.supabase.storage.from_(self.bucket_name).remove([file_path])
```

**Storage RLS Policies**:
```sql
-- Policy: Users can upload to their own folder
CREATE POLICY "Users upload to own folder"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'pilot-space-uploads'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy: Users can read files in their workspace
CREATE POLICY "Users read workspace files"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'pilot-space-uploads'
  AND EXISTS (
    SELECT 1 FROM file_metadata
    WHERE file_metadata.path = storage.objects.name
    AND file_metadata.workspace_id IN (
      SELECT workspace_id FROM workspace_members
      WHERE user_id = auth.uid()
    )
  )
);
```

**Sources**:
- [Supabase Storage S3 Compatibility](https://supabase.com/blog/s3-compatible-storage)
- [S3 Upload Guide](https://supabase.com/docs/guides/storage/uploads/s3-uploads)
- [Storage Documentation](https://supabase.com/docs/guides/storage)

### 5. Background Jobs & Queues (Celery Alternative)

**Features**:
- **Supabase Queues** (pgmq): Postgres-native durable message queue
- **pg_cron**: Recurring job scheduler in PostgreSQL
- **Edge Functions**: Serverless compute for workers
- Guaranteed message delivery
- Exactly-once processing
- Built-in retry logic

**Replaces**: RabbitMQ + Celery + Redis

**Use Cases in Pilot Space**:
| Current (Celery + RabbitMQ) | Supabase Queues + pg_cron | Benefit |
|----------------------------|--------------------------|---------|
| PR Review background task | Edge Function + Queue | No separate services needed |
| AI Context generation | Scheduled Edge Function | Simplified deployment |
| Embedding indexing | Queue worker | Postgres-native, no Redis |
| Email notifications | pg_cron + pg_net | Built-in scheduling |

**Architecture Pattern**:
```python
# Option 1: Supabase Queues (for guaranteed delivery)
# Insert message into queue table
supabase.table("job_queue").insert({
    "job_type": "pr_review",
    "payload": {"pr_number": 123, "repo": "owner/repo"},
    "status": "pending",
    "created_at": datetime.utcnow()
}).execute()

# Edge Function polls queue and processes
# (Triggered by pg_cron every minute or via webhook)

# Option 2: pg_cron for recurring tasks
# Schedule directly in PostgreSQL
"""
SELECT cron.schedule(
  'index-embeddings-daily',
  '0 2 * * *',  -- 2 AM daily
  $$
    SELECT net.http_post(
      url := 'https://[project-ref].supabase.co/functions/v1/index-embeddings',
      headers := '{"Authorization": "Bearer [anon-key]"}'::jsonb
    ) AS request_id;
  $$
);
"""

# Option 3: Keep Celery for complex AI workflows
# Use Celery for:
# - Long-running AI agent tasks (30+ min)
# - Complex retry logic with exponential backoff
# - Fan-out/fan-in patterns for parallel processing

# Use Supabase Queues for:
# - Short background tasks (<10 min)
# - Database-heavy operations
# - Simple job processing
```

**Implementation: PR Review Background Job**

```typescript
// Edge Function: /functions/process-pr-review/index.ts
import { createClient } from '@supabase/supabase-js'

Deno.serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )

  try {
    // Dequeue next pending PR review job
    const { data: job, error } = await supabase
      .from('pr_review_queue')
      .select('*')
      .eq('status', 'pending')
      .order('created_at', { ascending: true })
      .limit(1)
      .single()

    if (error || !job) {
      return new Response('No jobs pending', { status: 200 })
    }

    // Mark as processing
    await supabase
      .from('pr_review_queue')
      .update({ status: 'processing', started_at: new Date() })
      .eq('id', job.id)

    // Call FastAPI backend to run AI review
    const response = await fetch(`${BACKEND_URL}/api/v1/ai/pr-review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(job.payload)
    })

    const result = await response.json()

    // Mark as completed
    await supabase
      .from('pr_review_queue')
      .update({
        status: 'completed',
        result: result,
        completed_at: new Date()
      })
      .eq('id', job.id)

    return new Response(JSON.stringify({ success: true, job_id: job.id }), {
      headers: { 'Content-Type': 'application/json' }
    })

  } catch (error) {
    // Mark as failed and retry
    await supabase
      .from('pr_review_queue')
      .update({
        status: 'failed',
        error: error.message,
        retry_count: job.retry_count + 1
      })
      .eq('id', job.id)

    throw error
  }
})
```

**Queue Table Schema**:
```sql
CREATE TABLE pr_review_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  retry_count integer DEFAULT 0,
  max_retries integer DEFAULT 3,
  created_at timestamptz DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz,
  error text,
  result jsonb
);

-- Index for efficient dequeuing
CREATE INDEX idx_pr_review_queue_status ON pr_review_queue(status, created_at);

-- Enable RLS
ALTER TABLE pr_review_queue ENABLE ROW LEVEL SECURITY;

-- Policy: Service role only
CREATE POLICY "Service role full access"
ON pr_review_queue
USING (auth.role() = 'service_role');
```

**Schedule Worker with pg_cron**:
```sql
-- Schedule worker to run every minute
SELECT cron.schedule(
  'process-pr-reviews',
  '* * * * *',  -- Every minute
  $$
    SELECT net.http_post(
      url := 'https://[project-ref].supabase.co/functions/v1/process-pr-review',
      headers := jsonb_build_object(
        'Authorization',
        'Bearer ' || current_setting('app.settings.anon_key')
      )
    );
  $$
);

-- Schedule embedding indexing daily at 2 AM
SELECT cron.schedule(
  'index-embeddings-daily',
  '0 2 * * *',
  $$
    SELECT net.http_post(
      url := 'https://[project-ref].supabase.co/functions/v1/index-embeddings',
      headers := jsonb_build_object(
        'Authorization',
        'Bearer ' || current_setting('app.settings.service_role_key')
      )
    );
  $$
);

-- Cleanup old completed jobs weekly
SELECT cron.schedule(
  'cleanup-old-jobs',
  '0 3 * * 0',  -- Sunday 3 AM
  $$
    DELETE FROM pr_review_queue
    WHERE status = 'completed'
    AND completed_at < now() - interval '7 days';
  $$
);
```

**Monitoring Jobs**:
```sql
-- View active jobs
SELECT * FROM pr_review_queue
WHERE status IN ('pending', 'processing')
ORDER BY created_at;

-- View failed jobs
SELECT * FROM pr_review_queue
WHERE status = 'failed'
AND retry_count < max_retries
ORDER BY created_at;

-- View cron job history
SELECT * FROM cron.job_run_details
ORDER BY start_time DESC
LIMIT 100;
```

**Hybrid Architecture Decision**:

| Task Type | Use Supabase | Use Celery | Reason |
|-----------|-------------|-----------|---------|
| **PR Review** | ✅ Queue + Edge Function | ❌ | <10 min, DB-heavy |
| **AI Context** | ✅ Queue + Edge Function | ❌ | Quick aggregation |
| **Embedding Index** | ✅ pg_cron scheduled | ❌ | Daily batch job |
| **Complex AI Agents** | ❌ | ✅ Celery | 30+ min, needs sophisticated retry |
| **Parallel Processing** | ❌ | ✅ Celery | Fan-out pattern |

**Recommendation**:
- **Use Supabase Queues for 80% of background jobs** (simpler, fewer services)
- **Keep Celery for complex AI orchestration** (long-running, sophisticated patterns)

**Sources**:
- [Supabase Queues Documentation](https://supabase.com/docs/guides/queues)
- [Supabase Queues Module](https://supabase.com/modules/queues)
- [pg_cron Extension Guide](https://supabase.com/docs/guides/database/extensions/pg_cron)
- [Scheduling Edge Functions](https://supabase.com/docs/guides/functions/schedule-functions)
- [Processing Large Jobs with Edge Functions](https://supabase.com/blog/processing-large-jobs-with-edge-functions)
- [Background Jobs with Supabase](https://www.jigz.dev/blogs/how-i-solved-background-jobs-using-supabase-tables-and-edge-functions)

### 6. Realtime (WebSockets) ✨ NEW CAPABILITY

**Features**:
- Listen to database changes (INSERT, UPDATE, DELETE)
- Broadcast messages between clients
- Presence tracking (who's online)
- 10,000+ concurrent connections per node
- Global Elixir cluster (Phoenix Framework)

**Unlocks Deferred Features**:
- ✅ **Real-time note collaboration** (DD-005 - currently deferred)
- ✅ **Live issue board updates** (Kanban drag-drop sync)
- ✅ **Presence indicators** (who's viewing/editing)
- ✅ **Live notifications** (no polling needed)

**Implementation for Note Collaboration**:
```typescript
// Frontend: Note Canvas real-time collaboration
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Subscribe to note block changes
const channel = supabase
  .channel(`note:${noteId}`)
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'note_blocks',
      filter: `note_id=eq.${noteId}`
    },
    (payload) => {
      console.log('Block changed:', payload)
      // Update editor state (TipTap)
      handleRemoteChange(payload.new)
    }
  )
  .on('broadcast', { event: 'cursor' }, ({ payload }) => {
    // Show other users' cursors
    updateRemoteCursor(payload.user_id, payload.position)
  })
  .on('presence', { event: 'sync' }, () => {
    // Track who's editing
    const state = channel.presenceState()
    updateActiveUsers(state)
  })
  .subscribe()

// Broadcast cursor position
const broadcastCursor = (position: number) => {
  channel.send({
    type: 'broadcast',
    event: 'cursor',
    payload: { user_id: currentUser.id, position }
  })
}

// Track presence
channel.track({ user_id: currentUser.id, online_at: new Date().toISOString() })
```

**Backend: No Changes Needed**:
```python
# Realtime works automatically with database changes
# No backend code needed for basic subscriptions!

# For custom broadcast events (optional):
from supabase import Client

async def broadcast_issue_update(supabase: Client, issue_id: str, event_data: dict):
    """Send custom broadcast event."""
    channel = supabase.channel(f"issue:{issue_id}")
    await channel.send({
        "type": "broadcast",
        "event": "issue_updated",
        "payload": event_data
    })
```

**Architecture Impact**:
```
BEFORE (DD-005 - Realtime Deferred):
┌─────────────────────────────────────────────┐
│  Client polls /api/notes/{id} every 5s     │ ❌ Inefficient
│  No live collaboration                      │ ❌ No multiplayer
│  No presence tracking                       │ ❌ Can't see who's editing
└─────────────────────────────────────────────┘

AFTER (Supabase Realtime Enabled):
┌─────────────────────────────────────────────┐
│  WebSocket connection to Supabase           │ ✅ Efficient
│  Auto-sync on database changes              │ ✅ Live collaboration
│  Presence + Broadcast for cursors           │ ✅ Multiplayer UX
└─────────────────────────────────────────────┘
```

**Sources**:
- [Supabase Realtime Architecture](https://supabase.com/docs/guides/realtime/architecture)
- [Realtime Postgres Changes](https://supabase.com/features/realtime-postgres-changes)
- [Broadcast Documentation](https://supabase.com/docs/guides/realtime/broadcast)
- [Realtime on GitHub](https://github.com/supabase/realtime)

### 7. Automatic Embedding Generation (Edge Functions) ✨ NEW CAPABILITY

**Features**:
- Automatic embedding generation on INSERT/UPDATE via database triggers
- Queue-based async processing with pgmq for reliability
- Built-in retry logic with visibility timeouts
- Batch processing for efficiency (10 jobs per batch)
- Support for OpenAI text-embedding-3-large (3072 dimensions)
- HNSW indexing for fast similarity search

**Use Cases in Pilot Space**:
| Content Type | Embedding Input | Purpose |
|--------------|-----------------|---------|
| **Issues** | Title + Description + Comments | Semantic issue search, similar issue detection |
| **Notes** | Note title + block content | Knowledge base search, context for AI |
| **Documents** | File content chunks | RAG retrieval, code context |
| **PR Reviews** | PR title + diff summary | Find related past reviews |

**Architecture Overview**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTOMATIC EMBEDDING PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    Trigger    ┌─────────────┐    pg_cron    ┌───────────┐ │
│  │   INSERT/   │ ────────────► │    pgmq     │ ────────────► │   Edge    │ │
│  │   UPDATE    │               │   Queue     │   (10 sec)   │ Function  │ │
│  │  (issues,   │               │             │               │  (embed)  │ │
│  │   notes)    │               │             │               │           │ │
│  └─────────────┘               └─────────────┘               └─────┬─────┘ │
│                                                                     │       │
│                                      ┌──────────────────────────────┘       │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         OpenAI API (BYOK)                            │   │
│  │                    text-embedding-3-large (3072 dims)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      pgvector + HNSW Index                           │   │
│  │              Stores embeddings in halfvec(3072) column               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Step 1: Enable Required Extensions**:
```sql
-- For vector operations
CREATE EXTENSION IF NOT EXISTS vector
WITH SCHEMA extensions;

-- For queueing and processing jobs (creates its own schema)
CREATE EXTENSION IF NOT EXISTS pgmq;

-- For async HTTP requests to Edge Functions
CREATE EXTENSION IF NOT EXISTS pg_net
WITH SCHEMA extensions;

-- For scheduled processing and retries
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- For clearing embeddings during updates
CREATE EXTENSION IF NOT EXISTS hstore
WITH SCHEMA extensions;
```

**Step 2: Create Utility Functions**:
```sql
-- Schema for utility functions
CREATE SCHEMA IF NOT EXISTS util;

-- Utility function to get the Supabase project URL (required for Edge Functions)
CREATE OR REPLACE FUNCTION util.project_url()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  secret_value text;
BEGIN
  -- Retrieve the project URL from Vault
  SELECT decrypted_secret INTO secret_value
  FROM vault.decrypted_secrets
  WHERE name = 'project_url';
  RETURN secret_value;
END;
$$;

-- Generic function to invoke any Edge Function
CREATE OR REPLACE FUNCTION util.invoke_edge_function(
  name text,
  body jsonb,
  timeout_milliseconds int = 5 * 60 * 1000  -- default 5 minute timeout
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  headers_raw text;
  auth_header text;
BEGIN
  -- If we're in a PostgREST session, reuse the request headers for authorization
  headers_raw := current_setting('request.headers', true);

  -- Only try to parse if headers are present
  auth_header := CASE
    WHEN headers_raw IS NOT NULL THEN
      (headers_raw::json->>'authorization')
    ELSE
      NULL
  END;

  -- Perform async HTTP request to the edge function
  PERFORM net.http_post(
    url => util.project_url() || '/functions/v1/' || name,
    headers => jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', auth_header
    ),
    body => body,
    timeout_milliseconds => timeout_milliseconds
  );
END;
$$;

-- Generic trigger function to clear a column on update
CREATE OR REPLACE FUNCTION util.clear_column()
RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    clear_column text := TG_ARGV[0];
BEGIN
    NEW := NEW #= hstore(clear_column, NULL);
    RETURN NEW;
END;
$$;
```

**Step 3: Create Queue and Triggers**:
```sql
-- Queue for processing embedding jobs
SELECT pgmq.create('embedding_jobs');

-- Generic trigger function to queue embedding jobs
CREATE OR REPLACE FUNCTION util.queue_embeddings()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  content_function text = TG_ARGV[0];
  embedding_column text = TG_ARGV[1];
BEGIN
  PERFORM pgmq.send(
    queue_name => 'embedding_jobs',
    msg => jsonb_build_object(
      'id', NEW.id,
      'schema', TG_TABLE_SCHEMA,
      'table', TG_TABLE_NAME,
      'contentFunction', content_function,
      'embeddingColumn', embedding_column
    )
  );
  RETURN NEW;
END;
$$;

-- Function to process embedding jobs from the queue
CREATE OR REPLACE FUNCTION util.process_embeddings(
  batch_size int = 10,
  max_requests int = 10,
  timeout_milliseconds int = 5 * 60 * 1000 -- default 5 minute timeout
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  job_batches jsonb[];
  batch jsonb;
BEGIN
  WITH
    -- First get jobs and assign batch numbers
    numbered_jobs AS (
      SELECT
        message || jsonb_build_object('jobId', msg_id) AS job_info,
        (row_number() OVER (ORDER BY 1) - 1) / batch_size AS batch_num
      FROM pgmq.read(
        queue_name => 'embedding_jobs',
        vt => timeout_milliseconds / 1000,
        qty => max_requests * batch_size
      )
    ),
    -- Then group jobs into batches
    batched_jobs AS (
      SELECT
        jsonb_agg(job_info) AS batch_array,
        batch_num
      FROM numbered_jobs
      GROUP BY batch_num
    )
  -- Finally aggregate all batches into array
  SELECT array_agg(batch_array)
  FROM batched_jobs
  INTO job_batches;

  -- Invoke the embed edge function for each batch
  FOREACH batch IN ARRAY job_batches LOOP
    PERFORM util.invoke_edge_function(
      name => 'embed',
      body => batch,
      timeout_milliseconds => timeout_milliseconds
    );
  END LOOP;
END;
$$;

-- Schedule the embedding processing (every 10 seconds)
SELECT cron.schedule(
  'process-embeddings',
  '10 seconds',
  $$
    SELECT util.process_embeddings();
  $$
);
```

**Step 4: Create Edge Function (embed)**:

Create the Edge Function file at `supabase/functions/embed/index.ts`:

```typescript
// supabase/functions/embed/index.ts
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import OpenAI from 'jsr:@openai/openai'
import { z } from 'npm:zod'
import postgres from 'https://deno.land/x/postgresjs@v3.4.5/mod.js'

// Initialize OpenAI client (uses user's BYOK key)
const openai = new OpenAI({
  apiKey: Deno.env.get('OPENAI_API_KEY'),
})

// Initialize Postgres client
const sql = postgres(
  Deno.env.get('SUPABASE_DB_URL')!
)

const jobSchema = z.object({
  jobId: z.number(),
  id: z.string().or(z.number()), // Support both UUID and serial IDs
  schema: z.string(),
  table: z.string(),
  contentFunction: z.string(),
  embeddingColumn: z.string(),
})

const failedJobSchema = jobSchema.extend({
  error: z.string(),
})

type Job = z.infer<typeof jobSchema>
type FailedJob = z.infer<typeof failedJobSchema>

type Row = {
  id: string
  content: unknown
}

const QUEUE_NAME = 'embedding_jobs'

// Pilot Space uses text-embedding-3-large with 3072 dimensions
const EMBEDDING_MODEL = 'text-embedding-3-large'
const EMBEDDING_DIMENSIONS = 3072

Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response('expected POST request', { status: 405 })
  }

  if (req.headers.get('content-type') !== 'application/json') {
    return new Response('expected json body', { status: 400 })
  }

  const parseResult = z.array(jobSchema).safeParse(await req.json())

  if (parseResult.error) {
    return new Response(`invalid request body: ${parseResult.error.message}`, {
      status: 400,
    })
  }

  const pendingJobs = parseResult.data
  const completedJobs: Job[] = []
  const failedJobs: FailedJob[] = []

  async function processJobs() {
    let currentJob: Job | undefined

    while ((currentJob = pendingJobs.shift()) !== undefined) {
      try {
        await processJob(currentJob)
        completedJobs.push(currentJob)
      } catch (error) {
        failedJobs.push({
          ...currentJob,
          error: error instanceof Error ? error.message : JSON.stringify(error),
        })
      }
    }
  }

  try {
    await Promise.race([processJobs(), catchUnload()])
  } catch (error) {
    failedJobs.push(
      ...pendingJobs.map((job) => ({
        ...job,
        error: error instanceof Error ? error.message : JSON.stringify(error),
      }))
    )
  }

  console.log('finished processing jobs:', {
    completedJobs: completedJobs.length,
    failedJobs: failedJobs.length,
  })

  return new Response(
    JSON.stringify({ completedJobs, failedJobs }),
    {
      status: 200,
      headers: {
        'content-type': 'application/json',
        'x-completed-jobs': completedJobs.length.toString(),
        'x-failed-jobs': failedJobs.length.toString(),
      },
    }
  )
})

/**
 * Generates an embedding for the given text using OpenAI.
 */
async function generateEmbedding(text: string) {
  const response = await openai.embeddings.create({
    model: EMBEDDING_MODEL,
    input: text,
    dimensions: EMBEDDING_DIMENSIONS,
  })
  const [data] = response.data

  if (!data) {
    throw new Error('failed to generate embedding')
  }

  return data.embedding
}

/**
 * Processes an embedding job.
 */
async function processJob(job: Job) {
  const { jobId, id, schema, table, contentFunction, embeddingColumn } = job

  // Fetch content for the schema/table/row combination
  const [row]: [Row] = await sql`
    SELECT
      id,
      ${sql(contentFunction)}(t) AS content
    FROM
      ${sql(schema)}.${sql(table)} t
    WHERE
      id = ${id}
  `

  if (!row) {
    throw new Error(`row not found: ${schema}.${table}/${id}`)
  }

  if (typeof row.content !== 'string') {
    throw new Error(`invalid content - expected string: ${schema}.${table}/${id}`)
  }

  const embedding = await generateEmbedding(row.content)

  await sql`
    UPDATE
      ${sql(schema)}.${sql(table)}
    SET
      ${sql(embeddingColumn)} = ${JSON.stringify(embedding)}
    WHERE
      id = ${id}
  `

  await sql`
    SELECT pgmq.delete(${QUEUE_NAME}, ${jobId}::bigint)
  `
}

/**
 * Returns a promise that rejects if the worker is terminating.
 */
function catchUnload() {
  return new Promise((reject) => {
    addEventListener('beforeunload', (ev: any) => {
      reject(new Error(ev.detail?.reason))
    })
  })
}
```

**Step 5: Configure Issues Table for Automatic Embeddings**:
```sql
-- Add embedding column to issues table
ALTER TABLE issues
ADD COLUMN IF NOT EXISTS embedding halfvec(3072);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_issues_embedding
ON issues USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Function to generate embedding input for issues
-- Concatenates title, description, and labels for rich semantic context
CREATE OR REPLACE FUNCTION issue_embedding_input(issue issues)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN '# ' || COALESCE(issue.title, '') || E'\n\n' ||
         'State: ' || COALESCE(issue.state_name, 'Unknown') || E'\n' ||
         'Priority: ' || COALESCE(issue.priority::text, 'None') || E'\n\n' ||
         COALESCE(issue.description, '');
END;
$$;

-- Trigger for insert events
CREATE TRIGGER embed_issues_on_insert
  AFTER INSERT
  ON issues
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_embeddings('issue_embedding_input', 'embedding');

-- Trigger for update events (only when title or description changes)
CREATE TRIGGER embed_issues_on_update
  AFTER UPDATE OF title, description, state_name, priority
  ON issues
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_embeddings('issue_embedding_input', 'embedding');

-- Optional: Clear embedding on update to ensure freshness
CREATE TRIGGER clear_issue_embedding_on_update
  BEFORE UPDATE OF title, description, state_name, priority
  ON issues
  FOR EACH ROW
  EXECUTE FUNCTION util.clear_column('embedding');
```

**Step 6: Configure Notes Table for Automatic Embeddings**:
```sql
-- Add embedding column to notes table
ALTER TABLE notes
ADD COLUMN IF NOT EXISTS embedding halfvec(3072);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_notes_embedding
ON notes USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Function to generate embedding input for notes
-- Includes title and flattened block content
CREATE OR REPLACE FUNCTION note_embedding_input(note notes)
RETURNS text
LANGUAGE plpgsql
STABLE  -- STABLE because it queries note_blocks table
AS $$
DECLARE
  block_content text;
BEGIN
  -- Aggregate all block content
  SELECT string_agg(content, E'\n\n')
  INTO block_content
  FROM note_blocks
  WHERE note_id = note.id
  ORDER BY position;

  RETURN '# ' || COALESCE(note.title, 'Untitled Note') || E'\n\n' ||
         COALESCE(block_content, '');
END;
$$;

-- Trigger for insert events
CREATE TRIGGER embed_notes_on_insert
  AFTER INSERT
  ON notes
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_embeddings('note_embedding_input', 'embedding');

-- Trigger for update events
CREATE TRIGGER embed_notes_on_update
  AFTER UPDATE OF title, content
  ON notes
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_embeddings('note_embedding_input', 'embedding');

-- Trigger when note blocks change (re-embed parent note)
CREATE OR REPLACE FUNCTION util.queue_note_embedding_on_block_change()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Queue embedding job for the parent note
  PERFORM pgmq.send(
    queue_name => 'embedding_jobs',
    msg => jsonb_build_object(
      'id', COALESCE(NEW.note_id, OLD.note_id),
      'schema', 'public',
      'table', 'notes',
      'contentFunction', 'note_embedding_input',
      'embeddingColumn', 'embedding'
    )
  );
  RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE TRIGGER embed_note_on_block_change
  AFTER INSERT OR UPDATE OR DELETE
  ON note_blocks
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_note_embedding_on_block_change();
```

**Step 7: Configure Documents/Files for RAG Embeddings**:
```sql
-- Table to store document chunks with embeddings (for RAG)
CREATE TABLE IF NOT EXISTS document_embeddings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  source_type text NOT NULL, -- 'file', 'pr', 'commit', 'issue'
  source_id text NOT NULL, -- Original source identifier
  file_path text,
  chunk_index integer NOT NULL DEFAULT 0,
  content text NOT NULL,
  embedding halfvec(3072),
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create HNSW index
CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding
ON document_embeddings USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Index for filtering by project
CREATE INDEX IF NOT EXISTS idx_document_embeddings_project
ON document_embeddings(project_id);

-- Function to generate embedding input for document chunks
CREATE OR REPLACE FUNCTION document_embedding_input(doc document_embeddings)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN CASE
    WHEN doc.file_path IS NOT NULL THEN
      'File: ' || doc.file_path || E'\n\n' || doc.content
    ELSE
      doc.content
  END;
END;
$$;

-- Triggers for automatic embedding
CREATE TRIGGER embed_documents_on_insert
  AFTER INSERT
  ON document_embeddings
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_embeddings('document_embedding_input', 'embedding');

CREATE TRIGGER embed_documents_on_update
  AFTER UPDATE OF content
  ON document_embeddings
  FOR EACH ROW
  EXECUTE FUNCTION util.queue_embeddings('document_embedding_input', 'embedding');
```

**Step 8: Semantic Search Functions**:
```sql
-- Search similar issues
CREATE OR REPLACE FUNCTION search_similar_issues(
  query_embedding halfvec(3072),
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 10,
  filter_project_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  title text,
  description text,
  state_name text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    i.id,
    i.title,
    i.description,
    i.state_name,
    1 - (i.embedding <=> query_embedding) AS similarity
  FROM issues i
  WHERE
    i.embedding IS NOT NULL
    AND 1 - (i.embedding <=> query_embedding) > match_threshold
    AND (filter_project_id IS NULL OR i.project_id = filter_project_id)
  ORDER BY i.embedding <=> query_embedding
  LIMIT LEAST(match_count, 50);
$$;

-- Search similar notes
CREATE OR REPLACE FUNCTION search_similar_notes(
  query_embedding halfvec(3072),
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 10,
  filter_workspace_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  title text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    n.id,
    n.title,
    1 - (n.embedding <=> query_embedding) AS similarity
  FROM notes n
  WHERE
    n.embedding IS NOT NULL
    AND 1 - (n.embedding <=> query_embedding) > match_threshold
    AND (filter_workspace_id IS NULL OR n.workspace_id = filter_workspace_id)
  ORDER BY n.embedding <=> query_embedding
  LIMIT LEAST(match_count, 50);
$$;

-- Search documents for RAG (unified search across all document types)
CREATE OR REPLACE FUNCTION search_documents_for_rag(
  query_embedding halfvec(3072),
  filter_project_id uuid,
  match_threshold float DEFAULT 0.78,
  match_count int DEFAULT 20
)
RETURNS TABLE (
  id uuid,
  source_type text,
  source_id text,
  file_path text,
  content text,
  similarity float,
  metadata jsonb
)
LANGUAGE sql STABLE
AS $$
  SELECT
    d.id,
    d.source_type,
    d.source_id,
    d.file_path,
    d.content,
    1 - (d.embedding <=> query_embedding) AS similarity,
    d.metadata
  FROM document_embeddings d
  WHERE
    d.embedding IS NOT NULL
    AND d.project_id = filter_project_id
    AND 1 - (d.embedding <=> query_embedding) > match_threshold
  ORDER BY d.embedding <=> query_embedding
  LIMIT LEAST(match_count, 100);
$$;
```

**Python Integration (FastAPI Backend)**:
```python
# ai/rag/embedder.py
from openai import AsyncOpenAI
from typing import List

class OpenAIEmbedder:
    """Generate embeddings using OpenAI API (BYOK)."""

    MODEL = "text-embedding-3-large"
    DIMENSIONS = 3072

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = await self.client.embeddings.create(
            model=self.MODEL,
            input=text,
            dimensions=self.DIMENSIONS,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        response = await self.client.embeddings.create(
            model=self.MODEL,
            input=texts,
            dimensions=self.DIMENSIONS,
        )
        return [item.embedding for item in response.data]


# ai/rag/retriever.py
from supabase import Client
from typing import List
from dataclasses import dataclass

@dataclass
class RetrievalResult:
    content: str
    source_type: str
    source_id: str
    file_path: str | None
    similarity_score: float
    metadata: dict

class SupabaseSemanticRetriever:
    """Retrieve relevant documents using semantic search."""

    def __init__(self, supabase: Client, embedder: OpenAIEmbedder):
        self.supabase = supabase
        self.embedder = embedder

    async def search_issues(
        self,
        query: str,
        project_id: str | None = None,
        threshold: float = 0.78,
        limit: int = 10,
    ) -> List[dict]:
        """Search for similar issues."""
        query_embedding = await self.embedder.embed(query)

        result = self.supabase.rpc(
            "search_similar_issues",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit,
                "filter_project_id": project_id,
            }
        ).execute()

        return result.data

    async def search_for_rag(
        self,
        query: str,
        project_id: str,
        threshold: float = 0.78,
        limit: int = 20,
    ) -> List[RetrievalResult]:
        """Search documents for RAG context."""
        query_embedding = await self.embedder.embed(query)

        result = self.supabase.rpc(
            "search_documents_for_rag",
            {
                "query_embedding": query_embedding,
                "filter_project_id": project_id,
                "match_threshold": threshold,
                "match_count": limit,
            }
        ).execute()

        return [
            RetrievalResult(
                content=row["content"],
                source_type=row["source_type"],
                source_id=row["source_id"],
                file_path=row["file_path"],
                similarity_score=row["similarity"],
                metadata=row["metadata"],
            )
            for row in result.data
        ]
```

**Frontend Integration (TypeScript)**:
```typescript
// lib/supabase/embeddings.ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(supabaseUrl, supabaseAnonKey)

interface SimilarIssue {
  id: string
  title: string
  description: string
  state_name: string
  similarity: number
}

interface SimilarNote {
  id: string
  title: string
  similarity: number
}

/**
 * Search for similar issues using semantic search.
 * Query embedding is generated server-side via Edge Function.
 */
export async function searchSimilarIssues(
  queryEmbedding: number[],
  projectId?: string,
  threshold = 0.78,
  limit = 10
): Promise<SimilarIssue[]> {
  const { data, error } = await supabase.rpc('search_similar_issues', {
    query_embedding: queryEmbedding,
    match_threshold: threshold,
    match_count: limit,
    filter_project_id: projectId,
  })

  if (error) throw error
  return data
}

/**
 * Search for similar notes using semantic search.
 */
export async function searchSimilarNotes(
  queryEmbedding: number[],
  workspaceId?: string,
  threshold = 0.78,
  limit = 10
): Promise<SimilarNote[]> {
  const { data, error } = await supabase.rpc('search_similar_notes', {
    query_embedding: queryEmbedding,
    match_threshold: threshold,
    match_count: limit,
    filter_workspace_id: workspaceId,
  })

  if (error) throw error
  return data
}

// Edge Function to generate query embedding (avoids exposing API key)
// supabase/functions/generate-query-embedding/index.ts
/*
import OpenAI from 'jsr:@openai/openai'

const openai = new OpenAI({
  apiKey: Deno.env.get('OPENAI_API_KEY'),
})

Deno.serve(async (req) => {
  const { query } = await req.json()

  const response = await openai.embeddings.create({
    model: 'text-embedding-3-large',
    input: query,
    dimensions: 3072,
  })

  return new Response(
    JSON.stringify({ embedding: response.data[0].embedding }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
*/
```

**Monitoring & Troubleshooting**:
```sql
-- View pending embedding jobs
SELECT * FROM pgmq.read('embedding_jobs', 0, 100);

-- View embedding job metrics
SELECT
  table_name,
  COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded,
  COUNT(*) FILTER (WHERE embedding IS NULL) AS pending,
  COUNT(*) AS total
FROM (
  SELECT 'issues' AS table_name, embedding FROM issues
  UNION ALL
  SELECT 'notes' AS table_name, embedding FROM notes
  UNION ALL
  SELECT 'document_embeddings' AS table_name, embedding FROM document_embeddings
) AS combined
GROUP BY table_name;

-- View failed HTTP requests (for debugging Edge Function issues)
SELECT *
FROM net._http_response
WHERE (headers->>'x-failed-jobs')::int > 0
ORDER BY created DESC
LIMIT 20;

-- View cron job execution history
SELECT *
FROM cron.job_run_details
WHERE jobname = 'process-embeddings'
ORDER BY start_time DESC
LIMIT 20;

-- Manually trigger embedding processing (for testing)
SELECT util.process_embeddings();
```

**Configuration for BYOK (Bring Your Own Key)**:
```bash
# Set OpenAI API key for Edge Functions
supabase secrets set OPENAI_API_KEY=sk-...

# Or add to .env for local development
echo "OPENAI_API_KEY=sk-..." >> supabase/.env
```

**Sources**:
- [Supabase Automatic Embeddings](https://supabase.com/docs/guides/ai/automatic-embeddings)
- [Generate Text Embeddings Quickstart](https://supabase.com/docs/guides/ai/quickstarts/generate-text-embeddings)
- [Semantic Search Guide](https://supabase.com/docs/guides/ai/semantic-search)
- [pgvector Extension](https://supabase.com/docs/guides/database/extensions/pgvector)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)

---

## Revised Architecture with Supabase

### Infrastructure Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           PILOT SPACE (Supabase)                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       FRONTEND (Next.js 14)                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │  │
│  │  │ Note Canvas│  │Issue Board │  │  AI Panel  │  │   Settings     │ │  │
│  │  │(TipTap +   │  │(Kanban +   │  │(SSE Stream)│  │   (BYOK)       │ │  │
│  │  │ Realtime)  │  │ Realtime)  │  │            │  │                │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                │                    │                  │                    │
│                ▼                    ▼                  ▼                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                  SUPABASE CLIENT SDK (JS/Python)                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │  │
│  │  │   Auth     │  │  Realtime  │  │  Storage   │  │   Database     │ │  │
│  │  │  (GoTrue)  │  │ (WebSocket)│  │    (S3)    │  │  (PostgREST)   │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        FASTAPI BACKEND                                │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Application Layer (Use Cases, Domain Services)                │  │  │
│  │  │  • Uses SQLAlchemy for complex queries                         │  │  │
│  │  │  • Uses Supabase Client for simple CRUD                        │  │  │
│  │  │  • Validates with Pydantic                                     │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  AI Layer (Claude SDK, Providers, Agents)                      │  │  │
│  │  │  • Same as before - no changes                                 │  │  │
│  │  │  • Uses pgvector for RAG                                       │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      SUPABASE PLATFORM                                │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐  │  │
│  │  │  PostgreSQL 16 │  │  Auth (GoTrue) │  │  Storage (S3)          │  │  │
│  │  │  + pgvector    │  │  + JWT         │  │  + CDN                 │  │  │
│  │  │  + RLS         │  │  + MFA         │  │  + Transforms          │  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘  │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐  │  │
│  │  │  Realtime      │  │  PostgREST     │  │  pgBouncer (Pooling)   │  │  │
│  │  │  (Phoenix)     │  │  (REST API)    │  │                        │  │  │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   BACKGROUND WORKERS (Celery)                         │  │
│  │  • PR Review Agent                                                    │  │
│  │  • AI Context Generation                                              │  │
│  │  • Embedding Indexing                                                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                   EXTERNAL SERVICES (Same as before)                  │  │
│  │  • Claude Agent SDK (BYOK)                                            │  │
│  │  • GitHub Integration                                                 │  │
│  │  • Slack Integration                                                  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## FastAPI Integration Patterns

### Hybrid Approach: Supabase + SQLAlchemy

```python
# infrastructure/database/supabase_client.py
from supabase import create_client, Client
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

class DatabaseClients:
    """Provide both Supabase client and SQLAlchemy for different use cases."""

    def __init__(self, config: "Config"):
        # Supabase client for simple CRUD + realtime + auth
        self.supabase: Client = create_client(
            config.supabase_url,
            config.supabase_service_key,  # Service key for backend
        )

        # SQLAlchemy for complex queries + domain logic
        self.engine = create_async_engine(
            config.supabase_db_url,  # Direct PostgreSQL connection
            echo=config.debug,
        )

    async def get_session(self) -> AsyncSession:
        """Get SQLAlchemy session for complex operations."""
        from sqlalchemy.orm import sessionmaker
        async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            yield session
```

### Use Case Decision Matrix

| Operation | Use Supabase Client | Use SQLAlchemy | Reason |
|-----------|-------------------|----------------|---------|
| **Simple SELECT** | ✅ | ❌ | `supabase.table().select()` is simpler |
| **Simple INSERT** | ✅ | ❌ | Auto-handles RLS + returns data |
| **Complex JOIN** | ❌ | ✅ | SQLAlchemy ORM is more powerful |
| **Transactions** | ❌ | ✅ | Multi-table consistency |
| **Domain Logic** | ❌ | ✅ | Use domain entities + repositories |
| **Realtime Subscribe** | ✅ | ❌ | Only Supabase supports |
| **RLS Enforcement** | ✅ | ⚠️ | Supabase auto-checks, SQLAlchemy needs manual |

### Example: Issue CRUD

```python
# application/services/issue/create_issue.py
from pilot_space.infrastructure.database.supabase_client import DatabaseClients
from supabase import Client

class CreateIssueService:
    def __init__(
        self,
        db_clients: DatabaseClients,
        ai_orchestrator: AIOrchestrator,
    ):
        self.supabase = db_clients.supabase
        self.db = db_clients  # For SQLAlchemy when needed

    async def execute(self, payload: CreateIssuePayload) -> CreateIssueResult:
        # Simple INSERT → Use Supabase (auto RLS)
        issue_data = {
            "project_id": payload.project_id,
            "title": payload.title,
            "description": payload.description,
            "state_name": "Backlog",
            "reporter_id": payload.created_by_id,
        }

        result = self.supabase.table("issues").insert(issue_data).execute()
        issue = result.data[0]

        # AI enhancement (same as before)
        ai_suggestions = await self.ai_orchestrator.enhance_issue(issue)

        return CreateIssueResult(issue=issue, ai_suggestions=ai_suggestions)


# application/services/issue/get_issue_with_context.py
# Complex query → Use SQLAlchemy
class GetIssueWithContextService:
    def __init__(self, db_clients: DatabaseClients):
        self.engine = db_clients.engine

    async def execute(self, payload: GetIssueWithContextPayload) -> IssueWithContext:
        async with db_clients.get_session() as session:
            # Complex join query
            query = (
                select(Issue, Note, AIContext)
                .join(NoteIssueLink, NoteIssueLink.issue_id == Issue.id)
                .join(Note, Note.id == NoteIssueLink.note_id)
                .outerjoin(AIContext, AIContext.issue_id == Issue.id)
                .where(Issue.id == payload.issue_id)
            )

            result = await session.execute(query)
            # ... process complex result
```

### Dependency Injection

```python
# api/dependencies.py
from fastapi import Depends
from supabase import Client

def get_supabase_client() -> Client:
    """Get Supabase client (singleton)."""
    return create_client(settings.supabase_url, settings.supabase_service_key)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    supabase: Client = Depends(get_supabase_client),
):
    """Validate token and get current user."""
    user = supabase.auth.get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

# Use in routes
@router.get("/issues")
async def list_issues(
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    # Supabase automatically applies RLS based on JWT
    # No need to filter by workspace manually!
    issues = supabase.table("issues").select("*").execute()
    return issues.data
```

**Sources**:
- [FastAPI with Supabase Best Practices](https://blog.theinfosecguy.xyz/building-a-crud-api-with-fastapi-and-supabase-a-step-by-step-guide)
- [FastAPI Supabase Integration Guide](https://medium.com/@abhik12295/building-a-supabase-and-fastapi-project-a-modern-backend-stack-52030ca54ddf)
- [Dependency Injection Patterns](https://github.com/orgs/supabase/discussions/33811)

---

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)

**Tasks**:
1. Create Supabase project (cloud or self-hosted)
2. Configure database schema (migrate from current ERD)
3. Setup authentication (SAML SSO for enterprise)
4. Create storage buckets
5. Configure RLS policies

**Deliverables**:
- Supabase project live
- Database schema migrated
- Auth working
- Storage configured

### Phase 2: Backend Integration (Week 2-3)

**Tasks**:
1. Add Supabase Python client to FastAPI
2. Implement hybrid Supabase + SQLAlchemy pattern
3. Migrate simple CRUD to Supabase client
4. Keep complex queries in SQLAlchemy
5. Update dependency injection

**Deliverables**:
- FastAPI connects to Supabase
- CRUD operations working
- Tests passing

### Phase 3: Frontend Integration (Week 3-4)

**Tasks**:
1. Add Supabase JS client to Next.js
2. Implement auth flow (login, signup, session)
3. Update API calls to use Supabase where appropriate
4. Add realtime subscriptions for note canvas
5. Implement presence tracking

**Deliverables**:
- Auth working end-to-end
- Note canvas has realtime collaboration
- Issue board updates live

### Phase 4: Feature Enablement (Week 4-5)

**Tasks**:
1. Enable real-time note collaboration (DD-005 reversal)
2. Add presence indicators
3. Implement live Kanban updates
4. Add cursor tracking
5. Performance testing

**Deliverables**:
- Real-time features working
- Performance meets targets
- User acceptance testing

### Phase 5: Migration & Cleanup (Week 5-6)

**Tasks**:
1. Migrate data from old services (if applicable)
2. Remove Keycloak
3. Remove MinIO/S3
4. Simplify Docker Compose
5. Update documentation

**Deliverables**:
- Old services decommissioned
- Simplified deployment
- Documentation updated

---

## Cost Analysis

### Current Architecture Costs (Estimated)

| Service | Cost (Self-Hosted) | Cost (Managed) | Notes |
|---------|-------------------|----------------|-------|
| PostgreSQL | Infrastructure | $50-200/mo | AWS RDS, DigitalOcean |
| Keycloak | Infrastructure | $100-300/mo | Requires dedicated resources |
| S3/MinIO | Infrastructure + bandwidth | $20-100/mo | Storage + egress |
| Redis | Infrastructure | $20-50/mo | Cache |
| Total | **$50-200/mo** | **$190-650/mo** | 4-8 GB RAM, 2-4 vCPU |

### Supabase Costs

| Tier | Price | Includes | Use Case |
|------|-------|----------|----------|
| **Free** | $0/mo | 500 MB DB, 1 GB storage, 2 GB bandwidth, 50,000 auth users | Dev/Testing |
| **Pro** | $25/mo | 8 GB DB, 100 GB storage, 250 GB bandwidth, 100,000 auth users | Small teams |
| **Team** | $599/mo | 64 GB DB, 200 GB storage, 500 GB bandwidth, Dedicated resources | Production |
| **Enterprise** | Custom | Unlimited, SLA, support | Large scale |

**Self-Hosted Supabase**:
- Infrastructure: $100-300/mo (4-8 GB RAM, 2-4 vCPU)
- No platform fees
- Full control

**Savings**:
- **Managed**: ~$25-599/mo vs $190-650/mo = **Save 60-90%**
- **Self-hosted**: ~$100-300/mo vs $190-650/mo = **Save 15-50%**
- **Operational**: Fewer services to manage = reduced DevOps time

---

## Recommendation

### ✅ **Adopt Supabase for Pilot Space MVP**

**Rationale**:

1. **Simplifies Infrastructure**: 8 services → 1 platform
2. **Unlocks Deferred Features**: Real-time collaboration (DD-005) at no extra cost
3. **Faster Development**: Auto-generated APIs + built-in patterns
4. **Cost Effective**: $25-599/mo vs $190-650/mo for managed services
5. **PostgreSQL Native**: Same database engine, just better tooling
6. **Self-Hostable**: Can self-host if vendor lock-in is a concern

**Approach**: Hybrid Architecture
- **Use Supabase** for: Auth, Storage, Realtime, simple CRUD, RLS
- **Keep FastAPI** for: AI orchestration, complex domain logic, Celery tasks
- **Use SQLAlchemy** for: Complex queries, transactions, domain repositories

**Address Trade-Offs**:
- **Enterprise SSO**: Use Supabase SAML 2.0 (covers most use cases)
- **LDAP**: Offer Keycloak as enterprise add-on if needed
- **Vendor Lock-in**: Use self-hosted Supabase option
- **Learning Curve**: Invest in team training (well-documented platform)

### Implementation Timeline

| Phase | Duration | Effort |
|-------|----------|--------|
| Phase 1: Infrastructure Setup | 1 week | 1 developer |
| Phase 2: Backend Integration | 2 weeks | 2 developers |
| Phase 3: Frontend Integration | 2 weeks | 2 developers |
| Phase 4: Feature Enablement | 1 week | Full team |
| Phase 5: Migration & Cleanup | 1 week | 1 developer |
| **Total** | **7 weeks** | **Peak: 4 developers** |

### Success Criteria

| Metric | Target | Validation |
|--------|--------|------------|
| **Infrastructure Reduction** | 8 → 4 services | Docker Compose file |
| **Realtime Collaboration** | <100ms latency | Load testing |
| **Auth Performance** | <200ms token validation | Benchmarks |
| **Cost Savings** | 30%+ reduction | Monthly bills |
| **Developer Velocity** | 20%+ faster CRUD | Sprint retrospectives |

---

## Next Steps

1. **Decision**: Review this proposal with stakeholders
2. **Prototype**: Build proof-of-concept with Supabase (1 week)
3. **Evaluate**: Test realtime collaboration + auth performance
4. **Decide**: Go/No-Go based on prototype results
5. **Execute**: Follow migration plan if approved

---

## References

### Official Documentation
- [Supabase Documentation](https://supabase.com/)
- [Supabase Vector Database](https://supabase.com/modules/vector)
- [Supabase Auth Guide](https://supabase.com/docs/guides/auth)
- [Supabase Realtime](https://supabase.com/docs/guides/realtime/architecture)
- [Supabase Storage](https://supabase.com/docs/guides/storage)

### Comparisons & Analysis
- [Supabase vs Keycloak - SaaS Auth Comparison](https://cloudthrill.ca/supabase-vs-keycloak-saas)
- [IAM Solutions Compared - Keycloak vs Supabase](https://leancode.co/blog/identity-management-solutions-part-2-the-choice)
- [Supabase Review 2026 - Hackceleration](https://hackceleration.com/supabase-review/)

### Integration Guides
- [FastAPI with Supabase - Step-by-Step Guide](https://blog.theinfosecguy.xyz/building-a-crud-api-with-fastapi-and-supabase-a-step-by-step-guide)
- [Building a Supabase and FastAPI Project](https://medium.com/@abhik12295/building-a-supabase-and-fastapi-project-a-modern-backend-stack-52030ca54ddf)
- [FastAPI Supabase Auth Integration](https://dev.to/j0/integrating-fastapi-with-supabase-auth-780)
- [FastAPI Supabase Template on GitHub](https://github.com/AtticusZeller/fastapi_supabase_template)

### Technical Deep Dives
- [pgvector Integration with Supabase](https://supabase.com/docs/guides/database/extensions/pgvector)
- [Semantic Search with Supabase - OpenAI Cookbook](https://cookbook.openai.com/examples/vector_databases/supabase/semantic-search)
- [Supabase Realtime on GitHub](https://github.com/supabase/realtime)
- [S3-Compatible Storage](https://supabase.com/blog/s3-compatible-storage)

---

## Appendix: Code Examples

### A. Supabase Configuration

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_anon_key: str  # For frontend
    supabase_service_key: str  # For backend (bypasses RLS)
    supabase_db_url: str  # Direct PostgreSQL connection

    # AI (unchanged)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
```

### B. RLS Policy Examples

```sql
-- Workspace member check function (reusable)
CREATE OR REPLACE FUNCTION auth.is_workspace_member(workspace_id uuid)
RETURNS boolean AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM workspace_members
    WHERE workspace_members.workspace_id = $1
    AND workspace_members.user_id = auth.uid()
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Issue policies
ALTER TABLE issues ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Workspace members can view issues"
ON issues FOR SELECT
USING (auth.is_workspace_member(workspace_id));

CREATE POLICY "Members can create issues"
ON issues FOR INSERT
WITH CHECK (auth.is_workspace_member(workspace_id));

CREATE POLICY "Members can update own issues"
ON issues FOR UPDATE
USING (
  auth.is_workspace_member(workspace_id)
  AND (reporter_id = auth.uid() OR assignee_id = auth.uid())
);

CREATE POLICY "Admins can delete issues"
ON issues FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM workspace_members
    WHERE workspace_id = issues.workspace_id
    AND user_id = auth.uid()
    AND role IN ('owner', 'admin')
  )
);
```

### C. Realtime Note Collaboration (Full Example)

```typescript
// components/editor/NoteCanvas.tsx
import { useEffect, useState } from 'react'
import { useEditor } from '@tiptap/react'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(supabaseUrl, supabaseAnonKey)

export function NoteCanvas({ noteId }: { noteId: string }) {
  const [activeUsers, setActiveUsers] = useState<Record<string, any>>({})

  const editor = useEditor({
    extensions: [...],
    content: initialContent,
    onUpdate: ({ editor }) => {
      // Debounce and save
      debouncedSave(editor.getJSON())
    }
  })

  useEffect(() => {
    if (!editor) return

    const channel = supabase
      .channel(`note:${noteId}`)
      // Listen to database changes
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'notes',
          filter: `id=eq.${noteId}`
        },
        (payload) => {
          // Apply remote changes
          if (payload.new.content !== editor.getJSON()) {
            editor.commands.setContent(payload.new.content)
          }
        }
      )
      // Listen to cursor broadcasts
      .on('broadcast', { event: 'cursor' }, ({ payload }) => {
        updateRemoteCursor(payload.user_id, payload.position)
      })
      // Track presence
      .on('presence', { event: 'sync' }, () => {
        const state = channel.presenceState()
        setActiveUsers(state)
      })
      .subscribe()

    // Broadcast own cursor
    const handleCursorMove = () => {
      const position = editor.state.selection.from
      channel.send({
        type: 'broadcast',
        event: 'cursor',
        payload: { user_id: currentUser.id, position }
      })
    }

    editor.on('selectionUpdate', handleCursorMove)

    // Track presence
    channel.track({
      user_id: currentUser.id,
      name: currentUser.name,
      avatar: currentUser.avatar,
      color: generateUserColor(currentUser.id)
    })

    return () => {
      channel.unsubscribe()
      editor.off('selectionUpdate', handleCursorMove)
    }
  }, [editor, noteId])

  return (
    <div>
      {/* Active users */}
      <div className="flex gap-2 mb-4">
        {Object.values(activeUsers).map((user: any) => (
          <div key={user.user_id} className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-full"
              style={{ backgroundColor: user.color }}
            />
            <span>{user.name}</span>
          </div>
        ))}
      </div>

      {/* Editor */}
      <EditorContent editor={editor} />
    </div>
  )
}
```
