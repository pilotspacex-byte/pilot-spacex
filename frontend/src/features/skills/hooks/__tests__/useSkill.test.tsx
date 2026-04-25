/**
 * Tests for `useSkill` (Phase 91 Plan 02 Task 2).
 *
 * Coverage:
 *  1. enabled=false when slug is undefined → skillsApi.get not called.
 *  2. Returns SkillDetail when slug provided + skillsApi.get resolves.
 *  3. 404 surfaces and does NOT retry (mock called exactly once).
 *  4. 500 retries once (mock called twice).
 *  5. Cache differentiates by slug (separate entries).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ApiError } from '@/services/api/client';
import type { SkillDetail } from '@/types/skill';

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
// Fixtures + setup
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    // Default `retry: false` would defeat the test for 500-retry behavior;
    // we want to honor the hook's own `retry` function. Leaving the global
    // default unset preserves it.
    defaultOptions: { queries: {}, mutations: { retry: false } },
  });
  return {
    queryClient,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  };
}

const sampleDetail: SkillDetail = {
  name: 'AI Context',
  description: 'desc',
  category: 'context',
  icon: 'Sparkles',
  examples: [],
  slug: 'ai-context',
  feature_module: null,
  updated_at: null,
  body: '# Body',
  reference_files: [],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useSkill', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is disabled when slug is undefined — skillsApi.get not called', async () => {
    const { wrapper } = createWrapper();
    const { useSkill } = await import('../useSkill');
    const { result } = renderHook(() => useSkill(undefined), { wrapper });

    // Give TanStack a tick to (not) run the queryFn.
    await new Promise((r) => setTimeout(r, 50));

    expect(mockGet).not.toHaveBeenCalled();
    // When disabled, the hook is in `pending` status without fetching.
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('returns SkillDetail when slug provided and skillsApi.get resolves', async () => {
    mockGet.mockResolvedValueOnce(sampleDetail);
    const { wrapper } = createWrapper();

    const { useSkill } = await import('../useSkill');
    const { result } = renderHook(() => useSkill('ai-context'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(sampleDetail);
    expect(mockGet).toHaveBeenCalledWith('ai-context');
  });

  it('does NOT retry on 404 (mock called exactly once)', async () => {
    const err = new ApiError({ status: 404, title: 'gone' });
    mockGet.mockRejectedValue(err);
    const { wrapper } = createWrapper();

    const { useSkill } = await import('../useSkill');
    const { result } = renderHook(() => useSkill('missing'), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 });

    expect(mockGet).toHaveBeenCalledTimes(1);
    expect(result.current.error?.status).toBe(404);
  });

  it('retries once on 500 (mock called twice)', async () => {
    const err = new ApiError({ status: 500, title: 'boom' });
    mockGet.mockRejectedValue(err);
    const { wrapper } = createWrapper();

    const { useSkill } = await import('../useSkill');
    const { result } = renderHook(() => useSkill('ai-context'), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });

    expect(mockGet).toHaveBeenCalledTimes(2);
    expect(result.current.error?.status).toBe(500);
  });

  it('caches separately for different slugs', async () => {
    mockGet.mockImplementation((slug: string) =>
      Promise.resolve({ ...sampleDetail, slug, name: slug }),
    );
    const { wrapper, queryClient } = createWrapper();

    const { useSkill, skillQueryKey } = await import('../useSkill');

    const { result: r1 } = renderHook(() => useSkill('alpha'), { wrapper });
    await waitFor(() => expect(r1.current.isSuccess).toBe(true));

    const { result: r2 } = renderHook(() => useSkill('beta'), { wrapper });
    await waitFor(() => expect(r2.current.isSuccess).toBe(true));

    expect(queryClient.getQueryData(skillQueryKey('alpha'))).toMatchObject({ slug: 'alpha' });
    expect(queryClient.getQueryData(skillQueryKey('beta'))).toMatchObject({ slug: 'beta' });
  });
});
