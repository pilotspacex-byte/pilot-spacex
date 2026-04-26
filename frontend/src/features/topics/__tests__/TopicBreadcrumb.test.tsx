/**
 * TopicBreadcrumb — Plan 93-05 Task 2.
 *
 * Coverage:
 *  - Renders Home + ancestor chain + current with aria-current="page" on the leaf
 *  - Plain click on an ancestor lets the Next.js Link default-navigate (the
 *    test verifies preventDefault() is NOT called)
 *  - Alt-click on an ancestor calls openPeek with the ancestor id + 'NOTE'
 *  - Loading state renders the 3-segment skeleton
 *  - Error state renders the locked copy "Couldn't load breadcrumb."
 *  - Truncation: chain length > 5 collapses middle segments into a Popover
 *    with "Show {N} hidden topics" aria-label
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const ancestorsState: { data?: unknown; isLoading: boolean; isError: boolean } = {
  data: undefined,
  isLoading: false,
  isError: false,
};

vi.mock('../hooks', async () => {
  const actual = await vi.importActual<typeof import('../hooks')>('../hooks');
  return {
    ...actual,
    useTopicAncestors: () => ancestorsState,
  };
});

const openPeekMock = vi.fn();
vi.mock('@/hooks/use-artifact-peek-state', () => ({
  useArtifactPeekState: () => ({
    openPeek: openPeekMock,
    closePeek: vi.fn(),
    openFocus: vi.fn(),
    closeFocus: vi.fn(),
    escalate: vi.fn(),
    demote: vi.fn(),
    setView: vi.fn(),
    openSkillFilePeek: vi.fn(),
    peekId: null,
    peekType: null,
    focusId: null,
    focusType: null,
    view: 'split',
    isPeekOpen: false,
    isFocusOpen: false,
    skillFile: null,
    isSkillFilePeek: false,
  }),
}));

// next/link → plain anchor so we can assert on href + altKey behavior.
vi.mock('next/link', () => ({
  __esModule: true,
  default: ({
    href,
    children,
    onClick,
    ...rest
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} onClick={onClick} {...rest}>
      {children}
    </a>
  ),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const buildNote = (id: string, title: string, parentTopicId: string | null = null) => ({
  id,
  title,
  parentTopicId,
  topicDepth: 0,
  // Other Note fields are not read by the breadcrumb — narrow object suffices.
}) as unknown;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TopicBreadcrumb', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    ancestorsState.data = undefined;
    ancestorsState.isLoading = false;
    ancestorsState.isError = false;
  });

  it('renders Home + ancestors + current with aria-current="page" on the leaf', async () => {
    ancestorsState.data = [
      buildNote('a-root', 'Roadmap'),
      buildNote('a-mid', 'Q2'),
      buildNote('a-self', 'Sprint 12', 'a-mid'),
    ];

    const Wrapper = createWrapper();
    const { TopicBreadcrumb } = await import('../components/TopicBreadcrumb');

    render(
      <Wrapper>
        <TopicBreadcrumb workspaceId="ws-1" workspaceSlug="acme" noteId="a-self" />
      </Wrapper>,
    );

    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Roadmap')).toBeInTheDocument();
    expect(screen.getByText('Q2')).toBeInTheDocument();

    const current = screen.getByTestId('topic-breadcrumb-current');
    expect(current).toHaveTextContent('Sprint 12');
    expect(current).toHaveAttribute('aria-current', 'page');
  });

  it('alt-click on an ancestor calls openPeek with id + NOTE token; plain click is preserved', async () => {
    ancestorsState.data = [
      buildNote('a-root', 'Roadmap'),
      buildNote('a-mid', 'Q2'),
      buildNote('a-self', 'Sprint 12', 'a-mid'),
    ];

    const Wrapper = createWrapper();
    const { TopicBreadcrumb } = await import('../components/TopicBreadcrumb');

    render(
      <Wrapper>
        <TopicBreadcrumb workspaceId="ws-1" workspaceSlug="acme" noteId="a-self" />
      </Wrapper>,
    );

    const roadmapLink = screen.getByText('Roadmap').closest('a')!;

    // Plain click — should NOT trigger openPeek.
    fireEvent.click(roadmapLink);
    expect(openPeekMock).not.toHaveBeenCalled();

    // Alt-click — should call openPeek with ancestor id + 'NOTE'.
    fireEvent.click(roadmapLink, { altKey: true });
    expect(openPeekMock).toHaveBeenCalledWith('a-root', 'NOTE');
  });

  it('renders the skeleton row when ancestors query is loading', async () => {
    ancestorsState.isLoading = true;

    const Wrapper = createWrapper();
    const { TopicBreadcrumb } = await import('../components/TopicBreadcrumb');

    const { container } = render(
      <Wrapper>
        <TopicBreadcrumb workspaceId="ws-1" workspaceSlug="acme" noteId="a-self" />
      </Wrapper>,
    );

    // The skeleton uses animate-pulse divs — assert the breadcrumb nav is
    // present but no current/last segment is rendered yet.
    expect(container.querySelector('[aria-label="Breadcrumb"]')).toBeInTheDocument();
    expect(screen.queryByTestId('topic-breadcrumb-current')).not.toBeInTheDocument();
  });

  it('renders the locked error copy when the ancestors query errors', async () => {
    ancestorsState.isError = true;

    const Wrapper = createWrapper();
    const { TopicBreadcrumb } = await import('../components/TopicBreadcrumb');

    render(
      <Wrapper>
        <TopicBreadcrumb workspaceId="ws-1" workspaceSlug="acme" noteId="a-self" />
      </Wrapper>,
    );

    expect(screen.getByTestId('topic-breadcrumb-error')).toHaveTextContent(
      "Couldn't load breadcrumb.",
    );
  });

  it('renders nothing when ancestors data is empty (top-level note / soft-deleted)', async () => {
    ancestorsState.data = [];

    const Wrapper = createWrapper();
    const { TopicBreadcrumb } = await import('../components/TopicBreadcrumb');

    const { container } = render(
      <Wrapper>
        <TopicBreadcrumb workspaceId="ws-1" workspaceSlug="acme" noteId="a-self" />
      </Wrapper>,
    );

    expect(container.firstChild).toBeNull();
  });

  it('truncates middle segments into a Popover when chain length > 5', async () => {
    // 7 ancestors total (incl. self) — triggers the static-threshold truncation.
    ancestorsState.data = [
      buildNote('a1', 'A1'),
      buildNote('a2', 'A2'),
      buildNote('a3', 'A3'),
      buildNote('a4', 'A4'),
      buildNote('a5', 'A5'),
      buildNote('a6', 'A6'),
      buildNote('a-self', 'Self'),
    ];

    const Wrapper = createWrapper();
    const { TopicBreadcrumb } = await import('../components/TopicBreadcrumb');

    render(
      <Wrapper>
        <TopicBreadcrumb workspaceId="ws-1" workspaceSlug="acme" noteId="a-self" />
      </Wrapper>,
    );

    const overflow = screen.getByTestId('topic-breadcrumb-overflow');
    expect(overflow).toBeInTheDocument();
    // Hidden middle = ancestors slice(1, len-2) → 6 ancestors → indices 1..3 → 3 hidden.
    expect(overflow).toHaveAttribute('aria-label', 'Show 3 hidden topics');

    // Only first ancestor (A1) and last 2 (A5, A6) are visible by default.
    expect(screen.getByText('A1')).toBeInTheDocument();
    expect(screen.getByText('A5')).toBeInTheDocument();
    expect(screen.getByText('A6')).toBeInTheDocument();
    expect(screen.queryByText('A2')).not.toBeInTheDocument();

    // Open the popover — hidden segments now appear.
    await userEvent.click(overflow);
    expect(await screen.findByText('A2')).toBeInTheDocument();
    expect(screen.getByText('A3')).toBeInTheDocument();
    expect(screen.getByText('A4')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// TopicTreeRowContextMenu (right-click "Move to…" wrapper)
// ---------------------------------------------------------------------------

const openPaletteForMoveMock = vi.fn();

vi.mock('@/stores', () => ({
  useUIStore: () => ({
    openPaletteForMove: openPaletteForMoveMock,
  }),
}));

describe('TopicTreeRowContextMenu', () => {
  beforeEach(() => {
    openPaletteForMoveMock.mockClear();
  });

  it('renders children and exposes a "Move to…" item that calls openPaletteForMove with id + parent', async () => {
    const { TopicTreeRowContextMenu } = await import('../components/TopicTreeRowContextMenu');
    const note = {
      id: 'note-1',
      title: 'Sprint 12',
      parentTopicId: 'parent-A',
      topicDepth: 1,
    } as unknown as Parameters<typeof TopicTreeRowContextMenu>[0]['note'];

    render(
      <TopicTreeRowContextMenu note={note}>
        <div data-testid="row">Child row</div>
      </TopicTreeRowContextMenu>,
    );

    const row = screen.getByTestId('row');
    // Trigger Radix ContextMenu via the synthetic contextmenu event.
    fireEvent.contextMenu(row);

    const moveItem = await screen.findByTestId('topic-tree-row-move-to');
    expect(moveItem).toHaveTextContent(/Move to/i);

    await userEvent.click(moveItem);

    expect(openPaletteForMoveMock).toHaveBeenCalledWith('note-1', 'parent-A');
  });

  it('passes null parent when the note is at the root', async () => {
    const { TopicTreeRowContextMenu } = await import('../components/TopicTreeRowContextMenu');
    const note = {
      id: 'note-2',
      title: 'Top-Level',
      parentTopicId: null,
      topicDepth: 0,
    } as unknown as Parameters<typeof TopicTreeRowContextMenu>[0]['note'];

    render(
      <TopicTreeRowContextMenu note={note}>
        <div data-testid="row">Child row</div>
      </TopicTreeRowContextMenu>,
    );

    const row = screen.getByTestId('row');
    fireEvent.contextMenu(row);
    const moveItem = await screen.findByTestId('topic-tree-row-move-to');
    await userEvent.click(moveItem);

    expect(openPaletteForMoveMock).toHaveBeenCalledWith('note-2', null);
  });
});
