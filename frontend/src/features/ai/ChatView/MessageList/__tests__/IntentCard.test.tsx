/**
 * Unit tests for IntentCard component.
 * T-064
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IntentCard } from '../IntentCard';
import type { WorkIntentState } from '@/stores/ai/PilotSpaceStore';

function makeIntent(overrides?: Partial<WorkIntentState>): WorkIntentState {
  return {
    intentId: 'intent-1',
    what: 'Create a feature spec for user authentication',
    why: 'Current auth flow has too many steps',
    constraints: ['Must support OAuth', 'Session timeout >= 24h'],
    confidence: 0.82,
    status: 'detected',
    ...overrides,
  };
}

describe('IntentCard', () => {
  let onConfirm: ReturnType<typeof vi.fn>;
  let onDismiss: ReturnType<typeof vi.fn>;
  let onEdit: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onConfirm = vi.fn().mockResolvedValue(undefined);
    onDismiss = vi.fn().mockResolvedValue(undefined);
    onEdit = vi.fn().mockResolvedValue(undefined);
  });

  describe('detected state', () => {
    it('renders with correct ARIA role and label', () => {
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      const article = screen.getByRole('article');
      expect(article).toHaveAttribute(
        'aria-label',
        expect.stringContaining('Create a feature spec')
      );
    });

    it('renders what/why/constraints sections', () => {
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      expect(screen.getByText('Create a feature spec for user authentication')).toBeInTheDocument();
      expect(screen.getByText('Current auth flow has too many steps')).toBeInTheDocument();
      expect(screen.getByText('Must support OAuth')).toBeInTheDocument();
    });

    it('renders confidence bar with correct ARIA attributes', () => {
      render(
        <IntentCard
          intent={makeIntent({ confidence: 0.82 })}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      const bar = screen.getByRole('progressbar');
      expect(bar).toHaveAttribute('aria-valuenow', '82');
      expect(bar).toHaveAttribute('aria-valuemin', '0');
      expect(bar).toHaveAttribute('aria-valuemax', '100');
    });

    it('renders all three action buttons', () => {
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      expect(screen.getByTestId('intent-confirm')).toBeInTheDocument();
      expect(screen.getByTestId('intent-edit')).toBeInTheDocument();
      expect(screen.getByTestId('intent-dismiss')).toBeInTheDocument();
    });

    it('shows clarification note when confidence < 70%', () => {
      render(
        <IntentCard
          intent={makeIntent({ confidence: 0.65 })}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      expect(screen.getByText(/clarification needed/i)).toBeInTheDocument();
    });
  });

  describe('actions', () => {
    it('calls onConfirm when Confirm button clicked', async () => {
      const user = userEvent.setup();
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      await user.click(screen.getByTestId('intent-confirm'));
      expect(onConfirm).toHaveBeenCalledWith('intent-1');
    });

    it('calls onDismiss when Dismiss button clicked', async () => {
      const user = userEvent.setup();
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      await user.click(screen.getByTestId('intent-dismiss'));
      expect(onDismiss).toHaveBeenCalledWith('intent-1');
    });

    it('shows edit form when Edit clicked', async () => {
      const user = userEvent.setup();
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      await user.click(screen.getByTestId('intent-edit'));
      expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('Escape key cancels edit mode', async () => {
      const user = userEvent.setup();
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      await user.click(screen.getByTestId('intent-edit'));
      expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();

      await user.keyboard('{Escape}');
      expect(screen.queryByRole('button', { name: /save/i })).not.toBeInTheDocument();
    });

    it('calls onEdit with correct patch on Save', async () => {
      const user = userEvent.setup();
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      await user.click(screen.getByTestId('intent-edit'));

      const whatInput = screen.getByRole('textbox', { name: /intent description/i });
      await user.clear(whatInput);
      await user.type(whatInput, 'Updated what');

      await user.click(screen.getByRole('button', { name: /save/i }));
      await waitFor(() => {
        expect(onEdit).toHaveBeenCalledWith(
          'intent-1',
          expect.objectContaining({ new_what: 'Updated what' })
        );
      });
    });
  });

  describe('collapsed states', () => {
    it('renders confirmed collapsed state', () => {
      render(
        <IntentCard
          intent={makeIntent({ status: 'confirmed' })}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      expect(screen.getByText(/Intent confirmed/i)).toBeInTheDocument();
      expect(screen.queryByTestId('intent-confirm')).not.toBeInTheDocument();
    });

    it('renders rejected collapsed state', () => {
      render(
        <IntentCard
          intent={makeIntent({ status: 'rejected' })}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      // Intent what should be visible but strikethrough
      expect(screen.getByText('Create a feature spec for user authentication')).toBeInTheDocument();
    });

    it('renders nothing for executing status', () => {
      const { container } = render(
        <IntentCard
          intent={makeIntent({ status: 'executing' })}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      expect(container.firstChild).toBeNull();
    });
  });

  describe('accessibility', () => {
    it('all buttons have aria-label attributes', () => {
      render(
        <IntentCard
          intent={makeIntent()}
          onConfirm={onConfirm}
          onDismiss={onDismiss}
          onEdit={onEdit}
        />
      );
      expect(screen.getByTestId('intent-confirm')).toHaveAttribute('aria-label', 'Confirm intent');
      expect(screen.getByTestId('intent-edit')).toHaveAttribute('aria-label', 'Edit intent');
      expect(screen.getByTestId('intent-dismiss')).toHaveAttribute('aria-label', 'Dismiss intent');
    });
  });
});
