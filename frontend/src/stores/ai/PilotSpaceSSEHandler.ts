/**
 * PilotSpace SSE Handler - Manages SSE streaming and event parsing.
 *
 * Extracted from PilotSpaceStore to keep files under 700 lines.
 * Handles:
 * - SSE connection lifecycle (queue mode + direct mode)
 * - SSE buffer parsing
 * - Event routing to typed handlers
 * - Auth header retrieval
 *
 * @module stores/ai/PilotSpaceSSEHandler
 */
import { runInAction } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import type {
  ChatMessage,
  MessageRole,
  ToolCall,
} from './types/conversation';
import type {
  MessageStartEvent,
  TextDeltaEvent,
  ToolUseEvent,
  ToolResultEvent,
  TaskProgressEvent,
  ApprovalRequestEvent,
  ContentUpdateEvent,
  MessageStopEvent,
  ErrorEvent,
} from './types/events';
import {
  isMessageStartEvent,
  isTextDeltaEvent,
  isToolUseEvent,
  isToolResultEvent,
  isTaskProgressEvent,
  isApprovalRequestEvent,
  isMessageStopEvent,
  isErrorEvent,
} from './types/events';
import type { PilotSpaceStore } from './PilotSpaceStore';
import type { ApprovalRequest } from './PilotSpaceStore';
import type { ConfidenceTag } from './types/skills';

/**
 * API base URL for backend requests.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/**
 * Handles SSE streaming connections and event dispatching for PilotSpaceStore.
 *
 * Delegates state mutations back to the store via its public API.
 */
export class PilotSpaceSSEHandler {
  private client: SSEClient | null = null;

  constructor(private readonly store: PilotSpaceStore) {}

  /**
   * Connect to a specific SSE stream URL (queue mode).
   * @param streamUrl - Stream URL (e.g., /api/v1/ai/chat/stream/{job_id})
   */
  async connectToStream(streamUrl: string): Promise<void> {
    const absoluteUrl = streamUrl.startsWith('http')
      ? streamUrl
      : `${API_BASE}${streamUrl.startsWith('/') ? '' : '/'}${streamUrl}`;

    this.client = new SSEClient({
      url: absoluteUrl,
      method: 'GET',
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
   * Abort the current SSE connection.
   */
  abort(): void {
    this.client?.abort();
    this.client = null;
  }

  // ========================================
  // SSE Event Handlers
  // ========================================

  private handleSSEEvent(sseEvent: SSEEvent): void {
    runInAction(() => {
      const event = sseEvent as unknown as
        | MessageStartEvent
        | TextDeltaEvent
        | ToolUseEvent
        | ToolResultEvent
        | TaskProgressEvent
        | ApprovalRequestEvent
        | ContentUpdateEvent
        | MessageStopEvent
        | ErrorEvent;

      if (isMessageStartEvent(event)) {
        this.handleMessageStart(event);
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
      } else if (event.type === 'content_update') {
        this.store.handleContentUpdate(event as ContentUpdateEvent);
      } else if (isMessageStopEvent(event)) {
        this.handleTextComplete(event);
      } else if (isErrorEvent(event)) {
        this.handleError(event);
      }
    });
  }

  private handleMessageStart(event: MessageStartEvent): void {
    const { messageId, sessionId } = event.data;
    this.store.setSessionId(sessionId);
    this.store.updateStreamingState({
      isStreaming: true,
      streamContent: '',
      currentMessageId: messageId,
      phase: 'message_start',
    });
  }

  private handleTextDelta(event: TextDeltaEvent): void {
    const { delta } = event.data;
    this.store.streamingState.streamContent += delta;
    this.store.streamingState.phase = 'content';
  }

  private handleToolUseStart(event: ToolUseEvent): void {
    const { toolCallId, toolName, toolInput } = event.data;
    const toolCall: ToolCall = {
      id: toolCallId,
      name: toolName,
      input: toolInput,
      status: 'pending',
    };

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

  private handleToolResult(event: ToolResultEvent): void {
    const { toolCallId, status, output, errorMessage } = event.data;
    const toolCallStatus: 'pending' | 'completed' | 'failed' =
      status === 'cancelled' ? 'failed' : status;

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

  private handleTaskUpdate(event: TaskProgressEvent): void {
    const {
      taskId,
      subject,
      status,
      progress,
      description,
      currentStep,
      totalSteps,
      estimatedSecondsRemaining,
    } = event.data;

    this.store.addTask(taskId, {
      subject,
      status,
      progress,
      description,
      currentStep,
      totalSteps,
      estimatedSecondsRemaining,
    });
  }

  private handleApprovalRequired(event: ApprovalRequestEvent): void {
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

    const request: ApprovalRequest = {
      requestId,
      actionType,
      description,
      consequences,
      affectedEntities,
      urgency,
      proposedContent,
      expiresAt: new Date(expiresAt),
      confidenceTag: confidenceTag as ConfidenceTag | undefined,
      createdAt: new Date(),
    };

    this.store.addApproval(request);
  }

  private handleTextComplete(event: MessageStopEvent): void {
    const { messageId, usage, costUsd } = event.data;

    const assistantMessage: ChatMessage = {
      id: messageId,
      role: 'assistant' as MessageRole,
      content: this.store.streamingState.streamContent,
      timestamp: new Date(),
      metadata: {
        tokenCount: usage?.totalTokens,
        costUsd,
      },
    };

    this.store.messages.push(assistantMessage);

    this.store.updateStreamingState({
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    });
  }

  private handleError(event: ErrorEvent): void {
    const { errorCode, message, retryable, retryAfter } = event.data;
    this.store.error = `[${errorCode}] ${message}`;

    this.store.updateStreamingState({
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    });

    if (retryable && retryAfter) {
      console.log(`Error is retryable. Retry after ${retryAfter}s`);
    }
  }
}
