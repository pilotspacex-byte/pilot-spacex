/**
 * PilotSpace Stream Handler - SSE event handling and stream parsing.
 *
 * Extracts all SSE event handlers and stream parsing logic from PilotSpaceStore.
 * Operates on the store via a reference passed in the constructor.
 *
 * @module stores/ai/PilotSpaceStreamHandler
 * @see specs/005-conversational-agent-arch/plan.md (T048)
 */
import { runInAction } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import type { ChatMessage, MessageRole, ToolCall } from './types/conversation';
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
} from './types/events';
import type { PilotSpaceStore } from './PilotSpaceStore';

/**
 * API base URL for backend requests.
 * Falls back to localhost if not configured.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/**
 * Handles SSE event dispatch, stream parsing, and connection management.
 *
 * Separated from PilotSpaceStore to keep the store focused on state
 * and simple mutations while this class handles stream I/O.
 */
/** Maximum retry attempts for retryable errors */
const MAX_RETRY_ATTEMPTS = 3;

export class PilotSpaceStreamHandler {
  /** Active SSE client instance */
  private client: SSEClient | null = null;
  /** Last parent tool use ID from content_block_start for subagent correlation (G12) */
  private _lastParentToolUseId: string | null = null;
  /** Current retry attempt count */
  private _retryCount = 0;
  /** Pending retry timer ID */
  private _retryTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private store: PilotSpaceStore) {}

  // ========================================
  // Stream Connection
  // ========================================

  /**
   * Connect to a specific SSE stream URL (queue mode).
   * @param streamUrl - Stream URL (e.g., /api/v1/ai/chat/stream/{job_id})
   * @param _jobId - Optional job identifier for tracking (reserved for future use)
   */
  async connectToStream(streamUrl: string, _jobId?: string): Promise<void> {
    this.resetRetryState();
    // Ensure absolute URL
    const absoluteUrl = streamUrl.startsWith('http')
      ? streamUrl
      : `${API_BASE}${streamUrl.startsWith('/') ? '' : '/'}${streamUrl}`;

    this.client = new SSEClient({
      url: absoluteUrl,
      method: 'GET', // Queue mode uses GET for stream endpoint
      onMessage: (event: SSEEvent) => this.handleSSEEvent(event),
      onComplete: () => {
        runInAction(() => {
          this.store.updateStreamingState({
            isStreaming: false,
            streamContent: '',
            currentMessageId: null,
          });
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.store.updateStreamingState({
            isStreaming: false,
            streamContent: '',
            currentMessageId: null,
          });
          this.store.error = err.message;
        });
      },
    });

    await this.client.connect();
  }

  /**
   * Consume SSE events from a fetch Response stream (direct mode).
   * @param response - Fetch Response with text/event-stream body
   */
  async consumeSSEStream(response: Response): Promise<void> {
    this.resetRetryState();
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body available');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          // Process remaining buffer
          if (buffer.trim()) {
            const events = this.parseSSEBuffer(buffer + '\n\n');
            for (const event of events) {
              this.handleSSEEvent(event);
            }
          }
          runInAction(() => {
            this.store.updateStreamingState({
              isStreaming: false,
              streamContent: '',
              currentMessageId: null,
            });
          });
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = this.parseSSEBuffer(buffer);

        // Update buffer with remaining unparsed data
        const lastDoubleNewline = buffer.lastIndexOf('\n\n');
        if (lastDoubleNewline !== -1) {
          buffer = buffer.slice(lastDoubleNewline + 2);
        }

        for (const event of events) {
          this.handleSSEEvent(event);
        }
      }
    } catch (err) {
      runInAction(() => {
        this.store.updateStreamingState({
          isStreaming: false,
          streamContent: '',
          currentMessageId: null,
        });
        this.store.error = err instanceof Error ? err.message : 'Stream error';
      });
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Parse SSE buffer into events.
   * Returns array of parsed events.
   */
  parseSSEBuffer(buffer: string): SSEEvent[] {
    const events: SSEEvent[] = [];
    const eventBlocks = buffer.split('\n\n').filter((block) => block.trim());

    for (const block of eventBlocks) {
      const lines = block.split('\n');
      let eventType = '';
      let eventData = '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          eventData += line.slice(5).trim();
        }
      }

      if (eventType && eventData) {
        try {
          const data = JSON.parse(eventData);
          events.push({ type: eventType, data });
        } catch {
          // Skip invalid JSON
        }
      }
    }

    return events;
  }

  /**
   * Get Supabase auth headers for authenticated requests.
   */
  async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const { supabase } = await import('@/lib/supabase');
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.access_token) {
        return { Authorization: `Bearer ${session.access_token}` };
      }
    } catch {
      console.warn('Failed to get auth session for chat request');
    }
    return {};
  }

  /**
   * Abort the active SSE client connection.
   */
  abortClient(): void {
    this.resetRetryState();
    this.client?.abort();
    this.client = null;
  }

  // ========================================
  // SSE Event Handlers (T048)
  // ========================================

  /**
   * Handle SSE event from backend.
   * Routes to specific handler based on event type.
   *
   * @param sseEvent - SSE event from stream
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
        | ToolInputDeltaEvent;

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
        this.handleToolUseStart(event);
      } else if (isToolResultEvent(event)) {
        this.handleToolResult(event);
      } else if (isTaskProgressEvent(event)) {
        this.handleTaskUpdate(event);
      } else if (isApprovalRequestEvent(event)) {
        this.handleApprovalRequired(event);
      } else if (isAskUserQuestionEvent(event)) {
        this.handleAskUserQuestion(event);
      } else if (isContentUpdateEvent(event)) {
        this.store.handleContentUpdate(event);
      } else if (isStructuredResultEvent(event)) {
        this.handleStructuredResult(event);
      } else if (isCitationEvent(event)) {
        this.handleCitation(event);
      } else if (isMemoryUpdateEvent(event)) {
        this.handleMemoryUpdate(event);
      } else if (isToolInputDeltaEvent(event)) {
        this.handleToolInputDelta(event);
      } else if (isMessageStopEvent(event)) {
        this.handleTextComplete(event);
      } else if (isBudgetWarningEvent(event)) {
        this.handleBudgetWarning(event);
      } else if (isToolAuditEvent(event)) {
        this.handleToolAudit(event);
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

    // Reset parent correlation state
    this._lastParentToolUseId = null;

    // Initialize streaming state
    this.store.streamingState = {
      isStreaming: true,
      streamContent: '',
      currentMessageId: messageId,
      phase: 'message_start',
      thinkingContent: '',
      isThinking: false,
      thinkingStartedAt: null,
    };
  }

  /** Handle content_block_start — tracks block type for progressive rendering. */
  handleContentBlockStart(event: ContentBlockStartEvent): void {
    const { contentType, index, parentToolUseId } = event.data;

    // Track current block type and index for progressive rendering (G13)
    this.store.streamingState.currentBlockType = contentType;
    this.store.streamingState.currentBlockIndex = index;

    // Store parentToolUseId for subagent correlation (G12)
    if (parentToolUseId) {
      this._lastParentToolUseId = parentToolUseId;
    }

    // Pre-signal phase transitions based on block type (G-01)
    if (contentType === 'thinking') {
      this.store.streamingState.phase = 'thinking';
      this.store.streamingState.isThinking = true;
      if (!this.store.streamingState.thinkingStartedAt) {
        this.store.streamingState.thinkingStartedAt = Date.now();
      }
    } else if (contentType === 'text' && this.store.streamingState.phase === 'message_start') {
      this.store.streamingState.phase = 'content';
    }
  }

  /** Handle thinking_delta — appends streaming thinking chunks. */
  handleThinkingDelta(event: ThinkingDeltaEvent): void {
    const { delta, signature, blockIndex, redacted } = event.data;

    // Start thinking timer on first delta
    if (!this.store.streamingState.isThinking) {
      this.store.streamingState.isThinking = true;
      this.store.streamingState.thinkingStartedAt = Date.now();
    }

    // Backward-compatible: always accumulate into flat thinkingContent
    this.store.streamingState.thinkingContent += delta;
    this.store.streamingState.phase = 'thinking';

    // G-07: Accumulate per-block thinking entries for interleaved rendering
    if (blockIndex !== undefined) {
      if (!this.store.streamingState.thinkingBlocks) {
        this.store.streamingState.thinkingBlocks = [];
      }
      const existing = this.store.streamingState.thinkingBlocks.find(
        (b) => b.blockIndex === blockIndex
      );
      if (existing) {
        existing.content += delta;
      } else {
        this.store.streamingState.thinkingBlocks.push({
          content: delta,
          blockIndex,
          redacted,
        });
      }
    }

    // Capture thinking block signature for multi-turn verification (G-06)
    if (signature) {
      this.store.streamingState.thinkingSignature = signature;
    }
  }

  /** Handle text_delta — appends streaming text content. */
  handleTextDelta(event: TextDeltaEvent): void {
    const { delta } = event.data;

    // End thinking phase when text starts arriving
    if (this.store.streamingState.isThinking) {
      this.store.streamingState.isThinking = false;
    }

    // Accumulate text delta
    this.store.streamingState.streamContent += delta;
    this.store.streamingState.phase = 'content';
  }

  /** Handle tool_use — buffers tool call for attachment on message finalization (T63). */
  handleToolUseStart(event: ToolUseEvent): void {
    const { toolCallId, toolName, toolInput } = event.data;

    // Create tool call entry with optional parent correlation (G12)
    const toolCall: ToolCall = {
      id: toolCallId,
      name: toolName,
      input: toolInput,
      status: 'pending',
      parentToolUseId: this._lastParentToolUseId ?? undefined,
    };

    // Buffer tool call — message doesn't exist in messages[] during streaming
    this.store.addPendingToolCall(toolCall);

    this.store.streamingState.phase = 'tool_use';
  }

  /** Handle tool_result — updates tool call status/result, checks pending buffer first (T66). */
  handleToolResult(event: ToolResultEvent): void {
    const { toolCallId, status, output, errorMessage } = event.data;

    // Map backend status to ToolCall status
    const toolCallStatus: 'pending' | 'completed' | 'failed' =
      status === 'cancelled' ? 'failed' : status;

    // Check pending buffer first (tool call may not be in messages[] yet)
    const pendingTc = this.store.findPendingToolCall(toolCallId);
    if (pendingTc) {
      pendingTc.status = toolCallStatus;
      pendingTc.output = output;
      if (errorMessage) {
        pendingTc.errorMessage = errorMessage;
      }
      return;
    }

    // Fallback: search finalized messages
    for (const message of this.store.messages) {
      if (message.toolCalls) {
        const toolCall = message.toolCalls.find((tc) => tc.id === toolCallId);
        if (toolCall) {
          toolCall.status = toolCallStatus;
          toolCall.output = output;
          if (errorMessage) {
            toolCall.errorMessage = errorMessage;
          }
          break;
        }
      }
    }
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

    // Calculate thinking duration if thinking occurred
    const thinkingDurationMs = this.store.streamingState.thinkingStartedAt
      ? Date.now() - this.store.streamingState.thinkingStartedAt
      : undefined;

    // Consume buffered data from streaming phase (T63, T64)
    const toolCalls = this.store.consumePendingToolCalls();
    const citations = this.store.consumePendingCitations();

    // G-07: Collect interleaved thinking blocks if present
    const thinkingBlocks = this.store.streamingState.thinkingBlocks?.length
      ? [...this.store.streamingState.thinkingBlocks]
      : undefined;

    // Create completed assistant message
    const assistantMessage: ChatMessage = {
      id: messageId,
      role: 'assistant' as MessageRole,
      content: this.store.streamingState.streamContent,
      timestamp: new Date(),
      thinkingContent: this.store.streamingState.thinkingContent || undefined,
      thinkingBlocks,
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

    // Reset streaming state
    this.store.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
      thinkingContent: '',
      isThinking: false,
      thinkingStartedAt: null,
    };
  }

  /** Handle budget_warning — surfaces warning to user via store error state. */
  handleBudgetWarning(event: BudgetWarningEvent): void {
    const { currentCostUsd, maxBudgetUsd, percentUsed, message } = event.data;
    this.store.error = `Budget warning (${percentUsed}%): ${message} ($${currentCostUsd.toFixed(4)} / $${maxBudgetUsd.toFixed(2)})`;
  }

  /** Handle tool_audit — updates tool call with duration info, checks pending buffer first. */
  handleToolAudit(event: ToolAuditEvent): void {
    const { toolUseId, durationMs } = event.data;

    // Check pending buffer first (tool call may not be in messages[] yet)
    const pendingTc = this.store.findPendingToolCall(toolUseId);
    if (pendingTc) {
      pendingTc.durationMs = durationMs ?? undefined;
      return;
    }

    // Fallback: search finalized messages
    for (const message of this.store.messages) {
      if (message.toolCalls) {
        const toolCall = message.toolCalls.find((tc) => tc.id === toolUseId);
        if (toolCall) {
          toolCall.durationMs = durationMs ?? undefined;
          break;
        }
      }
    }
  }

  /**
   * Handle error event.
   * Implements exponential backoff retry for retryable errors (max 3 attempts).
   * Non-retryable errors reset streaming state immediately.
   */
  handleError(event: ErrorEvent): void {
    const { errorCode, message, retryable, retryAfter } = event.data;

    if (retryable && this._retryCount < MAX_RETRY_ATTEMPTS) {
      this._retryCount++;
      // Use server-provided retryAfter or exponential backoff (1s, 2s, 4s)
      const delaySeconds = retryAfter ?? Math.pow(2, this._retryCount - 1);
      this.store.error = `[${errorCode}] ${message} — retrying in ${delaySeconds}s (${this._retryCount}/${MAX_RETRY_ATTEMPTS})`;

      this._retryTimer = setTimeout(() => {
        this._retryTimer = null;
        // Reconnect: re-consume the current stream if client exists
        if (this.client) {
          this.client.connect();
        }
      }, delaySeconds * 1000);
      return;
    }

    // Non-retryable or max retries exceeded
    this._retryCount = 0;
    this.store.error = `[${errorCode}] ${message}`;

    // Reset streaming state
    this.store.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    };
  }

  /**
   * Handle citation event — buffer for attachment on message finalization (T64).
   */
  handleCitation(event: CitationEvent): void {
    const { citations } = event.data;
    this.store.addPendingCitations(citations);
  }

  /**
   * Handle memory_update event — store for UI notification (T73).
   */
  handleMemoryUpdate(event: MemoryUpdateEvent): void {
    this.store.lastMemoryUpdate = event.data;
  }

  /** Handle tool_input_delta — accumulates partial JSON on pending tool call (T65). */
  handleToolInputDelta(event: ToolInputDeltaEvent): void {
    const { toolUseId, inputDelta } = event.data;
    const tc = this.store.findPendingToolCall(toolUseId);
    if (tc) {
      tc.partialInput = (tc.partialInput ?? '') + inputDelta;
    }
  }

  /** Reset retry state. Call when starting a new stream. */
  resetRetryState(): void {
    this._retryCount = 0;
    if (this._retryTimer) {
      clearTimeout(this._retryTimer);
      this._retryTimer = null;
    }
  }
}
