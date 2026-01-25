# Research Document: Pilot Space MVP

**Branch**: `001-pilot-space-mvp` | **Date**: 2026-01-22
**Purpose**: Resolve all technical unknowns identified in the implementation plan before proceeding to Phase 1 design.
**Updated**: Session 2026-01-22 - Supabase Integration + Implementation Clarifications

---

## 1. TipTap/ProseMirror Custom Extensions

### Decision: Custom TipTap Extensions

**Rationale**: Full control over ghost text, margin annotations, and issue extraction UI is essential for the note-first workflow that differentiates Pilot Space. Custom extensions allow precise implementation of the unique UX patterns from DD-013.

### Research Findings

#### Ghost Text Implementation

**Approach**: Create a custom TipTap extension using ProseMirror decorations.

```typescript
// GhostTextExtension.ts
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

export interface GhostTextOptions {
  suggestion: string | null
  onAccept: () => void
  onAcceptWord: () => void
  onDismiss: () => void
}

export const GhostText = Extension.create<GhostTextOptions>({
  name: 'ghostText',

  addProseMirrorPlugins() {
    const pluginKey = new PluginKey('ghostText')

    return [
      new Plugin({
        key: pluginKey,
        props: {
          decorations: (state) => {
            const { suggestion } = this.options
            if (!suggestion) return DecorationSet.empty

            const { selection } = state
            if (!selection.empty) return DecorationSet.empty

            // Create inline decoration at cursor position
            const widget = Decoration.widget(selection.from, () => {
              const span = document.createElement('span')
              span.className = 'ghost-text'
              span.textContent = suggestion
              return span
            }, { side: 1 })

            return DecorationSet.create(state.doc, [widget])
          },
          handleKeyDown: (view, event) => {
            if (!this.options.suggestion) return false

            if (event.key === 'Tab') {
              event.preventDefault()
              this.options.onAccept()
              return true
            }
            if (event.key === 'ArrowRight' && event.shiftKey) {
              event.preventDefault()
              this.options.onAcceptWord()
              return true
            }
            if (event.key === 'Escape') {
              this.options.onDismiss()
              return true
            }
            return false
          }
        }
      })
    ]
  }
})
```

**CSS Styling**:
```css
.ghost-text {
  color: var(--color-text-muted);
  opacity: 0.5;
  pointer-events: none;
  animation: ghostFadeIn 150ms ease-out;
}

@keyframes ghostFadeIn {
  from { opacity: 0; }
  to { opacity: 0.5; }
}
```

#### Margin Annotation Positioning

**Approach**: Use ProseMirror NodeView for annotations positioned relative to blocks.

```typescript
// MarginAnnotation pattern
interface BlockAnnotation {
  blockId: string
  type: 'suggestion' | 'issue' | 'error'
  content: string
  actions: AnnotationAction[]
}

// Position calculation
const getAnnotationPosition = (blockId: string, editorView: EditorView) => {
  const dom = editorView.dom.querySelector(`[data-block-id="${blockId}"]`)
  if (!dom) return null
  const rect = dom.getBoundingClientRect()
  const editorRect = editorView.dom.getBoundingClientRect()
  return {
    top: rect.top - editorRect.top,
    height: rect.height
  }
}
```

**Layout Strategy**:
- Editor width: 65% of container
- Margin panel: 35% of container (resizable 150px-350px per DD-053)
- Annotations positioned absolutely relative to their linked blocks
- Smooth scroll animation when clicking annotation (per DD-015)

#### Block-Linked Content Tracking

**Approach**: Generate stable UUIDs for each block, persist in document structure.

```typescript
// Block schema extension
const BlockId = Extension.create({
  name: 'blockId',

  addGlobalAttributes() {
    return [{
      types: ['paragraph', 'heading', 'codeBlock', 'bulletList', 'orderedList'],
      attributes: {
        blockId: {
          default: null,
          parseHTML: element => element.getAttribute('data-block-id'),
          renderHTML: attributes => {
            if (!attributes.blockId) return {}
            return { 'data-block-id': attributes.blockId }
          }
        }
      }
    }]
  }
})

// Auto-generate IDs for new blocks
editor.on('create', ({ editor }) => {
  editor.view.state.doc.descendants((node, pos) => {
    if (!node.attrs.blockId && node.isBlock) {
      editor.commands.command(({ tr }) => {
        tr.setNodeMarkup(pos, null, {
          ...node.attrs,
          blockId: crypto.randomUUID()
        })
        return true
      })
    }
  })
})
```

#### Issue Extraction Rainbow Border

**Approach**: CSS animated gradient border using pseudo-elements.

```css
.issue-extraction-box {
  position: relative;
  padding: 12px 16px;
  margin: 8px 0;
  background: var(--color-bg-secondary);
  border-radius: 8px;
}

.issue-extraction-box::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 8px;
  padding: 2px;
  background: linear-gradient(
    90deg,
    #ff6b6b, #feca57, #48dbfb, #ff9ff3, #54a0ff, #5f27cd
  );
  background-size: 400% 100%;
  animation: rainbowBorder 3s ease infinite;
  -webkit-mask:
    linear-gradient(#fff 0 0) content-box,
    linear-gradient(#fff 0 0);
  mask-composite: exclude;
}

@keyframes rainbowBorder {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| TipTap Pro | Cost + less control over ghost text timing |
| Novel.js | Too opinionated, doesn't support margin annotations |
| Lexical (Meta) | Different architecture, less ProseMirror ecosystem |
| Slate.js | Less mature, smaller ecosystem than TipTap |

---

## 2. AI Provider Integration Patterns

### Decision: Unified Adapter Interface with Streaming

**Rationale**: Support 4 LLM providers (OpenAI, Anthropic, Google, Azure) with consistent interface, streaming for ghost text, and intelligent routing per DD-002.

### Research Findings

#### Unified Provider Interface

```python
# backend/src/pilot_space/ai/providers/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, TypeVar
from pydantic import BaseModel

class CompletionRequest(BaseModel):
    messages: list[dict]
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = False

class CompletionResponse(BaseModel):
    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Non-streaming completion."""
        pass

    @abstractmethod
    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """Streaming completion for ghost text."""
        pass

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for RAG."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens for cost estimation."""
        pass
```

#### Provider Implementations

```python
# Anthropic adapter (recommended for code review per constitution)
class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=request.max_tokens,
            messages=request.messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def count_tokens(self, text: str) -> int:
        return self.client.count_tokens(text)
```

#### Task Routing

```python
# Task-to-provider routing per DD-002 and AI_CAPABILITIES.md
TASK_ROUTING = {
    "code_review": {
        "preferred": ["anthropic", "google", "openai"],
        "model": "claude-sonnet-4-20250514"
    },
    "ghost_text": {
        "preferred": ["google", "openai", "anthropic"],
        "model": "gemini-3.0-flash"  # Fast for real-time
    },
    "documentation": {
        "preferred": ["google", "openai", "anthropic"],
        "model": "gemini-3.0-flash"
    },
    "task_decomposition": {
        "preferred": ["anthropic", "google", "openai"],
        "model": "claude-sonnet-4-20250514"
    },
    "diagram_generation": {
        "preferred": ["openai", "google", "anthropic"],
        "model": "gpt-4.1"
    },
    "semantic_search": {
        "preferred": ["openai", "google"],
        "model": "text-embedding-3-large"
    }
}
```

#### Rate Limit Handling

```python
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class RateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after

@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=60)
)
async def call_with_retry(provider: LLMProvider, request: CompletionRequest):
    try:
        return await provider.complete(request)
    except anthropic.RateLimitError as e:
        raise RateLimitError(retry_after=60)
    except openai.RateLimitError as e:
        raise RateLimitError(retry_after=60)
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| LangChain | Too heavy, abstracts away control we need |
| LiteLLM | Good but less control over streaming |
| Direct SDK only | No unified interface, harder to test |

---

## 3. pgvector Embedding Strategy

### Decision: text-embedding-3-large (3072 dims) with HNSW Index

**Rationale**: Higher quality retrieval justifies storage cost for RAG accuracy; HNSW provides better query performance than IVFFlat at MVP scale.

### Research Findings

#### Embedding Model Selection

| Model | Dimensions | Quality | Cost | Use Case |
|-------|------------|---------|------|----------|
| `text-embedding-3-large` | 3072 | Highest | $0.13/1M tokens | Primary (notes, issues) |
| `text-embedding-3-small` | 1536 | Good | $0.02/1M tokens | Fallback, cost-sensitive |
| `gemini-embedding-001` | 768 | Good | $0.01/1M tokens | Backup provider |

**Decision**: Use `text-embedding-3-large` for primary indexing; users can configure fallbacks.

#### Chunking Strategy

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Different chunking for different content types
CHUNK_CONFIGS = {
    "note": {
        "chunk_size": 512,
        "chunk_overlap": 50,
        "separators": ["\n\n", "\n", ". ", " "]
    },
    "page": {
        "chunk_size": 1000,
        "chunk_overlap": 100,
        "separators": ["\n## ", "\n### ", "\n\n", "\n"]
    },
    "code": {
        "chunk_size": 500,
        "chunk_overlap": 50,
        "separators": ["\n\ndef ", "\n\nclass ", "\n\n", "\n"]
    },
    "issue": {
        "chunk_size": 300,
        "chunk_overlap": 30,
        "separators": ["\n\n", "\n", ". "]
    }
}

def chunk_content(content: str, content_type: str) -> list[str]:
    config = CHUNK_CONFIGS.get(content_type, CHUNK_CONFIGS["note"])
    splitter = RecursiveCharacterTextSplitter(**config)
    return splitter.split_text(content)
```

#### Index Configuration

```sql
-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings table
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    entity_type VARCHAR(50) NOT NULL, -- 'note', 'issue', 'page', 'code'
    entity_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(3072) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_chunk UNIQUE (entity_id, chunk_index)
);

-- HNSW index for fast ANN search
CREATE INDEX embeddings_hnsw_idx ON embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Partial index for workspace isolation
CREATE INDEX embeddings_workspace_idx ON embeddings (workspace_id);
```

#### Embedding Refresh Strategy

```python
# Async embedding updates via Celery
@celery.task(bind=True, max_retries=3)
def update_embeddings(self, entity_type: str, entity_id: str):
    """Called on content create/update."""
    try:
        entity = get_entity(entity_type, entity_id)
        chunks = chunk_content(entity.content, entity_type)

        # Delete old embeddings
        delete_embeddings(entity_id)

        # Generate new embeddings
        embeddings = embed_texts(chunks)

        # Bulk insert
        insert_embeddings(entity_id, chunks, embeddings)
    except Exception as e:
        self.retry(exc=e, countdown=60)

# Trigger on save
@event.listens_for(Note, 'after_update')
def note_updated(mapper, connection, target):
    update_embeddings.delay('note', str(target.id))
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| IVFFlat index | Slower queries, need retraining with data growth |
| Pinecone | Additional infrastructure, cost at scale |
| Weaviate | Additional service to manage |
| 1536 dimensions | Lower quality retrieval |

---

## 4. Supabase Auth Integration

### Decision: Supabase Auth (GoTrue) with Row-Level Security

**Rationale**: Supabase Auth provides unified authentication with RLS for authorization, reducing infrastructure complexity from 10 services to 3. Session 2026-01-22 decision to migrate from Keycloak.

### Research Findings

#### Authentication Flow

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐
│ Browser │────▶│ Pilot Space │────▶│ Supabase Auth│
└─────────┘     └─────────────┘     └──────────────┘
     │                │                    │
     │  1. Login click                     │
     │───────────────▶│                    │
     │                │  2. Redirect to    │
     │◀───────────────│   Supabase OAuth   │
     │                │───────────────────▶│
     │  3. User authenticates (Email/OAuth/SAML)
     │─────────────────────────────────────▶│
     │                │                    │
     │  4. Redirect with tokens            │
     │◀─────────────────────────────────────│
     │                │                    │
     │  5. Store tokens, set session       │
     │◀───────────────│                    │
```

#### Implementation

```python
# backend/src/pilot_space/infrastructure/auth/supabase_auth.py
from supabase import create_client, Client
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

async def get_current_user(
    token: str = Depends(HTTPBearer())
) -> User:
    """Validate JWT and return user."""
    try:
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token.credentials)

        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Get or create user in local DB
        user = await get_or_create_user(
            supabase_id=user_response.user.id,
            email=user_response.user.email,
            name=user_response.user.user_metadata.get('name', ''),
        )

        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
```

#### Row-Level Security (RLS)

```sql
-- Enable RLS on all tables
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

-- Workspace member access policy
CREATE POLICY "workspace_member_access" ON issues
    FOR ALL
    USING (
        workspace_id IN (
            SELECT workspace_id FROM workspace_members
            WHERE user_id = auth.uid()
        )
    );

-- Admin RLS handling (per Session 2026-01-22)
CREATE POLICY "admin_full_access" ON issues
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM workspace_members
            WHERE workspace_id = issues.workspace_id
            AND user_id = auth.uid()
            AND role IN ('admin', 'owner')
        )
    );

-- Soft-delete restoration (per Session 2026-01-22)
-- Original creator OR workspace admin/owner can restore
CREATE POLICY "restore_deleted_items" ON issues
    FOR UPDATE
    USING (
        is_deleted = true
        AND (
            reporter_id = auth.uid()
            OR EXISTS (
                SELECT 1 FROM workspace_members
                WHERE workspace_id = issues.workspace_id
                AND user_id = auth.uid()
                AND role IN ('admin', 'owner')
            )
        )
    );
```

#### Session Token Strategy (per Session 2026-01-22)

```typescript
// Access token (1h) + Refresh token (7d) with rotation
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
});

// Token refresh handled automatically by Supabase client
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'TOKEN_REFRESHED') {
    console.log('Token refreshed');
  }
});
```

#### API Key Encryption (per Session 2026-01-22)

```sql
-- Store API keys using Supabase Vault (AES-256-GCM)
SELECT vault.create_secret(
    'openai_api_key',
    'sk-...',
    'OpenAI API key for workspace xyz'
);

-- Retrieve in application
SELECT vault.decrypted_secret('openai_api_key');
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| Keycloak | Additional infrastructure, more complex |
| Auth0 | External dependency, cost at scale |
| Custom JWT | Missing OAuth providers, session management |
| Firebase Auth | Less PostgreSQL integration |

---

## 5. GitHub App vs OAuth App

### Decision: GitHub App

**Rationale**: Better rate limits (5000/hour vs 5000/hour for OAuth but per-installation), granular permissions, webhook reliability, and organization-level installation.

### Research Findings

#### Comparison

| Feature | GitHub App | OAuth App |
|---------|------------|-----------|
| Rate limits | 5000/hr per installation | 5000/hr per user |
| Webhooks | Built-in, reliable | Manual configuration |
| Permissions | Fine-grained, per-repo | User-level all repos |
| Installation | Org/user level | Per-user authorization |
| AI review posting | As bot (clear labeling) | As user |

#### Implementation

```python
# backend/src/pilot_space/integrations/github/client.py
from githubkit import GitHub
from githubkit.versions.latest.models import Installation

class GitHubAppClient:
    def __init__(self, app_id: str, private_key: str):
        self.app = GitHub(AppAuth(app_id, private_key))

    async def get_installation_client(
        self, installation_id: int
    ) -> GitHub:
        """Get authenticated client for specific installation."""
        return self.app.with_installation_auth(installation_id)

    async def post_pr_review(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        review: PRReviewRequest
    ):
        """Post AI code review as GitHub App bot."""
        client = await self.get_installation_client(installation_id)
        await client.rest.pulls.async_create_review(
            owner=owner,
            repo=repo,
            pull_number=pr_number,
            body=review.summary,
            comments=review.comments,
            event="COMMENT"  # or "REQUEST_CHANGES" for critical
        )
```

#### Webhook Handler

```python
# backend/src/pilot_space/integrations/github/webhooks.py
from fastapi import APIRouter, Request, HTTPException
import hmac
import hashlib

router = APIRouter()

@router.post("/webhooks/github")
async def handle_github_webhook(request: Request):
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    body = await request.body()

    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = request.headers.get("X-GitHub-Event")
    payload = await request.json()

    # Route to handlers
    handlers = {
        "pull_request": handle_pull_request,
        "push": handle_push,
        "installation": handle_installation,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(payload)

    return {"status": "ok"}

def verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

#### Rate Limit Handling for AI Review

```python
# Queue AI review with backoff per spec clarification
@celery.task(bind=True, max_retries=5)
def queue_ai_pr_review(self, pr_data: dict):
    try:
        # Check rate limit before processing
        remaining = check_github_rate_limit(pr_data['installation_id'])
        if remaining < 100:
            # Wait until reset
            raise RateLimitExceeded(retry_after=get_reset_time())

        # Perform AI review
        review = generate_ai_review(pr_data)

        # Post to GitHub
        post_pr_review(pr_data, review)

        # Notify user
        notify_pr_review_complete(pr_data)

    except RateLimitExceeded as e:
        # Exponential backoff: 1min, 2min, 4min, 8min, 16min (max 30min per spec)
        countdown = min(60 * (2 ** self.request.retries), 1800)
        self.retry(exc=e, countdown=countdown)

        # Notify user of delay
        notify_pr_review_delayed(pr_data, countdown)
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| OAuth App | Lower rate limits, less granular permissions |
| Personal Access Token | Not suitable for organization use |
| Fine-grained PAT | Missing webhook support |

---

## 6. Slack App Architecture

### Decision: Events API + Socket Mode for Development

**Rationale**: Events API is production-ready with webhook reliability; Socket Mode simplifies local development without ngrok.

### Research Findings

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SLACK APP ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Production:                    Development:                     │
│  ┌──────────────┐              ┌──────────────┐                 │
│  │ Events API   │              │ Socket Mode  │                 │
│  │ (Webhooks)   │              │ (WebSocket)  │                 │
│  └──────┬───────┘              └──────┬───────┘                 │
│         │                             │                          │
│         └─────────────┬───────────────┘                          │
│                       │                                          │
│                       ▼                                          │
│            ┌──────────────────────┐                             │
│            │   Event Dispatcher   │                             │
│            └──────────┬───────────┘                             │
│                       │                                          │
│         ┌─────────────┼─────────────┐                           │
│         ▼             ▼             ▼                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                  │
│  │   Slash    │ │Interactive │ │   Event    │                  │
│  │  Commands  │ │  Actions   │ │ Handlers   │                  │
│  └────────────┘ └────────────┘ └────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Implementation

```python
# backend/src/pilot_space/integrations/slack/client.py
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

app = AsyncApp(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET
)

# Slash command handler
@app.command("/pilot")
async def handle_pilot_command(ack, command, client):
    await ack()

    subcommand = command['text'].split()[0] if command['text'] else ''

    if subcommand == 'create':
        await open_create_issue_modal(client, command)
    elif subcommand == 'search':
        query = command['text'][7:]  # Remove 'search '
        await show_search_results(client, command, query)
    elif subcommand == 'sprint':
        await show_sprint_status(client, command)
    else:
        await client.chat_postEphemeral(
            channel=command['channel_id'],
            user=command['user_id'],
            text="Usage: /pilot [create|search <query>|sprint]"
        )

# Event handler for URL unfurling
@app.event("link_shared")
async def handle_link_shared(event, client):
    links = event.get('links', [])
    unfurls = {}

    for link in links:
        if 'pilot-space.com' in link['url']:
            unfurl = await generate_link_preview(link['url'])
            unfurls[link['url']] = unfurl

    if unfurls:
        await client.chat_unfurl(
            channel=event['channel'],
            ts=event['message_ts'],
            unfurls=unfurls
        )
```

#### Notification Formatting

```python
# Rich notification blocks
def format_issue_notification(issue: Issue) -> list[dict]:
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 {issue.project.identifier}-{issue.sequence_id}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{issue.name}*\n{issue.description[:200]}..."
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "View"},
                "url": f"https://pilot-space.com/issue/{issue.id}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Priority:* {issue.priority} | *Assignee:* @{issue.assignee.name}"
                }
            ]
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Assign to me"},
                    "action_id": "assign_self",
                    "value": str(issue.id)
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Change Status"},
                    "action_id": "change_status",
                    "value": str(issue.id)
                }
            ]
        }
    ]
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| Socket Mode only | Not production-grade, connection issues |
| RTM API | Deprecated |
| Incoming Webhooks only | No interactivity support |

---

## 7. Real-time UI Updates

### Decision: Server-Sent Events (SSE) for AI Streaming

**Rationale**: SSE is simpler than WebSocket for unidirectional streaming (AI responses), has native browser support, and is easier to implement with FastAPI.

### Research Findings

#### SSE Implementation

```python
# backend/src/pilot_space/api/v1/routers/ai.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/notes/{note_id}/ghost-text")
async def stream_ghost_text(
    note_id: UUID,
    cursor_position: int,
    context: str,
    current_user: User = Depends(get_current_user)
):
    """Stream ghost text suggestions via SSE."""

    async def generate():
        provider = get_ai_provider(current_user.workspace_id, "ghost_text")

        async for chunk in provider.stream(
            CompletionRequest(
                messages=[
                    {"role": "system", "content": GHOST_TEXT_PROMPT},
                    {"role": "user", "content": context}
                ],
                max_tokens=100,
                stream=True
            )
        ):
            yield f"data: {json.dumps({'text': chunk})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
```

#### Frontend SSE Client

```typescript
// frontend/src/services/ai.ts
export function streamGhostText(
  noteId: string,
  cursorPosition: number,
  context: string,
  onChunk: (text: string) => void,
  onComplete: () => void,
  onError: (error: Error) => void
): () => void {
  const url = new URL(`/api/v1/notes/${noteId}/ghost-text`, window.location.origin);
  url.searchParams.set('cursor_position', cursorPosition.toString());
  url.searchParams.set('context', context);

  const eventSource = new EventSource(url.toString());

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close();
      onComplete();
      return;
    }

    const data = JSON.parse(event.data);
    onChunk(data.text);
  };

  eventSource.onerror = (error) => {
    eventSource.close();
    onError(new Error('SSE connection failed'));
  };

  // Return cleanup function
  return () => eventSource.close();
}
```

#### Debounce Strategy for Autosave

```typescript
// frontend/src/hooks/useAutosave.ts
import { useDebouncedCallback } from 'use-debounce';

export function useAutosave(
  noteId: string,
  content: () => JSONContent,
  options = { delay: 1500 }  // 1-2 seconds per DD-049
) {
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  const debouncedSave = useDebouncedCallback(
    async () => {
      setSaveStatus('saving');
      try {
        await saveNote(noteId, content());
        setSaveStatus('saved');
        // Reset to idle after showing "Saved" briefly
        setTimeout(() => setSaveStatus('idle'), 1500);
      } catch (error) {
        // Show error in margin annotation per DD-025
        showSaveError(error);
        setSaveStatus('idle');
      }
    },
    options.delay
  );

  return { saveStatus, triggerSave: debouncedSave };
}
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| WebSocket | Overkill for unidirectional streaming, more complex |
| HTTP/2 Push | Less browser support, complex setup |
| Long polling | Inefficient, higher latency |

---

## 8. Virtualized Rendering

### Decision: @tanstack/react-virtual (formerly react-virtual)

**Rationale**: More actively maintained than react-window, better TypeScript support, smaller bundle, works well with variable-height items.

### Research Findings

#### Implementation

```typescript
// frontend/src/components/editor/VirtualizedNoteCanvas.tsx
import { useVirtualizer } from '@tanstack/react-virtual';

interface Block {
  id: string;
  type: string;
  content: JSONContent;
  estimatedHeight: number;
}

export function VirtualizedNoteCanvas({ blocks }: { blocks: Block[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: blocks.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => blocks[index].estimatedHeight,
    overscan: 5,  // Render 5 extra items for smooth scrolling
    measureElement: (el) => el.getBoundingClientRect().height,
  });

  return (
    <div ref={parentRef} className="h-full overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={blocks[virtualItem.index].id}
            data-index={virtualItem.index}
            ref={virtualizer.measureElement}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <BlockRenderer block={blocks[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### Block Measurement Caching

```typescript
// Cache measured heights to avoid re-measurement
const heightCache = new Map<string, number>();

const estimateSize = (index: number) => {
  const block = blocks[index];
  const cached = heightCache.get(block.id);
  if (cached) return cached;

  // Estimate based on content type
  switch (block.type) {
    case 'heading':
      return 48;
    case 'paragraph':
      return Math.max(24, Math.ceil(block.content.text.length / 80) * 24);
    case 'codeBlock':
      return Math.max(100, block.content.code.split('\n').length * 20);
    default:
      return 40;
  }
};

// Update cache when measured
const measureElement = (el: Element) => {
  const index = Number(el.getAttribute('data-index'));
  const height = el.getBoundingClientRect().height;
  heightCache.set(blocks[index].id, height);
  return height;
};
```

#### Scroll Position Preservation

```typescript
// Preserve scroll position on content changes
const useScrollPreservation = (blocks: Block[]) => {
  const virtualizerRef = useRef<Virtualizer<HTMLDivElement, Element>>();
  const lastScrollOffset = useRef(0);

  useEffect(() => {
    if (!virtualizerRef.current) return;

    // Store scroll position before update
    lastScrollOffset.current = virtualizerRef.current.scrollOffset;

    return () => {
      // Restore after render
      requestAnimationFrame(() => {
        virtualizerRef.current?.scrollToOffset(lastScrollOffset.current);
      });
    };
  }, [blocks.length]);

  return virtualizerRef;
};
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| react-window | Less active, fixed-size items only |
| react-virtualized | Heavy, not well maintained |
| Custom implementation | Time-consuming, error-prone |

---

## 9. Background Job System

### Decision: Supabase Queues (pgmq + pg_cron)

**Rationale**: Session 2026-01-22 decision - Supabase Queues reduces infrastructure from 10 services to 3, leverages PostgreSQL for job persistence, integrates with RLS.

### Research Findings

#### Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                 SUPABASE QUEUES ARCHITECTURE                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FastAPI Backend                   Supabase                    │
│  ┌──────────────┐                 ┌──────────────────────┐    │
│  │ API Endpoint │ ─── enqueue ──▶ │ pgmq (Message Queue) │    │
│  └──────────────┘                 └──────────┬───────────┘    │
│                                              │                 │
│                                              ▼                 │
│  ┌──────────────┐                 ┌──────────────────────┐    │
│  │ Edge Function│ ◀── trigger ─── │ pg_cron (Scheduler)  │    │
│  │   (Worker)   │                 └──────────────────────┘    │
│  └──────┬───────┘                                              │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Job Handlers: AI Review, Embeddings, Notifications    │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

#### Configuration (per Session 2026-01-22)

```sql
-- Create queues with priority levels
SELECT pgmq.create('ai_high');     -- PR review, ghost text
SELECT pgmq.create('ai_normal');   -- Embeddings, summaries
SELECT pgmq.create('ai_low');      -- Graph recalc, cleanup

-- Dead letter queue for failed jobs
SELECT pgmq.create('dead_letter');

-- Schedule batch jobs (nightly 2 AM UTC per Session 2026-01-22)
SELECT cron.schedule(
    'semantic-graph-recalc',
    '0 2 * * *',  -- 2 AM UTC daily
    $$SELECT process_semantic_relationships()$$
);

SELECT cron.schedule(
    'cleanup-expired-sessions',
    '0 3 * * *',  -- 3 AM UTC daily
    $$SELECT cleanup_expired_data()$$
);
```

#### Task Definitions

```python
# backend/src/pilot_space/infrastructure/queue/supabase_queue.py
from supabase import create_client

class SupabaseQueue:
    def __init__(self):
        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

    async def enqueue(
        self,
        queue_name: str,
        payload: dict,
        delay_seconds: int = 0
    ) -> str:
        """Enqueue a job to Supabase Queue."""
        result = await self.client.rpc(
            'pgmq_send',
            {
                'queue_name': queue_name,
                'msg': payload,
                'delay': delay_seconds
            }
        ).execute()
        return result.data

    async def process_job(self, queue_name: str) -> dict | None:
        """Read and process a job from queue."""
        result = await self.client.rpc(
            'pgmq_read',
            {
                'queue_name': queue_name,
                'vt': 300,  # 5 minute visibility timeout (AI timeout per Session 2026-01-22)
                'qty': 1
            }
        ).execute()
        return result.data[0] if result.data else None

# Job handlers with retry logic
async def ai_pr_review(job_data: dict):
    """Perform AI code review on pull request."""
    try:
        review = await PRReviewAgent().review(job_data)
        await GitHubClient().post_review(job_data, review)
        await notify_pr_review_complete(job_data)
    except RateLimitError as e:
        # Re-enqueue with delay for retry
        await queue.enqueue('ai_high', job_data, delay_seconds=e.retry_after)
        await notify_pr_review_delayed(job_data, e.retry_after)
    except Exception as e:
        # Move to dead letter queue after max retries
        if job_data.get('retry_count', 0) >= 3:
            await queue.enqueue('dead_letter', {**job_data, 'error': str(e)})
            await notify_admin_job_failed(job_data, e)
        else:
            job_data['retry_count'] = job_data.get('retry_count', 0) + 1
            await queue.enqueue('ai_high', job_data, delay_seconds=60)
```

#### Priority Levels (per Session 2026-01-22)

| Queue | Priority | Jobs | Timeout |
|-------|----------|------|---------|
| `ai_high` | High | PR review, ghost text | 5 min |
| `ai_normal` | Normal | Embeddings, summaries | 5 min |
| `ai_low` | Low | Graph recalc, cleanup | 10 min |

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| Celery + RabbitMQ | Additional infrastructure, more services to manage |
| AWS SQS | External dependency, not integrated with Supabase |
| Redis Streams | Separate Redis instance needed |
| BullMQ | Requires separate Node.js worker |

---

## 10. Frontend Framework

### Decision: Next.js 14+ App Router

**Rationale**: Server components reduce bundle size, streaming SSR improves perceived performance, built-in API routes simplify BFF pattern, mature ecosystem.

### Research Findings

#### Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout with providers
│   │   ├── page.tsx             # Home → Note Canvas
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── callback/page.tsx
│   │   ├── (workspace)/
│   │   │   ├── layout.tsx       # Workspace layout with sidebar
│   │   │   ├── [workspaceSlug]/
│   │   │   │   ├── page.tsx     # Workspace home
│   │   │   │   ├── projects/
│   │   │   │   ├── issues/
│   │   │   │   ├── cycles/
│   │   │   │   └── settings/
│   │   │   └── notes/
│   │   │       ├── [noteId]/page.tsx
│   │   │       └── new/page.tsx
│   │   └── public/              # Public views (merged Space)
│   │       └── [workspaceSlug]/
│   │           └── [projectSlug]/
│   │               └── issues/[issueId]/page.tsx
│   │
│   ├── components/              # Shared components
│   ├── stores/                  # MobX stores
│   ├── services/                # API clients
│   └── lib/                     # Utilities
```

#### Server Components for Data Fetching

```typescript
// app/(workspace)/[workspaceSlug]/issues/page.tsx
import { getIssues } from '@/services/api';
import { IssueList } from '@/components/issues/IssueList';

// Server Component - no "use client"
export default async function IssuesPage({
  params,
  searchParams,
}: {
  params: { workspaceSlug: string };
  searchParams: { state?: string; priority?: string };
}) {
  // Data fetched on server
  const issues = await getIssues(params.workspaceSlug, searchParams);

  return (
    <div>
      <h1>Issues</h1>
      {/* Client component for interactivity */}
      <IssueList initialIssues={issues} />
    </div>
  );
}
```

#### Streaming for AI Responses

```typescript
// app/api/ai/ghost-text/route.ts
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const context = searchParams.get('context');

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const response = await getAIStream(context);

      for await (const chunk of response) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ text: chunk })}\n\n`)
        );
      }

      controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  });
}
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| Vite + React Router | No SSR benefits, separate API server needed |
| Remix | Less mature, smaller ecosystem |
| Astro | Not ideal for highly interactive apps |

---

---

## 11. Knowledge Graph Visualization

### Decision: Sigma.js + react-sigma (WebGL)

**Rationale**: Session 2026-01-22 decision - Sigma.js provides WebGL-based rendering for 50K+ nodes with ForceAtlas2 layout algorithm.

### Research Findings

#### Technology Stack

```
Graphology (data model)
    ↓
Sigma.js (WebGL rendering)
    ↓
@react-sigma/core (React bindings)
    ↓
@react-sigma/layout-force (ForceAtlas2)
    ↓
@react-sigma/minimap (navigation)
```

#### Implementation

```typescript
// frontend/src/components/knowledge/KnowledgeGraph.tsx
import { SigmaContainer, ControlsContainer } from '@react-sigma/core';
import { LayoutForceAtlas2Control } from '@react-sigma/layout-forceatlas2';
import { MiniMap } from '@react-sigma/minimap';
import Graph from 'graphology';

interface KnowledgeGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function KnowledgeGraph({ nodes, edges }: KnowledgeGraphProps) {
  const graph = useMemo(() => {
    const g = new Graph();

    nodes.forEach(node => {
      g.addNode(node.id, {
        label: node.label,
        size: node.size || 10,
        color: getNodeColor(node.type),
        x: Math.random(),
        y: Math.random(),
      });
    });

    edges.forEach(edge => {
      g.addEdge(edge.source, edge.target, {
        type: edge.type,
        weight: edge.weight || 1,
        color: getEdgeColor(edge.type),
      });
    });

    return g;
  }, [nodes, edges]);

  return (
    <SigmaContainer
      graph={graph}
      settings={{
        renderEdgeLabels: true,
        defaultNodeType: 'circle',
        labelRenderedSizeThreshold: 8,
      }}
    >
      <ControlsContainer>
        <LayoutForceAtlas2Control
          settings={{
            gravity: 1,
            scalingRatio: 2,
            strongGravityMode: true,
            slowDown: 5,
          }}
          autoRunFor={2000}  // Always auto-layout per Session 2026-01-22
        />
      </ControlsContainer>
      <MiniMap />
    </SigmaContainer>
  );
}
```

#### Relationship Storage (per Session 2026-01-22)

```sql
-- PostgreSQL adjacency table for relationships
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_id UUID NOT NULL,
    to_id UUID NOT NULL,
    from_type VARCHAR(20) NOT NULL,  -- issue, note, page, code
    to_type VARCHAR(20) NOT NULL,
    relationship_type VARCHAR(30) NOT NULL,  -- explicit, semantic, mentions
    weight FLOAT DEFAULT 1.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_relationship UNIQUE (from_id, to_id, relationship_type)
);

-- Index for graph queries
CREATE INDEX idx_relationships_from ON relationships (from_id);
CREATE INDEX idx_relationships_to ON relationships (to_id);
CREATE INDEX idx_relationships_type ON relationships (relationship_type);
```

#### Semantic Relationship Detection (per Session 2026-01-22)

```python
# Detect semantic relationships via embedding similarity
async def detect_semantic_relationships(entity_id: UUID) -> list[Relationship]:
    # Get entity embedding
    entity_embedding = await get_embedding(entity_id)

    # Find similar entities (cosine > 0.7 per Session 2026-01-22)
    similar = await supabase.rpc(
        'match_embeddings',
        {
            'query_embedding': entity_embedding,
            'match_threshold': 0.7,
            'match_count': 20
        }
    ).execute()

    relationships = []
    for match in similar.data:
        if match['similarity'] > 0.7:
            relationships.append(Relationship(
                from_id=entity_id,
                to_id=match['entity_id'],
                relationship_type='semantic',
                weight=match['similarity'],
                metadata={'similarity_score': match['similarity']}
            ))

    return relationships
```

### Alternatives Rejected

| Alternative | Reason Rejected |
|-------------|-----------------|
| Cytoscape.js | Slower for large graphs, canvas-based |
| React Flow | Designed for diagrams, not knowledge graphs |
| D3.js | Lower-level, more implementation effort |
| vis.js | Less modern, fewer React integrations |

---

## 12. State Management

### Decision: Feature-based MobX + TanStack Query

**Rationale**: Session 2026-01-22 decision - MobX for complex UI state (note canvas, AI interactions), TanStack Query for server state with optimistic updates.

### Research Findings

#### Store Organization

```typescript
// frontend/src/stores/RootStore.ts
import { createContext, useContext } from 'react';
import { IssueStore } from './IssueStore';
import { NoteStore } from './NoteStore';
import { AIStore } from './AIStore';
import { UIStore } from './UIStore';

class RootStore {
  issueStore: IssueStore;
  noteStore: NoteStore;
  aiStore: AIStore;
  uiStore: UIStore;

  constructor() {
    this.issueStore = new IssueStore(this);
    this.noteStore = new NoteStore(this);
    this.aiStore = new AIStore(this);
    this.uiStore = new UIStore(this);
  }
}

const StoreContext = createContext<RootStore | null>(null);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const store = useMemo(() => new RootStore(), []);
  return (
    <StoreContext.Provider value={store}>
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useStore must be used within StoreProvider');
  return store;
}
```

#### TanStack Query with Optimistic Updates (per Session 2026-01-22)

```typescript
// frontend/src/hooks/useIssues.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useUpdateIssue() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateIssue,
    onMutate: async (newIssue) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['issues', newIssue.id] });

      // Snapshot previous value
      const previousIssue = queryClient.getQueryData(['issues', newIssue.id]);

      // Optimistically update
      queryClient.setQueryData(['issues', newIssue.id], newIssue);

      // Return context for rollback
      return { previousIssue };
    },
    onError: (err, newIssue, context) => {
      // Rollback on error (per Session 2026-01-22)
      queryClient.setQueryData(['issues', newIssue.id], context?.previousIssue);
    },
    onSettled: (data, error, variables) => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries({ queryKey: ['issues', variables.id] });
    },
  });
}
```

#### Response Envelope Format (per Session 2026-01-22)

```typescript
// Cursor-based pagination with envelope
interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    cursor: string | null;
    hasMore: boolean;
  };
}

// Usage in hooks
export function useIssuesList(filters: IssueFilters) {
  return useInfiniteQuery({
    queryKey: ['issues', filters],
    queryFn: ({ pageParam }) => fetchIssues({ ...filters, cursor: pageParam }),
    getNextPageParam: (lastPage) =>
      lastPage.meta.hasMore ? lastPage.meta.cursor : undefined,
  });
}
```

---

## Summary of Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| Rich Text Editor | Custom TipTap extensions | Full control for note-first UX |
| AI Providers | Unified adapter with streaming | Support 4 providers consistently |
| Embeddings | pgvector + HNSW + 3072 dims | Quality retrieval, native PostgreSQL |
| Authentication | Supabase Auth (GoTrue) | Unified with RLS, fewer services |
| Authorization | Row-Level Security (RLS) | Database-level enforcement |
| GitHub | GitHub App | Better rate limits, granular permissions |
| Slack | Events API + Socket Mode | Production-ready + dev-friendly |
| AI Streaming | SSE via StreamingResponse | Simpler than WebSocket for unidirectional |
| Virtualization | @tanstack/react-virtual | Modern, well-maintained |
| Task Queue | Supabase Queues (pgmq) | Native PostgreSQL, fewer services |
| Frontend | Next.js 14+ App Router | Server components, streaming SSR |
| Knowledge Graph | Sigma.js + react-sigma | WebGL, 50K+ nodes, ForceAtlas2 |
| State Management | MobX + TanStack Query | Complex UI + server state |
| Pagination | Cursor-based | Stable with real-time updates |

---

*Research Version: 2.0*
*Generated: 2026-01-22*
*Updates: Supabase platform, Sigma.js, MobX+TanStack Query, 50+ implementation decisions*
*Next Step: Generate data-model.md based on spec entities*
