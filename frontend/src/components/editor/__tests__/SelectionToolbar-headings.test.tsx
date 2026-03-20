/**
 * SelectionToolbar heading dropdown and pull quote toggle tests
 *
 * EDIT-02: User can toggle H1/H2/H3 headings from floating toolbar on text selection.
 * EDIT-01 (toolbar side): Pull quote toggle button in toolbar.
 *
 * RED phase: SelectionToolbar does not have the heading dropdown or pull quote button yet.
 * Plan 03 adds these. Tests will fail with "Unable to find element" until then.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { Editor } from '@tiptap/react';
import { SelectionToolbar } from '../SelectionToolbar';

// Mock supabase before any store imports
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

// Mock AI store — SelectionToolbar calls getAIStore() unconditionally
vi.mock('@/stores/ai/AIStore', () => ({
  getAIStore: vi.fn(() => ({
    pilotSpace: {
      setWorkspaceId: vi.fn(),
      setNoteContext: vi.fn(),
      noteContext: null,
      sendMessage: vi.fn(),
    },
    ghostText: { requestSuggestion: vi.fn() },
    marginAnnotation: { autoTriggerAnnotations: vi.fn() },
  })),
}));

// Mock useSelectionAIActions — used in SelectionToolbar
vi.mock('@/features/notes/editor/hooks/useSelectionAIActions', () => ({
  useSelectionAIActions: vi.fn(() => ({
    askPilot: vi.fn(),
    enhanceSelection: vi.fn(),
  })),
}));

/** Build a minimal mock editor with the API surface SelectionToolbar uses */
function buildMockEditor(
  overrides: {
    isActiveMap?: Record<string, boolean>;
  } = {}
): { editor: Editor; fireSelectionUpdate: () => void } {
  const runMock = vi.fn();
  const selectionListeners: Array<() => void> = [];

  const focusMock = vi.fn(() => chainResult);
  const headingMock = vi.fn(() => chainResult);
  const paragraphMock = vi.fn(() => chainResult);
  const blockquoteMock = vi.fn(() => chainResult);
  const attrsMock = vi.fn(() => chainResult);

  const chainResult = {
    focus: focusMock,
    toggleHeading: headingMock,
    setParagraph: paragraphMock,
    toggleBlockquote: blockquoteMock,
    updateAttributes: attrsMock,
    run: runMock,
  };

  const editor = {
    isActive: vi.fn((name: string, attrs?: object) => {
      const key = attrs ? `${name}:${JSON.stringify(attrs)}` : name;
      return overrides.isActiveMap?.[key] ?? false;
    }),
    chain: vi.fn(() => chainResult),
    state: {
      selection: { from: 1, to: 10, empty: false },
      doc: {
        textBetween: vi.fn(() => 'selected text'),
        nodesBetween: vi.fn(),
      },
    },
    view: {
      coordsAtPos: vi.fn(() => ({ left: 100, top: 200, bottom: 220 })),
    },
    on: vi.fn((event: string, cb: () => void) => {
      if (event === 'selectionUpdate') {
        selectionListeners.push(cb);
      }
    }),
    off: vi.fn(),
    commands: {
      insertContent: vi.fn(),
    },
  } as unknown as Editor;

  /** Fire a fake selectionUpdate event to make the toolbar visible */
  function fireSelectionUpdate() {
    selectionListeners.forEach((listener) => listener());
  }

  return { editor, fireSelectionUpdate };
}

describe('SelectionToolbar — heading dropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('test_heading_label_shows_H1_when_heading_level_1_active', () => {
    const { editor, fireSelectionUpdate } = buildMockEditor({
      isActiveMap: { 'heading:{"level":1}': true },
    });
    render(<SelectionToolbar editor={editor} />);

    // Fire selectionUpdate to make toolbar visible
    act(() => {
      fireSelectionUpdate();
    });

    const trigger = screen.getByTestId('heading-dropdown-trigger');
    expect(trigger).toHaveTextContent('H1');
  });

  it('test_heading_label_shows_H2_when_heading_level_2_active', () => {
    const { editor, fireSelectionUpdate } = buildMockEditor({
      isActiveMap: { 'heading:{"level":2}': true },
    });
    render(<SelectionToolbar editor={editor} />);

    act(() => {
      fireSelectionUpdate();
    });

    const trigger = screen.getByTestId('heading-dropdown-trigger');
    expect(trigger).toHaveTextContent('H2');
  });

  it('test_heading_label_shows_P_when_no_heading_active', () => {
    const { editor, fireSelectionUpdate } = buildMockEditor({ isActiveMap: {} });
    render(<SelectionToolbar editor={editor} />);

    act(() => {
      fireSelectionUpdate();
    });

    const trigger = screen.getByTestId('heading-dropdown-trigger');
    expect(trigger).toHaveTextContent('P');
  });

  it('test_click_H2_calls_toggleHeading_level_2', async () => {
    const user = userEvent.setup();
    const { editor, fireSelectionUpdate } = buildMockEditor({ isActiveMap: {} });
    render(<SelectionToolbar editor={editor} />);

    act(() => {
      fireSelectionUpdate();
    });

    await user.click(screen.getByTestId('heading-dropdown-trigger'));
    await user.click(screen.getByTestId('heading-option-2'));
    expect(editor.chain).toHaveBeenCalled();
  });

  it('test_click_Normal_calls_setParagraph', async () => {
    const user = userEvent.setup();
    const { editor, fireSelectionUpdate } = buildMockEditor({ isActiveMap: {} });
    render(<SelectionToolbar editor={editor} />);

    act(() => {
      fireSelectionUpdate();
    });

    await user.click(screen.getByTestId('heading-dropdown-trigger'));
    await user.click(screen.getByTestId('heading-option-normal'));
    expect(editor.chain).toHaveBeenCalled();
  });

  it('test_pull_quote_toggle_shows_active_state_when_in_pull_quote', () => {
    const { editor, fireSelectionUpdate } = buildMockEditor({
      isActiveMap: { 'blockquote:{"pullQuote":true}': true },
    });
    render(<SelectionToolbar editor={editor} />);

    act(() => {
      fireSelectionUpdate();
    });

    const button = screen.getByTestId('pull-quote-toggle');
    // Active state — button should have secondary variant styling indicator
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('data-active', 'true');
  });
});
