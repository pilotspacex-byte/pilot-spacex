'use client';

/**
 * IssueEditorContent - Editor panel for the note-first issue detail page.
 *
 * NOTE: This component intentionally does NOT use observer() from MobX.
 * React 19's useSyncExternalStore (used internally by observer()) calls flushSync
 * when a tracked MobX observable changes during render. TipTap's ReactNodeViewRenderer
 * (used by PropertyBlockNode) creates React NodeViews inside ProseMirror transactions
 * during React's rendering lifecycle, causing a nested flushSync error:
 *   "flushSync was called from inside a lifecycle method"
 *
 * Instead, MobX reactivity is handled by:
 * - The parent IssueDetailPage (observer-wrapped) passes data via props/context
 * - Child components like PropertyBlockView use observer() in isolation
 */
import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import type { Content } from '@tiptap/core';
import { MessageSquare } from 'lucide-react';

import { cn } from '@/lib/utils';
import { SelectionToolbar } from '@/components/editor/SelectionToolbar';
import {
  IssueTitle,
  SubIssuesList,
  ActivityTimeline,
  CollapsibleSection,
  IssueSectionDivider,
} from '@/features/issues/components';
import { IssueDescriptionEmptyState } from './issue-description-empty-state';
import { createIssueNoteExtensions } from '@/features/issues/editor/create-issue-note-extensions';
import type { Issue, UpdateIssueData } from '@/types';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const DEBOUNCE_MS = 2000;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export interface IssueEditorContentProps {
  issue: Issue;
  issueId: string;
  workspaceId: string;
  workspaceSlug: string;
  onUpdate: (data: UpdateIssueData) => Promise<unknown>;
  onChatOpen: () => void;
  /** When provided, passed to the empty state CTA — opens chat AND sends generate prompt. */
  onAiGenerate?: () => void;
}

// ---------------------------------------------------------------------------
// Component (NOT observer-wrapped — see module doc above)
// ---------------------------------------------------------------------------
export function IssueEditorContent({
  issue,
  issueId,
  workspaceId,
  workspaceSlug,
  onUpdate,
  onChatOpen,
  onAiGenerate,
}: IssueEditorContentProps) {
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedHtmlRef = useRef(issue.descriptionHtml ?? '');

  // -- TipTap Editor --
  const extensions = useMemo(
    () =>
      createIssueNoteExtensions({
        issueId,
        enableSlashCommands: true,
        enableNoteLinks: false,
        enableInlineIssues: true,
        enableParagraphSplit: true,
      }),
    [issueId]
  );

  // Prepend propertyBlock to HTML so the parser creates it at position 0.
  // Fall back to markdown description when descriptionHtml is stale/empty (e.g. after AI update).
  // tiptap-markdown parses the markdown string in onBeforeCreate; appendTransaction adds propertyBlock.
  const initialContent = useMemo<Content>(() => {
    const htmlHasContent = !!(
      issue.descriptionHtml && issue.descriptionHtml.replace(/<[^>]*>/g, '').trim().length > 0
    );
    if (htmlHasContent) {
      return `<div data-property-block></div>${issue.descriptionHtml}`;
    }
    if (issue.description) {
      return issue.description;
    }
    return { type: 'doc', content: [{ type: 'propertyBlock' }, { type: 'paragraph' }] };
  }, [issue.descriptionHtml, issue.description]);

  const editor = useEditor({
    immediatelyRender: false,
    extensions,
    content: initialContent,
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-sm max-w-none min-h-[120px]',
          'outline-none focus:outline-none',
          'text-foreground',
          'prose-headings:text-foreground prose-p:text-foreground',
          'prose-strong:text-foreground prose-code:text-foreground',
          'prose-a:text-primary prose-a:no-underline hover:prose-a:underline'
        ),
        'aria-label': 'Issue content',
      },
    },
  });

  // -- Auto-save description --
  const clearDebounce = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
  }, []);

  const saveDescription = useCallback(
    async (html: string, text: string) => {
      const cleanHtml = html.replace(/<div[^>]*data-property-block[^>]*><\/div>/g, '').trim();
      if (cleanHtml === lastSavedHtmlRef.current) return;
      lastSavedHtmlRef.current = cleanHtml;
      await onUpdate({ description: text, descriptionHtml: cleanHtml });
    },
    [onUpdate]
  );

  useEffect(() => {
    if (!editor) return;

    const handleEditorUpdate = () => {
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

    editor.on('update', handleEditorUpdate);
    return () => {
      editor.off('update', handleEditorUpdate);
    };
  }, [editor, clearDebounce, saveDescription]);

  // Force save on Cmd+S
  useEffect(() => {
    const handleForce = () => {
      if (!editor) return;
      clearDebounce();
      const html = editor.getHTML();
      const markdown =
        (
          editor.storage as unknown as Record<string, { getMarkdown?: () => string }>
        ).markdown?.getMarkdown?.() ?? editor.getText();
      void saveDescription(html, markdown);
    };
    document.addEventListener('issue-force-save', handleForce);
    return () => document.removeEventListener('issue-force-save', handleForce);
  }, [editor, clearDebounce, saveDescription]);

  useEffect(() => clearDebounce, [clearDebounce]);

  return (
    <div className="flex flex-col min-w-0 overflow-hidden h-full">
      <div
        role="main"
        aria-label="Issue editor"
        className="relative flex-1 overflow-auto bg-background"
      >
        {editor && (
          <SelectionToolbar
            editor={editor}
            workspaceId={workspaceId}
            noteId={issueId}
            onChatViewOpen={onChatOpen}
          />
        )}

        <div
          className={cn(
            'h-full overflow-auto scrollbar-thin',
            'px-4 sm:px-5 md:px-6 lg:px-8',
            'py-2 sm:py-3'
          )}
        >
          <div className="mx-auto document-canvas max-w-[860px]">
            <IssueTitle title={issue.name} issueId={issueId} workspaceId={workspaceId} />

            <div className="mt-1">
              <EditorContent editor={editor} />
              <IssueDescriptionEmptyState
                editor={editor}
                onChatOpen={onChatOpen}
                onAiGenerate={onAiGenerate}
              />
            </div>

            {(issue.subIssueCount ?? 0) > 0 && (
              <>
                <IssueSectionDivider label="Sub-issues" count={issue.subIssueCount} />
                <SubIssuesList
                  parentId={issue.id}
                  workspaceId={workspaceId}
                  workspaceSlug={workspaceSlug}
                  projectId={issue.project?.id ?? ''}
                  subIssues={[]}
                />
              </>
            )}

            <CollapsibleSection title="Activity" icon={<MessageSquare className="size-3.5" />}>
              <ActivityTimeline issueId={issueId} workspaceId={workspaceId} />
            </CollapsibleSection>
          </div>
        </div>
      </div>
    </div>
  );
}
