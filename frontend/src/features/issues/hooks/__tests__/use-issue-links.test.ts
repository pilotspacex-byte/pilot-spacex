/**
 * useIssueLinks hook tests.
 *
 * Verifies TanStack Query integration, enabled guard, and link-type splitting.
 */

import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useIssueLinks } from '../use-issue-links';
import type { IntegrationLink } from '@/types';

vi.mock('@/services/api/integrations', () => ({
  integrationsApi: {
    getIssueLinks: vi.fn(),
  },
}));

import { integrationsApi } from '@/services/api/integrations';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function createLink(overrides: Partial<IntegrationLink>): IntegrationLink {
  return {
    id: 'link-1',
    issueId: 'issue-1',
    integrationType: 'github_pr',
    externalId: 'ext-1',
    externalUrl: 'https://github.com/org/repo/pull/1',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Wrapper
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
// Tests
// ---------------------------------------------------------------------------

describe('useIssueLinks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches links when workspaceId and issueId are provided', async () => {
    const links: IntegrationLink[] = [createLink({ id: 'link-1', link_type: 'pull_request' })];
    vi.mocked(integrationsApi.getIssueLinks).mockResolvedValue(links);

    const { result } = renderHook(() => useIssueLinks('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(integrationsApi.getIssueLinks).toHaveBeenCalledWith('ws-1', 'issue-1');
    expect(result.current.allLinks).toEqual(links);
  });

  it('does not fetch when workspaceId is empty', () => {
    const { result } = renderHook(() => useIssueLinks('', 'issue-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(integrationsApi.getIssueLinks).not.toHaveBeenCalled();
  });

  it('does not fetch when issueId is empty', () => {
    const { result } = renderHook(() => useIssueLinks('ws-1', ''), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(integrationsApi.getIssueLinks).not.toHaveBeenCalled();
  });

  it('splits links by type correctly', async () => {
    const mixed: IntegrationLink[] = [
      createLink({ id: 'pr-1', link_type: 'pull_request', integrationType: 'github_pr' }),
      createLink({ id: 'pr-2', link_type: 'pull_request', integrationType: 'github_pr' }),
      createLink({ id: 'commit-1', link_type: 'commit', integrationType: 'github_issue' }),
      createLink({ id: 'branch-1', link_type: 'branch', integrationType: 'github_issue' }),
    ];
    vi.mocked(integrationsApi.getIssueLinks).mockResolvedValue(mixed);

    const { result } = renderHook(() => useIssueLinks('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.pullRequests).toHaveLength(2);
    expect(result.current.commits).toHaveLength(1);
    expect(result.current.branches).toHaveLength(1);
    expect(result.current.allLinks).toHaveLength(4);

    expect(result.current.pullRequests.every((l) => l.link_type === 'pull_request')).toBe(true);
    expect(result.current.commits.every((l) => l.link_type === 'commit')).toBe(true);
    expect(result.current.branches.every((l) => l.link_type === 'branch')).toBe(true);
  });

  it('returns empty arrays as defaults before data loads', () => {
    // Never resolve so the query stays in loading state
    vi.mocked(integrationsApi.getIssueLinks).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useIssueLinks('ws-1', 'issue-1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.commits).toEqual([]);
    expect(result.current.pullRequests).toEqual([]);
    expect(result.current.branches).toEqual([]);
    expect(result.current.allLinks).toEqual([]);
  });
});
