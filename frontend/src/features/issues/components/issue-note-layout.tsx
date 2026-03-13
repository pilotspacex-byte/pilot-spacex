'use client';

/**
 * IssueNoteLayout - Resizable panel layout for issue detail page.
 *
 * Desktop: ResizablePanelGroup (editor 62% | chat 38%)
 * Mobile: Full-width editor with ChatView slide-over via NoteCanvasMobileLayout.
 *
 * Right panel supports an optional tab system (Chat | Knowledge Graph):
 * - When `knowledgeGraphContent` is provided, a tab bar is rendered at the top.
 * - Chat content uses `display:none` (not unmounted) to preserve chat state.
 * - Graph content uses `display:none` (not unmounted) to preserve graph state.
 *
 * Mirrors the NoteCanvasLayout pattern for consistent UX.
 */
import { type ReactNode, lazy, Suspense } from 'react';
import { motion } from 'motion/react';
import { MessageSquare, Network } from 'lucide-react';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import { CollapsedChatStrip } from '@/components/editor/CollapsedChatStrip';
import { NoteCanvasMobileLayout } from '@/components/editor/NoteCanvasMobileLayout';
import { cn } from '@/lib/utils';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

const ChatView = lazy(() =>
  import('@/features/ai/ChatView/ChatView').then((m) => ({ default: m.ChatView }))
);

export type RightPanelTab = 'chat' | 'knowledge-graph';

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
  /**
   * Optional knowledge graph content. When provided, a tab bar appears in the
   * right panel with Chat and Graph tabs. When undefined, behaves as before.
   */
  knowledgeGraphContent?: ReactNode;
  /** Active right panel tab. Required when knowledgeGraphContent is provided. */
  rightPanelTab?: RightPanelTab;
  /** Callback to change the active right panel tab. */
  onRightPanelTabChange?: (tab: RightPanelTab) => void;
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
  knowledgeGraphContent,
  rightPanelTab = 'chat',
  onRightPanelTabChange,
}: IssueNoteLayoutProps) {
  const isSmallScreen = useMediaQuery('(max-width: 1023px)');
  const pilotSpaceStore = aiStore.pilotSpace;

  const hasGraphTab = !!knowledgeGraphContent;

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

  /**
   * Right panel inner content with optional tab bar.
   * Chat is hidden via CSS (not unmounted) to preserve ChatView state.
   */
  const rightPanelContent = (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {hasGraphTab && onRightPanelTabChange && (
        <div
          className="flex h-12 shrink-0 border-b border-border"
          role="tablist"
          aria-label="Right panel tabs"
        >
          <button
            role="tab"
            aria-selected={rightPanelTab === 'chat'}
            onClick={() => onRightPanelTabChange('chat')}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors',
              rightPanelTab === 'chat'
                ? 'border-b-2 border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Chat
          </button>
          <button
            role="tab"
            aria-selected={rightPanelTab === 'knowledge-graph'}
            onClick={() => onRightPanelTabChange('knowledge-graph')}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors',
              rightPanelTab === 'knowledge-graph'
                ? 'border-b-2 border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Network className="h-3.5 w-3.5" />
            Graph
          </button>
        </div>
      )}

      {/* Chat: always mounted, hidden via CSS when graph tab is active */}
      <div
        className={cn(
          'flex-1 overflow-hidden min-h-0',
          hasGraphTab && rightPanelTab === 'knowledge-graph' ? 'hidden' : 'flex'
        )}
        role="tabpanel"
        aria-label="Chat panel"
        data-testid="chat-panel"
      >
        {chatViewContent}
      </div>

      {/* Graph: always mounted when content is provided, hidden via CSS when chat tab is active */}
      {hasGraphTab && (
        <div
          className={cn(
            'flex-1 overflow-hidden min-h-0',
            rightPanelTab !== 'knowledge-graph' && 'hidden'
          )}
          role="tabpanel"
          aria-label="Knowledge graph panel"
        >
          {knowledgeGraphContent}
        </div>
      )}
    </div>
  );

  const leftColumn = (
    <div className="flex flex-col h-full min-h-0">
      {headerContent}
      <div className="flex-1 overflow-hidden min-h-0">{editorContent}</div>
    </div>
  );

  // Mobile/Tablet layout — chat-only on mobile (graph accessible via desktop)
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

  // Desktop: Chat open — full resizable layout with right panel visible
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
            aria-label="Right panel"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="h-full w-full overflow-hidden border-l border-border"
          >
            {rightPanelContent}
          </motion.aside>
        </ResizablePanel>
      </ResizablePanelGroup>
    );
  }

  // Desktop: Chat closed — ChatView stays mounted but the panel is hidden;
  // CollapsedChatStrip gives users a way to re-open it.
  return (
    <div className="flex h-full w-full overflow-hidden">
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {headerContent}
        <div className="flex-1 overflow-hidden min-h-0">{editorContent}</div>
      </div>
      {/* Keep ChatView mounted so streaming state is preserved */}
      <div className="hidden" aria-hidden="true">
        {rightPanelContent}
      </div>
      <CollapsedChatStrip onClick={onChatOpen} />
    </div>
  );
}
