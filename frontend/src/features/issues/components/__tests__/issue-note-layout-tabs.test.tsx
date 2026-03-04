/**
 * IssueNoteLayout tab system tests.
 *
 * Verifies:
 * - Tab bar renders when knowledgeGraphContent is provided
 * - Tab bar is absent when knowledgeGraphContent is not provided
 * - Clicking Graph tab calls onRightPanelTabChange('knowledge-graph')
 * - Chat panel uses display:none (not unmounted) when graph tab is active
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('@/hooks/useMediaQuery', () => ({
  useMediaQuery: () => false, // Desktop mode
}));

vi.mock('@/features/ai/ChatView/ChatView', () => ({
  ChatView: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="chat-view">
      <button onClick={onClose}>Close chat</button>
    </div>
  ),
}));

vi.mock('@/components/editor/CollapsedChatStrip', () => ({
  CollapsedChatStrip: ({ onClick }: { onClick: () => void }) => (
    <button data-testid="collapsed-chat-strip" onClick={onClick}>
      Open chat
    </button>
  ),
}));

vi.mock('@/components/editor/NoteCanvasMobileLayout', () => ({
  NoteCanvasMobileLayout: () => <div data-testid="mobile-layout" />,
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
  ResizablePanel: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="resizable-panel" {...props}>
      {children}
    </div>
  ),
  ResizableHandle: () => <div data-testid="resizable-handle" />,
}));

vi.mock('motion/react', () => ({
  motion: {
    aside: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
      <aside {...props}>{children}</aside>
    ),
  },
}));

// ---------------------------------------------------------------------------
// Import component under test (after mocks are registered)
// ---------------------------------------------------------------------------

import { IssueNoteLayout } from '../issue-note-layout';
import type { RightPanelTab } from '../issue-note-layout';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

const DEFAULT_PROPS = {
  editorContent: <div data-testid="editor-content">Editor</div>,
  aiStore: { pilotSpace: {} as PilotSpaceStore },
  isChatOpen: true,
  onChatOpen: vi.fn(),
  onChatClose: vi.fn(),
};

function renderLayout(overrides: Partial<React.ComponentProps<typeof IssueNoteLayout>> = {}) {
  return render(<IssueNoteLayout {...DEFAULT_PROPS} {...overrides} />);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssueNoteLayout — tab system', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render tab bar when knowledgeGraphContent is not provided', () => {
    renderLayout();
    expect(screen.queryByRole('tablist')).toBeNull();
  });

  it('renders tab bar with Chat and Graph buttons when knowledgeGraphContent is provided', () => {
    const onRightPanelTabChange = vi.fn();
    renderLayout({
      knowledgeGraphContent: <div data-testid="graph-content">Graph</div>,
      rightPanelTab: 'chat',
      onRightPanelTabChange,
    });

    const tablist = screen.getByRole('tablist', { name: 'Right panel tabs' });
    expect(tablist).toBeTruthy();

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(2);
    expect(tabs[0]).toHaveTextContent('Chat');
    expect(tabs[1]).toHaveTextContent('Graph');
  });

  it('calls onRightPanelTabChange with knowledge-graph when Graph tab is clicked', () => {
    const onRightPanelTabChange = vi.fn();
    renderLayout({
      knowledgeGraphContent: <div data-testid="graph-content">Graph</div>,
      rightPanelTab: 'chat',
      onRightPanelTabChange,
    });

    const graphTab = screen.getByRole('tab', { name: /graph/i });
    fireEvent.click(graphTab);

    expect(onRightPanelTabChange).toHaveBeenCalledWith('knowledge-graph');
  });

  it('calls onRightPanelTabChange with chat when Chat tab is clicked', () => {
    const onRightPanelTabChange = vi.fn();
    renderLayout({
      knowledgeGraphContent: <div data-testid="graph-content">Graph</div>,
      rightPanelTab: 'knowledge-graph' as RightPanelTab,
      onRightPanelTabChange,
    });

    const chatTab = screen.getByRole('tab', { name: /chat/i });
    fireEvent.click(chatTab);

    expect(onRightPanelTabChange).toHaveBeenCalledWith('chat');
  });

  it('chat panel has hidden class (not unmounted) when graph tab is active', () => {
    renderLayout({
      knowledgeGraphContent: <div data-testid="graph-content">Graph</div>,
      rightPanelTab: 'knowledge-graph' as RightPanelTab,
      onRightPanelTabChange: vi.fn(),
    });

    // Chat panel should exist in DOM but be visually hidden via Tailwind 'hidden' class
    const chatPanel = screen.getByTestId('chat-panel');
    expect(chatPanel).toBeTruthy();
    expect(chatPanel).toHaveClass('hidden');

    // Chat view content should still be mounted (not removed from DOM)
    expect(screen.getByTestId('chat-view')).toBeTruthy();
  });

  it('renders graph content when graph tab is active', () => {
    renderLayout({
      knowledgeGraphContent: <div data-testid="graph-content">Graph</div>,
      rightPanelTab: 'knowledge-graph' as RightPanelTab,
      onRightPanelTabChange: vi.fn(),
    });

    expect(screen.getByTestId('graph-content')).toBeTruthy();
  });

  it('graph panel is always mounted but hidden when chat tab is active', () => {
    renderLayout({
      knowledgeGraphContent: <div data-testid="graph-content">Graph</div>,
      rightPanelTab: 'chat',
      onRightPanelTabChange: vi.fn(),
    });

    // Graph content stays mounted (not removed from DOM) but is visually hidden
    const graphContent = screen.getByTestId('graph-content');
    expect(graphContent).toBeTruthy();
    // The parent panel div should have the 'hidden' class
    expect(graphContent.parentElement).toHaveClass('hidden');
  });

  it('Chat tab has aria-selected=true when chat tab is active', () => {
    renderLayout({
      knowledgeGraphContent: <div>Graph</div>,
      rightPanelTab: 'chat',
      onRightPanelTabChange: vi.fn(),
    });

    const chatTab = screen.getByRole('tab', { name: /chat/i });
    expect(chatTab).toHaveAttribute('aria-selected', 'true');

    const graphTab = screen.getByRole('tab', { name: /graph/i });
    expect(graphTab).toHaveAttribute('aria-selected', 'false');
  });
});
