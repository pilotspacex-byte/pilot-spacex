/**
 * Unit tests for NoteCanvasEditor extracted components and utilities.
 *
 * Tests cover:
 * - EditorErrorFallback: error display, retry button interaction
 * - EditorSkeleton: loading skeleton rendering
 * - extractFirstHeadingText: heading extraction (via new import path)
 * - NoteCanvasLayout: error/loading state rendering, responsive layout branching
 *
 * @module components/editor/__tests__/NoteCanvasEditor.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock supabase (must be before any imports that trigger it)
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
    },
    from: vi.fn(() => ({ select: vi.fn(), insert: vi.fn(), update: vi.fn(), delete: vi.fn() })),
  },
  getAuthHeaders: vi.fn(() => ({})),
}));

// Mock stores that NoteCanvasEditor imports
vi.mock('@/stores/ai/AIStore', () => ({
  getAIStore: vi.fn(() => ({
    pilotSpace: {
      setWorkspaceId: vi.fn(),
      setNoteContext: vi.fn(),
      noteContext: null,
      sendMessage: vi.fn(),
    },
    ghostText: { requestSuggestion: vi.fn() },
    marginAnnotation: { autoTriggerAnnotations: vi.fn(), getAnnotationsForNote: vi.fn(() => []) },
  })),
}));

vi.mock('@/stores/RootStore', () => ({
  useWorkspaceStore: vi.fn(() => ({
    getWorkspaceBySlug: vi.fn(),
    currentWorkspace: { id: 'ws-123' },
  })),
  useStores: vi.fn(() => ({})),
}));

vi.mock('@/hooks/useMediaQuery', () => ({
  useResponsive: vi.fn(() => ({ isSmallScreen: false })),
}));

vi.mock('@/hooks/useAIAutoScroll', () => ({
  useAIAutoScroll: vi.fn(() => ({
    hasOffScreenUpdate: false,
    offScreenDirection: 'below',
    scrollToBlock: vi.fn(),
    dismissIndicator: vi.fn(),
  })),
}));

vi.mock('@/features/notes/editor/hooks/useSelectionContext', () => ({
  useSelectionContext: vi.fn(),
}));

vi.mock('@/features/notes/editor/hooks/useContentUpdates', () => ({
  useContentUpdates: vi.fn(() => ({
    processingBlockIds: [],
    userEditingBlockId: null,
  })),
}));

vi.mock('@/features/notes/editor/extensions', () => ({
  createEditorExtensions: vi.fn(() => []),
}));

vi.mock('../hooks/useEditorSync', () => ({
  useEditorSync: vi.fn(),
}));

vi.mock('@/hooks/useNoteHealth', () => ({
  useNoteHealth: vi.fn(() => ({
    extractableCount: 0,
    clarityIssueCount: 0,
    overallScore: 'good',
    suggestedPrompts: [],
  })),
}));

vi.mock('react-resizable-panels', () => ({
  usePanelRef: vi.fn(() => ({ current: null })),
}));

// Mock TipTap useEditor to control editor instance
vi.mock('@tiptap/react', () => ({
  useEditor: vi.fn(() => null),
  EditorContent: ({ editor }: { editor: unknown }) => (
    <div data-testid="mock-editor-content">{editor ? 'editor-loaded' : 'no-editor'}</div>
  ),
}));

// Mock child components for NoteCanvasLayout tests
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(fn: T) => fn,
}));

vi.mock('motion/react', () => ({
  motion: {
    aside: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <aside {...props}>{children}</aside>
    ),
    div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
}));

vi.mock('@/features/ai/ChatView/ChatView', () => ({
  ChatView: () => <div data-testid="mock-chat-view" />,
}));

vi.mock('@/components/ui/resizable', () => ({
  ResizablePanelGroup: ({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="resizable-panel-group" {...props}>
      {children}
    </div>
  ),
  ResizablePanel: ({ children }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="resizable-panel">{children}</div>
  ),
  ResizableHandle: () => <div data-testid="resizable-handle" />,
}));

vi.mock('../NoteMetadata', () => ({
  NoteMetadata: () => <div data-testid="mock-note-metadata" />,
}));

vi.mock('../SelectionToolbar', () => ({
  SelectionToolbar: () => <div data-testid="mock-selection-toolbar" />,
}));

vi.mock('../InlineNoteHeader', () => ({
  InlineNoteHeader: () => <div data-testid="mock-inline-note-header" />,
}));

vi.mock('../CollapsedChatStrip', () => ({
  CollapsedChatStrip: ({ onClick }: { onClick: () => void }) => (
    <button data-testid="mock-collapsed-chat-strip" onClick={onClick}>
      Open Chat
    </button>
  ),
}));

vi.mock('../OffScreenAIIndicator', () => ({
  OffScreenAIIndicator: () => <div data-testid="mock-offscreen-indicator" />,
}));

vi.mock('../NoteCanvasMobileLayout', () => ({
  NoteCanvasMobileLayout: () => <div data-testid="mock-mobile-layout" />,
}));

vi.mock('../NoteHealthBadges', () => ({
  NoteHealthBadges: () => <div data-testid="mock-note-health-badges" />,
}));

import { EditorErrorFallback, EditorSkeleton, extractFirstHeadingText } from '../NoteCanvasEditor';
import { NoteCanvasLayout } from '../NoteCanvasLayout';
import { useResponsive } from '@/hooks/useMediaQuery';
import { useEditor } from '@tiptap/react';

const mockUseResponsive = vi.mocked(useResponsive);
const mockUseEditor = vi.mocked(useEditor);

// ---------------------------------------------------------------------------
// EditorErrorFallback
// ---------------------------------------------------------------------------
describe('EditorErrorFallback', () => {
  it('renders the error message text', () => {
    render(<EditorErrorFallback error="Something broke" onRetry={vi.fn()} />);
    expect(screen.getByText('Something broke')).toBeInTheDocument();
  });

  it('renders the "Editor Error" heading', () => {
    render(<EditorErrorFallback error="fail" onRetry={vi.fn()} />);
    expect(screen.getByText('Editor Error')).toBeInTheDocument();
  });

  it('renders a "Try Again" button', () => {
    render(<EditorErrorFallback error="fail" onRetry={vi.fn()} />);
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('calls onRetry when the retry button is clicked', () => {
    const onRetry = vi.fn();
    render(<EditorErrorFallback error="fail" onRetry={onRetry} />);

    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('displays the AlertTriangle icon in a destructive container', () => {
    const { container } = render(<EditorErrorFallback error="fail" onRetry={vi.fn()} />);
    const iconContainer = container.querySelector('.bg-destructive\\/10');
    expect(iconContainer).toBeInTheDocument();
  });

  it('renders long error messages without truncation', () => {
    const longError = 'A'.repeat(200);
    render(<EditorErrorFallback error={longError} onRetry={vi.fn()} />);
    expect(screen.getByText(longError)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// EditorSkeleton
// ---------------------------------------------------------------------------
describe('EditorSkeleton', () => {
  it('renders skeleton elements', () => {
    const { container } = render(<EditorSkeleton />);
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBe(9);
  });

  it('renders within a flex column container', () => {
    const { container } = render(<EditorSkeleton />);
    const wrapper = container.firstElementChild;
    expect(wrapper).toHaveClass('flex', 'flex-col');
  });

  it('renders a heading-width skeleton (3/4 width)', () => {
    const { container } = render(<EditorSkeleton />);
    const headingSkeleton = container.querySelector('.w-3\\/4');
    expect(headingSkeleton).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// extractFirstHeadingText (re-exported from NoteCanvasEditor)
// ---------------------------------------------------------------------------
describe('extractFirstHeadingText (NoteCanvasEditor export)', () => {
  function createMockDoc(nodes: Array<{ type: { name: string }; textContent: string }>) {
    return {
      forEach: (cb: (node: { type: { name: string }; textContent: string }) => void) => {
        nodes.forEach(cb);
      },
    };
  }

  it('returns empty string for empty document', () => {
    expect(extractFirstHeadingText(createMockDoc([]))).toBe('');
  });

  it('returns first heading text', () => {
    const doc = createMockDoc([
      { type: { name: 'paragraph' }, textContent: 'intro' },
      { type: { name: 'heading' }, textContent: 'Title' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('Title');
  });

  it('returns empty string when no headings exist', () => {
    const doc = createMockDoc([{ type: { name: 'paragraph' }, textContent: 'text' }]);
    expect(extractFirstHeadingText(doc)).toBe('');
  });

  it('returns first non-empty heading when first heading is empty', () => {
    const doc = createMockDoc([
      { type: { name: 'heading' }, textContent: '' },
      { type: { name: 'heading' }, textContent: 'Real Title' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('Real Title');
  });

  it('ignores subsequent headings after finding the first', () => {
    const doc = createMockDoc([
      { type: { name: 'heading' }, textContent: 'First' },
      { type: { name: 'heading' }, textContent: 'Second' },
    ]);
    expect(extractFirstHeadingText(doc)).toBe('First');
  });
});

// ---------------------------------------------------------------------------
// NoteCanvasLayout
// ---------------------------------------------------------------------------
const defaultProps = {
  noteId: 'note-1',
  title: 'Test Note',
  content: { type: 'doc' as const, content: [] },
};

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('NoteCanvasLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: desktop with editor loaded
    mockUseResponsive.mockReturnValue({
      isSmallScreen: false,
      isMobile: false,
      isTablet: false,
      isDesktop: true,
      isLargeDesktop: false,
      isLargeScreen: false,
    });
    mockUseEditor.mockReturnValue(null as unknown as ReturnType<typeof mockUseEditor>);
  });

  // --- Error states ---
  it('renders EditorErrorFallback when error prop is provided', () => {
    renderWithQueryClient(<NoteCanvasLayout {...defaultProps} error="Network error" />);
    expect(screen.getByText('Editor Error')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('prioritizes error prop over editorError', () => {
    renderWithQueryClient(<NoteCanvasLayout {...defaultProps} error="Prop error" />);
    expect(screen.getByText('Prop error')).toBeInTheDocument();
  });

  // --- Loading states ---
  it('renders EditorSkeleton when isLoading is true', () => {
    const { container } = renderWithQueryClient(<NoteCanvasLayout {...defaultProps} isLoading />);
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBe(9);
  });

  it('renders EditorSkeleton when editor is null (not yet initialized)', () => {
    mockUseEditor.mockReturnValue(null as unknown as ReturnType<typeof mockUseEditor>);
    const { container } = renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBe(9);
  });

  // --- Desktop layout (editor loaded) ---
  describe('when editor is loaded on desktop', () => {
    beforeEach(() => {
      const mockEditor = {
        isDestroyed: false,
        getJSON: vi.fn(() => ({})),
        state: {
          doc: { descendants: vi.fn(), forEach: vi.fn(), content: { size: 0 }, nodeSize: 2 },
          selection: { empty: true },
          tr: {},
        },
        view: { dispatch: vi.fn() },
        storage: {},
        commands: { setContent: vi.fn() },
        on: vi.fn(),
        off: vi.fn(),
      };
      mockUseEditor.mockReturnValue(mockEditor as unknown as ReturnType<typeof useEditor>);
      mockUseResponsive.mockReturnValue({
        isSmallScreen: false,
        isMobile: false,
        isTablet: false,
        isDesktop: true,
        isLargeDesktop: false,
        isLargeScreen: false,
      });
    });

    it('renders note-editor wrapper with data-testid', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.getByTestId('note-editor')).toBeInTheDocument();
    });

    it('renders resizable panel layout when ChatView is open (default)', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.getByTestId('resizable-panel-group')).toBeInTheDocument();
      expect(screen.getByTestId('resizable-handle')).toBeInTheDocument();
    });

    it('renders editor content and ChatView inside panels', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.getByTestId('mock-editor-content')).toBeInTheDocument();
      expect(screen.getByTestId('mock-chat-view')).toBeInTheDocument();
    });

    it('renders InlineNoteHeader when title is provided', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} title="My Note" />);
      expect(screen.getByTestId('mock-inline-note-header')).toBeInTheDocument();
    });

    it('renders NoteMetadata', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.getByTestId('mock-note-metadata')).toBeInTheDocument();
    });

    it('renders SelectionToolbar', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.getByTestId('mock-selection-toolbar')).toBeInTheDocument();
    });

    it('renders OffScreenAIIndicator', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.getByTestId('mock-offscreen-indicator')).toBeInTheDocument();
    });

    it('does not render mobile layout', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.queryByTestId('mock-mobile-layout')).not.toBeInTheDocument();
    });
  });

  // --- Mobile layout ---
  describe('when on small screen', () => {
    beforeEach(() => {
      const mockEditor = {
        isDestroyed: false,
        getJSON: vi.fn(() => ({})),
        state: {
          doc: { descendants: vi.fn(), forEach: vi.fn(), content: { size: 0 }, nodeSize: 2 },
          selection: { empty: true },
          tr: {},
        },
        view: { dispatch: vi.fn() },
        storage: {},
        commands: { setContent: vi.fn() },
        on: vi.fn(),
        off: vi.fn(),
      };
      mockUseEditor.mockReturnValue(mockEditor as unknown as ReturnType<typeof useEditor>);
      mockUseResponsive.mockReturnValue({
        isSmallScreen: true,
        isMobile: true,
        isTablet: false,
        isDesktop: false,
        isLargeDesktop: false,
        isLargeScreen: false,
      });
    });

    it('renders mobile layout', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.getByTestId('mock-mobile-layout')).toBeInTheDocument();
    });

    it('does not render resizable panel group', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.queryByTestId('resizable-panel-group')).not.toBeInTheDocument();
    });

    it('does not render collapsed chat strip', () => {
      renderWithQueryClient(<NoteCanvasLayout {...defaultProps} />);
      expect(screen.queryByTestId('mock-collapsed-chat-strip')).not.toBeInTheDocument();
    });
  });
});
