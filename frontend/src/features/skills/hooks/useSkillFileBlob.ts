/**
 * useSkillFileBlob — fetch a skill reference file as a blob URL (Plan 91-04).
 *
 * Used by the Peek Drawer's `skill-file:` branch. The blob URL is fed into
 * the existing renderers under
 * `frontend/src/features/artifacts/components/renderers/`
 * (MarkdownRenderer / CodeRenderer / ImageRenderer / etc.).
 *
 * Decision (D-91-02-C): blob fetching uses `apiClient` with
 * `responseType: 'blob'` rather than raw `fetch()`. This inherits:
 *   1. The auth interceptor (Bearer token, X-Workspace-Id).
 *   2. The 401-refresh-and-retry cycle.
 *   3. Uniform `ApiError` translation via the response interceptor.
 * `skillsApi.fileUrl` stays as a pure URL builder for callers that need an
 * absolute href (debugging, copy-link, external preview).
 *
 * Lifecycle: the hook owns the object URL and revokes it on unmount or on
 * key change — Chrome enforces a soft cap on outstanding object URLs.
 */
'use client';

import { useEffect, useRef } from 'react';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { apiClient, ApiError } from '@/services/api/client';

export interface SkillFileBlob {
  /** Object URL — revoked on unmount or query-key change. */
  url: string;
  mimeType: string;
  size: number;
}

/**
 * Encode a multi-segment path while preserving `/` so FastAPI's `:path`
 * matcher receives the original directory structure. Mirrors the helper in
 * `services/api/skills.ts` — kept colocated so the hook is self-contained.
 */
function encodeFilePath(path: string): string {
  return path.split('/').map(encodeURIComponent).join('/');
}

export function useSkillFileBlob(
  slug: string | undefined,
  path: string | undefined,
): UseQueryResult<SkillFileBlob, ApiError> {
  const enabled = Boolean(slug && path);

  const query = useQuery<SkillFileBlob, ApiError>({
    queryKey: ['skills', slug ?? '', 'file', path ?? ''],
    enabled,
    staleTime: 5 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: (failureCount, error) => {
      // 403/404 are deterministic (forbidden / does-not-exist) — no retry.
      if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
        return false;
      }
      return failureCount < 1;
    },
    queryFn: async () => {
      const url = `/skills/${encodeURIComponent(slug as string)}/files/${encodeFilePath(path as string)}`;
      // apiClient.get<Blob>(...) routes through the axios instance with
      // responseType:'blob' — interceptors run, ApiError translation happens.
      const blob = await apiClient.get<Blob>(url, { responseType: 'blob' });
      const objectUrl = URL.createObjectURL(blob);
      return { url: objectUrl, mimeType: blob.type, size: blob.size };
    },
  });

  // -------------------------------------------------------------------------
  // Object-URL lifecycle: revoke previous URL when the query data changes,
  // and revoke whatever is current on unmount. We use a ref instead of state
  // so the effect doesn't trigger an extra render and there's no stale-closure
  // hazard during fast key changes.
  // -------------------------------------------------------------------------
  const previousUrlRef = useRef<string | null>(null);

  useEffect(() => {
    const next = query.data?.url ?? null;
    const prev = previousUrlRef.current;
    if (prev && prev !== next) {
      URL.revokeObjectURL(prev);
    }
    previousUrlRef.current = next;
  }, [query.data?.url]);

  useEffect(() => {
    // Unmount cleanup — revoke whatever URL is currently held.
    return () => {
      if (previousUrlRef.current) {
        URL.revokeObjectURL(previousUrlRef.current);
        previousUrlRef.current = null;
      }
    };
  }, []);

  return query;
}
