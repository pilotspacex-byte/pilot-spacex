import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BacklinksPanel } from '../BacklinksPanel';
import { notesApi } from '@/services/api/notes';
import type { NoteBacklink } from '@/types';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
}));

// Mock notes API
vi.mock('@/services/api/notes', () => ({
  notesApi: {
    getNoteBacklinks: vi.fn(),
  },
}));

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockBacklinks: NoteBacklink[] = [
  {
    id: 'link-1',
    sourceNoteId: 'source-1',
    targetNoteId: 'target-1',
    linkType: 'inline' as const,
    workspaceId: 'ws-1',
    sourceNoteTitle: 'API Design Notes',
  },
  {
    id: 'link-2',
    sourceNoteId: 'source-2',
    targetNoteId: 'target-1',
    linkType: 'embed' as const,
    workspaceId: 'ws-1',
    sourceNoteTitle: 'Architecture Overview',
  },
];

describe('BacklinksPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    vi.mocked(notesApi.getNoteBacklinks).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    expect(screen.getByText('Loading backlinks...')).toBeInTheDocument();
  });

  it('shows empty state when no backlinks', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue([]);
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    expect(await screen.findByText('No notes link to this note yet.')).toBeInTheDocument();
  });

  it('renders backlink list with titles', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue(mockBacklinks);
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    expect(await screen.findByText('API Design Notes')).toBeInTheDocument();
    expect(screen.getByText('Architecture Overview')).toBeInTheDocument();
  });

  it('shows count header', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue(mockBacklinks);
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    expect(await screen.findByText('2 notes link to this note')).toBeInTheDocument();
  });

  it('shows singular count for single backlink', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue([mockBacklinks[0]!]);
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    expect(await screen.findByText('1 note links to this note')).toBeInTheDocument();
  });

  it('navigates to source note on click', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue(mockBacklinks);
    const user = userEvent.setup();
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    const firstItem = await screen.findByText('API Design Notes');
    await user.click(firstItem.closest('button')!);
    expect(mockPush).toHaveBeenCalledWith('/test-workspace/notes/source-1');
  });

  it('shows "Untitled" for backlinks without title', async () => {
    const untitledBacklink: NoteBacklink = {
      id: 'link-3',
      sourceNoteId: 'source-3',
      targetNoteId: 'target-1',
      linkType: 'inline' as const,
      workspaceId: 'ws-1',
    };
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue([untitledBacklink]);
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    expect(await screen.findByText('Untitled')).toBeInTheDocument();
  });

  it('shows link type as subtitle', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue(mockBacklinks);
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    await screen.findByText('API Design Notes');
    expect(screen.getByText('Inline link')).toBeInTheDocument();
    expect(screen.getByText('Embedded')).toBeInTheDocument();
  });

  it('shows error state on API failure', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockRejectedValue(new Error('fail'));
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    expect(await screen.findByText('Failed to load backlinks.')).toBeInTheDocument();
  });

  it('has correct ARIA attributes', async () => {
    vi.mocked(notesApi.getNoteBacklinks).mockResolvedValue(mockBacklinks);
    renderWithProviders(<BacklinksPanel workspaceId="ws-1" noteId="note-1" />);
    await screen.findByText('API Design Notes');
    expect(screen.getByRole('list', { name: 'Backlinks' })).toBeInTheDocument();
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(2);
  });

  it('does not fetch when workspaceId is empty', () => {
    renderWithProviders(<BacklinksPanel workspaceId="" noteId="note-1" />);
    expect(notesApi.getNoteBacklinks).not.toHaveBeenCalled();
  });
});
