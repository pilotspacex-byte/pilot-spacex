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
import type { AIStore } from './AIStore';

/**
 * API base URL for backend requests.
 * Falls back to localhost if not configured.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

/**
 * Session summary for list display.
 */
export interface SessionSummary {
  /** Session identifier */
  sessionId: string;
  /** Agent name (conversation, ai_context, etc.) */
  agentName: string;
  /** Context ID (note, issue, etc.) */
  contextId?: string;
  /** Context type for display */
  contextType?: 'note' | 'issue' | 'project';
  /** Session creation timestamp */
  createdAt: Date;
  /** Last activity timestamp */
  updatedAt: Date;
  /** Number of conversation turns */
  turnCount: number;
  /** Session expiration timestamp */
  expiresAt: Date;
  /** Session title (derived from context) */
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

  constructor(private rootStore: AIStore) {
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

  // ========================================
  // Actions - Session Management
  // ========================================

  /**
   * Fetch recent sessions for current user.
   * @param limit - Maximum number of sessions to fetch (default: 20)
   */
  async fetchSessions(limit = 20): Promise<void> {
    runInAction(() => {
      this.isLoading = true;
      this.error = null;
    });

    try {
      // Get sessions list from backend
      const response = await fetch(`${API_BASE}/ai/sessions?limit=${limit}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.statusText}`);
      }

      const data = await response.json();

      runInAction(() => {
        this.sessions = data.sessions.map((s: SessionSummaryResponse) => ({
          sessionId: s.session_id,
          agentName: s.agent_name,
          contextId: s.context_id,
          contextType: s.context_type,
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
        this.error = err instanceof Error ? err.message : 'Failed to fetch sessions';
        this.isLoading = false;
      });
    }
  }

  /**
   * Resume existing session in PilotSpaceStore.
   * @param sessionId - Session identifier to resume
   */
  async resumeSession(sessionId: string): Promise<void> {
    const session = this.sessions.find((s) => s.sessionId === sessionId);
    if (!session) {
      console.error(`Session ${sessionId} not found`);
      return;
    }

    try {
      // Resume session to fetch session history
      const response = await fetch(`${API_BASE}/ai/sessions/${sessionId}/resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch session messages: ${response.statusText}`);
      }

      const data = await response.json();

      // Load messages into PilotSpaceStore
      runInAction(() => {
        const pilotSpaceStore = this.rootStore.pilotSpace;
        if (pilotSpaceStore) {
          // Clear current conversation
          pilotSpaceStore.clear();

          // Set session ID
          pilotSpaceStore.setSessionId(sessionId);

          // Load messages
          data.messages.forEach((msg: MessageResponse) => {
            pilotSpaceStore.addMessage({
              id: msg.id,
              role: msg.role as 'user' | 'assistant' | 'system',
              content: msg.content,
              timestamp: new Date(msg.created_at),
              metadata: msg.metadata,
            });
          });

          // Update selected session
          this.selectedSessionId = sessionId;
        }
      });
    } catch (err) {
      runInAction(() => {
        this.error = err instanceof Error ? err.message : 'Failed to resume session';
      });
    }
  }

  /**
   * Find and resume the most recent session for a given context (e.g., a note).
   * If no matching session exists, does nothing.
   * @param contextId - The context ID (e.g., noteId)
   * @param contextType - The context type ('note' | 'issue' | 'project')
   */
  async resumeSessionForContext(
    contextId: string,
    contextType: 'note' | 'issue' | 'project'
  ): Promise<void> {
    // Ensure sessions are loaded
    if (this.sessions.length === 0 && !this.isLoading) {
      await this.fetchSessions();
    }

    // Find the most recent active session matching this context
    const now = new Date();
    const matchingSession = this.recentSessions.find(
      (s) => s.contextId === contextId && s.contextType === contextType && s.expiresAt > now
    );

    if (matchingSession) {
      await this.resumeSession(matchingSession.sessionId);
    }
  }

  /**
   * Delete session.
   * @param sessionId - Session identifier to delete
   */
  async deleteSession(sessionId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE}/ai/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
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
   * Fork a session for "what-if" exploration.
   * Sets the fork source on PilotSpaceStore so the next sendMessage
   * includes fork_session_id in the chat request body.
   * @param sourceSessionId - Session to fork from
   */
  prepareFork(sourceSessionId: string): void {
    const pilotSpaceStore = this.rootStore.pilotSpace;
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

interface SessionSummaryResponse {
  session_id: string;
  agent_name: string;
  context_id?: string;
  context_type?: 'note' | 'issue' | 'project';
  created_at: string;
  updated_at: string;
  turn_count: number;
  expires_at: string;
  title?: string;
  forked_from?: string;
  fork_count?: number;
}

interface MessageResponse {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}
