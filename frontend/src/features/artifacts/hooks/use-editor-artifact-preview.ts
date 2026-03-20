'use client';

/**
 * useEditorArtifactPreview — Listens for `pilot:preview-artifact` custom events
 * dispatched by FileCardView and FigureNodeView, and manages the FilePreviewModal state.
 *
 * Returns the props needed to render <FilePreviewModal /> at the page level.
 *
 * Usage:
 *   const preview = useEditorArtifactPreview(workspaceId, projectId);
 *   {preview.open && <FilePreviewModal {...preview} />}
 */

import { useCallback, useEffect, useState } from 'react';
import { useArtifactSignedUrl } from './use-artifact-signed-url';

interface PreviewArtifactDetail {
  artifactId: string;
  filename: string;
  mimeType: string;
  /** Pre-existing signed URL (e.g. for images that already have src) */
  signedUrl?: string;
}

export function useEditorArtifactPreview(workspaceId: string, projectId: string) {
  const [selected, setSelected] = useState<PreviewArtifactDetail | null>(null);
  const [open, setOpen] = useState(false);

  // Fetch signed URL on-demand when artifact is selected (unless pre-provided)
  const { data: urlData } = useArtifactSignedUrl(
    workspaceId,
    projectId,
    selected?.signedUrl ? null : (selected?.artifactId ?? null)
  );

  const signedUrl = selected?.signedUrl ?? urlData?.url ?? '';

  useEffect(() => {
    function handlePreview(e: Event) {
      const detail = (e as CustomEvent<PreviewArtifactDetail>).detail;
      if (!detail?.artifactId) return;
      setSelected(detail);
      setOpen(true);
    }

    window.addEventListener('pilot:preview-artifact', handlePreview);
    return () => window.removeEventListener('pilot:preview-artifact', handlePreview);
  }, []);

  const onOpenChange = useCallback((isOpen: boolean) => {
    setOpen(isOpen);
    if (!isOpen) setSelected(null);
  }, []);

  return {
    open,
    onOpenChange,
    artifactId: selected?.artifactId ?? '',
    filename: selected?.filename ?? '',
    mimeType: selected?.mimeType ?? '',
    signedUrl,
  };
}
