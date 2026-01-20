# Pilot Space - Design Decisions & Clarifications

This document records key design decisions made during the architecture review, capturing the rationale and implications for implementation.

---

## Decision Log

### DD-001: FastAPI Replaces Django

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
The initial architecture proposed using both FastAPI (as API Gateway) and Django (as Core API). This created ambiguity about request flow and added unnecessary complexity.

**Decision**:
Replace Django entirely with FastAPI + SQLAlchemy + Alembic.

**Rationale**:
- Single framework simplifies development and deployment
- FastAPI provides modern async support natively
- SQLAlchemy 2.0 offers excellent async capabilities
- Better alignment with AI workloads (async LLM calls)
- Cleaner OpenAPI/Swagger documentation

**Consequences**:
- Need to reimplement Django admin functionality (or use alternative like SQLAdmin)
- Lose Django's built-in authentication (implement with FastAPI-Users or custom)
- Migration from Plane's Django models to SQLAlchemy
- Team needs FastAPI/SQLAlchemy expertise

**Revised Technology Stack**:

| Layer | Technology |
|-------|------------|
| API Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | FastAPI-Users or custom JWT |
| Admin | SQLAdmin or custom |

---

### DD-002: BYOK (Bring Your Own Key) for AI

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
AI features require LLM access. Options included providing free credits, supporting local models (Ollama), or requiring users to provide their own API keys.

**Decision**:
- BYOK Required for all tiers
- Cloud LLM providers only (OpenAI, Anthropic, Azure OpenAI)
- No local model (Ollama) support
- No limits on AI usage when user provides valid API key

**Rationale**:
- Simplifies infrastructure (no need to run/scale LLM services)
- Users control their AI costs directly
- Avoids complex metering and billing
- Cloud LLMs provide consistent quality and reliability
- Local models add significant deployment complexity

**Consequences**:
- Users must have API keys to use AI features
- No "free trial" of AI capabilities
- Clear value proposition: platform is free, AI is BYOK
- Need secure key storage and management

**Configuration Model**:

```yaml
ai:
  providers:
    openai:
      api_key: ${USER_OPENAI_KEY}  # User-provided
      models: [gpt-4o, gpt-4o-mini]

    anthropic:
      api_key: ${USER_ANTHROPIC_KEY}  # User-provided
      models: [claude-sonnet-4-20250514, claude-3-5-haiku-20241022]

    azure_openai:
      api_key: ${USER_AZURE_KEY}  # User-provided
      endpoint: ${USER_AZURE_ENDPOINT}

  # No local model support
  # ollama: NOT SUPPORTED
```

---

### DD-003: AI Autonomy Model - Critical-Only Approval

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
The human-in-the-loop principle requires clarity on which AI actions need approval vs execute automatically.

**Decision**:
- **Auto-execute with notification**: Non-destructive actions (state transitions, label suggestions)
- **Require approval**: Destructive or critical actions (delete, merge, publish)
- **Configurable per project**: Project admins can adjust autonomy levels

**Action Classification**:

| Action | Default Behavior | Configurable |
|--------|------------------|--------------|
| Suggest labels/priority | Auto-apply suggestion UI | Yes |
| Auto-transition on PR events | Auto-execute + notify | Yes |
| Create sub-issues | Require approval | Yes |
| Post PR comments | Auto-execute | Yes |
| Delete/archive | Always require approval | No |
| Publish docs | Require approval | Yes |
| Send notifications | Auto-execute | Yes |

**Project Configuration**:

```yaml
project:
  ai_autonomy:
    level: balanced  # conservative | balanced | autonomous

    overrides:
      state_transitions: auto      # auto | approval | disabled
      pr_comments: auto
      issue_creation: approval
      documentation: approval
```

---

### DD-004: MVP Integration Scope - GitHub + Slack Only

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
Initial scope included all major integrations (GitHub, GitLab, Bitbucket, Jira, Trello, Asana, Slack, Discord, CI/CD). This was too ambitious for MVP.

**Decision**:
MVP includes only:
- **GitHub**: PR linking, commit tracking, AI code review comments
- **Slack**: Notifications, slash commands, issue creation

**Rationale**:
- GitHub is the dominant VCS platform
- Slack is the dominant team communication tool
- Focused scope enables quality over breadth
- Other integrations can be added in Phase 2

**Deferred to Phase 2**:
- GitLab integration
- Discord integration
- CI/CD pipeline integration

**Removed from Scope**:
- ~~Jira bidirectional sync~~ (too complex, limited value for target users)
- ~~Trello/Asana sync~~ (target users likely to migrate fully)
- ~~Bitbucket~~ (lower market share)
- ~~MS Teams~~ (enterprise focus is Phase 3)

---

### DD-005: Skip Real-Time Collaboration in MVP

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
Initial design included Y.js/HocusPocus for real-time collaborative editing of Pages (similar to Plane).

**Decision**:
Remove real-time collaboration from MVP. Use standard save-based editing.

**Rationale**:
- Significant infrastructure complexity (WebSocket server, CRDT state management)
- MVP can deliver value without real-time editing
- Standard editing with autosave is sufficient initially
- Can add real-time in Phase 2 if user demand exists

**Consequences**:
- Remove HocusPocus/Live server from architecture
- Simplify frontend (no Y.js integration)
- Pages use standard rich text editor with autosave
- Multiple users editing same content will have last-write-wins

**Future Consideration**:
If real-time is added later, start with Pages only (most valuable use case).

---

### DD-006: Both Architecture and Code Review in MVP

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
Originally, architecture review was MVP and code review was Phase 2.

**Decision**:
Include both AI Architecture Review and AI Code Review in MVP as a unified "AI PR Review" feature.

**Rationale**:
- AI-powered PR review is a core differentiator
- Architecture and code quality are closely related
- Single feature is easier to explain/market
- Combined review provides more value than either alone

**Unified Feature Scope**:

| Aspect | Checks |
|--------|--------|
| Architecture | Layer boundaries, patterns, dependency direction |
| Security | OWASP basics, secrets detection, auth checks |
| Quality | Complexity, duplication, naming |
| Performance | N+1 queries, blocking calls |
| Documentation | Missing docstrings, outdated comments |

---

### DD-007: Basic RBAC in MVP

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
Full RBAC with custom roles was planned for Phase 3, but enterprises often require access control from Day 1.

**Decision**:
Include basic fixed roles in MVP:

| Role | Permissions |
|------|-------------|
| **Owner** | Full workspace control, billing, delete workspace |
| **Admin** | Manage members, projects, integrations |
| **Member** | Create/edit issues, pages, cycles; view all |
| **Guest** | View assigned issues, comment on assigned |

**Phase 2 Additions**:
- Custom role creation
- Granular permissions
- Project-level role overrides

---

### DD-008: Remove AI Studio from Scope

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
Phase 4 roadmap included "AI Studio" as a separate app for custom agent creation and workflow automation.

**Decision**:
Remove AI Studio entirely. Focus on built-in AI agents with good defaults.

**Rationale**:
- Custom agent creation is complex to build and use
- Built-in agents cover primary use cases
- Reduces scope significantly
- If needed, can add prompt customization as a simpler alternative

**Alternative Approach**:
- Allow workspace-level prompt customization (simple text overrides)
- Provide agent enable/disable toggles per project
- Consider plugin system in future if extensibility demand exists

---

### DD-009: Merge Space App into Main App

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
Plane has a separate "Space" app (port 3002) for public read-only views.

**Decision**:
Merge public view functionality into the main web application as routes.

**Rationale**:
- Simplifies deployment (one frontend instead of three)
- Shared component library usage
- Easier routing and authentication
- Public views are just different auth contexts

**Implementation**:
- `/public/projects/:id` - Public project board
- `/public/issues/:id` - Public issue view
- `/public/pages/:id` - Public page view
- Authentication middleware handles public vs authenticated routes

---

### DD-010: Support Tiers Pricing Model

**Date**: 2026-01-20
**Status**: Accepted

**Context**:
Pricing showed $10/seat (Pro) and $18/seat (Business). Unclear if this applied to self-hosted.

**Decision**:
- Self-hosted is always 100% free with full features
- Paid tiers are for **support and SLA only** (Cloud or self-hosted)
- No feature gating based on payment

**Pricing Structure**:

| Tier | Price | What You Get |
|------|-------|--------------|
| **Community** | Free | Full platform, community support (GitHub issues) |
| **Pro Support** | $10/seat/mo | Email support, 48h response SLA |
| **Business Support** | $18/seat/mo | Priority support, 24h SLA, dedicated Slack |
| **Enterprise** | Custom | Dedicated support, custom SLA, consulting |

**Rationale**:
- Encourages adoption (no feature anxiety)
- Clear value proposition for support tiers
- Aligns with open-source community expectations
- Revenue from users who need guaranteed support

---

## Revised Architecture

Based on all decisions, the revised MVP architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PILOT SPACE MVP                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    WEB APPLICATION                       │   │
│  │                    (React + TypeScript)                  │   │
│  │                                                          │   │
│  │  Routes:                                                 │   │
│  │  • /app/* - Authenticated application                   │   │
│  │  • /admin/* - Admin panel                               │   │
│  │  • /public/* - Public views (merged Space)              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FASTAPI BACKEND                       │   │
│  │                                                          │   │
│  │  • REST API (OpenAPI documented)                        │   │
│  │  • SQLAlchemy 2.0 (async)                               │   │
│  │  • Alembic migrations                                   │   │
│  │  • Pydantic v2 validation                               │   │
│  │  • JWT authentication                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│              ┌───────────────┼───────────────┐                 │
│              │               │               │                 │
│              ▼               ▼               ▼                 │
│         ┌────────┐     ┌─────────┐     ┌─────────┐            │
│         │PostgreSQL│    │  Redis  │     │RabbitMQ │            │
│         │+ pgvector│    │ (Cache) │     │ (Queue) │            │
│         └────────┘     └─────────┘     └─────────┘            │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 BACKGROUND WORKERS                       │   │
│  │                 (Celery or ARQ)                          │   │
│  │                                                          │   │
│  │  • AI tasks (LLM calls)                                 │   │
│  │  • Integration sync (GitHub, Slack)                     │   │
│  │  • Email notifications                                  │   │
│  │  • Webhook delivery                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│                    External Services                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │ GitHub  │  │  Slack  │  │  LLM    │  │  S3/    │          │
│  │  API    │  │   API   │  │Provider │  │  MinIO  │          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Revised Feature Roadmap

### Phase 1: MVP

**Core PM**:
- Workspaces, Projects
- Issues with states, priorities, assignees
- Cycles (Sprints) with basic analytics
- Modules (Epics)
- Pages (standard editing, no real-time)
- Views with filtering
- Labels, custom states
- Basic RBAC (Owner/Admin/Member/Guest)

**AI Features** (BYOK):
- AI-enhanced issue creation
- Smart task decomposition
- AI PR Review (architecture + code)
- AI documentation generation
- Diagram generation (Mermaid)
- Semantic search

**Integrations**:
- GitHub (PR linking, commits, AI review comments)
- Slack (notifications, slash commands)
- Webhooks (outbound)

### Phase 2: Enhanced

**Features**:
- Real-time collaboration for Pages
- Custom workflows with AI transitions
- ADR (Architecture Decision Records)
- Sprint planning assistant
- Retrospective analyst

**Integrations**:
- GitLab integration
- Discord integration
- CI/CD status display

**Enterprise**:
- Custom RBAC roles
- SSO (OIDC/SAML)
- Audit logging

### Phase 3: Enterprise

**Features**:
- Advanced analytics
- Workflow automation builder
- LDAP directory sync
- Compliance reporting
- Custom report builder

---

## Removed from Scope

The following items have been explicitly removed:

| Item | Reason |
|------|--------|
| Jira bidirectional sync | Complexity, limited value for target users |
| Trello/Asana sync | Users expected to migrate fully |
| AI Studio | Too complex, built-in agents sufficient |
| Local AI (Ollama) | Deployment complexity, cloud LLM required |
| MS Teams integration | Enterprise focus deferred |
| Bitbucket integration | Lower priority |

---

*Document Version: 1.0*
*Last Updated: 2026-01-20*
*Author: Pilot Space Team*
