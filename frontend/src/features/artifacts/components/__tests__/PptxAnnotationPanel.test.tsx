/**
 * PptxAnnotationPanel tests -- ANNOT-PANEL
 *
 * Mocks usePptxAnnotations hook to isolate component behavior.
 * Tests: empty state, annotation list, owner controls, create, Cmd+Enter, collapsed badge, delete.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { AnnotationResponse } from '@/services/api/artifact-annotations';
import PptxAnnotationPanel from '../PptxAnnotationPanel';

// ---- Mock usePptxAnnotations ----
const mockCreateMutate = vi.fn();
const mockUpdateMutate = vi.fn();
const mockDeleteMutate = vi.fn();

const defaultHookReturn = {
  annotations: [] as AnnotationResponse[],
  total: 0,
  isLoading: false,
  createAnnotation: { mutate: mockCreateMutate, isPending: false, variables: undefined },
  updateAnnotation: { mutate: mockUpdateMutate, isPending: false, variables: undefined },
  deleteAnnotation: {
    mutate: mockDeleteMutate,
    isPending: false,
    variables: undefined as { annotationId: string } | undefined,
  },
};

let hookReturn: typeof defaultHookReturn = { ...defaultHookReturn };

vi.mock('../../hooks/usePptxAnnotations', () => ({
  usePptxAnnotations: vi.fn(() => hookReturn),
}));

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

const baseProps = {
  workspaceId: 'ws-1',
  projectId: 'proj-1',
  artifactId: 'art-1',
  slideIndex: 0,
  currentUserId: 'user-1',
  isCollapsed: false,
  onToggleCollapse: vi.fn(),
};

function renderPanel(overrides: Partial<typeof baseProps> = {}) {
  const client = makeClient();
  return render(
    <QueryClientProvider client={client}>
      <PptxAnnotationPanel {...baseProps} {...overrides} />
    </QueryClientProvider>
  );
}

describe('PptxAnnotationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hookReturn = { ...defaultHookReturn };
  });

  // 1. Empty state
  it('renders empty state when no annotations', () => {
    renderPanel();
    expect(screen.getByText('No annotations on this slide yet.')).toBeDefined();
  });

  // 2. Annotation list with correct content
  it('renders annotation list with correct content', () => {
    hookReturn = {
      ...defaultHookReturn,
      annotations: [
        {
          id: 'ann-1',
          artifact_id: 'art-1',
          slide_index: 0,
          content: 'First annotation',
          user_id: 'user-1',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: 'ann-2',
          artifact_id: 'art-1',
          slide_index: 0,
          content: 'Second annotation',
          user_id: 'user-2',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 2,
    };
    renderPanel();
    expect(screen.getByText('First annotation')).toBeDefined();
    expect(screen.getByText('Second annotation')).toBeDefined();
  });

  // 3. Owner-only edit/delete buttons
  it('shows edit/delete buttons only for current user annotations', () => {
    hookReturn = {
      ...defaultHookReturn,
      annotations: [
        {
          id: 'ann-1',
          artifact_id: 'art-1',
          slide_index: 0,
          content: 'My annotation',
          user_id: 'user-1',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: 'ann-2',
          artifact_id: 'art-1',
          slide_index: 0,
          content: 'Other annotation',
          user_id: 'user-2',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 2,
    };
    renderPanel();
    // There should be exactly one Edit and one Delete button (for user-1's annotation only)
    const editButtons = screen.getAllByRole('button', { name: /edit annotation/i });
    const deleteButtons = screen.getAllByRole('button', { name: /delete annotation/i });
    expect(editButtons).toHaveLength(1);
    expect(deleteButtons).toHaveLength(1);
  });

  // 4. Create form submits on button click
  it('submits annotation on Add Note button click', () => {
    renderPanel();
    const textarea = screen.getByLabelText('Add annotation');
    fireEvent.change(textarea, { target: { value: 'New note' } });
    const addButton = screen.getByRole('button', { name: /add note/i });
    fireEvent.click(addButton);
    expect(mockCreateMutate).toHaveBeenCalledWith({ content: 'New note' });
  });

  // 5. Create form submits on Cmd+Enter
  it('submits annotation on Cmd+Enter', () => {
    renderPanel();
    const textarea = screen.getByLabelText('Add annotation');
    fireEvent.change(textarea, { target: { value: 'Keyboard note' } });
    fireEvent.keyDown(textarea, { key: 'Enter', metaKey: true });
    expect(mockCreateMutate).toHaveBeenCalledWith({ content: 'Keyboard note' });
  });

  // 6. Collapsed state shows badge with count
  it('shows badge with annotation count when collapsed', () => {
    hookReturn = { ...defaultHookReturn, total: 5 };
    renderPanel({ isCollapsed: true });
    expect(screen.getByText('5')).toBeDefined();
  });

  // 7. Collapsed badge caps at 9+
  it('caps badge at 9+ for large counts', () => {
    hookReturn = { ...defaultHookReturn, total: 15 };
    renderPanel({ isCollapsed: true });
    expect(screen.getByText('9+')).toBeDefined();
  });

  // 8. Delete calls deleteAnnotation mutation
  it('calls deleteAnnotation on trash button click', () => {
    hookReturn = {
      ...defaultHookReturn,
      annotations: [
        {
          id: 'ann-1',
          artifact_id: 'art-1',
          slide_index: 0,
          content: 'To delete',
          user_id: 'user-1',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
    };
    renderPanel();
    const deleteButton = screen.getByRole('button', { name: /delete annotation/i });
    fireEvent.click(deleteButton);
    expect(mockDeleteMutate).toHaveBeenCalledWith({ annotationId: 'ann-1' });
  });

  // 9. Add Note button disabled when textarea empty
  it('disables Add Note button when textarea is empty', () => {
    renderPanel();
    const addButton = screen.getByRole('button', { name: /add note/i });
    expect(addButton).toHaveProperty('disabled', true);
  });

  // 10. Shows Cmd+Enter hint only when textarea has content
  it('shows Cmd+Enter hint only when textarea has content', () => {
    renderPanel();
    expect(screen.queryByText('Cmd+Enter to submit')).toBeNull();
    const textarea = screen.getByLabelText('Add annotation');
    fireEvent.change(textarea, { target: { value: 'some text' } });
    expect(screen.getByText('Cmd+Enter to submit')).toBeDefined();
  });

  // 11. Collapsed strip toggle calls onToggleCollapse
  it('calls onToggleCollapse when collapsed strip is clicked', () => {
    const onToggleCollapse = vi.fn();
    renderPanel({ isCollapsed: true, onToggleCollapse });
    const button = screen.getByRole('button', { name: /annotations/i });
    fireEvent.click(button);
    expect(onToggleCollapse).toHaveBeenCalledOnce();
  });
});
