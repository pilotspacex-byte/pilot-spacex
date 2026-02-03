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
 * Stream handling delegated to PilotSpaceStreamHandler.
 * User-facing async actions delegated to PilotSpaceActions.
 *
 * @module stores/ai/PilotSpaceStore
 * @see specs/005-conversational-agent-arch/plan.md (T042-T049)
 */
import { makeAutoObservable, runInAction, computed } from 'mobx';
import type { AIStore } from './AIStore';
import type {
  ChatMessage,
  StreamingState,
  ConversationContext,
  MessageMetadata,
} from './types/conversation';
import type { ContentUpdateEvent, AgentQuestion, TaskStatus } from './types/events';
import type { SkillDefinition, ConfidenceTag } from './types/skills';
import { PilotSpaceStreamHandler } from './PilotSpaceStreamHandler';
import { PilotSpaceActions } from './PilotSpaceActions';

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
  /** Subagent name executing this task */
  agentName?: string;
  /** AI model used by this subagent */
  model?: string;
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
    thinkingContent: '',
    isThinking: false,
    thinkingStartedAt: null,
  };

  /** Current session ID for multi-turn context */
  sessionId: string | null = null;

  /** Session ID to fork from (set by prepareFork, consumed on next sendMessage) */
  forkSessionId: string | null = null;

  /** Long-running tasks */
  tasks = new Map<string, TaskState>();

  /** Pending approval requests */
  pendingApprovals: ApprovalRequest[] = [];

  /** Pending content updates from AI (FIFO buffer, max 100) */
  pendingContentUpdates: ContentUpdateEvent['data'][] = [];

  /** Current note context */
  noteContext: NoteContext | null = null;

  /** Current issue context */
  issueContext: IssueContext | null = null;

  /** Current project context */
  projectContext: { projectId: string; name?: string; slug?: string } | null = null;

  /** Active skill for invocation (consumed on next sendMessage) */
  activeSkill: { name: string; args?: string } | null = null;

  /** Mentioned agents in current input (consumed on next sendMessage) */
  mentionedAgents: string[] = [];

  /** Current workspace ID */
  workspaceId: string | null = null;

  /** Error state */
  error: string | null = null;

  /** Pending structured result (set by structured_result event, consumed by message_stop) */
  private pendingStructuredResult: { schemaType: string; data: Record<string, unknown> } | null =
    null;

  /** Pending question from agent (requires user response before agent can continue) */
  pendingQuestion: {
    questionId: string;
    questions: AgentQuestion[];
    resolvedAnswer?: string;
  } | null = null;

  /** Available skills registry */
  skills: SkillDefinition[] = [];

  // ========================================
  // Delegates
  // ========================================

  private readonly streamHandler: PilotSpaceStreamHandler;
  private readonly actions: PilotSpaceActions;

  constructor(_rootStore: AIStore) {
    this.streamHandler = new PilotSpaceStreamHandler(this);
    this.actions = new PilotSpaceActions(this, this.streamHandler);

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
    if (!this.workspaceId) {
      throw new Error('Cannot create conversation context: workspaceId not set');
    }

    return {
      workspaceId: this.workspaceId,
      noteId: this.noteContext?.noteId ?? null,
      issueId: this.issueContext?.issueId ?? null,
      projectId: this.projectContext?.projectId ?? null,
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

  /**
   * Set fork session ID for "what-if" exploration.
   * The next sendMessage will include this in the request body.
   * @param forkSessionId - Source session to fork from
   */
  setForkSessionId(forkSessionId: string | null): void {
    this.forkSessionId = forkSessionId;
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
        agentName: update.agentName,
        model: update.model,
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
    return this.actions.approveRequest(requestId);
  }

  /**
   * Reject a pending request.
   * Sends rejection to backend and removes from queue.
   *
   * @param requestId - Request identifier
   * @param reason - Optional rejection reason
   */
  async rejectRequest(requestId: string, reason?: string): Promise<void> {
    return this.actions.rejectRequest(requestId, reason);
  }

  /**
   * Alias methods to match IPilotSpaceStore interface
   */
  async approveAction(id: string, modifications?: Record<string, unknown>): Promise<void> {
    return this.actions.approveAction(id, modifications);
  }

  async rejectAction(id: string, reason: string): Promise<void> {
    return this.actions.rejectAction(id, reason);
  }

  clearConversation(): void {
    this.clear();
  }

  // ========================================
  // Actions - Structured Result Management
  // ========================================

  /**
   * Set pending structured result (called by stream handler).
   * @param result - Structured result data
   */
  setPendingStructuredResult(
    result: { schemaType: string; data: Record<string, unknown> } | null
  ): void {
    this.pendingStructuredResult = result;
  }

  /**
   * Consume pending structured result (called by stream handler on message_stop).
   * Returns and clears the pending result.
   */
  consumePendingStructuredResult():
    | { schemaType: string; data: Record<string, unknown> }
    | undefined {
    const result = this.pendingStructuredResult ?? undefined;
    this.pendingStructuredResult = null;
    return result;
  }

  // ========================================
  // Actions - Content Update Management
  // ========================================

  /**
   * Handle content_update event from AI.
   * Adds to pending updates buffer (max 100, FIFO eviction).
   *
   * @param event - Content update event
   */
  handleContentUpdate(event: ContentUpdateEvent): void {
    runInAction(() => {
      // FIFO buffer, max 100
      if (this.pendingContentUpdates.length >= 100) {
        this.pendingContentUpdates.shift();
      }
      this.pendingContentUpdates.push(event.data);
    });
  }

  /**
   * Consume (remove) a pending content update for a specific note.
   * Returns the first matching update and removes it from the queue.
   *
   * @param noteId - Note ID to find update for
   * @returns Content update event data or undefined if not found
   */
  consumeContentUpdate(noteId: string): ContentUpdateEvent['data'] | undefined {
    return runInAction(() => {
      const idx = this.pendingContentUpdates.findIndex((u) => u.noteId === noteId);
      if (idx >= 0) {
        return this.pendingContentUpdates.splice(idx, 1)[0];
      }
      return undefined;
    });
  }

  // ========================================
  // Actions - Context Management
  // ========================================

  /**
   * Set workspace ID for AI operations.
   * Required before sending messages.
   * @param workspaceId - Workspace UUID
   */
  setWorkspaceId(workspaceId: string | null): void {
    this.workspaceId = workspaceId;
  }

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
    this.projectContext = null;
    this.activeSkill = null;
    this.mentionedAgents = [];
  }

  /**
   * Set project context for AI operations.
   * @param context - Project context state
   */
  setProjectContext(context: { projectId: string; name?: string; slug?: string } | null): void {
    this.projectContext = context;
  }

  /**
   * Set active skill for invocation.
   * @param skill - Skill name
   * @param args - Optional skill arguments
   */
  setActiveSkill(skill: string, args?: string): void {
    this.activeSkill = { name: skill, args };
  }

  /**
   * Add mentioned agent to context.
   * @param agent - Agent name
   */
  addMentionedAgent(agent: string): void {
    if (!this.mentionedAgents.includes(agent)) {
      this.mentionedAgents.push(agent);
    }
  }

  // ========================================
  // Delegated Actions (Message Sending + Lifecycle)
  // ========================================

  /**
   * Send message to AI and stream response via SSE.
   *
   * @param content - User message content
   * @param metadata - Optional message metadata (skill invocation, agent mention)
   */
  async sendMessage(content: string, metadata?: Partial<MessageMetadata>): Promise<void> {
    return this.actions.sendMessage(content, metadata);
  }

  /**
   * Submit an answer to a pending agent question.
   *
   * @param questionId - Question identifier (tool call ID)
   * @param answer - User's answer text
   */
  async submitQuestionAnswer(questionId: string, answer: string): Promise<void> {
    return this.actions.submitQuestionAnswer(questionId, answer);
  }

  /**
   * Abort current streaming response.
   */
  abort(): void {
    this.actions.abort();
  }

  /**
   * Clear conversation and reset state.
   */
  clear(): void {
    this.actions.clear();
  }

  /**
   * Reset all state (called on workspace change).
   */
  reset(): void {
    this.actions.reset();
  }
}
