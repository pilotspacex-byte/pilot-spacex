# Pilot Space - Self-Hosted Supabase

Production-ready self-hosted Supabase stack for Pilot Space, providing unified authentication, storage, realtime, and database services.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Security Hardening](#security-hardening)
- [Operations](#operations)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

## Overview

This setup replaces multiple services with a unified Supabase stack:

| Previous Service | Supabase Equivalent | Status |
|-----------------|---------------------|--------|
| PostgreSQL + pgvector | Supabase Database | ✅ Replaced |
| Keycloak | GoTrue (Auth) | ✅ Replaced |
| S3/MinIO | Storage API | ✅ Replaced |
| RabbitMQ + Celery | pgmq + pg_cron | ✅ Replaced |
| Custom WebSocket | Realtime | ✅ Replaced |
| Redis | Redis (kept) | ✅ Kept for AI caching |
| Meilisearch | Meilisearch (kept) | ✅ Kept for full-text search |

### Services Included

| Service | Port | Purpose |
|---------|------|---------|
| Kong | 8000/8443 | API Gateway |
| PostgreSQL | 5432 | Database with pgvector |
| GoTrue | 9999 | Authentication |
| PostgREST | 3000 | Auto-generated REST API |
| Realtime | 4000 | WebSocket subscriptions |
| Storage | 5000 | S3-compatible storage |
| Supavisor | 6543 | Connection pooler |
| Studio | 54323 | Admin dashboard (optional) |
| Redis | 6379 | AI response caching |
| Meilisearch | 7700 | Full-text search |

## Architecture

```
                              ┌─────────────────────────────────────────┐
                              │            CLIENT REQUESTS              │
                              └──────────────────┬──────────────────────┘
                                                 │
                                                 ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              KONG API GATEWAY (:8000)                          │
│  Routes: /auth/v1  /rest/v1  /realtime/v1  /storage/v1  /functions/v1          │
└───────────────────────────────────────────────────────────────────────────────┘
                    │             │             │             │
         ┌──────────┴───┐  ┌──────┴──────┐  ┌───┴───┐  ┌──────┴──────┐
         ▼              ▼  ▼             ▼  ▼       ▼  ▼             ▼
    ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌───────────┐
    │ GoTrue  │   │PostgREST │   │ Realtime │   │ Storage │   │ Functions │
    │  Auth   │   │  REST    │   │WebSocket │   │   S3    │   │   Deno    │
    └────┬────┘   └────┬─────┘   └────┬─────┘   └────┬────┘   └─────┬─────┘
         │             │              │              │               │
         └─────────────┴──────────────┴──────────────┴───────────────┘
                                      │
                                      ▼
         ┌───────────────────────────────────────────────────────────────┐
         │                     PostgreSQL 16 + pgvector                   │
         │         Supavisor (Connection Pooler) + RLS Policies           │
         └───────────────────────────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┴────────────────────────────┐
         ▼                                                         ▼
    ┌─────────┐                                              ┌──────────────┐
    │  Redis  │                                              │ Meilisearch  │
    │ Caching │                                              │ Full-Text    │
    └─────────┘                                              └──────────────┘
```

## Prerequisites

- Docker 24.0+ with Compose V2
- 8GB RAM minimum (16GB recommended for production)
- 20GB disk space minimum
- OpenSSL for generating secrets

## Quick Start

### 1. Clone and Setup

```bash
cd infra/supabase
cp .env.example .env
```

### 2. Generate Secure Secrets

**Option A: Automated Script**

```bash
./scripts/generate-secrets.sh
```

**Option B: Manual Generation**

```bash
# JWT Secret (min 32 characters)
openssl rand -base64 32

# Anon Key (generate at https://supabase.com/docs/guides/self-hosting#api-keys)
# Or use: npx @supabase/cli secrets generate

# Service Role Key
openssl rand -base64 32

# Realtime Secret
openssl rand -base64 48

# Supavisor Secret
openssl rand -base64 48
```

### 3. Configure Environment

Edit `.env` with your values:

```bash
# Required secrets
JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long
POSTGRES_PASSWORD=your-super-secret-password
ANON_KEY=your-anon-key
SERVICE_ROLE_KEY=your-service-role-key

# Site URLs (change for production)
SITE_URL=http://localhost:3000
API_EXTERNAL_URL=http://localhost:8000

# SMTP for email auth (optional for development)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=your-sendgrid-api-key
```

### 4. Start Services

```bash
# Development (without Studio)
docker compose up -d

# With Studio Dashboard
docker compose --profile studio up -d

# With Analytics (Logflare)
docker compose --profile studio --profile analytics up -d
```

### 5. Verify Health

```bash
# Check all services
docker compose ps

# Test Kong gateway
curl http://localhost:8000/rest/v1/ \
  -H "apikey: ${ANON_KEY}" \
  -H "Authorization: Bearer ${ANON_KEY}"

# Test Auth
curl http://localhost:8000/auth/v1/health
```

### 6. Access Services

| Service | URL | Notes |
|---------|-----|-------|
| API Gateway | http://localhost:8000 | All Supabase APIs |
| Studio | http://localhost:54323 | Admin dashboard |
| Meilisearch | http://localhost:7700 | Search dashboard |

## Configuration

### JWT Keys Generation

Supabase uses JWTs for authentication. Generate keys properly:

```bash
# Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)

# Generate anon key
ANON_KEY=$(echo -n '{"role":"anon","iss":"supabase","iat":'$(date +%s)',"exp":'$(($(date +%s) + 315360000))'}' | base64 | tr -d '\n')
# Then sign with JWT_SECRET

# For production, use Supabase CLI:
npx @supabase/cli secrets generate
```

### SMTP Configuration

For production email functionality:

**SendGrid:**
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=SG.your-api-key
```

**AWS SES:**
```env
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-access-key-id
SMTP_PASS=your-ses-secret-access-key
```

**Development (Mailtrap):**
```env
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=your-mailtrap-user
SMTP_PASS=your-mailtrap-pass
```

### OAuth Providers

Enable social logins:

```env
# GitHub
ENABLE_GITHUB_AUTH=true
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Google
ENABLE_GOOGLE_AUTH=true
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Resource Limits

Adjust in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 2G      # Increase for production
      cpus: '2.0'
    reservations:
      memory: 512M
```

## Security Hardening

### Production Checklist

- [ ] **Secrets**: All secrets are unique, random, and stored securely
- [ ] **TLS**: Enable HTTPS via reverse proxy (nginx, Traefik, Caddy)
- [ ] **Firewall**: Only expose Kong port (8000/8443) publicly
- [ ] **RLS**: All tables have RLS policies enabled
- [ ] **CORS**: Configure specific origins, not `*`
- [ ] **Rate Limiting**: Enable Kong rate limiting plugin
- [ ] **Monitoring**: Set up Prometheus/Grafana or similar
- [ ] **Backups**: Configure automated database backups
- [ ] **Updates**: Regular security updates for all images

### TLS with Traefik

```yaml
# Add to docker-compose.yml
traefik:
  image: traefik:v2.10
  command:
    - --providers.docker=true
    - --entrypoints.websecure.address=:443
    - --certificatesresolvers.letsencrypt.acme.email=admin@your-domain.com
    - --certificatesresolvers.letsencrypt.acme.tlschallenge=true
  ports:
    - "443:443"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - ./letsencrypt:/letsencrypt

kong:
  labels:
    - traefik.enable=true
    - traefik.http.routers.kong.rule=Host(`api.your-domain.com`)
    - traefik.http.routers.kong.tls.certresolver=letsencrypt
```

### Rate Limiting

Add to Kong configuration:

```yaml
plugins:
  - name: rate-limiting
    config:
      second: 10
      minute: 100
      policy: local
      fault_tolerant: true
```

### Firewall Rules

```bash
# Allow only essential ports
ufw allow 22/tcp     # SSH
ufw allow 443/tcp    # HTTPS
ufw allow 80/tcp     # HTTP (redirect to HTTPS)
ufw deny 5432/tcp    # Block direct PostgreSQL
ufw deny 6379/tcp    # Block direct Redis
ufw enable
```

## Operations

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f kong
docker compose logs -f auth
docker compose logs -f db

# Last 100 lines
docker compose logs --tail 100 db
```

### Database Migrations

Run Alembic migrations against the Supabase database:

```bash
# From backend directory
cd ../../backend

# Set database URL
export DATABASE_URL=postgresql+asyncpg://supabase_admin:${POSTGRES_PASSWORD}@localhost:5432/postgres

# Run migrations
uv run alembic upgrade head
```

### Backups

**Manual Backup:**
```bash
# Backup database
docker exec pilot-space-db pg_dump -U supabase_admin postgres > backup_$(date +%Y%m%d).sql

# Backup with compression
docker exec pilot-space-db pg_dump -U supabase_admin postgres | gzip > backup_$(date +%Y%m%d).sql.gz
```

**Automated Backup (cron):**
```bash
# Add to crontab: crontab -e
0 2 * * * /path/to/infra/supabase/scripts/backup.sh
```

**Restore:**
```bash
# Restore from backup
cat backup_20240101.sql | docker exec -i pilot-space-db psql -U supabase_admin postgres
```

### Scaling

**Horizontal Scaling (Kubernetes):**
- Use the official Supabase Helm chart
- Configure separate replicas for each service
- Use external PostgreSQL (RDS, Cloud SQL)

**Vertical Scaling (Docker Compose):**
```yaml
# Increase resources
db:
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: '4.0'
```

### Health Checks

```bash
# Check all services
docker compose ps

# Detailed health
docker inspect pilot-space-db --format='{{.State.Health.Status}}'
docker inspect pilot-space-kong --format='{{.State.Health.Status}}'

# API health endpoints
curl http://localhost:8000/auth/v1/health
curl http://localhost:8000/rest/v1/
curl http://localhost:7700/health
```

## Troubleshooting

### Common Issues

**Kong fails to start:**
```bash
# Check Kong configuration
docker compose logs kong

# Validate kong.yml
docker exec pilot-space-kong kong config parse /var/lib/kong/kong.yml
```

**Database connection refused:**
```bash
# Check if DB is healthy
docker compose ps db
docker compose logs db

# Test connection
docker exec -it pilot-space-db psql -U supabase_admin -d postgres -c "SELECT 1"
```

**Auth service errors:**
```bash
# Check GoTrue logs
docker compose logs auth

# Verify database connection
docker exec pilot-space-auth wget -qO- http://localhost:9999/health
```

**Realtime not working:**
```bash
# Check realtime logs
docker compose logs realtime

# Verify replication slot
docker exec -it pilot-space-db psql -U supabase_admin -d postgres -c "SELECT * FROM pg_replication_slots"
```

**Storage uploads failing:**
```bash
# Check storage logs
docker compose logs storage

# Verify storage directory permissions
ls -la volumes/storage
```

### Reset Everything

```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: deletes all data)
docker compose down -v

# Clean up
docker system prune -a

# Start fresh
docker compose up -d
```

## Rollback Procedures

### Service Rollback

```bash
# Rollback to previous image
docker compose down
# Edit docker-compose.yml to use previous image version
docker compose up -d
```

### Database Rollback

```bash
# Restore from backup
docker compose stop db
docker volume rm pilot-space-postgres-data
docker compose up -d db

# Wait for healthy
sleep 30

# Restore data
cat backup.sql | docker exec -i pilot-space-db psql -U supabase_admin postgres
```

### Full Stack Rollback

If self-hosted Supabase fails, revert to previous setup:

1. Stop Supabase stack: `docker compose down`
2. Restore old docker-compose.yml from git
3. Restore database backup to standalone PostgreSQL
4. Start old stack: `docker compose up -d`
5. Update backend/frontend environment variables

### Emergency Contacts

- Supabase GitHub Issues: https://github.com/supabase/supabase/issues
- Supabase Discord: https://discord.supabase.com/
- Pilot Space maintainers: See CODEOWNERS

## Related Documentation

- [Supabase Self-Hosting Guide](https://supabase.com/docs/guides/self-hosting)
- [Pilot Space Architecture](../../docs/architect/infrastructure.md)
- [Supabase Integration](../../docs/architect/supabase-integration.md)
- [RLS Patterns](../../docs/architect/rls-patterns.md)
