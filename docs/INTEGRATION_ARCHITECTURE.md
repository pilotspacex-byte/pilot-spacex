# Pilot Space - Integration Architecture

## Overview

Pilot Space integrates with essential development tools to enhance workflow without replacing existing systems. This document details the architecture for MVP integrations.

> **MVP Scope**: GitHub + Slack only. See DESIGN_DECISIONS.md DD-004 for rationale.

### MVP Integration Summary

| Integration | Status | Purpose |
|-------------|--------|---------|
| **GitHub** | MVP | PR linking, commits, AI code review |
| **Slack** | MVP | Notifications, slash commands, issue creation |
| GitLab | Phase 2 | Deferred |
| Discord | Phase 2 | Deferred |
| Jira | Removed | Users expected to migrate |
| Trello | Removed | Users expected to migrate |
| Asana | Removed | Users expected to migrate |
| CI/CD (Jenkins, etc.) | Phase 2 | Deferred |

---

## Integration Philosophy

### Design Principles

1. **Event-Driven**: Use webhooks and events for real-time sync
2. **Graceful Degradation**: Features work without integrations, enhanced with them
3. **Idempotent Operations**: Safe retry handling for all sync operations
4. **Source of Truth**: Pilot Space is the primary source; GitHub/Slack provide events
5. **Minimal Footprint**: Request only necessary OAuth scopes

### Integration Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATION PATTERNS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────┐  ┌───────────────────────┐          │
│  │   INBOUND (Import)    │  │   OUTBOUND (Export)   │          │
│  │                       │  │                       │          │
│  │  External → Pilot     │  │  Pilot → External     │          │
│  │                       │  │                       │          │
│  │  • Webhooks           │  │  • API calls          │          │
│  │  • Polling            │  │  • Webhooks           │          │
│  │  • OAuth triggers     │  │  • Event publishing   │          │
│  └───────────────────────┘  └───────────────────────┘          │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                  BIDIRECTIONAL (Sync)                      │ │
│  │                                                            │ │
│  │  • Conflict resolution strategies                          │ │
│  │  • Last-write-wins vs merge                                │ │
│  │  • Field-level sync rules                                  │ │
│  │  • Sync state tracking                                     │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Version Control Integration

### GitHub Integration

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GITHUB INTEGRATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                      ┌─────────────┐          │
│  │   GitHub    │◄────────────────────►│ Pilot Space │          │
│  │             │                      │             │          │
│  └──────┬──────┘                      └──────┬──────┘          │
│         │                                    │                  │
│         │  OAuth 2.0 (User Auth)            │                  │
│         │  GitHub App (Org Auth)            │                  │
│         │                                    │                  │
│         ▼                                    ▼                  │
│  ┌──────────────┐                    ┌──────────────┐          │
│  │   Webhooks   │                    │   REST API   │          │
│  │              │                    │   GraphQL    │          │
│  │  • push      │                    │              │          │
│  │  • PR events │                    │  • Issues    │          │
│  │  • review    │                    │  • PRs       │          │
│  │  • check     │                    │  • Commits   │          │
│  └──────────────┘                    └──────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Features

| Feature | Direction | Description |
|---------|-----------|-------------|
| **Repository Linking** | Setup | Connect GitHub repos to Pilot Space projects |
| **PR Linking** | Bidirectional | Link PRs to issues, update status |
| **Commit Tracking** | Inbound | Track commits mentioning issue IDs |
| **Branch Sync** | Inbound | Auto-create issues from branch naming |
| **Code Review AI** | Outbound | Post AI review comments on PRs |
| **Status Checks** | Outbound | Block merges based on issue state |
| **Issue Sync** | Bidirectional | Sync issues between platforms |

#### Data Mapping

```yaml
github_to_pilot:
  issue:
    title: name
    body: description_html
    labels: labels (matched by name)
    assignees: assignees (matched by email)
    state: state (open→todo, closed→done)
    milestone: cycle (matched by name)

  pull_request:
    title: link_title
    state: link_state
    merged: triggers issue state change
    reviews: activity entries

  commit:
    message: parsed for issue references
    sha: stored as link
    author: matched to user

pilot_to_github:
  issue:
    name: title
    description_html: body
    labels: labels (create if needed)
    assignees: assignees (by username)
    state: state (done→closed)
```

#### Webhook Events

| Event | Action |
|-------|--------|
| `pull_request.opened` | Create issue link, notify assignees |
| `pull_request.closed` | Update linked issue status |
| `pull_request.review` | Add activity, trigger AI re-review |
| `push` | Parse commits for issue mentions |
| `check_suite.completed` | Update CI status on linked issues |
| `issues.opened` | Sync to Pilot Space (if enabled) |

#### Configuration

```yaml
integration:
  github:
    app_id: ${GITHUB_APP_ID}
    private_key: ${GITHUB_PRIVATE_KEY}
    webhook_secret: ${GITHUB_WEBHOOK_SECRET}

    sync:
      issues: bidirectional  # none, inbound, outbound, bidirectional
      pull_requests: inbound
      commits: inbound

    features:
      ai_review: true
      status_checks: true
      auto_link: true

    branch_patterns:
      - pattern: "^(feature|fix|chore)/([A-Z]+-\\d+)"
        issue_regex: "([A-Z]+-\\d+)"

    commit_patterns:
      - pattern: "(closes?|fixes?|resolves?)\\s+#?(\\d+)"
        action: close_issue
```

---

## Deferred Integrations (Phase 2+)

The following integrations are planned for future phases:

| Integration | Phase | Rationale |
|-------------|-------|-----------|
| **GitLab** | Phase 2 | MR linking, commits, AI review (similar to GitHub) |
| **Discord** | Phase 2 | Notifications, bot commands (similar to Slack) |
| **CI/CD Pipelines** | Phase 2 | Build status, deployment tracking |
| **Bitbucket** | Removed | Lower market share |
| **Jira** | Removed | Complex bidirectional sync, users expected to migrate |
| **Trello** | Removed | Users expected to migrate fully |
| **Asana** | Removed | Users expected to migrate fully |
| **MS Teams** | Phase 3 | Enterprise focus |

See DESIGN_DECISIONS.md for detailed rationale on integration scope decisions.

---

## Communication Platform Integration

### Slack Integration

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SLACK INTEGRATION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    SLACK APP                              │   │
│  │                                                           │   │
│  │  Scopes:                                                  │   │
│  │  • chat:write (post messages)                             │   │
│  │  • channels:read (list channels)                          │   │
│  │  • users:read (user mapping)                              │   │
│  │  • commands (slash commands)                              │   │
│  │  • app_mentions:read (bot mentions)                       │   │
│  │  • links:read (URL unfurling)                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FEATURES                               │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │  │Notifications│  │   Slash     │  │   URL       │      │   │
│  │  │             │  │  Commands   │  │ Unfurling   │      │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │  │   Issue     │  │   Actions   │  │    Bot      │      │   │
│  │  │  Creation   │  │  (Buttons)  │  │   Mentions  │      │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │   │
│  │                                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Notification Types

| Event | Notification Format |
|-------|---------------------|
| Issue Created | Rich card with details + actions |
| Issue Updated | Compact update message |
| Comment Added | Threaded reply to issue message |
| PR Linked | Status update with link |
| Sprint Started | Summary with sprint goals |
| Due Date Alert | Reminder with snooze option |

#### Slash Commands

| Command | Description |
|---------|-------------|
| `/pilot create` | Create issue from Slack |
| `/pilot search <query>` | Search issues |
| `/pilot link <issue-id>` | Link issue to channel |
| `/pilot sprint` | Show current sprint status |
| `/pilot standup` | Generate standup summary |

#### Interactive Actions

```yaml
actions:
  issue_card:
    - label: "Assign to me"
      action: assign_self
    - label: "Change Status"
      action: status_dropdown
    - label: "Comment"
      action: open_modal

  notification:
    - label: "View"
      action: open_issue
    - label: "Snooze"
      action: snooze_menu
    - label: "Mark Done"
      action: complete_issue
```

> **Note**: Discord integration deferred to Phase 2. MS Teams deferred to Phase 3. See DESIGN_DECISIONS.md DD-004.

---

## Webhook System

### Outbound Webhooks

Pilot Space can notify external systems of events.

#### Configuration

```yaml
webhooks:
  - id: "wh_123"
    name: "External System Notifier"
    url: "https://api.external.com/webhook"
    secret: "whsec_..."

    events:
      - issue.created
      - issue.updated
      - issue.deleted
      - cycle.started
      - cycle.completed
      - comment.created

    filters:
      project_ids: ["proj_abc", "proj_def"]
      labels: ["external-sync"]

    delivery:
      retry_count: 5
      retry_delay: exponential  # 1s, 2s, 4s, 8s, 16s
      timeout: 30s
```

#### Payload Format

```json
{
  "id": "evt_123456",
  "type": "issue.updated",
  "timestamp": "2026-01-20T10:30:00Z",
  "workspace_id": "ws_abc",
  "project_id": "proj_def",
  "data": {
    "issue": {
      "id": "iss_789",
      "sequence_id": 42,
      "name": "Implement user authentication",
      "state": "in_progress",
      "priority": "high",
      "assignees": ["user_123"]
    },
    "changes": {
      "state": {
        "old": "todo",
        "new": "in_progress"
      }
    },
    "actor": {
      "id": "user_456",
      "name": "John Doe"
    }
  }
}
```

#### Signature Verification

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Inbound Webhooks

Pilot Space can receive events from external systems.

```yaml
inbound_webhooks:
  - id: "iwh_456"
    name: "External Issue Sync"
    endpoint: "/api/webhooks/inbound/iwh_456"
    secret: "iwhsec_..."

    handlers:
      - event_type: "ticket.created"
        action: create_issue
        mapping:
          title: "$.ticket.subject"
          description: "$.ticket.description"
          priority: "$.ticket.priority | priority_map"

      - event_type: "ticket.updated"
        action: update_issue
        match_by: external_id
```

---

## Integration Sync Engine

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SYNC ENGINE (MVP)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    EVENT QUEUE                             │ │
│  │  (RabbitMQ)                                                │ │
│  │                                                            │ │
│  │  Queues:                                                   │ │
│  │  • sync.github.inbound    (webhooks from GitHub)          │ │
│  │  • sync.github.outbound   (PR comments, AI review)        │ │
│  │  • sync.slack.outbound    (notifications, messages)       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    SYNC WORKERS                            │ │
│  │  (Celery or ARQ)                                           │ │
│  │                                                            │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐        │ │
│  │  │   GitHub Worker     │  │   Slack Worker      │        │ │
│  │  │                     │  │                     │        │ │
│  │  │  • PR webhooks      │  │  • Notifications    │        │ │
│  │  │  • Commit parsing   │  │  • Slash commands   │        │ │
│  │  │  • AI review posts  │  │  • URL unfurling    │        │ │
│  │  └─────────────────────┘  └─────────────────────┘        │ │
│  │                                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    SYNC STATE                              │ │
│  │  (PostgreSQL)                                              │ │
│  │                                                            │ │
│  │  Tables:                                                   │ │
│  │  • integration_links (issue ↔ PR/commit)                  │ │
│  │  • sync_log (audit trail)                                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Sync State Model (MVP - Simplified)

For MVP, sync is primarily one-directional:
- **GitHub → Pilot Space**: PR/commit events update linked issues
- **Pilot Space → Slack**: Notifications pushed to channels

```python
class IntegrationLink(Base):
    """Links Pilot Space issues to GitHub PRs/commits."""

    __tablename__ = "integration_links"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))

    # Internal entity
    entity_type: Mapped[str]  # issue, project
    entity_id: Mapped[UUID]

    # External entity
    integration_type: Mapped[str]  # github
    external_id: Mapped[str]  # PR number, commit SHA
    external_url: Mapped[str]

    # Metadata
    created_at: Mapped[datetime]
    link_type: Mapped[str]  # pr, commit, branch


class SyncLog(Base):
    """Audit log for sync operations."""

    __tablename__ = "sync_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    integration_type: Mapped[str]
    operation: Mapped[str]  # pr_linked, commit_parsed, notification_sent
    entity_id: Mapped[UUID]
    external_id: Mapped[str]
    status: Mapped[str]  # success, error
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime]
```

> **Note**: Complex bidirectional sync and conflict resolution deferred to Phase 2 with GitLab integration.

---

## API & SDK

### REST API for Integrations (MVP)

```yaml
endpoints:
  # GitHub Integration
  GET  /api/v1/workspaces/{workspace}/integrations/github
  POST /api/v1/workspaces/{workspace}/integrations/github/install
  DELETE /api/v1/workspaces/{workspace}/integrations/github

  # GitHub repositories
  GET  /api/v1/workspaces/{workspace}/integrations/github/repos
  POST /api/v1/projects/{project}/github/link  # Link repo to project

  # Slack Integration
  GET  /api/v1/workspaces/{workspace}/integrations/slack
  POST /api/v1/workspaces/{workspace}/integrations/slack/install
  DELETE /api/v1/workspaces/{workspace}/integrations/slack

  # Slack channels
  GET  /api/v1/workspaces/{workspace}/integrations/slack/channels
  POST /api/v1/projects/{project}/slack/link  # Link channel to project

  # Issue links (GitHub PRs/commits)
  GET /api/v1/issues/{issue}/links

  # Outbound Webhooks
  GET    /api/v1/workspaces/{workspace}/webhooks
  POST   /api/v1/workspaces/{workspace}/webhooks
  DELETE /api/v1/workspaces/{workspace}/webhooks/{id}
```

> **Note**: Integration SDK for custom integrations planned for Phase 2.

---

## Security Considerations

### OAuth Token Management

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOKEN MANAGEMENT                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Storage:                                                       │
│  • Tokens encrypted at rest (AES-256)                          │
│  • Separate encryption key per workspace                        │
│  • Key rotation support                                         │
│                                                                 │
│  Access:                                                        │
│  • Tokens never exposed in API responses                        │
│  • Server-side only usage                                       │
│  • Audit logging for token access                               │
│                                                                 │
│  Refresh:                                                       │
│  • Automatic refresh before expiry                              │
│  • Retry with backoff on failure                                │
│  • User notification on persistent failure                      │
│                                                                 │
│  Revocation:                                                    │
│  • Immediate revocation on disconnect                           │
│  • Workspace deletion cleans all tokens                         │
│  • Admin can force re-authentication                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Permission Scopes (MVP)

| Integration | Minimum Scopes | Optional Scopes |
|-------------|----------------|-----------------|
| GitHub | `repo:read`, `metadata` | `repo:write` (for AI review comments) |
| Slack | `chat:write`, `channels:read` | `commands`, `users:read` |

### Rate Limiting

```yaml
rate_limits:
  github:
    authenticated: 5000/hour
    search: 30/minute

  slack:
    tier_1: 1/second
    tier_2: 20/minute

  internal:
    webhook_delivery: 1000/minute
```

---

## Monitoring & Observability

### Integration Health Dashboard (MVP)

| Metric | Alert Threshold |
|--------|-----------------|
| Webhook processing latency | > 30 seconds |
| Error rate | > 5% |
| Queue depth | > 500 pending |
| GitHub token expiry | < 24 hours |
| Slack notification delivery | < 95% success |

### Sync Logs

```json
{
  "timestamp": "2026-01-20T10:30:00Z",
  "integration": "github",
  "operation": "pr_linked",
  "entity_type": "issue",
  "entity_id": "iss_123",
  "external_id": "PR#456",
  "status": "success",
  "duration_ms": 234
}
```

---

*Document Version: 1.1*
*Last Updated: 2026-01-20*
*Author: Pilot Space Team*
*Changes: Reduced MVP scope to GitHub + Slack only per DD-004*
