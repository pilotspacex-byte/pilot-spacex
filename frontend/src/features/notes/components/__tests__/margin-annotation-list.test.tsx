/**
 * MarginAnnotationList Tests (T177)
 * Component tests for margin annotation list
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MarginAnnotationList } from '../margin-annotation-list';
import { RootStore, StoreContext } from '@/stores/RootStore';
import type { BlockPosition } from '@/components/editor/plugins/annotation-positioning';
import type { NoteAnnotation } from '@/types';

// Mock Supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi
        .fn()
        .mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
    },
  },
}));

describe('MarginAnnotationList', () => {
  const mockBlockPositions: BlockPosition[] = [
    { blockId: 'block-1', top: 0, height: 100 },
    { blockId: 'block-2', top: 120, height: 80 },
  ];

  const mockAnnotations: NoteAnnotation[] = [
    {
      id: 'ann-1',
      noteId: 'note-1',
      blockId: 'block-1',
      type: 'suggestion',
      content: 'Full content here with more details',
      confidence: 0.85,
      status: 'pending',
      aiMetadata: {
        title: 'Consider refactoring',
        summary: 'This section could be clearer',
      },
      createdAt: new Date().toISOString(),
    },
    {
      id: 'ann-2',
      noteId: 'note-1',
      blockId: 'block-2',
      type: 'warning',
      content: 'Full warning content',
      confidence: 0.92,
      status: 'pending',
      aiMetadata: {
        title: 'Potential issue',
        summary: 'Missing error handling',
      },
      createdAt: new Date().toISOString(),
    },
  ];

  let rootStore: RootStore;

  beforeEach(() => {
    rootStore = new RootStore();
  });

  function renderWithStore(ui: React.ReactElement) {
    return render(<StoreContext.Provider value={rootStore}>{ui}</StoreContext.Provider>);
  }

  it('should render annotations at correct positions', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', mockAnnotations);

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    expect(screen.getByText('Consider refactoring')).toBeInTheDocument();
    expect(screen.getByText('Potential issue')).toBeInTheDocument();
  });

  it('should show annotation type labels', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', mockAnnotations);

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    expect(screen.getByText('suggestion')).toBeInTheDocument();
    expect(screen.getByText('warning')).toBeInTheDocument();
  });

  it('should show confidence scores', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', mockAnnotations);

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
  });

  it('should call selectAnnotation on click', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', mockAnnotations);

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    const card = screen.getByText('Consider refactoring').closest('[role="button"]');
    fireEvent.click(card!);

    // Check that annotation was selected
    expect(rootStore.ai.marginAnnotation.selectedAnnotationId).toBe('ann-1');
  });

  it('should highlight selected annotation', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', mockAnnotations);
    rootStore.ai.marginAnnotation.selectedAnnotationId = 'ann-1';

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    const selectedCard = screen.getByText('Consider refactoring').closest('[role="button"]');
    expect(selectedCard).toHaveClass('ring-2');
  });

  it('should not render for blocks without annotations', () => {
    const firstAnnotation = mockAnnotations[0];
    if (!firstAnnotation) return;

    rootStore.ai.marginAnnotation.annotations.set('note-1', [firstAnnotation]);

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    expect(screen.getByText('Consider refactoring')).toBeInTheDocument();
    expect(screen.queryByText('Potential issue')).not.toBeInTheDocument();
  });

  it('should render nothing when no annotations exist', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', []);

    const { container } = renderWithStore(
      <MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('should position annotations based on block positions', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', mockAnnotations);

    const { container } = renderWithStore(
      <MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />
    );

    // Find annotation containers with absolute positioning
    const containers = container.querySelectorAll('.absolute');

    // Check first annotation position
    const firstContainer = Array.from(containers).find((el) =>
      el.textContent?.includes('Consider refactoring')
    ) as HTMLElement | undefined;
    expect(firstContainer?.style.top).toBe('0px');

    // Check second annotation position
    const secondContainer = Array.from(containers).find((el) =>
      el.textContent?.includes('Potential issue')
    ) as HTMLElement | undefined;
    expect(secondContainer?.style.top).toBe('120px');
  });

  it('should show annotation summaries', () => {
    rootStore.ai.marginAnnotation.annotations.set('note-1', mockAnnotations);

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    expect(screen.getByText('This section could be clearer')).toBeInTheDocument();
    expect(screen.getByText('Missing error handling')).toBeInTheDocument();
  });

  it('should handle multiple annotations per block', () => {
    const multipleAnnotations: NoteAnnotation[] = [
      ...mockAnnotations,
      {
        id: 'ann-3',
        noteId: 'note-1',
        blockId: 'block-1', // Same block as ann-1
        type: 'question',
        content: 'Full question content',
        confidence: 0.7,
        status: 'pending',
        aiMetadata: {
          title: 'Additional question',
          summary: 'Is this correct?',
        },
        createdAt: new Date().toISOString(),
      },
    ];

    rootStore.ai.marginAnnotation.annotations.set('note-1', multipleAnnotations);

    renderWithStore(<MarginAnnotationList noteId="note-1" blockPositions={mockBlockPositions} />);

    // Both annotations for block-1 should be present
    expect(screen.getByText('Consider refactoring')).toBeInTheDocument();
    expect(screen.getByText('Additional question')).toBeInTheDocument();
  });
});
