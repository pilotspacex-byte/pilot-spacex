# Pilot Space - AI-Augmented SDLC Platform

## Executive Summary

**Pilot Space** is an AI-augmented Software Development Lifecycle (SDLC) platform designed to transform how software development teams collaborate, document, and manage projects. Built on proven open-source foundations (inspired by Plane's architecture), Pilot Space integrates powerful AI capabilities as first-class citizens to assist software architects, developers, and product teams throughout the entire development lifecycle.

### Mission Statement

> Enable software development teams to ship quality software faster through intelligent AI assistance that augments human expertise in architecture design, documentation, code review, and project management—while maintaining full human oversight and control.

### Core Value Proposition

**Pilot Space is a thought-first SDLC platform** with built-in AI capabilities. Unlike traditional issue trackers that start with forms, Pilot Space starts with collaborative thinking—users brainstorm with AI in a living document, and issues emerge naturally from refined thoughts.

> **"Think first, structure later"**

| Traditional PM Tools (Ticket-First) | Pilot Space (Thought-First) |
|-------------------------------------|------------------------------|
| Start with forms → Fill fields → Submit | Start with notes → Write thoughts → AI extracts |
| Structure imposed upfront | Structure emerges from thinking |
| Manual documentation | AI-generated + human-refined documentation |
| AI bolt-on (autocomplete) | AI embedded (co-writing partner) |
| Issues are the artifact | Notes become living documentation |
| Disconnected tools | Unified workspace with GitHub & Slack integrations |
| Dashboard as home | **Note Canvas as home** |

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
| 2 | **Note-First Approach** | Start with collaborative thinking, issues emerge from refined thoughts |
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

**AI Trigger Modes (All Supported):**

| Mode | Description | Examples |
|------|-------------|----------|
| **Explicit Commands** | User-invoked via slash commands or buttons | `/ai review`, `/ai plan`, "Generate diagram" button |
| **Automatic Suggestions** | AI proactively suggests based on context | Label suggestions on issue creation, duplicate detection |
| **Event-Driven** | AI triggers on system events | PR opened → auto code review, sprint ended → retrospective |

**Trigger Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI TRIGGER MODES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  EXPLICIT COMMANDS          AUTOMATIC SUGGESTIONS               │
│  ┌─────────────────┐       ┌─────────────────┐                 │
│  │ User invokes    │       │ Context detected│                 │
│  │ /ai command     │       │ (typing, editing)│                │
│  └────────┬────────┘       └────────┬────────┘                 │
│           │                         │                           │
│           ▼                         ▼                           │
│  ┌─────────────────────────────────────────────┐               │
│  │            AI ORCHESTRATOR                   │               │
│  │  • Route to appropriate agent               │               │
│  │  • Apply context (workspace, project, user) │               │
│  │  • Execute with confidence scoring          │               │
│  └─────────────────────────────────────────────┘               │
│           ▲                         ▲                           │
│           │                         │                           │
│  ┌────────┴────────┐       ┌────────┴────────┐                 │
│  │ EVENT-DRIVEN    │       │ OUTPUT          │                 │
│  │ PR created      │       │ Suggestion +    │                 │
│  │ Sprint ended    │       │ Human review    │                 │
│  │ Issue assigned  │       │ option          │                 │
│  └─────────────────┘       └─────────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation:**
- AI suggestions are always presented for human approval
- Critical actions (merge, deploy, delete) require explicit human confirmation
- AI provides rationale and alternatives for transparency
- Users can adjust AI behavior and trigger modes per workspace/project
- Event-driven triggers are configurable (enable/disable per event type)

### 2. Note-First Approach

The primary interface is a **collaborative note canvas** where users brainstorm with AI. Issues and tasks emerge naturally from refined thinking—not from filling out forms.

```
Note Canvas (Home)  →  AI Co-Writing  →  Issue Extraction  →  Living Documentation
        ↓                    ↓                  ↓                      ↓
   Start typing        AI suggests       Rainbow-bordered       Bidirectional
    thoughts           in margin         boxes wrap text          sync
```

**Workflow:**

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│   1. CAPTURE      Open Pilot Space → Note canvas is home                  │
│                                                                            │
│   2. BRAINSTORM   AI joins via inline suggestions + margin annotations    │
│                                                                            │
│   3. REFINE       Threaded discussions clarify each thought block         │
│                                                                            │
│   4. EXTRACT      AI automatically identifies actionable items            │
│                                                                            │
│   5. WRAP         Rainbow-bordered boxes wrap source text inline          │
│                                                                            │
│   6. APPROVE      User reviews and approves issue creation                │
│                                                                            │
│   7. TRACK        Issues link back to source note (bidirectional)         │
│                                                                            │
│   8. EVOLVE       Note continues as living documentation                  │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- **Note Canvas as Home**: Default view is ready-to-write, not a dashboard
- **Threaded AI Discussions**: Each block can spawn a conversation with AI
- **Margin Annotations**: AI proactively suggests ideas (smart visibility, block-linked)
- **Automatic Issue Extraction**: AI identifies actionable items, wraps text with rainbow borders
- **Bidirectional Sync**: Notes and issues stay connected
- **Living Documentation**: Notes evolve with the project

**Enhanced UI Features (v2.3):**
- **New Note AI Prompt**: AI greeting with work history summary and recommended templates
- **Ghost Text Autocomplete**: Inline suggestions as you type (Tab to accept all, → for word-by-word)
- **Issue Detail Modal**: Quick view modal when clicking issue boxes
- **Command Palette (Cmd+P)**: Smart AI suggestions based on context
- **Full-Page Search (Cmd+K)**: Spotlight-style search across all content
- **Selection Toolbar**: Rich formatting plus AI actions (Improve, Simplify, Expand, Ask, Extract)
- **Version History Panel**: Claude Code-style snapshots with AI reasoning (collapsible, expand for AI rationale)
- **@ Mentions**: Link to notes, issues, projects, and AI agents inline with typed icons

**AI Panel & Search (v2.3):**
- **Floating Action Button (FAB)**: Bottom-right button opens AI-enabled search bar
- **AI Search Bar**: Keyword + semantic search, AI answer first, search results as rows
- **Collapsible AI Panel**: Toggle panel at bottom with thin bar + pulse dot (●) when collapsed
- **Panel Input**: Free-form questions with static + dynamic action chips
- **Claude Code-Style Status**: Detailed AI activity indicators ("Searching codebase...", "Generating diagram...")
- **Full Keyboard Navigation**: Arrow keys, Tab, number keys for chip selection

**Note Management (v2.3):**
- **Virtual Scroll**: Performance optimization for long notes (1000+ blocks)
- **Auto-Generated TOC**: Click-to-scroll + highlight sync for current section
- **Rich Header**: Note metadata, word count, AI reading time estimate ("5 min • learn how to...")
- **Margin Annotations**: Block-linked AI suggestions with resizable margin, edge icon toggle
- **Interactive Issue Extraction**: Highlight source text, show draft issue inline, edit before accept
- **AI Similar Notes**: After note creation, AI shows related notes with guidance

**Template System (v2.3):**
- **Template Gallery**: System + User + AI-generated templates
- **Conversational Filling**: AI fills template hints from natural language input
- **Split View Modal**: Conversation on left, live preview on right
- **Skip Button**: Leave template hints empty if desired
- **Auto-Create**: Note created automatically when conversation completes

**Graph View (v2.3):**
- **Force-Directed Layout**: Current note at center, highlighted
- **Cluster Labels**: Grouped by project name
- **Full Navigation**: Pan/zoom + click focus + mini-map
- **AI Pattern Detection**: AI identifies connection patterns and suggests links
- **Preview + AI Explanation**: First click shows preview, second click opens with AI analysis
- **Full Metrics**: Connection count, cluster count, orphaned note detection

**Notification Center (v2.3):**
- **Sidebar Section**: Smart preview with AI-prioritized inbox
- **Priority Labels**: AI-assigned tags (Urgent, Important, FYI)
- **Smart Text Count**: "3 new" instead of raw numbers
- **Configurable Triggers**: All notification sources user-configurable
- **Delayed Mark-as-Read**: Brief delay before auto-marking as read

**Workspace Management (v2.3):**
- **Header Dropdown**: Workspace switcher with stats (note count, member count)
- **Tabbed Settings**: General, Members, API Keys, Activity organized in tabs
- **Simple Member List**: Role management without complex hierarchy
- **Real-Time API Key Validation**: Immediate feedback on key entry
- **Activity Log**: Basic events for all members (created, edited, deleted)
- **Workspace-Level API Keys**: All AI features configured at workspace scope

**Onboarding (v2.3):**
- **Sample Project**: "Product Launch" themed sample with realistic data
- **Pre-Populated Content**: Sample notes, issues, and AI threads
- **Progressive Tooltips**: Two-stage discovery (brief → detailed on hover)
- **Comprehensive Shortcut Discovery**: Tooltips + Command palette + Shortcut guide + Contextual hints

> See [DD-013: Note-First Collaborative Workspace](./DESIGN_DECISIONS.md#dd-013-note-first-collaborative-workspace) for core rationale.
> See [DD-014 through DD-054](./DESIGN_DECISIONS.md) for detailed UI clarifications.

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
│         │PostgreSQL│      │  Redis  │        │Supabase │              │
│         │+ pgvector│      │ (Cache) │        │ Queues  │              │
│         └────────┘        └─────────┘        └─────────┘              │
│                                 │                                       │
│                                 ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BACKGROUND WORKERS                            │   │
│  │                    (Supabase Edge Functions)                     │   │
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
│  │ GitHub  │  │  Slack  │  │   LLM   │  │Supabase │                    │
│  │   API   │  │   API   │  │Provider │  │ Storage │                    │
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
| **Queue** | Supabase Queues (pgmq + pg_cron) | Async tasks, AI job processing |
| **Storage** | Supabase Storage | S3-compatible object storage with RLS |
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
│  │  │  (OpenAI)   │  │ (pgvector)  │  │  (Hybrid)   │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  │                                                            │ │
│  │  Hybrid Retrieval: RRF Scoring (DD-057)                   │ │
│  │  • Semantic: pgvector HNSW cosine similarity              │ │
│  │  • Graph: KnowledgeGraphRelationship traversal            │ │
│  │  • Fusion: Reciprocal Rank Fusion (k=60)                  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐ │
│  │               LLM PROVIDERS (BYOK)                         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │ │
│  │  │  OpenAI  │ │Anthropic │ │  Google  │ │  Azure   │     │ │
│  │  │  GPT-4o  │ │  Claude  │ │  Gemini  │ │  OpenAI  │     │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │ │
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
- [ ] Notifications system (AI-prioritized with label tags)

**Note-First Editor**
- [ ] Note canvas as home (ready-to-write default)
- [ ] Ghost text autocomplete (Tab/→ to accept)
- [ ] Margin annotations (block-linked, resizable)
- [ ] Rainbow-bordered issue extraction with inline review
- [ ] Version history panel (Claude Code-style with AI reasoning)
- [ ] Virtual scroll for long notes (1000+ blocks)
- [ ] Auto-generated TOC with sync highlighting
- [ ] Rich header with word count and AI reading time

**AI Features (BYOK - Bring Your Own Key)**
- [ ] AI-enhanced issue creation (title, description, labels, priority)
- [ ] Smart task decomposition from feature descriptions
- [ ] AI PR Review (architecture + code quality + security)
- [ ] Documentation generation from code/issues
- [ ] Diagram generation (Mermaid)
- [ ] Keyword + semantic search across workspace content
- [ ] Duplicate detection
- [ ] Collapsible AI panel (bottom toggle with thin bar)
- [ ] FAB with AI search bar
- [ ] Conversational template filling

**Knowledge Features**
- [ ] Force-directed graph view (note connections)
- [ ] AI-suggested tags
- [ ] Template gallery (System + User + AI-generated)
- [ ] @ Mentions with inline dropdown
- [ ] Hybrid retrieval with RRF scoring (semantic + graph fusion)

**Integrations**
- [ ] GitHub: PR linking, commit tracking, AI review comments
- [ ] Slack: Notifications, slash commands, issue creation
- [ ] Webhooks (outbound)

**MVP Scope Exclusions**
- Offline editing (infrastructure complexity)
- Note sharing/export (focus on core workflow)
- Focus/Zen mode (standard layout sufficient)
- Mobile-specific features (desktop-first)
- Real-time collaboration (standard editing with autosave)
- Saved views/filters (basic filtering sufficient)
- Quick capture from anywhere (editor-focused)
- Inline comments from team members (Phase 2)

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
      - SUPABASE_URL=http://supabase:8000
      - SUPABASE_ANON_KEY=...
      - SUPABASE_SERVICE_ROLE_KEY=...

  # Background workers handled by Supabase Edge Functions
  # No separate worker container needed

  supabase:
    # Use Supabase CLI for local development:
    # supabase start
    # This starts: PostgreSQL, Auth, Storage, Realtime, Edge Functions
    image: supabase/postgres:15.1.0
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

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

**Core Philosophy:**
1. **Thought-First, Not Ticket-First**: Users brainstorm with AI in notes; issues emerge naturally (vs. Linear/Jira's form-first approach)
2. **AI-Native Architecture**: AI is not a bolt-on but a core platform capability embedded in the writing experience
3. **Living Documentation**: Notes stay connected to issues bidirectionally, evolving with the project
4. **Open Source + Self-Hosted**: Full control over data and customization
5. **Human-in-the-Loop**: AI augments, never replaces human judgment

**AI Experience:**
6. **Ghost Text AI**: Real-time inline suggestions as you type (like Copilot for project management)
7. **Always-Available AI Panel**: Bottom toggle panel with thin bar + pulse dot for AI suggestions
8. **FAB with AI Search**: Bottom-right button opens hybrid keyword + semantic search with AI answers
9. **Smart Command Palette**: Context-aware AI suggestions in Cmd+P based on current work
10. **Version History with AI Reasoning**: Claude Code-style snapshots showing what AI changed and why

**Knowledge Management:**
11. **Force-Directed Graph View**: Visualize note connections like Obsidian, with AI pattern detection
12. **AI-Suggested Tags**: Automatic tag suggestions based on content analysis
13. **Conversational Templates**: AI fills template hints from natural language descriptions
14. **AI-Prioritized Notifications**: Smart inbox with label tags (Urgent, Important, FYI)

**Technical Excellence:**
15. **SDLC-Focused AI**: Purpose-built for software development workflows
16. **Architecture-Aware**: Understands code structure, not just text
17. **Virtual Scroll**: High performance for notes with 1000+ blocks
18. **Auto-Generated TOC**: Click-to-scroll navigation with sync highlighting

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

*Document Version: 1.5*
*Last Updated: 2026-01-21*
*Author: Pilot Space Team*
*Changes: Added v2.3 UI features from Q&A clarifications - FAB with AI search, collapsible AI panel, force-directed graph view, template system with conversational filling, AI-prioritized notification center, sample project onboarding, virtual scroll, auto-generated TOC, rich header, interactive issue extraction, workspace management with API key validation, comprehensive shortcut discovery, and expanded differentiators (18 total)*
