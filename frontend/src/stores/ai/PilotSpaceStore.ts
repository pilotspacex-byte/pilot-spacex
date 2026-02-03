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
 * SSE handling extracted to PilotSpaceSSEHandler.ts.
 * Approval/task management extracted to PilotSpaceApprovals.ts.
 *
 * @module stores/ai/PilotSpaceStore
 * @see specs/005-conversational-agent-arch/plan.md (T042-T049)
 */
import { makeAutoObservable, runInAction, computed } from 'mobx';
import type { AIStore } from './AIStore';
import type {
  ChatMessage,
  MessageRole,
  StreamingState,
  ConversationContext,
  MessageMetadata,
} from './types/conversation';
import type { ContentUpdateEvent, TaskStatus } from './types/events';
import type { SkillDefinition, ConfidenceTag } from './types/skills';
import { PilotSpaceSSEHandler } from './PilotSpaceSSEHandler';
import { PilotSpaceApprovals } from './PilotSpaceApprovals';

/**
 * API base URL for backend requests.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/**
 * Task state for long-running operations.
 */
export interface TaskState {
  id: string;
  subject: string;
  status: TaskStatus;
  progress: number;
  description?: string;
  currentStep?: string;
  totalSteps?: number;
  estimatedSecondsRemaining?: number;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Approval request state per DD-003.
 */
export interface ApprovalRequest {
  requestId: string;
  actionType: string;
  description: string;
  consequences?: string;
  affectedEntities: Array<{
    type: string;
    id: string;
    name: string;
    preview?: unknown;
  }>;
  urgency: 'low' | 'medium' | 'high';
  proposedContent?: unknown;
  expiresAt: Date;
  confidenceTag?: ConfidenceTag;
  createdAt: Date;
}

export interface NoteContext {
  noteId: string;
  selectedText?: string;
  selectedBlockIds?: string[];
  noteTitle?: string;
}

export interface IssueContext {
  issueId: string;
  issueTitle?: string;
  issueStatus?: string;
}

/**
 * PilotSpace Store - Unified conversational agent state.
 */
export class PilotSpaceStore {
  // ========================================
  // Observable State
  // ========================================

  messages: ChatMessage[] = [];
  streamingState: StreamingState = {
    isStreaming: false,
    streamContent: '',
    currentMessageId: null,
  };
  sessionId: string | null = null;
  tasks = new Map<string, TaskState>();
  pendingApprovals: ApprovalRequest[] = [];
  pendingContentUpdates: ContentUpdateEvent['data'][] = [];
  noteContext: NoteContext | null = null;
  issueContext: IssueContext | null = null;
  workspaceId: string | null = null;
  error: string | null = null;
  skills: SkillDefinition[] = [];

  // ========================================
  // Delegates
  // ========================================

  private readonly sseHandler: PilotSpaceSSEHandler;
  private readonly approvalsHandler: PilotSpaceApprovals;

  constructor(_rootStore: AIStore) {
    this.sseHandler = new PilotSpaceSSEHandler(this);
    this.approvalsHandler = new PilotSpaceApprovals(this);
    makeAutoObservable(this, {
      activeTasks: computed,
      completedTasks: computed,
      conversationContext: computed,
    });
  }

  // ========================================
  // Computed Properties
  // ========================================

  get isStreaming(): boolean {
    return this.streamingState.isStreaming;
  }

  get streamContent(): string {
    return this.streamingState.streamContent;
  }

  get hasUnresolvedApprovals(): boolean {
    return this.pendingApprovals.length > 0;
  }

  get activeTasks(): TaskState[] {
    return Array.from(this.tasks.values()).filter(
      (task) => task.status === 'pending' || task.status === 'in_progress'
    );
  }

  get completedTasks(): TaskState[] {
    return Array.from(this.tasks.values()).filter((task) => task.status === 'completed');
  }

  get conversationContext(): ConversationContext {
    if (!this.workspaceId) {
      throw new Error('Cannot create conversation context: workspaceId not set');
    }
    return {
      workspaceId: this.workspaceId,
      noteId: this.noteContext?.noteId ?? null,
      issueId: this.issueContext?.issueId ?? null,
      projectId: null,
      selectedText: this.noteContext?.selectedText ?? null,
      selectedBlockIds: this.noteContext?.selectedBlockIds ?? [],
    };
  }

  // ========================================
  // Actions - Message Management
  // ========================================

  addMessage(message: ChatMessage): void {
    this.messages.push(message);
  }

  updateStreamingState(state: Partial<StreamingState>): void {
    Object.assign(this.streamingState, state);
  }

  setSessionId(sessionId: string | null): void {
    this.sessionId = sessionId;
  }

  // ========================================
  // Actions - Task Management (delegated)
  // ========================================

  addTask(taskId: string, update: Partial<Omit<TaskState, 'id'>>): void {
    this.approvalsHandler.addTask(taskId, update);
  }

  updateTaskStatus(taskId: string, status: TaskStatus): void {
    this.approvalsHandler.updateTaskStatus(taskId, status);
  }

  removeTask(taskId: string): void {
    this.approvalsHandler.removeTask(taskId);
  }

  // ========================================
  // Actions - Approval Management (DD-003, delegated)
  // ========================================

  addApproval(request: ApprovalRequest): void {
    this.pendingApprovals.push(request);
  }

  async approveRequest(requestId: string): Promise<void> {
    await this.approvalsHandler.approveRequest(requestId);
  }

  async rejectRequest(requestId: string, reason?: string): Promise<void> {
    await this.approvalsHandler.rejectRequest(requestId, reason);
  }

  async approveAction(id: string, _modifications?: Record<string, unknown>): Promise<void> {
    await this.approveRequest(id);
  }

  async rejectAction(id: string, reason: string): Promise<void> {
    await this.rejectRequest(id, reason);
  }

  clearConversation(): void {
    this.clear();
  }

  // ========================================
  // Actions - Content Update Management
  // ========================================

  handleContentUpdate(event: ContentUpdateEvent): void {
    runInAction(() => {
      if (this.pendingContentUpdates.length >= 100) {
        this.pendingContentUpdates.shift();
      }
      this.pendingContentUpdates.push(event.data);
    });
  }

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

  setWorkspaceId(workspaceId: string | null): void {
    this.workspaceId = workspaceId;
  }

  setNoteContext(context: NoteContext | null): void {
    this.noteContext = context;
  }

  setIssueContext(context: IssueContext | null): void {
    this.issueContext = context;
  }

  clearContext(): void {
    this.noteContext = null;
    this.issueContext = null;
  }

  setProjectContext(_context: { projectId: string; name?: string; slug?: string } | null): void {
    // No-op until projectContext is needed
  }

  setActiveSkill(skill: string, args?: string): void {
    console.log('Setting active skill:', skill, args);
  }

  addMentionedAgent(agent: string): void {
    console.log('Adding mentioned agent:', agent);
  }

  // ========================================
  // Actions - Message Sending
  // ========================================

  async sendMessage(content: string, metadata?: Partial<MessageMetadata>): Promise<void> {
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

    try {
      const authHeaders = await this.sseHandler.getAuthHeaders();

      const response = await fetch(`${API_BASE}/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({
          message: content,
          context: this.conversationContext,
          session_id: this.sessionId,
          metadata,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
      }

      const contentType = response.headers.get('Content-Type') || '';

      if (contentType.includes('application/json')) {
        const queueResponse = await response.json();
        const { session_id, stream_url } = queueResponse;

        if (session_id) {
          runInAction(() => {
            this.sessionId = session_id;
          });
        }

        await this.sseHandler.connectToStream(stream_url);
      } else if (contentType.includes('text/event-stream')) {
        await this.sseHandler.consumeSSEStream(response);
      } else {
        throw new Error(`Unexpected response content type: ${contentType}`);
      }
    } catch (err) {
      runInAction(() => {
        this.streamingState = {
          isStreaming: false,
          streamContent: '',
          currentMessageId: null,
        };
        this.error = err instanceof Error ? err.message : 'Failed to send message';
      });
    }
  }

  // ========================================
  // Lifecycle Actions
  // ========================================

  abort(): void {
    if (this.sessionId) {
      fetch(`${API_BASE}/ai/chat/abort`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.sessionId }),
      }).catch(() => {
        // Ignore - SSE disconnect triggers cleanup
      });
    }

    this.sseHandler.abort();

    this.streamingState = {
      isStreaming: false,
      streamContent: '',
      currentMessageId: null,
    };
  }

  clear(): void {
    this.abort();
    this.messages = [];
    this.sessionId = null;
    this.tasks.clear();
    this.pendingApprovals = [];
    this.pendingContentUpdates = [];
    this.error = null;
  }

  reset(): void {
    this.clear();
    this.clearContext();
    this.workspaceId = null;
    this.skills = [];
  }
}
