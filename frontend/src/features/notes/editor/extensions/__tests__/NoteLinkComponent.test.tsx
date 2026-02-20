/**
 * Unit tests for NoteLinkComponent.
 *
 * Tests inline note link chip rendering, title resolution from editor storage,
 * broken link state, click navigation, and accessibility attributes.
 *
 * @module features/notes/editor/extensions/__tests__/NoteLinkComponent.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NoteLinkComponent } from '../NoteLinkComponent';
import type { NodeViewProps } from '@tiptap/react';

const mockPush = vi.fn();

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-ws' }),
  useRouter: () => ({ push: mockPush }),
}));

// Mock NodeViewWrapper
vi.mock('@tiptap/react', () => ({
  NodeViewWrapper: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className?: string;
    as?: string;
  }) => <span className={className}>{children}</span>,
}));

// Mock Tooltip
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="tooltip-content">{children}</div>
  ),
}));

const mockEditorOn = vi.fn();
const mockEditorOff = vi.fn();

function createMockProps(
  overrides: {
    noteId?: string;
    noteTitles?: Map<string, string>;
    onClick?: (noteId: string) => void;
    workspaceSlug?: string;
  } = {}
): NodeViewProps {
  const { noteId = 'note-abc', noteTitles, onClick, workspaceSlug } = overrides;

  return {
    node: {
      attrs: { noteId },
      type: { name: 'noteLink' },
    },
    editor: {
      on: mockEditorOn,
      off: mockEditorOff,
    } as unknown as NodeViewProps['editor'],
    getPos: () => 0,
    updateAttributes: vi.fn(),
    deleteNode: vi.fn(),
    selected: false,
    extension: {
      options: {
        onClick,
        workspaceSlug: workspaceSlug ?? '',
      },
      storage: {
        noteTitles: noteTitles ?? new Map(),
      },
    } as unknown as NodeViewProps['extension'],
    HTMLAttributes: {},
    decorations: [] as unknown as NodeViewProps['decorations'],
  } as unknown as NodeViewProps;
}

describe('NoteLinkComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockEditorOn.mockClear();
    mockEditorOff.mockClear();
  });

  it('renders "Loading..." when title is not yet resolved', () => {
    const props = createMockProps();
    render(<NoteLinkComponent {...props} />);

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders note title when resolved from editor storage', () => {
    const titles = new Map([['note-abc', 'My Design Doc']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    expect(screen.getByText('My Design Doc')).toBeInTheDocument();
  });

  it('renders broken link state when title is empty string', () => {
    const titles = new Map([['note-abc', '']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    expect(screen.getByText('Note not found')).toBeInTheDocument();
    // Should have broken-link class
    const chip = screen.getByRole('link');
    expect(chip.className).toContain('broken-link');
  });

  it('has correct aria-label for accessible note link', () => {
    const titles = new Map([['note-abc', 'Architecture Notes']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    const chip = screen.getByRole('link');
    expect(chip).toHaveAttribute('aria-label', 'Linked note: Architecture Notes');
  });

  it('navigates to note URL on click when no onClick handler', async () => {
    const user = userEvent.setup();
    const titles = new Map([['note-abc', 'My Note']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    const chip = screen.getByRole('link');
    await user.click(chip);

    expect(mockPush).toHaveBeenCalledWith('/test-ws/notes/note-abc');
  });

  it('calls onClick handler when provided instead of navigating', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    const titles = new Map([['note-abc', 'My Note']]);
    const props = createMockProps({ noteTitles: titles, onClick });
    render(<NoteLinkComponent {...props} />);

    const chip = screen.getByRole('link');
    await user.click(chip);

    expect(onClick).toHaveBeenCalledWith('note-abc');
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('does not navigate when link is broken', async () => {
    const user = userEvent.setup();
    const titles = new Map([['note-abc', '']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    const chip = screen.getByRole('link');
    await user.click(chip);

    expect(mockPush).not.toHaveBeenCalled();
  });

  it('renders tooltip for broken links', () => {
    const titles = new Map([['note-abc', '']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    expect(screen.getByTestId('tooltip-content')).toHaveTextContent(
      'This note has been deleted or is unavailable.'
    );
  });

  it('does not render tooltip for valid links', () => {
    const titles = new Map([['note-abc', 'Valid Note']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    expect(screen.queryByTestId('tooltip-content')).not.toBeInTheDocument();
  });

  it('renders data-note-id attribute for DOM identification', () => {
    const titles = new Map([['note-xyz', 'Test']]);
    const props = createMockProps({ noteId: 'note-xyz', noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    const chip = screen.getByRole('link');
    expect(chip).toHaveAttribute('data-note-id', 'note-xyz');
  });

  it('handles keyboard enter for navigation', async () => {
    const user = userEvent.setup();
    const titles = new Map([['note-abc', 'Keyboard Test']]);
    const props = createMockProps({ noteTitles: titles });
    render(<NoteLinkComponent {...props} />);

    const chip = screen.getByRole('link');
    chip.focus();
    await user.keyboard('{Enter}');

    expect(mockPush).toHaveBeenCalledWith('/test-ws/notes/note-abc');
  });
});
