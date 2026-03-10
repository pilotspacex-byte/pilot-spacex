/**
 * useIssueExtraction Hook Tests — Feature 009
 * Tests for the issue extraction SSE hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { useIssueExtraction } from '../useIssueExtraction';

// Helper type for SSE options stored on globalThis
interface StoredSSEOptions {
  onMessage: (event: { type: string; data: unknown }) => void;
  onError?: (err: Error) => void;
  onComplete?: () => void;
}

// Mock SSEClient
const mockConnect = vi.fn();
const mockAbort = vi.fn();
let storedSSEOptions: StoredSSEOptions | null = null;

vi.mock('@/lib/sse-client', () => ({
  SSEClient: vi.fn().mockImplementation((options: StoredSSEOptions) => {
    storedSSEOptions = options;
    return {
      connect: mockConnect,
      abort: mockAbort,
    };
  }),
}));

// Mock supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}));

describe('useIssueExtraction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockConnect.mockResolvedValue(undefined);
    storedSSEOptions = null;
  });

  afterEach(() => {
    storedSSEOptions = null;
  });

  it('returns initial state', () => {
    const { result } = renderHook(() => useIssueExtraction());
    const [state] = result.current;

    expect(state.issues).toEqual([]);
    expect(state.isExtracting).toBe(false);
    expect(state.error).toBeNull();
    expect(state.isModalOpen).toBe(false);
  });

  it('starts extraction and sets isExtracting on startExtraction', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
      });
    });

    const [state] = result.current;
    // isModalOpen is always false (auto-approve mode replaced by review panel)
    expect(state.isModalOpen).toBe(false);
    expect(state.isExtracting).toBe(true);
    expect(mockConnect).toHaveBeenCalled();
  });

  it('closes modal and resets state on closeModal', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
      });
    });

    act(() => {
      result.current[1].closeModal();
    });

    const [state] = result.current;
    expect(state.isModalOpen).toBe(false);
    expect(state.isExtracting).toBe(false);
    expect(state.issues).toEqual([]);
    expect(state.error).toBeNull();
    expect(mockAbort).toHaveBeenCalled();
  });

  it('aborts on abort()', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
      });
    });

    act(() => {
      result.current[1].abort();
    });

    expect(mockAbort).toHaveBeenCalled();
    expect(result.current[0].isExtracting).toBe(false);
  });

  it('collects issues from SSE events', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
      });
    });

    expect(storedSSEOptions).not.toBeNull();

    act(() => {
      storedSSEOptions!.onMessage({
        type: 'issue',
        data: {
          index: 0,
          title: 'Test Issue',
          description: 'Description',
          priority: 2,
          labels: [],
          confidenceScore: 0.8,
          confidenceTag: 'explicit',
          sourceBlockIds: [],
          rationale: 'Test',
        },
      });
    });

    expect(result.current[0].issues).toHaveLength(1);
    expect(result.current[0].issues[0]!.title).toBe('Test Issue');
  });

  it('handles complete event and stops extracting', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
      });
    });

    expect(storedSSEOptions).not.toBeNull();

    act(() => {
      storedSSEOptions!.onMessage({ type: 'complete', data: { total_count: 0 } });
    });

    expect(result.current[0].isExtracting).toBe(false);
  });

  it('opens review panel after complete when issues were collected', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
        projectId: 'proj-1',
      });
    });

    act(() => {
      storedSSEOptions!.onMessage({
        type: 'issue',
        data: {
          index: 0,
          title: 'Test Issue',
          description: 'Description',
          priority: 2,
          labels: [],
          confidenceScore: 0.8,
          confidenceTag: 'explicit',
          sourceBlockIds: [],
          rationale: 'Test',
        },
      });
    });

    act(() => {
      storedSSEOptions!.onMessage({ type: 'complete', data: { total_count: 1 } });
    });

    expect(result.current[0].isReviewPanelOpen).toBe(true);
  });

  it('closeReviewPanel closes review panel without resetting issues', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
        projectId: 'proj-1',
      });
    });

    act(() => {
      storedSSEOptions!.onMessage({
        type: 'issue',
        data: {
          index: 0,
          title: 'Test Issue',
          description: '',
          priority: 2,
          labels: [],
          confidenceScore: 0.8,
          confidenceTag: 'explicit',
          sourceBlockIds: [],
          rationale: '',
        },
      });
    });

    act(() => {
      storedSSEOptions!.onMessage({ type: 'complete', data: { total_count: 1 } });
    });

    act(() => {
      result.current[1].closeReviewPanel();
    });

    expect(result.current[0].isReviewPanelOpen).toBe(false);
    // Issues are preserved after panel close
    expect(result.current[0].issues).toHaveLength(1);
  });

  it('handles error event', () => {
    const { result } = renderHook(() => useIssueExtraction());

    act(() => {
      result.current[1].startExtraction({
        noteId: 'note-1',
        noteTitle: 'Test Note',
        noteContent: { type: 'doc', content: [] },
        workspaceId: 'ws-1',
      });
    });

    expect(storedSSEOptions).not.toBeNull();

    act(() => {
      storedSSEOptions!.onMessage({
        type: 'error',
        data: { code: 'NO_API_KEY', message: 'API key not configured' },
      });
    });

    expect(result.current[0].error).toBe('API key not configured');
    expect(result.current[0].isExtracting).toBe(false);
  });
});
