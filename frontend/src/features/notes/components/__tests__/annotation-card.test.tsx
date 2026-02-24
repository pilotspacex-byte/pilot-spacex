/**
 * AnnotationCard Tests (T028)
 * Tests for annotation action buttons based on annotation type
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnnotationCard } from '../annotation-card';
import { RootStore, StoreContext } from '@/stores/RootStore';
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

function makeAnnotation(overrides: Partial<NoteAnnotation> = {}): NoteAnnotation {
  return {
    id: 'ann-1',
    noteId: 'note-1',
    blockId: 'block-1',
    type: 'info',
    content: 'Default annotation content',
    confidence: 0.8,
    status: 'pending' as const,
    aiMetadata: {
      title: 'Default Title',
      summary: 'Default summary text',
    },
    createdAt: new Date().toISOString(),
    ...overrides,
  };
}

describe('AnnotationCard', () => {
  let rootStore: RootStore;
  const mockOnSelect = vi.fn();

  beforeEach(() => {
    rootStore = new RootStore();
    mockOnSelect.mockClear();
  });

  function renderCard(annotation: NoteAnnotation, isSelected = false) {
    return render(
      <StoreContext.Provider value={rootStore}>
        <AnnotationCard annotation={annotation} isSelected={isSelected} onSelect={mockOnSelect} />
      </StoreContext.Provider>
    );
  }

  describe('action button visibility', () => {
    it('shows "Extract Issue" button for issue_candidate type', () => {
      renderCard(makeAnnotation({ type: 'issue_candidate' }));

      expect(screen.getByRole('button', { name: /extract issue/i })).toBeInTheDocument();
    });

    it('shows "Ask AI" button for question type', () => {
      renderCard(makeAnnotation({ type: 'question' }));

      expect(screen.getByRole('button', { name: /ask ai/i })).toBeInTheDocument();
    });

    it('shows "Create Task" button for suggestion type', () => {
      renderCard(makeAnnotation({ type: 'suggestion' }));

      expect(screen.getByRole('button', { name: /create task/i })).toBeInTheDocument();
    });

    it('shows "Create Task" button for warning type', () => {
      renderCard(makeAnnotation({ type: 'warning' }));

      expect(screen.getByRole('button', { name: /create task/i })).toBeInTheDocument();
    });

    it('does not show action button for info type', () => {
      const { container } = renderCard(makeAnnotation({ type: 'info' }));

      // No <button> elements — only the outer div[role=button] card wrapper
      const buttons = container.querySelectorAll('button');
      expect(buttons).toHaveLength(0);
    });

    it('does not show action button for insight type', () => {
      const { container } = renderCard(makeAnnotation({ type: 'insight' }));

      const buttons = container.querySelectorAll('button');
      expect(buttons).toHaveLength(0);
    });

    it('does not show action button for reference type', () => {
      const { container } = renderCard(makeAnnotation({ type: 'reference' }));

      const buttons = container.querySelectorAll('button');
      expect(buttons).toHaveLength(0);
    });
  });

  describe('action button click sends correct message', () => {
    it('sends extract-issues message for issue_candidate', async () => {
      const sendMessageSpy = vi
        .spyOn(rootStore.ai.pilotSpace, 'sendMessage')
        .mockResolvedValue(undefined);

      const annotation = makeAnnotation({
        type: 'issue_candidate',
        content: 'Missing error handling in auth flow',
      });
      renderCard(annotation);

      const button = screen.getByRole('button', { name: /extract issue/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(sendMessageSpy).toHaveBeenCalledWith(
          '/extract-issues from block: Missing error handling in auth flow'
        );
      });
    });

    it('sends clarify message for question type', async () => {
      const sendMessageSpy = vi
        .spyOn(rootStore.ai.pilotSpace, 'sendMessage')
        .mockResolvedValue(undefined);

      const annotation = makeAnnotation({
        type: 'question',
        content: 'What is the expected behavior?',
        aiMetadata: { title: 'Question', summary: 'Is this correct?' },
      });
      renderCard(annotation);

      const button = screen.getByRole('button', { name: /ask ai/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(sendMessageSpy).toHaveBeenCalledWith('Clarify this section: Is this correct?');
      });
    });

    it('sends create-issue message for suggestion type', async () => {
      const sendMessageSpy = vi
        .spyOn(rootStore.ai.pilotSpace, 'sendMessage')
        .mockResolvedValue(undefined);

      const annotation = makeAnnotation({
        type: 'suggestion',
        aiMetadata: { title: 'Add input validation', summary: 'Consider validating user input' },
      });
      renderCard(annotation);

      const button = screen.getByRole('button', { name: /create task/i });
      fireEvent.click(button);

      await waitFor(() => {
        expect(sendMessageSpy).toHaveBeenCalledWith('/create-issue title: Add input validation');
      });
    });
  });

  describe('loading state', () => {
    it('shows spinner and "Working..." label during action', async () => {
      let resolvePromise: () => void;
      const sendPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });
      vi.spyOn(rootStore.ai.pilotSpace, 'sendMessage').mockReturnValue(sendPromise);

      renderCard(makeAnnotation({ type: 'issue_candidate' }));

      const button = screen.getByRole('button', { name: /extract issue/i });
      fireEvent.click(button);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('Working...')).toBeInTheDocument();
      });

      // Resolve the promise to finish loading
      resolvePromise!();

      await waitFor(() => {
        expect(screen.queryByText('Working...')).not.toBeInTheDocument();
        expect(screen.getByText('Extract Issue')).toBeInTheDocument();
      });
    });
  });

  describe('card interaction', () => {
    it('calls onSelect when card is clicked', () => {
      renderCard(makeAnnotation({ type: 'info' }));

      const card = screen.getByRole('button', { name: /info/i });
      fireEvent.click(card);

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
    });

    it('does not trigger card select when action button is clicked', async () => {
      vi.spyOn(rootStore.ai.pilotSpace, 'sendMessage').mockResolvedValue(undefined);

      renderCard(makeAnnotation({ type: 'issue_candidate' }));

      const actionButton = screen.getByRole('button', { name: /extract issue/i });
      fireEvent.click(actionButton);

      // onSelect should NOT be called because stopPropagation is used
      expect(mockOnSelect).not.toHaveBeenCalled();
    });

    it('shows selected state with ring styling', () => {
      const { container } = renderCard(makeAnnotation({ type: 'info' }), true);

      const card = container.querySelector('[role="button"]');
      expect(card).toHaveClass('ring-2');
    });
  });

  describe('accessibility', () => {
    it('action buttons have descriptive aria-labels', () => {
      renderCard(
        makeAnnotation({
          type: 'issue_candidate',
          aiMetadata: { title: 'Missing validation' },
        })
      );

      const button = screen.getByRole('button', { name: /extract issue for: missing validation/i });
      expect(button).toBeInTheDocument();
    });

    it('card container has aria-label and aria-pressed', () => {
      const { container } = renderCard(makeAnnotation({ type: 'info' }), true);

      const card = container.querySelector('[role="button"]');
      expect(card).toHaveAttribute('aria-pressed', 'true');
      expect(card).toHaveAttribute('aria-label');
    });

    it('card responds to keyboard Enter', () => {
      renderCard(makeAnnotation({ type: 'info' }));

      const card = screen.getByRole('button', { name: /info/i });
      fireEvent.keyDown(card, { key: 'Enter' });

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
    });

    it('card responds to keyboard Space', () => {
      renderCard(makeAnnotation({ type: 'info' }));

      const card = screen.getByRole('button', { name: /info/i });
      fireEvent.keyDown(card, { key: ' ' });

      expect(mockOnSelect).toHaveBeenCalledTimes(1);
    });
  });
});
