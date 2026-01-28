"""Infrastructure tests for PilotSpace.

Tests infrastructure dependencies before running feature tests:
- Database (PostgreSQL, pgvector, RLS, migrations)
- Redis (connectivity, sessions, TTL, pub/sub)
- Meilisearch (health, indices, search)
- Supabase Auth (GoTrue, token validation, RLS integration)
- Sandbox (provisioning, resource limits, isolation, cleanup)

These tests must pass before proceeding to API or E2E tests.
"""
