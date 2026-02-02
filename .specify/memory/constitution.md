<!--
SYNC IMPACT REPORT
==================
Version Change: 1.2.0 → 1.2.1 (PATCH)

Modified Principles:
- Principle II: Expanded with three sub-sections (Ghost Text, Annotations, Issue Extraction)

Added Sections: None

Updated Sections:
- Principle II: Added detailed guidance for Ghost Text, Annotation Workflows, Issue Extraction Flow
- Version: 1.2.0 → 1.2.1
- Last Amended: 2026-01-23 → 2026-01-26

Removed Sections: None

Templates Requiring Updates:
✅ plan-template.md - Constitution Check section compatible (no changes needed)
✅ spec-template.md - Requirements format aligns with expanded principles
✅ tasks-template.md - Phase structure supports incremental delivery
✅ checklist-template.md - Generic format compatible
✅ CLAUDE.md - No updates needed (references remain valid)

Follow-up TODOs: None
-->

# Pilot Space Constitution

## Core Principles

### I. AI-Human Collaboration First

AI augments human expertise—it MUST NOT replace human judgment. All AI actions follow human-in-the-loop principles:

- AI suggestions MUST always be presented for human approval before execution
- Critical actions (merge, deploy, delete, publish) MUST require explicit human confirmation
- AI MUST provide rationale and alternatives for transparency
- Users MUST be able to adjust AI behavior and trigger modes per workspace/project
- Event-driven AI triggers MUST be configurable (enable/disable per event type)

**Trigger Flow**: User Intent → AI Suggestion → Human Review → Execution

**Rationale**: Human oversight ensures AI assists rather than controls, maintaining accountability and enabling course correction.

### II. Note-First Approach

Start with collaborative thinking in notes, then extract structured work items:

- Note canvas MUST be the default home view for capturing rough ideas
- AI-assisted clarification MUST help users discover explicit issues from implicit requests
- Related notes MUST be automatically linked to extracted issues (bidirectional sync)
- Issues MUST emerge naturally from refined thinking, not form-filling

**Flow**: Rough Ideas (Note) → AI Clarification → Explicit Issues → Structured Work Items

**Rationale**: Starting with thinking (not tickets) enables better problem discovery and reduces cognitive overhead of upfront structure.

#### II.A Ghost Text (Inline AI Suggestions)

Ghost text provides real-time writing assistance as users type in the note canvas:

- Ghost text MUST appear after 500ms typing pause (configurable per workspace)
- Ghost text MUST use a fast model (Claude Haiku) with <2s latency target
- Tab key MUST accept full suggestion; Right Arrow MUST accept word-by-word
- Ghost text requests MUST be cancellable via AbortController when user continues typing
- Ghost text MUST gracefully degrade on timeout (empty string, no error displayed)
- Context for ghost text MUST include: current block + 3 previous blocks + semantic summary

**Implementation**: Uses Claude Agent SDK with `claude-3-5-haiku` model. Max 50 tokens output, 2000ms timeout. Code blocks use separate prompt optimized for syntax completion.

**Reference**: DD-067 (Note Canvas Implementation), `specs/004-mvp-agents-build/ghost-text-sdk-design.md`

#### II.B Margin Annotations (AI Clarification)

AI margin annotations provide probing questions and suggestions in the document margin:

- Annotations MUST appear in the right margin, linked to specific content blocks
- Annotations MUST use vertical stacking with scroll when overflow occurs
- Annotations MUST support threaded discussions between user and AI
- Annotations MUST be dismissible, collapsible, and actionable
- CSS Anchor Positioning API MUST be used (Chrome 125+) with fallback for Safari/Firefox

**Annotation Types**:
- **Clarifying Question**: AI asks probing questions about vague content
- **Suggestion**: AI proposes improvements or alternatives
- **Issue Candidate**: AI identifies potential actionable items for extraction

**Trigger Flow**: Block Content Analysis → AI Detects Ambiguity → Annotation Created → User Responds/Dismisses → Discussion Thread (optional) → Resolution

**Reference**: DD-013 (Note-First Collaborative Workspace), DD-014-054 (UI Clarifications)

#### II.C Issue Extraction Flow

Issue extraction transforms refined thinking into actionable work items:

- AI MUST detect action patterns (e.g., "implement X", "fix Y", "add Z") to identify issue candidates
- Extracted issues MUST be categorized with rainbow boxes:
  - 🔴 **Explicit** (red): What user directly stated
  - 🟡 **Implicit** (yellow): What user meant but didn't say
  - 🟢 **Related** (green): What user will also need
- AI MUST limit suggestions to 3-5 issues per analysis (avoid overwhelming users)
- Extracted issues MUST maintain bidirectional links to source notes
- Deleted linked issues MUST show strikethrough + "Deleted" badge on rainbow box

**Extraction Flow**:
1. User writes rough content with implicit requests
2. AI analyzes via margin annotations, asks clarifying questions
3. User and AI refine understanding through threaded discussion
4. AI identifies explicit root issues from clarified content
5. User confirms/modifies extraction → Structured issues created
6. Issues link back to source note blocks (bidirectional sync)

**Issue Categorization**: AI uses confidence scoring to determine explicit vs implicit vs related. User can override categorization before confirming extraction.

**Reference**: DD-013 (Note-First), AC-01.08/AC-01.09 (Acceptance Criteria), FR-006 (Issue Extraction with Rainbow Boxes)

### III. Documentation-Third Approach

Comprehensive documentation flows naturally from work artifacts:

- Auto-generated API documentation from code MUST be supported
- Architecture diagram generation from codebase analysis SHOULD be available
- Living documentation MUST update with code changes
- Documentation MUST NOT require separate manual maintenance overhead

**Flow**: Code Changes → AI Analysis → Draft Documentation → Human Review → Published Doc

**Rationale**: Documentation that emerges from actual work is more accurate and maintainable than separately authored docs.

### IV. Task-Centric Workflow

Prioritize actionable tasks with AI-powered decomposition:

- Feature requests MUST be decomposable into User Stories and Technical Tasks
- AI SHOULD suggest acceptance criteria based on task context
- Task breakdown MUST support independent implementation and testing
- Each task MUST be traceable to its parent feature/epic

**Flow**: Epic/Feature Request → AI Decomposition → Task Breakdown → AI-Suggested Acceptance Criteria → Human Refinement

**Rationale**: Well-decomposed tasks enable parallel work, clear ownership, and measurable progress.

### V. Collaboration & Knowledge Sharing

Foster team knowledge through AI-curated insights:

- Pattern Library: AI MUST identify and catalog recurring patterns
- Decision Log: AI-assisted Architecture Decision Records (ADRs) MUST be supported
- Expertise Mapping: AI SHOULD suggest reviewers based on code ownership
- Knowledge Graph: AI SHOULD build relationships between docs, code, and decisions

**Rationale**: Collective knowledge compounds team effectiveness over time.

### VI. Agile Integration

Align with agile methodologies while enhancing with AI:

- Sprint Planning: AI SHOULD suggest story points based on historical data
- Retrospective Insights: AI MUST analyze sprint metrics for improvement areas
- Velocity Prediction: ML-based sprint velocity forecasting SHOULD be available
- Blocker Detection: Proactive identification of at-risk items MUST be supported

**Rationale**: AI enhances agile practices by providing data-driven insights without replacing team judgment.

### VII. Notation & Standards

Promote standardized architectural notation with AI assistance:

- UML Generation: AI MUST generate sequence/class diagrams from descriptions
- C4 Model: AI MUST support context, container, component, code diagrams
- Mermaid Integration: Code-based diagram rendering MUST be supported
- PlantUML/ArchiMate: Enterprise architecture modeling SHOULD be supported

**Supported Formats**: Mermaid (default), PlantUML, C4 Model, ArchiMate, Structurizr DSL

**Rationale**: Standardized notations enable consistent communication and reduce ambiguity in architectural discussions.

## Technology Standards

This section defines mandatory technology decisions per DD-001 through DD-012 in DESIGN_DECISIONS.md and Session 2026-01-22 clarifications:

| Layer | Technology | Constraint |
|-------|------------|------------|
| Backend | FastAPI + SQLAlchemy 2.0 (async) | MUST use Pydantic v2 for validation |
| Frontend | React 18 + TypeScript + MobX | MUST use TailwindCSS for styling |
| Database | PostgreSQL 16+ with pgvector | MUST support soft deletion, UUID PKs |
| AI | BYOK + Claude Agent SDK | MUST NOT require local LLM |
| Auth | Supabase Auth (GoTrue) | MUST use Row-Level Security (RLS) |
| Cache | Redis | MUST support session and AI response caching |
| Queue | Supabase Queues (pgmq + pg_cron) | MUST handle async AI tasks |
| Storage | Supabase Storage | S3-compatible file storage |
| Search | Meilisearch | MUST support typo-tolerant search |

**Platform**: Supabase (Auth, Database, Storage, Queues) per Session 2026-01-22

**Architecture Patterns** (per plan.md v4.0):
- Backend: CQRS-lite (Use Case Classes)
- Frontend: Feature-based MobX stores + TanStack Query
- AI Streaming: SSE via FastAPI StreamingResponse
- Error Format: RFC 7807 Problem Details
- DI: dependency-injector library

**Non-Negotiables**:
- All code MUST pass type checking (pyright/TypeScript strict mode)
- All public APIs MUST be documented via OpenAPI
- All database operations MUST use async patterns
- File size limit: 700 lines maximum per file
- AI features MUST respect human-in-the-loop principle

## Quality Gates

Development MUST pass these gates before any merge:

### Code Quality
- [ ] Lint passes (`uv run ruff check` / `pnpm lint`)
- [ ] Type check passes (`uv run pyright` / `pnpm type-check`)
- [ ] Tests pass with coverage > 80%
- [ ] No N+1 queries, no blocking I/O in async functions
- [ ] No TODOs, mocks, or placeholder code in production paths

### Security
- [ ] No secrets in code or configuration
- [ ] Input validation at all API boundaries
- [ ] OWASP Top 10 compliance verified
- [ ] Authentication required for all non-public endpoints
- [ ] RLS policies verified for multi-tenant data

### Architecture Compliance
- [ ] Follows layer boundaries (presentation → service → repository)
- [ ] Dependencies flow inward (clean architecture)
- [ ] AI features respect human-in-the-loop principle
- [ ] Changes documented if affecting > 3 files
- [ ] Patterns align with dev-pattern guidelines

## Governance

This constitution supersedes all other practices and conventions in the Pilot Space project.

**Amendment Process**:
1. Propose changes via Pull Request to `.specify/memory/constitution.md`
2. Document rationale and impact assessment
3. Obtain approval from at least 2 maintainers
4. Update all dependent templates if principles change
5. Increment version according to semantic versioning

**Versioning Policy**:
- MAJOR: Backward-incompatible principle removals or redefinitions
- MINOR: New principle/section added or materially expanded guidance
- PATCH: Clarifications, wording, typo fixes

**Compliance Review**:
- All PRs MUST verify compliance with Core Principles
- Constitution Check in plan-template.md MUST be completed before implementation
- Violations MUST be documented with justification if proceeding

**Reference Documents**:
- `specs/001-pilot-space-mvp/spec.md` - Feature specification with clarifications
- `specs/001-pilot-space-mvp/plan.md` - Implementation plan with architecture decisions
- `docs/dev-pattern/` - Development patterns (load 45-pilot-space-patterns.md first)
- `docs/dev-pattern/README.md` - Pattern lookup and workflow guides
- `docs/DESIGN_DECISIONS.md` - Architectural decision records
- `.specify/templates/` - Implementation templates aligned with principles

**Version**: 1.2.1 | **Ratified**: 2026-01-20 | **Last Amended**: 2026-01-26
