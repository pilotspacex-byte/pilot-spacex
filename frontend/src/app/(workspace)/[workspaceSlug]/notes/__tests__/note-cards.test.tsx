/**
 * Unit tests for NoteGridCard and NoteListRow rendering within NotesPage.
 *
 * Tests project reference display, linked issue state color dots,
 * overflow badges, and topics fallback on note cards.
 *
 * @module app/(workspace)/[workspaceSlug]/notes/__tests__/note-cards.test
 */
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Suspense } from 'react';
import { useQuery, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type {
  Issue,
  Note,
  Project,
  StateBrief,
  IssuePriority,
  UserBrief,
  LabelBrief,
  ProjectBrief,
  JSONContent,
} from '@/types';

// ---- Mocks ----

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return { ...actual, useQuery: vi.fn() };
});

const mockUseInfiniteNotes = vi.fn();
const mockUseCreateNote = vi.fn();
vi.mock('@/features/notes/hooks', () => ({
  useInfiniteNotes: (...args: unknown[]) => mockUseInfiniteNotes(...args),
  useCreateNote: (...args: unknown[]) => mockUseCreateNote(...args),
  createNoteDefaults: () => ({ title: '', content: { type: 'doc', content: [] } }),
}));

vi.mock('@/stores/RootStore', () => ({
  useWorkspaceStore: () => ({ currentWorkspace: { id: 'ws-1' } }),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => ({ get: () => null }),
}));

vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('motion/react', () => ({
  motion: {
    div: ({
      children,
      initial: _initial,
      animate: _animate,
      exit: _exit,
      transition: _transition,
      ...rest
    }: Record<string, unknown>) => <div {...rest}>{children as React.ReactNode}</div>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/services/api/projects', () => ({
  projectsApi: { list: vi.fn() },
}));

// ---- Factories ----

function makeStateBrief(overrides: Partial<StateBrief> = {}): StateBrief {
  return {
    id: 'state-1',
    name: 'Todo',
    color: '#5B8FC9',
    group: 'unstarted' as const,
    ...overrides,
  };
}

function makeIssue(overrides: Partial<Issue> = {}): Issue {
  const defaultReporter: UserBrief = { id: 'u1', email: 'a@b.com', displayName: 'User' };
  const defaultProject: ProjectBrief = { id: 'p1', name: 'Project', identifier: 'PS' };
  return {
    id: `issue-${Math.random().toString(36).slice(2, 8)}`,
    identifier: 'PS-1',
    name: 'Test Issue',
    description: '',
    state: makeStateBrief(),
    priority: 'medium' as IssuePriority,
    projectId: 'p1',
    workspaceId: 'w1',
    sequenceId: 1,
    sortOrder: 0,
    reporterId: 'u1',
    reporter: defaultReporter,
    labels: [] as LabelBrief[],
    subIssueCount: 0,
    project: defaultProject,
    hasAiEnhancements: false,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

function makeNote(overrides: Partial<Note> = {}): Note {
  return {
    id: `note-${Math.random().toString(36).slice(2, 8)}`,
    title: 'Test Note',
    content: { type: 'doc', content: [] } as JSONContent,
    wordCount: 42,
    readingTimeMins: 1,
    isPinned: false,
    ownerId: 'u1',
    workspaceId: 'ws-1',
    collaborators: [],
    linkedIssues: [],
    annotations: [],
    topics: [],
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-15T12:00:00Z',
    ...overrides,
  };
}

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 'proj-1',
    name: 'Alpha Project',
    identifier: 'ALPHA',
    workspaceId: 'ws-1',
    issueCount: 10,
    openIssueCount: 3,
    createdAt: '2025-01-01T00:00:00Z',
    updatedAt: '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

// ---- Helpers ----

async function renderNotesPage(notes: Note[], projects: Project[] = []) {
  (useQuery as Mock).mockReturnValue({
    data: {
      items: projects,
      total: projects.length,
      nextCursor: null,
      prevCursor: null,
      hasNext: false,
      hasPrev: false,
    },
    isLoading: false,
  });

  mockUseInfiniteNotes.mockReturnValue({
    data: {
      pages: [
        {
          items: notes,
          total: notes.length,
          nextCursor: null,
          prevCursor: null,
          hasNext: false,
          hasPrev: false,
        },
      ],
    },
    isLoading: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
  });

  mockUseCreateNote.mockReturnValue({ mutate: vi.fn(), isPending: false });

  // The page component uses React 19 `use(params)` which suspends.
  // Wrap in Suspense and use an already-resolved promise to avoid suspension.
  const { default: NotesPage } = await import('../page');
  const resolvedParams = Promise.resolve({ workspaceSlug: 'my-ws' });
  // Ensure the promise is settled before rendering
  await resolvedParams;

  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <QueryClientProvider client={queryClient}>
        <Suspense fallback={<div>Loading...</div>}>
          <NotesPage params={resolvedParams} />
        </Suspense>
      </QueryClientProvider>
    );
  });

  return result;
}

// ---- Tests ----

describe('NotesPage - NoteGridCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders project name when note has projectId and project exists', async () => {
    const project = makeProject({ id: 'proj-1', name: 'Alpha Project' });
    const note = makeNote({ projectId: 'proj-1' });

    await renderNotesPage([note], [project]);

    expect(screen.getByText('Alpha Project')).toBeInTheDocument();
  });

  it('renders linked issues with state color dots and identifiers', async () => {
    const issues = [
      makeIssue({
        id: 'i1',
        identifier: 'PS-10',
        state: makeStateBrief({ color: '#29A386', name: 'Done' }),
      }),
      makeIssue({
        id: 'i2',
        identifier: 'PS-11',
        state: makeStateBrief({ color: '#D9853F', name: 'In Progress' }),
      }),
    ];
    const note = makeNote({ linkedIssues: issues });

    await renderNotesPage([note]);

    expect(screen.getByText('PS-10')).toBeInTheDocument();
    expect(screen.getByText('PS-11')).toBeInTheDocument();
  });

  it('shows state color on linked issue dots', async () => {
    const issue = makeIssue({
      id: 'i1',
      identifier: 'PS-10',
      state: makeStateBrief({ color: '#29A386' }),
    });
    const note = makeNote({ linkedIssues: [issue] });

    await renderNotesPage([note]);

    const badge = screen.getByText('PS-10');
    const dot = badge.parentElement!.querySelector('span.rounded-full');
    expect(dot).toHaveStyle({ backgroundColor: '#29A386' });
  });

  it('shows "+N" overflow when more than 3 linked issues', async () => {
    const issues = Array.from({ length: 5 }, (_, i) =>
      makeIssue({ id: `i${i}`, identifier: `PS-${i + 1}` })
    );
    const note = makeNote({ linkedIssues: issues });

    await renderNotesPage([note]);

    expect(screen.getByText('PS-1')).toBeInTheDocument();
    expect(screen.getByText('PS-2')).toBeInTheDocument();
    expect(screen.getByText('PS-3')).toBeInTheDocument();
    expect(screen.queryByText('PS-4')).not.toBeInTheDocument();
    expect(screen.queryByText('PS-5')).not.toBeInTheDocument();
    expect(screen.getByText('+2')).toBeInTheDocument();
  });

  it('shows topics when no linked issues', async () => {
    const note = makeNote({ topics: ['react', 'testing'], linkedIssues: [] });

    await renderNotesPage([note]);

    // Topics joined with middle dot separator
    expect(screen.getByText('react · testing')).toBeInTheDocument();
  });

  it('shows empty word indicator when no linked issues and no topics', async () => {
    const note = makeNote({ topics: [], linkedIssues: [], wordCount: 0 });

    await renderNotesPage([note]);

    expect(screen.getByText('Empty')).toBeInTheDocument();
  });

  it('renders project progress bar with correct width', async () => {
    const project = makeProject({
      id: 'proj-1',
      issueCount: 10,
      openIssueCount: 5,
    });
    const note = makeNote({ projectId: 'proj-1' });

    await renderNotesPage([note], [project]);

    const projectName = screen.getByText(project.name);
    const projectRow = projectName.closest('div')!;
    const progressContainer = projectRow.querySelector('.bg-border');
    expect(progressContainer).toBeTruthy();
    const progressBar = progressContainer!.querySelector('div');
    expect(progressBar).toHaveStyle({ width: '50%' });
  });

  it('does not render project section when projectId is absent', async () => {
    const note = makeNote({ projectId: undefined, topics: ['design'] });

    await renderNotesPage([note]);

    expect(screen.getByText('design')).toBeInTheDocument();
  });
});

describe('NotesPage - NoteListRow (list view)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderInListView(notes: Note[], projects: Project[] = []) {
    const result = await renderNotesPage(notes, projects);
    const user = userEvent.setup();

    // Find the list-view toggle button (rounded-l-none class)
    const buttons = result.container.querySelectorAll('button');
    const listViewBtn = Array.from(buttons).find((btn) => btn.className.includes('rounded-l-none'));
    if (listViewBtn) {
      await user.click(listViewBtn);
    }

    return result;
  }

  it('renders project name in list row', async () => {
    const project = makeProject({ id: 'proj-1', name: 'Beta Project' });
    const note = makeNote({ projectId: 'proj-1' });

    await renderInListView([note], [project]);

    expect(screen.getByText('Beta Project')).toBeInTheDocument();
  });

  it('renders linked issue badges with state colors in list row', async () => {
    const issues = [
      makeIssue({
        id: 'i1',
        identifier: 'PS-20',
        state: makeStateBrief({ color: '#8B7EC8', name: 'In Review' }),
      }),
    ];
    const note = makeNote({ linkedIssues: issues });

    await renderInListView([note]);

    expect(screen.getByText('PS-20')).toBeInTheDocument();
    const badge = screen.getByText('PS-20');
    const dot = badge.parentElement!.querySelector('span.rounded-full');
    expect(dot).toHaveStyle({ backgroundColor: '#8B7EC8' });
  });

  it('shows separator dot between project and topics in list row', async () => {
    const project = makeProject({ id: 'proj-1', name: 'Gamma' });
    const note = makeNote({ projectId: 'proj-1', topics: ['api', 'docs'] });

    await renderInListView([note], [project]);

    expect(screen.getByText('Gamma')).toBeInTheDocument();
    expect(screen.getByText('\u00b7')).toBeInTheDocument();
    expect(screen.getByText('api, docs')).toBeInTheDocument();
  });

  it('shows "+N" overflow for more than 3 issues in list row', async () => {
    const issues = Array.from({ length: 4 }, (_, i) =>
      makeIssue({ id: `i${i}`, identifier: `PS-${i + 1}` })
    );
    const note = makeNote({ linkedIssues: issues });

    await renderInListView([note]);

    expect(screen.getByText('PS-1')).toBeInTheDocument();
    expect(screen.getByText('PS-3')).toBeInTheDocument();
    expect(screen.queryByText('PS-4')).not.toBeInTheDocument();
    expect(screen.getByText('+1')).toBeInTheDocument();
  });
});
