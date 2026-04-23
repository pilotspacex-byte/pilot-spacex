/**
 * PilotSpace Store - Unified conversational agent state management.
 * Stream handling → PilotSpaceStreamHandler. Actions → PilotSpaceActions.
 * @module stores/ai/PilotSpaceStore
 */
import { makeAutoObservable, runInAction, computed } from 'mobx';

/** Monotonic counter for generating unique skill message IDs within the same millisecond. */
let _skillMsgCounter = 0;
import type { AIStore } from './AIStore';
import type {
  ChatMessage,
  ToolCall,
  StreamingState,
  SessionState,
  ConversationContext,
  MessageMetadata,
} from './types/conversation';
import type { MemoryUpdateEvent } from './types/events';
import type {
  ContentUpdateEvent,
  AgentQuestion,
  QuestionRequestEvent,
  TaskStatus,
  SkillPreviewEvent,
  TestResultEvent,
  SkillSavedEvent,
} from './types/events';
import type { SkillDefinition } from './types/skills';
import { PilotSpaceStreamHandler } from './PilotSpaceStreamHandler';
import { PilotSpaceActions } from './PilotSpaceActions';

// Interfaces extracted to types/store-types.ts to keep this file under 700 lines.
import type {
  TaskState,
  ApprovalRequest,
  NoteContext,
  IssueContext,
  HomepageContextData,
} from './types/store-types';
export type {
  TaskState,
  ApprovalRequest,
  NoteContext,
  IssueContext,
  HomepageContextData,
} from './types/store-types';

/**
 * PilotSpace Store - Unified conversational agent state.
 */
export class PilotSpaceStore {
  // Observable State

  messages: ChatMessage[] = [];
  streamingState: StreamingState = {
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
  sessionId: string | null = null;

  /** Session state for token budget tracking (008) */
  sessionState: SessionState = {
    sessionId: null,
    isActive: false,
    createdAt: null,
    lastActivityAt: null,
  };

  /** Session ID to fork from (set by prepareFork, consumed on next sendMessage) */
  forkSessionId: string | null = null;

  /** Long-running tasks */
  tasks = new Map<string, TaskState>();
  pendingApprovals: ApprovalRequest[] = [];
  pendingContentUpdates: ContentUpdateEvent['data'][] = [];
  noteContext: NoteContext | null = null;
  issueContext: IssueContext | null = null;
  homepageContext: HomepageContextData | null = null;
  /** Current project context */
  projectContext: { projectId: string; name?: string; slug?: string } | null = null;

  /** Active skill for invocation (consumed on next sendMessage) */
  activeSkill: { name: string; args?: string } | null = null;

  /** Mentioned agents in current input (consumed on next sendMessage) */
  mentionedAgents: string[] = [];

  /** Current workspace ID */
  workspaceId: string | null = null;
  error: string | null = null;

  /** Per-session model selection — persisted to localStorage per workspace (13-04) */
  selectedModel: { provider: string; modelId: string; configId: string } | null = null;

  /** Block IDs targeted by pending AI tool calls (set on tool_use, cleared on content_update) */
  pendingAIBlockIds: string[] = [];

  /** Signal to scroll to end of note (set by write_to_note tool_use, consumed by useContentUpdates) */
  pendingNoteEndScroll = false;

  /** Pending structured result (set by structured_result event, consumed by message_stop) */
  private pendingStructuredResult: { schemaType: string; data: Record<string, unknown> } | null =
    null;

  /** Pending tool calls buffered during streaming (T63 — consumed by message_stop) */
  private _pendingToolCalls: ToolCall[] = [];

  /** Pending citations buffered during streaming (T64 — consumed by message_stop) */
  private _pendingCitations: ChatMessage['citations'] = [];

  /** Phase 69: Pending memory sources buffered from `memory_used` SSE event. */
  private _pendingMemorySources: ChatMessage['memorySources'] = [];

  /** Last memory update from cross-session memory tool (T73) */
  lastMemoryUpdate: MemoryUpdateEvent['data'] | null = null;

  /** Pending question from agent (requires user response before agent can continue) */
  pendingQuestion: {
    questionId: string;
    questions: AgentQuestion[];
  } | null = null;

  /** Guard: prevents duplicate answer submissions while one is in flight */
  isSubmittingAnswer = false;

  /** Available skills registry */
  skills: SkillDefinition[] = [];

  // Phase 64: Chat-first skill refinement state

  /** Current skill being created/edited in chat (set by skill_preview event) */
  skillPreview: SkillPreviewEvent['data'] | null = null;

  /** Latest test result for skill being refined (set by test_result event) */
  skillTestResult: TestResultEvent['data'] | null = null;

  /** Last saved skill confirmation (set by skill_saved event, triggers save flow) */
  skillSavedConfirmation: SkillSavedEvent['data'] | null = null;

  // Message Pagination State (scroll-up loading)

  /** Total messages in the resumed session (for pagination calculation) */
  totalMessages: number = 0;

  /** Whether older messages exist (for scroll-up loading) */
  hasMoreMessages: boolean = false;

  /** Loading state for fetching older messages */
  isLoadingMoreMessages: boolean = false;

  // Delegates

  private readonly streamHandler: PilotSpaceStreamHandler;
  private readonly actions: PilotSpaceActions;

  constructor(_rootStore: AIStore) {
    this.streamHandler = new PilotSpaceStreamHandler(this);
    this.actions = new PilotSpaceActions(this, this.streamHandler);

    makeAutoObservable(this, {
      activeTasks: computed,
      completedTasks: computed,
      conversationContext: computed,
      tokenBudgetPercent: computed,
      isWaitingForUser: computed,
    });
  }

  // Computed Properties

  get isStreaming(): boolean {
    return this.streamingState.isStreaming;
  }

  get streamContent(): string {
    return this.streamingState.streamContent;
  }

  /** Pending tool calls visible during streaming (for StreamingContent rendering). */
  get pendingToolCalls(): ToolCall[] {
    return this._pendingToolCalls;
  }

  get hasUnresolvedApprovals(): boolean {
    return this.pendingApprovals.length > 0;
  }

  get agentTaskList(): TaskState[] {
    return Array.from(this.tasks.values());
  }

  get activeTasks(): TaskState[] {
    return Array.from(this.tasks.values()).filter(
      (task) => task.status === 'pending' || task.status === 'in_progress'
    );
  }

  get completedTasks(): TaskState[] {
    return Array.from(this.tasks.values()).filter((task) => task.status === 'completed');
  }

  get conversationContext(): ConversationContext | null {
    if (!this.workspaceId) {
      return null;
    }
    return {
      workspaceId: this.workspaceId,
      noteId: this.noteContext?.noteId ?? null,
      issueId: this.issueContext?.issueId ?? null,
      projectId: this.projectContext?.projectId ?? null,
      selectedText: this.noteContext?.selectedText ?? null,
      selectedBlockIds: this.noteContext?.selectedBlockIds ?? [],
      homepageDigestSummary: this.homepageContext?.digestSummary ?? undefined,
    };
  }

  /** Token budget usage as percentage (0-100) based on 8K token limit (008). */
  get tokenBudgetPercent(): number {
    return ((this.sessionState.totalTokens ?? 0) / 8000) * 100;
  }

  /** True when the agent is waiting for user input (pending question or unresolved approval). */
  get isWaitingForUser(): boolean {
    return this.pendingQuestion !== null || this.hasUnresolvedApprovals;
  }

  // Actions - Message Management

  addMessage(message: ChatMessage): void {
    this.messages.push(message);
  }

  /** Prepend older messages for scroll-up loading when resuming sessions. */
  prependMessages(messages: ChatMessage[]): void {
    this.messages = [...messages, ...this.messages];
  }

  /** Update pagination state after loading messages. */
  setMessagePaginationState(hasMore: boolean, total: number): void {
    this.hasMoreMessages = hasMore;
    this.totalMessages = total;
  }

  /** Set loading state for fetching older messages. */
  setIsLoadingMoreMessages(loading: boolean): void {
    this.isLoadingMoreMessages = loading;
  }

  updateStreamingState(state: Partial<StreamingState>): void {
    this.streamingState = { ...this.streamingState, ...state };
  }

  setSessionId(sessionId: string | null): void {
    this.sessionId = sessionId;
  }

  /** Set fork session ID for "what-if" exploration (consumed on next sendMessage). */
  setForkSessionId(forkSessionId: string | null): void {
    this.forkSessionId = forkSessionId;
  }

  // Actions - Task Management (delegated)

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

  updateTaskStatus(taskId: string, status: TaskStatus): void {
    const task = this.tasks.get(taskId);
    if (task) {
      task.status = status;
      task.updatedAt = new Date();
    }
  }

  removeTask(taskId: string): void {
    this.tasks.delete(taskId);
  }

  // Actions - Approval Management (DD-003, delegated)

  addApproval(request: ApprovalRequest): void {
    this.pendingApprovals.push(request);
  }

  async approveRequest(requestId: string): Promise<void> {
    return this.actions.approveRequest(requestId);
  }

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

  removePendingApproval(requestId: string): void {
    this.pendingApprovals = this.pendingApprovals.filter((r) => r.requestId !== requestId);
  }

  clearConversation(): void {
    this.clear();
  }

  // Actions - Structured Result Management

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

  // Actions - Pending Tool Call Buffer (T63)

  /** Buffer a tool call during streaming (attached to assistant message on message_stop). */
  addPendingToolCall(tc: ToolCall): void {
    this._pendingToolCalls.push(tc);
  }

  /** Find a pending tool call by ID. */
  findPendingToolCall(toolUseId: string): ToolCall | undefined {
    return this._pendingToolCalls.find((tc) => tc.id === toolUseId);
  }

  /** Consume and clear all pending tool calls (called on message_stop). */
  consumePendingToolCalls(): ToolCall[] | undefined {
    if (this._pendingToolCalls.length === 0) return undefined;
    const calls = [...this._pendingToolCalls];
    this._pendingToolCalls = [];
    return calls;
  }

  // Actions - Pending Citation Buffer (T64)

  /** Buffer citations during streaming (citations arrive before message_stop). */
  addPendingCitations(citations: NonNullable<ChatMessage['citations']>): void {
    this._pendingCitations = [...(this._pendingCitations ?? []), ...citations];
  }

  /** Consume and clear all pending citations (called on message_stop). */
  consumePendingCitations(): ChatMessage['citations'] | undefined {
    if (!this._pendingCitations || this._pendingCitations.length === 0) return undefined;
    const citations = this._pendingCitations;
    this._pendingCitations = [];
    return citations;
  }

  /** Phase 69: Append memory sources from a `memory_used` SSE event. */
  addPendingMemorySources(
    sources: NonNullable<ChatMessage['memorySources']>
  ): void {
    this._pendingMemorySources = [...(this._pendingMemorySources ?? []), ...sources];
  }

  /** Consume and clear all pending memory sources (called on message_stop). */
  consumePendingMemorySources(): ChatMessage['memorySources'] | undefined {
    if (!this._pendingMemorySources || this._pendingMemorySources.length === 0) return undefined;
    const sources = this._pendingMemorySources;
    this._pendingMemorySources = [];
    return sources;
  }

  // Actions - Pending AI Block IDs (tool_use → auto-scroll)

  addPendingAIBlockId(blockId: string): void {
    if (!this.pendingAIBlockIds.includes(blockId)) {
      this.pendingAIBlockIds.push(blockId);
    }
  }

  removePendingAIBlockId(blockId: string): void {
    this.pendingAIBlockIds = this.pendingAIBlockIds.filter((id) => id !== blockId);
  }

  requestNoteEndScroll(): void {
    this.pendingNoteEndScroll = true;
  }

  clearNoteEndScroll(): void {
    this.pendingNoteEndScroll = false;
  }

  // Actions - Content Update Management

  handleContentUpdate(event: ContentUpdateEvent): void {
    const data = event.data as { operation?: string; issueId?: string };
    if (data.operation === 'issue_updated') {
      window?.dispatchEvent(
        new CustomEvent('pilot:issue-updated', { detail: { issueId: data.issueId } })
      );
      return;
    }
    runInAction(() => {
      if (this.pendingContentUpdates.length >= 100) this.pendingContentUpdates.shift();
      this.pendingContentUpdates.push(event.data);
    });
  }

  // Phase 64: Skill Event Handlers

  /**
   * Handle skill_preview SSE event.
   * Updates skillPreview observable and appends a system message so
   * the MessageList can render a SkillPreviewCard inline in ChatView.
   */
  handleSkillPreview(event: SkillPreviewEvent): void {
    this.skillPreview = event.data;
    this.messages.push({
      id: `skill_preview_${Date.now()}_${++_skillMsgCounter}`,
      role: 'system',
      content: '',
      timestamp: new Date(),
      structuredResult: {
        schemaType: 'skill_preview',
        data: event.data as unknown as Record<string, unknown>,
      },
    });
  }

  /**
   * Handle test_result SSE event.
   * Updates skillTestResult observable and appends a system message so
   * the MessageList can render a TestResultCard inline in ChatView.
   */
  handleTestResult(event: TestResultEvent): void {
    this.skillTestResult = event.data;
    this.messages.push({
      id: `test_result_${Date.now()}_${++_skillMsgCounter}`,
      role: 'system',
      content: '',
      timestamp: new Date(),
      structuredResult: {
        schemaType: 'test_result',
        data: event.data as unknown as Record<string, unknown>,
      },
    });
  }

  /**
   * Handle skill_saved SSE event.
   * Updates skillSavedConfirmation and clears in-progress skill preview/test state.
   * The confirmation message is embedded in the next assistant message_stop.
   */
  handleSkillSaved(event: SkillSavedEvent): void {
    this.skillSavedConfirmation = event.data;
    // Clear in-progress skill state — the skill is now persisted
    this.skillPreview = null;
    this.skillTestResult = null;
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

  // Actions - Question Management

  /**
   * Handle incoming question_request SSE event.
   * Sets pending question and pauses streaming state to indicate waiting for user.
   */
  handleQuestionRequest(event: QuestionRequestEvent): void {
    this.pendingQuestion = {
      questionId: event.data.questionId,
      questions: event.data.questions,
    };
    this.updateStreamingState({ phase: 'waiting_for_user' });
  }

  /**
   * Resolve a pending question: update the assistant message's questionData with answers
   * and clear the pending question state.
   */
  resolveQuestion(questionId: string, answers: Record<string, string>): void {
    // Update the assistant message that contains this question.
    // Search questionDataList first (new multi-question format), then questionData (legacy).
    const idx = this.messages.findLastIndex(
      (m) =>
        m.role === 'assistant' &&
        (m.questionDataList?.some((qd) => qd.questionId === questionId) ||
          m.questionData?.questionId === questionId)
    );
    if (idx >= 0) {
      const msg = this.messages[idx]!;
      if (msg.questionDataList) {
        // Resolve all entries in questionDataList with the merged answers
        this.messages[idx] = {
          ...msg,
          questionDataList: msg.questionDataList.map((qd) => ({
            ...qd,
            answers: qd.questionId === questionId ? answers : qd.answers,
          })),
          questionData: msg.questionData ? { ...msg.questionData, answers } : undefined,
        };
      } else if (msg.questionData) {
        this.messages[idx] = {
          ...msg,
          questionData: { ...msg.questionData, answers },
        };
      }
    } else {
      console.warn(`resolveQuestion: no assistant message found with questionId=${questionId}`);
    }
    // Clear pending question state
    this.pendingQuestion = null;
  }

  /**
   * Clear pending question after user submits an answer or dismisses.
   */
  clearPendingQuestion(): void {
    this.pendingQuestion = null;
  }

  // Actions - Context Management

  setWorkspaceId(workspaceId: string | null): void {
    this.workspaceId = workspaceId;
    if (workspaceId) {
      this.loadSelectedModel(workspaceId);
    }
  }

  /** Persist model selection to localStorage key chat_model_{workspaceId}. (13-04) */
  setSelectedModel(provider: string, modelId: string, configId: string): void {
    this.selectedModel = { provider, modelId, configId };
    const wsId = this.workspaceId;
    if (wsId) {
      try {
        localStorage.setItem(`chat_model_${wsId}`, JSON.stringify({ provider, modelId, configId }));
      } catch {
        /* quota / private browsing */
      }
    }
  }

  /** Restore persisted model selection on workspace switch. (13-04) */
  loadSelectedModel(workspaceId: string): void {
    try {
      const raw = localStorage.getItem(`chat_model_${workspaceId}`);
      if (raw) {
        const parsed = JSON.parse(raw) as Record<string, unknown>;
        if (parsed.provider && parsed.modelId && parsed.configId) {
          this.selectedModel = {
            provider: parsed.provider as string,
            modelId: parsed.modelId as string,
            configId: parsed.configId as string,
          };
          return;
        }
      }
    } catch {
      /* invalid JSON */
    }
    this.selectedModel = null;
  }

  setNoteContext(context: NoteContext | null): void {
    this.noteContext = context;
    if (context) this.homepageContext = null;
  }

  setIssueContext(context: IssueContext | null): void {
    this.issueContext = context;
  }

  setHomepageContext(data: HomepageContextData): void {
    this.homepageContext = data;
    this.noteContext = null;
  }

  clearHomepageContext(): void {
    this.homepageContext = null;
  }

  clearContext(): void {
    this.noteContext = null;
    this.issueContext = null;
    this.homepageContext = null;
    this.projectContext = null;
    this.activeSkill = null;
    this.mentionedAgents = [];
  }

  setProjectContext(context: { projectId: string; name?: string; slug?: string } | null): void {
    this.projectContext = context;
  }

  setActiveSkill(skill: string, args?: string): void {
    this.activeSkill = { name: skill, args };
  }

  addMentionedAgent(agent: string): void {
    if (!this.mentionedAgents.includes(agent)) {
      this.mentionedAgents.push(agent);
    }
  }

  // Delegated Actions (Message Sending + Lifecycle)

  /**
   * Send message to AI and stream response via SSE.
   *
   * @param content - User message content
   * @param metadata - Optional message metadata (skill invocation, agent mention)
   * @param attachmentIds - Optional server-assigned attachment IDs to include in context
   */
  async sendMessage(
    content: string,
    metadata?: Partial<MessageMetadata>,
    attachmentIds?: string[]
  ): Promise<void> {
    return this.actions.sendMessage(content, metadata, attachmentIds);
  }

  /**
   * Submit an answer to a pending agent question.
   *
   * @param questionId - Question identifier (tool call ID)
   * @param answer - User's answer text
   */
  async submitQuestionAnswer(
    questionId: string,
    answer: string,
    answersRecord?: Record<string, string>
  ): Promise<void> {
    return this.actions.submitQuestionAnswer(questionId, answer, answersRecord);
  }

  /**
   * Abort current streaming response.
   */
  abort(): void {
    this.streamingState.interrupted = true;
    this.actions.abort();
  }

  clear(): void {
    this.actions.clear();
  }

  reset(): void {
    this.actions.reset();
  }
}
