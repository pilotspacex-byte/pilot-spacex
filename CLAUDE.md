# Pilot Space - AI-Augmented SDLC Platform

**Built on "Note-First" paradigm** - Think first, structure later.

## Project Overview

AI-augmented SDLC on a "Note-First" paradigm — users write in a note canvas, AI provides ghost text completions, extracts issues from text, and reviews PRs. Human-in-the-loop on all destructive actions (DD-003). BYOK — no AI cost pass-through. Scale: 5-100 members/workspace. Details: `docs/BUSINESS_CONTEXT.md`

## Monorepo Structure

```text
backend/       Python FastAPI, Clean Architecture, SQLAlchemy async, DI (README.md)
frontend/      Next.js App Router, MobX + TanStack Query, shadcn/ui (README.md)
cli/           pilot-cli — `pilot login`, `pilot implement` (pyproject.toml)
authcore/      Supabase Auth self-hosted (docker-compose.yml)
infra/         Docker, Supabase local stack
docs/          Design decisions, dev patterns, specs
specs/         Feature specifications
scripts/       Utility scripts
design-system/ Design tokens and references
```

## Commands

```bash
# Install
cd backend && uv sync          # Backend deps
cd frontend && pnpm install    # Frontend deps

# Dev servers
cd backend && uv run uvicorn pilot_space.main:app --reload --port 8000
cd frontend && pnpm dev        # port 3000

# Quality gates (run before every commit)
make quality-gates-backend     # pyright + ruff check + pytest --cov
make quality-gates-frontend    # eslint + tsc --noEmit + vitest

# Backend only
cd backend && uv run ruff check                    # Lint
cd backend && uv run ruff check --fix              # Lint autofix
cd backend && uv run pyright                       # Type check
cd backend && uv run pytest                        # All tests
cd backend && uv run pytest tests/cli/ -q          # CLI tests only

# Frontend only
cd frontend && pnpm lint                           # ESLint
cd frontend && pnpm type-check                     # tsc --noEmit
cd frontend && pnpm test                           # Vitest
cd frontend && pnpm test:e2e                       # Playwright

# CLI
cd cli && uv run pilot login
cd cli && uv run pilot implement PS-1              # Interactive
cd cli && uv run pilot implement PS-1 --oneshot    # Non-interactive (CI)

# Migrations
cd backend && alembic heads    # Verify single head
cd backend && alembic check    # Head matches models
cd backend && alembic upgrade head
```

## Environment Setup

Each package requires its own `.env`. Copy from examples:
- `backend/.env.example` → `backend/.env`
- `frontend/.env.example` → `frontend/.env.local`

Backend needs: Supabase URL/keys, database URL, Redis URL, AI provider keys (BYOK).
Frontend needs: Supabase anon key, API base URL.

Dev server ports: backend 8000, frontend 3000, Supabase Kong gateway 18000.
Start Supabase locally: `cd infra/supabase && docker compose up -d`.

---

## AI Agent Architecture

**Complete AI layer architecture, agents, skills, MCP tools, and provider routing**: See `backend/src/pilot_space/ai/README.md`

**Design Philosophy**: Centralized conversational agent. Single `PilotSpaceAgent` orchestrator routes to skills (single-turn, stateless) and subagents (multi-turn, stateful).

## Design Decisions

Key DDs are referenced inline above (DD-001, DD-003, DD-011, DD-060–DD-070, DD-086–DD-088). **Full list (88 decisions)**: `docs/DESIGN_DECISIONS.md`

## UI/UX Design System

Full spec: `specs/001-pilot-space-mvp/ui-design-spec.md` v4.0 / `frontend/README.md`

### Standards & Patterns

| Topic | Document |
|-------|----------|
| Architecture decisions (88) | `docs/DESIGN_DECISIONS.md` |
| Dev patterns (start here) | `docs/dev-pattern/README.md` |
| Pilot Space patterns | `docs/dev-pattern/45-pilot-space-patterns.md` |
| MobX patterns | `docs/dev-pattern/21c-frontend-mobx-state.md` |
| Feature specs (17 features) | `docs/PILOT_SPACE_FEATURES.md` |

---

## Dev-Pattern Quick Reference

Load order for new features:

1. `docs/dev-pattern/45-pilot-space-patterns.md` → Project-specific overrides
2. Domain-specific pattern → (e.g., 07-repository, 20-component)
3. Cross-cutting patterns → (e.g., 26-di, 06-validation)

**Pilot Space Overrides** (from pattern 45):

- Zustand → MobX (complex observable state, auto-save reactions)
- Custom JWT → Supabase Auth+RLS (database-level auth)
- Kafka → Supabase Queues/pgmq (native PostgreSQL, exactly-once)

---

## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

### Claude Agent SDK Documentation

Read index at `docs/claude-sdk.txt` for full documentation.

---

## Gotchas

1. **Session ContextVar**: Every route using a DI-provided service MUST declare `session: SessionDep` in its signature. Without it, `get_current_session()` raises `RuntimeError: No session in current context` at first DB access. See `backend/src/pilot_space/dependencies/auth.py`.

2. **DI wiring**: `@inject` only works in modules listed in `container.py` `wiring_config.modules`. New files using `@inject` + `Provide[Container.x]` silently get default values if not registered. See `backend/src/pilot_space/container/container.py`.

3. **`get_settings()` is `lru_cache`**: Tests that modify env vars after first call see stale config. Call `get_settings.cache_clear()` between tests. See `backend/src/pilot_space/config.py`.

4. **Pre-commit uses `prek`**: The repo root uses [prek](https://prek.j178.dev/), not standard `pre-commit`. Run `prek install`, not `pre-commit install`. The `backend/` subdirectory has a separate `.pre-commit-config.yaml` with additional hooks (sqlfluff, detect-secrets).

5. **Test DB defaults to SQLite**: `backend/tests/conftest.py` uses `sqlite+aiosqlite:///:memory:` by default. RLS policies, pgvector, pgmq are PostgreSQL-specific and silently pass or fail with wrong semantics. Set `TEST_DATABASE_URL` for integration tests.

6. **`db_session` vs `db_session_committed`**: Default `db_session` wraps in a rollback transaction. Use `db_session_committed` when testing unique constraints or cross-session data visibility.

7. **Coverage gate**: `fail_under = 80` with `branch = true` in `backend/pyproject.toml`. New modules without tests can block CI.

8. **Error responses**: All backend errors use `Content-Type: application/problem+json` (RFC 7807), not `application/json`. Frontend `ApiError.fromAxiosError` handles both formats, but new error-parsing code must not assume `application/json`.

---

## Design Context

### Users
Software development teams (5-100 members/workspace). Roles: engineers, PMs, designers. "Note-First" workflow — brainstorm in rich text canvas, AI assists with ghost text, issue extraction, PR reviews. BYOK model (no AI cost pass-through).

### Brand Personality
**Warm, Capable, Collaborative.** AI is a co-pilot teammate, not a system. Voice is approachable and knowledgeable. Calm confidence as primary emotion, with layers of professional trust, creative energy, and playful delight.

### Aesthetic Direction
Notion-like neutral base with editorial quality. Inspirations: Craft (layered surfaces, typography), Apple (squircle corners, material depth), Things 3 (spacious calm, natural accents). Anti-references: generic SaaS defaults, dense enterprise tools (Jira), flashy startup trends, CLI-only aesthetics.

### Design Principles
1. **Think first, structure later** — Notes are the entry point, not forms
2. **AI is a teammate, not a toolbar** — Natural suggestions with "You + AI" attribution
3. **Spacious calm over dense efficiency** — Generous whitespace, progressive disclosure
4. **Warmth through craft** — Every surface/shadow/transition feels intentional and human
5. **Accessible by default** — WCAG 2.2 AA baseline, color never sole meaning carrier, keyboard-first

Full design context: `.impeccable.md` | Full UI spec: `specs/001-pilot-space-mvp/ui-design-spec.md`
