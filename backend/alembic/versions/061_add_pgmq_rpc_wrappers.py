"""Add public wrapper functions for pgmq RPC operations.

Revision ID: 061_add_pgmq_rpc_wrappers
Revises: 060_add_unique_constraint
Create Date: 2026-03-06

SupabaseQueueClient uses the Supabase REST API /rpc/{function_name} endpoint
which only exposes functions in the public schema.  The pgmq extension installs
its functions in the pgmq schema, so they are not reachable via REST.

This migration creates thin public wrapper functions that delegate to the
schema-qualified pgmq functions.  All wrappers are SECURITY DEFINER so that
service-role callers (the API) can invoke them without needing direct pgmq
schema EXECUTE grants.

Wrappers:
  pgmq_create(queue_name TEXT)          → pgmq.create(queue_name)
  pgmq_send(queue_name, msg, delay)     → pgmq.send(queue_name, msg, delay)
  pgmq_read(queue_name, vt, qty)        → pgmq.read(queue_name, vt, qty)
  pgmq_delete(queue_name, msg_id)       → pgmq.delete(queue_name, msg_id)
  pgmq_archive(queue_name, msg_id)      → pgmq.archive(queue_name, msg_id)
  pgmq_drop(queue_name)                 → pgmq.drop_queue(queue_name)
  pgmq_purge(queue_name)                → pgmq.purge_queue(queue_name)
  pgmq_metrics(queue_name)              → pgmq.metrics(queue_name)
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "061_add_pgmq_rpc_wrappers"
down_revision = "060_add_unique_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
-- ---------------------------------------------------------------------------
-- pgmq_create: create a new queue (idempotent)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_create(queue_name TEXT)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    PERFORM pgmq.create(queue_name);
END;
$$;

-- ---------------------------------------------------------------------------
-- pgmq_send: enqueue a message, returns the pgmq message ID
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_send(
    queue_name TEXT,
    msg        JSONB,
    delay      INT DEFAULT 0
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN pgmq.send(queue_name, msg, delay);
END;
$$;

-- ---------------------------------------------------------------------------
-- pgmq_read: dequeue up to qty messages with visibility timeout vt seconds
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_read(
    queue_name TEXT,
    vt         INT,
    qty        INT
)
RETURNS SETOF pgmq.message_record
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY SELECT * FROM pgmq.read(queue_name, vt, qty);
END;
$$;

-- ---------------------------------------------------------------------------
-- pgmq_delete: acknowledge and permanently remove a message
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_delete(
    queue_name TEXT,
    msg_id     BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN pgmq.delete(queue_name, msg_id);
END;
$$;

-- ---------------------------------------------------------------------------
-- pgmq_archive: move a message to the archive table (soft delete / nack)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_archive(
    queue_name TEXT,
    msg_id     BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN pgmq.archive(queue_name, msg_id);
END;
$$;

-- ---------------------------------------------------------------------------
-- pgmq_drop: delete a queue and all its messages
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_drop(queue_name TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN pgmq.drop_queue(queue_name);
END;
$$;

-- ---------------------------------------------------------------------------
-- pgmq_purge: delete all pending messages from a queue, returns count
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_purge(queue_name TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN pgmq.purge_queue(queue_name);
END;
$$;

-- ---------------------------------------------------------------------------
-- pgmq_metrics: queue metrics (queue_length, newest/oldest msg age, etc.)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pgmq_metrics(queue_name TEXT)
RETURNS SETOF pgmq.metrics_result
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY SELECT * FROM pgmq.metrics(queue_name);
END;
$$;
"""
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
DROP FUNCTION IF EXISTS public.pgmq_create(TEXT);
DROP FUNCTION IF EXISTS public.pgmq_send(TEXT, JSONB, INT);
DROP FUNCTION IF EXISTS public.pgmq_read(TEXT, INT, INT);
DROP FUNCTION IF EXISTS public.pgmq_delete(TEXT, BIGINT);
DROP FUNCTION IF EXISTS public.pgmq_archive(TEXT, BIGINT);
DROP FUNCTION IF EXISTS public.pgmq_drop(TEXT);
DROP FUNCTION IF EXISTS public.pgmq_purge(TEXT);
DROP FUNCTION IF EXISTS public.pgmq_metrics(TEXT);
"""
        )
    )
