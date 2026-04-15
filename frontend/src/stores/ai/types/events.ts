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
  | 'question_request'
  | 'content_update'
  | 'structured_result'
  | 'message_stop'
  | 'budget_warning'
  | 'tool_audit'
  | 'citation'
  | 'memory_update'
  | 'memory_used'
  | 'tool_input_delta'
  | 'focus_block'
  | 'error'
  // Feature 015: AI Workforce Platform intent lifecycle events
  | 'intent_detected'
  | 'intent_confirmed'
  | 'intent_executing'
  | 'intent_completed'
  | 'queue_update'
  | 'skill_completed'
  // Phase 64: Chat-first skill refinement events
  | 'skill_preview'
  | 'test_result'
  | 'skill_saved'
  // Phase 75: Chat-to-issue pipeline events
  | 'issue_batch_proposal';

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

/** Signals the beginning of a new assistant message. */
export interface MessageStartEvent extends SSEEvent {
  type: 'message_start';
  data: {
    messageId: string;
    sessionId: string;
    model?: string;
  };
}

/** New content block (text or tool use) starting. */
export interface ContentBlockStartEvent extends SSEEvent {
  type: 'content_block_start';
  data: {
    index: number;
    contentType: 'text' | 'tool_use' | 'thinking';
    parentToolUseId?: string;
  };
}

/** Streamed text content chunk for progressive rendering. */
export interface TextDeltaEvent extends SSEEvent {
  type: 'text_delta';
  data: {
    messageId: string;
    delta: string;
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
    /** Content block index for interleaved thinking ordering (G-07) */
    blockIndex?: number;
    /** Whether this block was redacted by safety system (G-04/G-07) */
    redacted?: boolean;
    /** Thinking block signature for multi-turn verification (G-06) */
    signature?: string;
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
    /** Legacy field name from web search events — use toolCallId when available */
    toolUseId?: string;
    /** Tool execution status */
    status: 'completed' | 'failed' | 'cancelled';
    /** Tool output (tool-specific structure) */
    output?: unknown;
    /** Error message if status is 'failed' */
    errorMessage?: string;
    /** Execution duration in milliseconds */
    duration?: number;
    /** Complete tool input from backend (resolves fragmented streaming input) */
    toolInput?: Record<string, unknown>;
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
 * Question option for QuestionRequest.
 */
export interface QuestionOption {
  /** Display label */
  label: string;
  /** Description of this option */
  description?: string;
}

/**
 * Condition to skip a question based on a previous question's answer.
 */
export interface SkipCondition {
  /** 0-based index of the referenced question */
  questionIndex: number;
  /** If this label is selected in the referenced question, skip this question */
  selectedLabel: string;
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
  /** Conditions to skip this question based on previous answers */
  skipWhen?: SkipCondition[];
}

/**
 * Question request event.
 * AI agent needs clarification during execution.
 * Frontend renders inline QuestionBlock for user response.
 */
export interface QuestionRequestEvent extends SSEEvent {
  type: 'question_request';
  data: {
    /** Message ID this question belongs to */
    messageId: string;
    /** Question ID (tool call ID, used to submit answer) */
    questionId: string;
    /** Tool call ID that triggered this question */
    toolCallId: string;
    /** Questions to display */
    questions: AgentQuestion[];
  };
}

/** Content update event data payload for content_update SSE event. */
export interface ContentUpdateData {
  noteId: string;
  operation:
    | 'replace_block'
    | 'append_blocks'
    | 'insert_inline_issue'
    | 'insert_blocks'
    | 'remove_block'
    | 'remove_content'
    | 'replace_content'
    | 'insert_pm_block'
    | 'update_pm_block'
    | 'create_issues'
    | 'create_single_issue';
  /**
   * Operation status from backend approval gate (DD-003).
   * 'pending_apply'    — auto-execute path; apply immediately.
   * 'approval_required' — human-in-the-loop; must be routed to ApprovalStore.
   */
  status?: 'pending_apply' | 'approval_required';
  blockId: string | null;
  /** Markdown content from AI agent (preferred over JSONContent) */
  markdown: string | null;
  /** TipTap JSONContent for block content (fallback) */
  content: Record<string, unknown> | null;
  issueData: {
    issueId?: string;
    issueKey?: string;
    title: string;
    description?: string;
    type?: 'bug' | 'improvement' | 'feature' | 'task';
    state?: 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled';
    priority?: 'urgent' | 'high' | 'medium' | 'low' | 'none';
    sourceBlockId?: string;
  } | null;
  afterBlockId: string | null;
  beforeBlockId?: string | null;
  pattern?: string | null;
  oldPattern?: string | null;
  newContent?: string | null;
  blockIds?: string[];
  /** PM block data for insert_pm_block/update_pm_block operations */
  pmBlockData?: {
    blockType: string;
    /** JSON-encoded block data string */
    data: string;
    version?: number;
  };
  /**
   * Bulk issues array — present when operation is 'create_issues'.
   * Each entry matches the normalized_issues shape from extract_issues tool.
   */
  issues?: Array<{
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high' | 'urgent';
    type: 'bug' | 'task' | 'feature' | 'improvement';
  }>;
  /**
   * Single issue data — present when operation is 'create_single_issue'.
   * Matches the issue_data shape from create_issue_from_note tool.
   */
  issue?: {
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high' | 'urgent';
    type: 'bug' | 'task' | 'feature' | 'improvement';
  };
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
  confidence?: number;
  labels?: string[];
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
  | 'timeout'
  | 'CONFIRMATION_TIMEOUT';

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

/**
 * Phase 69: Memory recall event — emitted before assistant text when long-term
 * memory recall returned items used to ground the response. Carries source
 * provenance for the inline `MemoryUsedChip` UI.
 */
export interface MemoryUsedSource {
  id: string;
  type: string;
  score: number;
}

export interface MemoryUsedEvent extends SSEEvent {
  type: 'memory_used';
  data: {
    /** Optional message correlation. */
    messageId?: string;
    sources: MemoryUsedSource[];
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

/** T59: Tool input delta for progressive tool parameter rendering.
 *
 * Supports two backend field formats:
 * - Original (pilotspace_agent_helpers): { toolUseId, toolName, inputDelta }
 * - Stream transformer (stream_event_transformer): { messageId, delta, blockIndex }
 */
export interface ToolInputDeltaEvent extends SSEEvent {
  type: 'tool_input_delta';
  data: {
    /** Tool use ID (original format) */
    toolUseId?: string;
    /** Tool name (original format) */
    toolName?: string;
    /** Input delta text (original format) */
    inputDelta?: string;
    /** Message ID (stream transformer format) */
    messageId?: string;
    /** Delta text (stream transformer format) */
    delta?: string;
    /** Content block index for mapping to tool call (stream transformer format) */
    blockIndex?: number;
  };
}

/**
 * Focus block event.
 * Emitted by backend immediately before content_update so the frontend can
 * scroll to and visually prepare (pending-edit highlight) the target block
 * before the content replacement arrives.
 */
export interface FocusBlockEvent extends SSEEvent {
  type: 'focus_block';
  data: {
    /** Note ID containing the block */
    noteId: string;
    /** Block ID to focus (null when scrollToEnd is true) */
    blockId: string | null;
    /** When true, scroll to the end of the document (write_to_note) */
    scrollToEnd: boolean;
  };
}

// Phase 64: Chat-first skill refinement — skill creation/test/save SSE events.

/**
 * Skill preview event.
 * Emitted by create_skill / update_skill MCP tools after the skill YAML is drafted.
 * Frontend renders an inline SkillPreviewCard in ChatView so the user can review
 * the skill before confirming the save.
 */
export interface SkillPreviewEvent extends SSEEvent {
  type: 'skill_preview';
  data: {
    /** Canonical skill file name (e.g. "review-pr") */
    skillName: string;
    /** Parsed YAML frontmatter key-value pairs */
    frontmatter: Record<string, string>;
    /** Full skill Markdown content (instructions body) */
    content: string;
    /** True when updating an existing skill, false when creating a new one */
    isUpdate: boolean;
  };
}

/**
 * Test result event.
 * Emitted by the test_skill MCP tool after running the eval suite.
 * Frontend renders an inline TestResultCard with pass/fail breakdown.
 */
export interface TestResultEvent extends SSEEvent {
  type: 'test_result';
  data: {
    /** Skill that was tested */
    skillName: string;
    /** Aggregate score 0–10 (5 rubric checks x 2 points each) */
    score: number;
    /** Descriptions of passing test cases */
    passed: string[];
    /** Descriptions of failing test cases */
    failed: string[];
    /** Suggested improvements from the evaluator */
    suggestions: string[];
    /** Representative sample output from the skill execution */
    sampleOutput: string;
  };
}

/**
 * Skill saved event.
 * Emitted after the user confirms and the skill is persisted to disk/DB.
 * Frontend clears the skill preview state and shows a success confirmation.
 */
export interface SkillSavedEvent extends SSEEvent {
  type: 'skill_saved';
  data: {
    /** Canonical skill name that was saved */
    skillName: string;
    /** Template ID if the skill was also published as a marketplace template */
    templateId?: string;
  };
}

// Phase 75: Chat-to-issue pipeline — batch issue proposal event.

/**
 * A single proposed issue from the generate_issues_from_description tool.
 */
export interface ProposedIssue {
  title: string;
  description: string;
  acceptance_criteria: Array<{ criterion: string; met: boolean }>;
  priority: 'none' | 'low' | 'medium' | 'high' | 'urgent';
}

/**
 * Issue batch proposal event.
 * Emitted by the generate_issues_from_description MCP tool after extracting issues
 * from a PM description in the chat. Frontend renders a BatchPreviewCard inline
 * in AssistantMessage so the PM can review, edit, and approve before DB writes.
 *
 * Attached to the triggering ChatMessage.batchProposal (not globally on store)
 * to support multiple proposals per session (RESEARCH Pitfall 2).
 */
export interface IssueBatchProposalEvent extends SSEEvent {
  type: 'issue_batch_proposal';
  data: {
    /** ID of the assistant message that carries this proposal */
    messageId: string;
    /** Proposed issues ready for PM review */
    issues: ProposedIssue[];
    /** Source note ID (null when initiated from plain chat) */
    sourceNoteId: string | null;
    /** Project ID to create issues in */
    projectId: string;
  };
}

// Feature 015: Intent/skill lifecycle events extracted to events-workforce.ts.
// Re-exported here for backward compatibility.
export type {
  IntentDetectedEvent,
  IntentConfirmedEvent,
  IntentExecutingEvent,
  IntentCompletedEvent,
  SkillCompletedEvent,
  QueueUpdateEvent,
} from './events-workforce';

// Type guards extracted to ./event-guards.ts to keep this file under 700 lines.
// Re-export for backward compatibility.
export {
  isMessageStartEvent,
  isContentBlockStartEvent,
  isTextDeltaEvent,
  isThinkingDeltaEvent,
  isToolUseEvent,
  isToolResultEvent,
  isTaskProgressEvent,
  isApprovalRequestEvent,
  isContentUpdateEvent,
  isQuestionRequestEvent,
  isStructuredResultEvent,
  isMessageStopEvent,
  isBudgetWarningEvent,
  isToolAuditEvent,
  isErrorEvent,
  isCitationEvent,
  isMemoryUpdateEvent,
  isMemoryUsedEvent,
  isToolInputDeltaEvent,
  isFocusBlockEvent,
  isIntentDetectedEvent,
  isIntentConfirmedEvent,
  isIntentExecutingEvent,
  isIntentCompletedEvent,
  isSkillCompletedEvent,
  isQueueUpdateEvent,
  // Phase 64: Chat-first skill refinement
  isSkillPreviewEvent,
  isTestResultEvent,
  isSkillSavedEvent,
  // Phase 75: Chat-to-issue pipeline
  isIssueBatchProposalEvent,
} from './event-guards';
