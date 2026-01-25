"""Infrastructure layer for Pilot Space.

This package contains external system integrations:
- database/: PostgreSQL via SQLAlchemy (models, repositories)
- cache/: Redis client
- queue/: Supabase Queues (pgmq + pg_cron)
- search/: Meilisearch client
- storage/: Supabase Storage (S3-compatible)
- auth/: Supabase Auth (GoTrue)
"""
