'use client';

/**
 * IssueDetailPage - Note-first issue detail view.
 *
 * Layout: [Note Editor (62%) | AI Chat Panel (38%)]
 * The editor contains:
 *   - PropertyBlockNode (inline properties at position 0)
 *   - IssueTitle (H1)
 *   - Full TipTap editor (same extensions as note canvas)
 *   - Sub-issues section
 *   - Activity section
 *
 * AI Chat panel reuses ChatView with issue-specific context.
 */

import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useRouter } from 'next/navigation';
import { useEditor, EditorContent } from '@tiptap/react';
import type { Content } from '@tiptap/core';
import { toast } from 'sonner';
import { MessageSquare } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { SelectionToolbar } from '@/components/editor/SelectionToolbar';

import {
  IssueNoteHeader,
  IssueNoteLayout,
  IssueTitle,
  SubIssuesList,
  ActivityTimeline,
  CollapsibleSection,
  IssueSectionDivider,
  IssuePropertiesPanel,
} from '@/features/issues/components';
import { DeleteConfirmDialog } from '@/components/issues/DeleteConfirmDialog';
import {
  useIssueDetail,
  useUpdateIssue,
  useWorkspaceMembers,
  useWorkspaceLabels,
  useProjectCycles,
  useIssueKeyboardShortcuts,
} from '@/features/issues/hooks';
import { IssueNoteContext } from '@/features/issues/contexts/issue-note-context';
import { createIssueNoteExtensions } from '@/features/issues/editor/create-issue-note-extensions';
import { useStore } from '@/stores';
import { copyToClipboard } from '@/lib/copy-context';
import type { UpdateIssueData, UserBrief } from '@/types';

import '@/features/notes/editor/extensions/note-link.css';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const DEBOUNCE_MS = 2000;

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------
function IssueDetailSkeleton() {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-4 border-b px-4 h-12">
        <Skeleton className="h-6 w-6" />
        <Skeleton className="h-5 w-32" />
        <div className="flex-1" />
        <Skeleton className="h-6 w-6" />
      </div>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 space-y-4 p-8">
          <Skeleton className="h-10 w-full max-w-md rounded-[12px]" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-48 w-full" />
        </div>
        <div className="w-[38%] hidden lg:block border-l p-4 space-y-4">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      </div>
    </div>
  );
}

function IssueNotFound({ onBack }: { onBack: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2">
      <p className="text-lg font-medium">Issue not found</p>
      <Button variant="link" onClick={onBack}>
        Back to issues
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------
const IssueDetailPage = observer(function IssueDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceSlug = params.workspaceSlug as string;
  const issueId = params.issueId as string;

  const { workspaceStore, issueStore, aiStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? workspaceSlug;

  // -- TanStack Query hooks --
  const { data: issue, isLoading, isError } = useIssueDetail(workspaceId, issueId);
  const updateIssue = useUpdateIssue(workspaceId, issueId);
  const { data: members = [] } = useWorkspaceMembers(workspaceId);
  const { data: labels = [] } = useWorkspaceLabels(workspaceId);
  const { data: cyclesData } = useProjectCycles(workspaceId, issue?.project?.id ?? '');

  // -- UI state --
  const [isChatOpen, setIsChatOpen] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [mobilePropertiesOpen, setMobilePropertiesOpen] = useState(false);

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedHtmlRef = useRef(issue?.descriptionHtml ?? '');

  // -- Derived data --
  const memberUsers = useMemo<UserBrief[]>(() => {
    const seen = new Set<string>();
    return members
      .filter((m) => {
        if (!m.userId || seen.has(m.userId)) return false;
        seen.add(m.userId);
        return true;
      })
      .map((m) => ({
        id: m.userId,
        email: m.email,
        displayName: m.fullName ?? null,
      }));
  }, [members]);

  const cycles = useMemo(() => cyclesData?.items ?? [], [cyclesData]);

  // -- Handlers --
  const handleBack = useCallback(() => {
    router.push(`/${workspaceSlug}/issues`);
  }, [router, workspaceSlug]);

  const handleUpdate = useCallback(
    (data: UpdateIssueData) => updateIssue.mutateAsync(data),
    [updateIssue]
  );

  const handleCopyLink = useCallback(() => {
    void copyToClipboard(window.location.href);
  }, []);

  const handleDeleteClick = useCallback(() => {
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!workspaceId || !issue?.id) return;
    setIsDeleting(true);
    try {
      await issueStore.deleteIssue(workspaceId, issue.id);
      setDeleteDialogOpen(false);
      router.push(`/${workspaceSlug}/issues`);
    } catch {
      toast.error('Failed to delete issue', {
        description: 'Please try again or contact support if the problem persists.',
      });
    } finally {
      setIsDeleting(false);
    }
  }, [workspaceId, issue?.id, issueStore, router, workspaceSlug]);

  const handleToggleChat = useCallback(() => {
    setIsChatOpen((prev) => !prev);
  }, []);

  // -- Keyboard shortcuts --
  const handleForceSave = useCallback(() => {
    document.dispatchEvent(new CustomEvent('issue-force-save'));
  }, []);

  useIssueKeyboardShortcuts({
    onForceSave: handleForceSave,
  });

  // -- TipTap Editor --
  const extensions = useMemo(
    () =>
      createIssueNoteExtensions({
        issueId,
        enableSlashCommands: true,
        enableNoteLinks: false, // Issue editor doesn't need note links
        enableInlineIssues: true,
        enableParagraphSplit: true,
      }),
    [issueId]
  );

  // Prepend propertyBlock to HTML so the parser creates it at position 0
  // without triggering appendTransaction during initial render (flushSync error).
  const initialContent = useMemo<Content>(() => {
    if (issue?.descriptionHtml) {
      return `<div data-property-block></div>${issue.descriptionHtml}`;
    }
    return { type: 'doc', content: [{ type: 'propertyBlock' }, { type: 'paragraph' }] };
  }, [issue?.descriptionHtml]);

  const editor = useEditor({
    immediatelyRender: false,
    extensions,
    content: initialContent,
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-sm max-w-none min-h-[300px]',
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
      // Strip propertyBlock from saved HTML — it's a UI-only node, not content
      const cleanHtml = html.replace(/<div[^>]*data-property-block[^>]*><\/div>/g, '').trim();
      if (cleanHtml === lastSavedHtmlRef.current) return;
      lastSavedHtmlRef.current = cleanHtml;
      await updateIssue.mutateAsync({ description: text, descriptionHtml: cleanHtml });
    },
    [updateIssue]
  );

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

  // -- Render states --
  if (isLoading) return <IssueDetailSkeleton />;
  if (isError || !issue) return <IssueNotFound onBack={handleBack} />;

  // -- IssueNoteContext value --
  const contextValue = {
    issue,
    members: memberUsers,
    labels,
    cycles,
    onUpdate: handleUpdate,
    disabled: false,
  };

  // -- Editor content --
  const editorContent = (
    <div className="flex flex-col min-w-0 overflow-hidden h-full">
      {/* Scrollable document area */}
      <div
        role="main"
        aria-label="Issue editor"
        className="relative flex-1 overflow-auto bg-background"
      >
        {/* Selection toolbar */}
        {editor && (
          <SelectionToolbar
            editor={editor}
            workspaceId={workspaceId}
            noteId={issueId}
            onChatViewOpen={() => setIsChatOpen(true)}
          />
        )}

        <div
          className={cn(
            'h-full overflow-auto scrollbar-thin',
            'px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16 2xl:px-20',
            'py-3 sm:py-4 lg:py-6 2xl:py-8'
          )}
        >
          <div
            className={cn(
              'mx-auto document-canvas',
              'max-w-full sm:max-w-[640px] md:max-w-[680px] lg:max-w-[720px] xl:max-w-[760px] 2xl:max-w-[800px]'
            )}
          >
            {/* Issue title */}
            <IssueTitle title={issue.name} issueId={issueId} workspaceId={workspaceId} />

            {/* TipTap editor with PropertyBlockNode + full extensions */}
            <div className="mt-4">
              <EditorContent editor={editor} />
            </div>

            {/* Sub-issues section */}
            <IssueSectionDivider label="Sub-issues" count={issue.subIssueCount} />
            <SubIssuesList
              parentId={issue.id}
              workspaceId={workspaceId}
              workspaceSlug={workspaceSlug}
              projectId={issue.project?.id ?? ''}
              subIssues={[]}
            />

            {/* Activity section */}
            <CollapsibleSection
              title="Activity"
              icon={<MessageSquare className="size-4" />}
              defaultOpen={true}
            >
              <ActivityTimeline issueId={issueId} workspaceId={workspaceId} />
            </CollapsibleSection>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <IssueNoteContext.Provider value={contextValue}>
      <div
        className="flex h-full flex-col bg-background overflow-hidden"
        data-testid="issue-detail"
      >
        {/* Minimal header */}
        <IssueNoteHeader
          identifier={issue.identifier}
          issueType={issue.type}
          aiGenerated={issue.aiGenerated ?? false}
          isChatOpen={isChatOpen}
          onBack={handleBack}
          onToggleChat={handleToggleChat}
          onCopyLink={handleCopyLink}
          onDelete={handleDeleteClick}
        />

        {/* Note-first layout: Editor | Chat */}
        <div className="flex flex-1 overflow-hidden">
          <IssueNoteLayout
            editorContent={editorContent}
            aiStore={aiStore}
            isChatOpen={isChatOpen}
            onChatOpen={() => setIsChatOpen(true)}
            onChatClose={() => setIsChatOpen(false)}
          />
        </div>

        {/* Mobile properties bottom sheet (fallback for property block on small screens) */}
        <Sheet open={mobilePropertiesOpen} onOpenChange={setMobilePropertiesOpen}>
          <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto rounded-t-2xl">
            <SheetHeader>
              <SheetTitle>Properties</SheetTitle>
            </SheetHeader>
            {mobilePropertiesOpen && (
              <IssuePropertiesPanel
                issue={issue}
                workspaceId={workspaceId}
                workspaceSlug={workspaceSlug}
                members={members}
                labels={labels}
                cycles={cycles}
                onUpdate={handleUpdate}
              />
            )}
          </SheetContent>
        </Sheet>

        {/* Delete confirmation dialog */}
        <DeleteConfirmDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          issues={[issue]}
          onConfirm={handleDeleteConfirm}
          isDeleting={isDeleting}
        />
      </div>
    </IssueNoteContext.Provider>
  );
});

export default IssueDetailPage;
