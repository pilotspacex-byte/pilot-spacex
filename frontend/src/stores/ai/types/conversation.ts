/**
 * Conversation types for PilotSpaceStore.
 * Defines message structure, session state, and streaming content.
 *
 * @module stores/ai/types/conversation
 */

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
  /** Parent tool use ID for subagent correlation (G12) */
  parentToolUseId?: string;
}

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
  /** Extended thinking content (from Claude Opus reasoning) */
  thinkingContent?: string;
  /** Duration of thinking phase in milliseconds */
  thinkingDurationMs?: number;
  /** Structured result data (from schema-validated AI responses) */
  structuredResult?: {
    schemaType: string;
    data: Record<string, unknown>;
  };
  /** Additional message metadata */
  metadata?: MessageMetadata;
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
  currentBlockType?: 'text' | 'tool_use';
  /** Current content block index from content_block_start (G13) */
  currentBlockIndex?: number;
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
  | 'completing';
