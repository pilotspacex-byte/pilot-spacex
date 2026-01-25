<!-- Note: `toon` code blocks are a compact table notation format. Each line represents a row with fields separated by commas. -->

# Implementation Plan: Pilot Space MVP

**Branch**: `001-pilot-space-mvp` | **Date**: 2026-01-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-pilot-space-mvp/spec.md` , plus architecture docs `/docs/architect/README.md` , and constitution `/ .specify/memory/constitution.md` , ui-design-spec.md
**Updated**: Session 2026-01-23 - Added optimized prompt templates via `/prompt-template-optimizer`

## Summary

Pilot Space MVP is an AI-augmented SDLC platform implementing a "Note-First" workflow—a **collaborative thinking space** where users write rough ideas, AI expert agents help clarify ambiguous concepts through probing questions, and **explicit root issues emerge from implicit requests**. The platform provides comprehensive project management (issues, cycles, modules, pages) enhanced with AI capabilities (smart issue creation, task decomposition, PR review, documentation generation, diagram creation) using a BYOK (Bring Your Own Key) model for LLM providers. MVP integrations are limited to GitHub (PR linking, commits, AI review) and Slack (notifications, slash commands).

**Core Differentiator**: Note canvas as the default home view, not a dashboard. AI acts as an **expert clarification partner** that helps users discover what they're actually trying to solve, not just a bolt-on autocomplete feature.

**Key Value Transformation**: Vague request → AI probing questions → Explicit root issues (e.g., "We need to change auth" → security vulnerability + compliance requirement + migration plan)

## Technical Context

**Language/Version**: Python 3.12+ (Backend), TypeScript 5.x (Frontend)
**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- Frontend: Next.js 14+, React 18, MobX + TanStack Query, TailwindCSS, TipTap/ProseMirror
- AI: Claude Agent SDK for orchestration
**Platform**: Supabase (Auth, Storage, Queues, Database)
- Auth: Supabase Auth (GoTrue) with RLS for authorization
- Database: PostgreSQL 16+ with pgvector (HNSW indexing)
- Queue: Supabase Queues (pgmq + pg_cron)
- Storage: Supabase Storage (S3-compatible)
- Cache: Redis (AI response caching)
- Search: Meilisearch (typo-tolerant)
**Testing**: pytest (backend), Vitest (frontend), Playwright (e2e)
**Target Platform**: Linux server (containerized), Modern browsers (Chrome, Firefox, Safari, Edge - latest 2 versions)
**Project Type**: Web application (frontend + backend)

**Frontend Performance Targets**:
```toon
perfTargets[6]{metric,target}:
  First Contentful Paint (FCP),<1.5s
  Largest Contentful Paint (LCP),<2.5s
  Time to Interactive (TTI),<3s
  Cumulative Layout Shift (CLS),<0.1
  Interaction to Next Paint (INP),<100ms
  Note canvas 1000+ blocks,60fps (virtualized)
```

**Architecture Patterns**:
- Backend: CQRS-lite (Command/Query separation without event sourcing)
- Frontend: Feature-based MobX stores with React Context providers
- AI Streaming: SSE via FastAPI StreamingResponse
- Note Storage: JSONB (TipTap native format)
- Pagination: Cursor-based for stable pagination
- UUID Generation: Database-generated via `gen_random_uuid()`

**Performance Goals**:
```toon
perfGoals[6]{metric,target}:
  API read ops,p95 <500ms
  API write ops,p95 <1s
  AI ghost text,<2s after 500ms typing pause
  AI code review,<5min after PR creation
  Search (10k items),<2s
  Note canvas 1000+ blocks,60fps
```

**Constraints**:
```toon
constraints[6]{constraint,value}:
  Uptime SLA,99.5% (~3.6h/month downtime)
  RTO,4 hours
  Accessibility,WCAG 2.1 Level AA
  Concurrent users/workspace,100 without degradation
  Concurrent edit strategy,Last-write-wins (no realtime collab MVP)
  Team size per workspace,5-100 members
```

**MVP Scope (P0 + P1)**:
- Issue volumes: up to 50,000 per workspace
- **6 user stories** (US-01, US-02, US-03, US-04, US-12, US-18) with 60 acceptance scenarios
- ~80 functional requirements, 18 non-functional requirements
- 7 MVP AI agents (GhostText, MarginAnnotation, PRReview, AIContext, IssueExtractor, DuplicateDetector, AssigneeRecommender)
- Infrastructure: 2-3 services (Supabase + FastAPI + Next.js)

**Future Phases**:
- Phase 2 (P2): 9 user stories → See `specs/002-pilot-space-phase2/`
- Phase 3 (P3): 3 user stories → See `specs/003-pilot-space-phase3/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: AI-Human Collaboration First ✅
```toon
principleI[5]{requirement,implementation,status}:
  AI suggestions for human approval,All AI features show suggestions user accepts/rejects/modifies,✅
  Critical actions require confirmation,Delete/merge/publish require approval per DD-003,✅
  AI provides rationale + alternatives,Confidence tags + percentage tooltips per DD-048,✅
  Configurable AI behavior,Project-level AI autonomy settings,✅
  Event-driven triggers configurable,Trigger enable/disable per event type,✅
```

### Principle II: Note-First Approach ✅
```toon
principleII[4]{requirement,implementation,status}:
  Collaborative thinking space,Note canvas as home with AI expert agents for clarification,✅
  AI-assisted clarification,AI asks probing questions helps extract explicit issues from implicit requests,✅
  Implicit → Explicit extraction,AI transforms vague requests into categorized root issues (🔴/🟡/🟢),✅
  Related notes linked to issues,Bidirectional sync between notes and extracted issues (DD-013),✅
```

### Principle III: Documentation-Third Approach ✅
```toon
principleIII[3]{requirement,implementation,status}:
  Auto-generated API documentation,AI Documentation Generator from code/OpenAPI,✅
  Living documentation updates with code,PR merge triggers doc refresh,✅
  Architecture diagram generation,AI Diagram Generator (Mermaid PlantUML C4),✅
```

### Principle IV: Task-Centric Workflow ✅
```toon
principleIV[4]{requirement,implementation,status}:
  Feature decomposition into tasks,AI Task Decomposition (PS-002),✅
  AI-suggested acceptance criteria,Generated with task breakdown,✅
  Task dependencies identified,AI identifies and marks task dependencies,✅
  Traceability to parent feature,Sub-issues linked to parent feature,✅
```

### Principle V: Collaboration & Knowledge Sharing ✅
```toon
principleV[4]{requirement,implementation,status}:
  Pattern Library,AI Pattern Matcher Agent,✅
  ADR support,AI-assisted ADRs (Phase 2 but structure in MVP),⚠️ Phase 2
  Expertise mapping,AI assignee recommendations based on code ownership,✅
  Knowledge Graph,Semantic search + graph view (DD-037),✅
```

### Principle VI: Agile Integration ✅
```toon
principleVI[3]{requirement,implementation,status}:
  AI-enhanced sprint planning,Velocity burndown metrics (PS-009 Phase 2),⚠️ Basic in MVP
  Retrospective insights,AI Retrospective Analyst (Phase 2),⚠️ Phase 2
  Blocker detection,Issue state tracking with blocked status,✅
```

### Principle VII: Notation & Standards ✅
```toon
principleVII[3]{requirement,implementation,status}:
  UML Generation,Mermaid + PlantUML support (DD-012),✅
  C4 Model support,All 4 levels via C4-PlantUML,✅
  Mermaid integration,Default format inline rendering,✅
```

### Technology Standards ✅
```toon
techStandards[13]{requirement,implementation,status}:
  FastAPI + SQLAlchemy 2.0 async,Per DD-001,✅
  Pydantic v2 for validation,All API validation,✅
  Next.js 14+ + React 18 + TypeScript,Frontend stack,✅
  MobX + TanStack Query,Feature-based stores + server state,✅
  TailwindCSS for styling,Per constitution,✅
  PostgreSQL 16+ with pgvector,Supabase soft deletion embeddings,✅
  BYOK only for AI,No local LLM support per DD-002,✅
  Redis for cache,AI response caching,✅
  Supabase Queues,pgmq + pg_cron for async tasks,✅
  Supabase Auth,GoTrue + RLS for authorization,✅
  Supabase Storage,S3-compatible file storage,✅
  Meilisearch for search,Typo-tolerant search,✅
  Sigma.js + react-sigma,Knowledge graph visualization *(Phase 2 US-14)*,✅
```

### Quality Gates ✅
```toon
qualityGates[10]{gate,implementation,status}:
  Lint passes,ruff (Python) ESLint (TypeScript),✅ Planned
  Type check passes,pyright (Python) tsc (TypeScript) strict mode,✅ Planned
  Tests pass coverage >80%,pytest Jest,✅ Planned
  No N+1 queries,SQLAlchemy query monitoring,✅ Planned
  No blocking I/O in async,Code review enforcement,✅ Planned
  No TODOs/mocks in production,Pre-commit hooks,✅ Planned
  Secrets not in code,Pre-commit secret scanning,✅ Planned
  Input validation at API boundaries,Pydantic v2,✅ Planned
  OWASP Top 10 compliance,Security review checklist,✅ Planned
  File size limit 700 lines,Pre-commit hooks,✅ Planned
```

### UI/UX Compliance ✅
```toon
uiuxCompliance[11]{requirement,implementation,status}:
  Design system tokens,TailwindCSS config with color spacing typography,✅ Planned
  WCAG 2.2 AA accessibility,axe-core automated testing + manual review,✅ Planned
  Color contrast 4.5:1,Warm neutrals palette verified,✅ Planned
  Focus visibility,3px primary ring on all interactive elements,✅ Planned
  Keyboard navigation,All features keyboard accessible,✅ Planned
  Screen reader support,ARIA labels roles live regions,✅ Planned
  Touch targets 44x44px,Minimum touch target enforcement,✅ Planned
  Responsive breakpoints,sm/md/lg/xl/2xl breakpoint coverage,✅ Planned
  Motion preferences,Respects prefers-reduced-motion,✅ Planned
  AI content labeling,100% AI content visually labeled,✅ Planned
  Performance targets,FCP <1.5s LCP <2.5s TTI <3s CLS <0.1 INP <100ms,✅ Planned
```

**Pre-Design Gate Status**: ✅ PASS (No blocking violations)

## Project Structure

### Documentation (this feature)

```text
specs/001-pilot-space-mvp/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── ui-design-spec.md    # UI/UX design specification
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── openapi.yaml     # REST API specification
├── checklists/          # Validation checklists
│   └── requirements.md  # Requirements traceability
├── tasks.md             # Phase 2 output (/speckit.tasks command)
└── sdlc/                # SDLC Documentation Suite
    ├── README.md        # Documentation index and navigation
    ├── 01-requirements/ # PRD, RTM, NFRs, Acceptance Criteria
    ├── 02-architecture/ # C4 diagrams (L1-L3)
    ├── 03-api/          # API developer guide
    ├── 04-ai-agents/    # AI agent reference (16 agents)
    ├── 05-development/  # Contributing, testing, local setup
    ├── 06-operations/   # Deployment, incident response
    ├── 07-user-guide/   # Getting started guide
    └── 08-governance/   # Documentation governance
```

### Source Code (repository root)

```text
# Web application structure (frontend + backend)

backend/
├── src/
│   ├── pilot_space/           # Main package
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── config.py          # Configuration management
│   │   ├── dependencies.py    # Dependency injection
│   │   │
│   │   ├── api/               # API layer (presentation)
│   │   │   ├── v1/
│   │   │   │   ├── routers/   # FastAPI routers
│   │   │   │   │   ├── workspaces.py
│   │   │   │   │   ├── projects.py
│   │   │   │   │   ├── issues.py
│   │   │   │   │   ├── notes.py
│   │   │   │   │   ├── pages.py
│   │   │   │   │   ├── cycles.py
│   │   │   │   │   ├── modules.py
│   │   │   │   │   ├── ai.py          # AI feature endpoints
│   │   │   │   │   ├── integrations.py
│   │   │   │   │   └── webhooks.py
│   │   │   │   ├── schemas/   # Pydantic request/response models
│   │   │   │   └── middleware/
│   │   │   └── webhooks/      # Inbound webhook handlers
│   │   │
│   │   ├── domain/            # Domain layer (business logic)
│   │   │   ├── models/        # Domain entities
│   │   │   │   ├── workspace.py
│   │   │   │   ├── project.py
│   │   │   │   ├── issue.py
│   │   │   │   ├── note.py
│   │   │   │   ├── page.py
│   │   │   │   ├── cycle.py
│   │   │   │   ├── module.py
│   │   │   │   ├── user.py
│   │   │   │   ├── label.py
│   │   │   │   ├── activity.py
│   │   │   │   ├── ai_context.py
│   │   │   │   └── template.py
│   │   │   └── events/        # Domain events
│   │   │
│   │   ├── application/       # Application layer (CQRS-lite)
│   │   │   └── services/      # Application services (CQRS-lite)
│   │   │       ├── workspace_service.py
│   │   │       ├── project_service.py
│   │   │       ├── issue_service.py
│   │   │       ├── note_service.py
│   │   │       ├── cycle_service.py
│   │   │       └── search_service.py
│   │   │
│   │   ├── ai/                # AI agent layer
│   │   │   ├── orchestrator.py    # Task router + context manager
│   │   │   ├── providers/         # LLM provider adapters
│   │   │   │   ├── base.py
│   │   │   │   ├── openai.py
│   │   │   │   ├── anthropic.py
│   │   │   │   ├── google.py
│   │   │   │   └── azure.py
│   │   │   ├── agents/            # AI agents
│   │   │   │   ├── pr_review.py
│   │   │   │   ├── doc_generator.py
│   │   │   │   ├── task_planner.py
│   │   │   │   ├── diagram_generator.py
│   │   │   │   ├── knowledge_search.py
│   │   │   │   ├── ai_context.py
│   │   │   │   └── ghost_text.py
│   │   │   ├── prompts/           # Prompt templates
│   │   │   └── rag/               # RAG pipeline
│   │   │       ├── indexer.py
│   │   │       ├── retriever.py
│   │   │       └── embeddings.py
│   │   │
│   │   ├── infrastructure/    # Infrastructure layer
│   │   │   ├── database/
│   │   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   │   ├── repositories/  # Data access
│   │   │   │   └── migrations/    # Alembic migrations
│   │   │   ├── cache/
│   │   │   │   └── redis.py
│   │   │   ├── queue/
│   │   │   │   └── supabase_queue.py  # Supabase Queues (pgmq)
│   │   │   ├── search/
│   │   │   │   └── meilisearch.py
│   │   │   ├── storage/
│   │   │   │   └── supabase_storage.py  # Supabase Storage
│   │   │   └── auth/
│   │   │       └── supabase_auth.py    # Supabase Auth (GoTrue)
│   │   │
│   │   └── integrations/      # External integrations
│   │       ├── github/
│   │       │   ├── client.py
│   │       │   ├── webhooks.py
│   │       │   └── sync.py
│   │       └── slack/
│   │           ├── client.py
│   │           ├── commands.py
│   │           └── notifications.py
│   │
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── contract/

frontend/
├── src/
│   ├── app/                   # Next.js app router (or React Router)
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Home (Note Canvas)
│   │   ├── (workspace)/
│   │   │   ├── projects/
│   │   │   ├── issues/
│   │   │   ├── cycles/
│   │   │   ├── modules/
│   │   │   ├── pages/
│   │   │   └── settings/
│   │   └── public/            # Public views (merged Space app)
│   │
│   ├── components/
│   │   ├── ui/                # Base UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Tooltip.tsx
│   │   │   └── ...
│   │   ├── editor/            # TipTap editor components
│   │   │   ├── NoteCanvas.tsx
│   │   │   ├── GhostText.tsx
│   │   │   ├── MarginAnnotations.tsx
│   │   │   ├── IssueExtractionPanel.tsx
│   │   │   ├── ThreadedDiscussion.tsx
│   │   │   └── SelectionToolbar.tsx
│   │   ├── issues/
│   │   │   ├── IssueDetail.tsx
│   │   │   ├── IssueBoard.tsx
│   │   │   ├── IssueList.tsx
│   │   │   ├── IssueQuickView.tsx
│   │   │   └── AIContext.tsx
│   │   ├── navigation/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── CommandPalette.tsx
│   │   │   ├── SearchModal.tsx
│   │   │   └── FAB.tsx
│   │   ├── ai/
│   │   │   ├── AIPanel.tsx
│   │   │   ├── ConfidenceTags.tsx
│   │   │   ├── AIStatusIndicator.tsx
│   │   │   └── ArtifactPreview.tsx
│   │   └── integrations/
│   │
│   ├── stores/                # MobX stores
│   │   ├── RootStore.ts
│   │   ├── WorkspaceStore.ts
│   │   ├── ProjectStore.ts
│   │   ├── IssueStore.ts
│   │   ├── NoteStore.ts
│   │   ├── AIStore.ts
│   │   └── UIStore.ts
│   │
│   ├── services/              # API client services
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   └── ai.ts
│   │
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utilities
│   └── styles/                # TailwindCSS configuration
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/

# Infrastructure
infra/
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── kubernetes/
└── terraform/

# Configuration
├── pyproject.toml             # Python dependencies (uv)
├── pnpm-workspace.yaml        # Frontend monorepo
├── .env.example
└── alembic.ini
```

**Structure Decision**: Web application structure selected per spec requirements (React frontend + FastAPI backend). Clean architecture layers (presentation → domain → infrastructure) with AI as a cross-cutting concern. Domain-driven design for core entities.

## UI Component Architecture

*Reference: `specs/001-pilot-space-mvp/ui-design-spec.md` v3.2.0*

### Design System Foundation

**Visual Identity**: Warm, Capable, Collaborative (Section 3)
- Inspirations: Craft (rich layered surfaces), Apple (squircle corners, frosted glass), Things 3 (natural color accents)
- NOT: Cold enterprise software, generic shadcn/ui defaults, AI as separate "system"

**Color System (Section 4.1)**:
```toon
colorSystem[4]{token,light,dark,usage}:
  Background,#FDFCFA,#1A1A1A,Warm off-white base
  Primary,#29A386,#29A386,Teal-green for actions
  AI Color,#6B8FAD,#6B8FAD,Dusty blue for AI elements
  Foreground,#171717,#EDEDED,Primary text
```

**Typography (Section 4.2)**:
```toon
typography[2]{type,fontFamily,fallback}:
  UI Text,Geist,system-ui -apple-system sans-serif
  Code,Geist Mono,SF Mono Monaco monospace
```

Type Scale: `text-xs` (11px) → `text-3xl` (30px), Geist font family

**Spacing System (Section 4.3)**: 4px grid base
- `space-1` (4px) to `space-16` (64px)
- Generous whitespace for calm, spacious layouts

**Border Radius - Apple Squircle Style (Section 4.4)**:
```toon
borderRadius[4]{token,value,usage}:
  rounded-sm,6px,Small elements badges
  rounded,10px,Buttons inputs
  rounded-lg,14px,Cards containers
  rounded-xl,18px,Modals large cards
```

**Shadows (Section 4.5)**: Warm-tinted, layered approach for natural depth
**Visual Textures (Section 4.6)**: Subtle noise overlay (2% opacity), frosted glass for overlays

### Component Library Mapping

**Base Components (shadcn/ui)**:
```toon
baseComponents[7]{component,location,uiSpecRef}:
  Button,components/ui/Button.tsx,Section 5.1: Variants + Sizes
  Card,components/ui/Card.tsx,Section 5.2: Interactive cards
  Badge,components/ui/Badge.tsx,Section 5.3: State/priority badges
  Input,components/ui/Input.tsx,Section 5.4: 38px height 10px radius
  Dialog/Modal,components/ui/Modal.tsx,Section 5.5: Frosted glass 18px radius
  Skeleton,components/ui/Skeleton.tsx,Section 5.6: Diagonal shimmer
  Tooltip,components/ui/Tooltip.tsx,Section 10.4: Progressive tooltips
```

**Note Canvas Components (Section 7)**:
```toon
noteCanvasComponents[8]{component,location,purpose}:
  NoteCanvas,components/editor/NoteCanvas.tsx,Main block-based editor (720px max-width)
  OutlineTree,components/editor/OutlineTree.tsx,Left sidebar navigation (220px)
  MarginAnnotations,components/editor/MarginAnnotations.tsx,Right-side AI notes (150-350px resizable)
  GhostText,components/editor/GhostText.ts,TipTap extension for inline suggestions
  IssueExtractionPanel,components/editor/IssueExtractionPanel.tsx,Rainbow-bordered issue boxes
  ThreadedDiscussion,components/editor/ThreadedDiscussion.tsx,Per-block AI discussions
  RichNoteHeader,components/editor/RichNoteHeader.tsx,Metadata display (Section 7.5)
  AutoTOC,components/editor/AutoTOC.tsx,Auto-generated table of contents (Section 7.6)
```

**AI Components (Section 8)**:
```toon
aiComponents[7]{component,location,purpose}:
  GhostTextAutocomplete,components/ai/GhostTextAutocomplete.tsx,Inline AI suggestions (Section 8.2)
  SelectionToolbar,components/ai/SelectionToolbar.tsx,Rich + AI actions (Section 8.3)
  VersionHistoryPanel,components/ai/VersionHistoryPanel.tsx,Document versions (Section 8.4)
  MentionDropdown,components/ai/MentionDropdown.tsx,@ mention system (Section 8.5)
  CollapsibleAIPanel,components/ai/CollapsibleAIPanel.tsx,Bottom AI panel (Section 8.6)
  ConfidenceTags,components/ai/ConfidenceTags.tsx,AI confidence display (Section 10.5)
  AIStatusIndicator,components/ai/AIStatusIndicator.tsx,Status text during operations
```

**Navigation Components (Section 9)**:
```toon
navComponents[5]{component,location,purpose}:
  CommandPalette,components/navigation/CommandPalette.tsx,Cmd+P palette (Section 9.1)
  SearchModal,components/navigation/SearchModal.tsx,Cmd+K search (Section 9.2)
  FAB,components/navigation/FAB.tsx,AI-enabled search button (Section 8.7)
  Sidebar,components/navigation/Sidebar.tsx,Main navigation (260px expanded 60px collapsed)
  NotificationCenter,components/navigation/NotificationCenter.tsx,AI-prioritized inbox (Section 10.7)
```

**Issue Components**:
```toon
issueComponents[5]{component,location,purpose}:
  IssueCard,components/issues/IssueCard.tsx,Card with state priority AI attribution
  IssueDetail,components/issues/IssueDetail.tsx,Full issue view
  IssueBoard,components/issues/IssueBoard.tsx,Kanban board view
  IssueList,components/issues/IssueList.tsx,List view
  AIContext,components/issues/AIContext.tsx,AI context panel (US-12)
```

### TipTap Extension Organization

```text
frontend/src/features/notes/editor/extensions/
├── GhostTextExtension.ts        # AI ghost text (500ms trigger, 50 tokens max)
├── MarginAnnotationExtension.ts # Right margin AI annotations
├── IssueLinkExtension.ts        # Rainbow-bordered issue boxes
├── CodeBlockExtension.ts        # Syntax highlighting + language selector + copy
├── MentionExtension.ts          # @mentions for notes, issues, AI
├── SlashCommandExtension.ts     # / commands for AI actions
└── index.ts                     # Export all extensions
```

## Design System Integration

*Detailed specifications: ui-design-spec.md Sections 3-4*

### Color Tokens

**Issue State Colors (Section 4.1.4)**:
```toon
issueStateColors[6]{state,color,cssVar}:
  Backlog,Warm Gray,--state-backlog
  Todo,Soft Blue,--state-todo
  In Progress,Amber,--state-in-progress
  In Review,Soft Purple,--state-in-review
  Done,Teal-Green,--state-done
  Cancelled,Warm Red,--state-cancelled
```

**Priority Colors (Section 4.1.5)**:
```toon
priorityColors[5]{priority,color,indicator}:
  Urgent,Warm Red #D9534F,4 vertical bars
  High,Amber #D9853F,3 vertical bars
  Medium,Gold #C4A035,2 vertical bars
  Low,Soft Blue #5B8FC9,1 vertical bar
  None,Warm Gray #9C9590,Horizontal line
```

**AI Confidence Tags (Section 10.5)**:
```toon
confidenceTags[4]{tag,background,border,icon}:
  Recommended,Primary 10%,Primary 30%,★ (filled star)
  Default,Muted,Border,None
  Current,AI blue 10%,AI blue 30%,None
  Alternative,Transparent,Border dashed,None
```

### Typography Rules

- Use `text-balance` on headings for better line breaks
- Use `tabular-nums` for metrics, counters, and tables
- Use curly quotes (`""`), not straight quotes
- Use proper ellipsis (`...`), not three periods
- AI voice uses regular weight with italic style

### Animation & Transitions

```toon
animations[6]{element,behavior,duration}:
  Button Hover,Scale up 2% elevated shadow,150ms
  Card Hover,Translate up 2px scale 1%,200ms
  Ghost Text,Fade-in slight left translation,150ms
  Loading Skeleton,Diagonal shimmer,1.5s infinite
  Rainbow Border (new issue),Hue-rotate animation,2s
  Focus Ring,3px primary ring at 30% opacity,instant
```

### Responsive Breakpoints

```toon
breakpoints[5]{name,value,usage}:
  sm,640px,Mobile landscape
  md,768px,Tablet portrait
  lg,1024px,Tablet landscape TOC collapse
  xl,1280px,Desktop
  2xl,1536px,Large desktop
```

**Mobile Adaptations (< 768px)**:
- Sidebar: Hidden, accessible via hamburger menu
- Note Canvas: Full width, margin annotations below
- Command Palette: Full screen modal
- Cards: Stack vertically

## Accessibility Implementation

*WCAG 2.2 AA Compliance - ui-design-spec.md Section 11*

### Compliance Checklist

```toon
a11yCompliance[6]{requirement,implementation,status}:
  Color Contrast,4.5:1 for text 3:1 for UI components,Planned
  Focus Visibility,3px ring on all interactive elements,Planned
  Keyboard Navigation,All features accessible via keyboard,Planned
  Screen Reader,ARIA labels roles live regions,Planned
  Motion,Respects prefers-reduced-motion,Planned
  Touch Targets,Minimum 44x44px,Planned
```

### Keyboard Navigation Requirements

**Global Shortcuts**:
```toon
globalShortcuts[8]{shortcut,action}:
  Cmd+P,Open command palette
  Cmd+K,Open search
  Cmd+N,Create new note
  C,Create new issue (when not in text input)
  G H,Go to Home
  G I,Go to Issues
  G C,Go to Cycles
  ?,Show keyboard shortcut guide
  /,Open slash command menu (in editor)
```

**Editor Shortcuts**:
```toon
editorShortcuts[5]{shortcut,action}:
  Tab,Accept ghost text
  Right Arrow,Accept word-by-word
  Escape,Dismiss ghost text
  Cmd+Shift+Up/Down,Move selected blocks
  Cmd+Z,Undo (extended stack)
```

### Screen Reader Requirements (ARIA Patterns)

```toon
ariaPatterns[7]{component,pattern}:
  Modal,role=dialog aria-modal=true
  Dropdown,aria-expanded aria-haspopup
  Tabs,role=tablist role=tab role=tabpanel
  Toast,role=alert aria-live=polite
  Loading,aria-busy=true aria-describedby
  Command Palette,role=combobox aria-autocomplete=list
  Issue Board,role=application drag-drop announcements
```

### Focus Management Patterns

```toon
focusPatterns[5]{pattern,implementation}:
  Modal Focus Trap,Focus trapped within modal restored on close
  Skip Links,Skip to main content link at top visible on focus
  Focus Restoration,Focus returns to trigger element after modal/panel close
  Roving Tabindex,List navigation uses single tab stop with arrow keys
  Live Regions,AI status updates announced via aria-live=polite
```

### Semantic HTML Requirements

- Use proper heading hierarchy (h1 → h2 → h3)
- Use button for actions, links for navigation
- Use lists for groups of related items
- Use tables for tabular data with proper headers
- Use landmarks (`<main>`, `<nav>`, `<aside>`) for page regions

## Complexity Tracking

> No Constitution Check violations requiring justification.

```toon
complexityDecisions[9]{decision,rationale,rejected}:
  Separate AI layer,AI agents are cross-cutting need unified orchestration,Inline AI calls in services - harder to maintain/test
  MobX + TanStack Query,Complex UI state (MobX) + server state (TanStack Query),Context API only - insufficient for real-time updates
  pgvector for embeddings,Native PostgreSQL via Supabase no separate vector DB,Pinecone/Weaviate - additional infrastructure
  Meilisearch vs ElasticSearch,Simpler typo-tolerant smaller footprint,ElasticSearch - over-engineered for MVP scale
  Supabase platform,Unified Auth/Storage/Queues reduces services 10→3,Separate Keycloak/S3/RabbitMQ - more infrastructure
  CQRS-lite,Command/Query separation prepares for read replicas,Full CQRS with event sourcing - over-complex for MVP
  JSONB for notes,TipTap native format atomic document,Separate blocks table - N+1 queries complex sync
  Sigma.js,WebGL performance for 50K+ nodes *(Phase 2 - Knowledge Graph US-14)*,Cytoscape/D3 - slower for large graphs
  Cursor-based pagination,Stable with real-time updates,Offset pagination - unstable with live data
```

---

## User Story Implementation Breakdown

This section maps each user story to its specific clarifications and implementation requirements.

### US-01: Note-First Collaborative Writing (P0)

**Spec Reference**: User Story 1 | **Priority**: P0 (Critical Path) | **Acceptance Scenarios**: 22

**UI Design References**: ui-design-spec.md Sections 7-8
- Note Canvas Layout: Section 7 (Layout Architecture)
- Document Canvas: Section 7.2 (720px max-width, 32px padding)
- Margin Annotations: Section 7.3 (200px width, 150-350px resizable, AI muted background)
- Ghost Text: Section 8.2 (40% opacity, italic, 150ms fade-in, 500ms trigger)
- Issue Extraction: Section 7.4 (Rainbow-bordered boxes, 2px gradient border)
- Rich Note Header: Section 7.5 (created date, word count, reading time, topics)
- Auto-TOC: Section 7.6 (fixed right, 200px width, smooth scroll)

**Clarifications Applied**: See [spec.md Clarifications - Session 2026-01-22](./spec.md#session-2026-01-22-implementation-details) for canonical Q&A including:
- Ghost text trigger, context, max length, code blocks, cancellation
- Ghost text word boundaries: See spec.md Session 2026-01-22 (DD-067)
- Margin annotation positioning, issue detection patterns, AI clarification flow
- Threaded discussion, issue extraction and categorization (🔴/🟡/🟢)

**Component Mapping**:
```toon
US01components[8]{component,uiSpec,specs}:
  NoteCanvas.tsx,7.2,720px max 32px padding warm background
  OutlineTree.tsx,7.1,220px width VS Code-inspired tree
  MarginAnnotations.tsx,7.3,200px default AI muted bg 3px left border; triggers clarifying questions
  GhostTextExtension.ts,8.2,40% opacity italic Tab/→ to accept
  IssueExtractionPanel.tsx,7.4,Rainbow gradient border hover scale 2%; categorizes as 🔴/🟡/🟢
  ThreadedDiscussion.tsx,7.4,Per-block AI clarification chat; Discuss button opens conversation
  RichNoteHeader.tsx,7.5,text-xs word count AI reading time
  AutoTOC.tsx,7.6,Fixed position current section highlighting
```

**Agent-to-Scenario Mapping**:
```toon
US01agentMapping[7]{agent,scenarios,description}:
  GhostTextAgent,2-3,Ghost text display (500ms pause) and acceptance (Tab/→)
  MarginAnnotationAgent,4-6 8-9 19-21,Clarifying questions margin annotations issue detection count
  IssueExtractorAgent,8-12,Issue detection rainbow boxes metadata pre-fill bidirectional sync
  ThreadedDiscussion (UI),5-6 14,Threaded AI discussions per block /ask command
  (Frontend),1 13 15-18 22,Core canvas experience navigation performance auto-save
```
*Note: Scenarios 1, 13, 15-18, 22 are frontend-only (no AI agent). Scenarios 5-6, 14 use ThreadedDiscussion UI component with MarginAnnotationAgent backend.*

**Data Model Entities**: Note, NoteBlock, NoteAnnotation, NoteIssueLink, ThreadedDiscussion
**Key Components**: `NoteCanvas.tsx`, `GhostText.ts` (TipTap extension), `MarginAnnotations.tsx`, `ThreadedDiscussion.tsx`

**AI Clarification Flow** (Implicit → Explicit):
1. User writes ambiguous statement → AI detects implicit intent via pattern matching
2. Margin annotation appears with clarifying question → User clicks "Discuss"
3. Threaded AI conversation opens → AI asks probing questions (What's driving this? Why now?)
4. AI identifies explicit root issues from implicit request → Presents with categorization
5. User selects issues to extract → Created with 🔴/🟡/🟢 badges and source note link

---

### US-02: AI Issue Creation (P1)

**Spec Reference**: User Story 2 | **Priority**: P1 | **Acceptance Scenarios**: 8

**UI Design References**: ui-design-spec.md Sections 5, 10.5
- Issue Card Anatomy: Section 5.2.4 (state icon, AI attribution, rounded pill badges)
- AI Confidence Tags: Section 10.5 (Recommended/Default/Alternative with percentage on hover)
- Priority Colors: Section 4.1.5 (Urgent red, High amber, Medium gold, Low blue)

**Clarifications Applied**:
```toon
US02clarify[3]{question,answer,impact}:
  When duplicate detection runs?,Auto on title blur,onBlur event trigger async check
  How to present detected issues?,Inline rainbow box + margin count,Rainbow border CSS + count badge
  What metadata to pre-fill?,Title + description + priority + labels,AI suggestions for all fields
```

**Component Mapping**:
```toon
US02components[3]{component,uiSpec,specs}:
  IssueCard.tsx,5.2.4,State icon You + AI attribution pill badges
  ConfidenceTags.tsx,10.5,★ Recommended (≥80%) percentage on hover
  DuplicateDetection.tsx,-,Inline warning dialog link to existing issue
```

**Data Model Entities**: Issue, Label, IssueLink
**Key Components**: `IssueCreateModal.tsx`, `DuplicateDetection.tsx`, `AIIssueEnhancer` agent

---

### US-03: AI PR Review (P1)

**Spec Reference**: User Story 3 | **Priority**: P1 | **Acceptance Scenarios**: 5

**Clarifications Applied**:
```toon
US03clarify[4]{question,answer,impact}:
  When AI review triggers?,Auto on PR open via webhook,GitHub webhook handler async job
  What aspects to review?,Architecture + Security + Quality,3-part prompt structure
  Comment format?,Severity (🔴🟡🔵) + suggestion + rationale + AI fix prompt,Structured comment template
  GitHub API rate limit handling?,Queue with exponential backoff notify user,Supabase Queues with retry logic
```

**Data Model Entities**: Issue, IntegrationLink, Integration
**Key Components**: `PRReviewAgent`, GitHub webhook handler, `queue/ai_high`

---

### US-04: Sprint Planning (P1)

**Spec Reference**: User Story 4 | **Priority**: P1 | **Acceptance Scenarios**: 5

**Clarifications Applied**:
```toon
US04clarify[1]{question,answer,impact}:
  How to calculate velocity?,Sum of story points for issues completed in cycle,Query aggregate on completed issues
```

**Data Model Entities**: Cycle, Issue (estimate_points, state_id)
**Key Components**: `CycleBoard.tsx`, `VelocityChart.tsx`, velocity computation service

---

### US-12: AI Context (P1)

**Spec Reference**: User Story 12 | **Priority**: P1 | **Acceptance Scenarios**: 10

**UI Design References**: ui-design-spec.md Sections 8.6, 10.5
- AI Panel: Section 8.6 (collapsible, status text during operations)
- Confidence Tags: Section 10.5 (for AI-suggested context items)
- Artifact Preview: Section 8.6 (collapsed preview with fade-out gradient)

**Clarifications Applied**:
```toon
US12clarify[4]{question,answer,impact}:
  How to discover code files for context?,AST analysis of code references in description,Pattern matching for file paths
  What patterns to detect?,File paths + symbols (e.g. src/UserService.ts),Regex patterns
  How to resolve to actual files?,GitHub API search in linked repos,GitHub client integration
  What context to extract?,Function signature + docstring + import dependencies,Code parser
```

**Component Mapping**:
```toon
US12components[5]{component,uiSpec,specs}:
  AIContext.tsx,8.6,Tabbed panel (Context/Tasks/Chat)
  ContextItemList.tsx,-,Related issues docs code files
  TaskChecklist.tsx,-,AI-generated implementation tasks
  ClaudeCodePrompt.tsx,-,Copy-to-clipboard ready prompts
  DependencyGraph.tsx,-,Visual task dependency graph
```

**Data Model Entities**: AIContext, Issue, IntegrationLink
**Key Components**: `AIContext.tsx`, `AIContextAgent`, `CodeContextExtractor`

---

### US-18: GitHub Integration (P1)

**Spec Reference**: User Story 18 | **Priority**: P1 | **Acceptance Scenarios**: 10

**Clarifications Applied**:
```toon
US18clarify[2]{question,answer,impact}:
  How commit linking works?,Hybrid: parse on webhook + scheduled scan for missed commits,Dual detection mechanism
  Should PR merge auto-transition issue?,Yes always auto-complete,State transition on PR merge event
```

**Data Model Entities**: Integration, IntegrationLink, Issue
**Key Components**: GitHub App, webhook handlers, commit linker

---

### Cross-Cutting Clarifications

These clarifications apply across multiple user stories:

**Authentication & Authorization (FR-060 to FR-062, FR-117 to FR-123)**:
```toon
authClarify[5]{question,answer,stories}:
  Auth system?,Supabase Auth (GoTrue),All
  Authorization?,Row-Level Security (RLS),All
  Session strategy?,Access token (1h) + Refresh token (7d),All
  API key encryption?,AES-256-GCM with Supabase Vault,US-11
  Admin RLS handling?,Role check in policy,All
```

**Background Jobs (FR-095 to FR-101)**:
```toon
jobsClarify[5]{question,answer,stories}:
  Queue system?,Supabase Queues (pgmq + pg_cron),US-03 US-10 US-14
  Priority levels?,High (PR review) Normal (embeddings) Low (graph recalc),US-03 US-10 US-14
  AI job timeout?,5 minutes,All AI features
  Failed job handling?,Dead letter queue + admin notification,All
  Batch schedule?,Nightly 2 AM UTC,US-10 US-14
```

**Data Model & API (FR-001 to FR-065)**:
```toon
dataClarify[7]{question,answer,stories}:
  Issue link modeling?,Junction table issue_links,US-02 US-12
  Pagination strategy?,Cursor-based,All list views
  List response format?,{data: [...] meta: {total cursor hasMore}},All APIs
  Optimistic updates?,TanStack Query with rollback,All mutations
  Issue state transitions?,All forward; completed→started; any→cancelled,US-04 US-18
  Soft-delete restoration?,Creator OR admin/owner,All entities
  Export/import format?,JSON archive (ZIP),US-11
```

**Note Storage (US-01, US-06)**:
```toon
noteClarify[3]{question,answer,stories}:
  Note block storage?,JSONB (TipTap native format),US-01 US-06
  Embedding refresh?,On >20% content change,US-10
  Chunk size?,512 tokens with 50 token overlap,US-10
```

**AI Provider Routing (All AI features)**:
```toon
aiRoutingClarify[4]{question,answer,stories}:
  Failover strategy?,Auto failover to next-best provider on error,All AI
  Rate limiting?,1000/min standard 100/min AI endpoints,All
  AI streaming?,SSE via FastAPI StreamingResponse,US-01 US-12
  AI execution boundary?,All AI in FastAPI. Edge Functions for webhooks only,All AI
```

**AI Clarification Flow (Session 2026-01-23)**:
```toon
aiClarificationClarify[5]{question,answer,stories}:
  When AI detects implicit intent?,On ambiguous statements (vague verbs undefined scope missing rationale),US-01 US-02
  How clarifying questions appear?,Margin annotations with Discuss button opening threaded chat,US-01
  What probing questions does AI ask?,What's driving this? Why now? What else is needed? What's the full scope?,US-01
  How are extracted issues categorized?,🔴 Explicit (literal) 🟡 Implicit (inferred) 🟢 Related (consequential),US-01 US-02
  How extraction affects issue creation?,Issues created with category badge + link to source note block,US-02
```

**Ambiguity Resolutions (Session 2026-01-22)**:
```toon
ambiguityResolutions[10]{decision,answer,impact}:
  Cancelled state terminal?,Yes cannot reopen,State machine simplification
  100% duplicate handling?,Warn but allow creation,UX dialog implementation
  Real-time updates?,Supabase Realtime (not polling),WebSocket subscription setup
  Code parsing languages?,AST: Python/TS/JS/Go/Java/Rust. Regex fallback,Parser implementation scope
  Cycle rollover?,Manual selection modal,UI component for cycle end
  Module progress calc?,Hybrid (points if available count fallback),Progress computation logic
  AI confidence display?,Only Recommended tag (≥80%),Simplified UI single badge
  Template placeholders?,Smart AI detection (no syntax),AI inference for fill-ins
  Notifications?,Supabase Realtime (no entity),Subscribe to activities table
  Sample project?,Minimal seed (5-10 issues 3 notes 1 cycle),Seed script scope
```

---

## Implementation Priority Order (MVP)

Based on dependencies and business value, the recommended implementation order for **MVP (P0 + P1)** is:

### MVP Phase 1: Foundation (P0)

```toon
phase1[2]{order,story,deps,deliverable}:
  1.1,Infrastructure Setup,None,Supabase + FastAPI + Next.js
  1.2,US-01: Note Canvas,Infrastructure,Core note-first UX
```

### MVP Phase 2: Core PM Features (P1)

```toon
phase2[5]{order,story,deps,deliverable}:
  2.1,US-02: AI Issue Creation,US-01 (note→issue extraction),Issue management + AI enhancement
  2.2,US-04: Sprint Planning,US-02 (issues exist),Cycle/sprint board
  2.3,US-18: GitHub Integration,US-02 (issues to link),PR/commit linking
  2.4,US-03: AI PR Review,US-18 (GitHub connected),Automated code review
  2.5,US-12: AI Context,US-02 US-18,Developer productivity
```

### Future Phases (See Separate Specs)

- **Phase 2 (P2)**: Enhanced Productivity - See [specs/002-pilot-space-phase2/plan.md](../002-pilot-space-phase2/plan.md)
- **Phase 3 (P3)**: Discovery & Onboarding - See [specs/003-pilot-space-phase3/plan.md](../003-pilot-space-phase3/plan.md)

---

## Phase 0: Research Requirements

Based on Technical Context analysis and Session 2026-01-22 clarifications, the following areas were researched:

### Research Topics (Resolved)

```toon
researchTopics[12]{topic,status,summary}:
  TipTap/ProseMirror Custom Extensions,✅,Ghost text: decorations 500ms pause 50 tokens max; context: block+3prev+3sections+history
  AI Provider Integration Patterns,✅,Task-based routing streaming via SSE failover auto to next-best
  pgvector Embedding Strategy,✅,text-embedding-3-large (3072 dims) 512 token chunks HNSW via Supabase
  Supabase Auth Integration,✅,GoTrue + JWT + RLS policies; sessions: 1h access + 7d refresh
  GitHub App,✅,App for better rate limits; webhook + scheduled scan hybrid; PR merge auto-transitions
  Slack App Architecture,✅,Events API for prod Socket Mode for dev; /pilot create opens modal
  SSE for AI Streaming,✅,FastAPI StreamingResponse; frontend EventSource API; 1.5s debounce autosave
  Virtualized Rendering,✅,@tanstack/react-virtual; block height caching; scroll position preservation
  Knowledge Graph,✅,Sigma.js + react-sigma WebGL ForceAtlas2; PostgreSQL adjacency table; weekly batch
  Background Jobs,✅,Supabase Queues (pgmq + pg_cron) 3 priority levels; 5min AI timeout; DLQ
  Next.js App Router,✅,Server components streaming SSR; feature-based folder structure
  State Management,✅,MobX for UI state TanStack Query for server state; strict separation
```

**Output**: `research.md` updated with all decisions (Last verified: 2026-01-23)

---

## Phase 1: Design Artifacts

### 1.1 Data Model (`data-model.md`)

Extract entities from spec and define:

**Core Entities**:
- Workspace (container for projects)
- Project (contains issues, cycles, modules, pages, notes)
- Note (block-based document with AI annotations)
- Issue (work item with state machine)
- AIContext (aggregated context for issue)
- Cycle (sprint container)
- Module (epic grouping)
- Page (rich text documentation)
- Template (note templates)
- User (Keycloak-synced identity)
- Label (categorization tags)
- Activity (audit log)
- Integration (GitHub/Slack connections)
- AIConfiguration (workspace LLM settings)

**Relationships**:
- Workspace 1:N Projects
- Project 1:N Issues, Notes, Pages, Cycles, Modules
- Note 1:N Blocks, NoteAnnotations, ThreadedDiscussions
- Note N:M Issues (bidirectional sync)
- Issue N:1 Cycle, Module (optional)
- Issue 1:N Activities, Labels, IntegrationLinks

**State Machines**:
- Issue states: Backlog → Todo → In Progress → Review → Done (with customization)
- Note sync states: Draft → Synced → Conflict

### 1.2 API Contracts (`contracts/`)

Generate OpenAPI specification for:

**Workspace & Project APIs**
- CRUD for workspaces, projects
- Member management
- Settings management

**Note Canvas APIs**
- Note CRUD with blocks
- AI ghost text suggestions (streaming)
- Margin annotations
- Issue extraction
- Threaded discussions

**Issue Management APIs**
- Issue CRUD with state transitions
- AI-enhanced creation
- Duplicate detection
- AI Context retrieval
- Task decomposition

**AI Feature APIs**
- PR review trigger
- Documentation generation
- Diagram generation
- Semantic search

**Integration APIs**
- GitHub OAuth/App installation
- Slack OAuth installation
- Webhook configuration

### 1.3 Quickstart Guide (`quickstart.md`)

Developer setup instructions:
- Prerequisites (Python 3.12+, Node 20+, Docker)
- Environment configuration
- Database setup (PostgreSQL + pgvector)
- Service startup (backend, frontend, workers)
- Sample data seeding
- Running tests

---

## Key Technical Decisions Summary

```toon
keyDecisions[19]{area,decision,reference}:
  Backend Framework,FastAPI (not Django),DD-001
  AI Model,BYOK only no local LLM,DD-002
  AI Autonomy,Critical-only approval,DD-003
  MVP Integrations,GitHub + Slack only,DD-004
  Real-time Collab,Deferred to Phase 2,DD-005
  Code Review,Unified AI PR Review,DD-006
  RBAC,Basic roles in MVP,DD-007
  Note Workflow,Note-First collaborative thinking space,DD-013
  AI Clarification,Implicit → Explicit root issue extraction,Session 2026-01-23
  Diagram Formats,Mermaid default PlantUML/C4 supported,DD-012
  Authentication,Supabase Auth (GoTrue),Session 2026-01-22
  Authorization,Row-Level Security (RLS),Session 2026-01-22
  Queue System,Supabase Queues (pgmq),Session 2026-01-22
  File Storage,Supabase Storage,Session 2026-01-22
  Backend Pattern,CQRS-lite,Session 2026-01-22
  Note Storage,JSONB (TipTap native),Session 2026-01-22
  State Management,MobX + TanStack Query,Session 2026-01-22
  AI Streaming,SSE via StreamingResponse,Session 2026-01-22
  Graph Visualization,Sigma.js + react-sigma,Session 2026-01-22
```

---

## Risk Assessment (MVP)

```toon
risks[5]{risk,impact,likelihood,mitigation}:
  TipTap complexity for ghost text,High,Medium,Spike early fallback to simpler overlay
  AI response latency >2s,Medium,Medium,Streaming via SSE caching common patterns
  pgvector scaling at 50k issues,Medium,Low,HNSW indexing via Supabase query monitoring
  GitHub API rate limits during PR review,Medium,Medium,Queue with backoff notify user of delays
  Supabase Queue limitations,Low,Low,pgmq is battle-tested can scale to Redis if needed
```

*Note: Knowledge graph and semantic relationship risks deferred to Phase 2*

---

## Post-Design Constitution Re-Evaluation

*GATE: Re-checked after Phase 1 design artifacts generated.*

### Design Artifact Compliance

```toon
artifactCompliance[8]{artifact,requirement,status}:
  data-model.md,Soft deletion UUID PKs,✅ All entities use soft delete + UUID
  data-model.md,pgvector for embeddings,✅ Embedding table with HNSW index
  data-model.md,Pydantic v2 models,✅ SQLAlchemy + Pydantic schemas
  contracts/openapi.yaml,FastAPI REST conventions,✅ RESTful endpoints Pydantic validation
  contracts/openapi.yaml,AI human-in-loop,✅ AI endpoints return suggestions not auto-apply
  quickstart.md,uv for Python deps,✅ Uses uv sync uv run
  quickstart.md,pnpm for frontend,✅ Uses pnpm shadcn/ui setup
  research.md,BYOK only,✅ No local LLM support provider adapters
```

### Technology Alignment

```toon
techAlignment[10]{requirement,implementation,status}:
  FastAPI + SQLAlchemy 2.0 async,data-model.md uses async mapped_column,✅
  Next.js 14+ + React 18 + TypeScript,quickstart.md Next.js 14+ App Router,✅
  MobX + TanStack Query,Feature-based stores + server state,✅
  TailwindCSS,shadcn/ui (Tailwind-based),✅
  TipTap/ProseMirror,Custom extensions per research.md,✅
  Supabase Queues,pgmq + pg_cron per Session 2026-01-22,✅
  Supabase Auth,GoTrue + RLS per Session 2026-01-22,✅
  GitHub App,research.md decision,✅
  SSE for AI streaming,research.md decision OpenAPI ghost-text endpoint,✅
  Sigma.js + react-sigma,Knowledge graph per Session 2026-01-22,✅
```

### Quality Gates Readiness

```toon
gateReadiness[6]{gate,ready,notes}:
  Lint (ruff/ESLint),✅,Configured in quickstart.md
  Type check (pyright/tsc),✅,Strict mode documented
  Tests (pytest/Jest),✅,Test commands documented
  Pre-commit hooks,✅,Installation in quickstart
  N+1 query prevention,✅,SQLAlchemy eager loading patterns
  File size limit (700 lines),✅,Pre-commit hooks
```

**Post-Design Gate Status**: ✅ PASS (All design artifacts comply with constitution)

---

## Generated Artifacts Summary

```toon
artifacts[9]{artifact,path,description}:
  Implementation Plan (MVP),specs/001-pilot-space-mvp/plan.md,This file (P0 + P1 features)
  Feature Specification (MVP),specs/001-pilot-space-mvp/spec.md,MVP user stories and requirements
  Phase 2 Specification,specs/002-pilot-space-phase2/spec.md,P2 features (9 user stories)
  Phase 3 Specification,specs/003-pilot-space-phase3/spec.md,P3 features (3 user stories)
  Research Document,specs/001-pilot-space-mvp/research.md,Technical decisions for 10 topics
  Data Model,specs/001-pilot-space-mvp/data-model.md,21 entities with relationships
  API Contracts,specs/001-pilot-space-mvp/contracts/openapi.yaml,REST API specification
  Prompt Templates,specs/001-pilot-space-mvp/prompts/,12 optimized prompts for planning stories architecture AI agents compliance data models TipTap extensions testing integrations
  SDLC Documentation Suite,specs/001-pilot-space-mvp/sdlc/,14 documents: PRD RTM NFRs Acceptance Criteria C4 diagrams API guide AI agent reference CONTRIBUTING testing strategy local development deployment incident response user guide documentation governance
```

---

---

## Architecture Pattern Decisions

Based on `/software-architect` clarifications and alignment with `docs/dev-pattern/`:

### Backend Architecture

```toon
backendPatterns[9]{component,decision,patternRef}:
  CQRS Handlers,Service Classes with Payloads (CreateIssueService.execute(payload)),Custom inspired by 08-service-layer
  AI Agents,Claude Agent SDK (state machine orchestration),Custom (not in patterns)
  Repositories,Generic + Specific (BaseRepository[T] + domain methods),07-repository-pattern ✅
  DI Container,dependency-injector (Singleton + Factory),26-dependency-injection ✅
  API Versioning,URL path (/api/v1/issues),27-api-builder-pattern
  Error Format,RFC 7807 Problem Details,Custom standard
  Migrations,Alembic autogenerate + review,28b-database-migrations ✅
  Config,Pydantic Settings + .env,26-dependency-injection ✅
  Logging,Structlog JSON with correlation IDs,41-logging-standards ✅
```

### Frontend Architecture

```toon
frontendPatterns[10]{component,decision,patternRef}:
  Module Structure,Feature folders (features/{domain}/),19-frontend-code-standards ✅
  State Management,MobX (override Zustand pattern for complex reactivity),Override 21a
  Server State,TanStack Query,21a ✅
  TipTap Extensions,Extension per feature,Custom
  Error Handling,Inline errors only,Custom
  Auth Flow,Supabase JS Client SDK,Custom (Supabase-specific)
  File Uploads,Direct to Supabase Storage,Custom
  Command Search,fuse.js client-side,Custom
  Realtime Scope,Per-workspace channel,Custom (Supabase-specific)
```

### Pattern Overrides

```toon
patternOverrides[3]{pattern,overrideReason}:
  21a: Zustand,MobX provides better reactivity for complex note canvas state
  17: Auth Service,Using Supabase Auth instead of custom JWT service
  10: Kafka Events,Using Supabase Queues instead of Kafka
```

---

## Session 2026-01-22: Frontend Architecture Decisions

**Context**: Clarification session to resolve 15 ambiguous frontend architecture decisions for MVP implementation.

### 1. State Management Responsibility Split

```toon
stateManagement[4]{aspect,decision}:
  Question,What is TanStack Query vs MobX boundary?
  Decision,MobX UI-only - TanStack Query handles ALL server data MobX only for ephemeral UI state
  MobX Scope,Selection state UI mode toggles local form drafts temporary filters
  TanStack Scope,All fetched data (notes issues projects) cache mutations optimistic updates
```

**Pattern**: No MobX store subscribes to TanStack Query - use `useQuery` hooks directly in components

### 2. Real-time Update Merging

```toon
realtimeMerging[4]{aspect,decision}:
  Question,How to merge Supabase Realtime updates with TanStack Query cache?
  Decision,Optimistic merge - Parse Realtime payload directly update TanStack Query cache with setQueryData()
  Implementation,Realtime handler → parse payload → queryClient.setQueryData(['issues' id] updater)
  Edge Case,If local mutation pending skip Realtime update for that entity
```

**Conflict Resolution**: Last-write-wins (MVP), no CRDT complexity

### 3. Ghost Text SSE Cancellation

```toon
sseCancel[4]{aspect,decision}:
  Question,How to cancel ghost text request when user continues typing?
  Decision,AbortController - Cancel previous SSE stream on new keystroke
  Implementation,Each ghost text request creates new AbortController signal passed to fetch()
  Cleanup,On component unmount OR new keystroke → controller.abort()
```

**UI Behavior**: Previous suggestion fades out, new request starts

### 4. Virtualization Library

```toon
virtualization[4]{aspect,decision}:
  Question,Which virtualization for TipTap Note Canvas with 1000+ blocks?
  Decision,@tanstack/react-virtual - Modern API excellent React integration
  Integration,TipTap NodeView wraps virtualized container
  Block Height,Measured via ResizeObserver cached in store
```

**Scroll Preservation**: Save scroll offset before re-render, restore after

### 5. Code Splitting Strategy

```toon
codeSplitting[4]{aspect,decision}:
  Question,Which components to dynamically import vs bundle statically?
  Decision,Heavy components only - Dynamic: Sigma.js Mermaid AI Panel. Static: TipTap Command Palette
  Dynamic,next/dynamic with loading placeholder: KnowledgeGraph MermaidPreview AIContextPanel
  Threshold,>50KB gzipped = dynamic import candidate
```

**Static**: Core editing (TipTap), navigation (CommandPalette, Sidebar) - loaded with initial bundle

### 6. Barrel File Convention

```toon
barrelFiles[4]{aspect,decision}:
  Question,Module barrel conventions to avoid bundle size issues?
  Decision,Feature-level only - One barrel per feature
  Structure,@/features/issues/index.ts exports public API only
  Anti-pattern,No @/components/index.ts - import directly from file
```

**Tree-shaking**: Named exports only, no `export *`

### 7. SSE Connection Management

```toon
sseConnection[4]{aspect,decision}:
  Question,One SSE stream per AI feature or multiplexed?
  Decision,Separate streams + cookie auth - Each AI operation gets own EventSource
  Auth,HttpOnly cookie for session no token in URL
  Reconnect,Browser auto-reconnect for network drops custom retry for errors
```

**Lifecycle**: EventSource created on operation start, closed on completion/abort

### 8. AI Error Display Patterns

```toon
aiErrors[5]{context,display}:
  Ghost Text,Inline muted text: AI unavailable with fade-out after 3s
  AI Panel,Panel error state with retry button
  PR Review,Toast notification + notification center entry
  Network Error,Retry with exponential backoff (3 attempts) then surface to user
```

### 9. TipTap Extension Key Priority

```toon
keyPriority[4]{context,behavior}:
  Ghost Text,Tab accepts suggestion ONLY when ghost text is visible
  Code Block,Tab inserts indent when cursor is inside code block
  Priority Order,1) Code block context → indent 2) Ghost text visible → accept 3) Default → next field
  Implementation,Custom keymap extension with priority ordering
```

### 10. Content Diff for Embeddings

```toon
contentDiff[4]{aspect,decision}:
  Question,How to detect content changes for embedding refresh?
  Decision,Block-level tracking via TipTap transaction
  Implementation,Track added/modified/deleted blocks in onUpdate
  Threshold,>20% blocks changed OR title/heading changed → trigger embedding refresh
```

**Queue**: Debounce 5s, then queue background job for embedding recalculation

### 11. Margin Annotation Positioning

```toon
marginPosition[4]{aspect,decision}:
  Question,How to position margin annotations relative to blocks?
  Decision,CSS Anchor Positioning API (Chrome 125+)
  Fallback,position: absolute with calculated offsets for Safari/Firefox
  Implementation,Block has anchor-name: --block-{id} annotation uses position-anchor: --block-{id}
```

**Scroll Sync**: Annotations scroll with blocks naturally via CSS anchoring

### 12. Command Palette AI Context

```toon
cmdPaletteContext[4]{aspect,decision}:
  Question,What context to provide AI suggestions in Command Palette?
  Decision,Minimal focused context
  Context Sent,Current selection text + active entity type (note/issue/project) + document title
  NOT Sent,Full document content user history (MVP)
```

**Caching**: Cache suggestions per entity type for 30s

### 13. Focus Management Pattern

```toon
focusManagement[4]{key,behavior}:
  Tab,Stays within editor (cycles blocks or accepts ghost text)
  Escape,Exits current context to sidebar focus
  F6,Cycles between major regions: Sidebar → Canvas → AI Panel
  Modal Focus,Trapped within modal restored to trigger on close
```

### 14. Motion/Animation Handling

```toon
motionHandling[4]{aspect,decision}:
  Question,How to respect prefers-reduced-motion?
  Decision,CSS media query - All animations defined in CSS with @media (prefers-reduced-motion: reduce) fallback
  Implementation,Tailwind motion-safe: and motion-reduce: variants
  Fallback,Instant state changes no transitions
```

**JS Animations**: Check `window.matchMedia('(prefers-reduced-motion: reduce)')` before triggering

### 15. Frontend Testing Architecture

```toon
frontendTesting[6]{type,approach}:
  Unit Tests,Pure functions hooks (Vitest)
  Integration,TipTap with real editor in Vitest (jsdom) user-event for interactions
  E2E,Playwright for critical user flows (note creation issue extraction)
  SSE Mocking,MSW handlers for streaming responses
  Accessibility,axe-core integrated in CI manual screen reader testing
```
