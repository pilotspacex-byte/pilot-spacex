/**
 * Tests for `useSkillFileBlob` (Phase 91 Plan 02 Task 3).
 *
 * Coverage:
 *  1. Disabled when slug or path missing → apiClient.get not called.
 *  2. Fetches blob and returns { url, mimeType, size }.
 *  3. 404 surfaces and does NOT retry (called exactly once).
 *  4. 403 surfaces and does NOT retry.
 *  5. Revokes the previous URL when slug/path changes.
 *  6. Revokes URL on unmount.
 *  7. Encodes path segments while preserving `/`.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ApiError } from '@/services/api/client';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockApiGet = vi.fn();

vi.mock('@/services/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/services/api/client')>(
    '@/services/api/client',
  );
  return {
    ...actual,
    apiClient: {
      get: (...args: unknown[]) => mockApiGet(...args),
    },
  };
});

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: {}, mutations: { retry: false } },
  });
  return {
    queryClient,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  };
}

// jsdom does not implement createObjectURL/revokeObjectURL natively — we
// install vi.fn() shims and reset them per test. We track them by reference
// (not via vi.spyOn) so the strict generic typing of MockInstance does not
// fight the (Blob | MediaSource) signature.
const createObjectURLMock = vi.fn<(obj: Blob | MediaSource) => string>();
const revokeObjectURLMock = vi.fn<(url: string) => void>();
let counter = 0;

// Install once; reset implementations per test in beforeEach.
URL.createObjectURL = createObjectURLMock;
URL.revokeObjectURL = revokeObjectURLMock;

beforeEach(() => {
  vi.clearAllMocks();
  counter = 0;
  createObjectURLMock.mockImplementation(() => {
    counter += 1;
    return `blob:mock-url-${counter}`;
  });
  revokeObjectURLMock.mockImplementation(() => undefined);
});

afterEach(() => {
  // No-op: the function references stay; mockClear runs in beforeEach.
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useSkillFileBlob', () => {
  it('is disabled when slug or path missing — apiClient.get not called', async () => {
    const { wrapper } = createWrapper();
    const { useSkillFileBlob } = await import('../useSkillFileBlob');

    const { result: r1 } = renderHook(() => useSkillFileBlob(undefined, 'a.md'), { wrapper });
    const { result: r2 } = renderHook(() => useSkillFileBlob('skill', undefined), { wrapper });

    await new Promise((r) => setTimeout(r, 50));

    expect(mockApiGet).not.toHaveBeenCalled();
    expect(r1.current.fetchStatus).toBe('idle');
    expect(r2.current.fetchStatus).toBe('idle');
  });

  it('fetches blob and returns { url, mimeType, size }', async () => {
    const blob = new Blob(['hello'], { type: 'text/markdown' });
    mockApiGet.mockResolvedValueOnce(blob);
    const { wrapper } = createWrapper();

    const { useSkillFileBlob } = await import('../useSkillFileBlob');
    const { result } = renderHook(() => useSkillFileBlob('ai-context', 'architecture.md'), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      url: 'blob:mock-url-1',
      mimeType: 'text/markdown',
      size: blob.size,
    });
    expect(createObjectURLMock).toHaveBeenCalledWith(blob);
    // Verify responseType: 'blob' was passed to apiClient.
    expect(mockApiGet).toHaveBeenCalledWith(
      '/skills/ai-context/files/architecture.md',
      expect.objectContaining({ responseType: 'blob' }),
    );
  });

  it('404 surfaces and does NOT retry', async () => {
    const err = new ApiError({ status: 404, title: 'gone' });
    mockApiGet.mockRejectedValue(err);
    const { wrapper } = createWrapper();

    const { useSkillFileBlob } = await import('../useSkillFileBlob');
    const { result } = renderHook(() => useSkillFileBlob('ai-context', 'missing.md'), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 });

    expect(mockApiGet).toHaveBeenCalledTimes(1);
    expect(result.current.error?.status).toBe(404);
  });

  it('403 surfaces and does NOT retry', async () => {
    const err = new ApiError({ status: 403, title: 'forbidden' });
    mockApiGet.mockRejectedValue(err);
    const { wrapper } = createWrapper();

    const { useSkillFileBlob } = await import('../useSkillFileBlob');
    const { result } = renderHook(() => useSkillFileBlob('ai-context', 'secret.md'), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 3000 });

    expect(mockApiGet).toHaveBeenCalledTimes(1);
    expect(result.current.error?.status).toBe(403);
  });

  it('revokes the previous URL when slug/path changes', async () => {
    mockApiGet.mockImplementation(() =>
      Promise.resolve(new Blob(['x'], { type: 'text/plain' })),
    );
    const { wrapper } = createWrapper();

    const { useSkillFileBlob } = await import('../useSkillFileBlob');
    const { result, rerender } = renderHook(
      ({ slug, path }: { slug: string; path: string }) => useSkillFileBlob(slug, path),
      { wrapper, initialProps: { slug: 's1', path: 'a.md' } },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.url).toBe('blob:mock-url-1');

    // Switch to a new key — TanStack runs a fresh queryFn → new blob URL,
    // and the lifecycle effect must revoke the previous one.
    rerender({ slug: 's2', path: 'b.md' });

    await waitFor(() => expect(result.current.data?.url).toBe('blob:mock-url-2'));

    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:mock-url-1');
  });

  it('revokes URL on unmount', async () => {
    mockApiGet.mockResolvedValueOnce(new Blob(['y'], { type: 'text/plain' }));
    const { wrapper } = createWrapper();

    const { useSkillFileBlob } = await import('../useSkillFileBlob');
    const { result, unmount } = renderHook(
      () => useSkillFileBlob('ai-context', 'one.md'),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const issuedUrl = result.current.data?.url;
    expect(issuedUrl).toBe('blob:mock-url-1');

    unmount();

    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:mock-url-1');
  });

  it('encodes path segments while preserving `/`', async () => {
    mockApiGet.mockResolvedValueOnce(new Blob([''], { type: 'application/octet-stream' }));
    const { wrapper } = createWrapper();

    const { useSkillFileBlob } = await import('../useSkillFileBlob');
    const { result } = renderHook(
      () => useSkillFileBlob('ai-context', 'sub dir/nested file.md'),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockApiGet).toHaveBeenCalledWith(
      '/skills/ai-context/files/sub%20dir/nested%20file.md',
      expect.objectContaining({ responseType: 'blob' }),
    );
  });
});
