/**
 * SessionListStore - Manages conversation session list and operations.
 *
 * Handles:
 * - Fetching recent sessions
 * - Resuming existing sessions
 * - Deleting sessions
 * - Session metadata display
 *
 * @module stores/ai/SessionListStore
 * @see T075-T079 (Session Persistence UI)
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { supabase } from '@/lib/supabase';
import type { PilotSpaceStore } from './PilotSpaceStore';

/**
 * API base URL for backend requests.
 * Falls back to localhost if not configured.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

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

/**
 * SessionListStore - Manages conversation session list.
 *
 * @example
 * ```typescript
 * const store = new SessionListStore(aiStore);
 *
 * // Fetch recent sessions
 * await store.fetchSessions();
 *
 * // Resume session
 * await store.resumeSession(sessionId);
 *
 * // Delete session
 * await store.deleteSession(sessionId);
 * ```
 */
export class SessionListStore {
  // ========================================
  // Observable State
  // ========================================

  /** List of sessions */
  sessions: SessionSummary[] = [];

  /** Loading state */
  isLoading = false;

  /** Error state */
  error: string | null = null;

  /** Currently selected session ID */
  selectedSessionId: string | null = null;

  constructor(private rootStore: PilotSpaceStore) {
    makeAutoObservable(this);
  }

  // ========================================
  // Computed Properties
  // ========================================

  /**
   * Get recent sessions (sorted by updated_at desc).
   */
  get recentSessions(): SessionSummary[] {
    return [...this.sessions].sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
  }

  /**
   * Get active (non-expired) sessions.
   */
  get activeSessions(): SessionSummary[] {
    const now = new Date();
    return this.sessions.filter((session) => session.expiresAt > now);
  }

  /**
   * Get sessions grouped by parent, with forks nested under their source.
   * Returns root sessions (non-forks) with any child forks attached.
   */
  get sessionsWithForks(): Array<{ session: SessionSummary; forks: SessionSummary[] }> {
    const recent = this.recentSessions;
    const forksByParent = new Map<string, SessionSummary[]>();
    const roots: SessionSummary[] = [];

    for (const s of recent) {
      if (s.forkedFrom) {
        const existing = forksByParent.get(s.forkedFrom) ?? [];
        existing.push(s);
        forksByParent.set(s.forkedFrom, existing);
      } else {
        roots.push(s);
      }
    }

    return roots.map((session) => ({
      session,
      forks: forksByParent.get(session.sessionId) ?? [],
    }));
  }

  /**
   * Get sessions grouped by date (Today, Yesterday, weekday, date).
   */
  get sessionsGroupedByDate(): Map<string, SessionSummary[]> {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

    const groups = new Map<string, SessionSummary[]>();

    for (const session of this.recentSessions) {
      const sessionDate = new Date(
        session.updatedAt.getFullYear(),
        session.updatedAt.getMonth(),
        session.updatedAt.getDate()
      );

      let label: string;
      if (sessionDate.getTime() === today.getTime()) {
        label = 'Today';
      } else if (sessionDate.getTime() === yesterday.getTime()) {
        label = 'Yesterday';
      } else {
        const daysDiff = Math.floor(
          (today.getTime() - sessionDate.getTime()) / (24 * 60 * 60 * 1000)
        );
        if (daysDiff < 7) {
          label = weekdays[sessionDate.getDay()] ?? 'Unknown';
        } else {
          const dateOptions: Intl.DateTimeFormatOptions = {
            month: 'long',
            day: 'numeric',
          };
          if (sessionDate.getFullYear() !== now.getFullYear()) {
            dateOptions.year = 'numeric';
          }
          label = sessionDate.toLocaleDateString('en-US', dateOptions);
        }
      }

      if (!groups.has(label)) {
        groups.set(label, []);
      }
      groups.get(label)!.push(session);
    }

    return groups;
  }

  // ========================================
  // Auth Helpers
  // ========================================

  /**
   * Get Supabase auth headers and workspace context for authenticated requests.
   */
  private async getAuthHeaders(): Promise<Record<string, string>> {
    const headers: Record<string, string> = {};

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }
    } catch {
      console.warn('Failed to get auth session for session list request');
    }

    const workspaceId = this.rootStore?.workspaceId;
    if (workspaceId) {
      headers['X-Workspace-Id'] = workspaceId;
    }

    return headers;
  }

  // ========================================
  // Actions - Session Management
  // ========================================

  /**
   * Fetch recent sessions for current user.
   * @param limit - Maximum number of sessions to fetch (default: 20)
   */
  async fetchSessions(limit = 20, contextId?: string): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      // Get sessions list from backend (optionally filtered by context)
      const authHeaders = await this.getAuthHeaders();
      let url = `${API_BASE}/ai/sessions?limit=${limit}`;
      if (contextId) {
        url += `&context_id=${contextId}`;
      }
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.statusText}`);
      }

      const data = await response.json();

      runInAction(() => {
        const fetched: SessionSummary[] = data.sessions.map((s: SessionSummaryResponse) => ({
          sessionId: s.id,
          agentName: s.agent_name,
          contextId: s.context_id,
          contextType: s.context_type,
          contextHistory: s.context_history?.map((ctx: ContextHistoryResponse) => ({
            turn: ctx.turn,
            noteId: ctx.note_id,
            noteTitle: ctx.note_title,
            issueId: ctx.issue_id,
            blockIds: ctx.block_ids,
            selectedText: ctx.selected_text,
            timestamp: ctx.timestamp,
          })),
          createdAt: new Date(s.created_at),
          updatedAt: new Date(s.updated_at),
          turnCount: s.turn_count,
          expiresAt: new Date(s.expires_at),
          title: s.title,
          forkedFrom: s.forked_from,
          forkCount: s.fork_count,
        }));

        if (contextId) {
          // Merge context-filtered results into existing sessions (don't overwrite)
          const existingIds = new Set(this.sessions.map((s) => s.sessionId));
          for (const s of fetched) {
            if (!existingIds.has(s.sessionId)) {
              this.sessions.push(s);
            }
          }
        } else {
          this.sessions = fetched;
        }
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to fetch sessions';
        this.isLoading = false;
      });
    }
  }

  /**
   * Resume existing session in PilotSpaceStore with pagination.
   * Loads only the latest N messages initially for faster load times.
   * Use loadMoreMessages() to fetch older messages on scroll-up.
   *
   * @param sessionId - Session identifier to resume
   * @param limit - Number of latest messages to load (default: 3)
   */
  async resumeSession(sessionId: string, limit: number = 3): Promise<void> {
    try {
      // Resume session with pagination (offset=0 = latest messages)
      const authHeaders = await this.getAuthHeaders();
      const response = await fetch(
        `${API_BASE}/ai/sessions/${sessionId}/resume?limit=${limit}&offset=0`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders },
          body: JSON.stringify({}),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch session messages: ${response.statusText}`);
      }

      const data: ResumeSessionResponse = await response.json();

      // Load messages into PilotSpaceStore
      runInAction(() => {
        const pilotSpaceStore = this.rootStore;
        if (pilotSpaceStore) {
          // Clear messages only (caller already handled full clear if needed)
          pilotSpaceStore.messages = [];

          // Set session ID
          pilotSpaceStore.setSessionId(sessionId);

          // Load initial messages (in chronological order from backend)
          data.messages.forEach((msg: MessageResponse, index: number) => {
            pilotSpaceStore.addMessage({
              id: msg.id ?? `restored-${index}`,
              role: msg.role as 'user' | 'assistant' | 'system',
              content: msg.content,
              timestamp: new Date(msg.timestamp),
              metadata: msg.metadata,
              // Map content_blocks from backend (snake_case) to frontend (camelCase)
              contentBlocks: msg.content_blocks?.map((block) => {
                if (block.type === 'thinking') {
                  return {
                    type: 'thinking' as const,
                    blockIndex: block.blockIndex,
                    content: block.content,
                  };
                }
                if (block.type === 'text') {
                  return { type: 'text' as const, content: block.content };
                }
                // tool_call
                return { type: 'tool_call' as const, toolCallId: block.toolCallId };
              }),
              // Map thinking_blocks from backend (snake_case) to frontend (camelCase)
              thinkingBlocks: msg.thinking_blocks?.map((block) => ({
                content: block.content,
                blockIndex: block.blockIndex,
                redacted: block.redacted,
              })),
            });
          });

          // Set pagination state
          pilotSpaceStore.setMessagePaginationState(data.has_more, data.total_messages);

          // Update selected session
          this.selectedSessionId = sessionId;
        }
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to resume session';
      runInAction(() => {
        this.error = errorMsg;
        // Propagate to store for UI visibility
        if (this.rootStore) {
          this.rootStore.error = errorMsg;
        }
      });
    }
  }

  /**
   * Load more (older) messages for the current session.
   * Called when user scrolls to the top of the message list.
   *
   * @param sessionId - Session identifier
   * @param limit - Number of older messages to fetch (default: 10)
   * @returns true if messages were loaded, false if no more messages
   */
  async loadMoreMessages(sessionId: string, limit: number = 10): Promise<boolean> {
    const pilotSpaceStore = this.rootStore;
    if (!pilotSpaceStore || !pilotSpaceStore.hasMoreMessages) {
      return false;
    }

    // Calculate offset: skip the messages we already have
    const currentMessageCount = pilotSpaceStore.messages.length;
    const offset = currentMessageCount;

    runInAction(() => {
      pilotSpaceStore.setIsLoadingMoreMessages(true);
    });

    try {
      const authHeaders = await this.getAuthHeaders();
      const response = await fetch(
        `${API_BASE}/ai/sessions/${sessionId}/resume?limit=${limit}&offset=${offset}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders },
          body: JSON.stringify({}),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to load more messages: ${response.statusText}`);
      }

      const data: ResumeSessionResponse = await response.json();

      runInAction(() => {
        if (data.messages.length > 0) {
          // Convert and prepend older messages with content blocks
          const olderMessages = data.messages.map((msg: MessageResponse, index: number) => ({
            id: msg.id ?? `restored-older-${offset + index}`,
            role: msg.role as 'user' | 'assistant' | 'system',
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            metadata: msg.metadata,
            // Map content_blocks from backend (snake_case) to frontend (camelCase)
            contentBlocks: msg.content_blocks?.map((block) => {
              if (block.type === 'thinking') {
                return {
                  type: 'thinking' as const,
                  blockIndex: block.blockIndex,
                  content: block.content,
                };
              }
              if (block.type === 'text') {
                return { type: 'text' as const, content: block.content };
              }
              // tool_call
              return { type: 'tool_call' as const, toolCallId: block.toolCallId };
            }),
            // Map thinking_blocks from backend (snake_case) to frontend (camelCase)
            thinkingBlocks: msg.thinking_blocks?.map((block) => ({
              content: block.content,
              blockIndex: block.blockIndex,
              redacted: block.redacted,
            })),
          }));

          pilotSpaceStore.prependMessages(olderMessages);
        }

        // Update pagination state
        pilotSpaceStore.setMessagePaginationState(data.has_more, data.total_messages);
        pilotSpaceStore.setIsLoadingMoreMessages(false);
      });

      return data.messages.length > 0;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load more messages';
      runInAction(() => {
        this.error = errorMsg;
        pilotSpaceStore.setIsLoadingMoreMessages(false);
      });
      return false;
    }
  }

  /**
   * Find and resume the most recent session for a given context (e.g., a note).
   * If no matching session exists, does nothing.
   * @param contextId - The context ID (e.g., noteId)
   * @param contextType - The context type ('note' | 'issue' | 'project')
   * @returns true if a session was found and resumed, false otherwise
   */
  async resumeSessionForContext(
    contextId: string,
    _contextType: 'note' | 'issue' | 'project'
  ): Promise<boolean> {
    // Always do a targeted fetch filtered by context_id.
    // The mount-time fetchSessions() may still be in-flight (isLoading=true)
    // or may have returned all sessions without this context match, so we
    // need a dedicated fetch to find sessions for this specific context.
    await this.fetchSessions(5, contextId);

    // Find the most recent active session matching this context
    const now = new Date();
    const matchingSession = this.recentSessions.find(
      (s) => s.contextId === contextId && s.expiresAt > now
    );

    if (matchingSession) {
      await this.resumeSession(matchingSession.sessionId);
      return true;
    }

    return false;
  }

  /**
   * Delete session.
   * @param sessionId - Session identifier to delete
   */
  async deleteSession(sessionId: string): Promise<void> {
    try {
      const authHeaders = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE}/ai/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete session: ${response.statusText}`);
      }

      runInAction(() => {
        this.sessions = this.sessions.filter((s) => s.sessionId !== sessionId);

        // Clear selected session if it was deleted
        if (this.selectedSessionId === sessionId) {
          this.selectedSessionId = null;
        }
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to delete session';
      });
    }
  }

  /**
   * Search sessions by title or context.
   * @param query - Search query string
   */
  async searchSessions(query: string): Promise<void> {
    if (!query.trim()) {
      // Empty query - fetch all sessions
      await this.fetchSessions();
      return;
    }

    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      const authHeaders = await this.getAuthHeaders();
      const url = `${API_BASE}/ai/sessions?search=${encodeURIComponent(query)}&limit=50`;
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
      });

      if (!response.ok) {
        throw new Error(`Failed to search sessions: ${response.statusText}`);
      }

      const data = await response.json();

      runInAction(() => {
        this.sessions = data.sessions.map((s: SessionSummaryResponse) => ({
          sessionId: s.id,
          agentName: s.agent_name,
          contextId: s.context_id,
          contextType: s.context_type,
          contextHistory: s.context_history?.map((ctx: ContextHistoryResponse) => ({
            turn: ctx.turn,
            noteId: ctx.note_id,
            noteTitle: ctx.note_title,
            issueId: ctx.issue_id,
            blockIds: ctx.block_ids,
            selectedText: ctx.selected_text,
            timestamp: ctx.timestamp,
          })),
          createdAt: new Date(s.created_at),
          updatedAt: new Date(s.updated_at),
          turnCount: s.turn_count,
          expiresAt: new Date(s.expires_at),
          title: s.title,
          forkedFrom: s.forked_from,
          forkCount: s.fork_count,
        }));
        this.isLoading = false;
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to search sessions';
        this.isLoading = false;
      });
    }
  }

  /**
   * Fork a session for "what-if" exploration.
   * Sets the fork source on PilotSpaceStore so the next sendMessage
   * includes fork_session_id in the chat request body.
   * @param sourceSessionId - Session to fork from
   */
  prepareFork(sourceSessionId: string): void {
    const pilotSpaceStore = this.rootStore;
    if (!pilotSpaceStore) return;

    // Clear current session so the backend creates a fork (not resumes)
    pilotSpaceStore.clear();
    pilotSpaceStore.setForkSessionId(sourceSessionId);
  }

  /**
   * Clear error state.
   */
  clearError(): void {
    this.error = null;
  }

  /**
   * Reset store state.
   */
  reset(): void {
    this.sessions = [];
    this.isLoading = false;
    this.error = null;
    this.selectedSessionId = null;
  }
}

// ========================================
// API Response Types
// ========================================

interface ContextHistoryResponse {
  turn: number;
  note_id?: string;
  note_title?: string;
  issue_id?: string;
  block_ids?: string[];
  selected_text?: string;
  timestamp: string;
}

interface SessionSummaryResponse {
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

interface MessageResponse {
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
}

/**
 * Response from resume session endpoint with pagination support.
 */
interface ResumeSessionResponse {
  session_id: string;
  messages: MessageResponse[];
  context: Record<string, unknown>;
  turn_count: number;
  total_messages: number;
  has_more: boolean;
}
