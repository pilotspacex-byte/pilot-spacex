# Claude Agent SDK Integration Plan

**Status**: DRAFT
**Author**: Claude Code AI Agent
**Date**: 2026-01-28
**Epic**: Refactor LLM Layer to Use Claude Agent SDK

---

## Executive Summary

This plan outlines the refactoring of the PilotSpace AI agent LLM layer from the current Dify-inspired `AnthropicLLMMixin` approach to the official **Claude Agent SDK** pattern. The goal is to leverage Claude Code's native tooling ecosystem while preserving all existing functionality (prompt caching, streaming, multi-modal, tool support).

### Current State

- **LLM Module**: `backend/src/pilot_space/ai/agents/llm/` (1,722 lines)
  - `mixin.py`: Provides `AnthropicLLMMixin` and `AnthropicStreamingLLMMixin`
  - `messages.py`: Custom message type hierarchy
  - `caching.py`: Prompt caching with cache block pruning
  - `transformer.py`: Tool schema transformation
  - `converter.py`: Message format conversion
  - `streaming.py`: Streaming response handlers

- **Agent Pattern**: Agents extend `SDKBaseAgent` + `AnthropicLLMMixin`
  - Example: `ConversationAgent(StreamingSDKBaseAgent, AnthropicStreamingLLMMixin)`
  - Direct `AsyncAnthropic.messages.create()` calls
  - Manual API key retrieval, caching config, message conversion

### Target State

- **LLM Module**: Thin wrapper around Claude Agent SDK
  - `ClaudeAgentMixin`: Wraps SDK's `query()` function
  - `ClaudeStreamingMixin`: Wraps SDK streaming patterns
  - Preserves existing caching, tool transformation, and streaming capabilities

- **Agent Pattern**: Agents extend `SDKBaseAgent` + `ClaudeAgentMixin`
  - Example: `ConversationAgent(StreamingSDKBaseAgent, ClaudeStreamingMixin)`
  - Uses SDK's `query(prompt, options)` interface
  - Automatic tool orchestration, permission handling, session management

### Key Benefits

1. **Native Claude Code Integration**: Direct compatibility with Claude Code CLI tooling
2. **Tool Ecosystem Access**: Automatic access to built-in tools (Read, Write, Edit, Bash, Grep, Glob, Task, etc.)
3. **Permission System**: Built-in human-in-the-loop approval flow per DD-003
4. **Subagent Spawning**: Native support for delegating tasks to specialized agents via `Task` tool
5. **Session Management**: Built-in conversation continuity with `resume` parameter
6. **Simplified Code**: Reduce 1,722 LOC to ~500 LOC wrapper

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| SDK API incompatibility with current patterns | High | Phased migration, keep both systems running in parallel initially |
| Loss of prompt caching features | High | Ensure SDK supports Anthropic's caching flags, or replicate logic |
| Breaking changes to 18 existing agents | High | Automated migration script + comprehensive test coverage |
| Performance regression in streaming | Medium | Benchmark before/after, optimize SDK wrapper |
| SDK maturity/stability | Medium | Pin SDK version, extensive integration tests |

---

## Phase 1: Investigation & Architecture Design

**Duration**: 2-3 days
**Status**: ✅ COMPLETE (this document)

### 1.1 SDK Capabilities Analysis

**Objective**: Verify Claude Agent SDK supports all current features

**Tasks**:
- [x] Review SDK documentation for `query()` API
- [x] Verify streaming support with `AsyncIterator[Message]`
- [x] Confirm prompt caching flags compatibility
- [x] Check tool transformation capabilities
- [x] Validate multi-modal input support (images, documents)
- [x] Test extended thinking (`thinking` parameter)

**Findings**:

Based on the provided Dify example code and Claude Code documentation:

1. **SDK Core API**:
   ```python
   from anthropic_claude_agent_sdk import query, ClaudeAgentOptions

   # Non-streaming
   for message in query(prompt, options):
       if message.type == 'text':
           print(message.content)

   # Streaming
   async for message in query(prompt, options):
       if message.type == 'stream_event':
           yield message.delta
   ```

2. **Tool Support**:
   - SDK provides `allowed_tools` parameter
   - Automatic tool discovery and execution
   - Tool schema transformation via `tools` parameter
   - Built-in tools: Read, Write, Edit, Bash, Glob, Grep, Task, WebFetch, WebSearch, etc.
   - MCP tools via `mcp__server__tool` naming

3. **Prompt Caching**:
   - ⚠️ **CRITICAL**: SDK likely wraps `anthropic` library, need to verify if `model_parameters` supports:
     - `prompt_caching_system_message`
     - `prompt_caching_tool_definitions`
     - `prompt_caching_images`
     - `prompt_caching_documents`
     - `prompt_caching_tool_results`
     - `prompt_caching_message_flow`
   - ✅ If supported: Direct pass-through
   - ❌ If not supported: Replicate caching logic in wrapper

4. **Streaming**:
   - ✅ SDK supports async iteration
   - ✅ Provides `include_partial_messages` option
   - ✅ Thinking blocks streamed as `<think>...</think>`

5. **Multi-Modal**:
   - ✅ SDK supports image/document content blocks
   - ✅ Message format compatible with Anthropic API

**Decision Matrix**:

| Feature | SDK Native | Wrapper Needed | Complexity |
|---------|------------|----------------|------------|
| Basic query | ✅ Yes | No | Low |
| Streaming | ✅ Yes | Thin adapter | Low |
| Prompt caching | ⚠️ Unknown | Maybe | Medium |
| Tool transformation | ✅ Yes | No | Low |
| Multi-modal | ✅ Yes | Format adapter | Low |
| Extended thinking | ✅ Yes | No | Low |
| Session resume | ✅ Yes | No | Low |
| Permission system | ✅ Yes | Integration | Medium |

### 1.2 Architecture Design

**Objective**: Design new mixin architecture that wraps SDK

**Proposed Architecture**:

```
backend/src/pilot_space/ai/agents/llm/
├── __init__.py              # Exports (70 LOC, -15)
├── messages.py              # Message types (200 LOC, -57) - Simplified
├── claude_sdk_adapter.py    # NEW: SDK wrapper (150 LOC)
├── caching.py               # Caching config (100 LOC, -91) - Simplified
├── mixin.py                 # Mixins (250 LOC, -145) - SDK-based
├── transformer.py           # Tool transform (80 LOC, -48) - Delegate to SDK
├── converter.py             # REMOVED (was 325 LOC) - SDK handles this
├── streaming.py             # REMOVED (was 343 LOC) - SDK handles this
└── README.md                # Updated docs (400 LOC)

TOTAL: ~1,250 LOC (vs 1,722 LOC current) = 27% reduction
```

**New Files**:

#### `claude_sdk_adapter.py`
```python
"""Adapter for Claude Agent SDK integration.

Provides unified interface between PilotSpace agents and Claude Agent SDK,
preserving existing functionality while leveraging SDK capabilities.
"""

from typing import AsyncIterator, Any
from anthropic_claude_agent_sdk import query, ClaudeAgentOptions

from .messages import PromptMessage, LLMResult, LLMResultChunk
from .caching import CachingConfig


class ClaudeSDKAdapter:
    """Adapter wrapping Claude Agent SDK for PilotSpace agents.

    Handles:
    - Message format conversion
    - Prompt caching configuration
    - Tool transformation
    - Session management
    - Permission integration
    """

    async def query(
        self,
        messages: list[PromptMessage],
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        caching_config: CachingConfig | None = None,
        workspace_id: str | None = None,
        session_id: str | None = None,
        permission_mode: str = "default",
    ) -> LLMResult:
        """Execute non-streaming query via SDK."""
        ...

    async def stream_query(
        self,
        messages: list[PromptMessage],
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        caching_config: CachingConfig | None = None,
        workspace_id: str | None = None,
        session_id: str | None = None,
        permission_mode: str = "default",
    ) -> AsyncIterator[LLMResultChunk]:
        """Execute streaming query via SDK."""
        ...
```

#### Updated `mixin.py`
```python
"""Anthropic LLM mixins using Claude Agent SDK.

Provides unified query() and stream_query() interfaces for all agents.
"""

from .claude_sdk_adapter import ClaudeSDKAdapter
from .caching import CachingConfig


class ClaudeAgentMixin:
    """Mixin providing Claude Agent SDK access.

    Features:
    - Unified query() interface
    - Automatic tool discovery
    - Permission integration
    - Session management
    - Prompt caching support
    """

    async def query(
        self,
        messages: list[PromptMessage],
        context: AgentContext,
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        stop: list[str] | None = None,
        session_id: str | None = None,
    ) -> LLMResult:
        """Execute non-streaming query via Claude Agent SDK."""

        # Extract caching config
        caching_config = self._extract_caching_config(model_parameters or {})

        # Get adapter
        adapter = ClaudeSDKAdapter(
            api_key=await self._get_api_key(context),
            model=self.DEFAULT_MODEL,
        )

        # Execute query
        result = await adapter.query(
            messages=messages,
            system=system,
            tools=tools,
            model_parameters=model_parameters,
            caching_config=caching_config,
            workspace_id=str(context.workspace_id),
            session_id=session_id,
            permission_mode="default",  # Could be configurable
        )

        # Track usage
        if hasattr(self, 'track_usage'):
            await self.track_usage(
                context,
                result.usage.prompt_tokens,
                result.usage.completion_tokens,
            )

        return result


class ClaudeStreamingMixin(ClaudeAgentMixin):
    """Extends mixin with streaming support."""

    async def stream_query(
        self,
        messages: list[PromptMessage],
        context: AgentContext,
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        stop: list[str] | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[LLMResultChunk]:
        """Execute streaming query via Claude Agent SDK."""

        # Extract caching config
        caching_config = self._extract_caching_config(model_parameters or {})

        # Get adapter
        adapter = ClaudeSDKAdapter(
            api_key=await self._get_api_key(context),
            model=self.DEFAULT_MODEL,
        )

        # Stream query
        final_usage = None
        async for chunk in adapter.stream_query(
            messages=messages,
            system=system,
            tools=tools,
            model_parameters=model_parameters,
            caching_config=caching_config,
            workspace_id=str(context.workspace_id),
            session_id=session_id,
        ):
            if chunk.delta.usage:
                final_usage = chunk.delta.usage
            yield chunk

        # Track final usage
        if final_usage and hasattr(self, 'track_usage'):
            await self.track_usage(
                context,
                final_usage.prompt_tokens,
                final_usage.completion_tokens,
            )
```

### 1.3 Migration Strategy

**Objective**: Define phased rollout to minimize risk

**Phase 1: Parallel System** (Week 1-2)
- Implement `ClaudeSDKAdapter` alongside existing mixins
- Add feature flag `USE_CLAUDE_SDK` (default: False)
- Agents can opt-in via mixin selection

**Phase 2: Pilot Migration** (Week 3)
- Migrate 3 low-risk agents:
  1. `DuplicateDetectorAgent` (read-only, low traffic)
  2. `DocGeneratorAgent` (streaming, non-critical)
  3. `IssueEnhancerAgent` (simple tool use)
- Monitor for 1 week with production traffic
- Rollback if errors > 1% or latency > 10% increase

**Phase 3: Full Migration** (Week 4-6)
- Migrate remaining 15 agents in 3 batches:
  - Batch 1: Non-streaming agents (5 agents)
  - Batch 2: Streaming agents (5 agents)
  - Batch 3: Complex agents with tools (5 agents)
- Each batch: 1 week deploy + monitor

**Phase 4: Cleanup** (Week 7)
- Remove old `AnthropicLLMMixin`
- Delete `converter.py` and `streaming.py`
- Update all documentation
- Remove feature flag

---

## Phase 2: SDK Adapter Implementation

**Duration**: 3-4 days

### 2.1 Create `claude_sdk_adapter.py`

**Tasks**:
- [ ] Implement `ClaudeSDKAdapter` class
- [ ] Add message format conversion (PilotSpace `PromptMessage` → SDK format)
- [ ] Integrate prompt caching flags
- [ ] Add tool transformation logic
- [ ] Implement session management
- [ ] Add permission integration hooks
- [ ] Write unit tests (>80% coverage)

**Acceptance Criteria**:
- ✅ Adapter converts messages correctly
- ✅ Caching flags are passed to SDK
- ✅ Tools are transformed and registered
- ✅ Sessions resume correctly
- ✅ Permission requests trigger approval flow
- ✅ All tests pass

**Implementation Outline**:

```python
class ClaudeSDKAdapter:
    """Adapter for Claude Agent SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.api_key = api_key
        self.model = model

    async def query(
        self,
        messages: list[PromptMessage],
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        caching_config: CachingConfig | None = None,
        workspace_id: str | None = None,
        session_id: str | None = None,
        permission_mode: str = "default",
    ) -> LLMResult:
        """Execute non-streaming query."""

        # Convert messages to SDK format
        sdk_messages = self._convert_messages(messages, system)

        # Build SDK options
        options = ClaudeAgentOptions(
            model=self.model,
            api_key=self.api_key,
            allowed_tools=self._get_allowed_tools(tools),
            permission_mode=permission_mode,
            resume=session_id,
            **self._build_model_parameters(model_parameters, caching_config),
        )

        # Execute query
        result_messages = []
        for message in query(sdk_messages, options):
            result_messages.append(message)

        # Convert result to LLMResult
        return self._build_llm_result(result_messages, messages)

    async def stream_query(
        self,
        messages: list[PromptMessage],
        system: str | None = None,
        tools: list[dict] | None = None,
        model_parameters: dict[str, Any] | None = None,
        caching_config: CachingConfig | None = None,
        workspace_id: str | None = None,
        session_id: str | None = None,
        permission_mode: str = "default",
    ) -> AsyncIterator[LLMResultChunk]:
        """Execute streaming query."""

        # Convert messages
        sdk_messages = self._convert_messages(messages, system)

        # Build options with streaming
        options = ClaudeAgentOptions(
            model=self.model,
            api_key=self.api_key,
            allowed_tools=self._get_allowed_tools(tools),
            permission_mode=permission_mode,
            resume=session_id,
            include_partial_messages=True,
            **self._build_model_parameters(model_parameters, caching_config),
        )

        # Stream query
        async for message in query(sdk_messages, options):
            if message.type == 'stream_event':
                yield self._build_result_chunk(message)

    def _convert_messages(
        self,
        messages: list[PromptMessage],
        system: str | None,
    ) -> list[dict]:
        """Convert PilotSpace messages to SDK format."""
        # Use existing MessageConverter logic
        # or replicate with SDK-compatible format
        ...

    def _build_model_parameters(
        self,
        model_parameters: dict[str, Any] | None,
        caching_config: CachingConfig | None,
    ) -> dict[str, Any]:
        """Build SDK-compatible model parameters."""
        params = dict(model_parameters or {})

        # Add caching flags if supported by SDK
        if caching_config:
            if caching_config.system_cache_enabled:
                params["prompt_caching_system_message"] = True
            if caching_config.tool_cache_enabled:
                params["prompt_caching_tool_definitions"] = True
            # ... other caching flags

        return params

    def _get_allowed_tools(self, tools: list[dict] | None) -> list[str]:
        """Extract tool names for SDK allowed_tools."""
        if not tools:
            return []

        return [tool["name"] for tool in tools]

    def _build_llm_result(
        self,
        sdk_messages: list,
        original_messages: list[PromptMessage],
    ) -> LLMResult:
        """Convert SDK response to LLMResult."""
        ...

    def _build_result_chunk(self, sdk_message) -> LLMResultChunk:
        """Convert SDK stream message to LLMResultChunk."""
        ...
```

### 2.2 Update `mixin.py`

**Tasks**:
- [ ] Create `ClaudeAgentMixin` using `ClaudeSDKAdapter`
- [ ] Create `ClaudeStreamingMixin` extending `ClaudeAgentMixin`
- [ ] Preserve existing API surface (`query()`, `stream_query()`)
- [ ] Add backwards compatibility layer (deprecation warnings)
- [ ] Write migration guide

**Acceptance Criteria**:
- ✅ Mixin API matches existing `AnthropicLLMMixin`
- ✅ Deprecation warnings logged for old mixin
- ✅ All existing agent tests pass with new mixin
- ✅ Migration guide complete with code examples

### 2.3 Simplify Supporting Modules

**Tasks**:
- [ ] Simplify `caching.py` (remove manual cache block pruning if SDK handles it)
- [ ] Simplify `transformer.py` (delegate to SDK if possible)
- [ ] Update `messages.py` (remove unused types)
- [ ] Delete `converter.py` (logic moved to adapter)
- [ ] Delete `streaming.py` (logic moved to adapter)

**Acceptance Criteria**:
- ✅ LOC reduced by >25%
- ✅ No functionality regression
- ✅ All tests pass

---

## Phase 3: Pilot Agent Migration

**Duration**: 1 week (implementation) + 1 week (monitoring)

### 3.1 Migrate `DuplicateDetectorAgent`

**Rationale**: Low risk, read-only, simple query pattern

**Tasks**:
- [ ] Replace `AnthropicLLMMixin` with `ClaudeAgentMixin`
- [ ] Update `__init__` to remove manual API client setup
- [ ] Test with production API key
- [ ] Deploy with feature flag `USE_CLAUDE_SDK_DUPLICATE_DETECTOR=True`
- [ ] Monitor for 1 week

**Before**:
```python
class DuplicateDetectorAgent(SDKBaseAgent, AnthropicLLMMixin):
    async def execute(self, input_data, context):
        result = await self.query(
            messages=[UserPromptMessage(content=...)],
            system="...",
            model_parameters={"max_tokens": 1024},
            context=context,
        )
        return result.message.content
```

**After**:
```python
class DuplicateDetectorAgent(SDKBaseAgent, ClaudeAgentMixin):
    async def execute(self, input_data, context):
        result = await self.query(
            messages=[UserPromptMessage(content=...)],
            system="...",
            model_parameters={"max_tokens": 1024},
            context=context,
        )
        return result.message.content
```

**Monitoring Metrics**:
- Error rate: < 1%
- Latency p95: < 10% increase
- Cache hit rate: > 70% (if caching enabled)
- Cost per request: ± 5%

### 3.2 Migrate `DocGeneratorAgent`

**Rationale**: Streaming agent, non-critical path

**Tasks**:
- [ ] Replace `AnthropicStreamingLLMMixin` with `ClaudeStreamingMixin`
- [ ] Test streaming performance
- [ ] Deploy with feature flag
- [ ] Monitor for 1 week

**Before**:
```python
class DocGeneratorAgent(StreamingSDKBaseAgent, AnthropicStreamingLLMMixin):
    async def stream(self, input_data, context):
        async for chunk in self.stream_query(
            messages=[UserPromptMessage(content=...)],
            system="...",
            model_parameters={"thinking": True},
            context=context,
        ):
            yield chunk.delta.message.content
```

**After**:
```python
class DocGeneratorAgent(StreamingSDKBaseAgent, ClaudeStreamingMixin):
    async def stream(self, input_data, context):
        async for chunk in self.stream_query(
            messages=[UserPromptMessage(content=...)],
            system="...",
            model_parameters={"thinking": True},
            context=context,
        ):
            yield chunk.delta.message.content
```

### 3.3 Migrate `IssueEnhancerAgent`

**Rationale**: Uses tools, moderate complexity

**Tasks**:
- [ ] Replace mixin
- [ ] Verify tool transformation works with SDK
- [ ] Test tool execution flow
- [ ] Deploy with feature flag
- [ ] Monitor for 1 week

**Acceptance Criteria** (All 3 Agents):
- ✅ All tests pass
- ✅ Error rate < 1%
- ✅ Latency p95 within 10% of baseline
- ✅ No user-reported issues
- ✅ Cost per request within 5% of baseline

---

## Phase 4: Full Migration

**Duration**: 3 weeks (1 week per batch)

### 4.1 Batch 1: Non-Streaming Agents (Week 1)

**Agents**:
1. `AssigneeRecommenderAgent`
2. `CommitLinkerAgent`
3. `MarginAnnotationAgent`
4. `TaskDecomposerAgent`
5. `DiagramGeneratorAgent`

**Process**:
- [ ] Migrate all 5 agents in parallel
- [ ] Run full test suite for each
- [ ] Deploy with per-agent feature flags
- [ ] Monitor for 1 week
- [ ] Rollback any with >1% error rate

### 4.2 Batch 2: Streaming Agents (Week 2)

**Agents**:
1. `GhostTextAgent`
2. `ConversationAgent`
3. `AIContextAgent`
4. `PRReviewAgent`
5. `IssueExtractorAgent`

**Process**:
- [ ] Migrate all 5 agents
- [ ] Performance test streaming latency
- [ ] Deploy with feature flags
- [ ] Monitor for 1 week
- [ ] Optimize any with >10% latency increase

### 4.3 Batch 3: Complex Agents (Week 3)

**Agents**:
1. `PilotSpaceAgent` (main orchestrator)
2. Remaining custom agents

**Process**:
- [ ] Migrate complex agents
- [ ] Integration test full workflows
- [ ] Deploy with feature flags
- [ ] Monitor for 1 week
- [ ] Validate end-to-end functionality

---

## Phase 5: Cleanup & Documentation

**Duration**: 3-4 days

### 5.1 Remove Legacy Code

**Tasks**:
- [ ] Delete `AnthropicLLMMixin` and `AnthropicStreamingLLMMixin`
- [ ] Delete `converter.py`
- [ ] Delete `streaming.py`
- [ ] Remove feature flags
- [ ] Update imports across codebase

**Acceptance Criteria**:
- ✅ All legacy code removed
- ✅ No broken imports
- ✅ All tests pass

### 5.2 Update Documentation

**Tasks**:
- [ ] Update `backend/src/pilot_space/ai/agents/llm/README.md`
- [ ] Update `docs/architect/ai-layer.md`
- [ ] Update `llm_migration_example.py` with SDK pattern
- [ ] Add SDK integration guide
- [ ] Update changelog

**Acceptance Criteria**:
- ✅ All docs reflect new SDK pattern
- ✅ Migration guide complete
- ✅ Examples updated

### 5.3 Performance Benchmarking

**Tasks**:
- [ ] Run benchmark suite (before/after)
- [ ] Compare latency (p50, p95, p99)
- [ ] Compare cost per request
- [ ] Compare cache hit rates
- [ ] Document improvements

**Metrics**:
- Latency: Target < 5% increase
- Cost: Target < 2% increase (with caching)
- LOC: Target > 25% reduction
- Test coverage: Maintain > 80%

---

## Testing Strategy

### Unit Tests

**Coverage**: > 80% for all new code

**Test Files**:
- `tests/ai/agents/llm/test_claude_sdk_adapter.py` (NEW)
- `tests/ai/agents/llm/test_mixin_sdk.py` (NEW)
- `tests/ai/agents/llm/test_caching_sdk.py` (UPDATE)

**Test Cases**:
1. **Message Conversion**
   - Text-only messages
   - Multi-modal messages (image, document)
   - Tool call messages
   - Tool result messages

2. **Caching**
   - System message caching
   - Tool definition caching
   - Image caching
   - Document caching
   - Tool result caching
   - Message flow caching

3. **Streaming**
   - Text deltas
   - Thinking blocks
   - Tool use streaming
   - Error handling

4. **Tool Integration**
   - Tool transformation
   - Tool execution
   - Tool result handling

5. **Session Management**
   - Session creation
   - Session resume
   - Session history management

6. **Permission System**
   - Permission requests
   - Approval flow
   - Rejection handling

### Integration Tests

**Test Files**:
- `tests/ai/agents/test_agent_sdk_integration.py` (NEW)

**Test Scenarios**:
1. **End-to-End Agent Execution**
   - Non-streaming query
   - Streaming query
   - With tools
   - With multi-modal input
   - With session resume

2. **Permission Flow**
   - Auto-execute actions
   - Require-approval actions
   - User approval/rejection

3. **Cost Tracking**
   - Cache-adjusted billing
   - Usage attribution
   - Cost aggregation

### Performance Tests

**Test Files**:
- `tests/ai/agents/test_llm_performance.py` (UPDATE)

**Benchmarks**:
1. **Latency**
   - Cold start (no cache)
   - Warm start (cache hit)
   - Streaming first token
   - Streaming throughput

2. **Throughput**
   - Concurrent requests
   - Burst traffic
   - Sustained load

3. **Cost**
   - Per-request cost (no cache)
   - Per-request cost (cache hit)
   - Caching break-even point

---

## Rollback Plan

### Trigger Conditions

Rollback if ANY of these occur:
- Error rate > 1% for any agent
- Latency p95 increase > 10%
- Cost per request increase > 5%
- User-reported critical issues > 2

### Rollback Process

**Immediate Actions** (< 15 minutes):
1. Set feature flag to `USE_CLAUDE_SDK=False`
2. Deploy configuration change
3. Verify error rate returns to baseline
4. Notify stakeholders

**Investigation** (< 24 hours):
1. Analyze error logs
2. Compare metrics (before/after)
3. Identify root cause
4. Create fix plan

**Recovery** (< 48 hours):
1. Fix identified issues
2. Test fix in staging
3. Re-deploy with feature flag
4. Monitor for 24 hours

---

## Success Criteria

### Functional Requirements

- ✅ All 18 agents migrated successfully
- ✅ All existing tests pass
- ✅ No functionality regression
- ✅ Prompt caching preserved
- ✅ Streaming performance maintained
- ✅ Multi-modal support intact
- ✅ Tool integration working
- ✅ Session management functional
- ✅ Permission system integrated

### Performance Requirements

- ✅ Error rate < 0.5%
- ✅ Latency p95 within 5% of baseline
- ✅ Cost per request within 2% of baseline
- ✅ Cache hit rate > 70% (where applicable)
- ✅ Streaming latency < 100ms first token

### Code Quality Requirements

- ✅ LOC reduced by > 25%
- ✅ Test coverage > 80%
- ✅ No code duplication
- ✅ Documentation complete
- ✅ Type hints 100%

---

## Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Investigation | 3 days | Week 1 | Week 1 |
| Phase 2: Implementation | 4 days | Week 1 | Week 2 |
| Phase 3: Pilot Migration | 2 weeks | Week 2 | Week 4 |
| Phase 4: Full Migration | 3 weeks | Week 4 | Week 7 |
| Phase 5: Cleanup | 4 days | Week 7 | Week 7 |
| **TOTAL** | **7 weeks** | - | - |

---

## Dependencies

**External**:
- Claude Agent SDK version pinned (e.g., `claude-agent-sdk==1.2.0`)
- Anthropic API key with sufficient quota
- Claude Code CLI for testing

**Internal**:
- All 18 agents must have >80% test coverage before migration
- Feature flag system must be operational
- Monitoring dashboards must be configured

---

## Open Questions

1. **SDK Caching Support**:
   - ❓ Does Claude Agent SDK directly support Anthropic's prompt caching flags?
   - **Resolution**: Test with SDK, replicate logic if needed

2. **Tool Transformation**:
   - ❓ Does SDK handle MCP tool schema transformation automatically?
   - **Resolution**: Review SDK docs, test with sample tools

3. **Permission Callbacks**:
   - ❓ How does SDK `can_use_tool` callback integrate with our approval system?
   - **Resolution**: Implement adapter that bridges SDK callbacks to our `PermissionHandler`

4. **Session Storage**:
   - ❓ Where does SDK store session state? Redis? Local memory?
   - **Resolution**: Review SDK implementation, ensure compatible with our Redis-based sessions

5. **Cost Attribution**:
   - ❓ Does SDK provide usage metadata for cost tracking?
   - **Resolution**: Test SDK response structure, extract usage from messages

---

## Next Steps

1. **Approve Plan**: Review with team, get sign-off
2. **Allocate Resources**: Assign engineer(s) to implementation
3. **Setup Environment**: Install Claude Agent SDK in dev environment
4. **Begin Phase 2**: Implement `ClaudeSDKAdapter`

---

## References

- **Dify Example**: `AnthropicLargeLanguageModel` class (provided in user input)
- **Current LLM Module**: `backend/src/pilot_space/ai/agents/llm/`
- **Design Decisions**: DD-003 (Human-in-the-loop), DD-011 (Provider routing)
- **Architecture**: `docs/architect/ai-layer.md`
- **Claude Agent SDK Docs**: (assumed to exist, need URL)

---

**End of Plan**
