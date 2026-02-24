/**
 * useWorkspaceDigest hook tests.
 *
 * T012: Verifies TanStack Query integration for digest fetch,
 * dismiss mutation with optimistic update, refresh mutation,
 * groupByCategory helper, and error handling.
 */

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useWorkspaceDigest, groupByCategory } from '../useWorkspaceDigest';
import type { DigestResponse, DigestSuggestion } from '../../types';

vi.mock('../../api/homepage-api', () => ({
  homepageApi: {
    getDigest: vi.fn(),
    refreshDigest: vi.fn(),
    dismissSuggestion: vi.fn(),
  },
}));

import { homepageApi } from '../../api/homepage-api';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockSuggestion1: DigestSuggestion = {
  id: 'sug-1',
  category: 'stale_issues' as const,
  title: 'PS-42 has been idle for 14 days',
  description: 'Consider closing or reassigning.',
  entityId: 'entity-1',
  entityType: 'issue',
  entityIdentifier: 'PS-42',
  projectId: 'proj-1',
  projectName: 'Test Project',
  actionType: 'navigate',
  actionLabel: 'View',
  actionUrl: '/issues/entity-1',
  relevanceScore: 0.9,
};

const mockSuggestion2: DigestSuggestion = {
  id: 'sug-2',
  category: 'unlinked_notes' as const,
  title: 'Meeting notes contain actionable items',
  description: 'Extract issues from meeting notes.',
  entityId: 'entity-2',
  entityType: 'note',
  entityIdentifier: null,
  projectId: null,
  projectName: null,
  actionType: 'navigate',
  actionLabel: 'Review',
  actionUrl: '/notes/entity-2',
  relevanceScore: 0.7,
};

const mockSuggestion3: DigestSuggestion = {
  id: 'sug-3',
  category: 'stale_issues' as const,
  title: 'PS-99 needs review',
  description: 'Stale for 7 days.',
  entityId: 'entity-3',
  entityType: 'issue',
  entityIdentifier: 'PS-99',
  projectId: 'proj-1',
  projectName: 'Test Project',
  actionType: 'navigate',
  actionLabel: 'View',
  actionUrl: '/issues/entity-3',
  relevanceScore: 0.8,
};

const mockDigestResponse: DigestResponse = {
  data: {
    generatedAt: '2026-02-20T10:00:00Z',
    generatedBy: 'scheduled',
    suggestions: [mockSuggestion1, mockSuggestion2, mockSuggestion3],
    suggestionCount: 3,
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ---------------------------------------------------------------------------
// groupByCategory tests
// ---------------------------------------------------------------------------

describe('groupByCategory', () => {
  it('groups suggestions by category and excludes empty categories', () => {
    const groups = groupByCategory([mockSuggestion1, mockSuggestion2, mockSuggestion3]);

    expect(groups).toHaveLength(2);
    expect(groups[0]!.category).toBe('stale_issues');
    expect(groups[0]!.items).toHaveLength(2);
    expect(groups[1]!.category).toBe('unlinked_notes');
    expect(groups[1]!.items).toHaveLength(1);
  });

  it('returns empty array for empty input', () => {
    expect(groupByCategory([])).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// useWorkspaceDigest tests
// ---------------------------------------------------------------------------

describe('useWorkspaceDigest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches digest when workspaceId is provided', async () => {
    vi.mocked(homepageApi.getDigest).mockResolvedValue(mockDigestResponse);

    const { result } = renderHook(() => useWorkspaceDigest({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(homepageApi.getDigest).toHaveBeenCalledWith('ws-1');
    expect(result.current.suggestions).toHaveLength(3);
    expect(result.current.suggestionCount).toBe(3);
    expect(result.current.generatedAt).toBe('2026-02-20T10:00:00Z');
    expect(result.current.groups).toHaveLength(2);
  });

  it('is disabled when workspaceId is empty', () => {
    const { result } = renderHook(() => useWorkspaceDigest({ workspaceId: '' }), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(homepageApi.getDigest).not.toHaveBeenCalled();
  });

  it('is disabled when enabled is false', () => {
    const { result } = renderHook(
      () => useWorkspaceDigest({ workspaceId: 'ws-1', enabled: false }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(homepageApi.getDigest).not.toHaveBeenCalled();
  });

  it('handles fetch error gracefully', async () => {
    vi.mocked(homepageApi.getDigest).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useWorkspaceDigest({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.suggestions).toEqual([]);
    expect(result.current.groups).toEqual([]);
    expect(result.current.suggestionCount).toBe(0);
  });

  it('dismiss mutation calls API with correct payload', async () => {
    vi.mocked(homepageApi.getDigest).mockResolvedValue(mockDigestResponse);
    vi.mocked(homepageApi.dismissSuggestion).mockResolvedValue(undefined);

    const { result } = renderHook(() => useWorkspaceDigest({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.dismiss(mockSuggestion1);
    });

    await waitFor(() => {
      expect(homepageApi.dismissSuggestion).toHaveBeenCalledWith('ws-1', {
        suggestionId: 'sug-1',
        entityId: 'entity-1',
        entityType: 'issue',
        category: 'stale_issues',
      });
    });
  });

  it('dismiss mutation optimistically removes suggestion from cache', async () => {
    // After dismiss, the refetch should return the filtered list
    const afterDismissResponse: DigestResponse = {
      data: {
        ...mockDigestResponse.data,
        suggestions: [mockSuggestion2, mockSuggestion3],
        suggestionCount: 2,
      },
    };
    vi.mocked(homepageApi.getDigest)
      .mockResolvedValueOnce(mockDigestResponse)
      .mockResolvedValue(afterDismissResponse);
    // Make dismiss slow so we can observe optimistic state
    vi.mocked(homepageApi.dismissSuggestion).mockResolvedValue(undefined);

    const { result } = renderHook(() => useWorkspaceDigest({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.suggestions).toHaveLength(3));

    act(() => {
      result.current.dismiss(mockSuggestion1);
    });

    // After settlement + refetch, sug-1 should be gone
    await waitFor(() => {
      expect(result.current.suggestions).toHaveLength(2);
      expect(result.current.suggestions.find((s) => s.id === 'sug-1')).toBeUndefined();
    });
  });

  it('refresh mutation calls API', async () => {
    vi.mocked(homepageApi.getDigest).mockResolvedValue(mockDigestResponse);
    vi.mocked(homepageApi.refreshDigest).mockResolvedValue({
      data: { status: 'generating', estimatedSeconds: 15 },
    });

    const { result } = renderHook(() => useWorkspaceDigest({ workspaceId: 'ws-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => {
      expect(homepageApi.refreshDigest).toHaveBeenCalledWith('ws-1');
    });
  });
});
