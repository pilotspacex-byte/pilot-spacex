/**
 * SessionListStore fork feature tests.
 *
 * Tests for:
 * - sessionsWithForks computed grouping
 * - prepareFork() action
 * - Fork field mapping in fetchSessions
 *
 * @see SessionListStore.sessionsWithForks
 * @see SessionListStore.prepareFork
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runInAction } from 'mobx';
import { SessionListStore, type SessionSummary } from '../SessionListStore';
import type { PilotSpaceStore } from '../PilotSpaceStore';

// ========================================
// Helpers
// ========================================

function makeSession(overrides: Partial<SessionSummary> & { sessionId: string }): SessionSummary {
  const now = new Date();
  return {
    agentName: 'conversation',
    createdAt: now,
    updatedAt: now,
    turnCount: 1,
    expiresAt: new Date(now.getTime() + 3600000),
    ...overrides,
  };
}

function createMockPilotSpaceStore(overrides?: Record<string, unknown>): PilotSpaceStore {
  return {
    clear: vi.fn(),
    setForkSessionId: vi.fn(),
    workspaceId: null,
    ...overrides,
  } as unknown as PilotSpaceStore;
}

// ========================================
// Tests
// ========================================

describe('SessionListStore - Fork Features', () => {
  let store: SessionListStore;
  let mockRootStore: PilotSpaceStore;

  beforeEach(() => {
    vi.clearAllMocks();
    mockRootStore = createMockPilotSpaceStore();
    store = new SessionListStore(mockRootStore);
  });

  describe('sessionsWithForks computed', () => {
    it('should group root sessions with their forks', () => {
      const parent = makeSession({ sessionId: 'parent-1', updatedAt: new Date('2025-01-02') });
      const fork1 = makeSession({
        sessionId: 'fork-1',
        forkedFrom: 'parent-1',
        updatedAt: new Date('2025-01-03'),
      });
      const fork2 = makeSession({
        sessionId: 'fork-2',
        forkedFrom: 'parent-1',
        updatedAt: new Date('2025-01-04'),
      });

      runInAction(() => {
        store.sessions = [parent, fork1, fork2];
      });

      const result = store.sessionsWithForks;

      expect(result).toHaveLength(1);
      expect(result[0]!.session.sessionId).toBe('parent-1');
      expect(result[0]!.forks).toHaveLength(2);
      expect(result[0]!.forks.map((f) => f.sessionId)).toContain('fork-1');
      expect(result[0]!.forks.map((f) => f.sessionId)).toContain('fork-2');
    });

    it('should return empty forks array for sessions without forks', () => {
      const session1 = makeSession({ sessionId: 'session-1', updatedAt: new Date('2025-01-01') });
      const session2 = makeSession({ sessionId: 'session-2', updatedAt: new Date('2025-01-02') });

      runInAction(() => {
        store.sessions = [session1, session2];
      });

      const result = store.sessionsWithForks;

      expect(result).toHaveLength(2);
      expect(result[0]!.forks).toEqual([]);
      expect(result[1]!.forks).toEqual([]);
    });

    it('should exclude orphan forks whose parent is not in the list', () => {
      const root = makeSession({ sessionId: 'root-1', updatedAt: new Date('2025-01-01') });
      const orphanFork = makeSession({
        sessionId: 'orphan-fork',
        forkedFrom: 'deleted-parent',
        updatedAt: new Date('2025-01-02'),
      });

      runInAction(() => {
        store.sessions = [root, orphanFork];
      });

      const result = store.sessionsWithForks;

      // Only root appears; orphan fork is not in roots and its parent is missing
      expect(result).toHaveLength(1);
      expect(result[0]!.session.sessionId).toBe('root-1');
      expect(result[0]!.forks).toEqual([]);
    });

    it('should handle mixed roots, forks, and orphans correctly', () => {
      const parentA = makeSession({ sessionId: 'parent-a', updatedAt: new Date('2025-01-01') });
      const forkA1 = makeSession({
        sessionId: 'fork-a1',
        forkedFrom: 'parent-a',
        updatedAt: new Date('2025-01-02'),
      });
      const parentB = makeSession({ sessionId: 'parent-b', updatedAt: new Date('2025-01-03') });
      const orphan = makeSession({
        sessionId: 'orphan',
        forkedFrom: 'nonexistent',
        updatedAt: new Date('2025-01-04'),
      });

      runInAction(() => {
        store.sessions = [parentA, forkA1, parentB, orphan];
      });

      const result = store.sessionsWithForks;
      const rootIds = result.map((r) => r.session.sessionId);

      expect(rootIds).toContain('parent-a');
      expect(rootIds).toContain('parent-b');
      expect(rootIds).not.toContain('orphan');

      const parentAEntry = result.find((r) => r.session.sessionId === 'parent-a');
      expect(parentAEntry?.forks).toHaveLength(1);
      expect(parentAEntry?.forks[0]!.sessionId).toBe('fork-a1');

      const parentBEntry = result.find((r) => r.session.sessionId === 'parent-b');
      expect(parentBEntry?.forks).toEqual([]);
    });

    it('should return empty array when no sessions exist', () => {
      expect(store.sessionsWithForks).toEqual([]);
    });
  });

  describe('prepareFork', () => {
    it('should call pilotSpaceStore.clear() and setForkSessionId()', () => {
      const mockClear = vi.fn();
      const mockSetForkSessionId = vi.fn();
      mockRootStore = createMockPilotSpaceStore({
        clear: mockClear,
        setForkSessionId: mockSetForkSessionId,
      });
      store = new SessionListStore(mockRootStore);

      store.prepareFork('source-session-123');

      expect(mockClear).toHaveBeenCalledOnce();
      expect(mockSetForkSessionId).toHaveBeenCalledOnce();
      expect(mockSetForkSessionId).toHaveBeenCalledWith('source-session-123');
    });

    it('should call clear() before setForkSessionId()', () => {
      const callOrder: string[] = [];
      mockRootStore = createMockPilotSpaceStore({
        clear: vi.fn(() => callOrder.push('clear')),
        setForkSessionId: vi.fn(() => callOrder.push('setForkSessionId')),
      });
      store = new SessionListStore(mockRootStore);

      store.prepareFork('session-abc');

      expect(callOrder).toEqual(['clear', 'setForkSessionId']);
    });
  });

  describe('fetchSessions fork field mapping', () => {
    it('should map forked_from and fork_count from API response', async () => {
      const mockResponse = {
        sessions: [
          {
            id: 'sess-1',
            agent_name: 'conversation',
            created_at: '2025-01-01T00:00:00Z',
            updated_at: '2025-01-01T01:00:00Z',
            turn_count: 5,
            expires_at: '2025-01-02T00:00:00Z',
            title: 'Parent session',
            forked_from: undefined,
            fork_count: 2,
          },
          {
            id: 'sess-2',
            agent_name: 'conversation',
            created_at: '2025-01-01T02:00:00Z',
            updated_at: '2025-01-01T03:00:00Z',
            turn_count: 3,
            expires_at: '2025-01-02T00:00:00Z',
            title: 'Forked session',
            forked_from: 'sess-1',
            fork_count: 0,
          },
        ],
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(mockResponse),
      });

      await store.fetchSessions();

      expect(store.sessions).toHaveLength(2);

      const parent = store.sessions.find((s) => s.sessionId === 'sess-1');
      expect(parent?.forkCount).toBe(2);
      expect(parent?.forkedFrom).toBeUndefined();

      const fork = store.sessions.find((s) => s.sessionId === 'sess-2');
      expect(fork?.forkedFrom).toBe('sess-1');
      expect(fork?.forkCount).toBe(0);
    });
  });
});
