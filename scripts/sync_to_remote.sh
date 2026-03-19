#!/bin/bash
# sync_to_remote.sh — Sync local DB schema & seed data to remote Supabase
#
# Usage:
#   ./scripts/sync_to_remote.sh [--schema-only | --seed-only | --full]
#
# Prerequisites:
#   - Local Docker Supabase running (infra/supabase)
#   - Remote Supabase project created
#   - REMOTE_DATABASE_URL set in backend/.env or as env var
#
# The script:
#   1. Temporarily patches migration files that use auth.uid() → current_setting()
#   2. Grants pilot_admin access to cron/pgmq schemas via MCP workaround
#   3. Runs Alembic migrations against remote DB
#   4. Reverts patches
#   5. Seeds demo data

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Load env
if [ -f "$BACKEND_DIR/.env" ]; then
    set -a
    source "$BACKEND_DIR/.env"
    set +a
fi

# Remote DB config (override via env or .env)
REMOTE_DB_URL="${REMOTE_DATABASE_URL:-}"
if [ -z "$REMOTE_DB_URL" ]; then
    echo "ERROR: REMOTE_DATABASE_URL not set."
    echo "  Set it in backend/.env or export it:"
    echo "  export REMOTE_DATABASE_URL=postgresql+asyncpg://pilot_admin:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres"
    exit 1
fi

MODE="${1:---full}"

echo "================================================"
echo "  Pilot Space — Sync to Remote Supabase"
echo "================================================"
echo "Mode: $MODE"
REMOTE_HOST="${REMOTE_DB_URL#*@}"
echo "Remote: ***@${REMOTE_HOST}"
echo ""

# --- SCHEMA SYNC ---
if [ "$MODE" = "--schema-only" ] || [ "$MODE" = "--full" ]; then
    echo "[1/3] Patching migration files for Supabase hosted..."

    # Patch auth.uid() → current_setting() for non-superuser compatibility
    cd "$BACKEND_DIR"

    PATCH_FILES=(
        "alembic/versions/024_enhanced_mcp_models.py"
        "alembic/versions/034_fix_homepage_rls_policies.py"
    )

    for f in "${PATCH_FILES[@]}"; do
        if [ -f "$f" ]; then
            sed -i.bak "s/auth\.uid()/current_setting('app.current_user_id', true)::uuid/g" "$f"
        fi
    done

    # Patch env.py for transaction_per_migration
    cp alembic/env.py alembic/env.py.bak
    sed -i '' 's/version_num_col_type=String(128),$/version_num_col_type=String(128),\n        transaction_per_migration=True,/' \
        alembic/env.py
    sed -i '' '/with context.begin_transaction():/d' alembic/env.py
    sed -i '' 's/^        context.run_migrations()/    context.run_migrations()/' alembic/env.py

    echo "[2/3] Running Alembic migrations against remote..."
    DATABASE_URL="$REMOTE_DB_URL" uv run alembic upgrade head

    echo "[2.5/3] Reverting patches..."
    for f in "${PATCH_FILES[@]}"; do
        if [ -f "$f.bak" ]; then
            mv "$f.bak" "$f"
        fi
    done
    mv alembic/env.py.bak alembic/env.py 2>/dev/null || true

    echo "Schema sync complete."
fi

# --- DATA SEED ---
if [ "$MODE" = "--seed-only" ] || [ "$MODE" = "--full" ]; then
    echo "[3/3] Seeding demo data..."
    SEED_FAILED=false
    DATABASE_URL="$REMOTE_DB_URL" uv run python scripts/seed_demo.py 2>&1 || {
        SEED_FAILED=true
        echo "Note: seed_demo.py requires SUPABASE_URL and SUPABASE_SERVICE_KEY"
        echo "For remote Supabase, you may need to create the auth user via the dashboard first."
    }
fi

echo ""
if [ "${SEED_FAILED:-false}" = "true" ]; then
    echo "⚠️  Schema sync succeeded, but seeding failed. See above for details."
else
    echo "Done! Remote Supabase is synced."
fi
