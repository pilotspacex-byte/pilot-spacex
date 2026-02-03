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
  ErrorEvent,
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
  isErrorEvent,
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
export class PilotSpaceStreamHandler {
  /** Active SSE client instance */
  private client: SSEClient | null = null;
  /** Last parent tool use ID from content_block_start for subagent correlation (G12) */
  private _lastParentToolUseId: string | null = null;

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
        | ErrorEvent;

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
      } else if (event.type === 'content_update') {
        // Handle content_update event
        this.store.handleContentUpdate(event as ContentUpdateEvent);
      } else if (isStructuredResultEvent(event)) {
        this.handleStructuredResult(event);
      } else if (isMessageStopEvent(event)) {
        this.handleTextComplete(event);
      } else if (isErrorEvent(event)) {
        this.handleError(event);
      }
    });
  }

  /**
   * Handle message_start event.
   * Initializes new assistant message.
   */
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

  /**
   * Handle content_block_start event.
   * Tracks block type (text vs tool_use) for progressive rendering.
   */
  handleContentBlockStart(event: ContentBlockStartEvent): void {
    const { contentType, index, parentToolUseId } = event.data;

    // Track current block type and index for progressive rendering (G13)
    this.store.streamingState.currentBlockType = contentType;
    this.store.streamingState.currentBlockIndex = index;

    // Store parentToolUseId for subagent correlation (G12)
    if (parentToolUseId) {
      this._lastParentToolUseId = parentToolUseId;
    }

    // Pre-signal thinking phase when a thinking block starts
    if (contentType === 'text' && this.store.streamingState.phase === 'message_start') {
      this.store.streamingState.phase = 'content';
    }
  }

  /**
   * Handle thinking_delta event.
   * Appends streaming thinking chunks.
   */
  handleThinkingDelta(event: ThinkingDeltaEvent): void {
    const { delta } = event.data;

    // Start thinking timer on first delta
    if (!this.store.streamingState.isThinking) {
      this.store.streamingState.isThinking = true;
      this.store.streamingState.thinkingStartedAt = Date.now();
    }

    this.store.streamingState.thinkingContent += delta;
    this.store.streamingState.phase = 'thinking';
  }

  /**
   * Handle text_delta event.
   * Appends streaming text content.
   */
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

  /**
   * Handle tool_use event.
   * Records tool invocation.
   */
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

    // Find or create message to attach tool call
    const messageId = this.store.streamingState.currentMessageId;
    if (messageId) {
      const message = this.store.messages.find((m) => m.id === messageId);
      if (message) {
        if (!message.toolCalls) {
          message.toolCalls = [];
        }
        message.toolCalls.push(toolCall);
      }
    }

    this.store.streamingState.phase = 'tool_use';
  }

  /**
   * Handle tool_result event.
   * Updates tool call status and result.
   */
  handleToolResult(event: ToolResultEvent): void {
    const { toolCallId, status, output, errorMessage } = event.data;

    // Map backend status to ToolCall status
    const toolCallStatus: 'pending' | 'completed' | 'failed' =
      status === 'cancelled' ? 'failed' : status;

    // Find tool call in messages
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

  /**
   * Handle task_progress event.
   * Updates long-running task state.
   */
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

  /**
   * Handle approval_request event (DD-003).
   * Adds pending approval request to queue.
   */
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

  /**
   * Handle ask_user_question event.
   * Sets pending question requiring user response.
   */
  handleAskUserQuestion(event: AskUserQuestionEvent): void {
    const { questionId, questions } = event.data;
    this.store.pendingQuestion = { questionId, questions };
  }

  /**
   * Handle structured_result event.
   * Stores pending structured result for attachment to message on stop.
   */
  handleStructuredResult(event: StructuredResultEvent): void {
    const { schemaType, data } = event.data;
    this.store.setPendingStructuredResult({ schemaType, data });
  }

  /**
   * Handle message_stop event.
   * Finalizes message and adds to history.
   */
  handleTextComplete(event: MessageStopEvent): void {
    const { messageId, usage, costUsd } = event.data;

    // Calculate thinking duration if thinking occurred
    const thinkingDurationMs = this.store.streamingState.thinkingStartedAt
      ? Date.now() - this.store.streamingState.thinkingStartedAt
      : undefined;

    // Create completed assistant message
    const assistantMessage: ChatMessage = {
      id: messageId,
      role: 'assistant' as MessageRole,
      content: this.store.streamingState.streamContent,
      timestamp: new Date(),
      thinkingContent: this.store.streamingState.thinkingContent || undefined,
      thinkingDurationMs,
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

  /**
   * Handle error event.
   * Sets error state and resets streaming.
   */
  handleError(event: ErrorEvent): void {
    const { errorCode, message, retryable, retryAfter } = event.data;

    this.store.error = `[${errorCode}] ${message}`;

    // Reset streaming state
    this.store.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    };

    // TODO: Implement retry logic if retryable === true
    if (retryable && retryAfter) {
      console.log(`Error is retryable. Retry after ${retryAfter}s`);
    }
  }
}
