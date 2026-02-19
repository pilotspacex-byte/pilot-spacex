/**
 * Unit tests for SkillProgressCard component.
 * T-064
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SkillProgressCard } from '../SkillProgressCard';
import type { WorkIntentState } from '@/stores/ai/PilotSpaceStore';

function makeIntent(overrides?: Partial<WorkIntentState>): WorkIntentState {
  return {
    intentId: 'intent-1',
    what: 'Create auth spec',
    confidence: 0.85,
    status: 'executing',
    skillName: 'create-spec',
    intentSummary: 'Create a feature spec for user auth',
    skillProgress: 50,
    skillStep: 2,
    skillTotalSteps: 4,
    skillCurrentStep: 'Reading workspace constitution…',
    ...overrides,
  };
}

describe('SkillProgressCard', () => {
  let onViewArtifact: ReturnType<typeof vi.fn>;
  let onRevise: ReturnType<typeof vi.fn>;
  let onDismiss: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onViewArtifact = vi.fn();
    onRevise = vi.fn();
    onDismiss = vi.fn();
  });

  describe('executing state', () => {
    it('renders with role="status" and aria-live="polite"', () => {
      render(
        <SkillProgressCard
          intent={makeIntent()}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      const status = screen.getByRole('status');
      expect(status).toHaveAttribute('aria-live', 'polite');
    });

    it('renders skill name', () => {
      render(
        <SkillProgressCard
          intent={makeIntent()}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      expect(screen.getByText('create-spec')).toBeInTheDocument();
    });

    it('renders Running badge during execution', () => {
      render(
        <SkillProgressCard
          intent={makeIntent()}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      expect(screen.getByText(/Running/i)).toBeInTheDocument();
    });

    it('renders progress bar with correct aria attributes', () => {
      render(
        <SkillProgressCard
          intent={makeIntent({ skillProgress: 50, skillStep: 2, skillTotalSteps: 4 })}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      const bar = screen.getByRole('progressbar');
      expect(bar).toHaveAttribute('aria-valuenow', '50');
      expect(bar).toHaveAttribute('aria-valuetext', 'Step 2 of 4');
    });

    it('renders current step text', () => {
      render(
        <SkillProgressCard
          intent={makeIntent()}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      expect(screen.getByText('Reading workspace constitution…')).toBeInTheDocument();
    });
  });

  describe('completed state', () => {
    const completedIntent = makeIntent({
      status: 'completed',
      skillProgress: 100,
      artifacts: [{ type: 'note', id: 'note-1', name: 'Auth Spec Note' }],
    });

    it('renders Complete badge', () => {
      render(
        <SkillProgressCard
          intent={completedIntent}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      expect(screen.getByText('Complete')).toBeInTheDocument();
    });

    it('renders artifact links', () => {
      render(
        <SkillProgressCard
          intent={completedIntent}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      expect(screen.getByText('Auth Spec Note')).toBeInTheDocument();
    });

    it('calls onViewArtifact when artifact link clicked', async () => {
      const user = userEvent.setup();
      render(
        <SkillProgressCard
          intent={completedIntent}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      await user.click(screen.getByText('Auth Spec Note'));
      expect(onViewArtifact).toHaveBeenCalledWith('note-1', 'note');
    });

    it('calls onRevise when Revise button clicked', async () => {
      const user = userEvent.setup();
      render(
        <SkillProgressCard
          intent={completedIntent}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      await user.click(screen.getByText('Revise'));
      expect(onRevise).toHaveBeenCalledWith('intent-1');
    });
  });

  describe('failed state', () => {
    const failedIntent = makeIntent({
      status: 'failed',
      errorMessage: 'Token budget exhausted at step 3/4',
    });

    it('renders Failed badge', () => {
      render(
        <SkillProgressCard
          intent={failedIntent}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      expect(screen.getByText('Failed')).toBeInTheDocument();
    });

    it('renders error message', () => {
      render(
        <SkillProgressCard
          intent={failedIntent}
          onViewArtifact={onViewArtifact}
          onRevise={onRevise}
          onDismiss={onDismiss}
        />
      );
      expect(screen.getByText('Token budget exhausted at step 3/4')).toBeInTheDocument();
    });
  });
});
