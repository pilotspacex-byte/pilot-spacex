/**
 * Session types for SessionListStore.
 * Defines session summary, context history, and API response shapes.
 *
 * @module stores/ai/types/session
 */

// ========================================
// Public Types (used by components)
// ========================================

/**
 * Context history entry for multi-context sessions.
 */
export interface ContextEntry {
  /** Turn number when context was used */
  turn: number;
  /** Note ID if context was a note */
  noteId?: string;
  /** Note title if available */
  noteTitle?: string;
  /** Issue ID if context was an issue */
  issueId?: string;
  /** Block IDs if specific blocks were selected */
  blockIds?: string[];
  /** Selected text if available */
  selectedText?: string;
  /** When the context was used */
  timestamp: string;
}

/**
 * Session summary for list display.
 */
export interface SessionSummary {
  /** Session identifier */
  sessionId: string;
  /** Agent name (conversation, ai_context, etc.) */
  agentName: string;
  /** Context ID (note, issue, etc.) - initial context */
  contextId?: string;
  /** Context type for display */
  contextType?: 'note' | 'issue' | 'project';
  /** History of contexts used in this session */
  contextHistory?: ContextEntry[];
  /** Session creation timestamp */
  createdAt: Date;
  /** Last activity timestamp */
  updatedAt: Date;
  /** Number of conversation turns */
  turnCount: number;
  /** Session expiration timestamp */
  expiresAt: Date;
  /** Auto-generated session title from first user message */
  title?: string;
  /** Session ID this was forked from (if fork) */
  forkedFrom?: string;
  /** Number of forks created from this session */
  forkCount?: number;
}

// ========================================
// API Response Types (snake_case from backend)
// ========================================

export interface ContextHistoryResponse {
  turn: number;
  note_id?: string;
  note_title?: string;
  issue_id?: string;
  block_ids?: string[];
  selected_text?: string;
  timestamp: string;
}

export interface SessionSummaryResponse {
  id: string;
  workspace_id: string;
  agent_name: string;
  context_id?: string;
  context_type?: 'note' | 'issue' | 'project';
  context_history?: ContextHistoryResponse[];
  created_at: string;
  updated_at: string;
  turn_count: number;
  total_cost_usd: number;
  expires_at: string;
  title?: string;
  forked_from?: string;
  fork_count?: number;
}

export interface MessageResponse {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  tokens?: number;
  cost_usd?: number;
  metadata?: Record<string, unknown>;
  /** Ordered content blocks for interleaved rendering (thinking/text/tool_call) */
  content_blocks?: Array<
    | { type: 'thinking'; blockIndex: number; content: string }
    | { type: 'text'; content: string }
    | { type: 'tool_call'; toolCallId: string }
  >;
  /** Thinking block entries for extended thinking display */
  thinking_blocks?: Array<{ content: string; blockIndex: number; redacted?: boolean }>;
  /** Question data for session resume Q&A rendering */
  question_data?: {
    questionId: string;
    questions: Array<{
      question: string;
      options: Array<{ label: string; description?: string }>;
      multiSelect?: boolean;
      header?: string;
    }>;
    answers?: Record<string, string>;
  };
  /** Tool call records for session resume rendering */
  tool_calls?: Array<{
    id: string;
    name: string;
    input: Record<string, unknown>;
    output?: unknown;
    status?: 'pending' | 'completed' | 'failed';
    error_message?: string;
    duration_ms?: number;
  }>;
}

/**
 * Response from resume session endpoint with pagination support.
 */
export interface ResumeSessionResponse {
  session_id: string;
  messages: MessageResponse[];
  context: Record<string, unknown>;
  turn_count: number;
  total_messages: number;
  has_more: boolean;
}
