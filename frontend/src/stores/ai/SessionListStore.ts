/**
 * SessionListStore - Manages conversation session list and operations.
 * Handles fetching, resuming, deleting sessions, and session metadata display.
 * @module stores/ai/SessionListStore
 * @see T075-T079 (Session Persistence UI)
 */
import { makeAutoObservable, runInAction } from 'mobx';
import { supabase } from '@/lib/supabase';
import type { PilotSpaceStore } from './PilotSpaceStore';
import { mapMessageResponse, mapSessionSummary } from './SessionListMappers';
import type { ResumeSessionResponse, SessionSummary } from './types/session';

// Re-export public types for backward compatibility
export type { ContextEntry, SessionSummary } from './types/session';

/**
 * API base URL for backend requests.
 * Falls back to localhost if not configured.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

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
   * Get active sessions (all sessions are now visible; backend handles expiry).
   */
  get activeSessions(): SessionSummary[] {
    return [...this.sessions];
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
        const fetched = data.sessions.map(mapSessionSummary);

        if (contextId) {
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

      runInAction(() => {
        const pilotSpaceStore = this.rootStore;
        if (pilotSpaceStore) {
          pilotSpaceStore.messages = [];
          pilotSpaceStore.setSessionId(sessionId);

          data.messages.forEach((msg, index) => {
            pilotSpaceStore.addMessage(mapMessageResponse(msg, `restored-${index}`));
          });

          pilotSpaceStore.setMessagePaginationState(data.has_more, data.total_messages);
          this.selectedSessionId = sessionId;

          // Restore pendingQuestion if the last assistant message has unanswered questions
          const lastAssistant = [...pilotSpaceStore.messages]
            .reverse()
            .find((m) => m.role === 'assistant');
          if (lastAssistant) {
            const pendingList = lastAssistant.questionDataList?.filter((qd) => !qd.answers);
            const pendingSingle =
              lastAssistant.questionData && !lastAssistant.questionData.answers
                ? lastAssistant.questionData
                : null;

            if (pendingList && pendingList.length > 0) {
              pilotSpaceStore.pendingQuestion = {
                questionId: pendingList[0]!.questionId,
                questions: pendingList.flatMap((qd) => qd.questions),
              };
            } else if (pendingSingle) {
              pilotSpaceStore.pendingQuestion = {
                questionId: pendingSingle.questionId,
                questions: pendingSingle.questions,
              };
            }
          }
        }
      });
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to resume session';
      runInAction(() => {
        this.error = errorMsg;
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

    const offset = pilotSpaceStore.messages.length;

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
          const olderMessages = data.messages.map((msg, index) =>
            mapMessageResponse(msg, `restored-older-${offset + index}`)
          );
          pilotSpaceStore.prependMessages(olderMessages);
        }

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
    await this.fetchSessions(5, contextId);

    const matchingSession = this.recentSessions.find((s) => s.contextId === contextId);

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
        this.sessions = data.sessions.map(mapSessionSummary);
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
