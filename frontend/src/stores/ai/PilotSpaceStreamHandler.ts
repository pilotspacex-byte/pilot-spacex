/**
 * PilotSpace Stream Handler - SSE event routing and message lifecycle management.
 *
 * Routes SSE events to specialized handlers:
 * - Tool call lifecycle → PilotSpaceToolCallHandler
 * - SSE connection/parsing → PilotSpaceSSEParser
 * - Message, thinking, text, and other events → handled inline
 *
 * @module stores/ai/PilotSpaceStreamHandler
 * @see specs/005-conversational-agent-arch/plan.md (T048)
 */
import { runInAction } from 'mobx';
import type { SSEEvent } from '@/lib/sse-client';
import type { ChatMessage, ContentBlock, MessageRole, ToolCall } from './types/conversation';
import type {
  MessageStartEvent,
  ContentBlockStartEvent,
  TextDeltaEvent,
  ThinkingDeltaEvent,
  ToolUseEvent,
  ToolResultEvent,
  TaskProgressEvent,
  ApprovalRequestEvent,
  AskUserQuestionEvent,
  ContentUpdateEvent,
  StructuredResultEvent,
  MessageStopEvent,
  BudgetWarningEvent,
  ToolAuditEvent,
  ErrorEvent,
  CitationEvent,
  MemoryUpdateEvent,
  ToolInputDeltaEvent,
  FocusBlockEvent,
} from './types/events';
import {
  isMessageStartEvent,
  isContentBlockStartEvent,
  isTextDeltaEvent,
  isThinkingDeltaEvent,
  isToolUseEvent,
  isToolResultEvent,
  isTaskProgressEvent,
  isApprovalRequestEvent,
  isAskUserQuestionEvent,
  isStructuredResultEvent,
  isMessageStopEvent,
  isBudgetWarningEvent,
  isToolAuditEvent,
  isErrorEvent,
  isCitationEvent,
  isMemoryUpdateEvent,
  isToolInputDeltaEvent,
  isContentUpdateEvent,
  isFocusBlockEvent,
} from './types/events';
import type { PilotSpaceStore } from './PilotSpaceStore';
import { PilotSpaceToolCallHandler } from './PilotSpaceToolCallHandler';
import { PilotSpaceSSEParser } from './PilotSpaceSSEParser';

/** Handles SSE event dispatch, stream parsing, and connection management. */
export class PilotSpaceStreamHandler {
  private toolCallHandler: PilotSpaceToolCallHandler;
  private sseParser: PilotSpaceSSEParser;

  /** Monotonic counter for thinking turns (incremented on each thinking content_block_start).
   *  Models like kimi-k2.5 reset blockIndex to 0 on each agentic turn, so we use our own
   *  counter to distinguish separate thinking blocks. */
  private _thinkingTurnIndex = -1;
  /** Flag to skip duplicate "summary" text blocks.
   *  Some models emit a content_block_start index:0 text after individual word deltas,
   *  containing the full text again. We detect and skip these duplicates. */
  private _skipDuplicateTextBlock = false;
  /** Flag-based block separator: set once in handleContentBlockStart when a new text
   *  block starts after existing content, consumed once in handleTextDelta. */
  private _needsBlockSeparator = false;
  /** Tracks text segments per content block for ordered rendering */
  private _textSegments: string[] = [];
  /** Tracks the sequence of content block types for ordered rendering */
  private _blockOrder: Array<'thinking' | 'text' | 'tool_use'> = [];

  constructor(private store: PilotSpaceStore) {
    this.toolCallHandler = new PilotSpaceToolCallHandler(store);
    this.sseParser = new PilotSpaceSSEParser(store, (event) => this.handleSSEEvent(event));
  }

  // ========================================
  // Stream Connection (delegates to PilotSpaceSSEParser)
  // ========================================

  /** Connect to a specific SSE stream URL (queue mode). */
  async connectToStream(streamUrl: string, _jobId?: string): Promise<void> {
    return this.sseParser.connectToStream(streamUrl);
  }

  /** Consume SSE events from a fetch Response stream (direct mode). */
  async consumeSSEStream(response: Response): Promise<void> {
    return this.sseParser.consumeSSEStream(response);
  }

  /** Parse SSE buffer into events. */
  parseSSEBuffer(buffer: string): SSEEvent[] {
    return this.sseParser.parseSSEBuffer(buffer);
  }

  /** Get Supabase auth headers and workspace context for authenticated requests. */
  async getAuthHeaders(): Promise<Record<string, string>> {
    return this.sseParser.getAuthHeaders();
  }

  /** Abort the active SSE client connection. */
  abortClient(): void {
    this.sseParser.abortClient();
  }

  /** Reset retry state. Call when starting a new stream. */
  resetRetryState(): void {
    this.sseParser.resetRetryState();
  }

  // ========================================
  // SSE Event Handlers (T048)
  // ========================================

  /**
   * Handle SSE event from backend.
   * Routes to specific handler based on event type.
   */
  handleSSEEvent(sseEvent: SSEEvent): void {
    runInAction(() => {
      // Cast to our typed event (SSEClient returns generic SSEEvent)
      const event = sseEvent as unknown as
        | MessageStartEvent
        | ContentBlockStartEvent
        | TextDeltaEvent
        | ThinkingDeltaEvent
        | ToolUseEvent
        | ToolResultEvent
        | TaskProgressEvent
        | ApprovalRequestEvent
        | AskUserQuestionEvent
        | ContentUpdateEvent
        | StructuredResultEvent
        | MessageStopEvent
        | BudgetWarningEvent
        | ToolAuditEvent
        | ErrorEvent
        | CitationEvent
        | MemoryUpdateEvent
        | ToolInputDeltaEvent
        | FocusBlockEvent;

      // Route to type-specific handler
      if (isMessageStartEvent(event)) {
        this.handleMessageStart(event);
      } else if (isContentBlockStartEvent(event)) {
        this.handleContentBlockStart(event);
      } else if (isThinkingDeltaEvent(event)) {
        this.handleThinkingDelta(event);
      } else if (isTextDeltaEvent(event)) {
        this.handleTextDelta(event);
      } else if (isToolUseEvent(event)) {
        this.toolCallHandler.handleToolUseStart(event);
      } else if (isToolResultEvent(event)) {
        this.toolCallHandler.handleToolResult(event);
      } else if (isTaskProgressEvent(event)) {
        this.handleTaskUpdate(event);
      } else if (isApprovalRequestEvent(event)) {
        this.handleApprovalRequired(event);
      } else if (isAskUserQuestionEvent(event)) {
        this.handleAskUserQuestion(event);
      } else if (isFocusBlockEvent(event)) {
        this.toolCallHandler.handleFocusBlock(event);
      } else if (isContentUpdateEvent(event)) {
        this.store.handleContentUpdate(event);
      } else if (isStructuredResultEvent(event)) {
        this.handleStructuredResult(event);
      } else if (isCitationEvent(event)) {
        this.handleCitation(event);
      } else if (isMemoryUpdateEvent(event)) {
        this.handleMemoryUpdate(event);
      } else if (isToolInputDeltaEvent(event)) {
        this.toolCallHandler.handleToolInputDelta(event);
      } else if (isMessageStopEvent(event)) {
        this.handleTextComplete(event);
      } else if (isBudgetWarningEvent(event)) {
        this.handleBudgetWarning(event);
      } else if (isToolAuditEvent(event)) {
        this.toolCallHandler.handleToolAudit(event);
      } else if (isErrorEvent(event)) {
        this.handleError(event);
      }
    });
  }

  /** Handle message_start — initializes new assistant message. */
  handleMessageStart(event: MessageStartEvent): void {
    const { messageId, sessionId } = event.data;

    // Update session ID
    this.store.setSessionId(sessionId);

    // Reset tool call handler state for new message
    this.toolCallHandler.resetState();

    // Reset local state
    this._thinkingTurnIndex = -1;
    this._skipDuplicateTextBlock = false;
    this._needsBlockSeparator = false;
    this._textSegments = [];
    this._blockOrder = [];

    // Initialize streaming state
    this.store.streamingState = {
      isStreaming: true,
      streamContent: '',
      currentMessageId: messageId,
      phase: 'message_start',
      thinkingContent: '',
      isThinking: false,
      thinkingStartedAt: null,
      activeToolName: null,
      interrupted: false,
      wordCount: 0,
    };
  }

  /** Finalize durationMs on the last thinking block if it has a startedAt but no durationMs. */
  private finalizeLastThinkingBlockDuration(): void {
    const blocks = this.store.streamingState.thinkingBlocks;
    if (!blocks || blocks.length === 0) return;
    const last = blocks[blocks.length - 1]!;
    if (last.startedAt && !last.durationMs) {
      last.durationMs = Date.now() - last.startedAt;
    }
  }

  /** Handle content_block_start — tracks block type for progressive rendering. */
  handleContentBlockStart(event: ContentBlockStartEvent): void {
    const { contentType, index, parentToolUseId } = event.data;

    // Track current block type and index for progressive rendering (G13)
    this.store.streamingState.currentBlockType = contentType;
    this.store.streamingState.currentBlockIndex = index;

    // Store parentToolUseId for subagent correlation (G12)
    this.toolCallHandler.setParentToolUseId(parentToolUseId ?? null);

    // Pre-signal phase transitions based on block type (G-01)
    if (contentType === 'thinking') {
      this.store.streamingState.phase = 'thinking';
      this.store.streamingState.isThinking = true;
      this._thinkingTurnIndex++;
      this._skipDuplicateTextBlock = false;
      this._blockOrder.push('thinking');
      this.syncBlockOrderToState();
      if (!this.store.streamingState.thinkingStartedAt) {
        this.store.streamingState.thinkingStartedAt = Date.now();
      }
    } else if (contentType === 'text') {
      // End thinking phase when text block starts (safety: also handled in handleTextDelta)
      if (this.store.streamingState.isThinking) {
        this.store.streamingState.isThinking = false;
        this.finalizeLastThinkingBlockDuration();
      }

      // Detect duplicate "summary" text blocks: models like kimi-k2.5 emit
      // a content_block_start index:0 text after word-by-word deltas, containing
      // the full text again. Skip these to avoid duplicate content.
      if (index === 0 && this.store.streamingState.streamContent.trim().length > 0) {
        this._skipDuplicateTextBlock = true;
      } else {
        this._skipDuplicateTextBlock = false;
        this._blockOrder.push('text');
        this._textSegments.push('');
        this.syncBlockOrderToState();
        // Set separator flag if existing content precedes this text block
        if (this.store.streamingState.streamContent.length > 0) {
          this._needsBlockSeparator = true;
        }
      }
      this.store.streamingState.phase = 'content';
    } else if (contentType === 'tool_use') {
      // End thinking phase when tool_use starts (thinking → tool_use without text in between)
      if (this.store.streamingState.isThinking) {
        this.store.streamingState.isThinking = false;
        this.finalizeLastThinkingBlockDuration();
      }
      // Track block index for tool_input_delta routing
      this.toolCallHandler.setLastToolUseBlockIndex(index);
      this._skipDuplicateTextBlock = false;
      this._blockOrder.push('tool_use');
      this.syncBlockOrderToState();
    }
  }

  /** Handle thinking_delta — appends streaming thinking chunks. */
  handleThinkingDelta(event: ThinkingDeltaEvent): void {
    const { delta, signature, redacted } = event.data;

    // Filter noise text (same pattern as handleTextDelta)
    if (this.isNoiseDelta(delta)) {
      return;
    }

    // Start thinking timer on first delta
    if (!this.store.streamingState.isThinking) {
      this.store.streamingState.isThinking = true;
      this.store.streamingState.thinkingStartedAt = Date.now();
    }

    // Backward-compatible: always accumulate into flat thinkingContent
    this.store.streamingState.thinkingContent += delta;
    this.store.streamingState.phase = 'thinking';

    // G-07: Accumulate per-block thinking entries for interleaved rendering.
    // Use _thinkingTurnIndex instead of raw blockIndex because some models
    // (e.g. kimi-k2.5) reset blockIndex to 0 on each agentic turn.
    const turnIndex = this._thinkingTurnIndex >= 0 ? this._thinkingTurnIndex : 0;
    if (!this.store.streamingState.thinkingBlocks) {
      this.store.streamingState.thinkingBlocks = [];
    }
    const existingIdx = this.store.streamingState.thinkingBlocks.findIndex(
      (b) => b.blockIndex === turnIndex
    );
    if (existingIdx >= 0) {
      // Immutable update: replace entry to create new object reference
      const existing = this.store.streamingState.thinkingBlocks[existingIdx]!;
      this.store.streamingState.thinkingBlocks[existingIdx] = {
        ...existing,
        content: existing.content + delta,
      };
    } else {
      this.store.streamingState.thinkingBlocks.push({
        content: delta,
        blockIndex: turnIndex,
        redacted,
        startedAt: Date.now(),
      });
    }
    // Create new array reference so React memo() on OrderedStreamingBlocks detects changes
    this.store.streamingState.thinkingBlocks = [...this.store.streamingState.thinkingBlocks];

    // Capture thinking block signature for multi-turn verification (G-06)
    if (signature) {
      this.store.streamingState.thinkingSignature = signature;
    }
  }

  /** Handle text_delta — appends streaming text content. */
  handleTextDelta(event: TextDeltaEvent): void {
    const { delta } = event.data;

    // Filter noise text produced by some models between thinking/tool blocks
    if (this.isNoiseDelta(delta)) {
      return;
    }

    // Skip duplicate "summary" text blocks (see _skipDuplicateTextBlock)
    if (this._skipDuplicateTextBlock) {
      return;
    }

    // End thinking phase when text starts arriving
    if (this.store.streamingState.isThinking) {
      this.store.streamingState.isThinking = false;
    }

    // Flag-based block separator: only fires once at the start of a new text block
    if (this._needsBlockSeparator) {
      this.store.streamingState.streamContent += '\n\n';
      this._needsBlockSeparator = false;
    }

    // Accumulate text delta
    this.store.streamingState.streamContent += delta;

    // Track per-segment text for ordered content blocks
    if (this._textSegments.length > 0) {
      this._textSegments[this._textSegments.length - 1] += delta;
      this.store.streamingState.textSegments = [...this._textSegments];
    }
    this.store.streamingState.phase = 'content';

    const words = delta.split(/\s+/).filter((w) => w.length > 0);
    this.store.streamingState.wordCount = (this.store.streamingState.wordCount ?? 0) + words.length;
  }

  /** Handle task_progress — updates long-running task state. */
  handleTaskUpdate(event: TaskProgressEvent): void {
    const {
      taskId,
      subject,
      status,
      progress,
      description,
      currentStep,
      totalSteps,
      estimatedSecondsRemaining,
      agentName,
      model,
    } = event.data;

    this.store.addTask(taskId, {
      subject,
      status,
      progress,
      description,
      currentStep,
      totalSteps,
      estimatedSecondsRemaining,
      agentName,
      model,
    });
  }

  /** Handle approval_request (DD-003) — adds pending approval to queue. */
  handleApprovalRequired(event: ApprovalRequestEvent): void {
    const {
      requestId,
      actionType,
      description,
      consequences,
      affectedEntities,
      urgency,
      proposedContent,
      expiresAt,
      confidenceTag,
    } = event.data;

    this.store.addApproval({
      requestId,
      actionType,
      description,
      consequences,
      affectedEntities,
      urgency,
      proposedContent,
      expiresAt: new Date(expiresAt),
      confidenceTag,
      createdAt: new Date(),
    });
  }

  /** Handle ask_user_question — sets pending question requiring user response. */
  handleAskUserQuestion(event: AskUserQuestionEvent): void {
    const { questionId, questions } = event.data;
    this.store.pendingQuestion = { questionId, questions };
  }

  /** Handle structured_result — stores pending for attachment on message_stop. */
  handleStructuredResult(event: StructuredResultEvent): void {
    const { schemaType, data } = event.data;
    this.store.setPendingStructuredResult({ schemaType, data });
  }

  /** Handle message_stop — finalizes message and adds to history. */
  handleTextComplete(event: MessageStopEvent): void {
    const { messageId, usage, costUsd } = event.data;

    // Finalize any in-progress thinking block duration
    this.finalizeLastThinkingBlockDuration();

    // Calculate thinking duration if thinking occurred
    const thinkingDurationMs = this.store.streamingState.thinkingStartedAt
      ? Date.now() - this.store.streamingState.thinkingStartedAt
      : undefined;

    // Consume buffered data from streaming phase (T63, T64)
    const toolCalls = this.store.consumePendingToolCalls();
    const citations = this.store.consumePendingCitations();

    // Resolve any tool calls still in 'pending' status (no tool_result received).
    // This happens with models that emit tool_use events without executing tools.
    if (toolCalls) {
      for (const tc of toolCalls) {
        if (tc.status === 'pending') {
          tc.status = 'completed';
        }
      }
    }

    // G-07: Collect interleaved thinking blocks if present
    const thinkingBlocks = this.store.streamingState.thinkingBlocks?.length
      ? [...this.store.streamingState.thinkingBlocks]
      : undefined;

    // Build ordered content blocks from tracked sequence
    const contentBlocks = this.buildContentBlocks(thinkingBlocks, toolCalls);

    // Create completed assistant message
    const assistantMessage: ChatMessage = {
      id: messageId,
      role: 'assistant' as MessageRole,
      content: this.store.streamingState.streamContent,
      timestamp: new Date(),
      thinkingContent: this.store.streamingState.thinkingContent || undefined,
      thinkingBlocks,
      contentBlocks: contentBlocks.length > 0 ? contentBlocks : undefined,
      thinkingDurationMs,
      thinkingSignature: this.store.streamingState.thinkingSignature,
      toolCalls,
      citations,
      structuredResult: this.store.consumePendingStructuredResult(),
      metadata: {
        tokenCount: usage?.totalTokens,
        costUsd,
      },
    };

    this.store.messages.push(assistantMessage);

    if (usage?.totalTokens) {
      this.store.sessionState.totalTokens =
        (this.store.sessionState.totalTokens ?? 0) + usage.totalTokens;
    }

    // Reset streaming state
    this.store.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
      thinkingContent: '',
      isThinking: false,
      thinkingStartedAt: null,
      activeToolName: null,
      interrupted: false,
      wordCount: 0,
    };
  }

  /** Handle budget_warning — surfaces warning to user via store error state. */
  handleBudgetWarning(event: BudgetWarningEvent): void {
    const { currentCostUsd, maxBudgetUsd, percentUsed, message } = event.data;
    this.store.error = `Budget warning (${percentUsed}%): ${message} ($${currentCostUsd.toFixed(4)} / $${maxBudgetUsd.toFixed(2)})`;

    this.store.sessionState.totalTokens = Math.round((percentUsed / 100) * 8000);
  }

  /**
   * Handle error event.
   * Implements exponential backoff retry for retryable errors (max 3 attempts).
   * Non-retryable errors reset streaming state immediately.
   */
  handleError(event: ErrorEvent): void {
    const { errorCode, message, retryable, retryAfter } = event.data;

    if (retryable) {
      const willRetry = this.sseParser.handleRetryableError(errorCode, message, retryAfter);
      if (willRetry) return;
    }

    // Non-retryable or max retries exceeded
    this.store.error = `[${errorCode}] ${message}`;

    // Reset streaming state
    this.store.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    };
  }

  /** Handle citation event — buffer for attachment on message finalization (T64). */
  handleCitation(event: CitationEvent): void {
    const { citations } = event.data;
    this.store.addPendingCitations(citations);
  }

  /** Handle memory_update event — store for UI notification (T73). */
  handleMemoryUpdate(event: MemoryUpdateEvent): void {
    this.store.lastMemoryUpdate = event.data;
  }

  // ========================================
  // Private Helpers
  // ========================================

  /**
   * Sync internal block order + text segments to observable streaming state.
   * Creates new array references so MobX detects the change.
   */
  private syncBlockOrderToState(): void {
    this.store.streamingState.blockOrder = [...this._blockOrder];
    this.store.streamingState.textSegments = [...this._textSegments];
  }

  /**
   * Build ordered content blocks from the tracked block sequence.
   * Reconstructs the interleaved order of thinking/text/tool blocks
   * using _blockOrder + thinkingBlocks + _textSegments + toolCalls.
   */
  private buildContentBlocks(
    thinkingBlocks: import('./types/conversation').ThinkingBlockEntry[] | undefined,
    toolCalls: ToolCall[] | undefined
  ): ContentBlock[] {
    const blocks: ContentBlock[] = [];
    let thinkingIdx = 0;
    let textIdx = 0;
    let toolIdx = 0;

    for (const blockType of this._blockOrder) {
      if (blockType === 'thinking') {
        const tb = thinkingBlocks?.[thinkingIdx];
        if (tb) {
          blocks.push({
            type: 'thinking',
            blockIndex: tb.blockIndex,
            content: tb.content,
            redacted: tb.redacted,
            startedAt: tb.startedAt,
            durationMs: tb.durationMs,
          });
        }
        thinkingIdx++;
      } else if (blockType === 'text') {
        const text = this._textSegments[textIdx];
        if (text?.trim()) {
          blocks.push({ type: 'text', content: text });
        }
        textIdx++;
      } else if (blockType === 'tool_use') {
        const tc = toolCalls?.[toolIdx];
        if (tc) {
          blocks.push({ type: 'tool_call', toolCallId: tc.id });
        }
        toolIdx++;
      }
    }

    return blocks;
  }

  /**
   * Check if a delta is noise content produced by some models
   * between thinking/tool blocks (e.g., literal "(no content)").
   * Newline-only deltas (\n, \n\n) are NOT noise — they are critical
   * for markdown list formatting and paragraph breaks.
   */
  private isNoiseDelta(delta: string): boolean {
    if (delta.length === 0) return true;
    if (delta.trim() === '(no content)') return true;
    return false;
  }
}
