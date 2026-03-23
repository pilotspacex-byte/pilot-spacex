'use client';

/**
 * IssueNoteLayout - Resizable panel layout for issue detail page.
 *
 * Desktop: ResizablePanelGroup (editor 62% | chat 38%)
 * Mobile: Full-width editor with ChatView slide-over via NoteCanvasMobileLayout.
 *
 * Mirrors the NoteCanvasLayout pattern for consistent UX.
 */
import { type ReactNode, lazy, Suspense } from 'react';
import { motion } from 'motion/react';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { CollapsedChatStrip } from '@/components/editor/CollapsedChatStrip';
import { NoteCanvasMobileLayout } from '@/components/editor/NoteCanvasMobileLayout';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

const ChatView = lazy(() =>
  import('@/features/ai/ChatView/ChatView').then((m) => ({ default: m.ChatView }))
);

export interface IssueNoteLayoutProps {
  /** Header rendered above editor only (not above chat panel) */
  headerContent?: ReactNode;
  /** Editor panel content */
  editorContent: ReactNode;
  /** AI store for ChatView */
  aiStore: { pilotSpace: PilotSpaceStore };
  /** Chat panel open state */
  isChatOpen: boolean;
  /** Set chat open state */
  onChatOpen: () => void;
  /** Set chat closed */
  onChatClose: () => void;
  /** Optional empty state slot to render inside ChatView */
  emptyStateSlot?: ReactNode;
  /** Optional initial prompt to pre-fill in ChatView */
  initialPrompt?: string;
}

export function IssueNoteLayout({
  headerContent,
  editorContent,
  aiStore,
  isChatOpen,
  onChatOpen,
  onChatClose,
  emptyStateSlot,
  initialPrompt,
}: IssueNoteLayoutProps) {
  const isSmallScreen = useMediaQuery('(max-width: 1023px)');
  const pilotSpaceStore = aiStore.pilotSpace;

  const chatViewContent = (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
          Loading AI chat...
        </div>
      }
    >
      <ChatView
        store={pilotSpaceStore}
        autoFocus
        onClose={onChatClose}
        emptyStateSlot={emptyStateSlot}
        initialPrompt={initialPrompt}
      />
    </Suspense>
  );

  const leftColumn = (
    <div className="flex flex-col h-full min-h-0">
      {headerContent}
      <div className="flex-1 overflow-hidden min-h-0">{editorContent}</div>
    </div>
  );

  // Mobile/Tablet layout
  if (isSmallScreen) {
    return (
      <div className="flex flex-col h-full w-full">
        {headerContent}
        <NoteCanvasMobileLayout
          editorContent={editorContent}
          chatViewContent={chatViewContent}
          isChatViewOpen={isChatOpen}
          onClose={onChatClose}
          onOpen={onChatOpen}
        />
      </div>
    );
  }

  // Desktop: Chat open — full resizable layout
  if (isChatOpen) {
    return (
      <ResizablePanelGroup
        orientation="horizontal"
        className="h-full w-full"
        id="issue-note-layout"
      >
        <ResizablePanel id="editor-panel" defaultSize="62%" minSize="50%" className="min-w-0">
          {leftColumn}
        </ResizablePanel>

        <ResizableHandle withHandle />

        <ResizablePanel
          id="chat-panel"
          defaultSize="38%"
          minSize="30%"
          maxSize="50%"
          className="min-w-0"
        >
          <motion.aside
            aria-label="Chat panel"
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
    );
  }

  // Desktop: Chat closed — ChatView stays mounted but hidden
  return (
    <div className="flex h-full w-full overflow-hidden">
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {headerContent}
        <div className="flex-1 overflow-hidden min-h-0">{editorContent}</div>
      </div>
      <div className="hidden" aria-hidden="true">
        {chatViewContent}
      </div>
      <CollapsedChatStrip onClick={onChatOpen} />
    </div>
  );
}
