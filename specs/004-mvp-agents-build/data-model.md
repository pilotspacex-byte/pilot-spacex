# Data Model: MVP AI Agents Build

**Feature**: 004-mvp-agents-build
**Date**: 2026-01-25
**Status**: Draft

---

## New Entities

### 1. WorkspaceAPIKey

**Purpose**: Store encrypted API keys for BYOK (DD-002) model per workspace per provider.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| `workspace_id` | UUID | FK → workspaces(id), NOT NULL | Parent workspace |
| `provider` | VARCHAR(50) | NOT NULL, CHECK IN ('anthropic', 'openai', 'google', 'azure') | LLM provider |
| `vault_secret_id` | UUID | NOT NULL | Reference to Supabase Vault secret |
| `validation_status` | VARCHAR(20) | DEFAULT 'pending', CHECK IN ('pending', 'valid', 'invalid') | Key validation state |
| `last_validated_at` | TIMESTAMPTZ | NULL | Last successful validation |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() | Last update timestamp |

**Constraints**:
- UNIQUE(workspace_id, provider)
- ON DELETE CASCADE from workspace

**RLS Policy**:
```sql
-- Only workspace admins/owners can access API keys
CREATE POLICY "workspace_api_keys_admin_access" ON workspace_api_keys
    FOR ALL
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'owner')
    ));
```

**Indexes**:
- `idx_workspace_api_keys_workspace` ON (workspace_id)

---

### 2. AIApprovalRequest

**Purpose**: Track pending human approvals for AI actions (DD-003).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| `user_id` | UUID | FK → users(id), NOT NULL | Requesting user |
| `workspace_id` | UUID | FK → workspaces(id), NOT NULL | Parent workspace |
| `action_type` | VARCHAR(100) | NOT NULL | Action type (e.g., 'create_issue', 'delete_note') |
| `description` | TEXT | NOT NULL | Human-readable action description |
| `payload` | JSONB | NOT NULL | Data needed to execute action |
| `confidence` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | AI confidence score (0.0-1.0) |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | pending/approved/rejected/expired |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Expiration time (24h from creation) |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Creation timestamp |
| `resolved_at` | TIMESTAMPTZ | NULL | Resolution timestamp |
| `resolved_by` | UUID | FK → users(id), NULL | User who resolved |
| `resolution_note` | TEXT | NULL | Optional note on resolution |

**Constraints**:
- CHECK status IN ('pending', 'approved', 'rejected', 'expired')

**RLS Policy**:
```sql
-- Users can see their own requests
CREATE POLICY "ai_approval_requests_user_access" ON ai_approval_requests
    FOR SELECT
    USING (user_id = auth.uid());

-- Admins can see all requests in workspace
CREATE POLICY "ai_approval_requests_admin_access" ON ai_approval_requests
    FOR ALL
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'owner')
    ));
```

**Indexes**:
- `idx_ai_approval_requests_user_status` ON (user_id, status)
- `idx_ai_approval_requests_workspace_status` ON (workspace_id, status)
- `idx_ai_approval_requests_expires` ON (expires_at) WHERE status = 'pending'

---

### 3. AICostRecord

**Purpose**: Track AI usage costs for analytics and billing display.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| `user_id` | UUID | FK → users(id), NOT NULL | User who triggered |
| `workspace_id` | UUID | FK → workspaces(id), NOT NULL | Parent workspace |
| `agent_type` | VARCHAR(50) | NOT NULL | Agent name (e.g., 'ghost_text', 'pr_review') |
| `provider` | VARCHAR(50) | NOT NULL | LLM provider used |
| `model` | VARCHAR(100) | NOT NULL | Model name (e.g., 'claude-opus-4-5') |
| `input_tokens` | INTEGER | NOT NULL, CHECK >= 0 | Input token count |
| `output_tokens` | INTEGER | NOT NULL, CHECK >= 0 | Output token count |
| `total_cost_usd` | DECIMAL(10, 6) | NOT NULL, CHECK >= 0 | Calculated cost in USD |
| `duration_ms` | INTEGER | NOT NULL, CHECK >= 0 | Execution duration |
| `correlation_id` | VARCHAR(100) | NULL | Request correlation ID |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Record timestamp |

**Constraints**:
- No soft delete (audit records are immutable)

**RLS Policy**:
```sql
-- Users can see their own cost records
CREATE POLICY "ai_cost_records_user_access" ON ai_cost_records
    FOR SELECT
    USING (user_id = auth.uid());

-- Admins can see all records in workspace
CREATE POLICY "ai_cost_records_admin_access" ON ai_cost_records
    FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'owner')
    ));
```

**Indexes**:
- `idx_ai_cost_records_workspace_created` ON (workspace_id, created_at DESC)
- `idx_ai_cost_records_user_created` ON (user_id, created_at DESC)
- `idx_ai_cost_records_agent_type` ON (agent_type, created_at DESC)

**Aggregate Views**:
```sql
-- Daily cost summary per workspace
CREATE VIEW workspace_daily_ai_costs AS
SELECT
    workspace_id,
    DATE(created_at) AS date,
    agent_type,
    provider,
    COUNT(*) AS request_count,
    SUM(input_tokens) AS total_input_tokens,
    SUM(output_tokens) AS total_output_tokens,
    SUM(total_cost_usd) AS total_cost_usd,
    AVG(duration_ms) AS avg_duration_ms
FROM ai_cost_records
GROUP BY workspace_id, DATE(created_at), agent_type, provider;
```

---

### 4. AISession (Redis Only)

**Purpose**: Manage multi-turn conversation state. Stored in Redis, not PostgreSQL.

**Redis Key Pattern**: `ai_session:{session_id}`

**Redis Value Schema** (JSON):
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "agent_type": "ai_context|conversation",
  "context": {
    "issue_id": "uuid",
    "workspace_id": "uuid",
    "custom_key": "custom_value"
  },
  "messages": [
    {
      "role": "user|assistant",
      "content": "message text",
      "timestamp": "2026-01-25T10:30:00Z",
      "token_count": 150
    }
  ],
  "created_at": "2026-01-25T10:00:00Z",
  "last_activity": "2026-01-25T10:30:00Z",
  "total_cost_usd": 0.0532
}
```

**TTL**: 1800 seconds (30 minutes) from last activity

**Limits**:
- MAX_MESSAGES: 20
- MAX_TOKENS: 8000 (FIFO truncation when exceeded)

---

## Entity Relationships

```
┌───────────────────────────────────────────────────────────────────┐
│                        WORKSPACE                                  │
│  (existing entity)                                                │
└──────────────────┬────────────────────────────────────────────────┘
                   │
                   │ 1:N
                   │
    ┌──────────────┼──────────────┬──────────────┐
    │              │              │              │
    ▼              ▼              ▼              ▼
┌─────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐
│Workspace│  │AIApproval │  │AICost    │  │AISession   │
│APIKey   │  │Request    │  │Record    │  │(Redis)     │
│         │  │           │  │          │  │            │
│N per ws │  │N per ws   │  │N per ws  │  │N per user  │
└─────────┘  └───────────┘  └──────────┘  └────────────┘
     │              │              │
     │              │              │
     │              └──────────────┤
     │                             │
     ▼                             ▼
┌─────────────────┐         ┌───────────────┐
│  Supabase Vault │         │     USER      │
│  (secret store) │         │ (existing)    │
└─────────────────┘         └───────────────┘
```

---

## Migration Scripts

### Migration 1: add_workspace_api_keys_table

**File**: `backend/alembic/versions/YYYY_MM_DD_add_workspace_api_keys.py`

```python
"""Add workspace_api_keys table for BYOK storage.

Revision ID: 004_001
Revises: [previous_revision]
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '004_001'
down_revision = '[previous_revision]'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workspace_api_keys',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('vault_secret_id', UUID(as_uuid=True), nullable=False),
        sa.Column('validation_status', sa.String(20), nullable=False,
                  server_default='pending'),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'],
                                ondelete='CASCADE'),
        sa.UniqueConstraint('workspace_id', 'provider',
                           name='uq_workspace_api_keys_workspace_provider'),
        sa.CheckConstraint(
            "provider IN ('anthropic', 'openai', 'google', 'azure')",
            name='ck_workspace_api_keys_provider'
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid')",
            name='ck_workspace_api_keys_status'
        ),
    )

    op.create_index('idx_workspace_api_keys_workspace', 'workspace_api_keys',
                    ['workspace_id'])

    # Enable RLS
    op.execute('ALTER TABLE workspace_api_keys ENABLE ROW LEVEL SECURITY')

    # RLS Policy
    op.execute("""
        CREATE POLICY workspace_api_keys_admin_access ON workspace_api_keys
        FOR ALL
        USING (workspace_id IN (
            SELECT workspace_id FROM workspace_members
            WHERE user_id = auth.uid() AND role IN ('admin', 'owner')
        ))
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS workspace_api_keys_admin_access ON workspace_api_keys')
    op.drop_table('workspace_api_keys')
```

### Migration 2: add_ai_approval_requests_table

**File**: `backend/alembic/versions/YYYY_MM_DD_add_ai_approval_requests.py`

```python
"""Add ai_approval_requests table for human-in-the-loop.

Revision ID: 004_002
Revises: 004_001
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '004_002'
down_revision = '004_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_approval_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('payload', JSONB(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', UUID(as_uuid=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id']),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name='ck_ai_approval_requests_status'
        ),
        sa.CheckConstraint(
            'confidence >= 0 AND confidence <= 1',
            name='ck_ai_approval_requests_confidence'
        ),
    )

    op.create_index('idx_ai_approval_requests_user_status',
                    'ai_approval_requests', ['user_id', 'status'])
    op.create_index('idx_ai_approval_requests_workspace_status',
                    'ai_approval_requests', ['workspace_id', 'status'])
    op.create_index('idx_ai_approval_requests_expires',
                    'ai_approval_requests', ['expires_at'],
                    postgresql_where=sa.text("status = 'pending'"))

    # Enable RLS
    op.execute('ALTER TABLE ai_approval_requests ENABLE ROW LEVEL SECURITY')

    # RLS Policies
    op.execute("""
        CREATE POLICY ai_approval_requests_user_access ON ai_approval_requests
        FOR SELECT
        USING (user_id = auth.uid())
    """)

    op.execute("""
        CREATE POLICY ai_approval_requests_admin_access ON ai_approval_requests
        FOR ALL
        USING (workspace_id IN (
            SELECT workspace_id FROM workspace_members
            WHERE user_id = auth.uid() AND role IN ('admin', 'owner')
        ))
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS ai_approval_requests_user_access ON ai_approval_requests')
    op.execute('DROP POLICY IF EXISTS ai_approval_requests_admin_access ON ai_approval_requests')
    op.drop_table('ai_approval_requests')
```

### Migration 3: add_ai_cost_records_table

**File**: `backend/alembic/versions/YYYY_MM_DD_add_ai_cost_records.py`

```python
"""Add ai_cost_records table for usage tracking.

Revision ID: 004_003
Revises: 004_002
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '004_003'
down_revision = '004_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_cost_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('total_cost_usd', sa.Numeric(10, 6), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'],
                                ondelete='CASCADE'),
        sa.CheckConstraint('input_tokens >= 0', name='ck_ai_cost_records_input'),
        sa.CheckConstraint('output_tokens >= 0', name='ck_ai_cost_records_output'),
        sa.CheckConstraint('total_cost_usd >= 0', name='ck_ai_cost_records_cost'),
        sa.CheckConstraint('duration_ms >= 0', name='ck_ai_cost_records_duration'),
    )

    op.create_index('idx_ai_cost_records_workspace_created',
                    'ai_cost_records', ['workspace_id', sa.text('created_at DESC')])
    op.create_index('idx_ai_cost_records_user_created',
                    'ai_cost_records', ['user_id', sa.text('created_at DESC')])
    op.create_index('idx_ai_cost_records_agent_type',
                    'ai_cost_records', ['agent_type', sa.text('created_at DESC')])

    # Enable RLS
    op.execute('ALTER TABLE ai_cost_records ENABLE ROW LEVEL SECURITY')

    # RLS Policies (SELECT only - audit records are immutable)
    op.execute("""
        CREATE POLICY ai_cost_records_user_access ON ai_cost_records
        FOR SELECT
        USING (user_id = auth.uid())
    """)

    op.execute("""
        CREATE POLICY ai_cost_records_admin_access ON ai_cost_records
        FOR SELECT
        USING (workspace_id IN (
            SELECT workspace_id FROM workspace_members
            WHERE user_id = auth.uid() AND role IN ('admin', 'owner')
        ))
    """)

    # Aggregate view for cost summary
    op.execute("""
        CREATE VIEW workspace_daily_ai_costs AS
        SELECT
            workspace_id,
            DATE(created_at) AS date,
            agent_type,
            provider,
            COUNT(*) AS request_count,
            SUM(input_tokens) AS total_input_tokens,
            SUM(output_tokens) AS total_output_tokens,
            SUM(total_cost_usd) AS total_cost_usd,
            AVG(duration_ms)::INTEGER AS avg_duration_ms
        FROM ai_cost_records
        GROUP BY workspace_id, DATE(created_at), agent_type, provider
    """)


def downgrade() -> None:
    op.execute('DROP VIEW IF EXISTS workspace_daily_ai_costs')
    op.execute('DROP POLICY IF EXISTS ai_cost_records_user_access ON ai_cost_records')
    op.execute('DROP POLICY IF EXISTS ai_cost_records_admin_access ON ai_cost_records')
    op.drop_table('ai_cost_records')
```

---

## Validation Rules

### WorkspaceAPIKey
- `provider` must be one of: anthropic, openai, google, azure
- `validation_status` must be one of: pending, valid, invalid
- `vault_secret_id` must reference valid Supabase Vault secret

### AIApprovalRequest
- `confidence` must be between 0.0 and 1.0
- `status` must be one of: pending, approved, rejected, expired
- `expires_at` should be 24 hours after `created_at`
- `resolved_by` required when status is approved/rejected

### AICostRecord
- All numeric fields must be non-negative
- `total_cost_usd` should match provider pricing calculation
- Immutable after creation (no UPDATE/DELETE)

### AISession (Redis)
- `messages` array max length: 20
- Total token count max: 8000
- TTL: 30 minutes from last activity
