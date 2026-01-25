# Pilot Space Backend

AI-Augmented SDLC Platform with Note-First Workflow - Backend API

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 16+ via Supabase with pgvector
- **Cache**: Redis
- **Search**: Meilisearch
- **AI**: Claude Agent SDK (Anthropic), OpenAI, Google Gemini
- **Auth**: Supabase Auth (GoTrue)
- **Queue**: Supabase Queues (pgmq + pg_cron)

## Quick Start

```bash
# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run development server
uv run uvicorn pilot_space.main:app --reload

# Run tests
uv run pytest

# Run quality checks
uv run ruff check .
uv run pyright
```

## Mock AI Mode (Development)

**Save $5K/month in development costs** by using deterministic AI responses without external API calls.

### Enable Mock Mode

```bash
# In .env
APP_ENV=development
AI_FAKE_MODE=true
AI_FAKE_LATENCY_MS=500  # Simulated response time
AI_FAKE_STREAMING_CHUNK_DELAY_MS=50
```

### Features

- ✅ **Zero API costs** - No calls to Claude, OpenAI, or Gemini
- ✅ **Deterministic** - Same input = same output (great for testing)
- ✅ **Fast development** - No rate limits, instant responses
- ✅ **Offline** - Works without internet connection
- ✅ **All 10 agents supported**:
  - GhostTextAgent (inline completions)
  - IssueEnhancerAgent (title/description enhancement)
  - MarginAnnotationAgent (contextual annotations)
  - IssueExtractorAgent (extract issues from notes)
  - ConversationAgent (AI chat)
  - AssigneeRecommenderAgent (assignee suggestions)
  - DuplicateDetectorAgent (duplicate issue detection)
  - CommitLinkerAgent (issue reference extraction)
  - AIContextAgent (comprehensive context generation)
  - PRReviewAgent (code review)

### Testing

**API Tests**:
```bash
# See full guide in tests/manual/test_mock_ai_api.md
curl -X POST http://localhost:8000/api/v1/ai/ghost-text \
  -H "Content-Type: application/json" \
  -d '{"current_text": "def ", "cursor_position": 4, "is_code": true}'
```

**Browser Tests**: See `tests/manual/test_mock_ai_browser.md`

### Production

Mock mode is **automatically disabled** in production (`APP_ENV=production`). It only activates when both conditions are met:
- `APP_ENV=development`
- `AI_FAKE_MODE=true`

## Project Structure

```
src/pilot_space/
├── api/          # Presentation layer (FastAPI routers, schemas)
├── domain/       # Business domain (models, services, events)
├── application/  # Application services (CQRS-lite handlers)
├── ai/           # AI layer (agents, prompts, RAG pipeline)
├── infrastructure/ # External systems (database, cache, queue)
└── integrations/ # Third-party integrations (GitHub, Slack)
```

## License

MIT
