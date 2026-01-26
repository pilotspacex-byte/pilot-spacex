# Legacy Code Cleanup Manifest

**Generated**: 2026-01-25
**Purpose**: Track all legacy files to delete/archive during Claude Agent SDK migration

---

## Summary

| Category | Files | Lines (est.) | Action |
|----------|-------|--------------|--------|
| Agent Base Classes | 1 | 435 | DELETE |
| Agent Implementations | 10 | ~2,500 | REFACTOR/DELETE |
| Prompt Templates | 6 | ~600 | DELETE |
| Mock Provider | 1 | 323 | DELETE |
| Mock Generators | 10 | ~500 | DELETE |
| Orchestrator | 1 | 575 | DELETE |
| **Total** | **29** | **~4,933** | - |

---

## Section A: Files to DELETE (After Migration)

### A.1 Agent Base Class

| File | Lines | Reason | Task |
|------|-------|--------|------|
| `backend/src/pilot_space/ai/agents/base.py` | 435 | SDK provides agent framework | T249 |

**Contains (to be removed):**
- `BaseAgent[InputT, OutputT]` abstract class
- `AgentContext` dataclass (API keys, correlation ID)
- `AgentResult[OutputT]` dataclass
- `PROVIDER_ROUTING` dict
- `DEFAULT_MODELS` dict
- `TaskType` enum
- MockProvider integration

---

### A.2 Legacy Agent Implementations

| File | Lines | Provider | Task |
|------|-------|----------|------|
| `backend/src/pilot_space/ai/agents/ghost_text_agent.py` | ~200 | Gemini direct | T253 |

**Note**: Other agents are REFACTORED, not deleted. Only ghost_text uses Gemini which is completely replaced.

---

### A.3 Legacy Prompt Templates

| File | Lines | Replacement | Task |
|------|-------|-------------|------|
| `backend/src/pilot_space/ai/prompts/ghost_text.py` | ~80 | SDK tool schema | T266 |
| `backend/src/pilot_space/ai/prompts/margin_annotation.py` | ~100 | SDK tool schema | T267 |
| `backend/src/pilot_space/ai/prompts/issue_extraction.py` | ~120 | SDK tool schema | T268 |
| `backend/src/pilot_space/ai/prompts/issue_enhancement.py` | ~80 | SDK tool schema | T269 |
| `backend/src/pilot_space/ai/prompts/ai_context.py` | ~150 | SDK tool schema | T270 |
| `backend/src/pilot_space/ai/prompts/pr_review.py` | ~100 | SDK tool schema | T271 |

**Common Pattern Being Removed:**
```python
# OLD: String template approach
SYSTEM_PROMPT = """You are a helpful assistant..."""

def build_prompt(context: str, **kwargs) -> str:
    return SYSTEM_PROMPT.format(context=context, ...)
```

**Replaced By:**
```python
# NEW: SDK tool definition
GHOST_TEXT_TOOL = {
    "name": "ghost_text",
    "description": "Generate text completion suggestions",
    "input_schema": {
        "type": "object",
        "properties": {
            "context": {"type": "string"},
            "cursor_position": {"type": "integer"}
        }
    }
}
```

---

### A.4 Mock Provider System

| File | Lines | Reason | Task |
|------|-------|--------|------|
| `backend/src/pilot_space/ai/providers/mock.py` | 323 | SDK has test fixtures | T262 |

**Contains (to be removed):**
- `MockResponseRegistry` class (decorator-based registration)
- `MockProvider` singleton
- `MockCallRecord` for debugging
- Side-effect import pattern for generators

---

### A.5 Mock Generators

| File | Lines | Task |
|------|-------|------|
| `backend/src/pilot_space/ai/providers/mock_generators/__init__.py` | ~20 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/ghost_text.py` | ~50 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/margin_annotation.py` | ~50 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/issue_extraction.py` | ~60 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/issue_enhancer.py` | ~40 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/duplicate_detector.py` | ~40 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/pr_review.py` | ~80 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/ai_context.py` | ~60 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/conversation.py` | ~40 | T263 |
| `backend/src/pilot_space/ai/providers/mock_generators/commit_linker.py` | ~40 | T263 |

**Replaced By:**
```python
# NEW: SDK test fixtures in backend/tests/fixtures/ai/
@pytest.fixture
def mock_ghost_text_response():
    return SDKMessage(content="suggested completion")
```

---

### A.6 Legacy Orchestrator

| File | Lines | Reason | Task |
|------|-------|--------|------|
| `backend/src/pilot_space/ai/orchestrator.py` | 575 | Replaced by sdk_orchestrator.py | T257 |

**Contains (to be removed):**
- `RateLimiter` class (in-memory, replaced by Redis)
- `WorkspaceAIConfig` class (extract to separate file)
- `AIOrchestrator` class (replaced by SDKOrchestrator)
- `get_orchestrator()` singleton function
- Agent instantiation and routing logic

---

## Section B: Files to REFACTOR

### B.1 Agent Implementations (Remove Direct Provider Imports)

| File | Current Import | Task |
|------|----------------|------|
| `conversation_agent.py` | `import anthropic` | T273 |
| `issue_extractor_agent.py` | `import anthropic` | T274 |
| `margin_annotation_agent.py` | `import anthropic` | T275 |
| `issue_enhancer_agent.py` | `import anthropic` | T276 |
| `duplicate_detector_agent.py` | `import anthropic` | T277 |
| `pr_review_agent.py` | `import anthropic` | T278 |
| `ai_context_agent.py` | `import anthropic` | T279 |
| `commit_linker_agent.py` | `import anthropic` | T280 |
| `assignee_recommender_agent.py` | `import anthropic` | T281 |

**Before:**
```python
import anthropic
from anthropic import AsyncAnthropic

class ConversationAgent(BaseAgent[ConversationInput, ConversationOutput]):
    async def _execute_impl(self, input_data, context):
        client = AsyncAnthropic(api_key=context.api_keys["anthropic"])
        response = await client.messages.create(...)
```

**After:**
```python
from claude_agent_sdk import query, ClaudeSDKClient
from pilot_space.ai.agents.sdk_base import SDKBaseAgent

class ConversationAgent(SDKBaseAgent):
    async def execute(self, **kwargs):
        async with ClaudeSDKClient(options=self.options) as client:
            response = await client.query(...)
```

---

### B.2 Telemetry Updates

| File | Changes | Task |
|------|---------|------|
| `backend/src/pilot_space/ai/telemetry.py` | Update enums, pricing | T287-T290 |

**Updates Required:**
```python
# Remove from AIProvider enum:
GEMINI = "google"  # No longer used

# Update TOKEN_COSTS:
TOKEN_COSTS = {
    "anthropic": {
        "claude-opus-4-5": {"input": 15.0, "output": 75.0},  # NEW
        "claude-sonnet-4": {"input": 3.0, "output": 15.0},   # UPDATED
        "claude-3-5-haiku": {"input": 1.0, "output": 5.0},   # NEW
    },
    # Remove "google" section
}
```

---

### B.3 Infrastructure Updates

| File | Changes | Task |
|------|---------|------|
| `backend/src/pilot_space/ai/exceptions.py` | Add SDK exceptions | N/A (minor) |
| `backend/src/pilot_space/ai/circuit_breaker.py` | Update for SDK client | N/A (minor) |

---

## Section C: Files to KEEP (No Changes)

| File | Reason |
|------|--------|
| `backend/src/pilot_space/ai/degradation.py` | Generic fallback patterns |
| `backend/src/pilot_space/ai/utils/retry.py` | Generic retry logic |
| `backend/src/pilot_space/ai/utils/code_context_extractor.py` | Utility for PR review |
| `backend/src/pilot_space/infrastructure/cache/ai_cache.py` | Generic Redis caching |
| `backend/src/pilot_space/infrastructure/cache/redis.py` | Redis client |
| All frontend components | API contracts unchanged |

---

## Section D: New Files Created

### D.1 SDK Infrastructure

| File | Purpose | Task |
|------|---------|------|
| `backend/src/pilot_space/ai/sdk_orchestrator.py` | SDK client wrapper | T035 |
| `backend/src/pilot_space/ai/agents/sdk_base.py` | Agent base with telemetry | T034 |
| `backend/src/pilot_space/ai/infrastructure/key_storage.py` | Secure API key storage | T011 |
| `backend/src/pilot_space/ai/infrastructure/approval.py` | Human-in-the-loop | T012 |
| `backend/src/pilot_space/ai/infrastructure/cost_tracker.py` | Cost tracking | T013 |
| `backend/src/pilot_space/ai/session/session_manager.py` | Redis sessions | T014 |

### D.2 MCP Tools

| File | Purpose | Task |
|------|---------|------|
| `backend/src/pilot_space/ai/tools/mcp_server.py` | MCP server factory | T017 |
| `backend/src/pilot_space/ai/tools/database_tools.py` | DB access tools | T018-T024, T030-T031 |
| `backend/src/pilot_space/ai/tools/search_tools.py` | Search tools | T025-T026 |
| `backend/src/pilot_space/ai/tools/github_tools.py` | GitHub tools | T027-T029, T032 |

---

## Verification Checklist

After cleanup, these greps should return 0 results:

```bash
# No direct Gemini usage
grep -r "google.generativeai" backend/src/

# No old base agent imports
grep -r "from pilot_space.ai.agents.base import" backend/

# No old orchestrator imports
grep -r "from pilot_space.ai.orchestrator import" backend/

# No MockProvider usage (outside tests)
grep -r "MockProvider" backend/src/

# No direct anthropic imports in agents
grep -r "^import anthropic" backend/src/pilot_space/ai/agents/

# No PROVIDER_ROUTING usage
grep -r "PROVIDER_ROUTING" backend/src/
```

---

## Archive Structure

All deleted files should be archived before deletion:

```
backend/src/pilot_space/ai/_archive/
├── base.py.bak                    # Old BaseAgent
├── orchestrator.py.bak            # Old AIOrchestrator
├── ghost_text_agent.py.bak        # Old Gemini agent
├── mock.py.bak                    # Old MockProvider
├── mock_generators/               # All old generators
│   ├── ghost_text.py.bak
│   ├── margin_annotation.py.bak
│   └── ...
└── prompts/                       # Old string templates
    ├── ghost_text.py.bak
    ├── margin_annotation.py.bak
    └── ...
```

**Note**: Add `_archive/` to `.gitignore` or remove before production deployment.

---

## Rollback Plan

If SDK migration fails, rollback steps:

1. Restore from `_archive/` directory
2. Revert `container.py` to use old `AIOrchestrator`
3. Revert agent imports to use `base.py`
4. Revert telemetry pricing
5. Re-enable mock provider in agents

**Estimated Rollback Time**: 30 minutes (file restores + import updates)
