'use client';

/**
 * useSkillPreview — Listens for `pilot:preview-skill` custom events
 * and manages FilePreviewModal state using a Blob URL.
 *
 * The Blob URL trick lets us reuse FilePreviewModal + MarkdownRenderer
 * without any modifications — fetch() supports blob: URLs natively.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface SkillPreviewDetail {
  skillContent: string;
  skillName: string;
}

export function useSkillPreview() {
  const [open, setOpen] = useState(false);
  const [filename, setFilename] = useState('SKILL.md');
  const blobUrlRef = useRef<string | null>(null);
  const [signedUrl, setSignedUrl] = useState('');

  // Clean up blob URL when modal closes
  const revokeBlobUrl = useCallback(() => {
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    function handlePreview(e: Event) {
      const detail = (e as CustomEvent<SkillPreviewDetail>).detail;
      if (!detail?.skillContent) return;

      // Revoke previous blob URL if any
      revokeBlobUrl();

      // Create blob URL from in-memory markdown content
      const blob = new Blob([detail.skillContent], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      blobUrlRef.current = url;

      setSignedUrl(url);
      setFilename(detail.skillName ? `${detail.skillName}.md` : 'SKILL.md');
      setOpen(true);
    }

    window.addEventListener('pilot:preview-skill', handlePreview);
    return () => {
      window.removeEventListener('pilot:preview-skill', handlePreview);
      revokeBlobUrl();
    };
  }, [revokeBlobUrl]);

  const onOpenChange = useCallback(
    (isOpen: boolean) => {
      setOpen(isOpen);
      if (!isOpen) {
        revokeBlobUrl();
        setSignedUrl('');
      }
    },
    [revokeBlobUrl]
  );

  return {
    open,
    onOpenChange,
    artifactId: '',
    filename,
    mimeType: 'text/markdown',
    signedUrl,
  };
}
