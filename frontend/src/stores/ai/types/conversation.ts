/**
 * Conversation types for PilotSpaceStore.
 * Defines message structure, session state, and streaming content.
 *
 * @module stores/ai/types/conversation
 */
import type { AttachmentMetadata } from '@/types/attachments';

/**
 * Message role in conversation.
 * - user: Message from the user
 * - assistant: Message from AI assistant
 * - system: System-level instructions or context
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Tool call invoked during assistant message generation.
 * Maps to backend MCP tool execution.
 */
export interface ToolCall {
  /** Unique identifier for this tool invocation */
  id: string;
  /** Tool name as registered in MCP registry */
  name: string;
  /** Tool input parameters */
  input: Record<string, unknown>;
  /** Tool execution result */
  output?: unknown;
  /** Tool execution status */
  status?: 'pending' | 'completed' | 'failed';
  /** Error message if execution failed */
  errorMessage?: string;
  /** Accumulated partial JSON input from tool_input_delta streaming (T65) */
  partialInput?: string;
  /** Parent tool use ID for subagent correlation (G12) */
  parentToolUseId?: string;
  /** Execution duration in milliseconds (from tool_audit) */
  durationMs?: number;
}

/**
 * Individual thinking block entry for interleaved thinking (G-07).
 * Each entry corresponds to a separate thinking content block from Claude.
 */
export interface ThinkingBlockEntry {
  /** Thinking text content */
  content: string;
  /** Content block index from the AssistantMessage (for ordering) */
  blockIndex: number;
  /** Whether this block was redacted by Claude safety system (G-04) */
  redacted?: boolean;
  /** Timestamp (ms) when this thinking block started */
  startedAt?: number;
  /** Duration of this thinking block in milliseconds (set when block ends) */
  durationMs?: number;
}

/**
 * Ordered content block for preserving interleaved rendering order.
 * Used by AssistantMessage to render thinking/text/tool blocks in the
 * order they were received from the server, rather than grouped by type.
 */
export type ContentBlock =
  | {
      type: 'thinking';
      blockIndex: number;
      content: string;
      redacted?: boolean;
      startedAt?: number;
      durationMs?: number;
    }
  | { type: 'text'; content: string }
  | { type: 'tool_call'; toolCallId: string };

/**
 * Chat message in a conversation thread.
 */
export interface ChatMessage {
  /** Unique message identifier (UUIDv4) */
  id: string;
  /** Message sender role */
  role: MessageRole;
  /** Message text content */
  content: string;
  /** Message timestamp (ISO 8601) */
  timestamp: Date;
  /** Tool calls invoked during message generation */
  toolCalls?: ToolCall[];
  /** Extended thinking content — concatenated fallback (from Claude Opus reasoning) */
  thinkingContent?: string;
  /** Individual thinking blocks for interleaved rendering (G-07) */
  thinkingBlocks?: ThinkingBlockEntry[];
  /** Ordered content blocks preserving interleaved rendering sequence */
  contentBlocks?: ContentBlock[];
  /** Duration of thinking phase in milliseconds */
  thinkingDurationMs?: number;
  /** Thinking block signature for multi-turn verification (G-06) */
  thinkingSignature?: string;
  /** Structured result data (from schema-validated AI responses) */
  structuredResult?: {
    schemaType: string;
    data: Record<string, unknown>;
  };
  /** Phase 69: Long-term memory sources used by the agent for this message. */
  memorySources?: Array<{
    id: string;
    type: string;
    score: number;
  }>;
  /** Citation references from source documents (T58) */
  citations?: Array<{
    sourceType: string;
    sourceId: string;
    sourceTitle: string;
    citedText: string;
    startIndex?: number;
    endIndex?: number;
  }>;
  /** Question data embedded in assistant message (stateless two-turn model).
   *  - answers undefined = pending (QuestionBlock renders inline)
   *  - answers present = resolved (ResolvedSummary renders inline)
   *  Legacy single-question format kept for backward compatibility. */
  questionData?: {
    questionId: string;
    questions: import('./events').AgentQuestion[];
    answers?: Record<string, string>;
  };
  /** Multiple question sets from multiple ask_user calls in one turn.
   *  Each entry corresponds to one ask_user tool invocation.
   *  Questions are merged into a single wizard UI. */
  questionDataList?: Array<{
    questionId: string;
    questions: import('./events').AgentQuestion[];
    answers?: Record<string, string>;
  }>;
  /** Additional message metadata */
  metadata?: MessageMetadata;
  /** Phase 75: Batch issue proposal from generate_issues_from_description tool.
   *  Attached to the triggering message so multiple proposals can coexist in a session. */
  batchProposal?: import('./events').IssueBatchProposalEvent['data'] | null;
}

/**
 * Additional metadata attached to chat messages.
 */
export interface MessageMetadata {
  /** Skill invoked via slash command (e.g., "/extract-issues") */
  skillInvoked?: string;
  /** Agent explicitly mentioned (e.g., "@pr-review") */
  agentMentioned?: string;
  /** Context used for generating this message */
  contextUsed?: ConversationContext;
  /** Token count for cost tracking */
  tokenCount?: number;
  /** AI model used for generation (e.g., "claude-sonnet-4-20250514") */
  model?: string;
  /** Cost in USD for this message */
  costUsd?: number;
  /** Whether this message is an answer to an agent question (hides protocol text) */
  isAnswerMessage?: boolean;
  /** Files attached to this message (persisted in message metadata for history) */
  attachments?: AttachmentMetadata[];
  /** Signed URL for voice recording playback (from voice-to-text input). 1-hour expiry. */
  voiceAudioUrl?: string | null;
}

/**
 * Context available during conversation.
 * Determines which data sources are accessible to the agent.
 */
export interface ConversationContext {
  /** Current workspace ID (required for backend API) */
  workspaceId: string;
  /** Current note ID if conversation is within a note */
  noteId: string | null;
  /** Current issue ID if conversation is within an issue */
  issueId: string | null;
  /** Current project ID for scoping queries */
  projectId: string | null;
  /** User-selected text in the editor */
  selectedText: string | null;
  /** Selected block IDs in note canvas */
  selectedBlockIds: string[];
  /** Current workspace slug */
  workspaceSlug?: string;
  /** Current user ID */
  userId?: string;
  /** Homepage digest summary for AI context awareness */
  homepageDigestSummary?: string;
}

/**
 * Session state for multi-turn conversations.
 * Maps to backend SessionManager (Redis-backed, 30-minute TTL).
 */
export interface SessionState {
  /** Session identifier (UUIDv4, backend-generated) */
  sessionId: string | null;
  /** Whether session is currently active */
  isActive: boolean;
  /** Session creation timestamp */
  createdAt: Date | null;
  /** Last activity timestamp (used for TTL calculation) */
  lastActivityAt: Date | null;
  /** Agent name used in this session */
  agentName?: string;
  /** Accumulated cost for this session (USD) */
  totalCostUsd?: number;
  /** Turn count in this session */
  turnCount?: number;
  /** Accumulated token count for budget ring display (008) */
  totalTokens?: number;
}

/**
 * SSE streaming state.
 * Tracks in-progress message streaming from backend.
 */
export interface StreamingState {
  /** Whether currently receiving streamed content */
  isStreaming: boolean;
  /** Accumulated streamed content (text deltas) */
  streamContent: string;
  /** Message ID being streamed (maps to ChatMessage.id) */
  currentMessageId: string | null;
  /** Current streaming phase */
  phase?: StreamingPhase;
  /** Accumulated thinking content (thinking deltas from extended thinking) */
  thinkingContent?: string;
  /** Whether thinking is actively streaming */
  isThinking?: boolean;
  /** Timestamp when thinking started (for duration display) */
  thinkingStartedAt?: number | null;
  /** Current content block type from content_block_start (G13) */
  currentBlockType?: 'text' | 'tool_use' | 'thinking';
  /** Current content block index from content_block_start (G13) */
  currentBlockIndex?: number;
  /** Thinking block signature for multi-turn verification (G-06) */
  thinkingSignature?: string;
  /** Accumulated thinking blocks for interleaved rendering (G-07) */
  thinkingBlocks?: ThinkingBlockEntry[];
  /** Currently executing tool name for banner display (008) */
  activeToolName?: string | null;
  /** Stream was aborted by user (008) */
  interrupted?: boolean;
  /** Accumulated word count during text generation phase (008) */
  wordCount?: number;
  /** Ordered sequence of content block types for interleaved streaming rendering */
  blockOrder?: Array<'thinking' | 'text' | 'tool_use'>;
  /** Per-text-block segments for ordered rendering (one entry per 'text' in blockOrder) */
  textSegments?: string[];
}

/**
 * Phase of streaming process.
 * - connecting: Establishing SSE connection
 * - message_start: Backend sent message_start event
 * - content: Receiving text_delta events
 * - tool_use: Agent is using tools
 * - completing: Backend sent message_stop event
 */
export type StreamingPhase =
  | 'connecting'
  | 'message_start'
  | 'thinking'
  | 'content'
  | 'tool_use'
  | 'completing'
  | 'waiting_for_user';

// ============================================================
// Feature 015: WorkIntent state for chat engine
// ============================================================

/**
 * WorkIntent UI state for rendering in chat timeline.
 */
export interface WorkIntentState {
  intentId: string;
  what: string;
  why?: string;
  constraints?: string[];
  confidence: number;
  /** Current lifecycle phase */
  status: 'detected' | 'confirmed' | 'rejected' | 'executing' | 'completed' | 'failed';
  /** If executing/completed: the skill name */
  skillName?: string;
  /** Human-readable intent summary for SkillProgressCard */
  intentSummary?: string;
  /** Skill execution progress (0-100) */
  skillProgress?: number;
  /** Current step description */
  skillCurrentStep?: string;
  /** Total execution steps */
  skillTotalSteps?: number;
  /** Current step number */
  skillStep?: number;
  /** Skill output artifacts */
  artifacts?: Array<{ type: string; id: string; name: string; url?: string }>;
  /** Error message if failed */
  errorMessage?: string;
  /** Whether output is partial (failed mid-execution) */
  partialOutput?: boolean;
  /** Whether this skill output needs approval before persisting */
  requiresApproval?: boolean;
  /** Approval request ID */
  approvalId?: string;
}

/**
 * Skill execution queue state.
 */
export interface SkillQueueState {
  runningCount: number;
  queuedCount: number;
  maxConcurrent: number;
}
