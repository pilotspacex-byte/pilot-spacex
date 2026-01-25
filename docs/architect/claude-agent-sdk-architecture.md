# Claude Agent SDK Architecture for Pilot Space MVP

**Version**: 1.0.0
**Date**: 2026-01-22
**Status**: Approved
**References**: DD-002, DD-003, DD-006, DD-011, ai-layer.md

---

## Executive Summary

This document details the Claude Agent SDK integration architecture for Pilot Space MVP. The Claude Agent SDK serves as the **primary AI orchestration layer** for all agentic tasks, providing unified tool execution, multi-turn conversations, and seamless integration with Pilot Space's custom MCP tools.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary Orchestrator | Claude Agent SDK | Best agentic capabilities, MCP tool support |
| Primary Model | Claude Opus 4.5 | Superior code understanding, reasoning |
| API Pattern | `query()` + `ClaudeSDKClient` | Task-based selection |
| Tool Protocol | Model Context Protocol (MCP) | Standard tool interface |
| Streaming | SSE via FastAPI | Real-time response delivery |

---

## BYOK (Bring Your Own Key) Architecture

### Overview (DD-002)

Pilot Space uses a **BYOK (Bring Your Own Key)** model where users must provide their own LLM API keys. This architectural decision ensures:

- **No platform-hosted LLM costs** - Pilot Space doesn't need to scale/manage LLM infrastructure
- **User cost control** - Users pay directly to providers, monitor costs via provider dashboards
- **No usage limits** - When valid API key is provided, AI features have no artificial limits
- **Provider flexibility** - Users choose providers based on their needs/preferences

### Required vs Optional Keys

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BYOK PROVIDER REQUIREMENTS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    REQUIRED FOR AI FEATURES                            │ │
│  │                                                                         │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │  ANTHROPIC API KEY                                              │  │ │
│  │   │  ─────────────────                                              │  │ │
│  │   │  Required for: Claude Agent SDK orchestration                   │  │ │
│  │   │  Used by: All agentic tasks (PR review, task decomposition,     │  │ │
│  │   │           AI context, documentation, issue enhancement)         │  │ │
│  │   │  Models: claude-opus-4-5, claude-sonnet-4, claude-3-5-haiku     │  │ │
│  │   │                                                                 │  │ │
│  │   │  ⚠️ WITHOUT THIS KEY: Core AI features will be disabled         │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │  OPENAI API KEY                                                 │  │ │
│  │   │  ─────────────                                                  │  │ │
│  │   │  Required for: Embeddings (semantic search, RAG, duplicates)    │  │ │
│  │   │  Used by: text-embedding-3-large (3072 dimensions)              │  │ │
│  │   │  Models: text-embedding-3-large                                 │  │ │
│  │   │                                                                 │  │ │
│  │   │  ⚠️ WITHOUT THIS KEY: Semantic search will be disabled          │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    OPTIONAL (RECOMMENDED)                              │ │
│  │                                                                         │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │  GOOGLE API KEY (Gemini)                                        │  │ │
│  │   │  ─────────────────────                                          │  │ │
│  │   │  Recommended for: Latency-sensitive tasks, large context        │  │ │
│  │   │  Used by: Ghost text, margin annotations, large codebase        │  │ │
│  │   │  Models: gemini-2.0-flash (256K), gemini-2.0-pro (2M context)   │  │ │
│  │   │                                                                 │  │ │
│  │   │  💡 WITHOUT THIS KEY: Falls back to Claude Haiku (slower)       │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                         │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐  │ │
│  │   │  AZURE OPENAI KEY + ENDPOINT                                    │  │ │
│  │   │  ─────────────────────────                                      │  │ │
│  │   │  Optional for: Enterprise data residency requirements           │  │ │
│  │   │  Used by: Fallback for compliance-sensitive workspaces          │  │ │
│  │   │  Models: gpt-4o (via Azure)                                     │  │ │
│  │   │                                                                 │  │ │
│  │   │  💡 Enterprise feature for data sovereignty                     │  │ │
│  │   └─────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Storage & Security

```python
# API keys are stored encrypted using Supabase Vault (AES-256-GCM)
# Keys are NEVER stored in plaintext or logged

# ai/infrastructure/key_storage.py
from supabase import create_client
from cryptography.fernet import Fernet

class SecureKeyStorage:
    """Secure API key storage using Supabase Vault.

    Security measures:
    - AES-256-GCM encryption at rest
    - Keys decrypted only at runtime
    - Audit logging for key access
    - Per-workspace isolation
    """

    async def store_api_key(
        self,
        workspace_id: str,
        provider: str,
        api_key: str,
    ) -> None:
        """Store encrypted API key."""
        # Encrypt using Supabase Vault
        encrypted = await self.vault.encrypt(api_key)

        await self.db.execute("""
            INSERT INTO workspace_api_keys (workspace_id, provider, encrypted_key)
            VALUES (:workspace_id, :provider, :encrypted_key)
            ON CONFLICT (workspace_id, provider)
            DO UPDATE SET encrypted_key = :encrypted_key, updated_at = now()
        """, {
            "workspace_id": workspace_id,
            "provider": provider,
            "encrypted_key": encrypted,
        })

    async def get_api_key(
        self,
        workspace_id: str,
        provider: str,
    ) -> str | None:
        """Retrieve and decrypt API key."""
        result = await self.db.execute("""
            SELECT encrypted_key FROM workspace_api_keys
            WHERE workspace_id = :workspace_id AND provider = :provider
        """, {"workspace_id": workspace_id, "provider": provider})

        row = result.fetchone()
        if not row:
            return None

        return await self.vault.decrypt(row.encrypted_key)

    async def validate_api_key(
        self,
        provider: str,
        api_key: str,
    ) -> bool:
        """Validate API key by making test call to provider."""
        try:
            if provider == "anthropic":
                # Test Claude API
                client = AsyncAnthropic(api_key=api_key)
                await client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
            elif provider == "openai":
                # Test OpenAI API
                client = AsyncOpenAI(api_key=api_key)
                await client.embeddings.create(
                    model="text-embedding-3-large",
                    input="test",
                    dimensions=256,
                )
            elif provider == "google":
                # Test Gemini API
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")
                await model.generate_content_async("test")

            return True
        except Exception:
            return False
```

### Configuration Model

```yaml
# Workspace AI Configuration (stored in workspace_settings)
ai:
  # Orchestration layer (required for agentic features)
  orchestrator:
    sdk: claude-agent-sdk
    default_model: claude-opus-4-5
    required: true  # Anthropic key needed for core AI features

  providers:
    anthropic:
      api_key: ${USER_ANTHROPIC_KEY}  # User-provided (REQUIRED)
      models: [claude-opus-4-5, claude-sonnet-4, claude-3-5-haiku-20241022]
      use_for: [pr_review, task_decomposition, ai_context, doc_generation, issue_enhancement]

    google:
      api_key: ${USER_GOOGLE_KEY}  # User-provided (optional but recommended)
      models: [gemini-2.0-pro, gemini-2.0-flash]
      use_for: [ghost_text, margin_annotations, notification_priority, large_context]

    openai:
      api_key: ${USER_OPENAI_KEY}  # User-provided (required for embeddings)
      models: [gpt-4o, gpt-4o-mini, text-embedding-3-large]
      use_for: [embeddings, fallback_generation]

    azure_openai:
      api_key: ${USER_AZURE_KEY}  # User-provided (optional)
      endpoint: ${USER_AZURE_ENDPOINT}
      use_for: [enterprise_fallback]

  # No local model support per DD-002
  # ollama: NOT SUPPORTED
```

---

## Human-in-the-Loop Approval (DD-003)

### AI Autonomy Model

Pilot Space implements a **Critical-Only Approval** model where AI actions are classified by their impact:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AI AUTONOMY CLASSIFICATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  AUTO-EXECUTE                    HUMAN APPROVAL                             │
│  ────────────                    ──────────────                             │
│  Non-destructive                 Destructive/Critical                       │
│  Reversible                      Irreversible                               │
│  Low impact                      High impact                                │
│                                                                              │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────────┐│
│  │ ✅ AUTO-EXECUTE         │    │ ⚠️ REQUIRE APPROVAL                      ││
│  │                         │    │                                          ││
│  │ • Suggest labels        │    │ • Create sub-issues                     ││
│  │ • Suggest priority      │    │ • Delete any content                    ││
│  │ • Show ghost text       │    │ • Archive projects                      ││
│  │ • Display annotations   │    │ • Publish documentation                 ││
│  │ • Post PR comments      │    │ • Merge PRs                             ││
│  │ • State transitions     │    │ • Bulk operations                       ││
│  │ • Send notifications    │    │ • External API writes                   ││
│  │                         │    │                                          ││
│  │ User notified after     │    │ User must explicitly approve            ││
│  └─────────────────────────┘    └─────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Action Classification

| Action | Default Behavior | Configurable | Category |
|--------|------------------|--------------|----------|
| Suggest labels/priority | Auto-apply to suggestion UI | Yes | Non-destructive |
| Show ghost text | Auto-display | Yes | Non-destructive |
| Display margin annotations | Auto-display | Yes | Non-destructive |
| Auto-transition on PR events | Auto-execute + notify | Yes | Low impact |
| Post PR review comments | Auto-execute | Yes | Low impact |
| Send notifications | Auto-execute | Yes | Low impact |
| Create sub-issues | **Require approval** | Yes | Creates content |
| Extract issues from note | **Require approval** | Yes | Creates content |
| Delete/archive any content | **Always require approval** | No | Destructive |
| Merge PRs | **Always require approval** | No | Irreversible |
| Publish documentation | **Require approval** | Yes | External impact |

### Approval Flow Implementation

```python
# ai/infrastructure/approval.py
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import uuid


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class AIApprovalRequest:
    """Request for human approval of AI action.

    Implements DD-003: Critical-only approval model.
    """
    id: str
    user_id: str
    workspace_id: str
    action_type: str  # "create_issue", "delete", "publish_docs", etc.
    description: str  # Human-readable description
    payload: dict     # Data needed to execute action
    confidence: float # AI confidence (0.0-1.0)
    status: ApprovalStatus
    expires_at: datetime
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class ApprovalService:
    """Manage AI action approvals per DD-003."""

    # Actions that ALWAYS require approval (cannot be overridden)
    ALWAYS_REQUIRE_APPROVAL = {
        "delete_workspace",
        "delete_project",
        "delete_issue",
        "delete_note",
        "merge_pr",
        "bulk_delete",
    }

    # Actions that require approval by default (can be overridden per project)
    DEFAULT_REQUIRE_APPROVAL = {
        "create_sub_issues",
        "extract_issues",
        "publish_docs",
        "create_from_template",
    }

    # Actions that auto-execute with notification (can be disabled)
    AUTO_EXECUTE_WITH_NOTIFY = {
        "suggest_labels",
        "suggest_priority",
        "auto_transition_state",
        "post_pr_comments",
        "send_notifications",
    }

    async def check_approval_required(
        self,
        action_type: str,
        project_settings: dict,
    ) -> bool:
        """Check if action requires human approval."""
        # Always require approval for destructive actions
        if action_type in self.ALWAYS_REQUIRE_APPROVAL:
            return True

        # Check project-level override
        overrides = project_settings.get("ai_autonomy", {}).get("overrides", {})
        if action_type in overrides:
            return overrides[action_type] == "approval"

        # Default behavior
        return action_type in self.DEFAULT_REQUIRE_APPROVAL

    async def create_approval_request(
        self,
        user_id: str,
        workspace_id: str,
        action_type: str,
        description: str,
        payload: dict,
        confidence: float,
    ) -> AIApprovalRequest:
        """Create approval request and notify user."""
        request = AIApprovalRequest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            workspace_id=workspace_id,
            action_type=action_type,
            description=description,
            payload=payload,
            confidence=confidence,
            status=ApprovalStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            created_at=datetime.utcnow(),
        )

        # Store request
        await self._store(request)

        # Notify user (in-app + optionally Slack)
        await self._notify_user(request)

        return request

    async def resolve(
        self,
        request_id: str,
        approved: bool,
        resolved_by: str,
    ) -> AIApprovalRequest:
        """Resolve approval request."""
        request = await self._get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        request.resolved_at = datetime.utcnow()
        request.resolved_by = resolved_by

        await self._store(request)

        if approved:
            await self._execute_action(request)

        return request

    async def _execute_action(self, request: AIApprovalRequest) -> None:
        """Execute approved action."""
        action_handlers = {
            "create_sub_issues": self._handle_create_sub_issues,
            "extract_issues": self._handle_extract_issues,
            "publish_docs": self._handle_publish_docs,
        }

        handler = action_handlers.get(request.action_type)
        if handler:
            await handler(request.payload)
```

### Project-Level Autonomy Configuration

```yaml
# Project settings (stored in project.settings JSONB)
project:
  ai_autonomy:
    level: balanced  # conservative | balanced | autonomous

    overrides:
      # Override default behavior for specific actions
      state_transitions: auto      # auto | approval | disabled
      pr_comments: auto
      issue_creation: approval     # Force approval for issue creation
      documentation: approval
      label_suggestions: auto

    notifications:
      # Control notifications for auto-executed actions
      show_state_transitions: true
      show_pr_comments: true
      show_suggestions: true
```

### Frontend Approval UI

```typescript
// components/ai/ApprovalDialog.tsx
import { Dialog, Button, Badge } from '@/components/ui';
import { AIApprovalRequest } from '@/types';

interface ApprovalDialogProps {
  request: AIApprovalRequest;
  onApprove: () => void;
  onReject: () => void;
}

export function ApprovalDialog({ request, onApprove, onReject }: ApprovalDialogProps) {
  return (
    <Dialog open={true}>
      <Dialog.Content>
        <Dialog.Header>
          <Badge variant="ai">✨ AI Action Approval</Badge>
          <Dialog.Title>{getActionTitle(request.action_type)}</Dialog.Title>
        </Dialog.Header>

        <Dialog.Body>
          <p className="text-sm text-muted-foreground">
            {request.description}
          </p>

          {/* Show AI confidence */}
          <div className="mt-4 p-3 bg-muted rounded-lg">
            <span className="text-xs font-medium">AI Confidence</span>
            <ConfidenceTag confidence={request.confidence} />
          </div>

          {/* Show preview of action */}
          <ActionPreview payload={request.payload} type={request.action_type} />
        </Dialog.Body>

        <Dialog.Footer>
          <Button variant="outline" onClick={onReject}>
            Reject
          </Button>
          <Button variant="primary" onClick={onApprove}>
            Approve & Execute
          </Button>
        </Dialog.Footer>
      </Dialog.Content>
    </Dialog>
  );
}
```

---

## Unified PR Review (DD-006)

### Overview

Pilot Space combines **Architecture Review** and **Code Review** into a single unified "AI PR Review" feature. This decision ensures:

- AI-powered PR review as a core differentiator
- Combined review provides more value than separate features
- Single feature is easier to understand and use
- Architecture and code quality are closely related

### Review Aspects

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED PR REVIEW (DD-006)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     ARCHITECTURE REVIEW                                  ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                  ││
│  │  │ Layer         │ │ Design        │ │ Dependency    │                  ││
│  │  │ Boundaries    │ │ Patterns      │ │ Direction     │                  ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘                  ││
│  │  • Controllers calling repositories directly?                           ││
│  │  • Missing service layer abstractions?                                  ││
│  │  • Circular dependencies introduced?                                    ││
│  │  • Domain logic leaking to presentation?                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     SECURITY REVIEW                                      ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                  ││
│  │  │ OWASP         │ │ Secrets       │ │ Auth/Authz    │                  ││
│  │  │ Top 10        │ │ Detection     │ │ Checks        │                  ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘                  ││
│  │  • SQL injection, XSS, CSRF vulnerabilities?                            ││
│  │  • Hardcoded credentials or API keys?                                   ││
│  │  • Missing authentication on endpoints?                                 ││
│  │  • Improper authorization checks?                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     CODE QUALITY REVIEW                                  ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                  ││
│  │  │ Complexity    │ │ Duplication   │ │ Naming        │                  ││
│  │  │ (Cyclomatic)  │ │ (DRY)         │ │ Conventions   │                  ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘                  ││
│  │  • Functions with complexity > 10?                                      ││
│  │  • Copy-pasted code blocks?                                             ││
│  │  • Unclear variable/function names?                                     ││
│  │  • Missing type annotations?                                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     PERFORMANCE REVIEW                                   ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                  ││
│  │  │ N+1 Queries   │ │ Blocking      │ │ Resource      │                  ││
│  │  │               │ │ Calls         │ │ Leaks         │                  ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘                  ││
│  │  • Database queries in loops?                                           ││
│  │  • Synchronous I/O in async context?                                    ││
│  │  • Unclosed file handles or connections?                                ││
│  │  • Missing pagination on list endpoints?                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                     DOCUMENTATION REVIEW                                 ││
│  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                  ││
│  │  │ Missing       │ │ Outdated      │ │ Test          │                  ││
│  │  │ Docstrings    │ │ Comments      │ │ Coverage      │                  ││
│  │  └───────────────┘ └───────────────┘ └───────────────┘                  ││
│  │  • Public functions without docstrings?                                 ││
│  │  • Comments that no longer match code?                                  ││
│  │  • New code paths without tests?                                        ││
│  │  • README updates needed?                                               ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### PRReviewAgent Implementation

```python
# ai/agents/pr_review_agent.py
from pilot_space.ai.agents.base import BaseAgent
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, ResultMessage
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class PRReviewResult:
    """Structured PR review result per DD-006."""
    # Architecture issues
    architecture_issues: list[dict]  # Layer violations, pattern issues

    # Security issues
    security_issues: list[dict]      # OWASP, secrets, auth

    # Code quality issues
    code_quality_issues: list[dict]  # Complexity, duplication, naming

    # Performance issues
    performance_issues: list[dict]   # N+1, blocking, leaks

    # Documentation issues
    documentation_issues: list[dict] # Missing docs, outdated comments

    # Overall recommendation
    overall_recommendation: str      # "approve", "request_changes", "comment"
    summary: str
    confidence: float
    total_cost_usd: float


class PRReviewAgent(BaseAgent):
    """Unified AI PR Review combining all review aspects.

    Implements DD-006: Both architecture and code review in MVP.

    Uses Claude Opus 4.5 via Claude Agent SDK with MCP tools
    to access codebase context and project conventions.
    """

    AGENT_NAME = "pr_review"
    DEFAULT_MODEL = "claude-opus-4-5"
    MAX_BUDGET_USD = 20.0  # PR reviews can be expensive
    MAX_TURNS = 15

    SYSTEM_PROMPT = """You are an expert code reviewer analyzing pull requests for Pilot Space.

Your review MUST cover all five aspects (per DD-006 Unified PR Review):

1. **Architecture** (🏗️)
   - Layer boundary violations (controller → service → repository)
   - Design pattern adherence
   - Dependency direction (no circular deps, proper abstraction)
   - Domain logic placement

2. **Security** (🔒)
   - OWASP Top 10 vulnerabilities
   - Hardcoded secrets or credentials
   - Authentication/authorization gaps
   - Input validation and sanitization

3. **Code Quality** (✨)
   - Cyclomatic complexity (flag > 10)
   - Code duplication (DRY violations)
   - Naming conventions and clarity
   - Type safety and annotations

4. **Performance** (⚡)
   - N+1 query patterns
   - Blocking I/O in async context
   - Resource leaks (unclosed handles)
   - Missing pagination

5. **Documentation** (📚)
   - Missing docstrings on public functions
   - Outdated comments
   - Test coverage for new code
   - README/changelog updates

Format your review as Markdown with severity indicators:
- 🔴 **Critical**: Must fix before merge
- 🟡 **Warning**: Should fix, but not blocking
- 🔵 **Info**: Suggestions for improvement

For each issue, provide:
1. **Location**: `file:line` or `file:line-range`
2. **Issue**: Clear description of the problem
3. **Suggestion**: How to fix it
4. **Rationale**: Why this matters

End with:
- **Summary**: Overall assessment
- **Recommendation**: APPROVE, REQUEST_CHANGES, or COMMENT
- **Confidence**: Your confidence in this review"""

    async def execute(
        self,
        pr_number: int,
        repo_full_name: str,
        project_id: str,
        user_id: str,
        workspace_id: str,
    ) -> AsyncIterator[str]:
        """Execute comprehensive PR review with streaming.

        Args:
            pr_number: GitHub PR number
            repo_full_name: Repository in 'owner/repo' format
            project_id: Pilot Space project UUID
            user_id: Requesting user UUID
            workspace_id: Workspace UUID

        Yields:
            Markdown chunks of review content
        """
        prompt = f"""Review Pull Request #{pr_number} in {repo_full_name}.

Instructions:
1. Use `get_pr_details` to fetch PR metadata
2. Use `get_pr_diff` to get the full diff
3. Use `get_project_context` to understand project conventions
4. Use `search_codebase` to find related patterns and code
5. Analyze against all five review aspects
6. Provide structured review with severity ratings

Perform a thorough review covering Architecture, Security, Code Quality, Performance, and Documentation."""

        options = self._build_options(
            system_prompt=self.SYSTEM_PROMPT,
            allowed_tools=[
                "mcp__pilot_space__get_pr_details",
                "mcp__pilot_space__get_pr_diff",
                "mcp__pilot_space__get_project_context",
                "mcp__pilot_space__search_codebase",
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
                yield f"\n\n---\n*Review Cost: ${message.total_cost_usd:.4f} | Duration: {message.duration_ms}ms*"

    async def post_to_github(
        self,
        pr_number: int,
        repo_full_name: str,
        review_content: str,
        recommendation: str,
    ) -> None:
        """Post review to GitHub PR (auto-execute per DD-003)."""
        event_map = {
            "approve": "APPROVE",
            "request_changes": "REQUEST_CHANGES",
            "comment": "COMMENT",
        }

        await self.github_client.create_pr_review(
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            body=review_content,
            event=event_map.get(recommendation.lower(), "COMMENT"),
        )
```

### Review Output Format

```markdown
## 🔍 AI PR Review

**PR**: #123 - Add user authentication feature
**Repository**: owner/repo
**Files Changed**: 12 | **Additions**: +450 | **Deletions**: -23

---

### 🏗️ Architecture Review

🔴 **Critical**: Direct database access in controller
- **Location**: `src/api/controllers/auth_controller.py:45-52`
- **Issue**: Controller directly queries database, bypassing service layer
- **Suggestion**: Move database access to `AuthService.validate_credentials()`
- **Rationale**: Violates layered architecture; makes testing difficult

🟡 **Warning**: Missing repository abstraction
- **Location**: `src/services/auth_service.py:78`
- **Issue**: Service uses SQLAlchemy session directly
- **Suggestion**: Create `UserRepository` for data access
- **Rationale**: Per ADR-0023 Repository Pattern

### 🔒 Security Review

🔴 **Critical**: Potential SQL injection
- **Location**: `src/services/auth_service.py:92`
- **Issue**: f-string used in SQL query: `f"SELECT * FROM users WHERE email = '{email}'"`
- **Suggestion**: Use parameterized query: `session.execute(select(User).where(User.email == email))`
- **Rationale**: OWASP A03:2021 - Injection

🟡 **Warning**: Missing rate limiting on login endpoint
- **Location**: `src/api/routes/auth.py:15`
- **Issue**: No rate limiting on `/auth/login` endpoint
- **Suggestion**: Add `@rate_limit(max_requests=5, window_seconds=60)`
- **Rationale**: Prevents brute force attacks

### ✨ Code Quality Review

🟡 **Warning**: High cyclomatic complexity
- **Location**: `src/services/auth_service.py:100-150`
- **Issue**: `validate_user()` has complexity of 15 (threshold: 10)
- **Suggestion**: Extract validation logic into smaller functions
- **Rationale**: Improves testability and readability

### ⚡ Performance Review

✅ No performance issues detected

### 📚 Documentation Review

🔵 **Info**: Missing docstrings
- **Location**: `src/services/auth_service.py:25`
- **Issue**: `AuthService.authenticate()` lacks docstring
- **Suggestion**: Add docstring with parameters, returns, and raises
- **Rationale**: Public API should be documented

---

### Summary

This PR introduces user authentication but has **2 critical issues** that must be addressed:
1. SQL injection vulnerability in auth service
2. Direct database access in controller

Also found 3 warnings and 1 informational suggestion.

**Recommendation**: REQUEST_CHANGES
**Confidence**: 92%

---
*Review Cost: $0.0847 | Duration: 12,450ms*
```

---

## Provider Routing Rules (DD-011)

### Task-Based Provider Selection

Pilot Space routes AI tasks to optimal providers based on task characteristics:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROVIDER ROUTING RULES (DD-011)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TASK CHARACTERISTICS              →           OPTIMAL PROVIDER              │
│  ─────────────────────                         ────────────────              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ CODE-INTENSIVE TASKS                          → ANTHROPIC (CLAUDE)      ││
│  │                                                                          ││
│  │  • PR Review (architecture + code + security)   claude-opus-4-5         ││
│  │  • Task Decomposition                           claude-opus-4-5         ││
│  │  • AI Context Building                          claude-opus-4-5         ││
│  │  • Issue Enhancement                            claude-sonnet-4         ││
│  │  • Documentation Generation                     claude-sonnet-4         ││
│  │  • Diagram Generation                           claude-sonnet-4         ││
│  │                                                                          ││
│  │  RATIONALE: Best code understanding, MCP tool support, strong reasoning ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LATENCY-SENSITIVE TASKS                       → GOOGLE (GEMINI FLASH)   ││
│  │                                                                          ││
│  │  • Ghost Text Autocomplete                      gemini-2.0-flash        ││
│  │  • Margin Annotations                           gemini-2.0-flash        ││
│  │  • Notification Priority Scoring                gemini-2.0-flash        ││
│  │  • Quick Issue Detection                        gemini-2.0-flash        ││
│  │                                                                          ││
│  │  RATIONALE: <100ms first token, cost-effective, good enough quality     ││
│  │  FALLBACK: claude-3-5-haiku-20241022                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ LARGE CONTEXT TASKS                           → GOOGLE (GEMINI PRO)     ││
│  │                                                                          ││
│  │  • Large Codebase Analysis (>100K tokens)       gemini-2.0-pro (2M ctx) ││
│  │  • Full Repository Indexing                     gemini-2.0-pro          ││
│  │  • Cross-Project Analysis                       gemini-2.0-pro          ││
│  │                                                                          ││
│  │  RATIONALE: 2M token context window enables full codebase analysis      ││
│  │  FALLBACK: Chunked analysis with Claude                                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ EMBEDDING TASKS                               → OPENAI                   ││
│  │                                                                          ││
│  │  • Semantic Search Embeddings                   text-embedding-3-large  ││
│  │  • Duplicate Detection                          text-embedding-3-large  ││
│  │  • RAG Index Building                           text-embedding-3-large  ││
│  │  • Knowledge Graph Relationships                text-embedding-3-large  ││
│  │                                                                          ││
│  │  RATIONALE: Superior 3072-dimension vectors, best semantic resolution   ││
│  │  FALLBACK: Google gemini-embedding-001 (768-dim, less precise)          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ENTERPRISE COMPLIANCE                         → AZURE OPENAI             ││
│  │                                                                          ││
│  │  • Data Residency Requirements                  gpt-4o (via Azure)      ││
│  │  • Compliance-Sensitive Workspaces             gpt-4o (via Azure)       ││
│  │                                                                          ││
│  │  RATIONALE: Data sovereignty, enterprise compliance                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Provider Routing Table

| Task Type | Primary Provider | Model | Rationale | Fallback |
|-----------|------------------|-------|-----------|----------|
| **PR Review** | Anthropic | claude-opus-4-5 | Best code understanding + MCP | None (critical) |
| **Task Decomposition** | Anthropic | claude-opus-4-5 | Strong multi-step reasoning + MCP | None (critical) |
| **AI Context** | Anthropic | claude-opus-4-5 | Multi-turn + tool use | None (critical) |
| **Issue Enhancement** | Anthropic | claude-sonnet-4 | Balanced speed/quality | Claude Haiku |
| **Documentation** | Anthropic | claude-sonnet-4 | Good prose generation | Gemini Pro |
| **Diagram Generation** | Anthropic | claude-sonnet-4 | Structured output | Gemini Pro |
| **Ghost Text** | Google | gemini-2.0-flash | Lowest latency (~100ms) | Claude Haiku |
| **Margin Annotations** | Google | gemini-2.0-flash | Fast suggestions | Claude Haiku |
| **Notification Priority** | Google | gemini-2.0-flash | Quick scoring | Claude Haiku |
| **Large Codebase** | Google | gemini-2.0-pro | 2M token context | Chunked Claude |
| **Embeddings** | OpenAI | text-embedding-3-large | Best 3072-dim vectors | Google (768-dim) |
| **Enterprise** | Azure | gpt-4o | Data residency | OpenAI direct |

### Provider Selector Implementation

```python
# ai/providers/provider_selector.py
from dataclasses import dataclass
from typing import Literal
from pilot_space.ai.config import AIConfig


@dataclass
class SelectedProvider:
    """Result of provider selection."""
    provider: str
    model: str
    reason: str
    api_key: str
    fallback_provider: str | None = None
    fallback_model: str | None = None


class ProviderSelector:
    """Select optimal LLM provider based on task requirements.

    Implements DD-011: Provider routing rules.

    Key principles:
    - Route to best provider for task type
    - Consider latency requirements
    - Handle provider unavailability with fallbacks
    - Respect user provider preferences
    """

    # Complete routing table per DD-011
    ROUTING_TABLE: dict[str, tuple[str, str, str, str | None, str | None]] = {
        # (provider, model, reason, fallback_provider, fallback_model)

        # Code-intensive tasks → Claude
        "pr_review": (
            "anthropic", "claude-opus-4-5",
            "Best code understanding + MCP tools",
            None, None  # No fallback - requires MCP tools
        ),
        "task_decomposition": (
            "anthropic", "claude-opus-4-5",
            "Strong multi-step reasoning + MCP tools",
            None, None
        ),
        "ai_context": (
            "anthropic", "claude-opus-4-5",
            "Multi-turn conversation + tool use",
            None, None
        ),
        "issue_enhancement": (
            "anthropic", "claude-sonnet-4",
            "Balanced speed and quality",
            "anthropic", "claude-3-5-haiku-20241022"
        ),
        "doc_generation": (
            "anthropic", "claude-sonnet-4",
            "Good prose generation",
            "google", "gemini-2.0-pro"
        ),
        "diagram_generation": (
            "anthropic", "claude-sonnet-4",
            "Structured DSL output",
            "google", "gemini-2.0-pro"
        ),

        # Latency-sensitive tasks → Gemini Flash
        "ghost_text": (
            "google", "gemini-2.0-flash",
            "Lowest latency for real-time suggestions",
            "anthropic", "claude-3-5-haiku-20241022"
        ),
        "margin_annotation": (
            "google", "gemini-2.0-flash",
            "Fast annotation generation",
            "anthropic", "claude-3-5-haiku-20241022"
        ),
        "notification_priority": (
            "google", "gemini-2.0-flash",
            "Quick priority scoring",
            "anthropic", "claude-3-5-haiku-20241022"
        ),
        "issue_detection": (
            "google", "gemini-2.0-flash",
            "Fast pattern detection",
            "anthropic", "claude-3-5-haiku-20241022"
        ),

        # Large context tasks → Gemini Pro
        "large_codebase": (
            "google", "gemini-2.0-pro",
            "2M token context for full codebase",
            "anthropic", "claude-opus-4-5"  # Will chunk
        ),

        # Embeddings → OpenAI
        "embeddings": (
            "openai", "text-embedding-3-large",
            "Superior 3072-dim vectors",
            "google", "gemini-embedding-001"  # 768-dim fallback
        ),
    }

    # Latency targets per task type (milliseconds)
    LATENCY_TARGETS = {
        "ghost_text": 2000,       # 2 seconds max
        "margin_annotation": 3000,
        "notification_priority": 1000,
        "issue_detection": 2000,
    }

    def __init__(self, config: AIConfig):
        self.config = config

    async def select(
        self,
        task_type: str,
        user_override: dict | None = None,
    ) -> SelectedProvider:
        """Select provider for task type.

        Args:
            task_type: Type of AI task
            user_override: User preference override (optional)

        Returns:
            SelectedProvider with provider, model, and fallback info
        """
        # Check user preference override first
        if user_override and task_type in user_override:
            override = user_override[task_type]
            return SelectedProvider(
                provider=override["provider"],
                model=override["model"],
                reason="User preference override",
                api_key=await self._get_api_key(override["provider"]),
            )

        # Use routing table
        if task_type in self.ROUTING_TABLE:
            provider, model, reason, fb_provider, fb_model = self.ROUTING_TABLE[task_type]

            # Check if primary provider is available
            primary_key = await self._get_api_key(provider)
            if primary_key:
                return SelectedProvider(
                    provider=provider,
                    model=model,
                    reason=reason,
                    api_key=primary_key,
                    fallback_provider=fb_provider,
                    fallback_model=fb_model,
                )

            # Try fallback if primary unavailable
            if fb_provider:
                fallback_key = await self._get_api_key(fb_provider)
                if fallback_key:
                    return SelectedProvider(
                        provider=fb_provider,
                        model=fb_model,
                        reason=f"Fallback: {provider} unavailable",
                        api_key=fallback_key,
                    )

        # Ultimate fallback to default
        return await self._get_default_provider()

    async def select_for_latency(
        self,
        task_type: str,
        target_latency_ms: int | None = None,
    ) -> SelectedProvider:
        """Select fastest provider meeting latency target.

        Args:
            task_type: Type of AI task
            target_latency_ms: Target latency (uses default if not specified)

        Returns:
            SelectedProvider optimized for latency
        """
        target = target_latency_ms or self.LATENCY_TARGETS.get(task_type, 5000)

        # Fast models ordered by latency
        fast_models = [
            ("google", "gemini-2.0-flash"),
            ("anthropic", "claude-3-5-haiku-20241022"),
            ("openai", "gpt-4o-mini"),
        ]

        for provider, model in fast_models:
            api_key = await self._get_api_key(provider)
            if api_key and await self._check_provider_health(provider):
                return SelectedProvider(
                    provider=provider,
                    model=model,
                    reason=f"Selected for {target}ms latency target",
                    api_key=api_key,
                )

        return await self._get_default_provider()

    async def _get_api_key(self, provider: str) -> str | None:
        """Get API key for provider from secure storage."""
        config = getattr(self.config, provider, None)
        if config and config.api_key:
            return config.api_key.get_secret_value()
        return None

    async def _check_provider_health(self, provider: str) -> bool:
        """Check if provider is healthy (not rate limited, reachable)."""
        # Check circuit breaker state
        # Check recent error rate
        # Ping provider health endpoint
        return True

    async def _get_default_provider(self) -> SelectedProvider:
        """Get default provider as ultimate fallback."""
        for provider in ["anthropic", "google", "openai"]:
            api_key = await self._get_api_key(provider)
            if api_key:
                config = getattr(self.config, provider)
                return SelectedProvider(
                    provider=provider,
                    model=config.default_model,
                    reason="Default fallback",
                    api_key=api_key,
                )

        raise ValueError("No AI providers configured. Please add API keys in workspace settings.")
```

### Automatic Failover

```python
# ai/infrastructure/failover.py
from pilot_space.ai.providers.provider_selector import ProviderSelector, SelectedProvider
from typing import AsyncIterator, TypeVar, Callable
import logging

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ProviderFailover:
    """Handle automatic provider failover on errors.

    Implements DD-011 failover strategy:
    - On provider error, automatically try fallback
    - Track error rates per provider
    - Open circuit breaker after repeated failures
    """

    def __init__(self, provider_selector: ProviderSelector):
        self.selector = provider_selector

    async def execute_with_failover(
        self,
        task_type: str,
        operation: Callable[[SelectedProvider], AsyncIterator[T]],
    ) -> AsyncIterator[T]:
        """Execute operation with automatic failover.

        Args:
            task_type: Type of AI task
            operation: Async generator function that takes SelectedProvider

        Yields:
            Results from operation
        """
        selected = await self.selector.select(task_type)

        try:
            async for result in operation(selected):
                yield result

        except Exception as e:
            logger.warning(
                f"Provider {selected.provider} failed for {task_type}: {e}"
            )

            # Try fallback if available
            if selected.fallback_provider:
                logger.info(
                    f"Failing over to {selected.fallback_provider} for {task_type}"
                )

                fallback = SelectedProvider(
                    provider=selected.fallback_provider,
                    model=selected.fallback_model,
                    reason=f"Failover from {selected.provider}",
                    api_key=await self.selector._get_api_key(selected.fallback_provider),
                )

                async for result in operation(fallback):
                    yield result
            else:
                # No fallback available, re-raise
                raise
```

---

## AI Confidence Display (DD-048)

Pilot Space displays AI confidence using contextual tags rather than raw percentages:

### Confidence Tags

| Tag | Range | Meaning | UI Behavior |
|-----|-------|---------|-------------|
| `Recommended` | ≥80% | Best option based on analysis | Prominent display, one-click accept |
| `Default` | 60-79% | Standard choice for context | Visible suggestion, review recommended |
| `Current` | N/A | Matches existing codebase pattern | Informational badge |
| `Alternative` | <60% | Valid but less common option | Flagged for human attention |

### Implementation

```typescript
// components/ai/ConfidenceTags.tsx
import { Badge, Tooltip } from '@/components/ui';

interface ConfidenceTagProps {
  confidence: number;  // 0.0 - 1.0
  matchesPattern?: boolean;  // If matches existing codebase pattern
}

export function ConfidenceTag({ confidence, matchesPattern }: ConfidenceTagProps) {
  // Determine tag based on confidence level
  const getTag = () => {
    if (matchesPattern) {
      return { label: 'Current', variant: 'info', icon: '📋' };
    }
    if (confidence >= 0.8) {
      return { label: 'Recommended', variant: 'success', icon: '✨' };
    }
    if (confidence >= 0.6) {
      return { label: 'Default', variant: 'default', icon: '📌' };
    }
    return { label: 'Alternative', variant: 'warning', icon: '🔄' };
  };

  const tag = getTag();
  const percentage = Math.round(confidence * 100);

  return (
    <Tooltip content={`${percentage}% confidence`}>
      <Badge variant={tag.variant}>
        <span className="mr-1">{tag.icon}</span>
        {tag.label}
      </Badge>
    </Tooltip>
  );
}
```

---

## Table of Contents

1. [SDK Overview](#sdk-overview)
2. [API Selection Pattern](#api-selection-pattern)
3. [MCP Tool Architecture](#mcp-tool-architecture)
4. [Agent Implementation Patterns](#agent-implementation-patterns)
5. [Provider Configuration](#provider-configuration)
6. [Streaming Architecture](#streaming-architecture)
7. [Session Management](#session-management)
8. [Error Handling & Resilience](#error-handling--resilience)
9. [Cost Management](#cost-management)
10. [MVP Agent Catalog](#mvp-agent-catalog)
11. [Implementation Examples](#implementation-examples)
12. [Testing Strategy](#testing-strategy)

---

## SDK Overview

### Claude Agent SDK Core Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CLAUDE AGENT SDK ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         ENTRY POINTS                                    │ │
│  │                                                                         │ │
│  │   ┌─────────────────────────┐    ┌─────────────────────────────────┐  │ │
│  │   │        query()           │    │      ClaudeSDKClient             │  │ │
│  │   ├─────────────────────────┤    ├─────────────────────────────────┤  │ │
│  │   │ • One-off agentic tasks │    │ • Multi-turn conversations      │  │ │
│  │   │ • Async iterator        │    │ • Session continuity            │  │ │
│  │   │ • Auto tool execution   │    │ • Streaming responses           │  │ │
│  │   │ • Budget/turn limits    │    │ • Session resume                │  │ │
│  │   └─────────────────────────┘    └─────────────────────────────────┘  │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      CONFIGURATION (ClaudeAgentOptions)                 │ │
│  │                                                                         │ │
│  │  model: claude-opus-4-5        │  mcp_servers: {pilot_space: ...}      │ │
│  │  system_prompt: str            │  permission_mode: default|bypass      │ │
│  │  allowed_tools: [...]          │  max_budget_usd: 10.0                 │ │
│  │  max_turns: 20                 │  resume: session_id (optional)        │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         MESSAGE TYPES                                   │ │
│  │                                                                         │ │
│  │   AssistantMessage    │   ToolUseBlock      │   ResultMessage          │ │
│  │   ├─ TextBlock        │   ├─ tool_name      │   ├─ session_id          │ │
│  │   ├─ ToolUseBlock     │   ├─ tool_input     │   ├─ total_cost_usd      │ │
│  │   └─ content[]        │   └─ tool_id        │   ├─ duration_ms         │ │
│  │                       │                      │   └─ turns_used          │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         MCP TOOL INTERFACE                              │ │
│  │                                                                         │ │
│  │  @tool decorator      │   create_sdk_mcp_server()   │   Tool Result    │ │
│  │  ├─ name              │   ├─ name                    │   ├─ content[]   │ │
│  │  ├─ description       │   ├─ version                 │   └─ is_error    │ │
│  │  └─ parameters        │   └─ tools[]                 │                   │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### SDK Imports

```python
from claude_agent_sdk import (
    # Entry Points
    query,                    # One-off agentic tasks
    ClaudeSDKClient,          # Multi-turn conversations

    # Configuration
    ClaudeAgentOptions,       # Agent configuration

    # Tool Definition
    tool,                     # Decorator for MCP tools
    create_sdk_mcp_server,    # Create MCP server from tools

    # Message Types
    AssistantMessage,         # Agent text/tool responses
    TextBlock,                # Text content block
    ToolUseBlock,             # Tool invocation block
    ResultMessage,            # Final result with metadata
)
from claude_agent_sdk.types import McpSdkServerConfig
```

---

## API Selection Pattern

### Decision Matrix: `query()` vs `ClaudeSDKClient`

| Criterion | `query()` | `ClaudeSDKClient` |
|-----------|-----------|-------------------|
| **Task Type** | One-off, fire-and-forget | Multi-turn, interactive |
| **State** | Stateless | Maintains session |
| **Streaming** | Async iterator | Async context manager |
| **Use Cases** | PR review, doc gen, decomposition | AIContext chat, ghost text |
| **Session Resume** | No | Yes (via `resume` option) |
| **Complexity** | Lower | Higher |

### Task-to-API Mapping for MVP

| Agent | API | Rationale |
|-------|-----|-----------|
| **PRReviewAgent** | `query()` | Single analysis task, no follow-up |
| **TaskDecomposerAgent** | `query()` | One-shot decomposition |
| **DocGeneratorAgent** | `query()` | Stateless document generation |
| **DiagramGeneratorAgent** | `query()` | Single diagram per request |
| **IssueEnhancerAgent** | `query()` | One-shot enhancement |
| **GhostTextAgent** | `ClaudeSDKClient` | Real-time, may need context |
| **AIContextAgent** | `ClaudeSDKClient` | Multi-turn context building |
| **MarginAnnotationAgent** | `query()` | Independent annotations |
| **DuplicateDetectorAgent** | `query()` | Single search operation |

---

## MCP Tool Architecture

### Custom MCP Server for Pilot Space

Pilot Space implements a custom MCP server exposing database and integration tools to Claude Agent SDK.

```python
# ai/tools/mcp_server.py
from claude_agent_sdk import create_sdk_mcp_server, tool
from pilot_space.ai.tools.database_tools import (
    get_issue_context,
    get_note_content,
    create_note_annotation,
    search_codebase,
    get_project_context,
)
from pilot_space.ai.tools.github_tools import (
    get_pr_details,
    get_pr_diff,
    search_code_in_repo,
)
from pilot_space.ai.tools.search_tools import (
    semantic_search,
    find_similar_issues,
)


def create_pilot_space_mcp_server() -> McpSdkServerConfig:
    """Create MCP server with all Pilot Space tools.

    Tool Categories:
    1. Database Tools - Access Pilot Space entities
    2. GitHub Tools - Repository and PR operations
    3. Search Tools - Semantic and similarity search
    """
    return create_sdk_mcp_server(
        name="pilot-space",
        version="1.0.0",
        tools=[
            # Database Tools
            get_issue_context,
            get_note_content,
            create_note_annotation,
            search_codebase,
            get_project_context,

            # GitHub Tools
            get_pr_details,
            get_pr_diff,
            search_code_in_repo,

            # Search Tools
            semantic_search,
            find_similar_issues,
        ]
    )
```

### Tool Definitions

#### Database Tools

```python
# ai/tools/database_tools.py
from claude_agent_sdk import tool
from typing import Any
import json


@tool(
    name="get_issue_context",
    description="""Retrieve complete issue context including:
    - Issue metadata (title, description, state, priority)
    - Related notes with excerpts
    - Linked issues (blocks, relates, duplicates)
    - Activity history
    - Code references (if any)
    Use this to understand the full context of an issue before analysis.""",
    parameters={
        "issue_id": {
            "type": "string",
            "description": "UUID of the issue to retrieve"
        }
    }
)
async def get_issue_context(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch comprehensive issue context from database."""
    from pilot_space.container import Container

    container = Container()
    issue_repo = container.issue_repository()
    note_repo = container.note_repository()

    issue = await issue_repo.get_by_id(args["issue_id"])
    if not issue:
        return {
            "content": [{"type": "text", "text": f"Issue not found: {args['issue_id']}"}],
            "is_error": True
        }

    # Get related notes
    related_notes = await note_repo.find_by_linked_issue(issue.id)

    # Get linked issues
    linked_issues = await issue_repo.get_linked_issues(issue.id)

    context = {
        "issue": {
            "id": str(issue.id),
            "identifier": issue.identifier,
            "title": issue.title,
            "description": issue.description,
            "state": issue.state.name,
            "priority": issue.priority.value if issue.priority else None,
            "assignee_id": str(issue.assignee_id) if issue.assignee_id else None,
            "labels": [label.name for label in issue.labels],
            "created_at": issue.created_at.isoformat(),
        },
        "related_notes": [
            {
                "id": str(note.id),
                "title": note.title,
                "excerpt": note.content[:500] if note.content else None,
            }
            for note in related_notes
        ],
        "linked_issues": [
            {
                "id": str(link.id),
                "identifier": link.identifier,
                "title": link.title,
                "link_type": link.link_type,
            }
            for link in linked_issues
        ],
    }

    return {"content": [{"type": "text", "text": json.dumps(context, indent=2)}]}


@tool(
    name="get_note_content",
    description="""Retrieve complete note content with all blocks.
    Returns structured block data including:
    - Block type (paragraph, heading, code, etc.)
    - Block content
    - Block position
    Use for analyzing note structure and content.""",
    parameters={
        "note_id": {
            "type": "string",
            "description": "UUID of the note to retrieve"
        }
    }
)
async def get_note_content(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch note content including all blocks."""
    from pilot_space.container import Container

    container = Container()
    note_repo = container.note_repository()

    note = await note_repo.get_by_id(args["note_id"])
    if not note:
        return {
            "content": [{"type": "text", "text": f"Note not found: {args['note_id']}"}],
            "is_error": True
        }

    # Parse JSONB blocks (TipTap format)
    blocks = note.content_blocks if hasattr(note, 'content_blocks') else []

    content = {
        "note_id": str(note.id),
        "title": note.title,
        "blocks": blocks,
        "total_blocks": len(blocks),
        "project_id": str(note.project_id),
    }

    return {"content": [{"type": "text", "text": json.dumps(content, indent=2)}]}


@tool(
    name="create_note_annotation",
    description="""Create an AI-generated annotation for a specific note block.
    Annotations appear in the right margin of the note canvas.
    Types: suggestion, improvement, question, reference
    Confidence should reflect certainty (0.0-1.0).""",
    parameters={
        "note_id": {"type": "string", "description": "UUID of the parent note"},
        "block_id": {"type": "string", "description": "UUID of the target block"},
        "annotation_type": {
            "type": "string",
            "enum": ["suggestion", "improvement", "question", "reference"],
            "description": "Type of annotation"
        },
        "content": {"type": "string", "description": "Annotation text content"},
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "AI confidence score"
        }
    }
)
async def create_note_annotation(args: dict[str, Any]) -> dict[str, Any]:
    """Create NoteAnnotation entity in database."""
    from pilot_space.domain.entities.note import NoteAnnotation
    from pilot_space.container import Container

    container = Container()
    annotation_repo = container.annotation_repository()
    uow = container.uow()

    async with uow:
        annotation = NoteAnnotation.create(
            note_id=args["note_id"],
            block_id=args["block_id"],
            annotation_type=args["annotation_type"],
            content=args["content"],
            confidence=args["confidence"],
        )

        await annotation_repo.add(annotation)
        await uow.commit()

    return {
        "content": [{
            "type": "text",
            "text": f"Annotation created: {annotation.id} for block {args['block_id']}"
        }]
    }


@tool(
    name="search_codebase",
    description="""Search the linked repository codebase using semantic search.
    Returns code snippets ranked by relevance.
    Use to find implementation patterns, function definitions, or related code.""",
    parameters={
        "query": {"type": "string", "description": "Search query (natural language)"},
        "project_id": {"type": "string", "description": "UUID of the project"},
        "limit": {
            "type": "integer",
            "default": 10,
            "description": "Maximum results to return"
        }
    }
)
async def search_codebase(args: dict[str, Any]) -> dict[str, Any]:
    """Semantic search across indexed codebase."""
    from pilot_space.ai.rag.retriever import SemanticRetriever
    from pilot_space.container import Container

    container = Container()
    retriever = container.semantic_retriever()

    results = await retriever.search(
        query=args["query"],
        project_id=args["project_id"],
        limit=args.get("limit", 10),
        source_types=["code"],
    )

    formatted_results = [
        {
            "file_path": r.file_path,
            "chunk": r.content[:500],
            "score": r.similarity_score,
            "line_start": r.line_start,
            "line_end": r.line_end,
        }
        for r in results
    ]

    return {"content": [{"type": "text", "text": json.dumps(formatted_results, indent=2)}]}


@tool(
    name="get_project_context",
    description="""Get project-level context including:
    - Project settings and conventions
    - Label definitions
    - State workflow configuration
    - Team members and roles
    Use to understand project-specific rules and patterns.""",
    parameters={
        "project_id": {"type": "string", "description": "UUID of the project"}
    }
)
async def get_project_context(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch project configuration and conventions."""
    from pilot_space.container import Container

    container = Container()
    project_repo = container.project_repository()

    project = await project_repo.get_by_id(args["project_id"])
    if not project:
        return {
            "content": [{"type": "text", "text": f"Project not found: {args['project_id']}"}],
            "is_error": True
        }

    context = {
        "project": {
            "id": str(project.id),
            "name": project.name,
            "identifier": project.identifier,
            "description": project.description,
        },
        "labels": [
            {"name": label.name, "color": label.color}
            for label in project.labels
        ],
        "states": [
            {"name": state.name, "group": state.group}
            for state in project.states
        ],
        "conventions": project.conventions if hasattr(project, 'conventions') else {},
    }

    return {"content": [{"type": "text", "text": json.dumps(context, indent=2)}]}
```

#### GitHub Tools

```python
# ai/tools/github_tools.py
from claude_agent_sdk import tool
from typing import Any
import json


@tool(
    name="get_pr_details",
    description="""Get pull request details from GitHub including:
    - Title and description
    - Author and reviewers
    - Changed files summary
    - CI status
    Use before reviewing a PR to understand scope.""",
    parameters={
        "repo_full_name": {
            "type": "string",
            "description": "Repository in 'owner/repo' format"
        },
        "pr_number": {
            "type": "integer",
            "description": "Pull request number"
        }
    }
)
async def get_pr_details(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch PR metadata from GitHub."""
    from pilot_space.integrations.github.client import GitHubClient
    from pilot_space.container import Container

    container = Container()
    github = container.github_client()

    pr = await github.get_pull_request(
        repo=args["repo_full_name"],
        number=args["pr_number"]
    )

    return {"content": [{"type": "text", "text": json.dumps(pr, indent=2)}]}


@tool(
    name="get_pr_diff",
    description="""Get the full diff for a pull request.
    Returns unified diff format with file changes.
    Use for detailed code review analysis.""",
    parameters={
        "repo_full_name": {
            "type": "string",
            "description": "Repository in 'owner/repo' format"
        },
        "pr_number": {
            "type": "integer",
            "description": "Pull request number"
        }
    }
)
async def get_pr_diff(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch PR diff from GitHub."""
    from pilot_space.integrations.github.client import GitHubClient
    from pilot_space.container import Container

    container = Container()
    github = container.github_client()

    diff = await github.get_pull_request_diff(
        repo=args["repo_full_name"],
        number=args["pr_number"]
    )

    return {"content": [{"type": "text", "text": diff}]}


@tool(
    name="search_code_in_repo",
    description="""Search for code patterns in a GitHub repository.
    Uses GitHub code search API.
    Good for finding existing implementations or usage patterns.""",
    parameters={
        "repo_full_name": {
            "type": "string",
            "description": "Repository in 'owner/repo' format"
        },
        "query": {
            "type": "string",
            "description": "Code search query"
        },
        "language": {
            "type": "string",
            "description": "Filter by language (optional)"
        }
    }
)
async def search_code_in_repo(args: dict[str, Any]) -> dict[str, Any]:
    """Search code in GitHub repository."""
    from pilot_space.integrations.github.client import GitHubClient
    from pilot_space.container import Container

    container = Container()
    github = container.github_client()

    results = await github.search_code(
        repo=args["repo_full_name"],
        query=args["query"],
        language=args.get("language")
    )

    return {"content": [{"type": "text", "text": json.dumps(results, indent=2)}]}
```

#### Search Tools

```python
# ai/tools/search_tools.py
from claude_agent_sdk import tool
from typing import Any
import json


@tool(
    name="semantic_search",
    description="""Perform semantic search across all workspace content:
    - Notes and pages
    - Issues and comments
    - Code (if indexed)
    Returns relevance-ranked results with excerpts.""",
    parameters={
        "query": {
            "type": "string",
            "description": "Natural language search query"
        },
        "workspace_id": {
            "type": "string",
            "description": "UUID of the workspace"
        },
        "source_types": {
            "type": "array",
            "items": {"type": "string", "enum": ["note", "page", "issue", "code"]},
            "description": "Filter by content type (optional)"
        },
        "limit": {
            "type": "integer",
            "default": 10,
            "description": "Maximum results"
        }
    }
)
async def semantic_search(args: dict[str, Any]) -> dict[str, Any]:
    """Semantic search across workspace content."""
    from pilot_space.ai.rag.retriever import SemanticRetriever
    from pilot_space.container import Container

    container = Container()
    retriever = container.semantic_retriever()

    results = await retriever.search(
        query=args["query"],
        workspace_id=args["workspace_id"],
        source_types=args.get("source_types"),
        limit=args.get("limit", 10),
    )

    formatted = [
        {
            "content": r.content[:300],
            "source_type": r.source_type,
            "source_id": r.source_id,
            "score": r.similarity_score,
        }
        for r in results
    ]

    return {"content": [{"type": "text", "text": json.dumps(formatted, indent=2)}]}


@tool(
    name="find_similar_issues",
    description="""Find issues similar to a given issue or description.
    Uses embedding similarity via pgvector.
    Use for duplicate detection or finding related work.""",
    parameters={
        "query": {
            "type": "string",
            "description": "Issue title/description or search query"
        },
        "project_id": {
            "type": "string",
            "description": "UUID of the project to search within"
        },
        "exclude_issue_id": {
            "type": "string",
            "description": "Issue ID to exclude from results (optional)"
        },
        "threshold": {
            "type": "number",
            "default": 0.7,
            "description": "Minimum similarity score (0.0-1.0)"
        },
        "limit": {
            "type": "integer",
            "default": 5,
            "description": "Maximum results"
        }
    }
)
async def find_similar_issues(args: dict[str, Any]) -> dict[str, Any]:
    """Find similar issues using embedding similarity."""
    from pilot_space.ai.rag.retriever import SemanticRetriever
    from pilot_space.container import Container

    container = Container()
    retriever = container.semantic_retriever()

    results = await retriever.find_similar(
        query=args["query"],
        project_id=args["project_id"],
        entity_type="issue",
        exclude_id=args.get("exclude_issue_id"),
        threshold=args.get("threshold", 0.7),
        limit=args.get("limit", 5),
    )

    formatted = [
        {
            "issue_id": r.entity_id,
            "identifier": r.identifier,
            "title": r.title,
            "similarity": r.score,
        }
        for r in results
    ]

    return {"content": [{"type": "text", "text": json.dumps(formatted, indent=2)}]}
```

### Tool Permission Modes

```python
# Permission modes for Claude Agent SDK
PERMISSION_MODES = {
    # Default: SDK handles tool confirmation
    "default": "default",

    # Bypass: Auto-execute tools without confirmation
    # Use only for read-only tools
    "bypassPermissions": "bypassPermissions",
}

# Tool categorization by permission requirement
TOOL_PERMISSIONS = {
    # Read-only tools - can bypass permission
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
        "update_issue",
        "post_pr_comment",
    ],
}
```

---

## Agent Implementation Patterns

### Base Agent Class

```python
# ai/agents/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any
from dataclasses import dataclass
from pilot_space.ai.providers.provider_selector import ProviderSelector, ProviderConfig


@dataclass
class AgentResult:
    """Standardized agent result."""
    content: str
    metadata: dict[str, Any]
    cost_usd: float
    duration_ms: int
    model_used: str


class BaseAgent(ABC):
    """Abstract base class for all Pilot Space AI agents.

    Agents must implement:
    - execute(): Main execution method returning async iterator

    Agents should:
    - Use ProviderSelector for model selection
    - Track costs via CostTracker
    - Handle errors gracefully
    - Provide streaming output when possible
    """

    # Override in subclasses
    AGENT_NAME: str = "base"
    PROVIDER_PREFERENCE: list[str] = ["anthropic"]
    DEFAULT_MODEL: str = "claude-opus-4-5"
    MAX_BUDGET_USD: float = 10.0
    MAX_TURNS: int = 20

    def __init__(
        self,
        provider_selector: ProviderSelector,
        mcp_server: "McpSdkServerConfig",
        cost_tracker: "CostTracker",
    ):
        self.provider_selector = provider_selector
        self.mcp_server = mcp_server
        self.cost_tracker = cost_tracker

    @abstractmethod
    async def execute(self, **kwargs) -> AsyncIterator[str]:
        """Execute agent task with streaming output.

        Yields:
            Text chunks of agent output
        """
        pass

    def _build_options(
        self,
        system_prompt: str,
        allowed_tools: list[str] | None = None,
        model: str | None = None,
        max_budget_usd: float | None = None,
    ) -> "ClaudeAgentOptions":
        """Build ClaudeAgentOptions with defaults."""
        from claude_agent_sdk import ClaudeAgentOptions

        return ClaudeAgentOptions(
            model=model or self.DEFAULT_MODEL,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools or [],
            mcp_servers={"pilot_space": self.mcp_server},
            permission_mode="default",
            max_budget_usd=max_budget_usd or self.MAX_BUDGET_USD,
            max_turns=self.MAX_TURNS,
        )

    async def _track_result(
        self,
        result: "ResultMessage",
        user_id: str,
        workspace_id: str,
    ) -> None:
        """Track agent execution costs."""
        await self.cost_tracker.track(
            user_id=user_id,
            workspace_id=workspace_id,
            task_type=self.AGENT_NAME,
            provider="anthropic",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            duration_ms=result.duration_ms,
        )
```

### One-Shot Agent Pattern (Using `query()`)

```python
# ai/agents/pr_review_agent.py
from pilot_space.ai.agents.base import BaseAgent
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, ResultMessage
from typing import AsyncIterator


class PRReviewAgent(BaseAgent):
    """Unified AI PR Review agent.

    Implements DD-006: Architecture + Code + Security review in one pass.
    Uses query() for one-shot analysis.
    """

    AGENT_NAME = "pr_review"
    DEFAULT_MODEL = "claude-opus-4-5"
    MAX_BUDGET_USD = 20.0  # PR reviews can be expensive
    MAX_TURNS = 15

    SYSTEM_PROMPT = """You are an expert code reviewer analyzing pull requests.

Your review must cover:
1. **Architecture**: Layer boundaries, design patterns, dependency direction
2. **Security**: OWASP vulnerabilities, secrets, auth issues
3. **Code Quality**: Complexity, duplication, naming, test coverage
4. **Performance**: N+1 queries, blocking calls, resource leaks
5. **Documentation**: Missing docstrings, outdated comments

Format your review as Markdown with severity indicators:
- 🔴 Critical: Must fix before merge
- 🟡 Warning: Should fix, but not blocking
- 🔵 Info: Suggestions for improvement

For each issue, provide:
- Location (file:line)
- Description of the problem
- Suggested fix
- Link to relevant documentation or pattern

End with an overall recommendation: APPROVE, REQUEST_CHANGES, or COMMENT."""

    async def execute(
        self,
        pr_number: int,
        repo_full_name: str,
        project_id: str,
        user_id: str,
        workspace_id: str,
    ) -> AsyncIterator[str]:
        """Execute PR review with streaming output.

        Args:
            pr_number: GitHub PR number
            repo_full_name: Repository in 'owner/repo' format
            project_id: Pilot Space project UUID
            user_id: Requesting user UUID
            workspace_id: Workspace UUID

        Yields:
            Markdown chunks of review content
        """
        # Build prompt with PR context
        prompt = f"""Review Pull Request #{pr_number} in {repo_full_name}.

Use the available tools to:
1. Get PR details and diff
2. Search the codebase for related patterns
3. Check project conventions

Provide a comprehensive review covering all aspects."""

        options = self._build_options(
            system_prompt=self.SYSTEM_PROMPT,
            allowed_tools=[
                "mcp__pilot_space__get_pr_details",
                "mcp__pilot_space__get_pr_diff",
                "mcp__pilot_space__search_codebase",
                "mcp__pilot_space__get_project_context",
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
                yield f"\n\n---\n*Review Cost: ${message.total_cost_usd:.4f} | Duration: {message.duration_ms}ms*"
```

### Multi-Turn Agent Pattern (Using `ClaudeSDKClient`)

```python
# ai/agents/ai_context_agent.py
from pilot_space.ai.agents.base import BaseAgent
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import AssistantMessage, TextBlock, ResultMessage
from typing import AsyncIterator


class AIContextAgent(BaseAgent):
    """Build comprehensive AI context for issues.

    Uses ClaudeSDKClient for multi-turn context building:
    1. Analyze issue requirements
    2. Search related documentation
    3. Find relevant code
    4. Identify similar issues
    5. Generate implementation suggestions
    """

    AGENT_NAME = "ai_context"
    DEFAULT_MODEL = "claude-opus-4-5"
    MAX_BUDGET_USD = 10.0
    MAX_TURNS = 10

    SYSTEM_PROMPT = """You are an AI assistant helping developers understand issues.

Your task is to build comprehensive context by:
1. Analyzing the issue requirements and scope
2. Finding related documentation and notes
3. Identifying relevant code sections
4. Finding similar past issues
5. Suggesting implementation approaches

Always explain your reasoning and cite sources.
Format output as structured Markdown."""

    async def execute(
        self,
        issue_id: str,
        user_id: str,
        workspace_id: str,
        refresh: bool = False,
    ) -> AsyncIterator[str]:
        """Build AI context with multi-turn conversation.

        Args:
            issue_id: Issue UUID
            user_id: Requesting user UUID
            workspace_id: Workspace UUID
            refresh: Force regenerate context

        Yields:
            Progress updates and context chunks
        """
        options = self._build_options(
            system_prompt=self.SYSTEM_PROMPT,
            allowed_tools=[
                "mcp__pilot_space__get_issue_context",
                "mcp__pilot_space__get_note_content",
                "mcp__pilot_space__search_codebase",
                "mcp__pilot_space__semantic_search",
                "mcp__pilot_space__find_similar_issues",
            ],
        )

        async with ClaudeSDKClient(options=options) as client:
            # Turn 1: Analyze issue
            yield "📋 Analyzing issue...\n\n"
            await client.query(
                f"First, get the full context for issue {issue_id} and analyze "
                "its requirements, scope, and technical needs."
            )

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text

            # Turn 2: Find related docs
            yield "\n\n📚 Searching related documentation...\n\n"
            await client.query(
                "Based on your analysis, search for related documentation, "
                "notes, and pages that would help implement this issue."
            )

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text

            # Turn 3: Find code references
            yield "\n\n💻 Finding relevant code...\n\n"
            await client.query(
                "Search the codebase for files and functions relevant to this issue. "
                "Identify entry points and dependencies."
            )

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text

            # Turn 4: Check similar issues
            yield "\n\n🔍 Checking similar issues...\n\n"
            await client.query(
                "Find similar issues that have been resolved. "
                "Extract patterns and lessons learned."
            )

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text

            # Turn 5: Generate implementation guide
            yield "\n\n🛠️ Generating implementation guide...\n\n"
            await client.query(
                "Based on all the context gathered, provide:\n"
                "1. A summary of the approach\n"
                "2. Step-by-step implementation tasks\n"
                "3. Key files to modify\n"
                "4. Potential challenges\n"
                "5. Ready-to-use Claude Code prompts for each task"
            )

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            yield block.text

                if isinstance(message, ResultMessage):
                    await self._track_result(message, user_id, workspace_id)
                    yield f"\n\n---\n*Context Build Cost: ${message.total_cost_usd:.4f}*"
```

### Latency-Optimized Agent Pattern

```python
# ai/agents/ghost_text_agent.py
from pilot_space.ai.agents.base import BaseAgent
from pilot_space.ai.providers.provider_selector import ProviderSelector
from typing import AsyncIterator
import asyncio


class GhostTextAgent(BaseAgent):
    """Real-time ghost text suggestions.

    Optimized for <2s latency using Gemini Flash.
    Falls back to Claude Haiku if Gemini unavailable.
    """

    AGENT_NAME = "ghost_text"
    PROVIDER_PREFERENCE = ["google", "anthropic"]
    DEFAULT_MODEL = "gemini-2.0-flash"
    FALLBACK_MODEL = "claude-3-5-haiku-20241022"
    MAX_TOKENS = 150
    LATENCY_TARGET_MS = 2000

    SYSTEM_PROMPT = """You are a writing assistant providing inline text suggestions.

Rules:
- Continue the text naturally from where the user stopped
- Match the tone, style, and technical level
- Keep suggestions short (1-2 sentences max)
- If in a code block, provide valid code
- Never repeat what's already written
- Stop at natural boundaries (period, newline)"""

    async def execute(
        self,
        context: str,
        cursor_position: int,
        note_id: str,
        block_id: str,
    ) -> AsyncIterator[str]:
        """Generate ghost text with minimal latency.

        Args:
            context: Text before cursor (max 2000 chars)
            cursor_position: Position in current block
            note_id: Parent note UUID
            block_id: Current block UUID

        Yields:
            Character/word chunks for ghost text display
        """
        # Select fastest provider
        provider_config = await self.provider_selector.select_for_latency(
            task_type="ghost_text",
            target_latency_ms=self.LATENCY_TARGET_MS,
            preference_order=self.PROVIDER_PREFERENCE,
        )

        # Truncate context for speed
        truncated_context = context[-2000:] if len(context) > 2000 else context

        prompt = f"""Continue this text naturally:

{truncated_context}"""

        # Use provider-specific API for lowest latency
        if provider_config.provider == "google":
            async for chunk in self._gemini_stream(prompt, provider_config):
                yield chunk
        else:
            async for chunk in self._claude_stream(prompt, provider_config):
                yield chunk

    async def _gemini_stream(
        self,
        prompt: str,
        config: "ProviderConfig",
    ) -> AsyncIterator[str]:
        """Stream from Gemini for lowest latency."""
        from google import generativeai as genai

        model = genai.GenerativeModel(config.model)

        response = await model.generate_content_async(
            prompt,
            generation_config={
                "max_output_tokens": self.MAX_TOKENS,
                "temperature": 0.7,
            },
            stream=True,
        )

        accumulated = ""
        async for chunk in response:
            text = chunk.text
            accumulated += text
            yield text

            # Stop at natural boundaries
            if any(stop in accumulated for stop in [".", "!", "?", "\n"]):
                break

            if len(accumulated) > 100:
                break

    async def _claude_stream(
        self,
        prompt: str,
        config: "ProviderConfig",
    ) -> AsyncIterator[str]:
        """Stream from Claude as fallback."""
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()

        async with client.messages.stream(
            model=config.model,
            max_tokens=self.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            system=self.SYSTEM_PROMPT,
        ) as stream:
            accumulated = ""
            async for text in stream.text_stream:
                accumulated += text
                yield text

                if any(stop in accumulated for stop in [".", "!", "?", "\n"]):
                    break

                if len(accumulated) > 100:
                    break
```

---

## Provider Configuration

### Multi-Provider Setup

```python
# ai/config.py
from pydantic import BaseModel, Field, SecretStr
from typing import Literal


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""
    api_key: SecretStr | None = None
    endpoint: str | None = None  # For Azure
    enabled: bool = True
    default_model: str

    def is_configured(self) -> bool:
        """Check if provider has valid configuration."""
        return self.api_key is not None and self.enabled


class AIConfig(BaseModel):
    """Complete AI layer configuration (BYOK model)."""

    # Provider configurations
    anthropic: ProviderConfig = Field(
        default=ProviderConfig(default_model="claude-opus-4-5")
    )
    openai: ProviderConfig = Field(
        default=ProviderConfig(default_model="gpt-4o")
    )
    google: ProviderConfig = Field(
        default=ProviderConfig(default_model="gemini-2.0-pro")
    )
    azure: ProviderConfig = Field(
        default=ProviderConfig(default_model="gpt-4o", enabled=False)
    )

    # Default provider for unspecified tasks
    default_provider: Literal["anthropic", "openai", "google", "azure"] = "anthropic"

    # Cost controls
    max_cost_per_request_usd: float = 10.0
    max_cost_per_workspace_day_usd: float = 100.0

    # Rate limits
    max_requests_per_minute: int = 100
    max_tokens_per_minute: int = 100_000

    # Ghost text configuration
    ghost_text_debounce_ms: int = 500
    ghost_text_max_tokens: int = 150
    ghost_text_timeout_ms: int = 2000

    # PR review configuration
    pr_review_max_diff_lines: int = 5000
    pr_review_max_files: int = 50

    # RAG configuration
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_top_k: int = 10
```

### Provider Selection Logic

```python
# ai/providers/provider_selector.py
from dataclasses import dataclass
from pilot_space.ai.config import AIConfig


@dataclass
class SelectedProvider:
    """Result of provider selection."""
    provider: str
    model: str
    reason: str
    api_key: str


class ProviderSelector:
    """Select optimal LLM provider based on task and availability.

    Implements DD-002 (BYOK) and DD-011 (provider routing):
    - Anthropic: Code review, task decomposition, AI context
    - Google: Ghost text, margin annotations, large context
    - OpenAI: Embeddings
    """

    TASK_ROUTING = {
        # Code-intensive → Claude
        "pr_review": ("anthropic", "claude-opus-4-5", "Best code understanding"),
        "task_decomposition": ("anthropic", "claude-opus-4-5", "Strong reasoning"),
        "ai_context": ("anthropic", "claude-opus-4-5", "Multi-turn + tools"),
        "doc_generation": ("anthropic", "claude-sonnet-4", "Good prose"),
        "issue_enhancement": ("anthropic", "claude-sonnet-4", "Balanced"),
        "diagram_generation": ("anthropic", "claude-sonnet-4", "Structured output"),

        # Latency-sensitive → Gemini Flash
        "ghost_text": ("google", "gemini-2.0-flash", "Lowest latency"),
        "margin_annotation": ("google", "gemini-2.0-flash", "Fast suggestions"),
        "notification_priority": ("google", "gemini-2.0-flash", "Quick scoring"),

        # Large context → Gemini Pro
        "large_codebase": ("google", "gemini-2.0-pro", "2M context window"),

        # Embeddings → OpenAI
        "embeddings": ("openai", "text-embedding-3-large", "Superior vectors"),
    }

    def __init__(self, config: AIConfig):
        self.config = config

    async def select(
        self,
        task_type: str,
        user_override: dict | None = None,
    ) -> SelectedProvider:
        """Select provider for task type."""
        # Check user preference
        if user_override and task_type in user_override:
            return user_override[task_type]

        # Use routing table
        if task_type in self.TASK_ROUTING:
            provider, model, reason = self.TASK_ROUTING[task_type]
            config = getattr(self.config, provider)

            if config.is_configured():
                return SelectedProvider(
                    provider=provider,
                    model=model,
                    reason=reason,
                    api_key=config.api_key.get_secret_value(),
                )

        # Fallback to default
        return self._get_fallback()

    async def select_for_latency(
        self,
        task_type: str,
        target_latency_ms: int,
        preference_order: list[str],
    ) -> SelectedProvider:
        """Select fastest available provider."""
        fast_models = {
            "google": "gemini-2.0-flash",
            "anthropic": "claude-3-5-haiku-20241022",
            "openai": "gpt-4o-mini",
        }

        for provider in preference_order:
            config = getattr(self.config, provider)
            if config.is_configured() and await self._check_health(provider):
                return SelectedProvider(
                    provider=provider,
                    model=fast_models.get(provider, config.default_model),
                    reason=f"Selected for {target_latency_ms}ms latency",
                    api_key=config.api_key.get_secret_value(),
                )

        return self._get_fallback()

    async def _check_health(self, provider: str) -> bool:
        """Check if provider is healthy (not rate limited, reachable)."""
        # Implementation: ping provider, check circuit breaker
        return True

    def _get_fallback(self) -> SelectedProvider:
        """Get fallback provider."""
        config = getattr(self.config, self.config.default_provider)
        return SelectedProvider(
            provider=self.config.default_provider,
            model=config.default_model,
            reason="Default fallback",
            api_key=config.api_key.get_secret_value() if config.api_key else "",
        )
```

---

## Streaming Architecture

### SSE Endpoint Pattern

```python
# api/v1/routers/ai.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncIterator
import json

router = APIRouter(prefix="/ai", tags=["AI"])


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

        yield f"data: {json.dumps({'type': 'done'})}\n\n".encode()

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n".encode()


@router.post("/issues/{issue_id}/context")
async def stream_ai_context(
    issue_id: str,
    current_user: "User" = Depends(get_current_user),
    ai_context_agent: AIContextAgent = Depends(get_ai_context_agent),
):
    """Stream AI context building via SSE."""
    return StreamingResponse(
        create_sse_stream(
            ai_context_agent.execute(
                issue_id=issue_id,
                user_id=str(current_user.id),
                workspace_id=str(current_user.workspace_id),
            )
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/notes/{note_id}/ghost-text")
async def stream_ghost_text(
    note_id: str,
    context: str,
    cursor_position: int,
    block_id: str,
    current_user: "User" = Depends(get_current_user),
    ghost_text_agent: GhostTextAgent = Depends(get_ghost_text_agent),
):
    """Stream ghost text suggestions via SSE."""
    return StreamingResponse(
        create_sse_stream(
            ghost_text_agent.execute(
                context=context,
                cursor_position=cursor_position,
                note_id=note_id,
                block_id=block_id,
            ),
            event_type="ghost_text",
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/prs/{pr_number}/review")
async def stream_pr_review(
    pr_number: int,
    repo_full_name: str,
    project_id: str,
    current_user: "User" = Depends(get_current_user),
    pr_review_agent: PRReviewAgent = Depends(get_pr_review_agent),
):
    """Stream PR review via SSE."""
    return StreamingResponse(
        create_sse_stream(
            pr_review_agent.execute(
                pr_number=pr_number,
                repo_full_name=repo_full_name,
                project_id=project_id,
                user_id=str(current_user.id),
                workspace_id=str(current_user.workspace_id),
            ),
            event_type="review",
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

### Frontend SSE Consumer

```typescript
// services/ai-stream.ts
export interface SSEEvent {
  type: 'content' | 'ghost_text' | 'review' | 'done' | 'error';
  data?: string;
  message?: string;
}

export async function* streamAIResponse(
  url: string,
  options: RequestInit,
): AsyncGenerator<SSEEvent> {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Accept': 'text/event-stream',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

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
        const data = JSON.parse(line.slice(6));
        yield data as SSEEvent;

        if (data.type === 'done' || data.type === 'error') {
          return;
        }
      }
    }
  }
}

// Usage in React component
export function useAIStream(url: string, options: RequestInit) {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startStream = useCallback(async () => {
    setIsStreaming(true);
    setContent('');
    setError(null);

    try {
      for await (const event of streamAIResponse(url, options)) {
        if (event.type === 'error') {
          setError(event.message || 'Unknown error');
          break;
        }
        if (event.data) {
          setContent(prev => prev + event.data);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Stream failed');
    } finally {
      setIsStreaming(false);
    }
  }, [url, options]);

  return { content, isStreaming, error, startStream };
}
```

---

## Session Management

### Multi-Turn Session Handling

```python
# ai/session/session_manager.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
import uuid


@dataclass
class AISession:
    """Track multi-turn AI conversation state."""
    id: str
    user_id: str
    agent_type: str
    context: dict[str, Any] = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    total_cost_usd: float = 0.0

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() - self.last_activity > timedelta(minutes=timeout_minutes)


class SessionManager:
    """Manage AI conversation sessions.

    Sessions enable multi-turn conversations with context preservation.
    Used by AIContextAgent and other interactive agents.
    """

    def __init__(self, redis_client: "Redis"):
        self.redis = redis_client
        self.session_ttl_seconds = 1800  # 30 minutes

    async def create_session(
        self,
        user_id: str,
        agent_type: str,
        initial_context: dict | None = None,
    ) -> AISession:
        """Create new AI session."""
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
        data = await self.redis.get(f"ai_session:{session_id}")
        if not data:
            return None

        return AISession(**json.loads(data))

    async def update_session(
        self,
        session_id: str,
        message: dict | None = None,
        context_update: dict | None = None,
        cost_delta: float = 0.0,
    ) -> AISession | None:
        """Update session with new data."""
        session = await self.get_session(session_id)
        if not session:
            return None

        if message:
            session.messages.append(message)

        if context_update:
            session.context.update(context_update)

        session.total_cost_usd += cost_delta
        session.last_activity = datetime.utcnow()

        await self._store(session)
        return session

    async def end_session(self, session_id: str) -> None:
        """End and cleanup session."""
        await self.redis.delete(f"ai_session:{session_id}")

    async def _store(self, session: AISession) -> None:
        """Store session in Redis."""
        await self.redis.setex(
            f"ai_session:{session.id}",
            self.session_ttl_seconds,
            json.dumps(asdict(session), default=str),
        )
```

---

## Error Handling & Resilience

### Resilience Patterns

```python
# ai/infrastructure/resilience.py
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import AsyncIterator, TypeVar, Callable
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for provider resilience."""
    failures: int = 0
    last_failure: datetime | None = None
    state: str = "closed"  # closed, open, half-open

    FAILURE_THRESHOLD = 5
    RESET_TIMEOUT = timedelta(seconds=60)

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure = datetime.utcnow()
        if self.failures >= self.FAILURE_THRESHOLD:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failures} failures")

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if datetime.utcnow() - self.last_failure > self.RESET_TIMEOUT:
                self.state = "half-open"
                return True
            return False
        return True  # half-open


class ResilientExecutor:
    """Execute AI operations with retry, timeout, and circuit breaker."""

    def __init__(self):
        self.circuit_breakers: dict[str, CircuitBreakerState] = {}

    def _get_circuit_breaker(self, provider: str) -> CircuitBreakerState:
        if provider not in self.circuit_breakers:
            self.circuit_breakers[provider] = CircuitBreakerState()
        return self.circuit_breakers[provider]

    async def execute(
        self,
        provider: str,
        operation: Callable[[], AsyncIterator[T]],
        timeout_sec: int = 300,
        max_retries: int = 3,
    ) -> AsyncIterator[T]:
        """Execute with resilience patterns.

        Args:
            provider: Provider name for circuit breaker tracking
            operation: Async generator to execute
            timeout_sec: Timeout in seconds
            max_retries: Maximum retry attempts

        Yields:
            Results from operation

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            TimeoutError: If operation times out after retries
        """
        circuit_breaker = self._get_circuit_breaker(provider)

        if not circuit_breaker.can_attempt():
            raise CircuitBreakerOpenError(f"Circuit breaker open for: {provider}")

        last_error = None

        for attempt in range(max_retries):
            try:
                async with asyncio.timeout(timeout_sec):
                    async for item in operation():
                        yield item

                circuit_breaker.record_success()
                return

            except asyncio.TimeoutError as e:
                last_error = e
                circuit_breaker.record_failure()
                logger.warning(f"Timeout on attempt {attempt + 1} for {provider}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                last_error = e
                circuit_breaker.record_failure()
                logger.error(f"Error on attempt {attempt + 1} for {provider}: {e}")

                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise last_error or TimeoutError(f"All retries exhausted for {provider}")
```

---

## Cost Management

### Cost Tracking

```python
# ai/infrastructure/cost_tracker.py
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import uuid


@dataclass
class CostRecord:
    """Individual AI cost record."""
    id: str
    user_id: str
    workspace_id: str
    task_type: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    duration_ms: int
    created_at: datetime


class CostTracker:
    """Track and report AI costs per workspace/user.

    Pricing data current as of 2026-01.
    """

    PRICING_PER_MILLION = {
        "anthropic": {
            "claude-opus-4-5": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4": {"input": 3.0, "output": 15.0},
            "claude-3-5-haiku-20241022": {"input": 1.0, "output": 5.0},
        },
        "openai": {
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.6},
            "text-embedding-3-large": {"input": 0.13, "output": 0.0},
        },
        "google": {
            "gemini-2.0-pro": {"input": 1.25, "output": 5.0},
            "gemini-2.0-flash": {"input": 0.075, "output": 0.3},
        },
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost in USD."""
        pricing = self.PRICING_PER_MILLION.get(provider, {}).get(
            model, {"input": 0, "output": 0}
        )
        return (
            (input_tokens / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )

    async def track(
        self,
        user_id: str,
        workspace_id: str,
        task_type: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
    ) -> CostRecord:
        """Record AI usage."""
        cost_usd = self.calculate_cost(provider, model, input_tokens, output_tokens)

        record = CostRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            workspace_id=workspace_id,
            task_type=task_type,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=cost_usd,
            duration_ms=duration_ms,
            created_at=datetime.utcnow(),
        )

        # Persist to database
        await self._store(record)

        return record

    async def get_workspace_summary(
        self,
        workspace_id: str,
        days: int = 30,
    ) -> dict:
        """Get cost summary for workspace."""
        # Query aggregated costs
        # Implementation details...
        pass
```

---

## MVP Agent Catalog

### Complete Agent List for MVP

| Agent | User Story | API Pattern | Provider | MCP Tools | Trigger |
|-------|------------|-------------|----------|-----------|---------|
| **GhostTextAgent** | US-01 | Direct API | Gemini Flash | None | 500ms typing pause |
| **IssueExtractorAgent** | US-01 | `query()` | Claude | `get_note_content` | User action |
| **MarginAnnotationAgent** | US-01 | `query()` | Gemini Flash | `get_note_content` | Block focus + 1s |
| **IssueEnhancerAgent** | US-02 | `query()` | Claude | `get_project_context`, `find_similar_issues` | Issue create/edit |
| **DuplicateDetectorAgent** | US-02 | `query()` | Claude | `find_similar_issues` | Issue creation |
| **PRReviewAgent** | US-03 | `query()` | Claude Opus | `get_pr_diff`, `search_codebase` | PR webhook |
| **TaskDecomposerAgent** | US-07 | `query()` | Claude Opus | `get_issue_context`, `search_codebase` | User action |
| **DiagramGeneratorAgent** | US-08 | `query()` | Claude | `get_issue_context` | User action |
| **DocGeneratorAgent** | US-06 | `query()` | Claude | `search_codebase`, `semantic_search` | User action |
| **AIContextAgent** | US-12 | `ClaudeSDKClient` | Claude Opus | All tools | Issue view |
| **SemanticSearchAgent** | US-10 | Direct API | pgvector + Gemini | `semantic_search` | Search query |
| **AssigneeRecommenderAgent** | US-02 | `query()` | Claude Haiku | `get_issue_context`, `get_project_context` | Issue assignment |

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/ai/test_provider_selector.py
import pytest
from pilot_space.ai.providers.provider_selector import ProviderSelector
from pilot_space.ai.config import AIConfig, ProviderConfig


@pytest.fixture
def configured_selector():
    config = AIConfig(
        anthropic=ProviderConfig(
            api_key="test-anthropic-key",
            default_model="claude-opus-4-5",
        ),
        google=ProviderConfig(
            api_key="test-google-key",
            default_model="gemini-2.0-flash",
        ),
        openai=ProviderConfig(
            api_key="test-openai-key",
            default_model="text-embedding-3-large",
        ),
    )
    return ProviderSelector(config)


def test_pr_review_selects_anthropic(configured_selector):
    result = configured_selector.select("pr_review")
    assert result.provider == "anthropic"
    assert result.model == "claude-opus-4-5"


def test_ghost_text_selects_google(configured_selector):
    result = configured_selector.select("ghost_text")
    assert result.provider == "google"
    assert result.model == "gemini-2.0-flash"


def test_embeddings_selects_openai(configured_selector):
    result = configured_selector.select("embeddings")
    assert result.provider == "openai"
    assert result.model == "text-embedding-3-large"


def test_unknown_task_uses_fallback(configured_selector):
    result = configured_selector.select("unknown_task")
    assert result.provider == "anthropic"  # Default fallback
```

### Integration Tests

```python
# tests/integration/ai/test_pr_review_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from pilot_space.ai.agents.pr_review_agent import PRReviewAgent


@pytest.mark.asyncio
async def test_pr_review_streams_content():
    """Test that PR review agent streams review content."""
    mock_mcp_server = AsyncMock()
    mock_cost_tracker = AsyncMock()
    mock_provider_selector = AsyncMock()

    agent = PRReviewAgent(
        provider_selector=mock_provider_selector,
        mcp_server=mock_mcp_server,
        cost_tracker=mock_cost_tracker,
    )

    with patch('pilot_space.ai.agents.pr_review_agent.query') as mock_query:
        # Setup mock to yield test content
        async def mock_generator(*args, **kwargs):
            from claude_agent_sdk.types import AssistantMessage, TextBlock
            yield AssistantMessage(content=[TextBlock(text="## Review\n")])
            yield AssistantMessage(content=[TextBlock(text="LGTM!")])

        mock_query.return_value = mock_generator()

        chunks = []
        async for chunk in agent.execute(
            pr_number=123,
            repo_full_name="owner/repo",
            project_id="proj-123",
            user_id="user-123",
            workspace_id="ws-123",
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert "Review" in "".join(chunks)
```

### E2E Tests

```python
# tests/e2e/ai/test_ai_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ghost_text_endpoint(client: AsyncClient, auth_headers: dict):
    """Test ghost text SSE endpoint."""
    response = await client.post(
        "/api/v1/ai/notes/note-123/ghost-text",
        json={
            "context": "def calculate_total(",
            "cursor_position": 21,
            "block_id": "block-123",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"


@pytest.mark.asyncio
async def test_ai_context_endpoint(client: AsyncClient, auth_headers: dict):
    """Test AI context building SSE endpoint."""
    response = await client.post(
        "/api/v1/ai/issues/issue-123/context",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
```

---

## Related Documents

- [AI Layer Architecture](ai-layer.md) - Complete AI layer overview
- [Backend Architecture](backend-architecture.md) - FastAPI structure
- [Design Decisions](../DESIGN_DECISIONS.md) - DD-002, DD-003, DD-006, DD-011
- [AI Capabilities](../AI_CAPABILITIES.md) - Feature descriptions
- [MVP Specification](../../specs/001-pilot-space-mvp/spec.md) - Full requirements

---

## Appendix: Claude Agent SDK Quick Reference

### Imports

```python
from claude_agent_sdk import (
    query,                    # One-shot tasks
    ClaudeSDKClient,          # Multi-turn
    ClaudeAgentOptions,       # Configuration
    tool,                     # MCP tool decorator
    create_sdk_mcp_server,    # MCP server factory
)
from claude_agent_sdk.types import (
    AssistantMessage,         # Agent response
    TextBlock,                # Text content
    ToolUseBlock,             # Tool call
    ResultMessage,            # Final result
)
```

### Configuration Options

```python
ClaudeAgentOptions(
    model="claude-opus-4-5",           # Model selection
    system_prompt="...",                # System instructions
    allowed_tools=["tool1", "tool2"],   # Allowed tool names
    mcp_servers={"name": server},       # MCP server configs
    permission_mode="default",          # default | bypassPermissions
    max_budget_usd=10.0,               # Cost limit
    max_turns=20,                       # Turn limit
    resume="session-id",                # Resume session (ClaudeSDKClient)
)
```

### Tool Definition

```python
@tool(
    name="tool_name",
    description="Tool description",
    parameters={
        "param1": {"type": "string", "description": "..."},
        "param2": {"type": "integer", "default": 10},
    }
)
async def tool_name(args: dict) -> dict:
    return {
        "content": [{"type": "text", "text": "result"}],
        "is_error": False,  # Optional
    }
```
