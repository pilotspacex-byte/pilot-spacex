# PilotSpace — AI-Augmented SDLC Platform

PilotSpace is an AI-augmented Software Development Lifecycle platform built on a **Note-First** paradigm. Users write freely in a collaborative note canvas, and AI assists with inline completions, issue extraction, margin annotations, and contextual code reviews.

## Core Principles

- **Note-First**: Think first, structure later. Notes are the primary artifact; issues emerge naturally through AI-powered extraction.
- **Human-in-the-Loop (DD-003)**: All destructive AI actions require explicit user approval. Non-dismissable modals with 24h countdown for critical operations.
- **BYOK (DD-002)**: Bring Your Own Key. Workspaces store their own AI provider API keys — no cost pass-through from the platform.
- **Multi-Tenant RLS**: Row-Level Security enforced at the PostgreSQL level. Every query is scoped to `workspace_id`.

## Platform Scale

- **Target**: 5–100 members per workspace
- **Features**: 17 core features across notes, issues, cycles, projects, AI chat, approvals, integrations
- **Design Decisions**: 88 documented (see `docs/DESIGN_DECISIONS.md`)

## Tech Stack

| Layer        | Technology                                                                          |
| ------------ | ----------------------------------------------------------------------------------- |
| **Frontend** | Next.js 15+ (App Router), React 19, MobX + TanStack Query, shadcn/ui, TipTap Editor |
| **Backend**  | Python 3.12+, FastAPI, SQLAlchemy 2.0 async, dependency-injector                    |
| **Database** | PostgreSQL 16 + pgvector + pgmq, Redis 7, Meilisearch                               |
| **Auth**     | Supabase Auth (JWT + RLS), SAML SSO                                                 |
| **AI**       | Claude Agent SDK, 33 MCP tools, multi-provider routing                              |
| **Infra**    | Docker Compose (dev), Kubernetes + Helm (enterprise), GitHub Actions CI/CD          |

## Monorepo Structure

```text
backend/       Python FastAPI — Clean Architecture, CQRS-lite
frontend/      Next.js App Router — MobX + TanStack Query, shadcn/ui
cli/           pilot-cli — login, implement commands
authcore/      Supabase Auth self-hosted (optional)
infra/         Docker, Kubernetes, Terraform
docs/          Design decisions, dev patterns (68 pattern files)
specs/         Feature specifications (28 spec directories)
```

## Key Design Decisions

| DD     | Decision                            | Rationale                                                        |
| ------ | ----------------------------------- | ---------------------------------------------------------------- |
| DD-002 | BYOK model                          | No AI cost pass-through; user controls their own API keys        |
| DD-003 | Human-in-the-loop approvals         | Non-dismissable modal, 24h countdown for destructive actions     |
| DD-011 | Task-based provider routing         | Route each task type to optimal model (Opus/Sonnet/Haiku/OpenAI) |
| DD-013 | Note-First paradigm                 | Users think in documents; issues emerge via extraction           |
| DD-065 | MobX (UI) + TanStack Query (server) | Clear separation of concerns for state management                |
| DD-086 | Centralized PilotSpaceAgent         | Single orchestrator routes to skills, subagents, and MCP tools   |
