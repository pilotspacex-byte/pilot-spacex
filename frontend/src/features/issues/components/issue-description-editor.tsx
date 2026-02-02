'use client';

/**
 * IssueDescriptionEditor - Rich text editor for issue descriptions.
 *
 * T030: TipTap-based editor with 2s debounced auto-save, per-field save
 * status feedback, and warm neutral styling matching the design system.
 * Uses createIssueEditorExtensions() for a focused extension set.
 */

import { useRef, useEffect, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import { cn } from '@/lib/utils';
import { SaveStatus } from '@/components/ui/save-status';
import { useSaveStatus } from '@/features/issues/hooks/use-save-status';
import { useUpdateIssue } from '@/features/issues/hooks/use-update-issue';
import { createIssueEditorExtensions } from '@/features/issues/editor/create-issue-editor-extensions';

// ============================================================================
// Types
// ============================================================================

export interface IssueDescriptionEditorProps {
  /** HTML content for the editor */
  content: string | undefined;
  /** Issue ID for mutations */
  issueId: string;
  /** Workspace ID for mutations */
  workspaceId: string;
  /** Disable editing */
  disabled?: boolean;
}

// ============================================================================
// Constants
// ============================================================================

const DEBOUNCE_MS = 2000;

// ============================================================================
// Component
// ============================================================================

export function IssueDescriptionEditor({
  content,
  issueId,
  workspaceId,
  disabled = false,
}: IssueDescriptionEditorProps) {
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedHtmlRef = useRef(content ?? '');

  const { status, wrapMutation } = useSaveStatus('description');
  const updateIssue = useUpdateIssue(workspaceId, issueId);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: createIssueEditorExtensions(),
    content: content ?? '',
    editable: !disabled,
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-sm max-w-none min-h-[200px] px-4 py-3',
          'outline-none focus:outline-none',
          'text-foreground',
          'prose-headings:text-foreground prose-p:text-foreground',
          'prose-strong:text-foreground prose-code:text-foreground',
          'prose-a:text-primary prose-a:no-underline hover:prose-a:underline'
        ),
        'aria-label': 'Issue description',
      },
    },
  });

  const clearDebounce = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
  }, []);

  const saveDescription = useCallback(
    async (html: string, text: string) => {
      if (html === lastSavedHtmlRef.current) return;
      lastSavedHtmlRef.current = html;

      await wrapMutation(() =>
        updateIssue.mutateAsync({
          description: text,
          descriptionHtml: html,
        })
      );
    },
    [wrapMutation, updateIssue]
  );

  // Listen for editor updates and debounce saves
  useEffect(() => {
    if (!editor) return;

    const handleUpdate = () => {
      clearDebounce();
      const html = editor.getHTML();
      const markdown =
        (
          editor.storage as unknown as Record<string, { getMarkdown?: () => string }>
        ).markdown?.getMarkdown?.() ?? editor.getText();

      debounceTimerRef.current = setTimeout(() => {
        void saveDescription(html, markdown);
      }, DEBOUNCE_MS);
    };

    editor.on('update', handleUpdate);
    return () => {
      editor.off('update', handleUpdate);
    };
  }, [editor, clearDebounce, saveDescription]);

  // Sync editable state when disabled prop changes
  useEffect(() => {
    if (editor && editor.isEditable === disabled) {
      editor.setEditable(!disabled);
    }
  }, [editor, disabled]);

  // Listen for force-save event (Cmd/Ctrl+S)
  useEffect(() => {
    const handleForceSave = () => {
      if (!editor) return;
      clearDebounce();
      const html = editor.getHTML();
      const markdown =
        (
          editor.storage as unknown as Record<string, { getMarkdown?: () => string }>
        ).markdown?.getMarkdown?.() ?? editor.getText();
      void saveDescription(html, markdown);
    };
    document.addEventListener('issue-force-save', handleForceSave);
    return () => document.removeEventListener('issue-force-save', handleForceSave);
  }, [editor, clearDebounce, saveDescription]);

  // Cleanup debounce timer on unmount
  useEffect(() => clearDebounce, [clearDebounce]);

  return (
    <div
      className={cn(
        'rounded-[14px] border border-[#E5E2DD]',
        'bg-background transition-colors duration-150',
        'focus-within:border-primary focus-within:ring-1 focus-within:ring-primary/20',
        disabled && 'opacity-60 cursor-not-allowed'
      )}
    >
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#E5E2DD]">
        <span className="text-xs font-medium text-foreground-muted">Description</span>
        <SaveStatus status={status} />
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}

export default IssueDescriptionEditor;
