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

const ChatView = lazy(() =>
  import('@/features/ai/ChatView/ChatView').then((m) => ({ default: m.ChatView }))
);

export interface IssueNoteLayoutProps {
  /** Editor panel content */
  editorContent: ReactNode;
  /** AI store for ChatView */
  aiStore: { pilotSpace: unknown };
  /** Chat panel open state */
  isChatOpen: boolean;
  /** Set chat open state */
  onChatOpen: () => void;
  /** Set chat closed */
  onChatClose: () => void;
}

export function IssueNoteLayout({
  editorContent,
  aiStore,
  isChatOpen,
  onChatOpen,
  onChatClose,
}: IssueNoteLayoutProps) {
  const isSmallScreen = useMediaQuery('(max-width: 1023px)');

  const chatViewContent = (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
          Loading AI chat...
        </div>
      }
    >
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <ChatView store={aiStore.pilotSpace as any} autoFocus onClose={onChatClose} />
    </Suspense>
  );

  // Mobile/Tablet layout
  if (isSmallScreen) {
    return (
      <NoteCanvasMobileLayout
        editorContent={editorContent}
        chatViewContent={chatViewContent}
        isChatViewOpen={isChatOpen}
        onClose={onChatClose}
        onOpen={onChatOpen}
      />
    );
  }

  // Desktop: Resizable panels
  if (isChatOpen) {
    return (
      <ResizablePanelGroup orientation="horizontal" className="h-full" id="issue-note-layout">
        <ResizablePanel id="editor-panel" defaultSize="62%" minSize="50%" className="min-w-0">
          {editorContent}
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
    );
  }

  // Desktop: Chat closed with collapsed strip
  return (
    <>
      <div className="flex-1 min-w-0">{editorContent}</div>
      <CollapsedChatStrip onClick={onChatOpen} />
    </>
  );
}
