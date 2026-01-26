# Quickstart: MVP AI Agents Build

**Feature**: 004-mvp-agents-build
**Date**: 2026-01-25

---

## Prerequisites

1. **Python 3.12+** installed
2. **Redis** running (for session management)
3. **PostgreSQL 16+** with pgvector extension
4. **Supabase** project configured (Auth, Vault)
5. **API Keys** for testing:
   - Anthropic API key (required)
   - OpenAI API key (required for embeddings)
   - Google API key (optional, for latency testing)

---

## Development Setup

### 1. Install Dependencies

```bash
cd backend
uv sync

# Verify installation
uv run python -c "from claude_agent_sdk import query; print('SDK installed')"
```

### 2. Run Migrations

```bash
# Apply new migrations
uv run alembic upgrade head

# Verify tables created
uv run python -c "
from pilot_space.infrastructure.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
assert 'workspace_api_keys' in tables
assert 'ai_approval_requests' in tables
assert 'ai_cost_records' in tables
print('Migrations verified!')
"
```

### 3. Configure Test Environment

```bash
# .env.test
ANTHROPIC_API_KEY=sk-ant-test-xxx
OPENAI_API_KEY=sk-test-xxx
GOOGLE_API_KEY=AIza-test-xxx
REDIS_URL=redis://localhost:6379/1
DATABASE_URL=postgresql+asyncpg://localhost/pilot_space_test
```

### 4. Run Tests

```bash
# Unit tests (fast, uses mocks)
uv run pytest tests/unit/ai/ -v

# Integration tests (uses real providers)
uv run pytest tests/integration/ai/ -v --run-integration

# E2E tests (full stack)
uv run pytest tests/e2e/ai/ -v --run-e2e
```

---

## Agent Development Guide

### Creating a New Agent (One-Shot)

```python
# ai/agents/my_agent.py
from pilot_space.ai.agents.sdk_base import SDKBaseAgent
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, ResultMessage
from typing import AsyncIterator


class MyAgent(SDKBaseAgent):
    """Description of what this agent does."""

    AGENT_NAME = "my_agent"
    DEFAULT_MODEL = "claude-sonnet-4"  # or claude-opus-4-5 for complex tasks
    MAX_BUDGET_USD = 5.0
    MAX_TURNS = 10

    SYSTEM_PROMPT = """You are an expert at [task description].

Your task is to:
1. [Step 1]
2. [Step 2]
3. [Step 3]

Always explain your reasoning."""

    async def execute(
        self,
        input_param: str,
        user_id: str,
        workspace_id: str,
    ) -> AsyncIterator[str]:
        """Execute the agent task."""
        prompt = f"Process this: {input_param}"

        options = self._build_options(
            system_prompt=self.SYSTEM_PROMPT,
            allowed_tools=[
                "mcp__pilot_space__get_issue_context",
                # Add other tools as needed
            ],
            max_budget_usd=self.MAX_BUDGET_USD,
        )

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        yield block.text

            if isinstance(message, ResultMessage):
                await self._track_result(message, user_id, workspace_id)
```

### Creating a Multi-Turn Agent

```python
# ai/agents/my_multiturn_agent.py
from claude_agent_sdk import ClaudeSDKClient


class MyMultiTurnAgent(SDKBaseAgent):
    """Agent with multi-turn conversation."""

    async def execute(
        self,
        issue_id: str,
        user_id: str,
        workspace_id: str,
        session_id: str | None = None,
    ) -> AsyncIterator[str]:
        options = self._build_options(
            system_prompt=self.SYSTEM_PROMPT,
            allowed_tools=["mcp__pilot_space__get_issue_context"],
        )

        async with ClaudeSDKClient(options=options) as client:
            # Turn 1
            yield "📋 Analyzing...\n"
            await client.query(f"Analyze issue {issue_id}")
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text

            # Turn 2
            yield "\n📚 Searching...\n"
            await client.query("Find related documentation")
            async for message in client.receive_response():
                # ... handle response
```

### Adding MCP Tools

```python
# ai/tools/database_tools.py
from claude_agent_sdk import tool


@tool(
    name="get_my_data",
    description="Fetch custom data for the agent",
    parameters={
        "entity_id": {
            "type": "string",
            "format": "uuid",
            "description": "ID of entity to fetch",
            "required": True,
        },
    }
)
async def get_my_data(args: dict) -> dict:
    """Tool implementation."""
    entity_id = args["entity_id"]

    # Access repository via DI
    from pilot_space.container import container
    repo = container.my_repository()

    entity = await repo.get_by_id(entity_id)
    if not entity:
        return {
            "content": [{"type": "text", "text": "Entity not found"}],
            "is_error": True,
        }

    return {
        "content": [{"type": "text", "text": json.dumps(entity.to_dict())}],
        "is_error": False,
    }
```

---

## Testing Patterns

### Unit Testing Agents

```python
# tests/unit/ai/agents/test_my_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from pilot_space.ai.agents.my_agent import MyAgent


@pytest.fixture
def mock_agent():
    """Create agent with mocked dependencies."""
    return MyAgent(
        provider_selector=AsyncMock(),
        mcp_server=AsyncMock(),
        cost_tracker=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_my_agent_streams_content(mock_agent):
    """Test agent streams expected content."""
    with patch('pilot_space.ai.agents.my_agent.query') as mock_query:
        # Setup mock response
        async def mock_generator(*args, **kwargs):
            from claude_agent_sdk.types import AssistantMessage, TextBlock
            yield AssistantMessage(content=[TextBlock(text="Result: ")])
            yield AssistantMessage(content=[TextBlock(text="Success!")])

        mock_query.return_value = mock_generator()

        # Execute
        chunks = []
        async for chunk in mock_agent.execute(
            input_param="test",
            user_id="user-123",
            workspace_id="ws-123",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert "Success" in "".join(chunks)
```

### Integration Testing with Real Provider

```python
# tests/integration/ai/test_sdk_agents.py
import pytest
from pilot_space.ai.agents.ghost_text_agent import GhostTextAgent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ghost_text_real_provider(configured_agent):
    """Test ghost text with real API (requires API key)."""
    chunks = []
    async for chunk in configured_agent.execute(
        current_text="def calculate_",
        cursor_position=15,
        is_code=True,
        language="python",
    ):
        chunks.append(chunk)

    result = "".join(chunks)
    assert len(result) > 0
    # Ghost text should complete the function
    assert "(" in result or ":" in result
```

---

## SSE Endpoint Pattern

```python
# api/v1/routers/ai.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import json


router = APIRouter(prefix="/ai", tags=["AI"])


async def create_sse_stream(generator, event_type="content"):
    """Wrap generator in SSE format."""
    try:
        async for chunk in generator:
            yield f"data: {json.dumps({'type': event_type, 'data': chunk})}\n\n".encode()
        yield f"data: {json.dumps({'type': 'done'})}\n\n".encode()
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode()


@router.post("/my-agent/{entity_id}")
async def stream_my_agent(
    entity_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: SDKOrchestrator = Depends(get_sdk_orchestrator),
):
    """Stream agent output via SSE."""
    return StreamingResponse(
        create_sse_stream(
            orchestrator.agents["my_agent"].execute(
                entity_id=entity_id,
                user_id=str(current_user.id),
                workspace_id=str(current_user.workspace_id),
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

---

## Quality Gates

Before submitting PR:

```bash
# Run all quality checks
uv run ruff check .
uv run pyright
uv run pytest --cov=pilot_space.ai --cov-report=term-missing

# Expected coverage: >80%
# Expected: all checks pass
```

---

## Common Issues

### 1. "API key not configured"

```python
# Ensure workspace has API key
await key_storage.store_api_key(
    workspace_id=workspace_id,
    provider="anthropic",
    api_key=os.environ["ANTHROPIC_API_KEY"],
)
```

### 2. "Session expired"

Sessions TTL is 30 minutes. Pass `session_id` to resume, or start new session.

### 3. "Rate limit exceeded"

Circuit breaker is open. Wait 30 seconds for recovery.

### 4. "Approval required"

Action requires human approval per DD-003. Check `/ai/approvals` endpoint.

---

## Reference

- [spec.md](./spec.md) - Feature specification
- [plan.md](./plan.md) - Implementation plan
- [data-model.md](./data-model.md) - Entity definitions
- [contracts/ai-endpoints.yaml](./contracts/ai-endpoints.yaml) - API contracts
- [contracts/mcp-tools.yaml](./contracts/mcp-tools.yaml) - MCP tool definitions
