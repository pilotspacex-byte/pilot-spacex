'use client';

/**
 * NoteCanvasLayout - Responsive layout rendering for NoteCanvas.
 * Extracted from NoteCanvas to stay under 700-line limit.
 *
 * Handles:
 * - Desktop: ResizablePanelGroup (editor + ChatView side-by-side)
 * - Mobile: NoteCanvasMobileLayout (overlay ChatView)
 * - Header, metadata, toolbar, editor content area
 * - Off-screen AI indicator
 *
 * Responsive behavior:
 * - Ultra-large (2xl+): Wider content, larger ChatView panel, more padding
 * - Large desktop (xl-2xl): Standard wide layout
 * - Desktop (lg-xl): Side-by-side layout with ChatView panel
 * - Tablet (md-lg): Collapsible ChatView, full-width editor
 * - Mobile (<md): Overlay ChatView panel, compact header
 */
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { notesKeys } from '@/features/notes/hooks';
import { EditorContent } from '@tiptap/react';
import { motion } from 'motion/react';
import { History, Users, MessageSquare, SmilePlus, Minimize2 } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

const ChatView = lazy(() =>
  import('@/features/ai/ChatView/ChatView').then((m) => ({ default: m.ChatView }))
);

import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { cn } from '@/lib/utils';
import { NoteMetadata } from './NoteMetadata';
import { SelectionToolbar } from './SelectionToolbar';
import { InlineNoteHeader } from './InlineNoteHeader';
import { CollapsedChatStrip } from './CollapsedChatStrip';
import { OffScreenAIIndicator } from './OffScreenAIIndicator';
import { NoteCanvasMobileLayout } from './NoteCanvasMobileLayout';
import { LargeNoteWarning } from './LargeNoteWarning';
import { SidebarPanel, useSidebarPanel } from './sidebar';
import type { SidebarTab } from './sidebar';
import { PresenceSidebarPanel, ConversationSidebarPanel } from '@/features/notes/components/panels';
import { VersionPanel } from '@/features/notes/components/VersionPanel';
import { VersionStore } from '@/features/notes/stores/VersionStore';
import { useIssueExtraction } from '@/features/notes/hooks/useIssueExtraction';
import { ExtractionPreviewModal } from '@/features/notes/components/ExtractionPreviewModal';
import { ExtractionReviewPanel } from '@/features/notes/components/ExtractionReviewPanel';

import { extractHeadings, extractSectionBlocks } from './AutoTOC';
import type { HeadingItem } from './AutoTOC';
import { OnThisPageTOC } from './OnThisPageTOC';
import { NoteHealthBadges } from './NoteHealthBadges';
import { ProjectContextHeader } from './ProjectContextHeader';
import type { NoteCanvasProps } from './NoteCanvasEditor';
import { useNoteCanvasEditor, EditorErrorFallback, EditorSkeleton } from './NoteCanvasEditor';

/** Sidebar tabs definition (T-136 framework, T-137/T-138/T-139 panels) */
const SIDEBAR_TABS: SidebarTab[] = [
  { id: 'versions', label: 'Versions', icon: <History className="h-3.5 w-3.5" /> },
  // COL-M8: Presence and Conversation panels not yet wired — mark as comingSoon
  { id: 'presence', label: 'Presence', icon: <Users className="h-3.5 w-3.5" />, comingSoon: true },
  {
    id: 'conversation',
    label: 'Threads',
    icon: <MessageSquare className="h-3.5 w-3.5" />,
    comingSoon: true,
  },
];

/**
 * NoteCanvas component with responsive layout per Prototype v4
 * Layout: [Document Canvas | AI ChatView] [Sidebar Panel (right)]
 *
 * NOTE: This component intentionally does NOT use observer() from MobX-React-Lite.
 * React 19's useSyncExternalStore (used internally by observer()) calls flushSync when
 * a tracked MobX observable changes during render. TipTap's ReactNodeViewRenderer
 * (used by PMBlockExtension) creates React NodeViews inside ProseMirror transactions
 * during React's rendering lifecycle, causing a nested flushSync error:
 *   "flushSync was called from inside a lifecycle method"
 * All MobX reactivity is handled by child components (ChatView has its own observer)
 * or by explicit reactions (useEditorSync, useContentUpdates use queueMicrotask).
 * aiStore.pilotSpace is a stable singleton set in AIStore's constructor — it never
 * changes after initialization so observer() tracking provides no benefit here.
 * Workspace reactivity is propagated via props from NoteDetailPage (which IS observer()).
 * @see NoteDetailPage — sole intended consumer; responsible for pre-resolving workspaceId to a UUID.
 */
export function NoteCanvasLayout(props: NoteCanvasProps) {
  const {
    noteId,
    readOnly = false,
    isLoading = false,
    error = null,
    workspaceId,
    title = 'Untitled',
    createdAt,
    updatedAt,
    wordCount = 0,
    isPinned = false,
    isAIAssisted = false,
    topics,
    workspaceSlug = '',
    onShare,
    onExport,
    onDelete,
    onTogglePin,
    onVersionHistory,
    projectId,
    linkedIssues = [],
    onMove,
    iconEmoji,
    onEmojiChange,
    isFocusMode = false,
    onToggleFocusMode,
  } = props;

  // Issue extraction SSE pipeline (Feature 009)
  const [extractionState, extractionActions] = useIssueExtraction();
  const queryClient = useQueryClient();

  const handleExtractIssues = useCallback(
    (params: {
      noteId: string;
      noteTitle: string;
      noteContent: Record<string, unknown>;
      selectedText?: string;
    }) => {
      if (!workspaceId) return;
      extractionActions.startExtraction({
        ...params,
        workspaceId,
        projectId: projectId ?? null,
        onCreated: () => {
          // Refetch the note so linkedIssues reflects the newly created NoteIssueLinks
          void queryClient.invalidateQueries({
            queryKey: notesKeys.detail(workspaceId, params.noteId),
          });
        },
      });
    },
    [workspaceId, projectId, extractionActions, queryClient]
  );

  const {
    editor,
    editorContainerRef,
    scrollRef,
    chatPanelRef,
    isChatViewOpen,
    setIsChatViewOpen,
    chatPanelState,
    isSmallScreen,
    aiStore,
    hasOffScreenUpdate,
    offScreenDirection,
    scrollToBlock,
    dismissIndicator,
    handleChatViewOpen,
    handleChatPanelToggle,
    handleChatPanelResize,
    handleRetry,
    editorError,
    noteHealth,
  } = useNoteCanvasEditor({ ...props, onExtractIssues: handleExtractIssues });

  // T-136/T-137/T-138/T-139: Sidebar panel framework
  const sidebar = useSidebarPanel();

  // T-216: Version history — VersionStore instance (stable, per-editor-mount)
  const [versionStore] = useState(() => new VersionStore());

  // Extract headings for OnThisPageTOC + ChatInput section menu.
  // Uses functional setState to skip re-render when headings haven't structurally changed,
  // preventing cascade re-renders to OnThisPageTOC + ChatView on every keystroke.
  const [noteHeadings, setNoteHeadings] = useState<HeadingItem[]>([]);
  useEffect(() => {
    if (!editor) return;
    const update = () => {
      const extracted = extractHeadings(editor);
      setNoteHeadings((prev) => {
        if (
          prev.length === extracted.length &&
          prev.every((h, i) => h.id === extracted[i]?.id && h.text === extracted[i]?.text)
        ) {
          return prev;
        }
        return extracted;
      });
    };
    update();
    editor.on('update', update);
    return () => {
      editor.off('update', update);
    };
  }, [editor]);

  // Section selection handler — sets note context to focused section blocks
  const handleSelectSection = useCallback(
    (heading: HeadingItem) => {
      if (!editor || !noteId) return;
      const { text, blockIds } = extractSectionBlocks(editor, heading.id);
      aiStore.pilotSpace.setNoteContext({
        noteId,
        noteTitle: title,
        selectedText: text,
        selectedBlockIds: blockIds,
      });
    },
    [editor, noteId, title, aiStore.pilotSpace]
  );

  // Emoji picker state (Notion-style page icon)
  const [emojiPopoverOpen, setEmojiPopoverOpen] = useState(false);
  const [emojiInput, setEmojiInput] = useState('');

  // Count top-level doc nodes for large-note warning
  const blockCount = useMemo(() => {
    if (!editor) return 0;
    return editor.state.doc.childCount;
  }, [editor]);

  // Show error state
  if (error || editorError) {
    return (
      <EditorErrorFallback error={error ?? editorError ?? 'Unknown error'} onRetry={handleRetry} />
    );
  }

  // Show loading state
  if (isLoading || !editor) {
    return <EditorSkeleton />;
  }

  // Editor content component - reusable for both resizable and non-resizable layouts
  const editorContent = (
    <div className="flex flex-col min-w-0 overflow-hidden h-full">
      {/* Project context header — shown only when note belongs to a project */}
      {!isFocusMode && projectId && (
        <ProjectContextHeader
          projectId={projectId}
          workspaceSlug={workspaceSlug}
          workspaceId={workspaceId}
        />
      )}

      {/* Inline Note Header - Fixed at top, outside scrollable area */}
      {!isFocusMode && (title || createdAt) && (
        <InlineNoteHeader
          title={title}
          createdAt={createdAt ?? new Date().toISOString()}
          updatedAt={updatedAt}
          wordCount={wordCount}
          isPinned={isPinned}
          isAIAssisted={isAIAssisted}
          topics={topics}
          workspaceSlug={workspaceSlug}
          projectId={projectId}
          workspaceId={workspaceId}
          onShare={onShare}
          onExport={onExport}
          onDelete={onDelete}
          onTogglePin={onTogglePin}
          onVersionHistory={() => {
            sidebar.openSidebar('versions');
            onVersionHistory?.();
          }}
          onMove={onMove}
          disabled={readOnly}
          isFocusMode={isFocusMode}
          onToggleFocusMode={onToggleFocusMode}
        />
      )}

      {/* Emoji icon picker — Notion-style page icon, shown above the editor content */}
      {!isFocusMode && onEmojiChange && (
        <div className="px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16 2xl:px-20 pt-3 pb-0">
          <div className="mx-auto max-w-full sm:max-w-[640px] md:max-w-[680px] lg:max-w-[720px] xl:max-w-[760px] 2xl:max-w-[800px]">
            <Popover
              open={emojiPopoverOpen}
              onOpenChange={(open) => {
                setEmojiPopoverOpen(open);
                if (open) setEmojiInput(iconEmoji ?? '');
              }}
            >
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground p-1 rounded transition-colors"
                  aria-label={iconEmoji ? 'Change icon' : 'Add icon'}
                >
                  {iconEmoji ? (
                    <span className="text-2xl leading-none">{iconEmoji}</span>
                  ) : (
                    <SmilePlus className="h-5 w-5" />
                  )}
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-48 p-2" align="start">
                <div className="flex gap-2">
                  <Input
                    value={emojiInput}
                    onChange={(e) => setEmojiInput(e.target.value)}
                    aria-label="Page icon emoji"
                    placeholder="Type emoji..."
                    className="h-8 text-base"
                    maxLength={10}
                    autoFocus
                  />
                  <Button
                    size="sm"
                    className="h-8 shrink-0"
                    onClick={() => {
                      onEmojiChange(emojiInput.trim() || null);
                      setEmojiPopoverOpen(false);
                      setEmojiInput('');
                    }}
                  >
                    Set
                  </Button>
                </div>
                {iconEmoji && (
                  <button
                    type="button"
                    className="mt-1 w-full text-left text-xs text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() => {
                      onEmojiChange(null);
                      setEmojiPopoverOpen(false);
                      setEmojiInput('');
                    }}
                  >
                    Remove icon
                  </button>
                )}
              </PopoverContent>
            </Popover>
          </div>
        </div>
      )}

      {/* Note health badges (T024) */}
      {!isFocusMode && (
        <NoteHealthBadges
          health={noteHealth}
          pilotSpaceStore={aiStore.pilotSpace}
          onOpenChat={handleChatViewOpen}
          isSmallScreen={isSmallScreen}
          className="px-4 py-1"
        />
      )}

      {/* Note metadata: linked issues (project context shown in ProjectContextHeader above) */}
      {!isFocusMode && <NoteMetadata linkedIssues={linkedIssues} workspaceSlug={workspaceSlug} />}

      {/* Large note warning banner (>= 1000 blocks) */}
      {!isFocusMode && <LargeNoteWarning noteId={noteId} blockCount={blockCount} />}

      {/* Scrollable Editor Area */}
      <div
        ref={editorContainerRef}
        role="main"
        aria-label="Note editor"
        className="relative flex-1 overflow-auto bg-background"
      >
        {/* Fixed exit focus mode affordance — only visible when header is hidden */}
        {isFocusMode && onToggleFocusMode && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={onToggleFocusMode}
                className="fixed top-3 right-3 z-[41] h-7 w-7 text-muted-foreground hover:text-foreground bg-background/80 backdrop-blur-sm border border-border/40 rounded-md"
                aria-label="Exit focus mode"
              >
                <Minimize2 className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left">Exit focus mode (Cmd+Shift+F)</TooltipContent>
          </Tooltip>
        )}
        {/* Selection Toolbar */}
        <SelectionToolbar
          editor={editor}
          workspaceId={workspaceId}
          noteId={noteId}
          onChatViewOpen={handleChatViewOpen}
        />

        {/* Editor Content - Responsive padding and width */}
        <div
          ref={scrollRef}
          className={cn(
            'h-full overflow-auto scrollbar-thin',
            'px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16 2xl:px-20',
            'py-3 sm:py-4 lg:py-6 2xl:py-8'
          )}
        >
          <div
            className={cn(
              'mx-auto document-canvas relative',
              isFocusMode
                ? 'max-w-[720px]'
                : 'max-w-full sm:max-w-[640px] md:max-w-[680px] lg:max-w-[720px] xl:max-w-[760px] 2xl:max-w-[800px]'
            )}
          >
            {/* TipTap Editor */}
            <EditorContent editor={editor} />
          </div>

          {/* Off-screen AI edit indicator */}
          <OffScreenAIIndicator
            isVisible={hasOffScreenUpdate}
            direction={offScreenDirection}
            onScrollToBlock={scrollToBlock}
            onDismiss={dismissIndicator}
          />
        </div>

        {/* Medium-style "On This Page" TOC — fixed to right edge, shown when chat closed */}
        {!isChatViewOpen && noteHeadings.length >= 2 && (
          <div className="hidden lg:block fixed top-1/4 right-14 w-48 z-30">
            <OnThisPageTOC editor={editor} headings={noteHeadings} />
          </div>
        )}
      </div>
    </div>
  );

  // ChatView content component - reusable for both mobile and desktop
  // Lazy-loaded: ChatView (~200KB) only loads when chat panel opens
  const chatViewContent = (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
          Loading AI chat...
        </div>
      }
    >
      <ChatView
        store={aiStore.pilotSpace}
        approvalStore={aiStore.approval}
        autoFocus
        onClose={() => setIsChatViewOpen(false)}
        suggestedPrompts={
          noteHealth.suggestedPrompts.length > 0 ? noteHealth.suggestedPrompts : undefined
        }
        noteHeadings={noteHeadings}
        onSelectSection={handleSelectSection}
      />
    </Suspense>
  );

  /** Render sidebar panel content based on active tab */
  const sidebarContent =
    sidebar.activePanel === 'versions' ? (
      <VersionPanel workspaceId={workspaceId ?? ''} noteId={noteId} store={versionStore} />
    ) : sidebar.activePanel === 'presence' ? (
      <PresenceSidebarPanel entries={[]} crdtActive={false} />
    ) : sidebar.activePanel === 'conversation' ? (
      <ConversationSidebarPanel
        threads={[]}
        onNewThread={() => {
          /* link to annotation system */
        }}
      />
    ) : null;

  return (
    <div className="flex h-full bg-background overflow-hidden" data-testid="note-editor">
      {/* Desktop: Resizable two-panel layout (lg and above) */}
      {!isSmallScreen && (
        <>
          {isChatViewOpen ? (
            <ResizablePanelGroup
              orientation="horizontal"
              className="h-full"
              id="note-editor-layout"
            >
              {/* Editor Panel - min 50% (when ChatView at max), default 62% */}
              <ResizablePanel id="editor-panel" defaultSize="62%" minSize="50%" className="min-w-0">
                {editorContent}
              </ResizablePanel>

              {/* Resize Handle with toggle button */}
              <ResizableHandle
                withHandle
                toggleState={chatPanelState}
                onToggle={handleChatPanelToggle}
              />

              {/* ChatView Panel - min 30% - default 38% (current), max 50% */}
              <ResizablePanel
                id="chat-panel"
                defaultSize="38%"
                minSize="30%"
                maxSize="50%"
                className="min-w-0"
                panelRef={chatPanelRef}
                onResize={handleChatPanelResize}
              >
                <motion.aside
                  aria-label="AI Chat Assistant"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2, ease: 'easeInOut' }}
                  className="h-full w-full overflow-hidden border-l border-border"
                >
                  {chatViewContent}
                </motion.aside>
              </ResizablePanel>
            </ResizablePanelGroup>
          ) : (
            <>
              {/* Full-width editor when ChatView is closed */}
              <div className="flex-1 min-w-0">{editorContent}</div>
              {/* Collapsed ChatView strip */}
              <CollapsedChatStrip onClick={handleChatViewOpen} />
            </>
          )}
        </>
      )}

      {/* Mobile/Tablet: Full-width editor with slide-over ChatView */}
      {isSmallScreen && (
        <NoteCanvasMobileLayout
          editorContent={editorContent}
          chatViewContent={chatViewContent}
          isChatViewOpen={isChatViewOpen}
          onClose={() => setIsChatViewOpen(false)}
          onOpen={handleChatViewOpen}
        />
      )}

      {/* T-136/T-137/T-138/T-139: Sidebar panel (Versions | Presence | Threads) */}
      <SidebarPanel
        isOpen={sidebar.isOpen}
        activePanel={sidebar.activePanel}
        tabs={SIDEBAR_TABS}
        title="Note Panels"
        width={sidebar.width}
        onTabChange={sidebar.openSidebar}
        onClose={sidebar.closeSidebar}
        onWidthChange={sidebar.setWidth}
      >
        {sidebarContent}
      </SidebarPanel>

      {/* Issue Extraction Preview Modal (Feature 009 — legacy, isModalOpen always false) */}
      {workspaceId && (
        <ExtractionPreviewModal
          open={extractionState.isModalOpen}
          onOpenChange={(open) => {
            if (!open) extractionActions.closeModal();
          }}
          issues={extractionState.issues}
          isExtracting={extractionState.isExtracting}
          error={extractionState.error}
          workspaceId={workspaceId}
          noteId={noteId}
        />
      )}

      {/* Extraction Review Panel (T-013/T-014) — slide-over with per-item approve/skip */}
      {workspaceId && (
        <ExtractionReviewPanel
          open={extractionState.isReviewPanelOpen}
          onOpenChange={(open) => {
            if (!open) extractionActions.closeReviewPanel();
          }}
          issues={extractionState.issues}
          isExtracting={extractionState.isExtracting}
          error={extractionState.error}
          workspaceId={workspaceId}
          workspaceSlug={workspaceSlug}
          noteId={noteId}
          projectId={projectId}
          onCreated={(_createdIds) => {
            void queryClient.invalidateQueries({
              queryKey: notesKeys.detail(workspaceId, noteId),
            });
            extractionActions.closeModal();
          }}
        />
      )}
    </div>
  );
}

export default NoteCanvasLayout;
