'use client';

/**
 * useAttachmentPreview — Listens for `pilot:preview-attachment` events
 * from AttachmentChip clicks and manages FilePreviewModal state.
 *
 * Fetches a signed URL on-demand via the chat attachments API,
 * then passes it to FilePreviewModal for rendering.
 */

import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { attachmentsApi } from '@/services/api/attachments';

interface PreviewAttachmentDetail {
  attachmentId: string;
  filename: string;
  mimeType: string;
}

export function useAttachmentPreview() {
  const [selected, setSelected] = useState<PreviewAttachmentDetail | null>(null);
  const [open, setOpen] = useState(false);

  const { data: urlData } = useQuery({
    queryKey: ['attachment-signed-url', selected?.attachmentId],
    queryFn: () => attachmentsApi.getSignedUrl(selected!.attachmentId),
    enabled: !!selected?.attachmentId && open,
    staleTime: 55 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
  });

  const signedUrl = urlData?.url ?? '';

  useEffect(() => {
    function handlePreview(e: Event) {
      const detail = (e as CustomEvent<PreviewAttachmentDetail>).detail;
      if (!detail?.attachmentId) return;
      setSelected(detail);
      setOpen(true);
    }

    window.addEventListener('pilot:preview-attachment', handlePreview);
    return () => window.removeEventListener('pilot:preview-attachment', handlePreview);
  }, []);

  const onOpenChange = useCallback((isOpen: boolean) => {
    setOpen(isOpen);
    if (!isOpen) setSelected(null);
  }, []);

  return {
    open,
    onOpenChange,
    artifactId: selected?.attachmentId ?? '',
    filename: selected?.filename ?? '',
    mimeType: selected?.mimeType ?? '',
    signedUrl,
  };
}
