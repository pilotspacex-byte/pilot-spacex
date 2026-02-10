# Integrations Module Documentation - Pilot Space

**For backend architecture context, see `/backend/CLAUDE.md`**

---

## Overview

The integrations module provides external service connectivity for Pilot Space, enabling seamless GitHub integration for PR reviews, webhook handling, and commit/PR linking to issues. The module is built around a provider-based architecture supporting OAuth flows, webhook validation, and async event processing.

**Current Integration Status**:
- **GitHub**: Fully implemented (OAuth, webhooks, commit/PR linking, API client)
- **Slack**: Placeholder (structure ready, implementation deferred to Phase 2)

---

## Quick Reference

### Module Structure

```
backend/src/pilot_space/integrations/
├─ __init__.py                              # Module exports
├─ github/                                  # GitHub integration
│  ├─ client.py                            # GitHubClient (OAuth, API operations)
│  ├─ webhooks.py                          # GitHubWebhookHandler (signature verification, parsing)
│  ├─ models.py                            # Data classes (GitHubUser, GitHubRepository, etc.)
│  ├─ exceptions.py                        # GitHub-specific exceptions
│  ├─ sync.py                              # GitHubSyncService (commit/PR linking)
│  └─ __init__.py                          # Exports
└─ slack/                                   # Slack integration (placeholder)
   └─ __init__.py
```

### Integration Flow Overview

```
User Action (Connect GitHub)
  ↓
OAuth Authorization URL → GitHub
  ↓ (User approves)
OAuth Callback → Code Exchange
  ↓
ConnectGitHubService.execute()
  ├─ Exchange code for access token (GitHubClient)
  ├─ Fetch user info (GitHubClient)
  ├─ Encrypt and store token (Integration model)
  └─ Return integration record
  ↓
Issue Linking (Webhook or Manual)
  ├─ GitHub Webhook → /api/v1/webhooks/github
  │  └─ Verify signature (HMAC-SHA256)
  │  └─ Parse event (GitHubWebhookHandler)
  │  └─ ProcessGitHubWebhookService.execute()
  │     └─ GitHubSyncService (link commits/PRs to issues)
  │
  └─ Manual Link (User-initiated)
     └─ LinkCommitService.link_commit() / link_pull_request()
     └─ Fetch from GitHub (GitHubClient)
     └─ Create IntegrationLink record
```

---

## GitHub Integration

### 1. GitHubClient - API Operations

**Location**: `/backend/src/pilot_space/integrations/github/client.py`

**Purpose**: Async HTTP client for GitHub REST API v3 with OAuth support and rate limiting.

**Key Features**:
- OAuth code exchange (retrieve access tokens)
- Authenticated API requests with automatic header injection
- Rate limit monitoring and error handling
- Pagination support for list operations
- Webhook management (create, delete)

#### OAuth Flow

```python
# Step 1: Generate authorization URL (CSRF-protected with state)
authorize_url = GitHubClient.get_authorize_url(
    client_id="your-client-id",
    redirect_uri="https://app.example.com/auth/github/callback",
    state="workspace-uuid:random-token",
)

# Step 2: Exchange code for token, fetch user, store encrypted token
service = ConnectGitHubService(session, integration_repo)
result = await service.execute(
    ConnectGitHubPayload(
        workspace_id=workspace_id,
        code="code-from-callback",
        user_id=current_user_id,
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        redirect_uri=settings.github_callback_url,
    )
)
```

#### API Methods (14 async methods)

**User**: `get_current_user()` → GitHubUser
**Repositories**: `get_repos()`, `get_repo(owner, repo)` → list[GitHubRepository]
**Commits**: `get_commits(owner, repo, since)`, `get_commit(owner, repo, sha)` → list[GitHubCommit]
**Pull Requests**: `get_pull_requests(owner, repo)`, `get_pull_request(owner, repo, number)` → list[GitHubPullRequest]
**Comments**: `post_comment()`, `post_review_comment()`, `get_pull_request_files()` → dict
**Webhooks**: `create_webhook()`, `delete_webhook()` → dict | None
**Rate Limit**: `get_rate_limit()` → RateLimitInfo

#### Error Handling

**Exception Hierarchy**:
```python
GitHubAPIError              # Base exception
├─ GitHubAuthError         # OAuth or token issues
└─ GitHubRateLimitError    # Rate limit exceeded (includes reset_at)

# Usage
try:
    repos = await client.get_repos()
except GitHubRateLimitError as e:
    print(f"Rate limited. Resets at {e.reset_at}")
    # Backoff and retry
except GitHubAuthError as e:
    print(f"Auth failed: {e}")
    # Re-authenticate
except GitHubAPIError as e:
    print(f"API error ({e.status_code}): {e}")
    # Handle error
```

---

### 2. GitHubWebhookHandler - Webhook Processing

**Location**: `/backend/src/pilot_space/integrations/github/webhooks.py`

**Purpose**: Parse and validate GitHub webhook events with HMAC-SHA256 signature verification.

**Key Features**:
- HMAC-SHA256 signature verification
- Event type parsing and validation
- Payload parsing for push and PR events
- Idempotency tracking (delivery ID deduplication)
- Queue-based async processing support

#### Signature Verification

**How GitHub Webhooks Work**:
1. GitHub sends POST to webhook URL with `X-Hub-Signature-256` header
2. Signature is `sha256=<hex-digest>` of request body
3. We verify by recomputing HMAC with shared secret

```python
from pilot_space.integrations.github import GitHubWebhookHandler

handler = GitHubWebhookHandler(webhook_secret="your-secret-key")

# Verify signature
try:
    handler.verify_signature(
        payload=request_body_bytes,
        signature="sha256=abc123...",  # From X-Hub-Signature-256 header
    )
except WebhookVerificationError:
    # Signature invalid - reject webhook
    return 401 Unauthorized
```

**Router Integration** (see `/backend/src/pilot_space/api/v1/routers/webhooks.py`):
```python
@router.post("/webhooks/github")
async def receive_github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
) -> WebhookProcessResult:
    """Receive and process GitHub webhook events."""
    settings = get_settings()
    body = await request.body()  # Raw bytes for signature verification

    handler = GitHubWebhookHandler(
        webhook_secret=settings.github_webhook_secret.get_secret_value()
    )

    # Verify signature FIRST
    try:
        handler.verify_signature(body, x_hub_signature_256)
    except WebhookVerificationError as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    payload = await request.json()
    webhook = handler.parse_event(x_github_event, x_github_delivery, payload)

    # Check for duplicate
    if handler.is_duplicate(x_github_delivery):
        return WebhookProcessResult(processed=False, error="Duplicate delivery")

    # Enqueue for processing
    msg_id = await handler.enqueue_for_processing(
        workspace_id=workspace_id,
        integration_id=integration_id,
        webhook=webhook,
    )

    handler.mark_processed(x_github_delivery)
    return WebhookProcessResult(processed=True, event_type=webhook.event_type.value)
```

#### Supported Event Types

```python
class GitHubEventType(str, Enum):
    PUSH = "push"                           # Branch push
    PULL_REQUEST = "pull_request"          # PR opened/closed/merged
    PULL_REQUEST_REVIEW = "pull_request_review"  # Code review
    ISSUE_COMMENT = "issue_comment"        # Comment on issue/PR

# Event-specific actions
class GitHubPRAction(str, Enum):
    OPENED = "opened"
    CLOSED = "closed"
    REOPENED = "reopened"
    MERGED = "merged"                       # Virtual action (closed + merged)
    SYNCHRONIZE = "synchronize"            # New commits pushed
```

#### Webhook Payload Parsing

- `parse_push_event(payload)` → ParsedPushEvent with branch, commits, repository
- `parse_pr_event(payload)` → ParsedPREvent with action, number, title, branches, author

#### Idempotency

Webhooks can be delivered multiple times. GitHub includes delivery ID in `X-GitHub-Delivery` header.

```python
# Check if already processed
if handler.is_duplicate(delivery_id):
    logger.info(f"Duplicate delivery {delivery_id}, skipping")
    return  # Already processed

# Process webhook
# ...

# Mark as processed
handler.mark_processed(delivery_id)
```

**Note**: Deduplication is in-memory with bounded size (max 10,000 entries, LRU eviction). For distributed systems, use database-level deduplication.

---

### 3. GitHubSyncService - Commit/PR Linking

**Location**: `/backend/src/pilot_space/integrations/github/sync.py`

**Purpose**: Link commits and PRs to issues via issue reference extraction from commit messages.

**Pattern Recognition**:
- Matches issue references: `PROJ-123`, `PILOT-42`, etc.
- Detects closing prefixes: "Fix PILOT-42", "Closes #100"
- Case-insensitive matching
- Deduplication of references

```python
# Issue reference pattern
ISSUE_REF_PATTERN = r"([A-Z]{2,10})-(\d+)"

# Closing prefixes
FIX_PREFIXES = ("fix", "fixes", "fixed", "close", "closes", "closed", "resolve", "resolves")

# Examples matched:
# "Fix PROJ-123" → IssueReference(identifier="PROJ-123", is_closing=True)
# "PILOT-42 description" → IssueReference(identifier="PILOT-42", is_closing=False)
# "Fixes ABC-456" → IssueReference(identifier="ABC-456", is_closing=True)
```

#### Service Methods

- `sync_commit(workspace_id, integration_id, commit, repository)` → Result with links_created/updated, issues_matched
- `sync_pull_request(workspace_id, integration_id, pr, repository)` → Result
- `sync_push_event(workspace_id, integration_id, push)` → Result (batch commits)
- `sync_pr_event(workspace_id, integration_id, pr)` → Result (from webhook)

#### IntegrationLink Storage

IntegrationLink records store: workspace_id, integration_id, issue_id, link_type (COMMIT/PULL_REQUEST), external_id (sha/number), external_url, title, author_name, author_avatar_url, link_metadata (sha, message, repository, timestamp, additions, deletions, files_changed, is_closing)

---

### 4. Integration Service Layer

**Location**: `/backend/src/pilot_space/application/services/integration/`

Application services follow CQRS-lite pattern, providing high-level integration operations.

#### ConnectGitHubService

Connects GitHub account via OAuth. Returns integration record with encrypted token.

**Flow**: Exchange code → Fetch user → Encrypt token → Store integration → Return result

**Result**: integration.id, github_login, github_name, github_avatar_url

**Errors**: GitHubConnectionError (OAuth/user fetch), other exceptions (500)

#### LinkCommitService

Manually links commits/PRs to issues. Validates integration, checks duplicates, records activity.

**Methods**: `link_commit(workspace_id, issue_id, integration_id, repository, commit_sha)`, `link_pull_request(workspace_id, issue_id, integration_id, repository, pr_number)`

**Result**: link.id, created (bool), commit_message, author_name

#### ProcessGitHubWebhookService

Processes webhook events (push, PR). Extracts commits/PRs, finds issue refs, creates links.

**Result**: processed (bool), event_type, links_created, issues_affected

**Handles**: Push events (commits), PR events (creation/merge), PR review (Phase 2)

---

## API Integration Points

### API Endpoints Summary

**Location**: `/backend/src/pilot_space/api/v1/routers/integrations.py` and `webhooks.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /integrations/github/authorize?workspace_id=X | Get OAuth URL with CSRF state |
| POST | /integrations/github/callback | Exchange code for token, create integration |
| GET | /integrations?workspace_id=X | List workspace integrations |
| GET | /integrations/{id} | Get integration details |
| DELETE | /integrations/{id} | Disconnect integration |
| GET | /integrations/github/{id}/repos | List repositories |
| POST | /integrations/github/{id}/repos/{owner}/{repo}/webhook | Setup webhook |
| GET | /integrations/issues/{id}/links | Get issue links (commits/PRs) |
| POST | /integrations/issues/{id}/links/commit | Manually link commit |
| POST | /integrations/issues/{id}/links/pull-request | Manually link PR |
| POST | /webhooks/github | Receive webhook (push, PR, review) |

---

## Webhook Setup in GitHub

### Step 1: Configure OAuth App

1. Go to GitHub Settings → Developer Settings → OAuth Apps
2. Create new OAuth Application
3. Set Authorization callback URL to: `https://app.example.com/auth/github/callback`
4. Note the Client ID and Client Secret

### Step 2: Set Environment Variables

```bash
# .env or deployment config
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
GITHUB_CALLBACK_URL=https://app.example.com/auth/github/callback
GITHUB_WEBHOOK_SECRET=random-secret-key-min-32-chars
```

### Step 3: User Connects GitHub

1. User clicks "Connect GitHub" button
2. Frontend gets OAuth URL: `GET /api/v1/integrations/github/authorize?workspace_id=<workspace>`
3. User redirected to GitHub login
4. User approves permissions
5. GitHub redirects to callback with code
6. Frontend sends: `POST /api/v1/integrations/github/callback` with code
7. Backend exchanges code for access token
8. Integration saved to database

### Step 4: Setup Webhook in Repository

1. User selects repository from list: `GET /api/v1/integrations/github/<integration_id>/repos`
2. User clicks "Setup Webhook"
3. Backend creates webhook: `POST /api/v1/integrations/github/<integration_id>/repos/<owner>/<repo>/webhook`
4. GitHub sends events to `https://app.example.com/api/v1/webhooks/github`

### Step 5: GitHub Sends Events

GitHub sends webhook events to the configured URL with signature verification.

Backend:
1. Receives POST to `/api/v1/webhooks/github`
2. Verifies `X-Hub-Signature-256` header
3. Parses event type from `X-GitHub-Event`
4. Enqueues for async processing (or processes synchronously)
5. Returns 200 OK immediately

---

## Security Considerations

**CRITICAL**: Webhook signature verification must happen BEFORE processing payload.

| Consideration | Pattern | Details |
|---|---|---|
| Webhook Signatures | HMAC-SHA256 verify first | `body = await request.body()` → `handler.verify_signature(body, x_hub_signature_256)` → parse |
| Token Encryption | Supabase Vault (AES-256-GCM) | encrypt_api_key() on storage, decrypt on use |
| RLS in Links | Always filter by workspace_id | IntegrationLink queries must include `workspace_id == workspace_id` AND condition |
| OAuth CSRF | State parameter tied to workspace | Generate: `state = f"{workspace_id}:{token}"`, validate after callback |

---

## Testing

**See `backend/CLAUDE.md` for testing patterns and best practices.**

All integrations require:
- Unit tests for signature verification, event parsing, issue reference extraction
- Integration tests for OAuth flow, webhook idempotency, RLS isolation
- Coverage >80% (run `pytest --cov=.`)

---

## Common Patterns

### OAuth Flow (See Step 1-3 Above)

1. Generate authorization URL with CSRF state token
2. User approves on GitHub
3. Exchange code for token via ConnectGitHubService
4. Token encrypted and stored (Supabase Vault)

---

## Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| Webhook signature verification failed | Wrong webhook secret, body modified, not from GitHub | Verify signature BEFORE reading body (`request.body()` then `verify_signature()`) |
| Integration not found | OAuth broken, deleted, workspace ID mismatch | Verify integration.workspace_id matches request context |
| Rate limit exceeded | Too many GitHub API calls | Catch GitHubRateLimitError, retry after reset_at, or queue job |
| Duplicate delivery | GitHub retry or double-processing | GitHubWebhookHandler.is_duplicate() + mark_processed() (in-memory; use DB for distributed) |

---

## Phase 2 & Future Work

### Planned Integrations
- **Slack**: Notifications, slash commands, approval workflows
- **Linear**: Issue sync
- **Jira**: Issue mapping
- **GitLab**: Alternative Git provider

### Planned Features
- PR review comments with AI analysis (Phase 2)
- Auto-transitions when PRs merged (DD-003 approval workflow)
- Bidirectional sync (Pilot Space → GitHub issues)
- Custom webhooks for user-defined integrations
- Rate limit pooling across workspaces

---

## Generation Metadata

**Documentation Generated**: 2026-02-10

**Files Analyzed**:
- `backend/src/pilot_space/integrations/github/client.py` (700 lines)
- `backend/src/pilot_space/integrations/github/webhooks.py` (333 lines)
- `backend/src/pilot_space/integrations/github/models.py` (89 lines)
- `backend/src/pilot_space/integrations/github/exceptions.py` (64 lines)
- `backend/src/pilot_space/integrations/github/sync.py` (477 lines)
- `backend/src/pilot_space/application/services/integration/` (4 services)
- `backend/src/pilot_space/api/v1/routers/integrations.py` (678 lines)
- `backend/src/pilot_space/api/v1/routers/webhooks.py` (147 lines)

**Scope**: GitHub OAuth, webhook validation, commit/PR linking, API integration patterns

**Key Components Documented**:
- GitHubClient (14 async methods, OAuth, rate limiting)
- GitHubWebhookHandler (signature verification, event parsing, deduplication)
- GitHubSyncService (issue reference extraction, link creation)
- 4 Application Services (ConnectGithub, LinkCommit, LinkPR, ProcessWebhook)
- 2 API Routers (integrations, webhooks)
- Complete OAuth flow with examples
- Webhook security and validation patterns
- Error handling and resilience strategies

**Patterns Detected**:
- OAuth 2.0 code exchange with CSRF state
- HMAC-SHA256 webhook signature verification
- Idempotent webhook processing (delivery ID deduplication)
- Issue reference extraction from commit messages
- Closing prefixes detection ("Fix", "Closes", etc.)
- Token encryption for secure storage (Supabase Vault)
- RLS enforcement on integration links
- Async/await patterns for external API calls
- Service layer abstraction with explicit payloads

**Coverage**:
- All GitHub API operations (OAuth, repos, commits, PRs, webhooks)
- Webhook event handling (push, PR, PR review)
- Manual and automatic link creation
- Error types and handling strategies
- Security considerations (signature verification, token encryption, RLS)
- Testing patterns (unit, integration, RLS isolation)
- Complete router API documentation
- Step-by-step OAuth setup guide

**Deferred / Not Yet Implemented**:
- Slack integration (placeholder only)
- PR review comments with details (Phase 2, uses TriggerPRReviewService)
- Auto-transition on PR merge (DD-003 approval workflow)
- Bidirectional sync (Pilot Space → GitHub)
- Rate limit pooling across workspaces
- Distributed webhook deduplication (currently in-memory)

