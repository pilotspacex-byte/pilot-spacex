# Project Structure

Complete directory layout for the Pilot Space monorepo following Clean Architecture principles.

---

## Repository Root

```
pilot-space/
├── backend/                    # FastAPI backend application
├── frontend/                   # Next.js frontend application
├── infra/                      # Infrastructure configuration
├── design-system/              # Shared UI component library
├── docs/                       # Documentation
├── specs/                      # Feature specifications
├── .claude/                    # Claude Code configuration
├── .specify/                   # Speckit templates
├── .github/                    # GitHub workflows
├── CLAUDE.md                   # AI assistant instructions
├── .gitignore
├── .env.example
└── README.md
```

---

## Backend Structure

```
backend/
├── src/
│   └── pilot_space/
│       ├── __init__.py
│       ├── main.py                          # FastAPI application factory
│       ├── config.py                        # Settings (Pydantic BaseSettings)
│       ├── container.py                     # Dependency injection container
│       │
│       ├── api/                             # PRESENTATION LAYER
│       │   ├── __init__.py
│       │   ├── dependencies.py              # FastAPI dependencies
│       │   ├── middleware/
│       │   │   ├── __init__.py
│       │   │   ├── auth.py                  # Supabase Auth (GoTrue) + JWT
│       │   │   ├── error_handler.py         # Global exception handling
│       │   │   ├── rate_limiter.py          # Rate limiting middleware
│       │   │   ├── correlation_id.py        # Request tracing
│       │   │   └── logging.py               # Request/response logging
│       │   ├── v1/
│       │   │   ├── __init__.py
│       │   │   ├── routers/
│       │   │   │   ├── __init__.py          # Router aggregation
│       │   │   │   ├── auth.py              # /auth - login, logout, refresh
│       │   │   │   ├── users.py             # /users - user profile
│       │   │   │   ├── workspaces.py        # /workspaces - CRUD
│       │   │   │   ├── projects.py          # /projects - CRUD
│       │   │   │   ├── issues.py            # /issues - CRUD + AI enhance
│       │   │   │   ├── notes.py             # /notes - CRUD + ghost text
│       │   │   │   ├── pages.py             # /pages - documentation
│       │   │   │   ├── cycles.py            # /cycles - sprints
│       │   │   │   ├── modules.py           # /modules - epics
│       │   │   │   ├── labels.py            # /labels - tags
│       │   │   │   ├── ai.py                # /ai - AI feature endpoints
│       │   │   │   ├── search.py            # /search - semantic search
│       │   │   │   ├── integrations.py      # /integrations - GitHub/Slack
│       │   │   │   ├── webhooks.py          # /webhooks - outbound config
│       │   │   │   └── health.py            # /health - health checks
│       │   │   └── schemas/                 # Pydantic request/response DTOs
│       │   │       ├── __init__.py
│       │   │       ├── base.py              # BaseSchema, pagination
│       │   │       ├── auth.py              # Auth DTOs
│       │   │       ├── user.py              # User DTOs
│       │   │       ├── workspace.py         # Workspace DTOs
│       │   │       ├── project.py           # Project DTOs
│       │   │       ├── issue.py             # Issue DTOs
│       │   │       ├── note.py              # Note DTOs
│       │   │       ├── page.py              # Page DTOs
│       │   │       ├── cycle.py             # Cycle DTOs
│       │   │       ├── module.py            # Module DTOs
│       │   │       ├── ai.py                # AI response DTOs
│       │   │       └── integration.py       # Integration DTOs
│       │   └── webhooks/                    # Inbound webhook handlers
│       │       ├── __init__.py
│       │       ├── github.py                # GitHub App webhooks
│       │       └── slack.py                 # Slack Events API
│       │
│       ├── application/                     # APPLICATION LAYER
│       │   ├── __init__.py
│       │   ├── services/                    # Command/Query service handlers
│       │   │   ├── __init__.py
│       │   │   ├── workspace/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── create_workspace.py
│       │   │   │   ├── update_workspace.py
│       │   │   │   ├── delete_workspace.py
│       │   │   │   ├── invite_member.py
│       │   │   │   ├── remove_member.py
│       │   │   │   └── update_settings.py
│       │   │   ├── project/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── create_project.py
│       │   │   │   ├── update_project.py
│       │   │   │   └── delete_project.py
│       │   │   ├── issue/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── create_issue.py
│       │   │   │   ├── update_issue.py
│       │   │   │   ├── delete_issue.py
│       │   │   │   ├── change_state.py
│       │   │   │   ├── assign_issue.py
│       │   │   │   ├── ai_enhance_issue.py
│       │   │   │   ├── extract_from_note.py
│       │   │   │   └── get_ai_context.py
│       │   │   ├── note/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── create_note.py
│       │   │   │   ├── update_note.py
│       │   │   │   ├── delete_note.py
│       │   │   │   ├── get_ghost_text.py
│       │   │   │   └── extract_issues.py
│       │   │   ├── cycle/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── create_cycle.py
│       │   │   │   ├── update_cycle.py
│       │   │   │   └── complete_cycle.py
│       │   │   ├── ai/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── generate_pr_review.py
│       │   │   │   ├── decompose_tasks.py
│       │   │   │   ├── generate_documentation.py
│       │   │   │   ├── generate_diagram.py
│       │   │   │   └── semantic_search.py
│       │   │   └── integration/
│       │   │       ├── __init__.py
│       │   │       ├── link_github_repo.py
│       │   │       ├── process_pr_event.py
│       │   │       ├── process_commit_event.py
│       │   │       └── configure_slack.py
│       │   ├── shared/                      # Shared application concerns
│       │   │   ├── __init__.py
│       │   │   ├── auth_service.py          # Token validation, user sync
│       │   │   ├── permission_service.py    # RBAC checks
│       │   │   └── notification_service.py  # In-app + Slack notifications
│       │   └── interfaces/                  # Port interfaces for infra
│       │       ├── __init__.py
│       │       ├── unit_of_work.py          # UoW pattern interface
│       │       └── event_publisher.py       # Domain event publishing
│       │
│       ├── domain/                          # DOMAIN LAYER (Pure Python)
│       │   ├── __init__.py
│       │   ├── entities/                    # Aggregates and Entities
│       │   │   ├── __init__.py
│       │   │   ├── workspace.py             # Workspace aggregate root
│       │   │   ├── project.py               # Project aggregate root
│       │   │   ├── issue.py                 # Issue aggregate root
│       │   │   ├── note.py                  # Note aggregate root
│       │   │   ├── note_block.py            # Note block entity
│       │   │   ├── note_annotation.py       # AI annotation entity
│       │   │   ├── cycle.py                 # Cycle entity
│       │   │   ├── module.py                # Module entity
│       │   │   ├── page.py                  # Page entity
│       │   │   ├── user.py                  # User entity
│       │   │   ├── label.py                 # Label entity
│       │   │   ├── activity.py              # Activity log entity
│       │   │   ├── template.py              # Template entity
│       │   │   └── ai_context.py            # AI context entity
│       │   ├── value_objects/               # Immutable value objects
│       │   │   ├── __init__.py
│       │   │   ├── identifiers.py           # WorkspaceId, ProjectId, etc.
│       │   │   ├── issue_identifier.py      # PS-123 format
│       │   │   ├── priority.py              # Priority enum
│       │   │   ├── issue_state.py           # State with group
│       │   │   ├── role.py                  # Role enum
│       │   │   ├── email_address.py         # Validated email
│       │   │   ├── slug.py                  # URL-safe slug
│       │   │   └── ai_confidence.py         # Confidence level
│       │   ├── services/                    # Domain services (pure logic)
│       │   │   ├── __init__.py
│       │   │   ├── issue_identifier_generator.py
│       │   │   ├── duplicate_detector.py
│       │   │   └── note_issue_sync.py       # Bidirectional sync logic
│       │   ├── repositories/                # Repository interfaces (ABC)
│       │   │   ├── __init__.py
│       │   │   ├── workspace_repository.py
│       │   │   ├── project_repository.py
│       │   │   ├── issue_repository.py
│       │   │   ├── note_repository.py
│       │   │   ├── cycle_repository.py
│       │   │   ├── module_repository.py
│       │   │   ├── page_repository.py
│       │   │   └── user_repository.py
│       │   ├── events/                      # Domain events
│       │   │   ├── __init__.py
│       │   │   ├── base.py                  # DomainEvent base class
│       │   │   ├── workspace_events.py
│       │   │   ├── project_events.py
│       │   │   ├── issue_events.py          # IssueCreated, StateChanged
│       │   │   ├── note_events.py           # NoteCreated, IssueExtracted
│       │   │   └── integration_events.py    # PRLinked, CommitLinked
│       │   └── exceptions/                  # Domain-specific exceptions
│       │       ├── __init__.py
│       │       ├── base.py                  # DomainError base
│       │       ├── workspace.py
│       │       ├── project.py
│       │       ├── issue.py
│       │       ├── note.py
│       │       └── permission.py
│       │
│       ├── infrastructure/                  # INFRASTRUCTURE LAYER
│       │   ├── __init__.py
│       │   ├── persistence/                 # Database implementations
│       │   │   ├── __init__.py
│       │   │   ├── database.py              # AsyncEngine, AsyncSession
│       │   │   ├── models/                  # SQLAlchemy ORM models
│       │   │   │   ├── __init__.py
│       │   │   │   ├── base.py              # Base model with soft delete
│       │   │   │   ├── workspace.py
│       │   │   │   ├── project.py
│       │   │   │   ├── issue.py
│       │   │   │   ├── note.py
│       │   │   │   ├── page.py
│       │   │   │   ├── cycle.py
│       │   │   │   ├── module.py
│       │   │   │   ├── user.py
│       │   │   │   ├── label.py
│       │   │   │   ├── activity.py
│       │   │   │   ├── integration.py
│       │   │   │   ├── ai_config.py
│       │   │   │   └── embedding.py         # pgvector embeddings
│       │   │   ├── repositories/            # Repository implementations
│       │   │   │   ├── __init__.py
│       │   │   │   ├── sqlalchemy_workspace_repo.py
│       │   │   │   ├── sqlalchemy_project_repo.py
│       │   │   │   ├── sqlalchemy_issue_repo.py
│       │   │   │   ├── sqlalchemy_note_repo.py
│       │   │   │   ├── sqlalchemy_cycle_repo.py
│       │   │   │   └── sqlalchemy_user_repo.py
│       │   │   ├── unit_of_work.py          # SQLAlchemy UoW implementation
│       │   │   └── migrations/              # Alembic migrations
│       │   │       ├── env.py
│       │   │       ├── script.py.mako
│       │   │       └── versions/
│       │   │           └── 001_initial.py
│       │   ├── cache/
│       │   │   ├── __init__.py
│       │   │   └── redis_cache.py           # Redis client wrapper
│       │   ├── search/
│       │   │   ├── __init__.py
│       │   │   └── meilisearch_client.py    # Search indexing/querying
│       │   ├── storage/
│       │   │   ├── __init__.py
│       │   │   └── supabase_storage.py      # Supabase Storage (S3-compatible)
│       │   ├── queue/                       # Async task queue
│       │   │   ├── __init__.py
│       │   │   ├── supabase_queue.py        # Supabase Queues (pgmq) client
│       │   │   ├── handlers/                # Queue job handlers
│       │   │   │   ├── __init__.py
│       │   │   │   ├── ai_handlers.py       # PR review, decomposition
│       │   │   │   ├── embedding_handlers.py # Vector indexing
│       │   │   │   ├── notification_handlers.py
│       │   │   │   └── sync_handlers.py     # Integration sync
│       │   │   └── event_handlers/          # Domain event consumers
│       │   │       ├── __init__.py
│       │   │       ├── issue_event_handler.py
│       │   │       └── note_event_handler.py
│       │   ├── auth/
│       │   │   ├── __init__.py
│       │   │   ├── supabase_auth.py         # Supabase Auth (GoTrue) client
│       │   │   └── jwt_handler.py           # JWT utilities
│       │   └── external/                    # External service adapters
│       │       ├── __init__.py
│       │       ├── github/
│       │       │   ├── __init__.py
│       │       │   ├── client.py            # GitHub App client
│       │       │   ├── webhook_handler.py   # Webhook processing
│       │       │   └── models.py            # GitHub-specific DTOs
│       │       └── slack/
│       │           ├── __init__.py
│       │           ├── client.py            # Slack Bolt app
│       │           ├── commands.py          # Slash command handlers
│       │           └── notifications.py     # Message formatting
│       │
│       └── ai/                              # AI LAYER (Cross-cutting)
│           ├── __init__.py
│           ├── orchestrator.py              # Task routing + provider selection
│           ├── providers/                   # LLM provider adapters
│           │   ├── __init__.py
│           │   ├── base.py                  # LLMProvider ABC
│           │   ├── openai_provider.py
│           │   ├── anthropic_provider.py
│           │   ├── google_provider.py
│           │   └── azure_provider.py
│           ├── agents/                      # Domain-specific AI agents
│           │   ├── __init__.py
│           │   ├── base.py                  # BaseAgent ABC
│           │   ├── ghost_text_agent.py      # Real-time suggestions
│           │   ├── issue_enhancer_agent.py  # Title/description improvement
│           │   ├── pr_review_agent.py       # Code review
│           │   ├── task_decomposer_agent.py # Feature → subtasks
│           │   ├── doc_generator_agent.py   # Documentation from code
│           │   ├── diagram_generator_agent.py # Mermaid/PlantUML
│           │   ├── duplicate_detector_agent.py
│           │   └── ai_context_agent.py      # Context aggregation
│           ├── prompts/                     # Prompt templates
│           │   ├── __init__.py
│           │   ├── ghost_text.py
│           │   ├── issue_enhancement.py
│           │   ├── pr_review.py
│           │   ├── task_decomposition.py
│           │   └── diagram_generation.py
│           └── rag/                         # RAG pipeline
│               ├── __init__.py
│               ├── embedder.py              # Text → vector
│               ├── chunker.py               # Content chunking
│               ├── retriever.py             # Semantic search
│               └── indexer.py               # Index management
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                          # Shared fixtures
│   ├── unit/
│   │   ├── domain/                          # Pure domain logic tests
│   │   │   ├── test_issue.py
│   │   │   ├── test_note.py
│   │   │   └── test_value_objects.py
│   │   ├── application/                     # Use case tests
│   │   │   ├── test_create_issue.py
│   │   │   └── test_extract_issues.py
│   │   └── ai/                              # AI agent tests
│   │       ├── test_ghost_text_agent.py
│   │       └── test_pr_review_agent.py
│   ├── integration/
│   │   ├── api/                             # API endpoint tests
│   │   │   ├── test_issues_api.py
│   │   │   └── test_notes_api.py
│   │   ├── persistence/                     # Repository tests
│   │   │   ├── test_issue_repository.py
│   │   │   └── test_note_repository.py
│   │   └── external/                        # Integration tests
│   │       ├── test_github_client.py
│   │       └── test_slack_client.py
│   └── e2e/                                 # End-to-end API tests
│       ├── test_issue_workflow.py
│       └── test_note_workflow.py
│
├── pyproject.toml                           # uv dependencies
├── alembic.ini                              # Alembic configuration
├── pytest.ini                               # Pytest configuration
├── .ruff.toml                               # Ruff linter config
├── pyrightconfig.json                       # Pyright config
└── Dockerfile
```

---

## Frontend Structure

```
frontend/
├── src/
│   ├── app/                                 # Next.js App Router
│   │   ├── layout.tsx                       # Root layout (providers)
│   │   ├── page.tsx                         # Landing / redirect
│   │   ├── globals.css                      # TailwindCSS imports
│   │   ├── not-found.tsx                    # 404 page
│   │   ├── error.tsx                        # Error boundary
│   │   │
│   │   ├── (auth)/                          # Auth routes (no sidebar)
│   │   │   ├── layout.tsx                   # Centered auth layout
│   │   │   ├── login/page.tsx
│   │   │   ├── callback/page.tsx            # OAuth callback
│   │   │   └── logout/page.tsx
│   │   │
│   │   ├── (workspace)/                     # Authenticated routes
│   │   │   ├── layout.tsx                   # Sidebar + Header layout
│   │   │   └── [workspaceSlug]/
│   │   │       ├── page.tsx                 # Workspace home (Note Canvas)
│   │   │       ├── notes/
│   │   │       │   ├── page.tsx             # Notes list
│   │   │       │   ├── [noteId]/
│   │   │       │   │   ├── page.tsx         # Note editor
│   │   │       │   │   └── loading.tsx
│   │   │       │   └── new/page.tsx         # New note with AI
│   │   │       ├── projects/
│   │   │       │   ├── page.tsx             # Projects list
│   │   │       │   └── [projectId]/
│   │   │       │       ├── page.tsx         # Project overview
│   │   │       │       ├── issues/
│   │   │       │       │   ├── page.tsx     # Issue board/list
│   │   │       │       │   ├── [issueId]/
│   │   │       │       │   │   ├── page.tsx # Issue detail
│   │   │       │       │   │   └── loading.tsx
│   │   │       │       │   └── new/page.tsx
│   │   │       │       ├── cycles/
│   │   │       │       │   ├── page.tsx
│   │   │       │       │   └── [cycleId]/page.tsx
│   │   │       │       ├── modules/
│   │   │       │       │   └── page.tsx
│   │   │       │       ├── pages/
│   │   │       │       │   ├── page.tsx
│   │   │       │       │   └── [pageId]/page.tsx
│   │   │       │       └── settings/
│   │   │       │           └── page.tsx
│   │   │       ├── settings/
│   │   │       │   ├── page.tsx             # Workspace settings
│   │   │       │   ├── members/page.tsx
│   │   │       │   ├── ai/page.tsx          # AI provider config
│   │   │       │   └── integrations/page.tsx
│   │   │       └── search/page.tsx          # Full-page search
│   │   │
│   │   ├── (public)/                        # Public views
│   │   │   ├── layout.tsx
│   │   │   └── [workspaceSlug]/
│   │   │       └── [projectSlug]/
│   │   │           └── issues/
│   │   │               └── [issueId]/page.tsx
│   │   │
│   │   └── api/                             # API routes (BFF)
│   │       ├── auth/
│   │       │   ├── login/route.ts
│   │       │   ├── callback/route.ts
│   │       │   └── refresh/route.ts
│   │       └── ai/
│   │           └── ghost-text/route.ts
│   │
│   ├── components/                          # React components
│   │   ├── ui/                              # Base UI (shadcn/ui style)
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── avatar.tsx
│   │   │   ├── select.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── toast.tsx
│   │   │   ├── skeleton.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── command.tsx
│   │   │   ├── popover.tsx
│   │   │   ├── tooltip.tsx
│   │   │   └── index.ts
│   │   ├── editor/                          # TipTap editor
│   │   │   ├── NoteCanvas.tsx
│   │   │   ├── extensions/
│   │   │   │   ├── ghost-text.ts
│   │   │   │   ├── block-id.ts
│   │   │   │   ├── slash-commands.ts
│   │   │   │   └── mentions.ts
│   │   │   ├── GhostTextOverlay.tsx
│   │   │   ├── MarginAnnotations.tsx
│   │   │   ├── IssueExtractionBox.tsx
│   │   │   ├── SelectionToolbar.tsx
│   │   │   ├── ThreadedDiscussion.tsx
│   │   │   └── TableOfContents.tsx
│   │   ├── issues/
│   │   │   ├── IssueCard.tsx
│   │   │   ├── IssueDetail.tsx
│   │   │   ├── IssueBoard.tsx
│   │   │   ├── IssueList.tsx
│   │   │   ├── IssueCreateModal.tsx
│   │   │   ├── IssueQuickView.tsx
│   │   │   ├── AIContext.tsx
│   │   │   └── AIContextTasks.tsx
│   │   ├── cycles/
│   │   │   ├── CycleBoard.tsx
│   │   │   ├── CycleCard.tsx
│   │   │   └── BurndownChart.tsx
│   │   ├── navigation/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── SidebarProjects.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── CommandPalette.tsx
│   │   │   ├── SearchModal.tsx
│   │   │   ├── FAB.tsx
│   │   │   └── NotificationCenter.tsx
│   │   ├── ai/
│   │   │   ├── AIPanel.tsx
│   │   │   ├── AIStatusIndicator.tsx
│   │   │   ├── ConfidenceTags.tsx
│   │   │   ├── ArtifactPreview.tsx
│   │   │   └── ApprovalDialog.tsx
│   │   ├── integrations/
│   │   │   ├── GitHubSetup.tsx
│   │   │   ├── SlackSetup.tsx
│   │   │   ├── PRLinkBadge.tsx
│   │   │   └── CommitTimeline.tsx
│   │   └── layouts/
│   │       ├── AppShell.tsx
│   │       ├── AuthLayout.tsx
│   │       └── PublicLayout.tsx
│   │
│   ├── stores/                              # MobX stores
│   │   ├── RootStore.ts
│   │   ├── AuthStore.ts
│   │   ├── WorkspaceStore.ts
│   │   ├── ProjectStore.ts
│   │   ├── IssueStore.ts
│   │   ├── NoteStore.ts
│   │   ├── AIStore.ts
│   │   ├── UIStore.ts
│   │   └── context.tsx                      # StoreProvider
│   │
│   ├── hooks/                               # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useWorkspace.ts
│   │   ├── useProject.ts
│   │   ├── useIssues.ts
│   │   ├── useNotes.ts
│   │   ├── useGhostText.ts
│   │   ├── useAutosave.ts
│   │   ├── useCommandPalette.ts
│   │   ├── useKeyboardShortcuts.ts
│   │   └── useDragAndDrop.ts
│   │
│   ├── services/                            # API services
│   │   ├── api/
│   │   │   ├── client.ts                    # Base fetch wrapper
│   │   │   ├── workspaces.ts
│   │   │   ├── projects.ts
│   │   │   ├── issues.ts
│   │   │   ├── notes.ts
│   │   │   ├── cycles.ts
│   │   │   ├── ai.ts
│   │   │   └── integrations.ts
│   │   ├── ai/
│   │   │   ├── ghost-text.ts                # SSE streaming
│   │   │   └── suggestions.ts
│   │   └── auth/
│   │       └── supabase-auth.ts             # Supabase Auth client
│   │
│   ├── lib/                                 # Utilities
│   │   ├── cn.ts                            # classnames
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   ├── constants.ts
│   │   └── query-client.ts                  # TanStack Query config
│   │
│   ├── types/                               # TypeScript types
│   │   ├── workspace.ts
│   │   ├── project.ts
│   │   ├── issue.ts
│   │   ├── note.ts
│   │   ├── ai.ts
│   │   └── api.ts
│   │
│   └── styles/
│       └── tailwind.css
│
├── public/
│   ├── pilot-icon.svg
│   └── fonts/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│       └── playwright/
│
├── package.json
├── pnpm-lock.yaml
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── .eslintrc.js
├── jest.config.js
└── Dockerfile
```

---

## Infrastructure Structure

```
infra/
├── docker/
│   ├── docker-compose.yml           # Full stack for local dev
│   ├── docker-compose.prod.yml      # Production overrides
│   ├── docker-compose.test.yml      # Test environment
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── init-db.sql                  # Database initialization
│   └── supabase/
│       └── config.toml              # Supabase local config
│
├── kubernetes/                      # K8s manifests (Phase 2)
│   ├── base/
│   │   ├── namespace.yaml
│   │   ├── backend/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── hpa.yaml
│   │   ├── frontend/
│   │   └── ingress.yaml
│   ├── overlays/
│   │   ├── development/
│   │   ├── staging/
│   │   └── production/
│   └── kustomization.yaml
│
└── terraform/                       # Cloud infra (Phase 3)
    ├── modules/
    │   ├── vpc/
    │   ├── rds/
    │   ├── elasticache/
    │   └── eks/
    └── environments/
        ├── staging/
        └── production/
```

---

## Documentation Structure

```
docs/
├── architect/                       # Architecture documentation
│   ├── README.md                    # Overview
│   ├── backend-architecture.md
│   ├── frontend-architecture.md
│   ├── infrastructure.md
│   ├── project-structure.md         # This file
│   ├── design-patterns.md
│   └── ai-layer.md
│
├── dev-pattern/                     # Development patterns (68 files)
│   ├── 00-core-principles.md
│   ├── 01-anti-patterns.md
│   ├── ...
│   └── _SHARED/
│
├── AI_CAPABILITIES.md
├── DESIGN_DECISIONS.md
├── PILOT_SPACE_FEATURES.md
├── PROJECT_VISION.md
└── INTEGRATION_ARCHITECTURE.md
```

---

## Naming Conventions

### Files

| Type | Convention | Example |
|------|------------|---------|
| Python modules | snake_case | `create_issue.py` |
| TypeScript files | kebab-case or PascalCase | `IssueCard.tsx`, `use-issues.ts` |
| Test files | `test_*.py` or `*.test.ts` | `test_issue.py`, `IssueCard.test.tsx` |
| Config files | lowercase | `pyproject.toml`, `tsconfig.json` |

### Code

| Type | Convention | Example |
|------|------------|---------|
| Python classes | PascalCase | `IssueRepository` |
| Python functions | snake_case | `create_issue()` |
| Python constants | UPPER_SNAKE | `MAX_RETRIES` |
| TypeScript components | PascalCase | `IssueCard` |
| TypeScript hooks | camelCase with `use` prefix | `useIssues` |
| TypeScript types | PascalCase | `Issue`, `CreateIssueData` |

### Directories

| Layer | Convention | Example |
|-------|------------|---------|
| Domain entities | singular | `domain/entities/issue.py` |
| API routers | plural | `api/v1/routers/issues.py` |
| React components | PascalCase | `components/issues/IssueCard.tsx` |
| Hooks | camelCase | `hooks/useIssues.ts` |

---

## Related Documents

- [Backend Architecture](./backend-architecture.md) - Layer details
- [Frontend Architecture](./frontend-architecture.md) - Component patterns
- [Infrastructure](./infrastructure.md) - Docker and deployment
