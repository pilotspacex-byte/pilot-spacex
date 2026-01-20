# Pilot Space - AI-Augmented SDLC Platform

## Executive Summary

**Pilot Space** is an AI-augmented Software Development Lifecycle (SDLC) platform designed to transform how software development teams collaborate, document, and manage projects. Built on proven open-source foundations (inspired by Plane's architecture), Pilot Space integrates powerful AI capabilities as first-class citizens to assist software architects, developers, and product teams throughout the entire development lifecycle.

### Mission Statement

> Enable software development teams to ship quality software faster through intelligent AI assistance that augments human expertise in architecture design, documentation, code review, and project management—while maintaining full human oversight and control.

### Core Value Proposition

**Pilot Space is a complete scrum board replacement** with built-in AI capabilities. It is not an integration layer on top of existing tools—it provides full project management functionality (Issues, Cycles/Sprints, Modules/Epics, Pages/Documentation) with AI augmentation throughout.

| Traditional PM Tools | Pilot Space |
|---------------------|-------------|
| Manual documentation | AI-generated + human-refined documentation |
| Reactive issue tracking | Proactive AI suggestions on patterns & best practices |
| Siloed code reviews | Integrated architecture compliance checking |
| Static task boards | Intelligent workflow automation with human-in-the-loop |
| Disconnected tools | Unified workspace with GitHub & Slack integrations |
| Separate scrum board (Jira/Trello) | **Built-in scrum board with AI enhancement** |

---

## Target Audience

### Primary Users

| Segment | Needs | Pilot Space Value |
|---------|-------|-------------------|
| **Software Development Teams** | Technical SDLC workflows, code-architecture alignment | AI-powered architecture reviews, automated documentation |
| **Cross-Functional Product Teams** | Collaboration between PM, design, engineering | Unified workspace with role-appropriate AI assistance |
| **Startups & SMBs** | Cost-effective, agile solutions | Open-source self-hosted, AI that scales with team |
| **Enterprise Organizations** | Compliance, RBAC, audit trails | Enterprise security, SOC 2 compliance support, LDAP |

### User Personas

**1. Sarah - Software Architect**
- Reviews architectural decisions across 5 teams
- Needs: Automated architecture compliance checks, pattern suggestions, ADR generation
- Pain: Manual review bottleneck, inconsistent documentation

**2. Marcus - Tech Lead**
- Manages sprint delivery and code quality
- Needs: AI-assisted code reviews, technical debt tracking, sprint analytics
- Pain: Context-switching between tools, review fatigue

**3. Elena - Product Manager**
- Coordinates cross-functional delivery
- Needs: Intelligent roadmap planning, stakeholder updates, requirement clarity
- Pain: Translating requirements to technical specs, status tracking overhead

**4. Dev - Junior Developer**
- Learning codebase and best practices
- Needs: Contextual guidance, documentation discovery, pattern examples
- Pain: Onboarding friction, finding relevant documentation

---

## Key Principles

Pilot Space is built on seven foundational principles that guide all product decisions:

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **AI-Human Collaboration First** | AI augments human expertise, never replaces human judgment |
| 2 | **Note-Second Approach** | Capture thoughts quickly, refine into structured documentation |
| 3 | **Documentation-Third Approach** | Documentation flows naturally from work artifacts |
| 4 | **Task-Centric Workflow** | Prioritize actionable tasks with AI-powered decomposition |
| 5 | **Collaboration & Knowledge Sharing** | Foster team knowledge through AI-curated insights |
| 6 | **Agile Integration** | Align with agile methodologies, enhance with AI |
| 7 | **Notation & Standards** | Promote standardized notations (UML, C4, ArchiMate, Mermaid) |

### 1. AI-Human Collaboration First

AI augments human expertise—it does not replace human judgment. Every AI action follows human-in-the-loop principles:

```
User Intent → AI Suggestion → Human Review → Execution
                   ↓
            User can modify, accept, or reject
```

**Implementation:**
- AI suggestions are always presented for human approval
- Critical actions (merge, deploy, delete) require explicit human confirmation
- AI provides rationale and alternatives for transparency
- Users can adjust AI behavior per workspace/project

### 2. Note-Second Approach

Encourage capturing thoughts, designs, and decisions in structured notes before formal documentation:

```
Quick Note (Sticky) → Refined Note (Page) → Formal Doc (Architecture Doc)
       ↓                      ↓                       ↓
  AI organizes          AI structures           AI validates
```

**Features:**
- Quick capture via Stickies with AI categorization
- AI-assisted note-to-document conversion
- Automatic linking of related notes to issues/decisions

### 3. Documentation-Third Approach

Comprehensive documentation flows naturally from work artifacts:

```
Code Changes → AI Analysis → Draft Documentation → Human Review → Published Doc
     ↓              ↓               ↓                   ↓
  PR/Commit   Pattern Detection   Template Fill   Quality Gate
```

**Features:**
- Auto-generated API documentation from code
- Architecture diagram generation from codebase analysis
- Living documentation that updates with code changes

### 4. Task-Centric Workflow

Prioritize actionable tasks with AI-powered decomposition:

```
Epic/Feature Request
       ↓
  AI Decomposition
       ↓
  Task Breakdown (User Stories, Technical Tasks)
       ↓
  AI-Suggested Acceptance Criteria
       ↓
  Human Refinement & Assignment
```

### 5. Collaboration & Knowledge Sharing

Foster team knowledge through AI-curated insights:

- **Pattern Library**: AI identifies and catalogs recurring patterns
- **Decision Log**: AI-assisted Architecture Decision Records (ADRs)
- **Expertise Mapping**: AI suggests reviewers based on code ownership
- **Knowledge Graph**: AI builds relationships between docs, code, and decisions

### 6. Agile Integration

Align with agile methodologies while enhancing with AI:

- **Sprint Planning**: AI suggests story points based on historical data
- **Retrospective Insights**: AI analyzes sprint metrics for improvement areas
- **Velocity Prediction**: ML-based sprint velocity forecasting
- **Blocker Detection**: Proactive identification of at-risk items

### 7. Notation & Standards

Promote standardized architectural notation with AI assistance:

- **UML Generation**: AI generates sequence/class diagrams from descriptions
- **ArchiMate Support**: Enterprise architecture modeling
- **C4 Model**: AI-assisted context, container, component, code diagrams
- **Mermaid Integration**: Code-based diagram rendering

---

## Technology Architecture

> **Note**: See [DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md) for detailed rationale behind architectural choices.

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PILOT SPACE PLATFORM                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      WEB APPLICATION                             │   │
│  │                   (React + TypeScript)                           │   │
│  │                                                                  │   │
│  │  Routes:                                                         │   │
│  │  • /app/* - Authenticated application                           │   │
│  │  • /admin/* - Admin panel                                       │   │
│  │  • /public/* - Public views (boards, pages)                     │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      FASTAPI BACKEND                             │   │
│  │                                                                  │   │
│  │  • REST API (OpenAPI documented)                                │   │
│  │  • SQLAlchemy 2.0 (async) + Alembic                            │   │
│  │  • Pydantic v2 validation                                       │   │
│  │  • JWT authentication                                           │   │
│  │  • AI service layer (LLM orchestration)                         │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                       │
│              ┌──────────────────┼──────────────────┐                   │
│              │                  │                  │                   │
│              ▼                  ▼                  ▼                   │
│         ┌────────┐        ┌─────────┐        ┌─────────┐              │
│         │PostgreSQL│      │  Redis  │        │RabbitMQ │              │
│         │+ pgvector│      │ (Cache) │        │ (Queue) │              │
│         └────────┘        └─────────┘        └─────────┘              │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BACKGROUND WORKERS                            │   │
│  │                    (Celery or ARQ)                               │   │
│  │                                                                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│  │  │  Email   │  │ Webhooks │  │    AI    │  │   Sync   │        │   │
│  │  │  Worker  │  │  Worker  │  │  Worker  │  │  Worker  │        │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

                         External Services
┌─────────────────────────────────────────────────────────────────────────┐
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                    │
│  │ GitHub  │  │  Slack  │  │   LLM   │  │   S3/   │                    │
│  │   API   │  │   API   │  │Provider │  │  MinIO  │                    │
│  │         │  │         │  │ (BYOK)  │  │         │                    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | React 18, TypeScript, MobX, TailwindCSS | Proven stack, component reuse, type safety |
| **Rich Editor** | TipTap/ProseMirror | Extensible rich text (no real-time in MVP) |
| **API** | FastAPI (Python) | Modern async, OpenAPI, Pydantic integration |
| **ORM** | SQLAlchemy 2.0 (async) | Native async support, excellent FastAPI fit |
| **Migrations** | Alembic | Standard SQLAlchemy migration tool |
| **AI Engine** | LangChain/LlamaIndex | LLM orchestration, RAG, agents |
| **Database** | PostgreSQL 15+ with pgvector | JSONB, full-text search, vector embeddings |
| **Cache** | Redis | Session, rate limiting, AI response cache |
| **Queue** | RabbitMQ + Celery/ARQ | Async tasks, AI job processing |
| **Storage** | S3-compatible (MinIO) | Self-hosted object storage |
| **Search** | Meilisearch | Fast, typo-tolerant search |

### AI Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI ENGINE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                   ORCHESTRATION LAYER                      │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │ Task Router │  │Context Mgr  │  │ Key Manager │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐ │
│  │                    AGENT FRAMEWORK                         │ │
│  │                                                            │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │ │
│  │  │    PR    │ │   Doc    │ │  Task    │ │ Diagram  │     │ │
│  │  │  Review  │ │Generator │ │ Planner  │ │Generator │     │ │
│  │  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │     │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │ │
│  │                                                            │ │
│  │  ┌──────────┐ ┌──────────┐                               │ │
│  │  │ Knowledge│ │  Issue   │                               │ │
│  │  │  Search  │ │ Enhance  │                               │ │
│  │  │  Agent   │ │  Agent   │                               │ │
│  │  └──────────┘ └──────────┘                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐ │
│  │                    RAG PIPELINE                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │  Embeddings │  │Vector Store │  │  Retriever  │       │ │
│  │  │  (OpenAI)   │  │ (pgvector)  │  │             │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐ │
│  │               LLM PROVIDERS (BYOK)                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │   OpenAI    │  │  Anthropic  │  │ Azure OpenAI│       │ │
│  │  │             │  │   Claude    │  │             │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  │                                                            │ │
│  │  Users provide their own API keys (BYOK model)            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature Roadmap

> **Note**: See [DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md) for detailed rationale behind scope decisions.

### Phase 1: MVP

**Core Project Management**
- [ ] Workspaces and Projects
- [ ] Issues with states, priorities, assignees
- [ ] Cycles (Sprints) with basic analytics
- [ ] Modules (Epics/Features)
- [ ] Pages (standard editing, autosave)
- [ ] Views with filtering and layouts
- [ ] Labels and custom states
- [ ] Basic RBAC (Owner/Admin/Member/Guest)
- [ ] Notifications system

**AI Features (BYOK - Bring Your Own Key)**
- [ ] AI-enhanced issue creation (title, description, labels, priority)
- [ ] Smart task decomposition from feature descriptions
- [ ] AI PR Review (architecture + code quality + security)
- [ ] Documentation generation from code/issues
- [ ] Diagram generation (Mermaid)
- [ ] Semantic search across workspace content
- [ ] Duplicate detection

**Integrations**
- [ ] GitHub: PR linking, commit tracking, AI review comments
- [ ] Slack: Notifications, slash commands, issue creation
- [ ] Webhooks (outbound)

### Phase 2: Enhanced Workflows

**AI Enhancements**
- [ ] ADR (Architecture Decision Record) generation
- [ ] Custom workflow with AI-powered transitions
- [ ] Sprint planning assistant
- [ ] Retrospective analyst
- [ ] Pattern detection and suggestions

**Real-Time Collaboration**
- [ ] Pages: Y.js/HocusPocus real-time editing

**Integrations**
- [ ] GitLab integration
- [ ] Discord integration
- [ ] CI/CD status display (GitHub Actions)

**Enterprise**
- [ ] Custom RBAC roles
- [ ] SSO (OIDC/SAML)
- [ ] Audit logging

### Phase 3: Enterprise & Analytics

**Enterprise Features**
- [ ] LDAP directory sync
- [ ] Compliance reporting
- [ ] Advanced security controls

**Analytics**
- [ ] Predictive sprint analytics
- [ ] Team health metrics
- [ ] Cycle time optimization
- [ ] Custom report builder

**Community Engagement**
- [ ] Discussion forums for architects
- [ ] Pattern library sharing across workspaces
- [ ] Public template repository
- [ ] Mentorship matching

**Removed from Scope**
- ~~Jira bidirectional sync~~ (complexity vs value)
- ~~Trello/Asana sync~~ (users expected to migrate)
- ~~AI Studio~~ (built-in agents sufficient)
- ~~Local AI (Ollama)~~ (cloud LLM required)

---

## Deployment Model

### Open Source Self-Hosted (Primary)

```yaml
# docker-compose.yml
services:
  web:
    image: pilotspace/web:latest
    ports: ["3000:3000"]
    environment:
      - API_URL=http://api:8000

  api:
    image: pilotspace/api:latest
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://rabbitmq:5672

  worker:
    image: pilotspace/api:latest
    command: celery -A app worker
    environment:
      - DATABASE_URL=postgresql+asyncpg://...

  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  rabbitmq:
    image: rabbitmq:3-alpine

  minio:
    image: minio/minio
    command: server /data

volumes:
  postgres_data:
```

**Self-Hosted Benefits:**
- Full data sovereignty
- 100% free with all features
- BYOK for AI (users control costs)
- Air-gapped deployment support (AI features require external LLM access)

### Pricing Model (Support Tiers)

| Tier | Price | Support |
|------|-------|---------|
| **Community** | Free | GitHub issues, community forums |
| **Pro Support** | $10/seat/mo | Email support, 48h response SLA |
| **Business Support** | $18/seat/mo | Priority support, 24h SLA, dedicated Slack |
| **Enterprise** | Custom | Dedicated support, custom SLA, consulting |

**Note**: All features are free. Paid tiers are for support and SLA guarantees only.

---

## Competitive Positioning

### Market Landscape

| Tool | Strengths | Weaknesses | Pilot Space Advantage |
|------|-----------|------------|----------------------|
| **Jira** | Enterprise adoption, extensive features | Complex, expensive, slow | Simpler UX, AI-native, open source |
| **Linear** | Fast, modern UX, developer-focused | Closed source, limited AI | Open source, deeper AI integration |
| **Plane** | Open source, modern, self-hosted | No AI features | AI-first architecture |
| **GitHub Projects** | Tight VCS integration | Limited PM features | Full PM + AI + multi-VCS |
| **Notion** | Flexible docs + tasks | Not built for SDLC | SDLC-specific AI assistance |

### Unique Differentiators

1. **AI-Native Architecture**: AI is not a bolt-on but a core platform capability
2. **Open Source + Self-Hosted**: Full control over data and customization
3. **Human-in-the-Loop**: AI augments, never replaces human judgment
4. **SDLC-Focused AI**: Purpose-built for software development workflows
5. **Architecture-Aware**: Understands code structure, not just text
6. **Integration Hub**: Bridges existing tools rather than replacing them

---

## Success Metrics

### Adoption Metrics
- GitHub stars and forks
- Docker pulls
- Active installations (telemetry opt-in)
- Community contributors

### Usage Metrics
- AI feature activation rate
- AI suggestion acceptance rate
- Documentation generation usage
- Integration connection count

### Outcome Metrics
- Time to first commit (onboarding)
- Sprint velocity improvement
- Documentation coverage increase
- Code review turnaround time

---

## References & Research Sources

### AI-Augmented SDLC
- [How AI is Transforming SDLC](https://www.ilink-digital.com/insights/blog/how-ai-is-transforming-the-software-development-life-cycle-sdlc-a-smarter-faster-future-for-engineering-teams/)
- [SDLC in 2026: AI Integration and Best Practices](https://graffersid.com/software-development-life-cycle/)
- [AWS: Transforming SDLC with Generative AI](https://aws.amazon.com/blogs/apn/transforming-the-software-development-lifecycle-sdlc-with-generative-ai/)
- [The Modern SDLC in 2026: AI-Powered Tools](https://calmops.com/indie-hackers/modern-sdlc-ai-tools/)
- [EPAM: AI-Native Software Development](https://www.epam.com/insights/ai/blogs/the-future-of-sdlc-is-ai-native-development)
- [CMU SEI: AI-Augmented SDLC Workshop](https://www.sei.cmu.edu/events/ai-augmented-sdlc/)

### AI Code Review & Documentation
- [AI Code Review Tools 2026](https://www.qodo.ai/blog/best-ai-code-review-tools-2026/)
- [Best AI Coding Agents 2026](https://www.faros.ai/blog/best-ai-coding-agents-2026)
- [AI Tools for Coding Documentation](https://www.index.dev/blog/best-ai-tools-for-coding-documentation)
- [AI Code Documentation Automation](https://graphite.com/guides/ai-code-documentation-automation)

### Project Management Tools
- [Linear App Features & Review](https://efficient.app/apps/linear)
- [Jira vs Trello vs Asana 2026](https://productive.io/blog/jira-vs-trello-vs-asana/)
- [Top Open Source PM Software 2026](https://plane.so/blog/top-6-open-source-project-management-software-in-2026)
- [Plane GitHub Repository](https://github.com/makeplane/plane)

---

*Document Version: 1.1*
*Last Updated: 2026-01-20*
*Author: Pilot Space Team*
*Changes: Added Key Principles table, Community Engagement to Phase 3, clarified scrum board replacement positioning*
