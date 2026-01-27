# Quickstart: Conversational Agent Architecture

**Branch**: `005-conversational-agent-arch`
**Date**: 2026-01-27

## Prerequisites

- Python 3.12+
- Node.js 20+ / pnpm 9+
- Docker Compose (for local development)
- Anthropic API key (required for AI features)

## Quick Setup

### 1. Clone and Checkout

```bash
git clone https://github.com/your-org/pilot-space.git
cd pilot-space
git checkout 005-conversational-agent-arch
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your credentials:
# - ANTHROPIC_API_KEY (required)
# - SUPABASE_URL, SUPABASE_ANON_KEY
# - DATABASE_URL

# Run database migrations
alembic upgrade head

# Start development server
uvicorn pilot_space.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Copy environment template
cp .env.example .env.local

# Edit .env.local:
# - NEXT_PUBLIC_API_URL=http://localhost:8000
# - NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY

# Start development server
pnpm dev
```

### 4. Docker Compose (Full Stack)

```bash
# From project root
docker compose up -d

# Services:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000/docs
# - Supabase Studio: http://localhost:54323
```

## Feature Verification

### Test ChatView UI

1. Navigate to http://localhost:3000
2. Login with test credentials
3. Open a note in the workspace
4. Click the AI chat icon in the sidebar
5. Verify ChatView components render correctly

### Test Skill Invocation (after Phase 2)

1. Open ChatView
2. Type `\` to open skill menu
3. Select `extract-issues`
4. Verify skill executes and returns structured output

### Test Subagent Mention (after Phase 3)

1. Open ChatView
2. Type `@pr-review https://github.com/org/repo/pull/123`
3. Verify subagent spawns and streams output

### Test Approval Flow (after Phase 4)

1. Ask AI to create an issue
2. Verify ApprovalOverlay appears
3. Review proposed issue details
4. Approve or reject
5. Verify issue is created (if approved)

## Development Commands

### Backend

```bash
# Quality gates (must pass before merge)
uv run pyright && uv run ruff check && uv run pytest --cov=.

# Run specific tests
uv run pytest tests/ai/test_pilotspace_agent.py -v

# Format code
uv run ruff format

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Frontend

```bash
# Quality gates (must pass before merge)
pnpm lint && pnpm type-check && pnpm test

# Run specific tests
pnpm test -- --grep "PilotSpaceStore"

# E2E tests
pnpm test:e2e

# Storybook (component development)
pnpm storybook
```

## Key Files

### Backend

| File | Description |
|------|-------------|
| `backend/src/pilot_space/ai/sdk/config.py` | SDK configuration factory |
| `backend/src/pilot_space/ai/sdk/session_handler.py` | Session management |
| `backend/src/pilot_space/ai/sdk/permission_handler.py` | canUseTool callback |
| `backend/src/pilot_space/ai/agents/pilotspace_agent.py` | Main orchestrator |
| `backend/src/pilot_space/api/v1/routers/ai_chat.py` | Unified chat endpoint |
| `backend/.claude/skills/` | Skill SKILL.md files |

### Frontend

| File | Description |
|------|-------------|
| `frontend/src/stores/ai/PilotSpaceStore.ts` | Unified MobX store |
| `frontend/src/features/ai/ChatView/` | ChatView component tree |
| `frontend/src/services/api/ai.ts` | AI API client |

## Debugging

### Backend Logs

```bash
# Watch backend logs
docker compose logs -f backend

# Or in development mode
uvicorn pilot_space.main:app --reload --log-level debug
```

### Frontend DevTools

1. Open browser DevTools (F12)
2. Check Network tab for SSE stream events
3. Use MobX DevTools extension to inspect store state
4. Check Console for error messages

### Common Issues

| Issue | Solution |
|-------|----------|
| SSE not streaming | Check CORS headers; verify `X-Accel-Buffering: no` |
| Session not resuming | Verify `sdk_session_id` persisted in database |
| Skill not loading | Check `.claude/skills/` directory structure |
| Approval not appearing | Verify `canUseTool` callback registered |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Input            ChatView              PilotSpaceStore                │
│  ┌─────────┐          ┌─────────┐           ┌─────────┐                     │
│  │ Message │─────────▶│ ChatInput│──────────▶│ sendMsg │                     │
│  │ \skill  │          │ Menu    │           │ ()      │                     │
│  │ @agent  │          └─────────┘           └────┬────┘                     │
│  └─────────┘                                     │                          │
│                                                  ▼                          │
│                                           ┌─────────────┐                   │
│                                           │ SSE Client  │                   │
│                                           │ EventSource │                   │
│                                           └──────┬──────┘                   │
│                                                  │                          │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   │
│                                                  │                          │
│  POST /api/v1/ai/chat                           │                          │
│  ┌─────────┐          ┌─────────┐           ┌───▼─────┐                     │
│  │ Router  │─────────▶│ Pilot   │──────────▶│ SDK     │                     │
│  │         │          │ Space   │           │ query() │                     │
│  │         │          │ Agent   │           │         │                     │
│  └─────────┘          └────┬────┘           └────┬────┘                     │
│                            │                     │                          │
│                            ▼                     ▼                          │
│                      ┌─────────┐           ┌─────────┐                      │
│                      │ Skills  │           │ Sub-    │                      │
│                      │ .md     │           │ agents  │                      │
│                      └─────────┘           └─────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Next Steps

1. **Phase 1**: Implement SDK integration layer
2. **Phase 2**: Migrate 8 skills to SKILL.md format
3. **Phase 3**: Create PilotSpaceAgent and /ai/chat endpoint
4. **Phase 4**: Wire ChatView to PilotSpaceStore
5. **Phase 5**: E2E testing and documentation

## References

- [Feature Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Research Document](./research.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/)
