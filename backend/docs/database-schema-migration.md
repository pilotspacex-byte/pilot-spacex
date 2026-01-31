# Database Schema Migration Guide
**AI Messages Table - Queue Integration**

**Status:** Implementation Ready
**Priority:** P0 (Blocker for queue architecture)
**Estimated Time:** 30 minutes

---

## Problem

Current `ai_messages` table (from migration `020_create_ai_conversational_tables`) is missing critical columns required for queue-based architecture:

**Missing Columns:**
- ❌ `job_id` - Can't link messages to queue jobs
- ❌ `token_usage` - Can't track costs per workspace
- ❌ `processing_time_ms` - Can't measure performance
- ❌ `message_embedding` - Can't do semantic search/context pruning
- ❌ `completed_at` - Can't distinguish in-progress vs completed

**Current Schema:**
```sql
CREATE TABLE ai_messages (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ,
    session_id UUID REFERENCES ai_sessions,
    role VARCHAR(20),
    content TEXT,
    metadata JSONB  -- Generic blob
)
```

---

## Solution

Add missing columns with proper types and indexes.

---

## Migration Script

### Alembic Migration

**File:** `backend/alembic/versions/021_add_queue_columns_to_ai_messages.py`

```python
"""Add queue integration columns to ai_messages

Revision ID: 021_add_queue_columns
Revises: 020_create_ai_conv
Create Date: 2026-01-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers
revision: str = "021_add_queue_columns"
down_revision: str | None = "020_create_ai_conv"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add queue integration columns to ai_messages."""

    # 1. Add columns
    op.add_column(
        "ai_messages",
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,  # Nullable during migration
        ),
    )
    op.add_column(
        "ai_messages",
        sa.Column(
            "tool_calls",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "ai_messages",
        sa.Column("token_usage", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "ai_messages",
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ai_messages",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Add pgvector extension if not exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "ai_messages",
        sa.Column("message_embedding", sa.Vector(1536), nullable=True),
    )

    # 3. Backfill existing data
    # Set job_id = id for existing messages (one-time migration)
    op.execute("""
        UPDATE ai_messages
        SET job_id = id
        WHERE job_id IS NULL
    """)

    # Mark all existing messages as completed
    op.execute("""
        UPDATE ai_messages
        SET completed_at = created_at
        WHERE completed_at IS NULL
    """)

    # 4. Make job_id NOT NULL and UNIQUE after backfill
    op.alter_column(
        "ai_messages",
        "job_id",
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_ai_messages_job_id",
        "ai_messages",
        ["job_id"],
    )

    # 5. Create indexes
    op.create_index(
        "idx_ai_messages_job_id",
        "ai_messages",
        ["job_id"],
    )

    # Partial index for active (in-progress) messages
    op.execute("""
        CREATE INDEX idx_ai_messages_session_active
        ON ai_messages(session_id, completed_at)
        WHERE completed_at IS NULL
    """)

    # Vector similarity index (HNSW for better performance)
    op.execute("""
        CREATE INDEX idx_ai_messages_embedding
        ON ai_messages
        USING hnsw (message_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Remove queue integration columns."""

    # Drop indexes
    op.drop_index("idx_ai_messages_embedding", table_name="ai_messages")
    op.drop_index("idx_ai_messages_session_active", table_name="ai_messages")
    op.drop_index("idx_ai_messages_job_id", table_name="ai_messages")

    # Drop unique constraint
    op.drop_constraint("uq_ai_messages_job_id", "ai_messages", type_="unique")

    # Drop columns
    op.drop_column("ai_messages", "message_embedding")
    op.drop_column("ai_messages", "completed_at")
    op.drop_column("ai_messages", "processing_time_ms")
    op.drop_column("ai_messages", "token_usage")
    op.drop_column("ai_messages", "tool_calls")
    op.drop_column("ai_messages", "job_id")
```

---

## Running the Migration

### 1. Development Environment

```bash
cd backend

# Generate migration (if not using above script)
alembic revision --autogenerate -m "Add queue columns to ai_messages"

# Review the generated migration
cat alembic/versions/021_add_queue_columns_to_ai_messages.py

# Apply migration
alembic upgrade head

# Verify migration
psql $DATABASE_URL -c "\d ai_messages"
```

**Expected Output:**
```
                         Table "public.ai_messages"
      Column       |           Type           | Collation | Nullable | Default
-------------------+--------------------------+-----------+----------+---------
 id                | uuid                     |           | not null | gen_random_uuid()
 created_at        | timestamptz              |           | not null | now()
 session_id        | uuid                     |           | not null |
 role              | varchar(20)              |           | not null |
 content           | text                     |           | not null |
 metadata          | jsonb                    |           |          |
 job_id            | uuid                     |           | not null |  ← NEW
 tool_calls        | jsonb                    |           | not null | '[]'::jsonb  ← NEW
 token_usage       | jsonb                    |           |          |  ← NEW
 processing_time_ms| integer                  |           |          |  ← NEW
 completed_at      | timestamptz              |           |          |  ← NEW
 message_embedding | vector(1536)             |           |          |  ← NEW

Indexes:
    "ai_messages_pkey" PRIMARY KEY, btree (id)
    "uq_ai_messages_job_id" UNIQUE CONSTRAINT, btree (job_id)
    "idx_ai_messages_job_id" btree (job_id)
    "idx_ai_messages_session_active" btree (session_id, completed_at) WHERE completed_at IS NULL
    "idx_ai_messages_session_id" btree (session_id)
    "idx_ai_messages_session_created" btree (session_id, created_at)
    "idx_ai_messages_embedding" hnsw (message_embedding vector_cosine_ops)
```

---

### 2. Production Migration

**Pre-Migration Checklist:**

- [ ] Backup database
- [ ] Test migration on staging
- [ ] Verify downgrade path works
- [ ] Estimate migration time (rows × 10ms)
- [ ] Schedule maintenance window if needed

**Safe Migration Strategy:**

```bash
# 1. Backup database
pg_dump $DATABASE_URL > backup_before_021_$(date +%Y%m%d_%H%M%S).sql

# 2. Apply migration (should be fast - adds columns only)
alembic upgrade head

# 3. Verify
psql $DATABASE_URL -c "SELECT COUNT(*) FROM ai_messages WHERE job_id IS NOT NULL"

# 4. Monitor for errors
tail -f /var/log/app.log | grep "ai_messages"

# 5. If issues, rollback
alembic downgrade -1
```

**Expected Migration Time:**
- <1 second for empty table
- ~10ms per 1000 rows (adding columns is fast in PostgreSQL)
- ~1 second for 100k rows
- No downtime required (columns added as nullable first)

---

## Post-Migration Validation

### 1. Schema Verification

```sql
-- Check all columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'ai_messages'
ORDER BY ordinal_position;

-- Verify indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'ai_messages';

-- Check constraints
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'ai_messages'::regclass;
```

### 2. Data Integrity

```sql
-- Verify job_id uniqueness
SELECT COUNT(*), COUNT(DISTINCT job_id)
FROM ai_messages;
-- Should be equal

-- Check for NULL job_ids
SELECT COUNT(*)
FROM ai_messages
WHERE job_id IS NULL;
-- Should be 0

-- Verify completed_at for existing messages
SELECT COUNT(*)
FROM ai_messages
WHERE completed_at IS NULL;
-- Should be 0 (all existing messages marked completed)
```

### 3. Index Performance

```sql
-- Test job_id lookup (should use index)
EXPLAIN ANALYZE
SELECT * FROM ai_messages WHERE job_id = 'some-uuid';

-- Expected: Index Scan using idx_ai_messages_job_id

-- Test active messages query (should use partial index)
EXPLAIN ANALYZE
SELECT * FROM ai_messages
WHERE session_id = 'some-uuid' AND completed_at IS NULL;

-- Expected: Index Scan using idx_ai_messages_session_active
```

---

## SQLAlchemy Model Update

**File:** `backend/src/pilot_space/infrastructure/database/models/ai_message.py`

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from pilot_space.infrastructure.database.base import Base


class AIMessage(Base):
    """AI conversation message with queue integration."""

    __tablename__ = "ai_messages"

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    # Queue integration
    job_id: Mapped[UUID] = mapped_column(unique=True, nullable=False, index=True)

    # Session
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Content
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Metrics
    tool_calls: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb")
    )
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Vector search
    message_embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("NOW()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    # session: Mapped["AISession"] = relationship(back_populates="messages")


# Index for active (in-progress) messages
__table_args__ = (
    Index(
        "idx_ai_messages_session_active",
        "session_id",
        "completed_at",
        postgresql_where=text("completed_at IS NULL")
    ),
)
```

---

## Usage Examples

### 1. Create User Message (Immediate Completion)

```python
from uuid import uuid4
from datetime import datetime

# User message completes immediately
user_message = AIMessage(
    id=uuid4(),
    job_id=uuid4(),
    session_id=session_id,
    role="user",
    content="Explain authentication",
    created_at=datetime.utcnow(),
    completed_at=datetime.utcnow()  # User messages don't need processing
)
db.add(user_message)
await db.commit()
```

### 2. Create Assistant Message (In-Progress)

```python
# Create assistant message when job starts
assistant_message = AIMessage(
    id=uuid4(),
    job_id=job_id,
    session_id=session_id,
    role="assistant",
    content="",  # Empty initially
    completed_at=None  # NULL = in-progress
)
db.add(assistant_message)
await db.commit()
```

### 3. Update Message on Completion

```python
from sqlalchemy import update

# Worker updates message when done
await db.execute(
    update(AIMessage)
    .where(AIMessage.job_id == job_id)
    .values(
        content="The authentication flow uses FastAPI...",
        tool_calls=[
            {
                "tool_name": "Read",
                "params": {"file_path": "auth.py"},
                "result": "...file contents...",
                "status": "completed",
                "duration_ms": 450
            }
        ],
        token_usage={
            "input_tokens": 450,
            "output_tokens": 320,
            "cache_read_tokens": 1200
        },
        processing_time_ms=5420,
        completed_at=datetime.utcnow()
    )
)
await db.commit()
```

### 4. Query Active Messages

```python
from sqlalchemy import select

# Get all in-progress messages for a session
active_messages = await db.execute(
    select(AIMessage)
    .where(
        AIMessage.session_id == session_id,
        AIMessage.completed_at.is_(None)  # Uses partial index!
    )
)
results = active_messages.scalars().all()
```

### 5. Query by Job ID

```python
# Fast lookup by job_id (for reconnection)
message = await db.execute(
    select(AIMessage)
    .where(AIMessage.job_id == job_id)
)
result = message.scalar_one_or_none()

if result:
    if result.completed_at:
        return {"status": "completed", "content": result.content}
    else:
        return {"status": "processing"}
```

---

## Cost Tracking Queries

### 1. Workspace Token Usage

```sql
-- Total tokens used by workspace (last 30 days)
SELECT
    s.workspace_id,
    SUM((m.token_usage->>'input_tokens')::int) AS total_input_tokens,
    SUM((m.token_usage->>'output_tokens')::int) AS total_output_tokens,
    SUM((m.token_usage->>'cache_read_tokens')::int) AS total_cache_tokens,
    COUNT(*) AS message_count
FROM ai_messages m
JOIN ai_sessions s ON m.session_id = s.id
WHERE
    m.created_at > NOW() - INTERVAL '30 days'
    AND m.token_usage IS NOT NULL
GROUP BY s.workspace_id;
```

### 2. Cost Calculation

```python
async def calculate_workspace_cost(
    workspace_id: UUID,
    start_date: datetime,
    end_date: datetime
) -> dict:
    """Calculate AI cost for workspace in date range."""

    result = await db.execute(
        select(
            func.sum(
                (AIMessage.token_usage["input_tokens"].cast(Integer))
            ).label("input_tokens"),
            func.sum(
                (AIMessage.token_usage["output_tokens"].cast(Integer))
            ).label("output_tokens"),
            func.sum(
                (AIMessage.token_usage["cache_read_tokens"].cast(Integer))
            ).label("cache_tokens"),
        )
        .join(AISession)
        .where(
            AISession.workspace_id == workspace_id,
            AIMessage.created_at >= start_date,
            AIMessage.created_at <= end_date,
            AIMessage.token_usage.isnot(None)
        )
    )

    row = result.one()

    # Claude Sonnet 4.5 pricing (as of 2026-01-30)
    INPUT_COST_PER_MTok = 3.00  # $3 per million tokens
    OUTPUT_COST_PER_MTok = 15.00  # $15 per million tokens
    CACHE_COST_PER_MTok = 0.30  # $0.30 per million cached tokens

    input_cost = (row.input_tokens or 0) / 1_000_000 * INPUT_COST_PER_MTok
    output_cost = (row.output_tokens or 0) / 1_000_000 * OUTPUT_COST_PER_MTok
    cache_cost = (row.cache_tokens or 0) / 1_000_000 * CACHE_COST_PER_MTok

    total_cost = input_cost + output_cost + cache_cost

    return {
        "workspace_id": str(workspace_id),
        "period": {"start": start_date, "end": end_date},
        "usage": {
            "input_tokens": row.input_tokens or 0,
            "output_tokens": row.output_tokens or 0,
            "cache_tokens": row.cache_tokens or 0
        },
        "cost": {
            "input": round(input_cost, 2),
            "output": round(output_cost, 2),
            "cache": round(cache_cost, 2),
            "total": round(total_cost, 2)
        }
    }
```

---

## Troubleshooting

### Issue: Migration Fails with "column already exists"

**Cause:** Migration was partially applied.

**Solution:**
```sql
-- Check which columns exist
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'ai_messages';

-- If job_id exists but is nullable, make it NOT NULL
ALTER TABLE ai_messages
ALTER COLUMN job_id SET NOT NULL;

-- If unique constraint missing, add it
ALTER TABLE ai_messages
ADD CONSTRAINT uq_ai_messages_job_id UNIQUE (job_id);
```

### Issue: Slow queries after migration

**Cause:** Indexes not created or statistics not updated.

**Solution:**
```sql
-- Rebuild indexes
REINDEX TABLE ai_messages;

-- Update statistics
ANALYZE ai_messages;

-- Verify indexes are being used
EXPLAIN ANALYZE
SELECT * FROM ai_messages WHERE job_id = 'some-uuid';
```

### Issue: Vector index not working

**Cause:** pgvector extension not installed.

**Solution:**
```sql
-- Install pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Create index
CREATE INDEX idx_ai_messages_embedding
ON ai_messages
USING hnsw (message_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## Rollback Plan

If migration causes issues:

```bash
# 1. Rollback to previous version
alembic downgrade -1

# 2. Verify rollback
psql $DATABASE_URL -c "\d ai_messages"

# 3. Restore from backup if needed
pg_restore -d $DATABASE_URL backup_before_021_*.sql
```

---

## Next Steps

After migration:

1. ✅ Verify schema with validation queries
2. ✅ Update SQLAlchemy models
3. ✅ Test cost tracking queries
4. ⏭️ Implement queue worker (see worker-implementation-guide.md)
5. ⏭️ Update FastAPI endpoints for queue integration

**References:**
- Simplified architecture: `simplified-queue-architecture.md`
- Worker implementation: `worker-implementation-guide.md`
- Full review: `claude-sdk-architecture-review.md`
