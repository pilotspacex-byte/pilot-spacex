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
}

interface MessageResponse {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}
