# Data Model Design Prompt Template

> **Purpose**: Design production-ready data models with proper relationships, constraints, and migration strategies.
>
> **Source**: Extracted from `specs/001-pilot-space-mvp/data-model.md` patterns and plan.md entity requirements
>
> **Usage**: Use when designing new entities or modifying existing data models.

---

## Prompt Template

```markdown
# Expert Persona (P16)

You are a Senior Database Architect with 15 years designing scalable data models.
You excel at:
- Designing normalized schemas that balance query performance with data integrity
- Creating migration strategies that minimize downtime and data loss
- Implementing soft deletion, audit trails, and multi-tenancy patterns
- Optimizing for read-heavy vs write-heavy workloads

# Stakes Framing (P6)

This data model design is critical to [PROJECT_NAME]'s scalability and data integrity.
A well-designed model will:
- Prevent data corruption and orphaned records
- Enable efficient queries without N+1 problems
- Support future feature additions without major migrations
- Maintain referential integrity across all relationships

I'll tip you $200 for a production-ready data model with complete migration strategy.

# Task Context

## Entity Overview
**Entity Name**: [ENTITY_NAME]
**Purpose**: [ONE_SENTENCE_PURPOSE]
**User Stories**: [US-XX, US-YY]
**Expected Volume**: [ROWS_PER_WORKSPACE]

## Technology Stack
**ORM**: SQLAlchemy 2.0 (async)
**Database**: PostgreSQL 16+ with pgvector
**Migrations**: Alembic
**Multi-tenancy**: Workspace-scoped with RLS

## Related Entities
| Entity | Relationship | Cardinality |
|--------|--------------|-------------|
| [RELATED_ENTITY] | [RELATIONSHIP_TYPE] | 1:N / N:1 / N:M |

# Task Decomposition (P3)

Design the data model step by step:

## Step 1: Entity Definition
Define the core entity structure:

```python
# SQLAlchemy Model Template
class [EntityName](Base):
    __tablename__ = "[table_name]"

    # Primary Key (UUID, database-generated)
    id: Mapped[UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    # Foreign Keys
    [fk_field]: Mapped[UUID] = mapped_column(
        pg.UUID(as_uuid=True),
        ForeignKey("[table].[column]", ondelete="CASCADE"),
        nullable=False
    )

    # Fields
    [field_name]: Mapped[[type]] = mapped_column(
        [SQLAlchemy_Type],
        nullable=[True/False],
        default=[default_value],
        index=[True/False]
    )

    # Timestamps (required for all entities)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False
    )

    # Soft Delete (required for all entities)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        index=True
    )

    # Relationships
    [relationship]: Mapped["[RelatedEntity]"] = relationship(
        back_populates="[reverse_name]",
        lazy="selectin"  # Prevent N+1
    )
```

## Step 2: Field Specifications

Detail each field with constraints:

| Field | Type | Nullable | Default | Index | Constraints |
|-------|------|----------|---------|-------|-------------|
| id | UUID | No | gen_random_uuid() | PK | - |
| [field] | [type] | [Y/N] | [default] | [Y/N] | [constraints] |

**Field Types**:
- `String(N)` - Variable length text, max N chars
- `Text` - Unlimited text
- `Integer` / `BigInteger` - Numeric
- `Numeric(precision, scale)` - Decimal
- `Boolean` - True/False
- `JSONB` - Structured data (TipTap content, metadata)
- `TIMESTAMP(timezone=True)` - Datetime with timezone
- `pg.UUID(as_uuid=True)` - UUID
- `pgvector.Vector(N)` - Embedding vector

## Step 3: Relationship Design

Define all relationships:

### [Relationship Name]
| Aspect | Value |
|--------|-------|
| **Type** | One-to-Many / Many-to-One / Many-to-Many |
| **Parent Entity** | [ENTITY] |
| **Child Entity** | [ENTITY] |
| **Foreign Key** | [FK_COLUMN] |
| **On Delete** | CASCADE / SET NULL / RESTRICT |
| **Lazy Loading** | selectin / joined / subquery |

**Junction Table** (for M:N):
```python
[junction_table] = Table(
    "[table_name]",
    Base.metadata,
    Column("[entity1]_id", pg.UUID, ForeignKey("[entity1].id", ondelete="CASCADE")),
    Column("[entity2]_id", pg.UUID, ForeignKey("[entity2].id", ondelete="CASCADE")),
    Column("created_at", TIMESTAMP(timezone=True), server_default=text("now()")),
    UniqueConstraint("[entity1]_id", "[entity2]_id")
)
```

## Step 4: Indexes & Constraints

Define performance optimizations:

**Indexes**:
```sql
-- Single column indexes
CREATE INDEX idx_[table]_[column] ON [table]([column]);

-- Composite indexes (for common query patterns)
CREATE INDEX idx_[table]_[col1]_[col2] ON [table]([col1], [col2]);

-- Partial indexes (for soft delete)
CREATE INDEX idx_[table]_active ON [table]([column])
WHERE deleted_at IS NULL;

-- GIN index (for JSONB)
CREATE INDEX idx_[table]_[jsonb_col] ON [table]
USING GIN ([jsonb_col]);

-- Vector index (for embeddings)
CREATE INDEX idx_[table]_embedding ON [table]
USING hnsw ([embedding_col] vector_cosine_ops);
```

**Constraints**:
```sql
-- Unique constraint
ALTER TABLE [table] ADD CONSTRAINT [name] UNIQUE ([columns]);

-- Check constraint
ALTER TABLE [table] ADD CONSTRAINT [name] CHECK ([condition]);

-- Exclusion constraint (for overlapping ranges)
ALTER TABLE [table] ADD CONSTRAINT [name]
EXCLUDE USING gist ([range_col] WITH &&);
```

## Step 5: RLS Policies

Define Row-Level Security (required for multi-tenancy):

```sql
-- Enable RLS
ALTER TABLE [table] ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see rows in their workspace
CREATE POLICY [table]_workspace_isolation ON [table]
    FOR ALL
    USING (workspace_id = current_setting('app.current_workspace')::uuid);

-- Policy: Admins can see all rows in workspace
CREATE POLICY [table]_admin_access ON [table]
    FOR ALL
    USING (
        workspace_id = current_setting('app.current_workspace')::uuid
        AND current_setting('app.current_role') = 'admin'
    );

-- Policy: Users can only modify their own records
CREATE POLICY [table]_owner_modify ON [table]
    FOR UPDATE
    USING (created_by = current_setting('app.current_user')::uuid);
```

## Step 6: State Machine (if applicable)

For entities with workflow states:

```python
class [Entity]State(str, Enum):
    [STATE_1] = "[state_1]"
    [STATE_2] = "[state_2]"
    [STATE_3] = "[state_3]"

# Valid transitions
TRANSITIONS = {
    [Entity]State.[STATE_1]: [[Entity]State.[STATE_2]],
    [Entity]State.[STATE_2]: [[Entity]State.[STATE_3], [Entity]State.[STATE_1]],
    [Entity]State.[STATE_3]: [],  # Terminal state
}
```

**State Diagram**:
```
[STATE_1] → [STATE_2] → [STATE_3]
     ↑          |
     └──────────┘
```

## Step 7: Migration Strategy

Plan the migration:

```python
# Alembic migration
def upgrade() -> None:
    # Step 1: Create table
    op.create_table(
        "[table_name]",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # ... other columns
    )

    # Step 2: Add indexes
    op.create_index("idx_[table]_[column]", "[table]", ["[column]"])

    # Step 3: Enable RLS
    op.execute("ALTER TABLE [table] ENABLE ROW LEVEL SECURITY")

    # Step 4: Create policies
    op.execute("""
        CREATE POLICY [table]_workspace_isolation ON [table]
        FOR ALL USING (workspace_id = current_setting('app.current_workspace')::uuid)
    """)

def downgrade() -> None:
    op.drop_table("[table_name]")
```

**Migration Checklist**:
- [ ] Table created with all columns
- [ ] Foreign keys with proper ON DELETE behavior
- [ ] Indexes for query patterns
- [ ] RLS enabled with policies
- [ ] Soft delete column indexed
- [ ] Timestamps have server defaults
- [ ] Down migration is reversible

## Step 8: Pydantic Schemas

Define API schemas:

```python
# Base schema (shared fields)
class [Entity]Base(BaseModel):
    [field]: [type]

    model_config = ConfigDict(from_attributes=True)

# Create schema (POST request)
class [Entity]Create([Entity]Base):
    pass

# Update schema (PATCH request)
class [Entity]Update(BaseModel):
    [field]: Optional[[type]] = None

# Response schema (GET response)
class [Entity]Response([Entity]Base):
    id: UUID
    created_at: datetime
    updated_at: datetime

# List response (pagination)
class [Entity]ListResponse(BaseModel):
    data: list[[Entity]Response]
    meta: PaginationMeta
```

# Chain-of-Thought Guidance (P12)

For each design decision:
1. **What queries will use this?** - Design indexes for common patterns
2. **What could go wrong?** - Orphaned records, N+1 queries, data races
3. **How does it scale?** - Volume estimates, partition strategy
4. **How to migrate?** - Zero-downtime deployment strategy
5. **What's the rollback plan?** - Reversible migration

# Self-Evaluation Framework (P15)

After designing, rate confidence (0-1):

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Normalization**: Appropriate level for use case | ___ | |
| **Relationships**: All FKs and constraints defined | ___ | |
| **Indexes**: Common queries covered | ___ | |
| **Security**: RLS policies complete | ___ | |
| **Migration**: Reversible with no data loss | ___ | |
| **Schemas**: Pydantic models complete | ___ | |

**Refinement Threshold**: If any score < 0.9, identify gap and refine.

# Output Format

```markdown
## Data Model: [ENTITY_NAME]

### Overview
| Attribute | Value |
|-----------|-------|
| **Table Name** | [table_name] |
| **Purpose** | [ONE_LINER] |
| **User Stories** | US-[XX], US-[YY] |
| **Expected Volume** | [N] rows/workspace |

### SQLAlchemy Model
\`\`\`python
[FULL_MODEL_CODE]
\`\`\`

### Field Specifications
| Field | Type | Nullable | Index | Constraints |
|-------|------|----------|-------|-------------|
| [field] | [type] | [Y/N] | [Y/N] | [constraints] |

### Relationships
[RELATIONSHIP_DIAGRAM]

### Indexes
\`\`\`sql
[INDEX_DEFINITIONS]
\`\`\`

### RLS Policies
\`\`\`sql
[POLICY_DEFINITIONS]
\`\`\`

### State Machine (if applicable)
[STATE_DIAGRAM]

### Migration
\`\`\`python
[ALEMBIC_MIGRATION]
\`\`\`

### Pydantic Schemas
\`\`\`python
[SCHEMA_DEFINITIONS]
\`\`\`

---
*Model Version: 1.0*
*User Stories: US-[XX], US-[YY]*
```
```

---

## Quick-Fill Variants

### Variant A: Note Entity (Pilot Space)

```markdown
**Entity Name**: Note
**Purpose**: Block-based document with AI annotations
**User Stories**: US-01, US-06
**Expected Volume**: ~1000 notes/workspace

**Key Fields**:
- id (UUID, PK)
- workspace_id (UUID, FK → workspaces)
- project_id (UUID, FK → projects)
- title (String(255))
- content (JSONB - TipTap native format)
- embedding (Vector(3072) - for semantic search)
- created_by (UUID, FK → users)
- created_at, updated_at, deleted_at

**Relationships**:
- workspace: Many-to-One
- project: Many-to-One
- annotations: One-to-Many
- linked_issues: Many-to-Many via junction

**Indexes**:
- workspace_id (for listing)
- project_id (for filtering)
- embedding (HNSW for vector search)
- content GIN (for full-text search)
```

### Variant B: Issue Entity (Pilot Space)

```markdown
**Entity Name**: Issue
**Purpose**: Work item with state machine and AI metadata
**User Stories**: US-02, US-04, US-12
**Expected Volume**: ~50000 issues/workspace

**Key Fields**:
- id (UUID, PK)
- workspace_id, project_id (FKs)
- title (String(500))
- description (Text)
- state_id (FK → issue_states)
- priority (Enum: urgent, high, medium, low, none)
- estimate_points (Integer, nullable)
- parent_id (UUID, FK → issues, nullable - for sub-tasks)
- cycle_id, module_id (FKs, nullable)
- ai_context (JSONB - aggregated AI context)

**State Machine**:
backlog → todo → in_progress → in_review → done
                     ↓
                 cancelled

**Indexes**:
- (workspace_id, state_id) - for board views
- (project_id, priority) - for backlog
- parent_id - for sub-task queries
```

---

## Validation Checklist

Before implementing, verify:

- [ ] All fields have explicit types and constraints
- [ ] Primary key is UUID with gen_random_uuid()
- [ ] Foreign keys have ON DELETE behavior
- [ ] created_at/updated_at/deleted_at present
- [ ] Indexes cover common query patterns
- [ ] RLS policies enforce workspace isolation
- [ ] State machine transitions documented
- [ ] Migration is reversible
- [ ] Pydantic schemas match API contract

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `specs/001-pilot-space-mvp/data-model.md` | Full data model spec |
| `docs/architect/rls-patterns.md` | RLS security patterns |
| `docs/dev-pattern/07-repository-pattern.md` | Repository pattern |
| `docs/dev-pattern/28b-database-migrations.md` | Migration patterns |

---

*Template Version: 1.0*
*Extracted from: plan.md v7.1 and data-model.md*
*Techniques Applied: P3 (decomposition), P6 (stakes), P12 (CoT), P15 (self-eval), P16 (persona)*
