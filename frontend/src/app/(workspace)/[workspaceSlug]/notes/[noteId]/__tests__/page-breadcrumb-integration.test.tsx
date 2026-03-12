'use client';

/**
 * Integration tests for the note detail page breadcrumb wiring and content sanitization.
 *
 * Verifies:
 * - PageBreadcrumb renders with correct ancestors for project pages with parentId
 * - Root project pages show project name only in breadcrumb (no ancestor links)
 * - Personal pages (no projectId) show no PageBreadcrumb
 * - Content containing data-property-block is sanitized before reaching NoteCanvas
 * - Content without data-property-block passes through unchanged
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { PageTreeNode } from '@/lib/tree-utils';

// ---------------------------------------------------------------------------
// Mocks — must be declared before component imports
// ---------------------------------------------------------------------------

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ workspaceSlug: 'test-workspace', noteId: 'note-child' }),
}));

vi.mock('@/components/workspace-guard', () => ({
  useWorkspace: () => ({ workspace: { id: 'ws-123' } }),
}));

vi.mock('@/stores/RootStore', () => ({
  useNoteStore: () => ({ setCurrentNote: vi.fn() }),
  useWorkspaceStore: () => ({ currentWorkspace: { id: 'ws-123' } }),
}));

// Mock useNote
const mockUseNote = vi.fn();
vi.mock('@/features/notes/hooks/useNote', () => ({
  useNote: (...args: unknown[]) => mockUseNote(...args),
  useNoteAnnotations: () => ({ data: null }),
}));

// Mock useProjectPageTree
const mockUseProjectPageTree = vi.fn();
vi.mock('@/features/notes/hooks/useProjectPageTree', () => ({
  useProjectPageTree: (...args: unknown[]) => mockUseProjectPageTree(...args),
  projectTreeKeys: {
    all: ['notes', 'project-tree'],
    tree: (wsId: string, pId: string) => ['notes', 'project-tree', wsId, pId],
  },
}));

// Mock the entire hooks barrel to ensure our specific mocks take effect
vi.mock('@/features/notes/hooks', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/features/notes/hooks')>();
  return {
    ...original,
    useNote: (...args: unknown[]) => mockUseNote(...args),
    useProjectPageTree: (...args: unknown[]) => mockUseProjectPageTree(...args),
  };
});

// Mock useUpdateNote
vi.mock('@/features/notes/hooks/useUpdateNote', () => ({
  useUpdateNote: () => ({ mutate: vi.fn(), mutateAsync: vi.fn() }),
  useUpdateNoteContent: () => ({ mutate: vi.fn() }),
}));

// Mock useDeleteNote
vi.mock('@/features/notes/hooks/useDeleteNote', () => ({
  useDeleteNote: () => ({ mutate: vi.fn() }),
}));

// Mock useAutoSave
vi.mock('@/features/notes/hooks/useAutoSave', () => ({
  useAutoSave: () => ({ status: 'idle', save: vi.fn(), reset: vi.fn() }),
  getStatusIndicator: vi.fn(),
}));

vi.mock('@/hooks/useTogglePin', () => ({
  useTogglePin: () => ({ mutate: vi.fn() }),
}));

vi.mock('@/hooks/useNoteVersions', () => ({
  useNoteVersions: () => ({ data: [], isLoading: false }),
  useRestoreNoteVersion: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock('@/features/projects/hooks/useProjects', () => ({
  useProjects: () => ({ data: { items: [{ id: 'proj-123', name: 'My Project' }] } }),
  selectAllProjects: (data: { items: Array<{ id: string; name: string }> } | undefined) =>
    data?.items ?? [],
}));

// Capture NoteCanvas props for assertion
const mockNoteCanvasProps: Record<string, unknown>[] = [];
vi.mock('@/components/editor/NoteCanvas', () => ({
  NoteCanvas: (props: Record<string, unknown>) => {
    mockNoteCanvasProps.push(props);
    return <div data-testid="note-canvas" />;
  },
  NoteCanvasLayout: (props: Record<string, unknown>) => {
    mockNoteCanvasProps.push(props);
    return <div data-testid="note-canvas" />;
  },
}));

// Capture PageBreadcrumb props for assertion
const mockPageBreadcrumbProps: Record<string, unknown>[] = [];
vi.mock('@/components/editor/PageBreadcrumb', () => ({
  PageBreadcrumb: (props: Record<string, unknown>) => {
    mockPageBreadcrumbProps.push(props);
    return <nav data-testid="page-breadcrumb" aria-label="Breadcrumb" />;
  },
}));

vi.mock('@/components/editor/VersionHistoryPanel', () => ({
  VersionHistoryPanel: () => <div data-testid="version-history-panel" />,
}));

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function makeNote(overrides: Record<string, unknown> = {}) {
  return {
    id: 'note-child',
    title: 'Child Note',
    content: { type: 'doc', content: [{ type: 'paragraph' }] },
    projectId: 'proj-123',
    parentId: 'note-parent',
    depth: 1,
    position: 1000,
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

function makeTree(): PageTreeNode[] {
  return [
    {
      id: 'note-parent',
      title: 'Parent Note',
      parentId: null,
      depth: 0,
      position: 1000,
      children: [
        {
          id: 'note-child',
          title: 'Child Note',
          parentId: 'note-parent',
          depth: 1,
          position: 1000,
          children: [],
        },
      ],
    },
  ];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('NoteDetailPage — breadcrumb integration', () => {
  beforeEach(() => {
    mockNoteCanvasProps.length = 0;
    mockPageBreadcrumbProps.length = 0;
    vi.clearAllMocks();
  });

  it('Test 3: renders PageBreadcrumb with ancestor chain when note has projectId and parentId', async () => {
    mockUseNote.mockReturnValue({ data: makeNote(), isLoading: false, error: null });
    mockUseProjectPageTree.mockReturnValue({ data: makeTree() });

    const { default: NoteDetailPage } = await import('../page');
    render(<NoteDetailPage />);

    // PageBreadcrumb should be rendered
    expect(screen.getByTestId('page-breadcrumb')).toBeInTheDocument();

    // Should have been called with correct ancestors
    const breadcrumbCall = mockPageBreadcrumbProps[0];
    expect(breadcrumbCall).toBeDefined();
    const ancestors = breadcrumbCall!['ancestors'] as Array<{ id: string; title: string }>;
    expect(ancestors).toHaveLength(1);
    expect(ancestors[0]!.id).toBe('note-parent');
    expect(ancestors[0]!.title).toBe('Parent Note');
  });

  it('Test 4: renders PageBreadcrumb with project name only when note has projectId but no parentId', async () => {
    mockUseNote.mockReturnValue({
      data: makeNote({ parentId: null, depth: 0 }),
      isLoading: false,
      error: null,
    });
    mockUseProjectPageTree.mockReturnValue({
      data: [
        {
          id: 'note-child',
          title: 'Child Note',
          parentId: null,
          depth: 0,
          position: 1000,
          children: [],
        },
      ],
    });

    const { default: NoteDetailPage } = await import('../page');
    render(<NoteDetailPage />);

    // PageBreadcrumb should be rendered (project page)
    expect(screen.getByTestId('page-breadcrumb')).toBeInTheDocument();

    // Ancestors should be empty (root page)
    const breadcrumbCall = mockPageBreadcrumbProps[0];
    const ancestors = breadcrumbCall!['ancestors'] as Array<{ id: string; title: string }>;
    expect(ancestors).toHaveLength(0);
  });

  it('Test 5: renders NO PageBreadcrumb when note has no projectId (personal page)', async () => {
    mockUseNote.mockReturnValue({
      data: makeNote({ projectId: null, parentId: null }),
      isLoading: false,
      error: null,
    });
    mockUseProjectPageTree.mockReturnValue({ data: undefined });

    const { default: NoteDetailPage } = await import('../page');
    render(<NoteDetailPage />);

    // PageBreadcrumb should NOT be rendered
    expect(screen.queryByTestId('page-breadcrumb')).toBeNull();
  });

  it('Test 6: sanitizes content containing propertyBlock node before passing to NoteCanvas', async () => {
    const dirtyContent = {
      type: 'doc',
      content: [
        { type: 'propertyBlock', attrs: { 'data-property-block': 'true' }, content: [] },
        { type: 'paragraph', content: [{ type: 'text', text: 'Hello' }] },
      ],
    };
    mockUseNote.mockReturnValue({
      data: makeNote({ content: dirtyContent, projectId: null }),
      isLoading: false,
      error: null,
    });
    mockUseProjectPageTree.mockReturnValue({ data: undefined });

    const { default: NoteDetailPage } = await import('../page');
    render(<NoteDetailPage />);

    // NoteCanvas should receive sanitized content (no propertyBlock)
    const canvasCall = mockNoteCanvasProps[0];
    const content = canvasCall!['content'] as { type: string; content: Array<{ type: string }> };
    expect(content.content).toHaveLength(1);
    expect(content.content[0]!.type).toBe('paragraph');
  });

  it('Test 7: passes content unchanged when no propertyBlock present', async () => {
    const cleanContent = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Hello' }] }],
    };
    mockUseNote.mockReturnValue({
      data: makeNote({ content: cleanContent, projectId: null }),
      isLoading: false,
      error: null,
    });
    mockUseProjectPageTree.mockReturnValue({ data: undefined });

    const { default: NoteDetailPage } = await import('../page');
    render(<NoteDetailPage />);

    const canvasCall = mockNoteCanvasProps[0];
    const content = canvasCall!['content'] as { type: string; content: Array<{ type: string }> };
    expect(content.content).toHaveLength(1);
    expect(content.content[0]!.type).toBe('paragraph');
  });
});
