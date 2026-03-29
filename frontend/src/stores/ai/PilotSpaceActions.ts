/**
 * PilotSpace Actions - User-facing async actions for AI chat.
 *
 * Extracts message sending, approval handling, and lifecycle actions
 * from PilotSpaceStore. Operates on the store via a reference passed
 * in the constructor, and uses PilotSpaceStreamHandler for SSE I/O.
 *
 * @module stores/ai/PilotSpaceActions
 * @see specs/005-conversational-agent-arch/plan.md (T042-T049)
 */
import { runInAction } from 'mobx';
import { generateUUID } from '@/lib/utils';
import type { ChatMessage, MessageRole, MessageMetadata } from './types/conversation';
import type { PilotSpaceStore } from './PilotSpaceStore';
import type { PilotSpaceStreamHandler } from './PilotSpaceStreamHandler';

/**
 * API base URL for backend requests.
 * Falls back to localhost if not configured.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '/api/v1';

/**
 * Encapsulates user-facing async actions: sending messages,
 * handling approvals, submitting question answers, and lifecycle
 * operations (abort, clear, reset).
 */
export class PilotSpaceActions {
  constructor(
    private store: PilotSpaceStore,
    private streamHandler: PilotSpaceStreamHandler
  ) {}

  // ========================================
  // Actions - Message Sending
  // ========================================

  /**
   * Send message to AI and stream response via SSE.
   *
   * Supports both queue mode and direct mode:
   * - Queue mode (AI_QUEUE_MODE=true): POST /chat returns job_id + stream_url, then connect to GET /chat/stream/{job_id}
   * - Direct mode (AI_QUEUE_MODE=false): POST /chat returns StreamingResponse with SSE
   *
   * Implements SSE streaming with 8 event types:
   * - message_start: Initialize new message
   * - text_delta: Append streaming text
   * - tool_use: Agent using tools
   * - tool_result: Tool execution result
   * - task_progress: Long-running task update
   * - approval_request: Human approval required (DD-003)
   * - message_stop: Finalize message
   * - error: Error handling
   *
   * @param content - User message content
   * @param metadata - Optional message metadata (skill invocation, agent mention)
   */
  async sendMessage(
    content: string,
    metadata?: Partial<MessageMetadata>,
    attachmentIds?: string[]
  ): Promise<void> {
    // Enrich metadata with active skill/agent context
    const enrichedMetadata: Partial<MessageMetadata> = { ...metadata };
    if (this.store.activeSkill) {
      enrichedMetadata.skillInvoked = this.store.activeSkill.name;
    }
    if (this.store.mentionedAgents.length > 0) {
      enrichedMetadata.agentMentioned = this.store.mentionedAgents[0];
    }

    // Skip user message for answer submissions — the inline ResolvedSummary
    // already shows the Q&A in the assistant message (avoids redundant bubble).
    const skipUserMessage = !!enrichedMetadata.isAnswerMessage;

    const userMessage: ChatMessage | null = skipUserMessage
      ? null
      : {
          id: generateUUID(),
          role: 'user' as MessageRole,
          content: content,
          timestamp: new Date(),
          metadata: enrichedMetadata,
        };

    runInAction(() => {
      if (userMessage) {
        this.store.messages.push(userMessage);
      }
      this.store.streamingState = {
        isStreaming: true,
        streamContent: '',
        currentMessageId: null,
        phase: 'connecting',
      };
      this.store.error = null;
    });

    try {
      // Get auth headers
      const authHeaders = await this.streamHandler.getAuthHeaders();

      // Attempt to POST to /chat endpoint
      const response = await fetch(`${API_BASE}/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({
          message: content,
          context: {
            ...this.store.conversationContext,
            attachment_ids: attachmentIds ?? [],
          },
          session_id: this.store.sessionId,
          fork_session_id: this.store.forkSessionId,
          model_override: this.store.selectedModel
            ? {
                provider: this.store.selectedModel.provider,
                model: this.store.selectedModel.modelId,
                config_id: this.store.selectedModel.configId,
              }
            : undefined,
          metadata: enrichedMetadata,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
      }

      // Clear transient state after successful request (consumed once)
      runInAction(() => {
        this.store.forkSessionId = null;
        this.store.activeSkill = null;
        this.store.mentionedAgents = [];
      });

      // Check Content-Type to determine response mode
      const contentType = response.headers.get('Content-Type') || '';

      if (contentType.includes('application/json')) {
        // Queue mode: Extract job_id and stream_url from JSON response
        const queueResponse = await response.json();
        const { job_id, session_id, stream_url } = queueResponse;

        // Update session_id if provided
        if (session_id) {
          runInAction(() => {
            this.store.setSessionId(session_id);
          });
        }

        // Connect to queue stream endpoint
        await this.streamHandler.connectToStream(stream_url, job_id);
      } else if (contentType.includes('text/event-stream')) {
        // Direct mode: Response is already an SSE stream
        // Parse SSE events directly from response body
        await this.streamHandler.consumeSSEStream(response);
      } else {
        throw new Error(`Unexpected response content type: ${contentType}`);
      }

      // Detect silent failure: stream completed without producing an assistant message.
      // This can happen when the backend returns an empty SSE stream (e.g., missing API key,
      // provider outage) without sending an error event.
      const messageCountAfter = this.store.messages.length;
      const lastMessage = messageCountAfter > 0 ? this.store.messages[messageCountAfter - 1] : null;
      if (
        !enrichedMetadata.isAnswerMessage &&
        !this.store.error &&
        lastMessage?.role !== 'assistant' &&
        !this.store.streamingState.isStreaming
      ) {
        runInAction(() => {
          this.store.error =
            'No response received from AI. Check your API key configuration or try again.';
        });
      }
    } catch (err) {
      runInAction(() => {
        this.store.streamingState = {
          isStreaming: false,
          streamContent: '',
          currentMessageId: null,
        };
        this.store.error = err instanceof Error ? err.message : 'Failed to send message';
      });
    }
  }

  // ========================================
  // Actions - Approval Management (DD-003)
  // ========================================

  /**
   * Approve a pending request.
   * Sends approval to backend and removes from queue.
   *
   * @param requestId - Request identifier
   */
  async approveRequest(requestId: string, modifications?: Record<string, unknown>): Promise<void> {
    const request = this.store.pendingApprovals.find((r) => r.requestId === requestId);
    if (!request) {
      console.error(`Approval request ${requestId} not found`);
      return;
    }

    try {
      // Send approval to backend via API
      const authHeaders = await this.streamHandler.getAuthHeaders();
      const response = await fetch(`${API_BASE}/ai/approvals/${requestId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ approved: true, ...(modifications && { modifications }) }),
      });

      if (!response.ok) {
        throw new Error(`Approval failed: ${response.status} ${response.statusText}`);
      }

      runInAction(() => {
        this.store.pendingApprovals = this.store.pendingApprovals.filter(
          (r) => r.requestId !== requestId
        );
      });
    } catch (err) {
      runInAction(() => {
        this.store.error = err instanceof Error ? err.message : 'Failed to approve request';
      });
    }
  }

  /**
   * Reject a pending request.
   * Sends rejection to backend and removes from queue.
   *
   * @param requestId - Request identifier
   * @param reason - Optional rejection reason
   */
  async rejectRequest(requestId: string, reason?: string): Promise<void> {
    const request = this.store.pendingApprovals.find((r) => r.requestId === requestId);
    if (!request) {
      console.error(`Approval request ${requestId} not found`);
      return;
    }

    try {
      // Send rejection to backend via API
      const authHeaders = await this.streamHandler.getAuthHeaders();
      const response = await fetch(`${API_BASE}/ai/approvals/${requestId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ approved: false, note: reason }),
      });

      if (!response.ok) {
        throw new Error(`Rejection failed: ${response.status} ${response.statusText}`);
      }

      runInAction(() => {
        this.store.pendingApprovals = this.store.pendingApprovals.filter(
          (r) => r.requestId !== requestId
        );
      });
    } catch (err) {
      runInAction(() => {
        this.store.error = err instanceof Error ? err.message : 'Failed to reject request';
      });
    }
  }

  /**
   * Alias for approveRequest to match IPilotSpaceStore interface.
   */
  async approveAction(id: string, modifications?: Record<string, unknown>): Promise<void> {
    await this.approveRequest(id, modifications);
  }

  /**
   * Alias for rejectRequest to match IPilotSpaceStore interface.
   */
  async rejectAction(id: string, reason: string): Promise<void> {
    await this.rejectRequest(id, reason);
  }

  // ========================================
  // Actions - Question Handling
  // ========================================

  /**
   * Submit an answer to a pending agent question (stateless two-turn model).
   *
   * 1. Updates the assistant message's questionData with answers (inline resolved state)
   * 2. Sends a new chat turn with `[ANSWER:{questionId}]` prefix via sendMessage()
   * 3. Backend formats the Q&A context and continues the agent conversation
   *
   * @param questionId - Question identifier (tool call ID)
   * @param answer - User's answer text (JSON stringified answers)
   * @param answersRecord - Structured answers keyed by question index (q0, q1, ...)
   */
  async submitQuestionAnswer(
    questionId: string,
    answer: string,
    answersRecord?: Record<string, string>
  ): Promise<void> {
    if (!this.store.sessionId) return;
    if (this.store.isSubmittingAnswer) return;

    // Snapshot for rollback on failure
    const prevPendingQuestion = this.store.pendingQuestion
      ? { ...this.store.pendingQuestion }
      : null;
    const targetIdx = answersRecord
      ? this.store.messages.findLastIndex(
          (m) =>
            m.role === 'assistant' &&
            (m.questionDataList?.some((qd) => qd.questionId === questionId) ||
              m.questionData?.questionId === questionId)
        )
      : -1;

    try {
      runInAction(() => {
        this.store.isSubmittingAnswer = true;
        this.store.error = null;

        // Optimistically resolve the question inline in the assistant message
        if (answersRecord) {
          this.store.resolveQuestion(questionId, answersRecord);
        } else {
          this.store.clearPendingQuestion();
        }
      });

      // Send as new chat turn — backend recognizes [ANSWER:] prefix
      const prefixedMessage = `[ANSWER:${questionId}] ${answer}`;
      await this.sendMessage(prefixedMessage, { isAnswerMessage: true });

      // sendMessage catches errors internally — check if it recorded a failure
      if (this.store.error) {
        throw new Error(this.store.error);
      }
    } catch (err) {
      // Rollback optimistic update so user can re-submit
      runInAction(() => {
        this.store.error = err instanceof Error ? err.message : 'Failed to submit answer';
        this.store.pendingQuestion = prevPendingQuestion;
        if (targetIdx >= 0) {
          const msg = this.store.messages[targetIdx]!;
          if (msg.questionDataList) {
            this.store.messages[targetIdx] = {
              ...msg,
              questionDataList: msg.questionDataList.map((qd) =>
                qd.questionId === questionId ? { ...qd, answers: undefined } : qd
              ),
              questionData: msg.questionData
                ? { ...msg.questionData, answers: undefined }
                : undefined,
            };
          } else if (msg.questionData) {
            this.store.messages[targetIdx] = {
              ...msg,
              questionData: { ...msg.questionData, answers: undefined },
            };
          }
        }
      });
    } finally {
      runInAction(() => {
        this.store.isSubmittingAnswer = false;
      });
    }
  }

  // ========================================
  // Lifecycle Actions
  // ========================================

  /**
   * Abort current streaming response.
   *
   * Sends interrupt signal to backend (Claude SDK process) before
   * closing the SSE connection for graceful shutdown.
   */
  abort(): void {
    // Send abort signal to backend to interrupt Claude SDK process.
    // Fire-and-forget: don't await, SSE close handles cleanup regardless.
    if (this.store.sessionId) {
      const sessionId = this.store.sessionId;
      this.streamHandler
        .getAuthHeaders()
        .then((authHeaders) => {
          fetch(`${API_BASE}/ai/chat/abort`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders },
            body: JSON.stringify({ session_id: sessionId }),
          }).catch(() => {
            // Ignore errors - SSE disconnect will also trigger cleanup
          });
        })
        .catch(() => {
          // Ignore auth errors - SSE disconnect will also trigger cleanup
        });
    }

    this.streamHandler.abortClient();

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

  /**
   * Clear conversation and reset state.
   */
  clear(): void {
    this.abort();
    this.store.messages = [];
    this.store.setSessionId(null);
    this.store.setForkSessionId(null);
    this.store.tasks.clear();
    this.store.pendingApprovals = [];
    this.store.pendingContentUpdates = [];
    this.store.pendingQuestion = null;
    this.store.error = null;
    // Reset pagination state
    this.store.setMessagePaginationState(false, 0);
    this.store.setIsLoadingMoreMessages(false);
  }

  /**
   * Reset all state (called on workspace change).
   */
  reset(): void {
    this.clear();
    this.store.clearContext();
    this.store.setWorkspaceId(null);
    this.store.skills = [];
  }
}
