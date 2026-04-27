'use client';

/**
 * Issue #144 regression guard — TopicBreadcrumb suppression on project topics.
 *
 * The topic detail page (also serving /topics/[topicId] via re-export) renders
 * <TopicBreadcrumb /> above NoteCanvas. NoteCanvasLayout in turn renders
 * <ProjectContextHeader /> when the note has a projectId — which already
 * provides project name + tabs. Rendering both produced two stacked
 * horizontal bands above the editor.
 *
 * Fix: suppress <TopicBreadcrumb /> at the page level when `note.projectId`
 * is set. Personal / top-level topics (no projectId) keep the breadcrumb.
 *
 * This test renders only the page module with the relevant hooks mocked and
 * asserts the breadcrumb mock receives or doesn't receive a render call.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mocks — declared before the page import.
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ workspaceSlug: 'acme', noteId: 'note-1' }),
}));

vi.mock('@/components/workspace-guard', () => ({
  useWorkspace: () => ({ workspace: { id: 'ws-1' } }),
}));

vi.mock('@/stores/RootStore', () => ({
  useNoteStore: () => ({ setCurrentNote: vi.fn() }),
  useUIStore: () => ({ isFocusMode: false }),
  useWorkspaceStore: () => ({ currentWorkspace: { id: 'ws-1' } }),
}));

const mockUseNote = vi.fn();
vi.mock('@/features/notes/hooks', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/notes/hooks')>();
  return {
    ...actual,
    useNote: (...args: unknown[]) => mockUseNote(...args),
    useUpdateNote: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
    useAutoSave: () => ({ status: 'idle', save: vi.fn(), reset: vi.fn() }),
  };
});

vi.mock('@/features/notes/hooks/useDeleteNote', () => ({
  useDeleteNote: () => ({ mutate: vi.fn() }),
}));

vi.mock('@/hooks/useTogglePin', () => ({
  useTogglePin: () => ({ mutate: vi.fn() }),
}));

vi.mock('@/hooks/useNoteVersions', () => ({
  useNoteVersions: () => ({ data: [], isLoading: false }),
  useRestoreNoteVersion: () => ({ mutateAsync: vi.fn() }),
}));

// Capture TopicBreadcrumb render calls.
const topicBreadcrumbRenders: Record<string, unknown>[] = [];
vi.mock('@/features/topics/components', () => ({
  TopicBreadcrumb: (props: Record<string, unknown>) => {
    topicBreadcrumbRenders.push(props);
    return <nav data-testid="topic-breadcrumb-mock" />;
  },
}));

vi.mock('@/components/editor/NoteCanvas', () => ({
  NoteCanvas: () => <div data-testid="note-canvas-mock" />,
  NoteCanvasLayout: () => <div data-testid="note-canvas-mock" />,
}));

vi.mock('@/features/artifacts/components/EditorFilePreview', () => ({
  EditorFilePreview: () => null,
}));

vi.mock('@/features/notes/editor/extensions/file-card/inline-preview', () => ({
  FilePreviewConfigContext: {
    Provider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  },
}));

vi.mock('@/components/editor/VersionHistoryPanel', () => ({
  VersionHistoryPanel: () => null,
}));

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

vi.mock('@/services/api', () => ({
  notesApi: { moveNote: vi.fn() },
}));

// ---------------------------------------------------------------------------

function makeNote(overrides: Record<string, unknown> = {}) {
  return {
    id: 'note-1',
    title: 'Auth Refactor',
    content: { type: 'doc', content: [{ type: 'paragraph' }] },
    projectId: null,
    isPinned: false,
    isAIAssisted: false,
    owner: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    wordCount: 10,
    topics: [],
    linkedIssues: [],
    ...overrides,
  };
}

describe('NoteDetailPage — TopicBreadcrumb suppression (#144)', () => {
  beforeEach(() => {
    topicBreadcrumbRenders.length = 0;
    vi.clearAllMocks();
  });

  it('renders <TopicBreadcrumb /> when the note has NO projectId (personal / top-level)', async () => {
    mockUseNote.mockReturnValue({
      data: makeNote({ projectId: null }),
      isLoading: false,
      error: null,
    });

    const { default: NoteDetailPage } = await import('../page');
    render(<NoteDetailPage />);

    expect(topicBreadcrumbRenders.length).toBeGreaterThanOrEqual(1);
  });

  it('SUPPRESSES <TopicBreadcrumb /> when the note has a projectId (#144 stacked headers)', async () => {
    mockUseNote.mockReturnValue({
      data: makeNote({ projectId: 'proj-auth' }),
      isLoading: false,
      error: null,
    });

    const { default: NoteDetailPage } = await import('../page');
    render(<NoteDetailPage />);

    // ProjectContextHeader (rendered by NoteCanvasLayout, mocked away here)
    // already provides the "where am I" surface for project topics. The
    // breadcrumb must NOT also render — that produced two stacked bands.
    expect(topicBreadcrumbRenders).toHaveLength(0);
  });
});
