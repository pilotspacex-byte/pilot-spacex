# Deployment Guide

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This guide covers deploying Pilot Space to production using Supabase as the backend platform. Pilot Space uses a simplified 3-service architecture.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PRODUCTION STACK                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Next.js    │    │   FastAPI    │    │   Supabase   │  │
│  │   Frontend   │    │   Backend    │    │   Platform   │  │
│  │   (Vercel)   │    │   (Fly.io)   │    │   (Hosted)   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         └───────────────────┴───────────────────┘           │
│                                                              │
│  Supporting Services:                                        │
│  - Redis (Upstash)                                          │
│  - Meilisearch (Meilisearch Cloud)                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Accounts

| Service | Purpose | Tier |
|---------|---------|------|
| Supabase | Database, Auth, Storage, Queues | Pro ($25/mo) |
| Vercel | Frontend hosting | Pro ($20/mo) |
| Fly.io | Backend hosting | Pay-as-you-go |
| Upstash | Redis cache | Free tier |
| Meilisearch Cloud | Search | Build ($29/mo) |

### Required CLI Tools

```bash
# Install CLIs
npm install -g supabase vercel
brew install flyctl

# Authenticate
supabase login
vercel login
fly auth login
```

---

## Step 1: Supabase Setup

### Create Project

```bash
# Create new Supabase project
# Via Dashboard: https://app.supabase.com/new

# Or via CLI (if organization exists)
supabase projects create pilot-space-prod --org-id YOUR_ORG_ID --region us-east-1
```

### Configure Database

```bash
# Link to project
supabase link --project-ref YOUR_PROJECT_REF

# Apply migrations
supabase db push

# Seed initial data (optional)
supabase db seed
```

### Enable Extensions

```sql
-- Run in Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_cron";
CREATE EXTENSION IF NOT EXISTS "pgmq";
```

### Configure Row-Level Security

```sql
-- Enable RLS on all tables
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
-- ... (all tables)

-- Apply policies (see rls-patterns.md for details)
-- Example: workspace isolation
CREATE POLICY "workspace_member_access" ON issues
  FOR ALL
  USING (
    project_id IN (
      SELECT p.id FROM projects p
      JOIN workspace_members wm ON wm.workspace_id = p.workspace_id
      WHERE wm.user_id = auth.uid()
    )
  );
```

### Configure Authentication

```bash
# Via Supabase Dashboard > Authentication > Providers

# Enable providers:
# - Email (with magic link)
# - Google OAuth
# - GitHub OAuth
# - SAML (for enterprise)
```

**Environment variables for providers**:
```env
# Google OAuth
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# GitHub OAuth
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
```

### Configure Storage

```sql
-- Create storage buckets
INSERT INTO storage.buckets (id, name, public)
VALUES
  ('avatars', 'avatars', true),
  ('attachments', 'attachments', false),
  ('exports', 'exports', false);

-- Storage policies
CREATE POLICY "avatar_read_all" ON storage.objects
  FOR SELECT USING (bucket_id = 'avatars');

CREATE POLICY "attachment_workspace_access" ON storage.objects
  FOR ALL USING (
    bucket_id = 'attachments' AND
    -- Custom function to check workspace membership
    auth.check_workspace_access(storage.foldername(name))
  );
```

### Configure Background Jobs

```sql
-- Create job queues
SELECT pgmq.create('ai_tasks');
SELECT pgmq.create('notifications');
SELECT pgmq.create('webhooks');

-- Schedule recurring jobs
SELECT cron.schedule(
  'daily-cleanup',
  '0 2 * * *',  -- 2 AM UTC
  $$DELETE FROM activity_logs WHERE created_at < NOW() - INTERVAL '90 days'$$
);

SELECT cron.schedule(
  'weekly-embeddings',
  '0 3 * 0',  -- 3 AM Sunday
  $$SELECT refresh_semantic_relationships()$$
);
```

---

## Step 2: Backend Deployment (Fly.io)

### Initialize Fly App

```bash
cd backend

# Create app
fly launch --name pilot-space-api --region iad

# This creates fly.toml
```

### Configure fly.toml

```toml
# fly.toml
app = "pilot-space-api"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"
  ENVIRONMENT = "production"
  LOG_LEVEL = "info"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [services.concurrency]
    type = "requests"
    hard_limit = 250
    soft_limit = 200

  [[services.http_checks]]
    interval = "15s"
    timeout = "10s"
    grace_period = "30s"
    method = "GET"
    path = "/health"
```

### Set Secrets

```bash
# Database
fly secrets set SUPABASE_URL="https://xxx.supabase.co"
fly secrets set SUPABASE_KEY="service_role_key"
fly secrets set DATABASE_URL="postgres://..."

# Redis
fly secrets set REDIS_URL="redis://xxx.upstash.io:6379"

# Meilisearch
fly secrets set MEILISEARCH_URL="https://xxx.meilisearch.io"
fly secrets set MEILISEARCH_KEY="xxx"

# AI Providers (optional - users bring their own)
# These are defaults for system operations
fly secrets set ANTHROPIC_API_KEY="xxx"
fly secrets set OPENAI_API_KEY="xxx"

# GitHub App
fly secrets set GITHUB_APP_ID="xxx"
fly secrets set GITHUB_PRIVATE_KEY="xxx"
fly secrets set GITHUB_WEBHOOK_SECRET="xxx"

# Slack App
fly secrets set SLACK_CLIENT_ID="xxx"
fly secrets set SLACK_CLIENT_SECRET="xxx"
fly secrets set SLACK_SIGNING_SECRET="xxx"
```

### Deploy

```bash
# Deploy to Fly.io
fly deploy

# Check status
fly status

# View logs
fly logs
```

### Configure Auto-scaling

```bash
# Set scaling parameters
fly scale count 2 --max-per-region 4

# Memory allocation
fly scale memory 1024
```

---

## Step 3: Frontend Deployment (Vercel)

### Connect Repository

```bash
# Via Vercel Dashboard or CLI
vercel link

# Or import from GitHub
# https://vercel.com/import
```

### Configure Environment Variables

In Vercel Dashboard > Settings > Environment Variables:

```env
# API
NEXT_PUBLIC_API_URL=https://api.pilotspace.io

# Supabase (client-side)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx

# Analytics (optional)
NEXT_PUBLIC_POSTHOG_KEY=xxx
```

### Configure vercel.json

```json
{
  "framework": "nextjs",
  "buildCommand": "pnpm build",
  "installCommand": "pnpm install",
  "regions": ["iad1"],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        }
      ]
    }
  ]
}
```

### Deploy

```bash
# Deploy to production
vercel --prod

# Or auto-deploy via GitHub integration
git push origin main
```

---

## Step 4: Supporting Services

### Redis (Upstash)

1. Create database at https://console.upstash.com
2. Select region close to backend (us-east-1)
3. Copy connection URL
4. Set as `REDIS_URL` secret in Fly.io

### Meilisearch Cloud

1. Create project at https://cloud.meilisearch.com
2. Note the URL and API key
3. Set secrets in Fly.io

**Initialize indexes**:
```bash
# Create indexes via API
curl -X POST 'https://xxx.meilisearch.io/indexes' \
  -H 'Authorization: Bearer xxx' \
  -H 'Content-Type: application/json' \
  -d '{"uid": "issues", "primaryKey": "id"}'

curl -X POST 'https://xxx.meilisearch.io/indexes' \
  -H 'Authorization: Bearer xxx' \
  -H 'Content-Type: application/json' \
  -d '{"uid": "notes", "primaryKey": "id"}'
```

---

## Step 5: DNS & SSL

### Configure DNS

```
# A Records (if using custom domain)
api.pilotspace.io    → Fly.io IP
app.pilotspace.io    → Vercel IP (or CNAME)

# CNAME for Vercel
app.pilotspace.io    → cname.vercel-dns.com
```

### SSL Certificates

- **Fly.io**: Automatic via Let's Encrypt
- **Vercel**: Automatic via Let's Encrypt
- **Supabase**: Managed SSL included

---

## Step 6: GitHub Integration Setup

### Create GitHub App

1. Go to GitHub > Settings > Developer Settings > GitHub Apps
2. Create new app with:
   - **Name**: Pilot Space
   - **Homepage URL**: https://pilotspace.io
   - **Callback URL**: https://api.pilotspace.io/api/v1/integrations/github/callback
   - **Webhook URL**: https://api.pilotspace.io/api/v1/webhooks/github
   - **Webhook Secret**: Generate and save

3. Permissions required:
   - Repository contents: Read
   - Pull requests: Read & Write
   - Issues: Read (optional, for linking)
   - Metadata: Read

4. Subscribe to events:
   - Pull request
   - Push

5. Generate private key and save

---

## Step 7: Slack Integration Setup

### Create Slack App

1. Go to https://api.slack.com/apps
2. Create new app from manifest:

```yaml
display_information:
  name: Pilot Space
  description: AI-augmented SDLC platform
  background_color: "#29A386"

features:
  bot_user:
    display_name: Pilot Space
    always_online: true
  slash_commands:
    - command: /pilot
      url: https://api.pilotspace.io/api/v1/webhooks/slack/commands
      description: Create issues and interact with Pilot Space

oauth_config:
  scopes:
    bot:
      - chat:write
      - commands
      - links:read
      - links:write

settings:
  event_subscriptions:
    request_url: https://api.pilotspace.io/api/v1/webhooks/slack/events
    bot_events:
      - link_shared
  interactivity:
    is_enabled: true
    request_url: https://api.pilotspace.io/api/v1/webhooks/slack/interactive
```

---

## Monitoring & Alerting

### Health Checks

Backend exposes `/health` endpoint:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "meilisearch": "ok"
  }
}
```

### Recommended Monitoring

| Service | Purpose |
|---------|---------|
| Fly.io Metrics | Backend performance |
| Vercel Analytics | Frontend performance |
| Supabase Dashboard | Database metrics |
| Sentry | Error tracking |
| Upstash Console | Redis metrics |

### Alerting Rules

```yaml
# Example Fly.io alerts
alerts:
  - name: high_error_rate
    condition: error_rate > 1%
    duration: 5m
    notify: slack

  - name: high_latency
    condition: p95_latency > 1000ms
    duration: 5m
    notify: slack

  - name: low_availability
    condition: availability < 99%
    duration: 10m
    notify: pagerduty
```

---

## Rollback Procedures

### Backend Rollback

```bash
# List deployments
fly releases

# Rollback to previous version
fly deploy --image registry.fly.io/pilot-space-api:v123
```

### Frontend Rollback

```bash
# Via Vercel Dashboard
# Deployments > Select previous > Promote to Production

# Or via CLI
vercel rollback
```

### Database Rollback

```bash
# Point-in-time recovery via Supabase Dashboard
# Database > Backups > Restore to specific time
```

---

## Security Checklist

- [ ] All secrets stored in secret managers (not env files)
- [ ] RLS enabled on all tables
- [ ] HTTPS enforced everywhere
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] API key encryption enabled (Supabase Vault)
- [ ] Webhook secrets configured
- [ ] GitHub App private key secured
- [ ] Audit logging enabled

---

## References

- [monitoring-observability.md](./monitoring-observability.md) - Monitoring setup
- [incident-response.md](./incident-response.md) - Incident runbooks
- [backup-recovery.md](./backup-recovery.md) - Backup procedures
- [Supabase Docs](https://supabase.com/docs) - Platform documentation
