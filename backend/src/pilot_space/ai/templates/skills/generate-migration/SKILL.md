---
name: generate-migration
description: Generate an Alembic database migration for schema changes, with rollback procedure — requires admin approval before applying
approval: require
model: sonnet
tools: [write_to_note, insert_block, ask_user]
required_approval_role: admin
---

# Generate Migration Skill

Generate a complete, reversible Alembic migration for proposed database schema changes. Always requires admin approval before the migration can be applied, as schema changes are irreversible without a rollback procedure.

## Quick Start

Use this skill when:
- User requests a new migration (`/generate-migration`)
- Agent detects a schema change needed for a feature
- User describes a new table, column, or index requirement

**Example**:
```
User: "Generate a migration to add a 'priority' column (integer) to the issues table"

AI generates:
- Alembic migration file with upgrade() and downgrade()
- upgrade(): ALTER TABLE issues ADD COLUMN priority INTEGER DEFAULT 0
- downgrade(): ALTER TABLE issues DROP COLUMN priority
- Index if cardinality warrants it
```

## Workflow

1. **Gather Schema Context**
   - Read note content for schema requirements
   - Use `ask_user` to clarify ambiguous column types, constraints, or nullability
   - Identify affected tables and existing column names

2. **Design Migration**
   - Determine migration number by checking existing migrations (ask user for next number)
   - Write `upgrade()`: forward schema changes using `op.add_column`, `op.create_table`, etc.
   - Write `downgrade()`: exact reversal of every change in `upgrade()`
   - Add indexes for foreign keys and high-cardinality filter columns

3. **Validate Safety**
   - All new columns must be nullable or have a `server_default` (zero-downtime rule)
   - No `DROP TABLE` or `DROP COLUMN` in upgrade without explicit user confirmation
   - Destructive operations (DROP, TRUNCATE) require `ask_user` confirmation before generating

4. **Insert to Note**
   - Use `insert_block` to add the migration code block with file path header
   - Use `write_to_note` to add rollback instructions and deployment steps
   - Mark as `pending_approval` — admin must review before `alembic upgrade head`

5. **Return Approval-Required Status**
   - Return `status: pending_approval` with `required_approval_role: admin`
   - Include checklist: backup, staging test, rollback command

## Output Format

```json
{
  "status": "pending_approval",
  "skill": "generate-migration",
  "required_approval_role": "admin",
  "note_id": "note-uuid",
  "blocks_inserted": 1,
  "summary": "Migration to add priority column to issues — requires admin approval before alembic upgrade head",
  "migration_file": "backend/alembic/versions/038_add_priority_to_issues.py",
  "rollback_command": "alembic downgrade -1",
  "deployment_checklist": [
    "Backup database before applying",
    "Test on staging first: alembic upgrade head",
    "Verify rollback: alembic downgrade -1 on staging",
    "Apply to production during maintenance window"
  ]
}
```

## Examples

### Example 1: Add Column
**Input**: "Add a priority integer column to issues table with default 0"

**Output**: Inserts into note:
```
## Generated Migration: 038_add_priority_to_issues
<!-- File: backend/alembic/versions/038_add_priority_to_issues.py -->
<!-- REQUIRES ADMIN APPROVAL BEFORE APPLYING -->
\`\`\`python
"""Add priority column to issues.

Revision ID: 038_add_priority_to_issues
Revises: 037_previous_migration
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa

revision = "038_add_priority_to_issues"
down_revision = "037_previous_migration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "issues",
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_issues_priority", "issues", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_issues_priority", table_name="issues")
    op.drop_column("issues", "priority")
\`\`\`

### Deployment Checklist
1. Backup: `pg_dump $DATABASE_URL > backup_pre_038.sql`
2. Staging: `alembic upgrade head` → verify columns with `\d issues`
3. Rollback test: `alembic downgrade -1` → verify clean
4. Production: Apply during maintenance window
5. Rollback command: `alembic downgrade -1`
```

### Example 2: Create New Table
**Input**: "Create a workspace_events table for audit logging"

**Output**: Generates `op.create_table(...)` with full column spec, primary key, indexes, and RLS note.

## MCP Tools Used

- `search_note_content`: Read schema requirements and existing migration patterns
- `ask_user`: Clarify column types, constraints, nullability, or confirm destructive operations
- `insert_block`: Write migration code block to the note
- `write_to_note`: Add rollback instructions and deployment checklist

## Integration Points

- **PilotSpaceAgent**: Routes to this skill via `/generate-migration` command
- **SkillExecutor**: Acquires `note_write_lock:{note_id}` mutex before writes (C-3)
- **Approval Flow**: ALWAYS requires approval with `required_approval_role: admin` (DD-003, C-7)
- **Alembic**: Output follows existing migration numbering and parent revision pattern

## References

- Design Decision: DD-003 (Critical-only approval — migration is destructive)
- Constraint: C-7 (required_approval_role: admin for destructive skills)
- Constraint: C-3 (Redis mutex for note writes)
- Task: T-040
- Alembic docs: `docs/dev-pattern/07-repository.md`
