/**
 * IssueDescriptionEditor component tests (T032).
 *
 * Verifies editor content area, Description heading,
 * SaveStatus rendering, and read-only state when disabled.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useEditor } from '@tiptap/react';
import { IssueDescriptionEditor } from '../issue-description-editor';

const mockUseEditor = vi.mocked(useEditor);

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockEditorInstance = {
  getHTML: vi.fn(() => '<p>test</p>'),
  getText: vi.fn(() => 'test'),
  commands: { setContent: vi.fn() },
  on: vi.fn(),
  off: vi.fn(),
  destroy: vi.fn(),
  isDestroyed: false,
  isEditable: true,
  setEditable: vi.fn(),
};

vi.mock('@tiptap/react', () => ({
  useEditor: vi.fn(() => mockEditorInstance),
  EditorContent: vi.fn(({ editor }: { editor: unknown }) => (
    <div data-testid="editor-content">{editor ? 'Editor loaded' : 'No editor'}</div>
  )),
}));

vi.mock('@/features/issues/editor/create-issue-editor-extensions', () => ({
  createIssueEditorExtensions: vi.fn(() => []),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn(), onAuthStateChange: vi.fn() },
  },
}));

vi.mock('@/stores', () => ({
  useIssueStore: () => ({
    getSaveStatus: vi.fn().mockReturnValue('idle'),
    setSaveStatus: vi.fn(),
  }),
}));

vi.mock('@/features/issues/hooks/use-update-issue', () => ({
  useUpdateIssue: () => ({
    mutateAsync: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/features/issues/hooks/use-save-status', () => ({
  useSaveStatus: () => ({
    status: 'idle',
    wrapMutation: vi.fn((fn: () => Promise<unknown>) => fn()),
  }),
}));

vi.mock('@/components/ui/save-status', () => ({
  SaveStatus: ({ status }: { status: string }) => <span data-testid="save-status">{status}</span>,
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssueDescriptionEditor', () => {
  const defaultProps = {
    content: '<p>Initial content</p>',
    issueId: 'issue-1',
    workspaceId: 'ws-1',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockEditorInstance.isEditable = true;
  });

  it('renders editor content area', () => {
    render(<IssueDescriptionEditor {...defaultProps} />);

    expect(screen.getByTestId('editor-content')).toBeInTheDocument();
    expect(screen.getByText('Editor loaded')).toBeInTheDocument();
  });

  it('shows "Description" heading', () => {
    render(<IssueDescriptionEditor {...defaultProps} />);

    expect(screen.getByText('Description')).toBeInTheDocument();
  });

  it('SaveStatus component renders', () => {
    render(<IssueDescriptionEditor {...defaultProps} />);

    expect(screen.getByTestId('save-status')).toBeInTheDocument();
  });

  it('renders in read-only when disabled', () => {
    render(<IssueDescriptionEditor {...defaultProps} disabled />);

    // useEditor should have been called with editable: false
    const lastCall = mockUseEditor.mock.calls[mockUseEditor.mock.calls.length - 1]![0] as Record<
      string,
      unknown
    >;
    expect(lastCall.editable).toBe(false);
  });

  it('renders editor with provided content', () => {
    render(<IssueDescriptionEditor {...defaultProps} content="<p>Hello world</p>" />);

    const lastCall = mockUseEditor.mock.calls[mockUseEditor.mock.calls.length - 1]![0] as Record<
      string,
      unknown
    >;
    expect(lastCall.content).toBe('<p>Hello world</p>');
  });

  it('renders empty string when content is undefined', () => {
    render(<IssueDescriptionEditor {...defaultProps} content={undefined} />);

    const lastCall = mockUseEditor.mock.calls[mockUseEditor.mock.calls.length - 1]![0] as Record<
      string,
      unknown
    >;
    expect(lastCall.content).toBe('');
  });

  it('applies disabled styling when disabled', () => {
    const { container } = render(<IssueDescriptionEditor {...defaultProps} disabled />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('opacity-60');
    expect(wrapper.className).toContain('cursor-not-allowed');
  });
});
