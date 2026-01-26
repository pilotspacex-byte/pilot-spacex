# Research: MVP AI Agents Build with Claude Agent SDK

**Feature**: 004-mvp-agents-build
**Date**: 2026-01-25
**Status**: Complete

---

## Research Task 1: Claude Agent SDK API Patterns

### Question
How does claude-agent-sdk implement `query()` vs `ClaudeSDKClient` for different use cases?

### Findings

**SDK Import Structure**:
```python
from claude_agent_sdk import (
    query,                    # One-shot tasks
    ClaudeSDKClient,          # Multi-turn conversations
    ClaudeAgentOptions,       # Configuration
    tool,                     # MCP tool decorator
    create_sdk_mcp_server,    # MCP server factory
)
from claude_agent_sdk.types import (
    AssistantMessage,         # Agent response
    TextBlock,                # Text content
    ToolUseBlock,             # Tool call
    ResultMessage,            # Final result with cost info
)
```

**`query()` for One-Shot Tasks**:
- Best for: Single-turn operations (PR review, issue extraction, doc generation)
- Returns: Async iterator of messages
- Automatically handles tool execution
- No state management needed

```python
async def review_pr(pr_number: int, repo: str) -> AsyncIterator[str]:
    options = ClaudeAgentOptions(
        model="claude-opus-4-5",
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["get_pr_diff", "search_codebase"],
        mcp_servers={"pilot_space": mcp_server},
        max_budget_usd=20.0,
        max_turns=15,
    )

    async for message in query(prompt=f"Review PR #{pr_number}", options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    yield block.text
        if isinstance(message, ResultMessage):
            yield f"\n---\nCost: ${message.total_cost_usd:.4f}"
```

**`ClaudeSDKClient` for Multi-Turn**:
- Best for: Contextual follow-ups (AI context, conversation)
- Maintains conversation state
- Uses context manager for session lifecycle

```python
async def build_ai_context(issue_id: str) -> AsyncIterator[str]:
    options = ClaudeAgentOptions(
        model="claude-opus-4-5",
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["get_issue_context", "semantic_search"],
        mcp_servers={"pilot_space": mcp_server},
        max_budget_usd=10.0,
        max_turns=10,
    )

    async with ClaudeSDKClient(options=options) as client:
        # Turn 1: Analyze issue
        await client.query(f"Analyze issue {issue_id}")
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        yield block.text

        # Turn 2: Find related docs
        await client.query("Find related documentation")
        async for message in client.receive_response():
            # ... handle response
```

### Decision
- **One-shot agents** (GhostText, IssueExtractor, PRReview, DocGenerator, etc.): Use `query()`
- **Multi-turn agents** (AIContext, Conversation): Use `ClaudeSDKClient`

### Rationale
`query()` is simpler and handles all tool execution automatically for single-turn tasks. `ClaudeSDKClient` provides necessary state management for multi-turn conversations where each turn builds on previous context.

---

## Research Task 2: MCP Tool Definition Patterns

### Question
How to define MCP tools that integrate with Pilot Space repositories?

### Findings

**MCP Tool Decorator Pattern**:
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool(
    name="get_issue_context",
    description="Fetch complete issue context including relations, activity, and linked notes",
    parameters={
        "issue_id": {
            "type": "string",
            "description": "UUID of the issue to fetch",
            "required": True,
        },
        "include_relations": {
            "type": "boolean",
            "description": "Include related issues, notes, and pages",
            "default": True,
        },
    }
)
async def get_issue_context(args: dict) -> dict:
    """MCP tool implementation with repository access."""
    issue_id = args["issue_id"]
    include_relations = args.get("include_relations", True)

    # Access repository via DI container
    issue_repo = container.issue_repository()
    issue = await issue_repo.get_by_id(UUID(issue_id))

    if not issue:
        return {
            "content": [{"type": "text", "text": f"Issue not found: {issue_id}"}],
            "is_error": True,
        }

    result = {
        "id": str(issue.id),
        "identifier": issue.identifier,
        "name": issue.name,
        "description": issue.description,
        "state": issue.state.name,
        "priority": issue.priority,
    }

    if include_relations:
        result["related_issues"] = [...]
        result["linked_notes"] = [...]

    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
        "is_error": False,
    }
```

**MCP Server Factory**:
```python
def create_pilot_space_mcp_server() -> McpSdkServerConfig:
    """Create MCP server with all Pilot Space tools."""
    return create_sdk_mcp_server(
        name="pilot-space",
        version="1.0.0",
        tools=[
            get_issue_context,
            get_note_content,
            get_project_context,
            find_similar_issues,
            search_codebase,
            semantic_search,
            get_pr_details,
            get_pr_diff,
            search_code_in_repo,
            create_note_annotation,
            create_issue,
            post_pr_comment,
        ]
    )
```

**Permission Model**:
```python
TOOL_PERMISSIONS = {
    # Read-only tools - bypass permission prompts
    "read_only": [
        "get_issue_context",
        "get_note_content",
        "get_pr_details",
        "get_pr_diff",
        "search_codebase",
        "semantic_search",
        "find_similar_issues",
        "get_project_context",
        "search_code_in_repo",
    ],
    # Write tools - require default permission
    "write": [
        "create_note_annotation",
        "create_issue",
        "post_pr_comment",
    ],
}
```

### Decision
- Implement 12 MCP tools across 3 categories: database (7), GitHub (3), search (2)
- Use `permission_mode="default"` to allow read-only tools without prompts
- Write tools go through ApprovalService for human-in-the-loop

### Rationale
Separating read vs write permissions aligns with DD-003 human-in-the-loop principle. Read tools are safe to auto-execute; write tools require approval flow.

---

## Research Task 3: SSE Streaming with SDK

### Question
How to stream SDK responses through FastAPI SSE endpoints?

### Findings

**SSE Stream Wrapper**:
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

async def create_sse_stream(
    generator: AsyncIterator[str],
    event_type: str = "content",
) -> AsyncIterator[bytes]:
    """Wrap async generator in SSE format."""
    try:
        async for chunk in generator:
            event = {
                "type": event_type,
                "data": chunk,
            }
            yield f"data: {json.dumps(event)}\n\n".encode()

        # Send completion event
        yield f"data: {json.dumps({'type': 'done'})}\n\n".encode()

    except Exception as e:
        # Send error event
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode()
```

**FastAPI Endpoint Pattern**:
```python
@router.post("/issues/{issue_id}/context")
async def stream_ai_context(
    issue_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: SDKOrchestrator = Depends(get_sdk_orchestrator),
):
    """Stream AI context building via SSE."""
    return StreamingResponse(
        create_sse_stream(
            orchestrator.agents["ai_context"].execute(
                issue_id=issue_id,
                user_id=str(current_user.id),
                workspace_id=str(current_user.workspace_id),
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

**Frontend Consumer**:
```typescript
async function* streamAIResponse(url: string): AsyncGenerator<SSEEvent> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Accept': 'text/event-stream' },
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        yield JSON.parse(line.slice(6)) as SSEEvent;
      }
    }
  }
}
```

### Decision
Use FastAPI `StreamingResponse` with custom SSE wrapper that formats SDK output as JSON events with type discrimination.

### Rationale
SSE provides reliable streaming with automatic reconnection. JSON event format allows typed handling on frontend.

---

## Research Task 4: Supabase Vault Integration

### Question
How to use Supabase Vault for API key encryption at rest?

### Findings

**Supabase Vault API**:
```python
from supabase import create_client

class SecureKeyStorage:
    """Secure API key storage using Supabase Vault."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self._client = create_client(supabase_url, supabase_key)

    async def store_api_key(
        self,
        workspace_id: str,
        provider: str,
        api_key: str,
    ) -> None:
        """Store encrypted API key using Vault."""
        # Create vault secret
        result = await self._client.rpc(
            'vault.create_secret',
            {
                'secret': api_key,
                'name': f'api_key_{workspace_id}_{provider}',
                'description': f'API key for {provider} in workspace {workspace_id}',
            }
        ).execute()

        secret_id = result.data

        # Store reference in workspace_api_keys table
        await self._client.table('workspace_api_keys').upsert({
            'workspace_id': workspace_id,
            'provider': provider,
            'vault_secret_id': secret_id,
            'updated_at': 'now()',
        }).execute()

    async def get_api_key(
        self,
        workspace_id: str,
        provider: str,
    ) -> str | None:
        """Retrieve and decrypt API key from Vault."""
        # Get secret reference
        result = await self._client.table('workspace_api_keys').select(
            'vault_secret_id'
        ).eq(
            'workspace_id', workspace_id
        ).eq(
            'provider', provider
        ).single().execute()

        if not result.data:
            return None

        # Decrypt from Vault
        secret = await self._client.rpc(
            'vault.get_secret',
            {'id': result.data['vault_secret_id']}
        ).execute()

        return secret.data['secret']
```

**Database Schema**:
```sql
-- Table stores references to Vault secrets, not the keys themselves
CREATE TABLE workspace_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    vault_secret_id UUID NOT NULL,  -- Reference to Vault
    validation_status VARCHAR(20) DEFAULT 'pending',
    last_validated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(workspace_id, provider)
);

-- RLS policy
ALTER TABLE workspace_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "workspace_api_keys_policy" ON workspace_api_keys
    USING (workspace_id IN (
        SELECT workspace_id FROM workspace_members
        WHERE user_id = auth.uid() AND role IN ('admin', 'owner')
    ));
```

**Key Validation**:
```python
async def validate_api_key(provider: str, api_key: str) -> bool:
    """Validate API key by making test call."""
    try:
        if provider == "anthropic":
            client = AsyncAnthropic(api_key=api_key)
            await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
        elif provider == "openai":
            client = AsyncOpenAI(api_key=api_key)
            await client.embeddings.create(
                model="text-embedding-3-large",
                input="test",
                dimensions=256,
            )
        elif provider == "google":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            await model.generate_content_async("test")
        return True
    except Exception:
        return False
```

### Decision
Use Supabase Vault for AES-256-GCM encryption at rest. Store only Vault secret references in the database, not actual keys.

### Rationale
Supabase Vault provides enterprise-grade encryption without managing our own key infrastructure. Keys are decrypted only at runtime, minimizing exposure.

---

## Research Task 5: Session Management for Multi-Turn

### Question
How to manage multi-turn conversation state with session limits?

### Findings

**Session Schema**:
```python
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any
import json
import uuid

@dataclass
class ConversationMessage:
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0

@dataclass
class AISession:
    id: str
    user_id: str
    agent_type: str
    context: dict[str, Any] = field(default_factory=dict)
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    total_cost_usd: float = 0.0

    # Session limits per spec
    MAX_MESSAGES = 20
    MAX_TOKENS = 8000

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        return datetime.utcnow() - self.last_activity > timedelta(minutes=timeout_minutes)

    def add_message(self, role: str, content: str, tokens: int) -> None:
        """Add message with automatic truncation."""
        self.messages.append(ConversationMessage(
            role=role,
            content=content,
            token_count=tokens,
        ))
        self.last_activity = datetime.utcnow()

        # Truncate if limits exceeded
        self._truncate_if_needed()

    def _truncate_if_needed(self) -> None:
        """FIFO truncation when limits exceeded."""
        # Message count limit
        while len(self.messages) > self.MAX_MESSAGES:
            self.messages.pop(0)  # Remove oldest

        # Token limit
        total_tokens = sum(m.token_count for m in self.messages)
        while total_tokens > self.MAX_TOKENS and len(self.messages) > 1:
            removed = self.messages.pop(0)
            total_tokens -= removed.token_count

    def to_claude_messages(self) -> list[dict]:
        """Format for Claude API."""
        return [
            {"role": m.role, "content": m.content}
            for m in self.messages
        ]
```

**Redis Session Manager**:
```python
from redis.asyncio import Redis

class SessionManager:
    """Manage AI conversation sessions in Redis."""

    SESSION_TTL_SECONDS = 1800  # 30 minutes
    KEY_PREFIX = "ai_session:"

    def __init__(self, redis: Redis):
        self._redis = redis

    async def create_session(
        self,
        user_id: str,
        agent_type: str,
        initial_context: dict | None = None,
    ) -> AISession:
        """Create new session with 30-minute TTL."""
        session = AISession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            agent_type=agent_type,
            context=initial_context or {},
        )

        await self._store(session)
        return session

    async def get_session(self, session_id: str) -> AISession | None:
        """Retrieve session by ID."""
        data = await self._redis.get(f"{self.KEY_PREFIX}{session_id}")
        if not data:
            return None

        parsed = json.loads(data)
        parsed['messages'] = [
            ConversationMessage(**m) for m in parsed['messages']
        ]
        return AISession(**parsed)

    async def update_session(
        self,
        session_id: str,
        message: ConversationMessage | None = None,
        context_update: dict | None = None,
        cost_delta: float = 0.0,
    ) -> AISession | None:
        """Update session with new message or context."""
        session = await self.get_session(session_id)
        if not session:
            return None

        if message:
            session.add_message(
                role=message.role,
                content=message.content,
                tokens=message.token_count,
            )

        if context_update:
            session.context.update(context_update)

        session.total_cost_usd += cost_delta

        await self._store(session)
        return session

    async def end_session(self, session_id: str) -> None:
        """End and cleanup session."""
        await self._redis.delete(f"{self.KEY_PREFIX}{session_id}")

    async def _store(self, session: AISession) -> None:
        """Store session in Redis with TTL."""
        data = {
            **asdict(session),
            'messages': [asdict(m) for m in session.messages],
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
        }
        await self._redis.setex(
            f"{self.KEY_PREFIX}{session.id}",
            self.SESSION_TTL_SECONDS,
            json.dumps(data),
        )
```

### Decision
Use Redis for session storage with:
- 30-minute TTL for automatic cleanup
- FIFO message truncation at 20 messages / 8000 tokens
- JSON serialization for conversation history

### Rationale
Redis provides fast session access with automatic expiration. FIFO truncation ensures context window limits are respected while preserving most recent context.

---

## Summary of Decisions

| Research Area | Decision | Alternative Rejected |
|---------------|----------|---------------------|
| SDK Pattern | `query()` for one-shot, `ClaudeSDKClient` for multi-turn | Single pattern for all (inflexible) |
| MCP Tools | 12 tools with read/write permission separation | All tools require approval (slow) |
| SSE Streaming | FastAPI StreamingResponse with JSON events | WebSocket (more complex for one-way) |
| Key Storage | Supabase Vault with secret references | Direct encryption (key management overhead) |
| Sessions | Redis with FIFO truncation | PostgreSQL (slower for frequent access) |

---

## References

- Claude Agent SDK Documentation (internal)
- Supabase Vault Documentation: https://supabase.com/docs/guides/vault
- FastAPI Streaming Response: https://fastapi.tiangolo.com/advanced/custom-response/
- Redis Session Management: https://redis.io/docs/manual/patterns/
