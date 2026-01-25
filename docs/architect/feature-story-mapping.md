# Feature-to-Architecture Mapping

**Status**: Active
**Source**: `specs/001-pilot-space-mvp/spec.md` v3.0
**Last Updated**: 2026-01-22

This document maps the 18 user stories from the MVP specification to their corresponding architecture components, services, data entities, and AI agents.

---

## User Story Priority Overview

| Priority | Stories | Focus Area |
|----------|---------|------------|
| **P0** | US-01 | Note-First Foundation |
| **P1** | US-02, US-03, US-04, US-12, US-18 | Core Workflow |
| **P2** | US-05, US-06, US-07, US-08, US-09, US-13, US-14, US-15, US-17 | Enhanced Features |
| **P3** | US-10, US-11, US-16 | Supporting Features |

---

## P0: Foundation

### US-01: Note-First Collaborative Writing

> "As a developer, I want AI-augmented notes as my default workspace view so that I can brainstorm with AI assistance before creating formal issues."

**Priority**: P0 (Foundational)
**Acceptance Scenarios**: 18

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | TipTap Editor | Block-based rich text editing |
| **Frontend** | GhostTextExtension | AI typing suggestions (500ms pause trigger) |
| **Frontend** | MarginAnnotationPanel | Right-margin AI suggestions |
| **Frontend** | NoteStore (MobX) | Note canvas state management |
| **Frontend** | GhostTextStore (MobX) | Ghost text state + debounce |
| **Backend** | NoteService | Note CRUD operations |
| **Backend** | GhostTextAgent | Generate continuation suggestions |
| **Backend** | IssueExtractorAgent | Extract issues from note content |
| **AI** | Claude Agent SDK | Ghost text generation |
| **Realtime** | Supabase Realtime | Multi-user note collaboration |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Note` | id, title, content (JSONB), workspace_id, created_by_id | TipTap JSON in `content` field |
| `NoteAnnotation` | id, note_id, block_id, annotation_type, suggestion_text | AI suggestions linked to blocks |
| `NoteIssueLink` | note_id, issue_id, linked_at | Notes → Issues extracted |

#### Key Decisions

- **Note Storage**: JSONB (TipTap native format), not separate blocks table
- **Ghost Text Trigger**: 500ms pause in typing
- **Context**: Current block + 3 previous blocks + 3 sections summary + user history
- **Max Tokens**: 50 tokens for ghost text suggestions
- **Autosave**: 2-second debounce after last keystroke

---

## P1: Core Workflow

### US-02: Create and Manage Issues with AI

> "As a developer, I want to create issues with AI-suggested enhancements so that my issues are well-structured from the start."

**Priority**: P1 (Core)
**Acceptance Scenarios**: 8

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | IssueForm | Issue creation/editing form |
| **Frontend** | IssueStore (MobX) | Issue state management |
| **Frontend** | DuplicateSuggestionPanel | Show potential duplicates |
| **Backend** | IssueService | Issue CRUD + state machine |
| **Backend** | CreateIssueService | CQRS-lite service class |
| **Backend** | IssueEnhancerAgent | Suggest labels, priority, AC |
| **Backend** | DuplicateDetectorAgent | Find similar issues |
| **AI** | Semantic Search | Find duplicates via embeddings |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Issue` | id, title, description, state_name, priority, estimate_points | Main work item |
| `Label` | id, name, color, project_id | Issue categorization |
| `IssueLabel` | issue_id, label_id | Many-to-many junction |
| `IssueLink` | from_issue_id, to_issue_id, link_type | blocks/relates_to/duplicates |

#### Key Decisions

- **State Machine**: Backlog → Started → Completed (→Cancelled as terminal)
- **Duplicate Detection**: Semantic similarity > 0.85 threshold
- **AI Confidence**: Only show "Recommended" tag for ≥80% confidence

---

### US-03: Receive AI Code Review on PRs

> "As a developer, I want automated AI code review when I open a pull request so that I get immediate feedback on architecture, code quality, and security."

**Priority**: P1 (Core)
**Acceptance Scenarios**: 5

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Backend** | GitHubWebhookHandler | Receive PR events |
| **Backend** | PRReviewAgent | Unified code review (architecture + quality + security) |
| **Backend** | GitHubAppClient | Post review comments |
| **Queue** | Supabase Queues (pgmq) | Async PR review processing |
| **Scheduler** | pg_cron | Process queue every minute |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Integration` | id, type (github), workspace_id, config | GitHub App credentials |
| `IntegrationLink` | issue_id, integration_id, external_id, external_url | PR → Issue link |
| `Activity` | id, issue_id, action, metadata | Record review activity |

#### Key Decisions

- **Review Type**: Unified review (not separate passes)
- **Severity Levels**: info/warning/error inline comments
- **Async Processing**: Queue-based, not blocking webhook
- **Auto-Transition**: PR merged → Issue state to Completed (if linked)

---

### US-04: Plan and Track Sprints

> "As a team lead, I want to manage cycles/sprints with velocity tracking so that I can plan work capacity."

**Priority**: P1 (Core)
**Acceptance Scenarios**: 5

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | CycleBoard | Sprint planning board |
| **Frontend** | VelocityChart | Historical velocity visualization |
| **Frontend** | BurndownChart | Sprint progress tracking |
| **Backend** | CycleService | Cycle CRUD + metrics |
| **Backend** | VelocityCalculator | Compute velocity from history |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Cycle` | id, name, start_date, end_date, project_id, status | Sprint container |
| `Issue.cycle_id` | FK to Cycle | Issues assigned to sprint |
| `Issue.estimate_points` | integer | Story points for velocity |

#### Key Decisions

- **Velocity Calculation**: Sum of completed story points in cycle
- **Burndown**: Daily calculation of remaining points
- **Historical Data**: Last 6 cycles for velocity prediction

---

### US-12: AI Context for Issues

> "As a developer, I want aggregated AI context for any issue so that I can understand related documents, code, and tasks without manual search."

**Priority**: P1 (Core)
**Acceptance Scenarios**: 10

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | AIContextTab | Display aggregated context |
| **Frontend** | TaskChecklist | AI-generated task breakdown |
| **Frontend** | ClaudeCodePromptPanel | Copy-ready prompts |
| **Backend** | AIContextAgent | Aggregate context from multiple sources |
| **Backend** | CodeContextExtractor | Find related code files |
| **Backend** | GenerateAIContextCommand | CQRS-lite use case |
| **RAG** | pgvector + Meilisearch | Semantic search for related content |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `AIContext` | id, issue_id, context_data (JSONB), generated_at | Cached aggregated context |
| `Embedding` | id, content, embedding (vector), source_type, source_id | RAG embeddings |

#### Key Decisions

- **Context Sources**: Related notes, linked issues, code files, activity history
- **Claude Code Prompts**: Pre-formatted for copy-paste into Claude Code
- **Refresh**: Manual refresh button + auto-refresh on significant changes
- **Caching**: 1-hour TTL for context cache

---

### US-18: Link and Track GitHub Repositories

> "As a developer, I want to link my GitHub repositories so that commits and PRs automatically appear on related issues."

**Priority**: P1 (Core)
**Acceptance Scenarios**: 10

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | GitHubIntegrationSettings | OAuth + repo selection |
| **Frontend** | CommitActivityFeed | Show linked commits/PRs |
| **Backend** | GitHubAppService | GitHub App installation |
| **Backend** | CommitLinkerAgent | Parse commit messages for issue refs |
| **Backend** | PRSyncService | Sync PR status with issues |
| **Webhook** | GitHubWebhookRouter | Route push/PR events |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Integration` | id, type, workspace_id, installation_id | GitHub App installation |
| `IntegrationLink` | id, issue_id, integration_id, external_id, external_url | Commit/PR links |
| `Activity` | id, issue_id, action (commit_linked/pr_opened/pr_merged) | Activity log |

#### Key Decisions

- **Issue Reference**: Parse `#123` or `PROJ-123` from commit messages
- **Auto-Transition**: PR merged → Issue to Completed (configurable)
- **Webhook Events**: push, pull_request, pull_request_review

---

## P2: Enhanced Features

### US-05: Organize Work with Modules/Epics

> "As a team lead, I want to group issues into modules/epics so that I can track progress on larger features."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 4

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | ModuleList | List/manage modules |
| **Frontend** | ModuleProgressBar | Aggregate progress |
| **Backend** | ModuleService | Module CRUD |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Module` | id, name, description, project_id, lead_id | Epic container |
| `Issue.module_id` | FK to Module | Issue belongs to module |

---

### US-06: Create and Maintain Documentation Pages

> "As a developer, I want rich documentation pages with AI-generated diagrams so that architecture is always up-to-date."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 5

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | PageEditor (TipTap) | Documentation editor |
| **Frontend** | MermaidPreview | Render Mermaid diagrams |
| **Backend** | PageService | Page CRUD |
| **Backend** | DocGeneratorAgent | Generate docs from code |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Page` | id, title, content (JSONB), project_id | Documentation page |

---

### US-07: Decompose Features into Tasks with AI

> "As a developer, I want AI to break down a feature into sub-tasks so that work is properly scoped."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 4

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | TaskDecomposeModal | Trigger decomposition |
| **Frontend** | SubtaskList | Display/manage subtasks |
| **Backend** | TaskDecomposerAgent | AI task breakdown |
| **Backend** | IssueService | Create subtask issues |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Issue.parent_id` | FK to parent Issue | Hierarchical issues |

---

### US-08: Generate Architecture Diagrams

> "As a developer, I want AI to generate architecture diagrams from descriptions so that documentation stays current."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 3

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | DiagramEditor | Edit/preview diagrams |
| **Frontend** | MermaidRenderer | Render Mermaid DSL |
| **Backend** | DiagramGeneratorAgent | Generate Mermaid from text |

#### Key Decisions

- **Format**: Mermaid DSL (default), PlantUML (optional)
- **Types**: Sequence, class, flowchart, C4 diagrams

---

### US-09: Receive Notifications via Slack

> "As a developer, I want Slack notifications for important events so that I stay informed without checking the app."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 4

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Backend** | SlackIntegrationService | Slack App setup |
| **Backend** | SlackNotificationService | Send rich block messages |
| **Backend** | SlackCommandHandler | Handle `/pilot` commands |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Integration` | type=slack, channel_id, bot_token | Slack workspace |
| `Notification` | id, user_id, type, content, delivered_at | Notification log |

---

### US-13: Navigate with Command Palette and Search

> "As a developer, I want a command palette and fuzzy search so that I can quickly navigate anywhere."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 3

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | CommandPalette (⌘K) | Quick navigation |
| **Frontend** | FuzzySearch | Search across entities |
| **Backend** | SearchService | Unified search endpoint |
| **Search** | Meilisearch | Typo-tolerant search |

---

### US-14: Explore Knowledge Graph

> "As a developer, I want to visualize relationships between notes, issues, and code so that I can discover connections."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 3

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | KnowledgeGraphCanvas | Sigma.js visualization |
| **Backend** | GraphService | Build relationship graph |
| **Backend** | PatternDetectorAgent | Find recurring patterns |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `KnowledgeGraphRelationship` | source_id, target_id, relationship_type | Graph edges |

---

### US-15: Use Templates for New Notes

> "As a developer, I want templates for common note types so that I start with structure."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 3

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | TemplateGallery | Browse/select templates |
| **Frontend** | ConversationalFiller | AI template completion |
| **Backend** | TemplateService | Template CRUD |
| **Backend** | TemplateFillerAgent | Fill template with AI |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Template` | id, name, content (JSONB), category | Note template |

---

### US-17: Receive AI-Prioritized Notifications

> "As a developer, I want AI to prioritize my notifications so that I focus on what matters."

**Priority**: P2 (Secondary)
**Acceptance Scenarios**: 3

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | NotificationCenter | Display prioritized notifications |
| **Frontend** | PriorityBadges | Visual priority indicators |
| **Backend** | NotificationPrioritizerAgent | Score notification importance |

---

## P3: Supporting Features

### US-10: Search Across Workspace Content

> "As a developer, I want semantic search across all workspace content so that I can find relevant information."

**Priority**: P3 (Tertiary)
**Acceptance Scenarios**: 3

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | SemanticSearchModal | Advanced search UI |
| **Backend** | SemanticSearchAgent | Vector similarity search |
| **RAG** | pgvector | Vector embeddings |
| **Search** | Meilisearch | Full-text search |

---

### US-11: Configure Workspace and AI Settings

> "As a workspace admin, I want to configure AI providers and settings so that the team uses preferred models."

**Priority**: P3 (Tertiary)
**Acceptance Scenarios**: 4

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | WorkspaceSettings | Settings UI |
| **Frontend** | APIKeyVault | Secure key entry |
| **Backend** | SettingsService | Settings CRUD |
| **Security** | Supabase Vault | Encrypted key storage |

#### Data Entities

| Entity | Key Fields | Notes |
|--------|------------|-------|
| `Workspace` | id, name, settings (JSONB) | Workspace config |
| `AIConfiguration` | workspace_id, provider, api_key_ref | BYOK config |

---

### US-16: Onboard with Sample Project

> "As a new user, I want a sample project with demo data so that I can explore features."

**Priority**: P3 (Tertiary)
**Acceptance Scenarios**: 2

#### Architecture Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Frontend** | OnboardingFlow | Guided onboarding |
| **Backend** | SampleDataGenerator | Create demo data |
| **Seed** | Seed script | Initial data population |

---

## AI Agents Summary

| Agent | User Stories | Primary Purpose |
|-------|-------------|-----------------|
| **GhostTextAgent** | US-01 | Typing continuation suggestions |
| **IssueExtractorAgent** | US-01 | Extract issues from notes |
| **IssueEnhancerAgent** | US-02 | Suggest labels, priority, AC |
| **DuplicateDetectorAgent** | US-02 | Find similar issues |
| **PRReviewAgent** | US-03 | Unified code review |
| **AIContextAgent** | US-12 | Aggregate issue context |
| **CommitLinkerAgent** | US-18 | Parse commit refs |
| **TaskDecomposerAgent** | US-07 | Break features into tasks |
| **DiagramGeneratorAgent** | US-08 | Generate Mermaid diagrams |
| **DocGeneratorAgent** | US-06 | Generate docs from code |
| **TemplateFillerAgent** | US-15 | Fill templates with AI |
| **PatternDetectorAgent** | US-14 | Find knowledge patterns |
| **SemanticSearchAgent** | US-10 | Vector similarity search |
| **NotificationPrioritizerAgent** | US-17 | Score notification importance |

---

## Implementation Phases (from plan.md v4.0)

### Phase 1: Foundation
- US-01 (Note-First Writing) - **Core differentiator**
- US-02 (Issue Management) - **Core workflow**

### Phase 2: AI Integration
- US-03 (PR Review) - **GitHub integration**
- US-12 (AI Context) - **Claude Code integration**
- US-18 (GitHub Linking) - **Commit/PR sync**

### Phase 3: Team Features
- US-04 (Sprint Planning)
- US-05 (Modules/Epics)
- US-09 (Slack Notifications)

### Phase 4: Enhanced UX
- US-06, US-07, US-08 (Documentation + Decomposition)
- US-10, US-13, US-14 (Search + Navigation)
- US-11, US-15, US-16, US-17 (Settings + Templates + Onboarding)

---

## Related Documents

- [Specification](../../specs/001-pilot-space-mvp/spec.md) - Full user story details
- [Implementation Plan](../../specs/001-pilot-space-mvp/plan.md) - Architecture decisions
- [Data Model](../../specs/001-pilot-space-mvp/data-model.md) - Entity relationships
- [AI Layer Architecture](./ai-layer.md) - Agent implementation details
- [Backend Architecture](./backend-architecture.md) - Service patterns
