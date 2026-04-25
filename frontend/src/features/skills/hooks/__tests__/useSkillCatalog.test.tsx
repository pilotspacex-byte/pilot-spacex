/**
 * Tests for `useSkillCatalog` (Phase 91 Plan 02 Task 2).
 *
 * Coverage:
 *  1. Returns Skill[] on success.
 *  2. Surfaces ApiError on rejection.
 *  3. Cache key is `['skills', 'catalog']` (verified via QueryCache).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ApiError } from '@/services/api/client';
import type { Skill } from '@/types/skill';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockList = vi.fn();
const mockGet = vi.fn();
const mockFileUrl = vi.fn();

vi.mock('@/services/api/skills', () => ({
  skillsApi: {
    list: (...args: unknown[]) => mockList(...args),
    get: (...args: unknown[]) => mockGet(...args),
    fileUrl: (...args: unknown[]) => mockFileUrl(...args),
  },
}));

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    queryClient,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  };
}

const sampleSkill: Skill = {
  name: 'AI Context',
  description: 'desc',
  category: 'context',
  icon: 'Sparkles',
  examples: [],
  slug: 'ai-context',
  feature_module: null,
  reference_files: [],
  updated_at: null,
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useSkillCatalog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns the Skill[] when skillsApi.list resolves', async () => {
    mockList.mockResolvedValueOnce([sampleSkill]);
    const { wrapper } = createWrapper();

    const { useSkillCatalog } = await import('../useSkillCatalog');
    const { result } = renderHook(() => useSkillCatalog(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([sampleSkill]);
    expect(mockList).toHaveBeenCalledTimes(1);
  });

  it('surfaces ApiError when skillsApi.list rejects', async () => {
    // Reject every call — the hook's `retry: 1` will retry once before the
    // error settles, so a `mockRejectedValueOnce` would let the retry succeed
    // with `undefined` and the test would hang on `waitFor(isError)`.
    const err = new ApiError({ status: 500, title: 'boom' });
    mockList.mockRejectedValue(err);
    const { wrapper } = createWrapper();

    const { useSkillCatalog } = await import('../useSkillCatalog');
    const { result } = renderHook(() => useSkillCatalog(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });

    expect(result.current.error).toBe(err);
    expect(result.current.error?.status).toBe(500);
  });

  it('caches under the SKILLS_CATALOG_QUERY_KEY (["skills", "catalog"])', async () => {
    mockList.mockResolvedValueOnce([sampleSkill]);
    const { wrapper, queryClient } = createWrapper();

    const { useSkillCatalog, SKILLS_CATALOG_QUERY_KEY } = await import('../useSkillCatalog');
    const { result } = renderHook(() => useSkillCatalog(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(SKILLS_CATALOG_QUERY_KEY).toEqual(['skills', 'catalog']);

    const cached = queryClient.getQueryData(SKILLS_CATALOG_QUERY_KEY);
    expect(cached).toEqual([sampleSkill]);
  });
});
