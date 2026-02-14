# GitHub Integration - Pilot Space

**Parent**: [integrations/CLAUDE.md](../CLAUDE.md)

---

## Overview

OAuth connectivity, webhook handling, and commit/PR linking to issues. Supports full lifecycle: connect GitHub -> setup webhooks -> auto-link commits/PRs to issues -> AI-powered PR reviews.

---

## GitHubClient

**File**: `client.py`

Async HTTP client for GitHub REST API v3 with OAuth and rate limiting.

### OAuth Flow

1. `get_authorize_url(client_id, redirect_uri, state)` -- Generate URL with CSRF state (`{workspace_id}:{token}`)
2. Exchange code for token via `ConnectGitHubService` -> Fetch user -> Encrypt token (Supabase Vault) -> Store integration

### API Methods (14)

| Category | Methods | Returns |
|----------|---------|---------|
| User | `get_current_user()` | GitHubUser |
| Repositories | `get_repos()`, `get_repo(owner, repo)` | list[GitHubRepository] |
| Commits | `get_commits(owner, repo, since)`, `get_commit(owner, repo, sha)` | list[GitHubCommit] |
| Pull Requests | `get_pull_requests(owner, repo)`, `get_pull_request(owner, repo, number)` | list[GitHubPullRequest] |
| Comments | `post_comment()`, `post_review_comment()`, `get_pull_request_files()` | dict |
| Webhooks | `create_webhook()`, `delete_webhook()` | dict or None |
| Rate Limit | `get_rate_limit()` | RateLimitInfo |

### Error Hierarchy

`GitHubAPIError` -> `GitHubAuthError` (OAuth/token), `GitHubRateLimitError` (includes reset_at). See `exceptions.py`.

---

## GitHubWebhookHandler

**File**: `webhooks.py`

### Signature Verification

HMAC-SHA256 via `X-Hub-Signature-256` header. **Must verify BEFORE parsing payload.**

Interface: `verify_signature(payload_bytes, signature_header)` -- raises `WebhookVerificationError` on failure.

### Event Types

| Event | Actions |
|-------|---------|
| `push` | Branch push (commits) |
| `pull_request` | opened, closed, reopened, merged (virtual), synchronize |
| `pull_request_review` | Code review submitted |
| `issue_comment` | Comment on issue/PR |

### Idempotency

Deduplication via `X-GitHub-Delivery` header. In-memory bounded cache (max 10,000, LRU). Interface: `is_duplicate(delivery_id)`, `mark_processed(delivery_id)`.

---

## GitHubSyncService

**File**: `sync.py`

### Issue Reference Pattern

Pattern: `([A-Z]{2,10})-(\d+)`. Case-insensitive. Closing prefixes: fix, fixes, fixed, close, closes, closed, resolve, resolves.

Examples: "Fix PROJ-123" -> closing reference. "PILOT-42 desc" -> non-closing reference.

### Service Methods

| Method | Purpose |
|--------|---------|
| `sync_commit(workspace_id, integration_id, commit, repository)` | Link commit to matched issues |
| `sync_pull_request(workspace_id, integration_id, pr, repository)` | Link PR to matched issues |
| `sync_push_event(...)` | Batch all commits in push |
| `sync_pr_event(...)` | Process PR event from webhook |

### IntegrationLink Storage

Fields: workspace_id (RLS), integration_id, issue_id, link_type (COMMIT/PULL_REQUEST), external_id, external_url, title, author_name, author_avatar_url, link_metadata (JSONB: sha, message, repository, is_closing, additions, deletions, files_changed).

---

## Integration Services

**Location**: `application/services/integration/`

| Service | Purpose | Result |
|---------|---------|--------|
| ConnectGitHubService | OAuth code exchange, token encryption, store integration | integration.id, github_login |
| LinkCommitService | Manual commit/PR linking, duplicate check, activity recording | link.id, created (bool) |
| ProcessGitHubWebhookService | Process push/PR events, extract refs, create links | processed, links_created |
| AutoTransitionService | PR opened -> In Review, merged -> Done, commit -> In Progress | state transition |

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/integrations/github/authorize?workspace_id=X` | OAuth URL with CSRF state |
| POST | `/integrations/github/callback` | Exchange code, create integration |
| GET | `/integrations?workspace_id=X` | List integrations |
| GET/DELETE | `/integrations/{id}` | Get/disconnect integration |
| GET | `/integrations/github/{id}/repos` | List repositories |
| POST | `/integrations/github/{id}/repos/{owner}/{repo}/webhook` | Setup webhook |
| GET | `/integrations/issues/{id}/links` | Get issue links |
| POST | `/integrations/issues/{id}/links/commit` | Manual link commit |
| POST | `/integrations/issues/{id}/links/pull-request` | Manual link PR |
| POST | `/webhooks/github` | Receive webhook |

---

## Security

| Consideration | Pattern |
|---|---|
| Webhook Signatures | HMAC-SHA256 verify BEFORE parsing. See `webhooks.py:verify_signature` |
| Token Encryption | Supabase Vault (AES-256-GCM). See `infrastructure/encryption.py` |
| RLS in Links | Always filter by workspace_id |
| OAuth CSRF | State: `{workspace_id}:{random_token}` |

---

## Key Files

| File | Purpose |
|------|---------|
| `client.py` | GitHubClient (OAuth, 14 API methods) |
| `webhooks.py` | Signature verification, event parsing |
| `sync.py` | Issue reference extraction, link creation |
| `models.py` | Data classes (GitHubUser, GitHubRepository, etc.) |
| `exceptions.py` | Exception hierarchy |

---

## Related Documentation

- **Parent**: [integrations/CLAUDE.md](../CLAUDE.md)
- **Auth & Encryption**: [infrastructure/auth/CLAUDE.md](../../infrastructure/auth/CLAUDE.md)
- **AI PR Review**: [ai/agents/CLAUDE.md](../../ai/agents/CLAUDE.md) (PRReviewSubagent)
- **Webhook router**: `api/v1/routers/webhooks.py`
