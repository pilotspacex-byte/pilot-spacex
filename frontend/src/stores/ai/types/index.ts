/**
 * AI Store Types - Unified type definitions for PilotSpaceStore.
 *
 * This module re-exports all types used by the conversational agent architecture.
 * Import types from this index for better discoverability and simpler imports.
 *
 * @module stores/ai/types
 *
 * @example
 * ```typescript
 * import type {
 *   ChatMessage,
 *   SkillDefinition,
 *   SSEEvent,
 *   MessageStartEvent,
 * } from '@/stores/ai/types';
 * ```
 */

// Conversation types
export type {
  MessageRole,
  ToolCall,
  ChatMessage,
  MessageMetadata,
  ConversationContext,
  SessionState,
  StreamingState,
  StreamingPhase,
} from './conversation';

// Skills types
export type {
  SkillDefinition,
  SkillCategory,
  SkillInvocation,
  SkillInvocationStatus,
  SkillResult,
  SkillError,
  ConfidenceTag,
  SkillsRegistry,
} from './skills';

// SSE event types
export type {
  SSEEventType,
  SSEEvent,
  MessageStartEvent,
  ContentBlockStartEvent,
  TextDeltaEvent,
  ToolUseEvent,
  ToolResultEvent,
  TaskProgressEvent,
  TaskStatus,
  ApprovalRequestEvent,
  ApprovalActionType,
  ApprovalUrgency,
  AffectedEntity,
  MessageStopEvent,
  StopReason,
  TokenUsage,
  ErrorEvent,
  ErrorCode,
} from './events';

// Type guards (re-export for convenience)
export {
  isMessageStartEvent,
  isTextDeltaEvent,
  isToolUseEvent,
  isToolResultEvent,
  isTaskProgressEvent,
  isApprovalRequestEvent,
  isMessageStopEvent,
  isErrorEvent,
} from './events';
