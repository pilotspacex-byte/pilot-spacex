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
import { lazy, Suspense, useCallback, useMemo, useState } from 'react';
import { EditorContent } from '@tiptap/react';
import { motion } from 'motion/react';
import { History, Users, MessageSquare } from 'lucide-react';

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

import { NoteHealthBadges } from './NoteHealthBadges';
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
    author,
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
  } = props;

  // Issue extraction SSE pipeline (Feature 009)
  const [extractionState, extractionActions] = useIssueExtraction();

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
      });
    },
    [workspaceId, extractionActions]
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
      {/* Inline Note Header - Fixed at top, outside scrollable area */}
      {(title || createdAt) && (
        <InlineNoteHeader
          title={title}
          author={author}
          createdAt={createdAt ?? new Date().toISOString()}
          updatedAt={updatedAt}
          wordCount={wordCount}
          isPinned={isPinned}
          isAIAssisted={isAIAssisted}
          topics={topics}
          workspaceSlug={workspaceSlug}
          onShare={onShare}
          onExport={onExport}
          onDelete={onDelete}
          onTogglePin={onTogglePin}
          onVersionHistory={() => {
            sidebar.openSidebar('versions');
            onVersionHistory?.();
          }}
          disabled={readOnly}
        />
      )}

      {/* Note health badges (T024) */}
      <NoteHealthBadges
        health={noteHealth}
        pilotSpaceStore={aiStore.pilotSpace}
        onOpenChat={handleChatViewOpen}
        isSmallScreen={isSmallScreen}
        className="px-4 py-1"
      />

      {/* Note metadata: project + linked issues */}
      <NoteMetadata
        projectId={projectId}
        linkedIssues={linkedIssues}
        workspaceSlug={workspaceSlug}
      />

      {/* Large note warning banner (>= 1000 blocks) */}
      <LargeNoteWarning noteId={noteId} blockCount={blockCount} />

      {/* Scrollable Editor Area */}
      <div
        ref={editorContainerRef}
        role="main"
        aria-label="Note editor"
        className="relative flex-1 overflow-auto bg-background"
      >
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
              'mx-auto document-canvas',
              'max-w-full sm:max-w-[640px] md:max-w-[680px] lg:max-w-[720px] xl:max-w-[760px] 2xl:max-w-[800px]'
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
        autoFocus
        onClose={() => setIsChatViewOpen(false)}
        suggestedPrompts={
          noteHealth.suggestedPrompts.length > 0 ? noteHealth.suggestedPrompts : undefined
        }
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

      {/* Issue Extraction Preview Modal (Feature 009) */}
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
    </div>
  );
}

export default NoteCanvasLayout;
