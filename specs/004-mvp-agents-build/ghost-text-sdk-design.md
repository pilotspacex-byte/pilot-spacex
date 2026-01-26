# GhostTextAgent SDK Migration Design

## Overview

Migrate GhostTextAgent from direct Gemini API to Claude Agent SDK with Haiku model for unified architecture.

## Current Implementation (Gemini Direct)

```python
# Current: backend/src/pilot_space/ai/agents/ghost_text_agent.py
class GhostTextAgent(BaseAgent[GhostTextInput, GhostTextOutput]):
    task_type = TaskType.LATENCY_SENSITIVE  # Routes to Gemini

    async def _execute_impl(self, input_data, context):
        api_key = context.require_api_key(Provider.GEMINI)
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=GenerationConfig(max_output_tokens=50)
        )

        response = await model.generate_content_async(prompt, stream=True)
        # ... process response
```

## Target Implementation (Claude SDK)

```python
# Target: backend/src/pilot_space/ai/agents/ghost_text_agent.py
from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions, AssistantMessage, TextBlock

class GhostTextAgent(SDKBaseAgent):
    """Real-time ghost text suggestions using Claude SDK with Haiku.

    Uses claude-3-5-haiku for <2s latency target:
    - 50 token max output (short suggestions)
    - 2000ms timeout with graceful degradation
    - No MCP tools (stateless, fast execution)
    """

    AGENT_NAME = "ghost_text"
    DEFAULT_MODEL = "claude-3-5-haiku-20241022"
    MAX_OUTPUT_TOKENS = 50
    TIMEOUT_MS = 2000

    SYSTEM_PROMPT = """You are a writing assistant providing brief text completions.

RULES:
1. Complete the text naturally, continuing the user's thought
2. Keep suggestions SHORT (1-10 words maximum)
3. Match the user's writing style and tone
4. For code, complete the current statement/expression
5. Never add explanations or commentary
6. Return ONLY the completion text, nothing else

If the context is unclear, return an empty string."""

    SYSTEM_PROMPT_CODE = """You are a code completion assistant.

RULES:
1. Complete the code naturally at the cursor position
2. Keep completions SHORT (complete current line/statement only)
3. Match the existing code style exactly
4. Use proper syntax for the detected language
5. Return ONLY the code completion, no markdown or explanations

If context is insufficient, return an empty string."""

    async def execute(
        self,
        current_text: str,
        cursor_position: int,
        context: str | None = None,
        language: str | None = None,
        is_code: bool = False,
        user_id: str = "",
        workspace_id: str = "",
    ) -> AsyncIterator[str]:
        """Stream ghost text suggestions token by token.

        Args:
            current_text: Text before and after cursor
            cursor_position: Character position of cursor
            context: Optional surrounding context (file contents, note title)
            language: Programming language if is_code=True
            is_code: Whether this is code completion
            user_id: User making request
            workspace_id: Workspace for BYOK key lookup

        Yields:
            str: Suggestion tokens as they arrive

        Note:
            On timeout or error, yields empty string (graceful degradation)
        """
        # Build prompt
        text_before = current_text[:cursor_position]
        text_after = current_text[cursor_position:]

        prompt = self._build_prompt(
            text_before=text_before,
            text_after=text_after,
            context=context,
            language=language,
            is_code=is_code,
        )

        # Select system prompt
        system_prompt = self.SYSTEM_PROMPT_CODE if is_code else self.SYSTEM_PROMPT

        # Build SDK options (no MCP tools for latency)
        options = ClaudeAgentOptions(
            model=self.DEFAULT_MODEL,
            system_prompt=system_prompt,
            max_tokens=self.MAX_OUTPUT_TOKENS,
            timeout_ms=self.TIMEOUT_MS,
            # No MCP tools - pure text completion
            mcp_servers={},
            allowed_tools=[],
        )

        try:
            # Stream response via SDK
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Clean and yield suggestion
                            cleaned = self._clean_suggestion(block.text, text_before)
                            if cleaned:
                                yield cleaned

        except TimeoutError:
            # Graceful degradation on timeout
            yield ""
        except Exception as e:
            # Log error but don't fail - return empty suggestion
            logger.warning(f"Ghost text error: {e}", exc_info=True)
            yield ""

    def _build_prompt(
        self,
        text_before: str,
        text_after: str,
        context: str | None,
        language: str | None,
        is_code: bool,
    ) -> str:
        """Build completion prompt with context."""
        parts = []

        if context:
            parts.append(f"Context:\n{context}\n")

        if is_code and language:
            parts.append(f"Language: {language}\n")

        # Show cursor position with marker
        parts.append(f"Text before cursor:\n{text_before[-500:]}")  # Last 500 chars
        parts.append("\n[CURSOR]\n")

        if text_after:
            parts.append(f"Text after cursor:\n{text_after[:200]}")  # First 200 chars

        parts.append("\nProvide a brief completion (1-10 words):")

        return "\n".join(parts)

    def _clean_suggestion(self, text: str, text_before: str) -> str:
        """Clean suggestion text.

        - Remove quotes, prefixes like "Completion:", etc.
        - Truncate at word boundary if too long
        - Ensure doesn't repeat last word of text_before
        """
        cleaned = text.strip()

        # Remove common prefixes
        for prefix in ["Completion:", "Suggested:", "Continue:", "`", '"', "'"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        # Remove trailing quotes
        for suffix in ["`", '"', "'"]:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-1]

        # Don't repeat the last word
        last_word = text_before.split()[-1] if text_before.split() else ""
        if cleaned.lower().startswith(last_word.lower()):
            cleaned = cleaned[len(last_word):].strip()

        # Truncate at word boundary (max 50 chars)
        if len(cleaned) > 50:
            truncate_at = cleaned[:50].rfind(" ")
            if truncate_at > 0:
                cleaned = cleaned[:truncate_at]

        return cleaned
```

## SSE Endpoint

```python
# backend/src/pilot_space/api/v1/routers/ai.py

@router.post("/notes/{note_id}/ghost-text")
async def stream_ghost_text(
    note_id: str,
    request: GhostTextRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: SDKOrchestrator = Depends(get_sdk_orchestrator),
):
    """Stream ghost text suggestions via SSE.

    Returns:
        SSE stream with chunks: {"type": "content", "data": "suggestion text"}
        Final chunk: {"type": "done"}
    """
    async def generate():
        try:
            async for chunk in orchestrator.agents["ghost_text"].execute(
                current_text=request.current_text,
                cursor_position=request.cursor_position,
                context=request.context,
                language=request.language,
                is_code=request.is_code,
                user_id=str(current_user.id),
                workspace_id=str(current_user.workspace_id),
            ):
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

## Frontend Integration

```typescript
// frontend/src/stores/ghost-text-store.ts
import { makeAutoObservable, runInAction } from "mobx";
import { sseClient } from "@/lib/sse-client";

export class GhostTextStore {
  suggestion = "";
  isLoading = false;
  private abortController: AbortController | null = null;
  private debounceTimer: NodeJS.Timeout | null = null;

  constructor() {
    makeAutoObservable(this);
  }

  requestSuggestion = async (
    noteId: string,
    currentText: string,
    cursorPosition: number,
    context?: string,
    language?: string,
    isCode?: boolean,
  ) => {
    // Clear previous request
    this.cancel();

    // Debounce 500ms
    this.debounceTimer = setTimeout(async () => {
      runInAction(() => {
        this.isLoading = true;
        this.suggestion = "";
      });

      this.abortController = new AbortController();

      try {
        await sseClient.stream(
          `/api/v1/ai/notes/${noteId}/ghost-text`,
          {
            current_text: currentText,
            cursor_position: cursorPosition,
            context,
            language,
            is_code: isCode,
          },
          {
            onChunk: (data) => {
              if (data.type === "content") {
                runInAction(() => {
                  this.suggestion += data.data;
                });
              }
            },
            onDone: () => {
              runInAction(() => {
                this.isLoading = false;
              });
            },
            onError: (error) => {
              console.warn("Ghost text error:", error);
              runInAction(() => {
                this.isLoading = false;
                this.suggestion = "";
              });
            },
            signal: this.abortController.signal,
          }
        );
      } catch (error) {
        if (error.name !== "AbortError") {
          console.warn("Ghost text request failed:", error);
        }
        runInAction(() => {
          this.isLoading = false;
        });
      }
    }, 500);
  };

  acceptSuggestion = () => {
    const accepted = this.suggestion;
    this.suggestion = "";
    return accepted;
  };

  cancel = () => {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    this.suggestion = "";
    this.isLoading = false;
  };
}
```

```typescript
// frontend/src/components/editor/extensions/ghost-text-extension.ts
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

export const GhostTextExtension = Extension.create({
  name: "ghostText",

  addOptions() {
    return {
      store: null as GhostTextStore | null,
      enabled: true,
    };
  },

  addKeyboardShortcuts() {
    return {
      Tab: () => {
        const { store } = this.options;
        if (store?.suggestion) {
          // Accept suggestion
          const text = store.acceptSuggestion();
          this.editor.commands.insertContent(text);
          return true;
        }
        return false;
      },
      Escape: () => {
        const { store } = this.options;
        if (store?.suggestion) {
          store.cancel();
          return true;
        }
        return false;
      },
    };
  },

  addProseMirrorPlugins() {
    const { store, enabled } = this.options;

    return [
      new Plugin({
        key: new PluginKey("ghostText"),

        props: {
          decorations: (state) => {
            if (!enabled || !store?.suggestion) {
              return DecorationSet.empty;
            }

            const { from } = state.selection;

            // Create ghost text decoration at cursor
            const widget = Decoration.widget(from, () => {
              const span = document.createElement("span");
              span.className = "ghost-text-suggestion";
              span.textContent = store.suggestion;
              return span;
            });

            return DecorationSet.create(state.doc, [widget]);
          },
        },
      }),
    ];
  },
});
```

```css
/* frontend/src/styles/editor.css */
.ghost-text-suggestion {
  color: #9ca3af; /* gray-400 */
  opacity: 0.7;
  pointer-events: none;
  font-style: italic;
}
```

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| First token latency | <500ms | Time from request to first SSE chunk |
| Total latency (p95) | <2000ms | Time from request to done |
| Suggestion length | 1-10 words | Post-cleaning validation |
| Memory usage | <1MB per request | No MCP tools loaded |

## Test Cases

```python
# backend/tests/unit/ai/agents/test_ghost_text_agent.py

@pytest.mark.asyncio
async def test_ghost_text_prose_completion():
    """Test prose text completion."""
    agent = GhostTextAgent(...)

    chunks = []
    async for chunk in agent.execute(
        current_text="The quick brown fox",
        cursor_position=19,
        is_code=False,
    ):
        chunks.append(chunk)

    suggestion = "".join(chunks)
    assert len(suggestion) > 0
    assert len(suggestion) <= 50

@pytest.mark.asyncio
async def test_ghost_text_code_completion():
    """Test code completion."""
    agent = GhostTextAgent(...)

    chunks = []
    async for chunk in agent.execute(
        current_text="def calculate_",
        cursor_position=14,
        language="python",
        is_code=True,
    ):
        chunks.append(chunk)

    suggestion = "".join(chunks)
    # Should complete function name
    assert "(" in suggestion or suggestion.isidentifier()

@pytest.mark.asyncio
async def test_ghost_text_timeout_graceful():
    """Test graceful degradation on timeout."""
    agent = GhostTextAgent(...)
    agent.TIMEOUT_MS = 1  # Force timeout

    chunks = []
    async for chunk in agent.execute(
        current_text="Test",
        cursor_position=4,
    ):
        chunks.append(chunk)

    # Should return empty, not raise
    assert "".join(chunks) == ""

@pytest.mark.asyncio
async def test_ghost_text_latency_p95():
    """Test latency meets <2s target."""
    agent = GhostTextAgent(...)

    latencies = []
    for _ in range(20):
        start = time.monotonic()
        async for _ in agent.execute(
            current_text="Hello world",
            cursor_position=11,
        ):
            pass
        latencies.append(time.monotonic() - start)

    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 2.0, f"P95 latency {p95}s exceeds 2s target"
```

## Migration Steps

1. **T044**: Create new `GhostTextAgent` class extending `SDKBaseAgent`
2. **T044a**: Implement streaming via SDK async iterator
3. **T044b**: Add timeout handling with empty string fallback
4. **T045**: Update prompts for 50-token concise format
5. **T046**: Create SSE endpoint with `StreamingResponse`
6. **T047**: Register in `SDKOrchestrator.agents`
7. **T048**: Unit tests for streaming behavior
8. **T049**: Performance tests for <2s p95 latency

## Rollback Plan

If Haiku latency doesn't meet targets:
1. Revert to Gemini Flash direct API (non-SDK path)
2. Keep SDK architecture for other agents
3. GhostTextAgent uses separate `_execute_gemini()` method

This maintains unified SDK architecture while allowing latency-critical path optimization.
