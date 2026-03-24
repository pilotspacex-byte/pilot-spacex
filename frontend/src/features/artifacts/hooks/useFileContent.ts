'use client';

/**
 * useFileContent — Fetches file content from a Supabase Storage signed URL.
 *
 * IMPORTANT: Uses window.fetch() (i.e., the global fetch), NOT apiClient.
 * Signed URLs are external Supabase Storage URLs that include the auth token
 * in the URL query string. apiClient injects an Authorization: Bearer header
 * that Supabase Storage rejects with 403 — use fetch() directly.
 *
 * staleTime: 55 minutes max. Supabase signed URLs expire at 60 minutes.
 * retry: false. A 403 means the URL has expired — retrying won't help.
 * Only fetches when the modal is open and the renderer needs content.
 * Image and download renderers do not need fetched content — skipped via enabled.
 *
 * Binary mode: xlsx, docx, pptx renderer types return ArrayBuffer instead of
 * string. Office parsers (SheetJS, mammoth, pptxviewjs) require raw binary data.
 */

import { useQuery } from '@tanstack/react-query';
import type { RendererType } from '../utils/mime-type-router';

/** Renderer types that require ArrayBuffer content (binary Office formats). */
export const BINARY_RENDERER_TYPES: Set<RendererType> = new Set(['xlsx', 'docx', 'pptx']);

export const artifactKeys = {
  all: ['artifacts'] as const,
  signedUrl: (artifactId: string) => ['artifacts', 'signed-url', artifactId] as const,
  fileContent: (signedUrl: string) => ['file-content', signedUrl] as const,
};

export interface UseFileContentResult {
  /** The fetched content: string for text-based renderers, ArrayBuffer for binary (Office) renderers */
  content: string | ArrayBuffer | undefined;
  /** True while the fetch is in-flight */
  isLoading: boolean;
  /** True if any fetch error occurred */
  isError: boolean;
  /**
   * True when a 403 was returned — signals that the signed URL has expired.
   * The UI should show a "Link expired" message with a refresh action.
   */
  isExpired: boolean;
}

/**
 * Fetches file content from a Supabase Storage signed URL when the modal is open.
 *
 * Returns:
 * - ArrayBuffer for binary Office renderers (xlsx, docx, pptx) — required by Office parsers
 * - string for all text-based renderers (markdown, json, code, text, csv, html-preview)
 *
 * Skips fetching for:
 * - 'image' renderer — the component uses the signed URL as <img src> directly
 * - 'download' renderer — the component renders a download button with the URL
 * - Closed modal (open === false) — avoid background fetches
 * - Empty URL — guard against uninitialized state
 *
 * @param signedUrl - The Supabase Storage signed URL for the file
 * @param rendererType - Which renderer will display this content
 * @param open - Whether the preview modal is currently open
 */
export function useFileContent(
  signedUrl: string,
  rendererType: RendererType,
  open: boolean
): UseFileContentResult {
  const shouldFetch =
    open && !!signedUrl && rendererType !== 'image' && rendererType !== 'download';

  const { data, error, isLoading, isError } = useQuery({
    queryKey: artifactKeys.fileContent(signedUrl),
    queryFn: async () => {
      // Use fetch() directly — DO NOT use apiClient (it injects Authorization header)
      const res = await fetch(signedUrl);
      if (res.status === 403) throw new Error('URL_EXPIRED');
      if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
      // Binary mode: Office formats require ArrayBuffer for parsers (SheetJS, mammoth, pptxviewjs)
      if (BINARY_RENDERER_TYPES.has(rendererType)) {
        return res.arrayBuffer();
      }
      return res.text();
    },
    enabled: shouldFetch,
    staleTime: 1000 * 55 * 60, // 55 minutes — signed URLs expire at 60 min
    gcTime: 1000 * 60 * 60, // 1 hour cache retention after modal closes
    retry: false, // Do NOT retry 403 — show "Link expired" UI immediately
  });

  const isExpired = isError && (error as Error)?.message === 'URL_EXPIRED';

  return {
    content: data,
    isLoading: shouldFetch ? isLoading : false,
    isError,
    isExpired,
  };
}
