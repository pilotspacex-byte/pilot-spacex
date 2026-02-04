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
import type { ChatMessage, MessageRole, MessageMetadata } from './types/conversation';
import type { PilotSpaceStore } from './PilotSpaceStore';
import type { PilotSpaceStreamHandler } from './PilotSpaceStreamHandler';

/**
 * API base URL for backend requests.
 * Falls back to localhost if not configured.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

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
  async sendMessage(content: string, metadata?: Partial<MessageMetadata>): Promise<void> {
    // Enrich metadata with active skill/agent context
    const enrichedMetadata: Partial<MessageMetadata> = { ...metadata };
    if (this.store.activeSkill) {
      enrichedMetadata.skillInvoked = this.store.activeSkill.name;
    }
    if (this.store.mentionedAgents.length > 0) {
      enrichedMetadata.agentMentioned = this.store.mentionedAgents[0];
    }

    // Create user message
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user' as MessageRole,
      content,
      timestamp: new Date(),
      metadata: enrichedMetadata,
    };

    runInAction(() => {
      this.store.messages.push(userMessage);
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
          context: this.store.conversationContext,
          session_id: this.store.sessionId,
          fork_session_id: this.store.forkSessionId,
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
  async approveRequest(requestId: string): Promise<void> {
    const request = this.store.pendingApprovals.find((r) => r.requestId === requestId);
    if (!request) {
      console.error(`Approval request ${requestId} not found`);
      return;
    }

    try {
      // Send approval to backend via API
      const authHeaders = await this.streamHandler.getAuthHeaders();
      await fetch(`${API_BASE}/ai/approvals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          request_id: requestId,
          decision: 'approved',
        }),
      });

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
      await fetch(`${API_BASE}/ai/approvals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          request_id: requestId,
          decision: 'rejected',
          reason,
        }),
      });

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
  async approveAction(id: string, _modifications?: Record<string, unknown>): Promise<void> {
    await this.approveRequest(id);
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
   * Submit an answer to a pending agent question.
   *
   * @param questionId - Question identifier (tool call ID)
   * @param answer - User's answer text
   */
  async submitQuestionAnswer(questionId: string, answer: string): Promise<void> {
    if (!this.store.sessionId) return;

    try {
      const headers = await this.streamHandler.getAuthHeaders();
      await fetch(`${API_BASE}/ai/chat/answer`, {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.store.sessionId,
          question_id: questionId,
          answer,
        }),
      });

      runInAction(() => {
        if (this.store.pendingQuestion?.questionId === questionId) {
          this.store.pendingQuestion.resolvedAnswer = answer;
        }
      });
    } catch (err) {
      console.error('Failed to submit question answer:', err);
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
    this.store.error = null;
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
