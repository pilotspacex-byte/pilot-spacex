/**
 * PilotSpace Store - Unified conversational agent state management.
 *
 * Consolidates AI agent interactions with:
 * - Conversational chat with streaming SSE
 * - Multi-turn session management
 * - Task tracking and progress updates
 * - Approval flow per DD-003 (human-in-the-loop)
 * - Context-aware execution (note, issue, project)
 *
 * @module stores/ai/PilotSpaceStore
 * @see specs/005-conversational-agent-arch/plan.md (T042-T049)
 */
import { makeAutoObservable, runInAction, computed } from 'mobx';
import { SSEClient, type SSEEvent } from '@/lib/sse-client';
import type { AIStore } from './AIStore';
import type {
  ChatMessage,
  MessageRole,
  StreamingState,
  ConversationContext,
  ToolCall,
  MessageMetadata,
} from './types/conversation';
import type {
  MessageStartEvent,
  TextDeltaEvent,
  ToolUseEvent,
  ToolResultEvent,
  TaskProgressEvent,
  ApprovalRequestEvent,
  MessageStopEvent,
  ErrorEvent,
  TaskStatus,
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
import type { SkillDefinition, ConfidenceTag } from './types/skills';

/**
 * Task state for long-running operations.
 * Maps to backend task tracking.
 */
export interface TaskState {
  /** Task identifier (UUIDv4) */
  id: string;
  /** Human-readable subject */
  subject: string;
  /** Current task status */
  status: TaskStatus;
  /** Progress percentage (0-100) */
  progress: number;
  /** Detailed description */
  description?: string;
  /** Current step label */
  currentStep?: string;
  /** Total steps */
  totalSteps?: number;
  /** Estimated seconds remaining */
  estimatedSecondsRemaining?: number;
  /** Creation timestamp */
  createdAt: Date;
  /** Last update timestamp */
  updatedAt: Date;
}

/**
 * Approval request state per DD-003.
 * Tracks pending actions requiring human approval.
 */
export interface ApprovalRequest {
  /** Unique request identifier */
  requestId: string;
  /** Action type requiring approval */
  actionType: string;
  /** Human-readable description */
  description: string;
  /** Consequences of approval */
  consequences?: string;
  /** Affected entities */
  affectedEntities: Array<{
    type: string;
    id: string;
    name: string;
    preview?: unknown;
  }>;
  /** Urgency level */
  urgency: 'low' | 'medium' | 'high';
  /** Proposed content for preview */
  proposedContent?: unknown;
  /** Expiration timestamp */
  expiresAt: Date;
  /** Confidence tag per DD-048 */
  confidenceTag?: ConfidenceTag;
  /** Creation timestamp */
  createdAt: Date;
}

/**
 * Note context state.
 */
export interface NoteContext {
  /** Current note ID */
  noteId: string;
  /** Selected text in editor */
  selectedText?: string;
  /** Selected block IDs */
  selectedBlockIds?: string[];
  /** Note title */
  noteTitle?: string;
}

/**
 * Issue context state.
 */
export interface IssueContext {
  /** Current issue ID */
  issueId: string;
  /** Issue title */
  issueTitle?: string;
  /** Issue status */
  issueStatus?: string;
}

/**
 * PilotSpace Store - Unified conversational agent state.
 *
 * @example
 * ```typescript
 * const store = new PilotSpaceStore(aiStore);
 *
 * // Set context
 * store.setNoteContext({ noteId: 'note-123' });
 *
 * // Send message
 * await store.sendMessage('Extract issues from this note');
 *
 * // Handle approval
 * store.approveRequest(requestId);
 * ```
 */
export class PilotSpaceStore {
  // ========================================
  // Observable State
  // ========================================

  /** Chat messages in conversation */
  messages: ChatMessage[] = [];

  /** Streaming state for in-progress messages */
  streamingState: StreamingState = {
    isStreaming: false,
    streamContent: '',
    currentMessageId: null,
  };

  /** Current session ID for multi-turn context */
  sessionId: string | null = null;

  /** Long-running tasks */
  tasks = new Map<string, TaskState>();

  /** Pending approval requests */
  pendingApprovals: ApprovalRequest[] = [];

  /** Current note context */
  noteContext: NoteContext | null = null;

  /** Current issue context */
  issueContext: IssueContext | null = null;

  /** Error state */
  error: string | null = null;

  /** Available skills registry */
  skills: SkillDefinition[] = [];

  // ========================================
  // Private State
  // ========================================

  private client: SSEClient | null = null;

  constructor(_rootStore: AIStore) {
    makeAutoObservable(this, {
      // Explicitly mark computed properties
      activeTasks: computed,
      completedTasks: computed,
      conversationContext: computed,
    });
  }

  // ========================================
  // Computed Properties
  // ========================================

  /**
   * Check if currently streaming content.
   */
  get isStreaming(): boolean {
    return this.streamingState.isStreaming;
  }

  /**
   * Get current streaming content.
   */
  get streamContent(): string {
    return this.streamingState.streamContent;
  }

  /**
   * Check if there are unresolved approval requests.
   */
  get hasUnresolvedApprovals(): boolean {
    return this.pendingApprovals.length > 0;
  }

  /**
   * Get active (in-progress) tasks.
   */
  get activeTasks(): TaskState[] {
    return Array.from(this.tasks.values()).filter(
      (task) => task.status === 'pending' || task.status === 'in_progress'
    );
  }

  /**
   * Get completed tasks.
   */
  get completedTasks(): TaskState[] {
    return Array.from(this.tasks.values()).filter((task) => task.status === 'completed');
  }

  /**
   * Build conversation context from current state.
   * Used as input to backend /api/v1/ai/chat endpoint.
   */
  get conversationContext(): ConversationContext {
    return {
      noteId: this.noteContext?.noteId ?? null,
      issueId: this.issueContext?.issueId ?? null,
      projectId: null, // TODO: Extract from workspace context
      selectedText: this.noteContext?.selectedText ?? null,
      selectedBlockIds: this.noteContext?.selectedBlockIds ?? [],
    };
  }

  // ========================================
  // Actions - Message Management
  // ========================================

  /**
   * Add a message to conversation history.
   * @param message - Chat message to add
   */
  addMessage(message: ChatMessage): void {
    this.messages.push(message);
  }

  /**
   * Update streaming state during SSE streaming.
   * @param state - Partial streaming state update
   */
  updateStreamingState(state: Partial<StreamingState>): void {
    Object.assign(this.streamingState, state);
  }

  /**
   * Set session ID for multi-turn conversation.
   * @param sessionId - Session identifier from backend
   */
  setSessionId(sessionId: string | null): void {
    this.sessionId = sessionId;
  }

  // ========================================
  // Actions - Task Management
  // ========================================

  /**
   * Add or update a task.
   * @param taskId - Task identifier
   * @param update - Task state update
   */
  addTask(taskId: string, update: Partial<Omit<TaskState, 'id'>>): void {
    const existing = this.tasks.get(taskId);
    const now = new Date();

    if (existing) {
      this.tasks.set(taskId, {
        ...existing,
        ...update,
        updatedAt: now,
      });
    } else {
      this.tasks.set(taskId, {
        id: taskId,
        subject: update.subject ?? 'Task',
        status: update.status ?? 'pending',
        progress: update.progress ?? 0,
        description: update.description,
        currentStep: update.currentStep,
        totalSteps: update.totalSteps,
        estimatedSecondsRemaining: update.estimatedSecondsRemaining,
        createdAt: now,
        updatedAt: now,
      });
    }
  }

  /**
   * Update task status.
   * @param taskId - Task identifier
   * @param status - New status
   */
  updateTaskStatus(taskId: string, status: TaskStatus): void {
    const task = this.tasks.get(taskId);
    if (task) {
      this.tasks.set(taskId, {
        ...task,
        status,
        updatedAt: new Date(),
      });
    }
  }

  /**
   * Remove a task from tracking.
   * @param taskId - Task identifier
   */
  removeTask(taskId: string): void {
    this.tasks.delete(taskId);
  }

  // ========================================
  // Actions - Approval Management (DD-003)
  // ========================================

  /**
   * Add approval request.
   * @param request - Approval request to add
   */
  addApproval(request: ApprovalRequest): void {
    this.pendingApprovals.push(request);
  }

  /**
   * Approve a pending request.
   * Sends approval to backend and removes from queue.
   *
   * @param requestId - Request identifier
   */
  async approveRequest(requestId: string): Promise<void> {
    const request = this.pendingApprovals.find((r) => r.requestId === requestId);
    if (!request) {
      console.error(`Approval request ${requestId} not found`);
      return;
    }

    try {
      // Send approval to backend via API
      await fetch('/api/v1/ai/approvals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: requestId,
          decision: 'approved',
        }),
      });

      runInAction(() => {
        this.pendingApprovals = this.pendingApprovals.filter((r) => r.requestId !== requestId);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to approve request';
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
    const request = this.pendingApprovals.find((r) => r.requestId === requestId);
    if (!request) {
      console.error(`Approval request ${requestId} not found`);
      return;
    }

    try {
      // Send rejection to backend via API
      await fetch('/api/v1/ai/approvals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: requestId,
          decision: 'rejected',
          reason,
        }),
      });

      runInAction(() => {
        this.pendingApprovals = this.pendingApprovals.filter((r) => r.requestId !== requestId);
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to reject request';
      });
    }
  }

  /**
   * Alias methods to match IPilotSpaceStore interface
   */
  async approveAction(id: string, _modifications?: Record<string, unknown>): Promise<void> {
    // TODO: Handle modifications when modify-before-approve is implemented
    await this.approveRequest(id);
  }

  async rejectAction(id: string, reason: string): Promise<void> {
    await this.rejectRequest(id, reason);
  }

  clearConversation(): void {
    this.clear();
  }

  // ========================================
  // Actions - Context Management
  // ========================================

  /**
   * Set note context for AI operations.
   * @param context - Note context state
   */
  setNoteContext(context: NoteContext | null): void {
    this.noteContext = context;
  }

  /**
   * Set issue context for AI operations.
   * @param context - Issue context state
   */
  setIssueContext(context: IssueContext | null): void {
    this.issueContext = context;
  }

  /**
   * Clear all context.
   */
  clearContext(): void {
    this.noteContext = null;
    this.issueContext = null;
  }

  /**
   * Set project context for AI operations.
   * @param context - Project context state
   */
  setProjectContext(_context: { projectId: string; name?: string; slug?: string } | null): void {
    // TODO: Add projectContext to store state when needed
    // For now, this is a no-op to satisfy the interface
  }

  /**
   * Set active skill for invocation.
   * @param skill - Skill name
   * @param args - Optional skill arguments
   */
  setActiveSkill(skill: string, args?: string): void {
    // TODO: Track active skill in store state when skill system is implemented
    console.log('Setting active skill:', skill, args);
  }

  /**
   * Add mentioned agent to context.
   * @param agent - Agent name
   */
  addMentionedAgent(agent: string): void {
    // TODO: Track mentioned agents in store state when agent mention system is implemented
    console.log('Adding mentioned agent:', agent);
  }

  // ========================================
  // Actions - Message Sending
  // ========================================

  /**
   * Send message to AI and stream response via SSE.
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
    // Create user message
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user' as MessageRole,
      content,
      timestamp: new Date(),
      metadata,
    };

    runInAction(() => {
      this.messages.push(userMessage);
      this.streamingState = {
        isStreaming: true,
        streamContent: '',
        currentMessageId: null,
        phase: 'connecting',
      };
      this.error = null;
    });

    // Create SSE client for streaming response
    this.client = new SSEClient({
      url: '/api/v1/ai/chat',
      body: {
        message: content,
        context: this.conversationContext,
        session_id: this.sessionId,
        metadata,
      },
      onMessage: (event: SSEEvent) => this.handleSSEEvent(event),
      onComplete: () => {
        runInAction(() => {
          this.streamingState = {
            isStreaming: false,
            streamContent: '',
            currentMessageId: null,
          };
        });
      },
      onError: (err) => {
        runInAction(() => {
          this.streamingState = {
            isStreaming: false,
            streamContent: '',
            currentMessageId: null,
          };
          this.error = err.message;
        });
      },
    });

    await this.client.connect();
  }

  // ========================================
  // SSE Event Handlers (T048)
  // ========================================

  /**
   * Handle SSE event from backend.
   * Routes to specific handler based on event type.
   *
   * @param event - SSE event from stream
   */
  private handleSSEEvent(sseEvent: SSEEvent): void {
    runInAction(() => {
      // Cast to our typed event (SSEClient returns generic SSEEvent)
      const event = sseEvent as unknown as
        | MessageStartEvent
        | TextDeltaEvent
        | ToolUseEvent
        | ToolResultEvent
        | TaskProgressEvent
        | ApprovalRequestEvent
        | MessageStopEvent
        | ErrorEvent;

      // Route to type-specific handler
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
  private handleMessageStart(event: MessageStartEvent): void {
    const { messageId, sessionId } = event.data;

    // Update session ID
    this.sessionId = sessionId;

    // Initialize streaming state
    this.streamingState = {
      isStreaming: true,
      streamContent: '',
      currentMessageId: messageId,
      phase: 'message_start',
    };
  }

  /**
   * Handle text_delta event.
   * Appends streaming text chunks.
   */
  private handleTextDelta(event: TextDeltaEvent): void {
    const { delta } = event.data;

    // Accumulate text delta
    this.streamingState.streamContent += delta;
    this.streamingState.phase = 'content';
  }

  /**
   * Handle tool_use event.
   * Records tool invocation.
   */
  private handleToolUseStart(event: ToolUseEvent): void {
    const { toolCallId, toolName, toolInput } = event.data;

    // Create tool call entry
    const toolCall: ToolCall = {
      id: toolCallId,
      name: toolName,
      input: toolInput,
      status: 'pending',
    };

    // Find or create message to attach tool call
    const messageId = this.streamingState.currentMessageId;
    if (messageId) {
      const message = this.messages.find((m) => m.id === messageId);
      if (message) {
        if (!message.toolCalls) {
          message.toolCalls = [];
        }
        message.toolCalls.push(toolCall);
      }
    }

    this.streamingState.phase = 'tool_use';
  }

  /**
   * Handle tool_result event.
   * Updates tool call status and result.
   */
  private handleToolResult(event: ToolResultEvent): void {
    const { toolCallId, status, output, errorMessage } = event.data;

    // Map backend status to ToolCall status
    const toolCallStatus: 'pending' | 'completed' | 'failed' =
      status === 'cancelled' ? 'failed' : status;

    // Find tool call in messages
    for (const message of this.messages) {
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

    this.addTask(taskId, {
      subject,
      status,
      progress,
      description,
      currentStep,
      totalSteps,
      estimatedSecondsRemaining,
    });
  }

  /**
   * Handle approval_request event (DD-003).
   * Adds pending approval request to queue.
   */
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
      confidenceTag,
      createdAt: new Date(),
    };

    this.pendingApprovals.push(request);
  }

  /**
   * Handle message_stop event.
   * Finalizes message and adds to history.
   */
  private handleTextComplete(event: MessageStopEvent): void {
    const { messageId, usage, costUsd } = event.data;

    // Create completed assistant message
    const assistantMessage: ChatMessage = {
      id: messageId,
      role: 'assistant' as MessageRole,
      content: this.streamingState.streamContent,
      timestamp: new Date(),
      metadata: {
        tokenCount: usage?.totalTokens,
        costUsd,
      },
    };

    this.messages.push(assistantMessage);

    // Reset streaming state
    this.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    };
  }

  /**
   * Handle error event.
   * Sets error state and resets streaming.
   */
  private handleError(event: ErrorEvent): void {
    const { errorCode, message, retryable, retryAfter } = event.data;

    this.error = `[${errorCode}] ${message}`;

    // Reset streaming state
    this.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    };

    // TODO: Implement retry logic if retryable === true
    if (retryable && retryAfter) {
      console.log(`Error is retryable. Retry after ${retryAfter}s`);
    }
  }

  // ========================================
  // Lifecycle Actions
  // ========================================

  /**
   * Abort current streaming response.
   */
  abort(): void {
    this.client?.abort();
    this.client = null;

    this.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    };
  }

  /**
   * Clear conversation and reset state.
   */
  clear(): void {
    this.abort();
    this.messages = [];
    this.sessionId = null;
    this.tasks.clear();
    this.pendingApprovals = [];
    this.error = null;
  }

  /**
   * Reset all state (called on workspace change).
   */
  reset(): void {
    this.clear();
    this.clearContext();
    this.skills = [];
  }
}
