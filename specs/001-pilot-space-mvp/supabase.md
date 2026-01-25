# Pilot Space MVP Enhancements: Supabase Integration

**Date**: 2026-01-22
**Status**: Proposed Enhancements
**Based on**: Supabase Integration Architecture Analysis

---

## Executive Summary

This document outlines required enhancements to the Pilot Space MVP specification (`spec.md`) based on the proposed Supabase integration architecture. The Supabase platform enables significant improvements in real-time collaboration, background job processing, and infrastructure simplification.

**Key Architecture Documents**:
- `docs/architect/supabase-integration.md` - Comprehensive Supabase integration proposal
- `docs/architect/backend-architecture.md` - FastAPI + Clean Architecture
- `docs/architect/frontend-architecture.md` - Next.js App Router
- `docs/architect/ai-layer.md` - AI orchestration with Claude Agent SDK
- `docs/architect/infrastructure.md` - Deployment and services

---

## Major Enhancement Categories

### 1. Real-Time Collaboration (Unlocked Features)

**Current Status**: DD-005 defers real-time collaboration to post-MVP

**With Supabase**: Built-in WebSocket support enables real-time features at no extra infrastructure cost

#### New User Story: Real-Time Note Collaboration (Priority: P0)

**Rationale**: Supabase Realtime unlocks this deferred feature, transforming Pilot Space into a multiplayer collaboration tool. This is a major competitive advantage.

**Acceptance Scenarios**:

1. **Given** multiple users open the same note, **When** one user types, **Then** other users see changes appear in real-time (<100ms latency)
2. **Given** multiple users are editing, **When** viewing the note, **Then** each user sees colored presence indicators showing who else is online
3. **Given** a user is typing, **When** their cursor moves, **Then** other users see a labeled cursor with the user's name and color
4. **Given** a user selects text, **When** the selection changes, **Then** other users see a highlighted region with the user's color
5. **Given** users are collaborating, **When** one user creates a new block, **Then** other users see the block appear without page refresh
6. **Given** users are editing different sections, **When** changes occur, **Then** conflict-free merge ensures no lost edits (CRDT or OT)
7. **Given** a user goes offline, **When** they reconnect, **Then** their changes sync automatically without data loss
8. **Given** users are in the same note, **When** viewing the header, **Then** a presence list shows all active users with their status

**Technical Implementation**:
```typescript
// Supabase Realtime subscription for note collaboration
const channel = supabase
  .channel(`note:${noteId}`)
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'note_blocks',
    filter: `note_id=eq.${noteId}`
  }, handleBlockChange)
  .on('broadcast', { event: 'cursor' }, handleCursorMove)
  .on('presence', { event: 'sync' }, handlePresenceSync)
  .subscribe()
```

**New Functional Requirements**:
- **FR-094**: System SHALL support real-time note block synchronization via WebSocket (target: <100ms latency)
- **FR-095**: System SHALL display user presence indicators (online/away/editing status)
- **FR-096**: System SHALL show cursor positions for all active users in a note
- **FR-097**: System SHALL handle concurrent edits with conflict-free merge (operational transforms or CRDTs)
- **FR-098**: System SHALL maintain connection resilience with automatic reconnection
- **FR-099**: System SHALL synchronize offline edits when connection is restored

---

#### Enhanced User Story 2: Real-Time Issue Board Updates

**Addition to User Story 2** (Create and Manage Issues):

**New Acceptance Scenarios**:

9. **Given** multiple users view the same issue board, **When** one user drags an issue to a new state, **Then** all users see the issue move in real-time
10. **Given** an issue is updated by another user, **When** viewing the issue detail, **Then** a live update notification appears without page refresh
11. **Given** users are viewing the same Kanban board, **When** one user creates an issue, **Then** the new issue card appears for all users immediately

**Technical Implementation**:
```typescript
// Real-time issue board subscription
const channel = supabase
  .channel(`project:${projectId}:issues`)
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'issues',
    filter: `project_id=eq.${projectId}`
  }, (payload) => {
    // Update board state in real-time
    updateIssueBoard(payload)
  })
  .subscribe()
```

**New Functional Requirements**:
- **FR-100**: System SHALL broadcast issue state changes to all connected clients in real-time
- **FR-101**: System SHALL update Kanban board views without requiring manual refresh
- **FR-102**: System SHALL show optimistic updates with rollback on conflict

---

### 2. Background Jobs & Queue System (Architecture Change)

**Current Specification**: Uses Celery + RabbitMQ for background tasks

**With Supabase**: Native Postgres-based queues (pgmq) + pg_cron for scheduling

#### Updated Architecture Requirements

**Changes to Infrastructure Section**:

**BEFORE**:
- RabbitMQ for message queue
- Celery for background workers
- Redis for Celery backend
- Separate cron scheduler

**AFTER**:
- Supabase Queues (pgmq) for job queue
- pg_cron for scheduled tasks
- Edge Functions for job workers (optional: keep Celery for complex AI tasks)

**New Functional Requirements**:
- **FR-103**: System SHALL use Postgres-native message queue (pgmq) for background job processing
- **FR-104**: System SHALL schedule recurring jobs using pg_cron extension
- **FR-105**: System SHALL process background jobs with guaranteed delivery and exactly-once semantics
- **FR-106**: System SHALL retry failed jobs with exponential backoff (max 3 retries)
- **FR-107**: System SHALL clean up completed jobs older than 7 days automatically
- **FR-108**: System SHALL expose job monitoring via /admin/jobs endpoint

**Implementation Example**:
```sql
-- PR Review Queue Table
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

-- Schedule worker to run every minute
SELECT cron.schedule(
  'process-pr-reviews',
  '* * * * *',
  $$
    SELECT net.http_post(
      url := 'https://[project].supabase.co/functions/v1/process-pr-review'
    );
  $$
);
```

**Updated User Story 3** (AI Code Review):

**New Acceptance Scenario**:

6. **Given** a PR review job fails due to API rate limit, **When** the job is retried, **Then** exponential backoff delays subsequent attempts (2s, 4s, 8s)
7. **Given** a PR review is queued, **When** checking job status, **Then** users can view queue position and estimated processing time

---

### 3. Authentication & Authorization (Architecture Change)

**Current Specification**: Keycloak (OIDC)

**With Supabase**: Supabase Auth (GoTrue) with Row-Level Security (RLS)

#### Updated Authentication Requirements

**Changes to FR-001 to FR-010** (Authentication section):

**Modified Functional Requirements**:
- **FR-001 (Updated)**: System SHALL authenticate users via Supabase Auth supporting email/password, magic links, OAuth2 social providers, and SAML 2.0 SSO
- **FR-002 (Updated)**: System SHALL issue JWT tokens compatible with Supabase Auth format
- **FR-003 (Updated)**: System SHALL enforce Row-Level Security (RLS) policies for multi-tenant data isolation
- **FR-004 (New)**: System SHALL support social login providers (GitHub, Google, Microsoft) via Supabase Auth
- **FR-005 (Updated)**: System SHALL validate JWT tokens on every API request using Supabase `auth.uid()` function
- **FR-006 (New)**: System SHALL refresh access tokens automatically using refresh tokens (7-day expiry)
- **FR-007 (New)**: System SHALL enforce MFA (multi-factor authentication) for admin and owner roles
- **FR-008 (New)**: System SHALL provide SAML 2.0 SSO integration for enterprise customers
- **FR-009 (Updated)**: System SHALL implement RBAC using RLS policies instead of application-level checks
- **FR-010 (New)**: System SHALL support password reset via email with secure token (24-hour expiry)

**New RLS Policy Examples**:
```sql
-- Issues: Users can only view issues in workspaces they're members of
CREATE POLICY "Users see workspace issues"
ON issues FOR SELECT
USING (
  workspace_id IN (
    SELECT workspace_id FROM workspace_members
    WHERE user_id = auth.uid()
  )
);

-- Issues: Admins can delete issues
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

**Updated Clarifications**:
- **Auth Provider**: Change from "Keycloak (OIDC/OAuth2 identity provider)" to "Supabase Auth (GoTrue) with SAML 2.0 SSO for enterprise; optional Keycloak for LDAP-required customers"

---

### 4. Storage & File Management (Architecture Change)

**Current Specification**: S3/MinIO for file storage

**With Supabase**: S3-compatible Supabase Storage with RLS policies

#### Updated Storage Requirements

**New Functional Requirements**:
- **FR-109**: System SHALL store uploaded files in Supabase Storage with S3-compatible API
- **FR-110**: System SHALL enforce storage access control via Row-Level Security policies
- **FR-111**: System SHALL support resumable uploads using tus protocol for files >5MB
- **FR-112**: System SHALL provide on-the-fly image transformations (resize, crop, format conversion)
- **FR-113**: System SHALL serve files via CDN for optimal performance
- **FR-114**: System SHALL support public and private buckets with policy-based access control
- **FR-115**: System SHALL limit file upload size to 50MB per file (configurable per workspace)
- **FR-116**: System MAY scan uploaded files for malware using ClamAV integration (post-MVP enhancement)

**Updated User Story 6** (Documentation Pages):

**New Acceptance Scenario**:

8. **Given** a user uploads an image, **When** inserting into page, **Then** image is automatically optimized and served via CDN
9. **Given** a user drags a file >5MB, **When** upload begins, **Then** resumable upload allows pausing and resuming
10. **Given** a file is uploaded, **When** accessed by unauthorized user, **Then** RLS policy denies access with 403 error

**Storage RLS Policy Example**:
```sql
-- Users can upload to their workspace folder
CREATE POLICY "Users upload to workspace folder"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'pilot-space-uploads'
  AND (storage.foldername(name))[1] IN (
    SELECT workspace_id::text FROM workspace_members
    WHERE user_id = auth.uid()
  )
);
```

---

### 5. Database & Vector Search (Enhanced)

**Current Specification**: PostgreSQL 15+ with pgvector

**With Supabase**: PostgreSQL 16+ with built-in pgvector and HNSW indexing

#### Enhanced Database Requirements

**New Functional Requirements**:
- **FR-117**: System SHALL use PostgreSQL 16+ as the primary database
- **FR-118**: System SHALL use pgvector extension with HNSW indexing for semantic search
- **FR-119**: System SHALL store embeddings in 3072-dimensional vectors (OpenAI text-embedding-3-large)
- **FR-120**: System SHALL perform hybrid search combining vector similarity + full-text + filters
- **FR-121**: System SHALL index embeddings asynchronously via background jobs
- **FR-122**: System SHALL use connection pooling (PgBouncer) to handle 1000+ concurrent connections
- **FR-123**: System SHALL enable point-in-time recovery (PITR) with 7-day retention

**Enhanced User Story 7** (Search and Knowledge Graph):

**New Acceptance Scenarios**:

8. **Given** a user searches for "authentication bug", **When** executing search, **Then** hybrid search combines keyword + semantic + metadata filters
9. **Given** search results are returned, **When** viewing results, **Then** similarity scores are displayed with relevant code snippets
10. **Given** a large codebase is indexed, **When** semantic search runs, **Then** HNSW index ensures <2s query time for 100K+ documents

**HNSW Index Example**:
```sql
-- Create HNSW index for fast similarity search
CREATE INDEX ON embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

### 6. Deployment & Infrastructure (Simplified)

**Current Specification**: Docker Compose with 10+ services

**With Supabase**: 2-3 services (Supabase platform + FastAPI backend + Next.js frontend)

#### Updated Deployment Requirements

**New Non-Functional Requirements**:
- **NFR-011**: System SHALL deploy backend as containerized FastAPI service
- **NFR-012**: System SHALL deploy frontend as Next.js application (Vercel or self-hosted)
- **NFR-013**: System SHALL use Supabase managed service OR self-hosted Supabase platform
- **NFR-014**: System SHALL reduce infrastructure services from 10+ to 2-3 services
- **NFR-015**: System SHALL provide Docker Compose for local development with Supabase CLI
- **NFR-016**: System SHALL support environment-based configuration (dev, staging, production)
- **NFR-017**: System SHALL implement health check endpoints for all services
- **NFR-018**: System SHALL use managed PostgreSQL connection pooling (no separate PgBouncer container)

**Updated Development Environment**:
```bash
# BEFORE (10 services)
docker-compose up -d  # postgres, redis, keycloak, minio, rabbitmq, celery, meilisearch, backend, frontend, worker

# AFTER (simplified)
supabase start        # All Supabase services
uvicorn main:app --reload  # FastAPI backend
pnpm dev              # Next.js frontend
```

---

### 7. API & Integration Patterns (Enhanced)

**Current Specification**: Custom FastAPI REST API only

**With Supabase**: Auto-generated REST API + GraphQL + Custom FastAPI for complex operations

#### New API Requirements

**New Functional Requirements**:
- **FR-124**: System SHALL expose auto-generated REST API via PostgREST for simple CRUD operations
- **FR-125**: System SHALL expose auto-generated GraphQL API via pg_graphql for complex queries (optional)
- **FR-126**: System SHALL use custom FastAPI endpoints for complex business logic and AI operations
- **FR-127**: System SHALL support API filtering, sorting, pagination via PostgREST query parameters
- **FR-128**: System SHALL return standardized error responses in JSON format
- **FR-129**: System SHALL support OpenAPI 3.1 specification for API documentation
- **FR-130**: System SHALL rate-limit API requests (1000 req/min standard, 100 req/min AI endpoints)

**Hybrid API Pattern**:
```typescript
// Simple CRUD: Use Supabase client (auto-generated API)
const { data: issues } = await supabase
  .from('issues')
  .select('*')
  .eq('project_id', projectId)
  .order('created_at', { ascending: false })

// Complex operations: Use FastAPI endpoint
const response = await fetch('/api/v1/ai/pr-review', {
  method: 'POST',
  body: JSON.stringify({ pr_number, repo })
})
```

**Updated API Documentation Requirements**:
- Add section: "Supabase Auto-Generated APIs"
- Add section: "When to Use Supabase Client vs FastAPI"
- Update endpoint list with hybrid approach

---

### 8. Monitoring & Observability (Enhanced)

**Current Specification**: Standard application logs only (NFR-008)

**With Supabase**: Built-in monitoring dashboard + custom observability

#### Enhanced Monitoring Requirements

**New Functional Requirements**:
- **FR-131**: System SHALL expose Supabase Dashboard for database performance monitoring
- **FR-132**: System SHALL track background job status via job monitoring tables
- **FR-133**: System SHALL log pg_cron job executions in `cron.job_run_details` table
- **FR-134**: System SHALL monitor real-time connection count and broadcast latency
- **FR-135**: System SHALL track AI cost per workspace via cost tracking tables
- **FR-136**: System SHALL expose /health endpoint returning service status + dependency health
- **FR-137**: System SHALL track API request latency (p50, p95, p99) via middleware

**New Monitoring Dashboard Requirements**:
- Database performance (query time, connection pool usage)
- Background job queue depth and processing rate
- Real-time WebSocket connection count
- AI usage and cost per workspace
- Storage bandwidth and quota usage

---

### 9. Cost Management (New)

**Current Specification**: No AI usage tracking in MVP (Clarification 2026-01-21)

**With Supabase**: Cost tracking built into architecture

#### New Cost Management Requirements

**New Functional Requirements**:
- **FR-138**: System SHALL track AI API costs per request in `ai_cost_records` table
- **FR-139**: System SHALL display workspace-level AI usage dashboard
- **FR-140**: System SHALL calculate AI cost based on provider pricing (input/output tokens)
- **FR-141**: System SHALL provide cost breakdown by task type (PR review, ghost text, etc.)
- **FR-142**: System SHALL alert workspace admins when approaching monthly budget limits
- **FR-143**: System SHALL export cost reports in CSV format for billing
- **FR-144**: System SHALL track storage usage per workspace with quota enforcement

**New Admin Features**:
- Workspace AI usage dashboard
- Cost allocation by feature (ghost text, PR review, etc.)
- Monthly budget alerts
- Export cost reports

---

### 10. Security Enhancements (RLS-Based)

**Current Specification**: Application-level authorization checks

**With Supabase**: Database-level Row-Level Security (RLS)

#### Enhanced Security Requirements

**New Functional Requirements**:
- **FR-145**: System SHALL enforce all authorization via PostgreSQL RLS policies
- **FR-146**: System SHALL enable RLS on all user data tables
- **FR-147**: System SHALL use `auth.uid()` function to identify current user in RLS policies
- **FR-148**: System SHALL implement policy-based access control for workspace membership
- **FR-149**: System SHALL prevent SQL injection via parameterized queries only
- **FR-150**: System SHALL audit RLS policy changes via database triggers
- **FR-151**: System SHALL use service role key only in trusted backend services
- **FR-152**: System SHALL use anon key for client-side Supabase SDK (with RLS enforcement)

**Security Benefits**:
- Authorization at database level (defense in depth)
- No bypassing security via application bugs
- Automatic enforcement across all access methods (REST, GraphQL, direct SQL)
- Auditable policy changes

---

## Implementation Priority

### Phase 1: Infrastructure Setup (Week 1)
- [ ] Setup Supabase project (cloud or self-hosted)
- [ ] Migrate database schema to Supabase
- [ ] Configure RLS policies for all tables
- [ ] Setup authentication (Supabase Auth)
- [ ] Configure storage buckets

### Phase 2: Real-Time Features (Week 2-3)
- [ ] Implement real-time note collaboration
- [ ] Add presence indicators
- [ ] Implement cursor tracking
- [ ] Add real-time issue board updates
- [ ] Performance testing (target: <100ms latency)

### Phase 3: Background Jobs (Week 3-4)
- [ ] Migrate PR review to Supabase Queues
- [ ] Setup pg_cron for scheduled tasks
- [ ] Implement job monitoring
- [ ] Migrate embedding indexing to queues
- [ ] (Optional) Keep Celery for complex AI workflows

### Phase 4: API Integration (Week 4-5)
- [ ] Integrate Supabase client in FastAPI
- [ ] Implement hybrid API pattern
- [ ] Update frontend to use Supabase SDK
- [ ] Test RLS enforcement
- [ ] Update API documentation

### Phase 5: Storage & Files (Week 5)
- [ ] Migrate file uploads to Supabase Storage
- [ ] Implement RLS policies for files
- [ ] Add resumable upload support
- [ ] Configure CDN for file serving
- [ ] Test image transformations

### Phase 6: Testing & Documentation (Week 6-7)
- [ ] Update spec.md with all enhancements
- [ ] Update acceptance scenarios
- [ ] Run full regression testing
- [ ] Update developer documentation
- [ ] Performance benchmarking
- [ ] Security audit

---

## Specification Updates Required

### spec.md Changes

1. **Add new User Story 19**: Real-Time Note Collaboration (Priority P0)
2. **Update User Story 1**: Add 8 real-time acceptance scenarios
3. **Update User Story 2**: Add 3 real-time issue board scenarios
4. **Update User Story 3**: Add 2 background job queue scenarios
5. **Update User Story 6**: Add 3 file upload scenarios
6. **Update User Story 7**: Add 3 semantic search scenarios

7. **Update Functional Requirements**:
   - Modify FR-001 to FR-010 (Authentication)
   - Add FR-094 to FR-152 (58 new requirements)

8. **Update Non-Functional Requirements**:
   - Add NFR-011 to NFR-018 (Deployment)

9. **Update Clarifications**:
   - Change "Keycloak" to "Supabase Auth with SAML 2.0"
   - Update "No AI usage tracking" to "Workspace-level cost tracking"

10. **Add new sections**:
    - Real-Time Collaboration Architecture
    - Background Job Queue System
    - Row-Level Security Policies
    - Cost Management & Monitoring

---

## Testing Impact

### New Test Scenarios Required

1. **Real-Time Collaboration Tests**:
   - Multi-user concurrent editing
   - Presence tracking accuracy
   - Cursor synchronization
   - Offline sync recovery
   - Connection resilience

2. **Background Job Tests**:
   - Queue processing reliability
   - Job retry logic
   - pg_cron schedule execution
   - Job monitoring accuracy
   - Failure handling

3. **Security Tests**:
   - RLS policy enforcement
   - Multi-tenant data isolation
   - Authorization bypass attempts
   - Token validation
   - Rate limiting

4. **Performance Tests**:
   - Real-time latency (<100ms target)
   - Database query performance with RLS
   - Background job throughput
   - API response times with PostgREST
   - Storage CDN performance

---

## Migration Considerations

### Breaking Changes

1. **Authentication**: Migration from Keycloak to Supabase Auth requires user session migration
2. **API Endpoints**: Some endpoints may shift to auto-generated PostgREST
3. **Authorization**: Application-level checks → RLS policies (logic changes)
4. **Background Jobs**: Celery tasks → Supabase Queues (different retry semantics)

### Data Migration

1. **User accounts**: Export from Keycloak, import to Supabase Auth
2. **Files**: Migrate from S3/MinIO to Supabase Storage
3. **Database**: Schema compatible, add RLS policies
4. **Job queue**: No migration needed (new system)

### Backward Compatibility

- Optional Keycloak support for enterprise LDAP customers
- Optional Celery support for complex AI workflows (30+ min tasks)
- Gradual migration path: Can run hybrid architecture during transition

---

## Success Criteria

### Feature Enablement
- ✅ Real-time note collaboration working with <100ms latency
- ✅ Presence indicators showing online users
- ✅ Background jobs processing via Supabase Queues
- ✅ RLS policies enforcing all authorization
- ✅ Cost tracking dashboard functional

### Infrastructure Reduction
- ✅ 10 services → 2-3 services
- ✅ No RabbitMQ, Redis, Keycloak, MinIO in default setup
- ✅ Simplified local development (`supabase start` + backend + frontend)

### Performance Targets
- ✅ Real-time sync: <100ms p95 latency
- ✅ API reads: <500ms p95 (maintained)
- ✅ API writes: <1s p95 (maintained)
- ✅ Background jobs: <10min for PR review (maintained)

### Cost Targets
- ✅ 60-90% infrastructure cost reduction vs current architecture
- ✅ BYOK AI costs transparent to users
- ✅ Workspace-level cost tracking functional

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **Real-time latency >100ms** | Load test early, optimize RLS policies, use connection pooling |
| **RLS performance impact** | Benchmark queries, add indexes, cache policy checks |
| **Enterprise SSO requirements** | Keep Keycloak option for LDAP customers |
| **Complex AI workflow timeouts** | Keep optional Celery for 30+ min tasks |
| **Learning curve for team** | Training sessions, comprehensive docs, pair programming |
| **Vendor lock-in concerns** | Use self-hosted Supabase option, maintain clean architecture |

---

## References

- [Supabase Integration Architecture](../docs/architect/supabase-integration.md)
- [Backend Architecture](../docs/architect/backend-architecture.md)
- [Frontend Architecture](../docs/architect/frontend-architecture.md)
- [AI Layer Architecture](../docs/architect/ai-layer.md)
- [Project Structure](../docs/architect/project-structure.md)
- [Design Patterns](../docs/architect/design-patterns.md)
- [Infrastructure](../docs/architect/infrastructure.md)
