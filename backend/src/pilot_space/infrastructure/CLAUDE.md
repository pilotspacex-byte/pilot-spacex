# Infrastructure Layer - Pilot Space

**Parent**: `/backend/CLAUDE.md`

---

## Components

| Component | Technology | Count | Purpose |
|-----------|-----------|-------|---------|
| Models | SQLAlchemy 2.0 async | 35 | PostgreSQL entities with soft delete, RLS |
| Repositories | BaseRepository[T] | 18 | Type-safe data access with pagination |
| Migrations | Alembic | 36+ | Schema versioning, RLS policies, indexes |
| Database | PostgreSQL 16 | 1 | Async via Supabase (DD-060) |
| Cache | Redis 7 | 1 | Session cache (30-min TTL), AI cache (7-day TTL) |
| Search | Meilisearch 1.6 | 1 | Full-text search (typo-tolerant) |
| Queue | pgmq via Supabase | 1 | Async task processing |
| Auth | Supabase Auth (GoTrue) | 1 | JWT validation + RLS enforcement |
| Encryption | Supabase Vault | 1 | API key storage (AES-256-GCM) |

---

## Submodule Documentation

- **[database/CLAUDE.md](database/CLAUDE.md)** -- SQLAlchemy Models (35, inheritance hierarchy, mixins), Repository Pattern (BaseRepository[T], 18 repos, eager loading, cursor pagination), Connection & Session Management, Migrations (36+)
- **[auth/CLAUDE.md](auth/CLAUDE.md)** -- RLS Architecture, RLS Policies, Verification Checklist, Authentication (JWT), Encryption (AES-256-GCM, BYOK)

---

## Directory Structure

```
infrastructure/
+-- database/
|  +-- models/              (35 SQLAlchemy models)
|  +-- repositories/        (18 repositories + BaseRepository)
|  +-- engine.py            (SQLAlchemy engine, session factory, pooling)
|  +-- rls.py               (RLS context setters)
|  +-- types.py             (JSONBCompat, custom column types)
+-- cache/
|  +-- redis.py            (RedisClient: async ops, JSON serialization)
|  +-- ai_cache.py         (AICache: prompt/response caching)
+-- auth/
|  +-- supabase_auth.py    (SupabaseAuthClient: JWT validation)
+-- search/
|  +-- meilisearch.py      (MeilisearchClient: full-text, workspace-scoped)
+-- queue/
|  +-- supabase_queue.py   (SupabaseQueueClient: pgmq via RPC)
|  +-- handlers/            (Task-specific processors)
+-- jobs/
|  +-- expire_approvals.py (Scheduled: auto-expire after 24h)
+-- encryption.py          (Supabase Vault integration)
```

---

## Cache Layer

| Cache Key Pattern | TTL | Purpose |
|-------------------|-----|---------|
| `session:{session_id}` | 30min | Hot session cache |
| `ai:context:{issue_id}` | 24h | AI context for issue |
| `ai:response:{hash}` | 7d | Response by prompt hash (SHA-256) |
| `rate_limit:{user_id}:{endpoint}` | 1min | Rate limit counters |

---

## Search Layer

**MeilisearchClient**: Workspace-scoped full-text search with typo tolerance. Methods: `search()` (with workspace_id filter, faceting), `index_document()`. Indexes: issues, notes, pages.

---

## Queue Layer

**SupabaseQueueClient**: Async processing via pgmq. Methods: `enqueue()`, `dequeue()` (batch), `ack()`. Queue names: AI_TASKS, PR_REVIEWS, WEBHOOKS, NOTIFICATIONS.

---

## Common Patterns

- **Eager Load**: `joinedload()` for 1:1, `selectinload()` for 1:N. Prevents N+1 queries.
- **Workspace Scoping**: Always filter by workspace_id. Missing = RLS violation.
- **Soft Delete**: Default (sets is_deleted=True). Hard delete only for cleanup.
- **Anti-Patterns**: Lazy loading in loops, blocking I/O in async.

---

## Troubleshooting

- **N+1 Detection**: Enable SQLAlchemy echo=True. Look for repeated SELECT.
- **RLS Verification**: `SELECT current_setting('app.current_user_id')` to verify context.
- **Pool Exhaustion**: "QueuePool Overflow" -- check `engine.pool.checkedout()`, increase max_overflow.

---

## Related Documentation

- **Database deep-dive**: [database/CLAUDE.md](database/CLAUDE.md)
- **RLS security**: [auth/CLAUDE.md](auth/CLAUDE.md)
- **Domain entities**: [../domain/models/CLAUDE.md](../domain/models/CLAUDE.md)
