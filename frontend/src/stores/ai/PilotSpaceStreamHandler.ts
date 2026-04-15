/** PilotSpace Stream Handler - SSE event routing and message lifecycle management. */
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
  QuestionRequestEvent,
  ContentUpdateEvent,
  StructuredResultEvent,
  MessageStopEvent,
  BudgetWarningEvent,
  ToolAuditEvent,
  ErrorEvent,
  CitationEvent,
  MemoryUpdateEvent,
  MemoryUsedEvent,
  ToolInputDeltaEvent,
  FocusBlockEvent,
  SkillPreviewEvent,
  TestResultEvent,
  SkillSavedEvent,
  IssueBatchProposalEvent,
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
  isQuestionRequestEvent,
  isStructuredResultEvent,
  isMessageStopEvent,
  isBudgetWarningEvent,
  isToolAuditEvent,
  isErrorEvent,
  isCitationEvent,
  isMemoryUpdateEvent,
  isMemoryUsedEvent,
  isToolInputDeltaEvent,
  isContentUpdateEvent,
  isFocusBlockEvent,
  isSkillPreviewEvent,
  isTestResultEvent,
  isSkillSavedEvent,
  isIssueBatchProposalEvent,
} from './types/events';
import type { PilotSpaceStore } from './PilotSpaceStore';
import { PilotSpaceToolCallHandler } from './PilotSpaceToolCallHandler';
import { PilotSpaceSSEParser } from './PilotSpaceSSEParser';

/** Safety timeout (ms): synthesizes message_stop if it never arrives after question_request.
 *  PermissionResultDeny causes the SDK to end the stream quickly, so 5s is generous. */
const QUESTION_SAFETY_TIMEOUT_MS = 5000;

/** Handles SSE event dispatch, stream parsing, and connection management. */
export class PilotSpaceStreamHandler {
  private toolCallHandler: PilotSpaceToolCallHandler;
  private sseParser: PilotSpaceSSEParser;

  /** Monotonic thinking turn counter (some models reset blockIndex per turn). */
  private _thinkingTurnIndex = -1;
  /** Skip duplicate "summary" text blocks from models that re-emit full text. */
  private _skipDuplicateTextBlock = false;
  /** Flag: insert block separator at next text delta start. */
  private _needsBlockSeparator = false;
  private _textSegments: string[] = [];
  private _blockOrder: Array<'thinking' | 'text' | 'tool_use'> = [];
  /** Pending question data for merged wizard UI (supports multiple ask_user calls). */
  private _pendingQuestionDataList: Array<{
    questionId: string;
    questions: import('./types/events').AgentQuestion[];
  }> = [];
  /** Safety timeout handle: synthesizes message_stop if it never arrives after question_request */
  private _questionSafetyTimeout: ReturnType<typeof setTimeout> | null = null;

  constructor(private store: PilotSpaceStore) {
    this.toolCallHandler = new PilotSpaceToolCallHandler(store);
    this.sseParser = new PilotSpaceSSEParser(store, (event) => this.handleSSEEvent(event));
  }

  // --- Stream Connection (delegates to PilotSpaceSSEParser) ---

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

  // --- SSE Event Handlers (T048) ---

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
        | QuestionRequestEvent
        | ContentUpdateEvent
        | StructuredResultEvent
        | MessageStopEvent
        | BudgetWarningEvent
        | ToolAuditEvent
        | ErrorEvent
        | CitationEvent
        | MemoryUpdateEvent
        | MemoryUsedEvent
        | ToolInputDeltaEvent
        | FocusBlockEvent
        | SkillPreviewEvent
        | TestResultEvent
        | SkillSavedEvent
        | IssueBatchProposalEvent;

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
      } else if (isQuestionRequestEvent(event)) {
        this.handleQuestionRequest(event);
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
      } else if (isMemoryUsedEvent(event)) {
        this.handleMemoryUsed(event);
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
      } else if (isSkillPreviewEvent(event)) {
        this.store.handleSkillPreview(event);
      } else if (isTestResultEvent(event)) {
        this.store.handleTestResult(event);
      } else if (isSkillSavedEvent(event)) {
        this.store.handleSkillSaved(event);
      } else if (isIssueBatchProposalEvent(event)) {
        // Phase 75: Attach batch proposal to the current assistant message.
        // Attaching per-message (not globally) supports multiple proposals per session.
        const currentMsg = this.store.currentAssistantMessage;
        if (currentMsg) {
          currentMsg.batchProposal = event.data;
        }
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
    this._pendingQuestionDataList = [];
    this.clearQuestionSafetyTimeout();
    // SEC: Clear pending memory sources to prevent cross-turn leakage.
    // If a previous stream terminated without message_stop, stale sources
    // could be attached to the next assistant message.
    this.store.consumePendingMemorySources();

    // Defensive: clear any leftover pendingQuestion from previous turn.
    // Ensures WaitingIndicator hides when new message stream begins.
    if (this.store.pendingQuestion !== null) {
      this.store.pendingQuestion = null;
    }

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

    // Cancel question safety timeout — stream is still alive, wait for real message_stop
    this.clearQuestionSafetyTimeout();

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

  /** Handle question_request — accumulates question data for merged wizard UI. */
  handleQuestionRequest(event: QuestionRequestEvent): void {
    // Accumulate (not overwrite) for multiple ask_user calls in one turn
    this._pendingQuestionDataList.push({
      questionId: event.data.questionId,
      questions: event.data.questions,
    });
    // Also set store-level pending question (for UI state: isWaitingForUser, input disabling)
    this.store.handleQuestionRequest(event);

    // Safety: synthesize message_stop if it never arrives (PermissionResultDeny path)
    this.clearQuestionSafetyTimeout();
    this._questionSafetyTimeout = setTimeout(() => {
      this._questionSafetyTimeout = null;
      if (this._pendingQuestionDataList.length > 0 && this.store.streamingState.currentMessageId) {
        this.handleTextComplete({
          event: 'message_stop',
          data: {
            messageId: this.store.streamingState.currentMessageId,
            stopReason: 'question_pending',
          },
        } as unknown as MessageStopEvent);
      }
    }, QUESTION_SAFETY_TIMEOUT_MS);
  }

  /** Handle structured_result — stores pending for attachment on message_stop. */
  handleStructuredResult(event: StructuredResultEvent): void {
    const { schemaType, data } = event.data;
    this.store.setPendingStructuredResult({ schemaType, data });
  }

  /** Handle message_stop — finalizes message and adds to history. */
  handleTextComplete(event: MessageStopEvent): void {
    const { messageId, usage, costUsd } = event.data;

    // Cancel safety timeout — message_stop arrived normally
    this.clearQuestionSafetyTimeout();

    // Finalize any in-progress thinking block duration
    this.finalizeLastThinkingBlockDuration();

    // Calculate thinking duration if thinking occurred
    const thinkingDurationMs = this.store.streamingState.thinkingStartedAt
      ? Date.now() - this.store.streamingState.thinkingStartedAt
      : undefined;

    // Consume buffered data from streaming phase (T63, T64)
    const toolCalls = this.store.consumePendingToolCalls();
    const citations = this.store.consumePendingCitations();
    const memorySources = this.store.consumePendingMemorySources();

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
      memorySources,
      structuredResult: this.store.consumePendingStructuredResult(),
      questionData: this._pendingQuestionDataList[0],
      questionDataList:
        this._pendingQuestionDataList.length > 0 ? [...this._pendingQuestionDataList] : undefined,
      metadata: {
        tokenCount: usage?.totalTokens,
        costUsd,
      },
    };

    // Guard: if a message with the same ID already exists (e.g., safety timeout fired
    // before real message_stop), merge into existing instead of creating a duplicate.
    const existingIdx = this.store.messages.findIndex((m) => m.id === messageId);
    if (existingIdx >= 0) {
      this.store.messages[existingIdx] = assistantMessage;
    } else {
      this.store.messages.push(assistantMessage);
    }

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

    // Non-retryable or max retries exceeded — extract human-friendly message
    this.store.error = this.parseErrorMessage(errorCode, message);
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

  /**
   * Phase 69: Handle `memory_used` event — buffer recall sources to attach
   * to the in-flight assistant message at message_stop. Mirrors the citation
   * pattern (handleCitation -> consumePendingCitations).
   */
  handleMemoryUsed(event: MemoryUsedEvent): void {
    if (event.data?.sources?.length) {
      this.store.addPendingMemorySources(event.data.sources);
    }
  }

  // ========================================
  // Private Helpers
  // ========================================

  /** Clear the question safety timeout if active. */
  private clearQuestionSafetyTimeout(): void {
    if (this._questionSafetyTimeout !== null) {
      clearTimeout(this._questionSafetyTimeout);
      this._questionSafetyTimeout = null;
    }
  }

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

  /** Extract a human-friendly error message from potentially nested API error JSON. */
  private parseErrorMessage(errorCode: string, rawMessage: string): string {
    // Try to extract nested JSON error (e.g. "API Error: 429 {\"type\":\"error\",...}")
    const jsonMatch = rawMessage.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[0]);
        const nested = parsed?.error?.message ?? parsed?.message;
        if (typeof nested === 'string') return nested;
      } catch {
        /* not JSON — fall through */
      }
    }
    // Strip "API Error: NNN " prefix for cleaner display
    const stripped = rawMessage.replace(/^API Error:\s*\d+\s*/i, '').trim();
    return stripped || `${errorCode}: ${rawMessage}`;
  }

  /** Check if a delta is noise content (e.g., literal "(no content)"). */
  private isNoiseDelta(delta: string): boolean {
    if (delta.length === 0) return true;
    if (delta.trim() === '(no content)') return true;
    return false;
  }
}
