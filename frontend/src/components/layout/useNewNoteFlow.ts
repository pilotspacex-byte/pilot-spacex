'use client';

/**
 * useNewNoteFlow - Encapsulates TemplatePicker state for the "New Note" flow.
 *
 * TemplatePicker now includes an integrated project selector, so the flow is a
 * single step: open TemplatePicker → confirm with (template, projectId).
 */
import { useState, useCallback } from 'react';
import type { NoteTemplate } from '@/services/api/templates';
import type { JSONContent } from '@/types';

interface UseNewNoteFlowOptions {
  onCreateNote: (data: { title: string; content: JSONContent; projectId?: string }) => void;
}

export function useNewNoteFlow({ onCreateNote }: UseNewNoteFlowOptions) {
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);

  const open = useCallback(() => {
    setShowTemplatePicker(true);
  }, []);

  const handleTemplateConfirm = useCallback(
    (template: NoteTemplate | null, projectId: string | null) => {
      setShowTemplatePicker(false);
      onCreateNote({
        title: template ? `New ${template.name} Note` : 'Untitled',
        content: (template?.content ?? { type: 'doc', content: [{ type: 'paragraph' }] }) as JSONContent,
        ...(projectId ? { projectId } : {}),
      });
    },
    [onCreateNote]
  );

  const handleTemplateClose = useCallback(() => {
    setShowTemplatePicker(false);
  }, []);

  return {
    showTemplatePicker,
    handleTemplateConfirm,
    handleTemplateClose,
    open,
  };
}
