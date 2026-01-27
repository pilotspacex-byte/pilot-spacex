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
  | 'tool_use'
  | 'tool_result'
  | 'task_progress'
  | 'approval_request'
  | 'message_stop'
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

export function isTextDeltaEvent(event: SSEEvent): event is TextDeltaEvent {
  return event.type === 'text_delta';
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

export function isMessageStopEvent(event: SSEEvent): event is MessageStopEvent {
  return event.type === 'message_stop';
}

export function isErrorEvent(event: SSEEvent): event is ErrorEvent {
  return event.type === 'error';
}
