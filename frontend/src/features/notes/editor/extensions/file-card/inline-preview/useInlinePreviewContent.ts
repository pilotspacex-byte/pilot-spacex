'use client';

/**
 * useInlinePreviewContent — Lazy content-fetching hook for inline file previews.
 *
 * Fetch strategy:
 * 1. IntersectionObserver (threshold: 0.1) fires when 10% of the card enters the viewport.
 * 2. On first intersection: fetch signed URL via useArtifactSignedUrl (enabled by isVisible).
 * 3. Once signed URL is ready: fetch text content via useFileContent.
 *
 * This ensures cards scrolled past without being seen never trigger network requests.
 * All React hooks are called unconditionally — enabled flags control actual fetching.
 *
 * Returns `signedUrl` so the InlinePreviewHeader download button can use it directly
 * without an additional context lookup.
 */

import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import type { RendererType } from '@/features/artifacts/utils/mime-type-router';
import { useArtifactSignedUrl } from '@/features/artifacts/hooks/use-artifact-signed-url';
import { useFileContent } from '@/features/artifacts/hooks/useFileContent';
import { useFilePreviewConfigSafe } from './FilePreviewConfigContext';
import { getInlineRendererType } from './is-inline-previewable';
import type { InlineRendererType } from './is-inline-previewable';

export interface UseInlinePreviewContentResult {
  /** Attach to the card container element to trigger IntersectionObserver. */
  containerRef: RefObject<HTMLDivElement | null>;
  /** The fetched content: string for text types, ArrayBuffer for binary Office types. */
  content: string | ArrayBuffer | undefined;
  /** The signed URL for the artifact (used by the download button). */
  signedUrl: string;
  /** True while signed URL or content fetch is in-flight. */
  isLoading: boolean;
  /** True if any fetch error occurred. */
  isError: boolean;
  /** The resolved inline renderer type, or null if not previewable. */
  rendererType: InlineRendererType | null;
}

/**
 * Lazily fetches file content for inline preview when the card enters the viewport.
 *
 * @param artifactId - The artifact's UUID, or null if not yet ready
 * @param mimeType   - The file's MIME type
 * @param filename   - The file's name (used for extension-based renderer routing)
 */
export function useInlinePreviewContent(
  artifactId: string | null,
  mimeType: string,
  filename: string
): UseInlinePreviewContentResult {
  // Resolve renderer type up-front (pure calculation, no hooks involved)
  const rendererType = getInlineRendererType(mimeType, filename);

  // IntersectionObserver ref + visibility state
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  // One-shot IntersectionObserver — disconnect after first intersection to avoid
  // re-triggering on scroll-out/scroll-in cycles.
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    // If already visible (e.g. SSR hydration, fast re-mount), skip observer
    if (isVisible) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.disconnect();
          }
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(element);
    return () => observer.disconnect();
    // Intentionally omitting `isVisible` — effect only needs to run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Read workspace/project IDs from context (provided by the editor page).
  // Safe variant returns null when no provider is present — allows FileCardView
  // to fall back to compact card behavior without throwing.
  const config = useFilePreviewConfigSafe();

  // Fetch signed URL only after IntersectionObserver fires AND we have a provider.
  // Pass null when not yet visible or no config to keep the query disabled.
  const { data: urlData, isLoading: urlLoading } = useArtifactSignedUrl(
    config?.workspaceId ?? '',
    config?.projectId ?? '',
    isVisible && !!config ? artifactId : null
  );

  const signedUrl = urlData?.url ?? '';

  // Fetch text content once we have a signed URL, the card is visible, and config is present.
  // The `open` parameter in useFileContent maps to the `enabled` flag on the query.
  const fileContent = useFileContent(
    signedUrl,
    // Cast is safe — InlineRendererType is a subset of RendererType.
    // If rendererType is null (non-previewable), this hook still runs but
    // enabled will be false (signedUrl is empty or isVisible is false).
    (rendererType ?? 'download') as RendererType,
    isVisible && !!signedUrl && !!config
  );

  return {
    containerRef,
    content: fileContent.content,
    signedUrl,
    isLoading: (urlLoading && isVisible) || fileContent.isLoading,
    isError: fileContent.isError,
    // Return null rendererType when no provider present — FileCardView falls back to compact card
    rendererType: config ? rendererType : null,
  };
}
