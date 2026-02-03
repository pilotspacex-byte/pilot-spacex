/**
 * SSE event types for PilotSpaceStore.
 * Maps to backend SSE stream events from `/api/v1/ai/chat`.
 *
 * These types define the structure of Server-Sent Events (SSE) streamed
 * from the backend AI orchestrator during conversational interactions.
 *
 * @module stores/ai/types/events
 * @see backend/src/pilot_space/ai/sdk_orchestrator.py
 */

import type { ConfidenceTag } from './skills';

/**
 * SSE event type discriminator.
 * Maps to `event:` field in SSE protocol.
 */
export type SSEEventType =
  | 'message_start'
  | 'content_block_start'
  | 'text_delta'
  | 'thinking_delta'
  | 'tool_use'
  | 'tool_result'
  | 'task_progress'
  | 'approval_request'
  | 'ask_user_question'
  | 'content_update'
  | 'structured_result'
  | 'message_stop'
  | 'budget_warning'
  | 'tool_audit'
  | 'citation'
  | 'memory_update'
  | 'tool_input_delta'
  | 'error';

/**
 * Base SSE event structure.
 * Parsed from SSE `event:` and `data:` fields.
 * All specific event types extend this base.
 */
export interface SSEEvent {
  /** Event type discriminator */
  type: SSEEventType;
  /** Event payload (type-specific) */
  data: unknown;
}

/**
 * Message start event.
 * Signals the beginning of a new assistant message.
 */
export interface MessageStartEvent extends SSEEvent {
  type: 'message_start';
  data: {
    /** Unique message identifier (UUIDv4) */
    messageId: string;
    /** Session identifier for multi-turn context */
    sessionId: string;
    /** AI model being used */
    model?: string;
  };
}

/**
 * Content block start event.
 * Indicates a new content block (text or tool use) is starting.
 */
export interface ContentBlockStartEvent extends SSEEvent {
  type: 'content_block_start';
  data: {
    /** Content block index (0-based) */
    index: number;
    /** Content block type */
    contentType: 'text' | 'tool_use';
    /** Parent tool use ID for subagent content correlation (G12) */
    parentToolUseId?: string;
  };
}

/**
 * Text delta event.
 * Streamed text content chunk for progressive rendering.
 */
export interface TextDeltaEvent extends SSEEvent {
  type: 'text_delta';
  data: {
    /** Message ID this delta belongs to */
    messageId: string;
    /** Text content chunk (append to existing content) */
    delta: string;
    /** Content block index (for multi-block messages) */
    index?: number;
  };
}

/**
 * Thinking delta event.
 * Streamed extended thinking content from Claude (Opus tasks).
 * Rendered in a collapsible "Agent Reasoning" block.
 */
export interface ThinkingDeltaEvent extends SSEEvent {
  type: 'thinking_delta';
  data: {
    /** Message ID this thinking belongs to */
    messageId: string;
    /** Thinking content chunk (append to existing thinking content) */
    delta: string;
  };
}

/**
 * Tool use event.
 * AI agent is invoking a tool (MCP tool, database query, API call).
 */
export interface ToolUseEvent extends SSEEvent {
  type: 'tool_use';
  data: {
    /** Unique tool call identifier */
    toolCallId: string;
    /** Tool name (MCP registry name) */
    toolName: string;
    /** Tool input parameters */
    toolInput: Record<string, unknown>;
    /** Content block index */
    index?: number;
  };
}

/**
 * Tool result event.
 * Result of tool execution.
 */
export interface ToolResultEvent extends SSEEvent {
  type: 'tool_result';
  data: {
    /** Tool call identifier (matches ToolUseEvent.toolCallId) */
    toolCallId: string;
    /** Tool execution status */
    status: 'completed' | 'failed' | 'cancelled';
    /** Tool output (tool-specific structure) */
    output?: unknown;
    /** Error message if status is 'failed' */
    errorMessage?: string;
    /** Execution duration in milliseconds */
    duration?: number;
  };
}

/**
 * Task progress event.
 * Long-running task progress update (e.g., PR review, issue extraction).
 */
export interface TaskProgressEvent extends SSEEvent {
  type: 'task_progress';
  data: {
    /** Task identifier */
    taskId: string;
    /** Human-readable task description */
    subject: string;
    /** Current task status */
    status: TaskStatus;
    /** Progress percentage (0-100) */
    progress: number;
    /** Detailed progress description */
    description?: string;
    /** Current step (e.g., "Analyzing code", "Generating report") */
    currentStep?: string;
    /** Total steps */
    totalSteps?: number;
    /** Estimated time remaining in seconds */
    estimatedSecondsRemaining?: number;
    /** Subagent name executing this task */
    agentName?: string;
    /** AI model used by this subagent */
    model?: string;
  };
}

/**
 * Task status for progress tracking.
 */
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'blocked';

/**
 * Approval request event (DD-003 Human-in-the-Loop).
 * AI agent requires user approval before executing an action.
 */
export interface ApprovalRequestEvent extends SSEEvent {
  type: 'approval_request';
  data: {
    /** Unique approval request identifier */
    requestId: string;
    /** Action type requiring approval */
    actionType: ApprovalActionType;
    /** Human-readable action description */
    description: string;
    /** Consequences of approving this action */
    consequences?: string;
    /** Entities affected by this action */
    affectedEntities: AffectedEntity[];
    /** Approval urgency level */
    urgency: ApprovalUrgency;
    /** Proposed content (for preview) */
    proposedContent?: unknown;
    /** Expiration timestamp (ISO 8601) */
    expiresAt: string;
    /** Confidence tag for AI recommendation */
    confidenceTag?: ConfidenceTag;
  };
}

/**
 * Action types requiring approval per DD-003.
 */
export type ApprovalActionType =
  | 'create_issue'
  | 'create_issues_bulk'
  | 'modify_issue'
  | 'delete_issue'
  | 'modify_file'
  | 'delete_entity'
  | 'bulk_operation'
  | 'external_api_call';

/**
 * Approval urgency level.
 */
export type ApprovalUrgency = 'low' | 'medium' | 'high';

/**
 * Entity affected by approval action.
 */
export interface AffectedEntity {
  /** Entity type */
  type: 'issue' | 'note' | 'file' | 'project' | 'cycle' | 'module';
  /** Entity identifier */
  id: string;
  /** Entity name for display */
  name: string;
  /** Preview data (entity-specific structure) */
  preview?: unknown;
}

/**
 * Question option for AskUserQuestion.
 */
export interface QuestionOption {
  /** Display label */
  label: string;
  /** Description of this option */
  description?: string;
}

/**
 * Question from AI agent needing user input.
 */
export interface AgentQuestion {
  /** Question text */
  question: string;
  /** Available options */
  options: QuestionOption[];
  /** Whether multiple options can be selected */
  multiSelect: boolean;
  /** Short header label */
  header?: string;
}

/**
 * Ask user question event.
 * AI agent needs clarification during execution.
 * Frontend renders inline QuestionCard for user response.
 */
export interface AskUserQuestionEvent extends SSEEvent {
  type: 'ask_user_question';
  data: {
    /** Message ID this question belongs to */
    messageId: string;
    /** Question ID (tool call ID, used to submit answer) */
    questionId: string;
    /** Questions to display */
    questions: AgentQuestion[];
  };
}

/**
 * Content update event data.
 * Data payload for content_update SSE event.
 */
export interface ContentUpdateData {
  /** Note ID to update */
  noteId: string;
  /** Update operation type */
  operation: 'replace_block' | 'append_blocks' | 'insert_inline_issue';
  /** Block ID for replace_block operation (null for other operations) */
  blockId: string | null;
  /** Markdown content from AI agent (preferred over JSONContent) */
  markdown: string | null;
  /** TipTap JSONContent for block content (fallback, null for insert_inline_issue) */
  content: Record<string, unknown> | null;
  /** Issue data for insert_inline_issue operation (null for other operations) */
  issueData: {
    /** Issue identifier (optional — created by frontend if missing) */
    issueId?: string;
    /** Issue key e.g. PROJ-42 (optional — created by frontend if missing) */
    issueKey?: string;
    /** Issue title */
    title: string;
    /** Issue description (optional — used when creating issue) */
    description?: string;
    /** Issue type */
    type?: 'bug' | 'improvement' | 'feature' | 'task';
    /** Issue state */
    state?: 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled';
    /** Issue priority */
    priority?: 'urgent' | 'high' | 'medium' | 'low' | 'none';
    /** Source block ID where issue was extracted from */
    sourceBlockId?: string;
  } | null;
  /** Block ID to insert after (for append_blocks operation) */
  afterBlockId: string | null;
}

/**
 * Content update event.
 * AI agent proposing content changes to a note.
 * Used for block replacement, appending blocks, or inserting inline issues.
 */
export interface ContentUpdateEvent extends SSEEvent {
  type: 'content_update';
  data: ContentUpdateData;
}

/**
 * Structured result schema type discriminator.
 * Maps to backend output_schemas.py Pydantic models.
 */
export type StructuredResultSchemaType =
  | 'extraction_result'
  | 'decomposition_result'
  | 'duplicate_search_result';

/**
 * Extracted issue from structured output.
 */
export interface ExtractedIssue {
  title: string;
  description: string;
  issue_type: string;
  priority: string;
  source_block_id?: string | null;
  category: string;
}

/**
 * Subtask from task decomposition.
 */
export interface DecomposedSubtask {
  title: string;
  description: string;
  storyPoints: number;
  dependsOn: number[];
}

/**
 * Duplicate candidate from similarity search.
 */
export interface DuplicateCandidate {
  issueId: string;
  issueKey: string;
  title: string;
  similarityScore: number;
  reason: string;
}

/**
 * Structured result event.
 * AI agent returned a typed, schema-validated response.
 * Used for rich UI rendering of extraction, decomposition, etc.
 */
export interface StructuredResultEvent extends SSEEvent {
  type: 'structured_result';
  data: {
    /** Message ID this result belongs to */
    messageId: string;
    /** Schema type for frontend rendering dispatch */
    schemaType: StructuredResultSchemaType;
    /** Typed result data (matches backend Pydantic model) */
    data: Record<string, unknown>;
  };
}

/**
 * Message stop event.
 * Signals the end of message streaming.
 */
export interface MessageStopEvent extends SSEEvent {
  type: 'message_stop';
  data: {
    /** Message identifier */
    messageId: string;
    /** Reason for stopping */
    stopReason: StopReason;
    /** Token usage statistics */
    usage?: TokenUsage;
    /** Message generation cost (USD) */
    costUsd?: number;
  };
}

/**
 * Stop reason for message termination.
 */
export type StopReason = 'end_turn' | 'max_tokens' | 'stop_sequence' | 'tool_use';

/**
 * Token usage statistics.
 * Used for cost tracking and billing.
 */
export interface TokenUsage {
  /** Input tokens consumed */
  inputTokens: number;
  /** Output tokens generated */
  outputTokens: number;
  /** Total tokens (input + output) */
  totalTokens?: number;
  /** Total cached tokens (read + creation) */
  cachedTokens?: number;
  /** Tokens read from prompt cache (saves cost) */
  cachedReadTokens?: number;
  /** Tokens written to prompt cache */
  cachedCreationTokens?: number;
}

/**
 * Budget warning event.
 * Emitted when session token usage reaches 80% of budget ceiling.
 */
export interface BudgetWarningEvent extends SSEEvent {
  type: 'budget_warning';
  data: {
    /** Current cost in USD */
    currentCostUsd: number;
    /** Budget ceiling in USD */
    maxBudgetUsd: number;
    /** Percentage of budget used (0-100) */
    percentUsed: number;
    /** Warning message */
    message: string;
  };
}

/**
 * Tool audit event.
 * Emitted after each tool execution for audit logging.
 */
export interface ToolAuditEvent extends SSEEvent {
  type: 'tool_audit';
  data: {
    /** Tool use identifier */
    toolUseId: string;
    /** Tool name */
    toolName: string;
    /** Truncated input summary */
    inputSummary: string;
    /** Truncated output summary */
    outputSummary: string;
    /** Execution duration in milliseconds */
    durationMs: number | null;
  };
}

/**
 * Error event.
 * Signals an error during message generation.
 */
export interface ErrorEvent extends SSEEvent {
  type: 'error';
  data: {
    /** Error code for programmatic handling */
    errorCode: ErrorCode;
    /** Human-readable error message */
    message: string;
    /** Retry delay in seconds (if retryable) */
    retryAfter?: number;
    /** Whether error is retryable */
    retryable?: boolean;
    /** Error details (additional context) */
    details?: Record<string, unknown>;
  };
}

/**
 * Error codes for client-side error handling.
 */
export type ErrorCode =
  | 'rate_limited'
  | 'context_exceeded'
  | 'api_error'
  | 'network_error'
  | 'authentication_error'
  | 'permission_denied'
  | 'invalid_input'
  | 'resource_not_found'
  | 'provider_error'
  | 'timeout';

/** T58: Citation event for source attribution. */
export interface CitationEvent extends SSEEvent {
  type: 'citation';
  data: {
    messageId: string;
    citations: Array<{
      sourceType: string;
      sourceId: string;
      sourceTitle: string;
      citedText: string;
      startIndex?: number;
      endIndex?: number;
    }>;
  };
}

/** T57: Memory update event from cross-session memory tool. */
export interface MemoryUpdateEvent extends SSEEvent {
  type: 'memory_update';
  data: {
    /** Message ID for correlation (T68) */
    messageId?: string;
    operation: 'write' | 'read' | 'delete';
    key: string;
    value?: unknown;
  };
}

/** T59: Tool input delta for progressive tool parameter rendering. */
export interface ToolInputDeltaEvent extends SSEEvent {
  type: 'tool_input_delta';
  data: {
    toolUseId: string;
    toolName: string;
    inputDelta: string;
  };
}

/**
 * Type guard to narrow SSEEvent to specific event type.
 *
 * @example
 * ```typescript
 * if (isMessageStartEvent(event)) {
 *   console.log(event.messageId);
 * }
 * ```
 */
export function isMessageStartEvent(event: SSEEvent): event is MessageStartEvent {
  return event.type === 'message_start';
}

export function isContentBlockStartEvent(event: SSEEvent): event is ContentBlockStartEvent {
  return event.type === 'content_block_start';
}

export function isTextDeltaEvent(event: SSEEvent): event is TextDeltaEvent {
  return event.type === 'text_delta';
}

export function isThinkingDeltaEvent(event: SSEEvent): event is ThinkingDeltaEvent {
  return event.type === 'thinking_delta';
}

export function isToolUseEvent(event: SSEEvent): event is ToolUseEvent {
  return event.type === 'tool_use';
}

export function isToolResultEvent(event: SSEEvent): event is ToolResultEvent {
  return event.type === 'tool_result';
}

export function isTaskProgressEvent(event: SSEEvent): event is TaskProgressEvent {
  return event.type === 'task_progress';
}

export function isApprovalRequestEvent(event: SSEEvent): event is ApprovalRequestEvent {
  return event.type === 'approval_request';
}

export function isContentUpdateEvent(event: unknown): event is ContentUpdateEvent {
  if (!event || typeof event !== 'object') {
    return false;
  }

  const e = event as { type?: string; data?: unknown };

  // Must have type 'content_update'
  if (e.type !== 'content_update') {
    return false;
  }

  // Must have data field
  if (!e.data || typeof e.data !== 'object') {
    return false;
  }

  const data = e.data as Record<string, unknown>;

  // Must have required fields in data
  if (!data.noteId || typeof data.noteId !== 'string') {
    return false;
  }

  if (
    !data.operation ||
    !['replace_block', 'append_blocks', 'insert_inline_issue'].includes(data.operation as string)
  ) {
    return false;
  }

  // All required fields present and valid
  return true;
}

export function isAskUserQuestionEvent(event: SSEEvent): event is AskUserQuestionEvent {
  return event.type === 'ask_user_question';
}

export function isStructuredResultEvent(event: SSEEvent): event is StructuredResultEvent {
  return event.type === 'structured_result';
}

export function isMessageStopEvent(event: SSEEvent): event is MessageStopEvent {
  return event.type === 'message_stop';
}

export function isBudgetWarningEvent(event: SSEEvent): event is BudgetWarningEvent {
  return event.type === 'budget_warning';
}

export function isToolAuditEvent(event: SSEEvent): event is ToolAuditEvent {
  return event.type === 'tool_audit';
}

export function isErrorEvent(event: SSEEvent): event is ErrorEvent {
  return event.type === 'error';
}

export function isCitationEvent(event: SSEEvent): event is CitationEvent {
  return event.type === 'citation';
}

export function isMemoryUpdateEvent(event: SSEEvent): event is MemoryUpdateEvent {
  return event.type === 'memory_update';
}

export function isToolInputDeltaEvent(event: SSEEvent): event is ToolInputDeltaEvent {
  return event.type === 'tool_input_delta';
}
