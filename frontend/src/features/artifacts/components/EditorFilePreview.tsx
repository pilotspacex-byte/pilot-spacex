'use client';

/**
 * EditorFilePreview — Self-contained wrapper that listens for `pilot:preview-artifact`
 * events and renders the FilePreviewModal.
 *
 * IMPORTANT: This component isolates all preview state (open, selected, signedUrl)
 * so that opening/closing the preview modal does NOT trigger a re-render of the
 * parent component (NoteDetailPage → NoteCanvas → EditorContent).
 *
 * Without this isolation, the preview state change re-renders EditorContent, which
 * triggers TipTap's Portals (useSyncExternalStore) to call flushSync during React's
 * render cycle → "flushSync was called from inside a lifecycle method" in React 19.
 *
 * See: https://github.com/ueberdosis/tiptap/issues/3580
 */

import { useCallback, useEffect, useState } from 'react';
import { useArtifactSignedUrl } from '../hooks/use-artifact-signed-url';
import { FilePreviewModal } from './FilePreviewModal';

interface PreviewArtifactDetail {
  artifactId: string;
  filename: string;
  mimeType: string;
  signedUrl?: string;
}

export function EditorFilePreview({
  workspaceId,
  projectId,
}: {
  workspaceId: string;
  projectId: string;
}) {
  const [selected, setSelected] = useState<PreviewArtifactDetail | null>(null);
  const [open, setOpen] = useState(false);

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

  if (!signedUrl) return null;

  return (
    <FilePreviewModal
      open={open}
      onOpenChange={onOpenChange}
      artifactId={selected?.artifactId ?? ''}
      filename={selected?.filename ?? ''}
      mimeType={selected?.mimeType ?? ''}
      signedUrl={signedUrl}
      projectId={projectId}
    />
  );
}
