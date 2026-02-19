/**
 * Type guards for SSE events.
 * Extracted from events.ts to keep file sizes under 700-line limit.
 *
 * @module stores/ai/types/event-guards
 * @see ./events.ts for event type definitions
 */
import type {
  SSEEvent,
  MessageStartEvent,
  ContentBlockStartEvent,
  TextDeltaEvent,
  ThinkingDeltaEvent,
  ToolUseEvent,
  ToolResultEvent,
  TaskProgressEvent,
  ApprovalRequestEvent,
  ContentUpdateEvent,
  QuestionRequestEvent,
  StructuredResultEvent,
  MessageStopEvent,
  BudgetWarningEvent,
  ToolAuditEvent,
  ErrorEvent,
  CitationEvent,
  MemoryUpdateEvent,
  ToolInputDeltaEvent,
  FocusBlockEvent,
  IntentDetectedEvent,
  IntentConfirmedEvent,
  IntentExecutingEvent,
  IntentCompletedEvent,
  SkillCompletedEvent,
  QueueUpdateEvent,
} from './events';

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
  if (event.type !== 'tool_use') return false;
  const data = (event as { type: string; data?: unknown }).data;
  if (!data || typeof data !== 'object') {
    console.warn('[event-guards] tool_use event missing data:', event);
    return false;
  }
  const d = data as Record<string, unknown>;
  if (typeof d.toolCallId !== 'string' || typeof d.toolName !== 'string') {
    console.warn('[event-guards] tool_use event has invalid data shape:', event);
    return false;
  }
  return true;
}

export function isToolResultEvent(event: SSEEvent): event is ToolResultEvent {
  if (event.type !== 'tool_result') return false;
  const data = (event as { type: string; data?: unknown }).data;
  if (!data || typeof data !== 'object') {
    console.warn('[event-guards] tool_result event missing data:', event);
    return false;
  }
  const d = data as Record<string, unknown>;
  if (typeof d.toolCallId !== 'string' && typeof d.toolUseId !== 'string') {
    console.warn('[event-guards] tool_result event missing toolCallId or toolUseId:', event);
    return false;
  }
  const VALID_STATUSES = ['completed', 'failed', 'cancelled'];
  if (typeof d.status !== 'string' || !VALID_STATUSES.includes(d.status)) {
    console.warn('[event-guards] tool_result event has invalid status:', event);
    return false;
  }
  return true;
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

  const VALID_OPERATIONS = [
    'replace_block',
    'append_blocks',
    'insert_inline_issue',
    'insert_blocks',
    'remove_block',
    'remove_content',
    'replace_content',
    'insert_pm_block',
    'update_pm_block',
  ];
  if (!data.operation || !VALID_OPERATIONS.includes(data.operation as string)) {
    return false;
  }

  // All required fields present and valid
  return true;
}

export function isQuestionRequestEvent(event: SSEEvent): event is QuestionRequestEvent {
  return event.type === 'question_request';
}

export function isStructuredResultEvent(event: SSEEvent): event is StructuredResultEvent {
  return event.type === 'structured_result';
}

export function isMessageStopEvent(event: SSEEvent): event is MessageStopEvent {
  if (event.type !== 'message_stop') return false;
  const data = (event as { type: string; data?: unknown }).data;
  if (!data || typeof data !== 'object') {
    console.warn('[event-guards] message_stop event missing data:', event);
    return false;
  }
  const d = data as Record<string, unknown>;
  if (typeof d.messageId !== 'string' || typeof d.stopReason !== 'string') {
    console.warn('[event-guards] message_stop event has invalid data shape:', event);
    return false;
  }
  return true;
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

export function isFocusBlockEvent(event: SSEEvent): event is FocusBlockEvent {
  return event.type === 'focus_block';
}

// Feature 015: Intent lifecycle event guards

export function isIntentDetectedEvent(event: SSEEvent): event is IntentDetectedEvent {
  return event.type === 'intent_detected';
}

export function isIntentConfirmedEvent(event: SSEEvent): event is IntentConfirmedEvent {
  return event.type === 'intent_confirmed';
}

export function isIntentExecutingEvent(event: SSEEvent): event is IntentExecutingEvent {
  return event.type === 'intent_executing';
}

export function isIntentCompletedEvent(event: SSEEvent): event is IntentCompletedEvent {
  return event.type === 'intent_completed';
}

export function isSkillCompletedEvent(event: SSEEvent): event is SkillCompletedEvent {
  return event.type === 'skill_completed';
}

export function isQueueUpdateEvent(event: SSEEvent): event is QueueUpdateEvent {
  return event.type === 'queue_update';
}

const KNOWN_EVENT_TYPES = new Set([
  'message_start',
  'content_block_start',
  'text_delta',
  'thinking_delta',
  'tool_use',
  'tool_result',
  'tool_input_delta',
  'task_progress',
  'approval_request',
  'content_update',
  'question_request',
  'structured_result',
  'message_stop',
  'budget_warning',
  'tool_audit',
  'error',
  'citation',
  'memory_update',
  'focus_block',
  'intent_detected',
  'intent_confirmed',
  'intent_executing',
  'intent_completed',
  'skill_completed',
  'queue_update',
]);

/**
 * Log a warning for any SSE event type that is not recognized.
 * Call this in the event dispatch loop as a fallback after all guards.
 */
export function logUnrecognizedEvent(event: SSEEvent): void {
  if (!KNOWN_EVENT_TYPES.has(event.type)) {
    console.warn('[event-guards] Unrecognized SSE event type:', event.type, event);
  }
}
