# Incident Response Runbooks

**Version**: 1.0 | **Date**: 2026-01-23 | **Branch**: `001-pilot-space-mvp`

---

## Overview

This document provides runbooks for responding to common incidents in Pilot Space production environment.

### Severity Levels

| Level | Definition | Response Time | Examples |
|-------|------------|---------------|----------|
| **SEV1** | Complete outage | 15 min | API down, auth broken |
| **SEV2** | Major degradation | 30 min | AI features unavailable |
| **SEV3** | Minor impact | 2 hours | Search slow, single feature broken |
| **SEV4** | Minimal impact | 24 hours | UI glitch, minor bug |

---

## Incident Response Process

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Detect  │───▶│  Triage  │───▶│ Mitigate │───▶│  Resolve │───▶│  Review  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
  Alerts        Assess          Contain         Fix root        Post-mortem
  Reports       severity        impact          cause           Improvements
```

---

## Runbook: API Unavailable (SEV1)

### Symptoms
- HTTP 5xx errors from all endpoints
- Health check failures
- Users cannot access the application

### Diagnosis

```bash
# 1. Check Fly.io status
fly status

# 2. View recent logs
fly logs --app pilot-space-api

# 3. Check machine health
fly machine list

# 4. Test health endpoint
curl https://api.pilotspace.io/health
```

### Mitigation

```bash
# Option 1: Restart machines
fly machine restart

# Option 2: Scale up if resource exhaustion
fly scale count 4

# Option 3: Rollback to previous deployment
fly releases
fly deploy --image registry.fly.io/pilot-space-api:v{previous}

# Option 4: Check and restart specific machine
fly machine list
fly machine restart {machine_id}
```

### Resolution Checklist
- [ ] API responding normally
- [ ] Health checks passing
- [ ] Error rates returned to baseline
- [ ] Users can log in and use features

---

## Runbook: Database Connection Issues (SEV1)

### Symptoms
- "Connection refused" errors in logs
- Timeouts on database queries
- Pooler connection limits reached

### Diagnosis

```bash
# 1. Check Supabase status
# https://status.supabase.com/

# 2. Check connection count (via Supabase Dashboard)
# Database > Connection Pooler > Connections

# 3. Check slow queries (via Supabase Dashboard)
# Database > Query Performance
```

### Mitigation

```bash
# 1. If connection pool exhausted - restart backend
fly machine restart

# 2. If queries slow - identify and cancel
# Via Supabase SQL Editor:
SELECT pid, query, state, query_start
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;

-- Cancel specific query
SELECT pg_cancel_backend({pid});

# 3. Enable connection timeout (if not set)
# In application config:
DATABASE_POOL_SIZE=20
DATABASE_POOL_TIMEOUT=30
```

### Resolution Checklist
- [ ] Database connections stable
- [ ] Query performance normal
- [ ] No blocked queries
- [ ] Application responding

---

## Runbook: Authentication Failures (SEV1)

### Symptoms
- Users cannot log in
- 401 errors on all authenticated requests
- Token validation failing

### Diagnosis

```bash
# 1. Check Supabase Auth status
# Via Supabase Dashboard > Authentication

# 2. Test auth endpoint
curl https://{project}.supabase.co/auth/v1/health

# 3. Check JWT configuration
# Verify SUPABASE_JWT_SECRET is set correctly
fly secrets list | grep SUPABASE
```

### Mitigation

```bash
# 1. If JWT secret mismatch - update secret
fly secrets set SUPABASE_JWT_SECRET="{correct_secret}"

# 2. If Supabase Auth down - enable maintenance mode
# In frontend, show maintenance banner

# 3. Rotate compromised tokens (if security incident)
# Via Supabase Dashboard > Authentication > Users
# Revoke specific sessions
```

### Resolution Checklist
- [ ] Login flow working
- [ ] Existing sessions valid
- [ ] Token refresh working
- [ ] OAuth providers functioning

---

## Runbook: AI Features Unavailable (SEV2)

### Symptoms
- Ghost text not appearing
- PR review not completing
- "AI unavailable" errors

### Diagnosis

```bash
# 1. Check provider status pages
# https://status.anthropic.com/
# https://status.openai.com/

# 2. Check AI endpoint logs
fly logs --app pilot-space-api | grep "ai"

# 3. Test provider connectivity
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  https://api.anthropic.com/v1/messages \
  -d '{"model":"claude-sonnet-4","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'
```

### Mitigation

```bash
# 1. If provider rate limited - enable caching
fly secrets set AI_CACHE_ENABLED=true

# 2. If single provider down - switch to fallback
# Application should auto-fallback, verify in logs

# 3. If all providers down - graceful degradation
# AI features should show "temporarily unavailable"

# 4. If API key issues - rotate keys
fly secrets set ANTHROPIC_API_KEY="{new_key}"
```

### Resolution Checklist
- [ ] Ghost text working
- [ ] PR review processing
- [ ] Provider health restored
- [ ] Error rates normal

---

## Runbook: High Latency (SEV2)

### Symptoms
- API response times > 1s
- Frontend feels slow
- Users reporting delays

### Diagnosis

```bash
# 1. Check backend metrics
fly metrics --app pilot-space-api

# 2. Check database performance
# Via Supabase Dashboard > Database > Query Performance

# 3. Check Redis performance
# Via Upstash Console > Metrics

# 4. Check for N+1 queries in logs
fly logs --app pilot-space-api | grep "SELECT"
```

### Mitigation

```bash
# 1. If database slow - analyze slow queries
# Via Supabase SQL Editor:
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# 2. If missing indexes - add urgently
CREATE INDEX CONCURRENTLY idx_issues_project_state
ON issues(project_id, state_id);

# 3. If Redis slow - flush cache
redis-cli FLUSHDB

# 4. If backend overloaded - scale up
fly scale count 4 --max-per-region 6
fly scale memory 2048
```

### Resolution Checklist
- [ ] p95 latency < 500ms
- [ ] Database query times normal
- [ ] Cache hit rate > 80%
- [ ] No resource exhaustion

---

## Runbook: Search Not Working (SEV3)

### Symptoms
- Search returns no results
- Search is very slow
- Search index out of date

### Diagnosis

```bash
# 1. Check Meilisearch health
curl https://{host}.meilisearch.io/health

# 2. Check index status
curl https://{host}.meilisearch.io/indexes/issues/stats \
  -H "Authorization: Bearer $MEILISEARCH_KEY"

# 3. Check indexing tasks
curl https://{host}.meilisearch.io/tasks \
  -H "Authorization: Bearer $MEILISEARCH_KEY"
```

### Mitigation

```bash
# 1. If index corrupted - rebuild
curl -X DELETE https://{host}.meilisearch.io/indexes/issues \
  -H "Authorization: Bearer $MEILISEARCH_KEY"

# Then trigger reindex from backend
curl -X POST https://api.pilotspace.io/admin/reindex \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. If Meilisearch down - fallback to DB search
# Application should auto-fallback

# 3. If indexing stuck - cancel and retry
curl -X DELETE https://{host}.meilisearch.io/tasks?statuses=enqueued,processing \
  -H "Authorization: Bearer $MEILISEARCH_KEY"
```

### Resolution Checklist
- [ ] Search returning results
- [ ] Latency < 2s
- [ ] Index up to date
- [ ] No failed tasks

---

## Runbook: Webhook Failures (SEV3)

### Symptoms
- GitHub PRs not triggering reviews
- Slack notifications not sending
- Webhook events in dead letter queue

### Diagnosis

```bash
# 1. Check webhook logs
fly logs --app pilot-space-api | grep "webhook"

# 2. Check dead letter queue
# Via Supabase SQL Editor:
SELECT * FROM pgmq.read_dead_letter('webhooks', 100);

# 3. Verify webhook endpoints responding
curl -X POST https://api.pilotspace.io/api/v1/webhooks/github \
  -H "X-Hub-Signature-256: test" \
  -d '{"action":"ping"}'
```

### Mitigation

```bash
# 1. If signature verification failing - check secrets
fly secrets list | grep WEBHOOK
fly secrets set GITHUB_WEBHOOK_SECRET="{correct_secret}"

# 2. If events stuck - replay from dead letter
# Via Supabase SQL Editor:
SELECT pgmq.archive_dead_letter('webhooks');

# 3. If GitHub/Slack down - events will retry automatically
# Check retry policy in queue configuration
```

### Resolution Checklist
- [ ] Webhook endpoint responding
- [ ] Signature verification passing
- [ ] Events processing normally
- [ ] Dead letter queue empty

---

## Runbook: Data Inconsistency (SEV2)

### Symptoms
- Users see stale data
- Counts don't match
- Missing expected records

### Diagnosis

```bash
# 1. Check for orphaned records
# Via Supabase SQL Editor:
SELECT i.id FROM issues i
LEFT JOIN projects p ON i.project_id = p.id
WHERE p.id IS NULL;

# 2. Check for soft delete inconsistencies
SELECT * FROM issues
WHERE is_deleted = true AND deleted_at IS NULL;

# 3. Check RLS bypassed writes
# Review audit logs for unexpected patterns
```

### Mitigation

```bash
# 1. Fix orphaned records
UPDATE issues SET is_deleted = true
WHERE project_id NOT IN (SELECT id FROM projects);

# 2. Refresh materialized views if used
REFRESH MATERIALIZED VIEW CONCURRENTLY issue_counts;

# 3. Clear cache to force fresh reads
redis-cli FLUSHDB
```

### Resolution Checklist
- [ ] Data integrity verified
- [ ] No orphaned records
- [ ] Counts accurate
- [ ] Cache cleared

---

## Escalation Contacts

| Role | Contact | When |
|------|---------|------|
| On-call Engineer | PagerDuty rotation | All SEV1-2 |
| Engineering Lead | Direct contact | SEV1, security |
| Database Admin | Supabase support | DB issues |
| Security Team | Security channel | Security incidents |

---

## Post-Incident Review

After every SEV1-2 incident:

1. **Timeline**: Document what happened and when
2. **Impact**: Quantify user impact
3. **Root Cause**: Identify underlying cause
4. **Mitigation**: What stopped the bleeding
5. **Resolution**: What fixed it permanently
6. **Action Items**: Prevent recurrence

Template: [incident-template.md](./templates/incident-template.md)

---

## References

- [deployment-guide.md](./deployment-guide.md) - Deployment procedures
- [monitoring-observability.md](./monitoring-observability.md) - Monitoring setup
- [backup-recovery.md](./backup-recovery.md) - Recovery procedures
