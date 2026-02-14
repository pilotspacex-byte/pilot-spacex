# Integrations Module - Pilot Space

**Parent**: `/backend/CLAUDE.md`

---

## Overview

External service connectivity for Pilot Space: GitHub integration (OAuth, webhooks, commit/PR linking). Built around a provider-based architecture with OAuth flows, webhook validation, and async event processing.

**Status**: GitHub fully implemented. Slack deferred to Phase 2.

---

## Submodule Documentation

- **[github/CLAUDE.md](github/CLAUDE.md)** -- GitHubClient (14 async API methods), GitHubWebhookHandler (HMAC-SHA256), GitHubSyncService (commit/PR linking), Service Layer (4 services), API Endpoints (11 total)

---

## Module Structure

```
integrations/
├── github/
│   ├── client.py          # GitHubClient (OAuth, API operations)
│   ├── webhooks.py        # GitHubWebhookHandler (signature verification)
│   ├── models.py          # Data classes (GitHubUser, GitHubRepository, etc.)
│   ├── exceptions.py      # GitHub-specific exceptions
│   ├── sync.py            # GitHubSyncService (commit/PR linking)
│   └── CLAUDE.md          # Deep-dive documentation
└── slack/                 # Placeholder (Phase 2)
```

## Integration Flow

```
User (Connect GitHub) -> OAuth URL -> GitHub
  | (User approves)
OAuth Callback -> Code Exchange -> ConnectGitHubService
  +-- Exchange code for access token
  +-- Fetch user info
  +-- Encrypt and store token (Supabase Vault)
  +-- Return integration record

Webhook Events -> /api/v1/webhooks/github
  +-- Verify HMAC-SHA256 signature
  +-- Parse event (GitHubWebhookHandler)
  +-- ProcessGitHubWebhookService
     +-- GitHubSyncService (link commits/PRs to issues)
```

---

## Security

| Consideration | Pattern |
|---|---|
| Webhook Signatures | HMAC-SHA256 verify BEFORE parsing body |
| Token Encryption | Supabase Vault (AES-256-GCM), decrypt on use |
| RLS in Links | Always filter IntegrationLink by workspace_id |
| OAuth CSRF | State parameter: `{workspace_id}:{token}` |

---

## Common Errors

| Error | Solution |
|-------|----------|
| Webhook signature failed | Verify signature BEFORE reading body |
| Integration not found | Check integration.workspace_id matches request |
| Rate limit exceeded | Catch GitHubRateLimitError, retry after reset_at |
| Duplicate delivery | Use `is_duplicate()` + `mark_processed()` |

---

## Related Documentation

- **GitHub deep-dive**: [github/CLAUDE.md](github/CLAUDE.md)
- **Application services**: [../application/CLAUDE.md](../application/CLAUDE.md)
- **API routers**: `api/v1/routers/integrations.py`, `api/v1/routers/webhooks.py`
