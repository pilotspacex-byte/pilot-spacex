/**
 * PptxAnnotationPanel tests -- ANNOT-PANEL
 *
 * Tests annotation panel rendering including:
 * - New annotation textarea with aria-label
 * - Empty state message
 * - Add button disabled when textarea empty
 * - Annotation card rendering with content
 * - Collapsed badge with annotation count
 * - Owner-only edit/delete buttons
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// --- Mock use-slide-annotations hooks ---
const mockMutate = vi.fn();
const mockCreateMutation = { mutate: mockMutate, isPending: false };
const mockUpdateMutation = { mutate: vi.fn(), isPending: false };
const mockDeleteMutation = { mutate: vi.fn(), isPending: false };

let mockAnnotations: import('@/services/api/artifact-annotations').ArtifactAnnotation[] = [];
let mockIsLoading = false;
let mockIsError = false;

vi.mock('../../hooks/use-slide-annotations', () => ({
  useSlideAnnotations: () => ({
    data: mockAnnotations,
    isLoading: mockIsLoading,
    isError: mockIsError,
  }),
  useCreateAnnotation: () => mockCreateMutation,
  useUpdateAnnotation: () => mockUpdateMutation,
  useDeleteAnnotation: () => mockDeleteMutation,
  annotationKeys: {
    all: ['artifact-annotations'] as const,
    workspace: (wid: string, pid: string) => ['artifact-annotations', wid, pid] as const,
    artifact: (wid: string, pid: string, aid: string) =>
      ['artifact-annotations', wid, pid, aid] as const,
    slide: (wid: string, pid: string, aid: string, si: number) =>
      ['artifact-annotations', wid, pid, aid, si] as const,
  },
}));

import { PptxAnnotationPanel } from '../PptxAnnotationPanel';

function renderPanel(overrides: Partial<Parameters<typeof PptxAnnotationPanel>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const props = {
    workspaceId: 'ws-1',
    projectId: 'proj-1',
    artifactId: 'art-1',
    currentSlide: 0,
    currentUserId: 'user-1',
    ...overrides,
  };

  return render(
    <QueryClientProvider client={queryClient}>
      <PptxAnnotationPanel {...props} />
    </QueryClientProvider>
  );
}

describe('PptxAnnotationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAnnotations = [];
    mockIsLoading = false;
    mockIsError = false;
  });

  it('renders collapsed state with annotation toggle button', () => {
    renderPanel();

    // Panel starts collapsed — should show toggle button
    expect(screen.getByLabelText('Open annotation panel')).toBeDefined();
  });

  it('shows collapsed badge with count when annotations exist', () => {
    mockAnnotations = [
      {
        id: 'ann-1',
        artifactId: 'art-1',
        slideIndex: 0,
        content: 'First note',
        userId: 'user-1',
        workspaceId: 'ws-1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      {
        id: 'ann-2',
        artifactId: 'art-1',
        slideIndex: 0,
        content: 'Second note',
        userId: 'user-2',
        workspaceId: 'ws-1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    renderPanel();

    // Badge should display count
    expect(screen.getByText('2')).toBeDefined();
  });

  it('shows 9+ cap for collapsed badge when more than 9 annotations', () => {
    mockAnnotations = Array.from({ length: 12 }, (_, i) => ({
      id: `ann-${i}`,
      artifactId: 'art-1',
      slideIndex: 0,
      content: `Note ${i}`,
      userId: 'user-1',
      workspaceId: 'ws-1',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }));

    renderPanel();

    expect(screen.getByText('9+')).toBeDefined();
  });

  it('renders annotation textarea when panel is expanded', async () => {
    const user = userEvent.setup();
    renderPanel();

    // Expand panel
    await user.click(screen.getByLabelText('Open annotation panel'));

    // Should show new annotation textarea
    expect(screen.getByLabelText('New annotation content')).toBeDefined();
  });

  it('shows empty state message when no annotations exist', async () => {
    const user = userEvent.setup();
    mockAnnotations = [];

    renderPanel();

    // Expand panel
    await user.click(screen.getByLabelText('Open annotation panel'));

    expect(screen.getByText('No annotations on this slide yet.')).toBeDefined();
  });

  it('Add button is disabled when textarea is empty', async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByLabelText('Open annotation panel'));

    const addButton = screen.getByRole('button', { name: /add/i });
    expect(addButton).toHaveProperty('disabled', true);
  });

  it('renders existing annotations with content text', async () => {
    const user = userEvent.setup();
    mockAnnotations = [
      {
        id: 'ann-1',
        artifactId: 'art-1',
        slideIndex: 0,
        content: 'This is a test annotation',
        userId: 'user-1',
        workspaceId: 'ws-1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    renderPanel();

    await user.click(screen.getByLabelText('Open annotation panel'));

    expect(screen.getByText('This is a test annotation')).toBeDefined();
  });

  it('shows edit and delete buttons for own annotations', async () => {
    const user = userEvent.setup();
    mockAnnotations = [
      {
        id: 'ann-1',
        artifactId: 'art-1',
        slideIndex: 0,
        content: 'My annotation',
        userId: 'user-1', // matches currentUserId
        workspaceId: 'ws-1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    renderPanel();

    await user.click(screen.getByLabelText('Open annotation panel'));

    expect(screen.getByLabelText('Edit annotation')).toBeDefined();
    expect(screen.getByLabelText('Delete annotation')).toBeDefined();
  });

  it('hides edit and delete buttons for other users annotations', async () => {
    const user = userEvent.setup();
    mockAnnotations = [
      {
        id: 'ann-1',
        artifactId: 'art-1',
        slideIndex: 0,
        content: 'Their annotation',
        userId: 'user-other', // does NOT match currentUserId
        workspaceId: 'ws-1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
    ];

    renderPanel();

    await user.click(screen.getByLabelText('Open annotation panel'));

    expect(screen.queryByLabelText('Edit annotation')).toBeNull();
    expect(screen.queryByLabelText('Delete annotation')).toBeNull();
  });

  it('shows "Adding..." text when create mutation is pending', async () => {
    const user = userEvent.setup();
    mockCreateMutation.isPending = true;

    renderPanel();

    await user.click(screen.getByLabelText('Open annotation panel'));

    expect(screen.getByText('Adding...')).toBeDefined();

    // Reset
    mockCreateMutation.isPending = false;
  });

  it('shows error state when query fails', async () => {
    const user = userEvent.setup();
    mockIsError = true;

    renderPanel();

    await user.click(screen.getByLabelText('Open annotation panel'));

    expect(screen.getByText(/Failed to load annotations/)).toBeDefined();
  });
});
