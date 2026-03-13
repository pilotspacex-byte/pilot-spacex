/**
 * Unit tests for NoteCanvasLayout tablet content area adaptations (UI-03).
 *
 * Tests:
 * 1. NoteCanvasLayout editor scroll area has min-w-0 on its flex container
 * 2. Editor scroll area has overflow-auto class
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { NoteCanvasLayout } from '../NoteCanvasLayout';

// Mock mobx-react-lite
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

// Mock motion/react
vi.mock('motion/react', () => ({
  motion: {
    div: ({
      children,
      className,
      ...rest
    }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div className={className} {...rest}>
        {children}
      </div>
    ),
    aside: ({
      children,
      className,
      ...rest
    }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) => (
      <aside className={className} {...rest}>
        {children}
      </aside>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Minimal mock editor
const mockEditor = {
  state: { doc: { childCount: 0 } },
  isEditable: true,
};

// Mock useNoteCanvasEditor
vi.mock('../NoteCanvasEditor', () => ({
  useNoteCanvasEditor: () => ({
    editor: mockEditor,
    editorContainerRef: { current: null },
    scrollRef: { current: null },
    chatPanelRef: { current: null },
    isChatViewOpen: false,
    setIsChatViewOpen: vi.fn(),
    chatPanelState: 'collapsed',
    isSmallScreen: false,
    aiStore: {
      pilotSpace: {},
      approval: {},
    },
    hasOffScreenUpdate: false,
    offScreenDirection: 'up' as const,
    scrollToBlock: vi.fn(),
    dismissIndicator: vi.fn(),
    handleChatViewOpen: vi.fn(),
    handleChatPanelToggle: vi.fn(),
    handleChatPanelResize: vi.fn(),
    handleRetry: vi.fn(),
    editorError: null,
    noteHealth: {
      suggestedPrompts: [],
      score: 0,
      issues: [],
    },
  }),
  EditorErrorFallback: ({ error }: { error: string }) => <div>Error: {error}</div>,
  EditorSkeleton: () => <div>Loading...</div>,
}));

// Mock TipTap EditorContent
vi.mock('@tiptap/react', () => ({
  EditorContent: () => <div data-testid="editor-content" />,
}));

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

// Mock notes hooks
vi.mock('@/features/notes/hooks', () => ({
  notesKeys: {
    detail: (workspaceId: string, noteId: string) => ['notes', workspaceId, noteId],
  },
}));

// Mock useIssueExtraction
vi.mock('@/features/notes/hooks/useIssueExtraction', () => ({
  useIssueExtraction: () => [
    { isModalOpen: false, isReviewPanelOpen: false, issues: [], isExtracting: false, error: null },
    { startExtraction: vi.fn(), closeModal: vi.fn(), closeReviewPanel: vi.fn() },
  ],
}));

// Mock lazy-loaded ChatView
vi.mock('@/features/ai/ChatView/ChatView', () => ({
  ChatView: () => <div data-testid="chat-view" />,
}));

// Mock sub-components that have their own deep deps
vi.mock('../NoteMetadata', () => ({ NoteMetadata: () => null }));
vi.mock('../SelectionToolbar', () => ({ SelectionToolbar: () => null }));
vi.mock('../InlineNoteHeader', () => ({ InlineNoteHeader: () => null }));
vi.mock('../CollapsedChatStrip', () => ({ CollapsedChatStrip: () => null }));
vi.mock('../OffScreenAIIndicator', () => ({ OffScreenAIIndicator: () => null }));
vi.mock('../NoteCanvasMobileLayout', () => ({ NoteCanvasMobileLayout: () => null }));
vi.mock('../LargeNoteWarning', () => ({ LargeNoteWarning: () => null }));
vi.mock('../NoteHealthBadges', () => ({ NoteHealthBadges: () => null }));
vi.mock('../ProjectContextHeader', () => ({ ProjectContextHeader: () => null }));
vi.mock('../sidebar', () => ({
  SidebarPanel: () => null,
  useSidebarPanel: () => ({
    isOpen: false,
    activePanel: null,
    width: 300,
    openSidebar: vi.fn(),
    closeSidebar: vi.fn(),
    setWidth: vi.fn(),
  }),
}));
vi.mock('@/features/notes/components/panels', () => ({
  PresenceSidebarPanel: () => null,
  ConversationSidebarPanel: () => null,
}));
vi.mock('@/features/notes/components/VersionPanel', () => ({ VersionPanel: () => null }));
vi.mock('@/features/notes/stores/VersionStore', () => ({ VersionStore: class {} }));

// Mock ExtractionPreviewModal and ExtractionReviewPanel
vi.mock('@/features/notes/components/ExtractionPreviewModal', () => ({
  ExtractionPreviewModal: () => null,
}));
vi.mock('@/features/notes/components/ExtractionReviewPanel', () => ({
  ExtractionReviewPanel: () => null,
}));

// Mock ResizablePanelGroup
vi.mock('@/components/ui/resizable', () => ({
  ResizablePanelGroup: ({
    children,
    className,
  }: React.HTMLAttributes<HTMLDivElement> & {
    children?: React.ReactNode;
    orientation?: string;
    id?: string;
  }) => <div className={className}>{children}</div>,
  ResizablePanel: ({
    children,
    className,
  }: React.HTMLAttributes<HTMLDivElement> & {
    children?: React.ReactNode;
    id?: string;
    defaultSize?: string;
    minSize?: string;
    maxSize?: string;
    panelRef?: unknown;
    onResize?: unknown;
  }) => <div className={className}>{children}</div>,
  ResizableHandle: () => null,
}));

const defaultProps = {
  noteId: 'note-1',
  workspaceId: 'ws-1',
  workspaceSlug: 'test-ws',
};

describe('NoteCanvasLayout tablet content area', () => {
  it('editor content flex container has min-w-0 to prevent overflow on tablet', () => {
    const { container } = render(<NoteCanvasLayout {...defaultProps} />);

    // The editorContent div is "flex flex-col min-w-0 overflow-hidden h-full"
    const flexContainer = container.querySelector('.flex.flex-col.min-w-0.overflow-hidden.h-full');
    expect(flexContainer).toBeInTheDocument();
  });

  it('editor scroll area has overflow-auto class', () => {
    const { container } = render(<NoteCanvasLayout {...defaultProps} />);

    // The scrollable editor area has "relative flex-1 overflow-auto bg-background"
    const scrollArea = container.querySelector('.overflow-auto.bg-background');
    expect(scrollArea).toBeInTheDocument();
  });

  it('renders the note editor root with data-testid', () => {
    render(<NoteCanvasLayout {...defaultProps} />);

    expect(screen.getByTestId('note-editor')).toBeInTheDocument();
  });
});
