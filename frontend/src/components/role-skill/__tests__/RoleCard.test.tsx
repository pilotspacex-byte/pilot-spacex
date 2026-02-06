/**
 * Component tests for RoleCard.
 *
 * T019: Tests for role selection card rendering, interaction, and accessibility.
 * Source: FR-001, FR-002, FR-011, FR-012, US1, US4
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RoleCard } from '../RoleCard';

describe('RoleCard', () => {
  const defaultProps = {
    roleType: 'developer',
    displayName: 'Developer',
    description: 'Code & architecture',
    icon: 'Code',
    onToggle: vi.fn(),
  };

  describe('rendering', () => {
    it('should render the display name', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.getByText('Developer')).toBeInTheDocument();
    });

    it('should render the description when not compact', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.getByText('Code & architecture')).toBeInTheDocument();
    });

    it('should render with data-testid', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.getByTestId('role-card-developer')).toBeInTheDocument();
    });
  });

  describe('selected state', () => {
    it('should show checkmark when selected', () => {
      const { container } = render(<RoleCard {...defaultProps} selected />);
      // Checkmark is rendered as a Check icon inside a green circle
      const checkmark = container.querySelector('.bg-primary');
      expect(checkmark).toBeInTheDocument();
    });

    it('should not show checkmark when unselected', () => {
      const { container } = render(<RoleCard {...defaultProps} selected={false} />);
      const checkmark = container.querySelector('.bg-primary');
      expect(checkmark).not.toBeInTheDocument();
    });

    it('should show selection order badge when selected', () => {
      render(<RoleCard {...defaultProps} selected selectionOrder={1} />);
      // Order badge uses circled numbers ①②③
      expect(screen.getByText('\u2460')).toBeInTheDocument();
    });

    it('should show second order badge', () => {
      render(<RoleCard {...defaultProps} selected selectionOrder={2} />);
      expect(screen.getByText('\u2461')).toBeInTheDocument();
    });

    it('should show third order badge', () => {
      render(<RoleCard {...defaultProps} selected selectionOrder={3} />);
      expect(screen.getByText('\u2462')).toBeInTheDocument();
    });

    it('should not show order badge when unselected', () => {
      render(<RoleCard {...defaultProps} selectionOrder={null} />);
      expect(screen.queryByText('\u2460')).not.toBeInTheDocument();
    });
  });

  describe('primary role', () => {
    it('should show PRIMARY label when isPrimary and selected', () => {
      render(<RoleCard {...defaultProps} selected isPrimary />);
      expect(screen.getByText('Primary')).toBeInTheDocument();
    });

    it('should not show PRIMARY label when not primary', () => {
      render(<RoleCard {...defaultProps} selected isPrimary={false} />);
      expect(screen.queryByText('Primary')).not.toBeInTheDocument();
    });

    it('should not show PRIMARY label when primary but not selected', () => {
      render(<RoleCard {...defaultProps} selected={false} isPrimary />);
      expect(screen.queryByText('Primary')).not.toBeInTheDocument();
    });
  });

  describe('badges', () => {
    it('should show "Your default" badge when isDefaultRole', () => {
      render(<RoleCard {...defaultProps} isDefaultRole />);
      expect(screen.getByText('Your default')).toBeInTheDocument();
    });

    it('should not show "Your default" badge by default', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.queryByText('Your default')).not.toBeInTheDocument();
    });

    it('should show "Suggested by owner" badge when isSuggestedByOwner', () => {
      render(<RoleCard {...defaultProps} isSuggestedByOwner />);
      expect(screen.getByText('Suggested by owner')).toBeInTheDocument();
    });

    it('should not show "Suggested by owner" badge by default', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.queryByText('Suggested by owner')).not.toBeInTheDocument();
    });

    it('should prioritize "Your default" when both badges apply', () => {
      render(<RoleCard {...defaultProps} isDefaultRole isSuggestedByOwner />);
      expect(screen.getByText('Your default')).toBeInTheDocument();
      expect(screen.queryByText('Suggested by owner')).not.toBeInTheDocument();
    });
  });

  describe('interaction', () => {
    it('should call onToggle on click', async () => {
      const onToggle = vi.fn();
      const user = userEvent.setup();

      render(<RoleCard {...defaultProps} onToggle={onToggle} />);

      await user.click(screen.getByTestId('role-card-developer'));
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('should call onToggle on Enter key', async () => {
      const onToggle = vi.fn();
      const user = userEvent.setup();

      render(<RoleCard {...defaultProps} onToggle={onToggle} />);

      const card = screen.getByTestId('role-card-developer');
      card.focus();
      await user.keyboard('{Enter}');
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('should call onToggle on Space key', async () => {
      const onToggle = vi.fn();
      const user = userEvent.setup();

      render(<RoleCard {...defaultProps} onToggle={onToggle} />);

      const card = screen.getByTestId('role-card-developer');
      card.focus();
      await user.keyboard(' ');
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('should not call onToggle when disabled', async () => {
      const onToggle = vi.fn();
      const user = userEvent.setup();

      render(<RoleCard {...defaultProps} onToggle={onToggle} disabled />);

      await user.click(screen.getByTestId('role-card-developer'));
      expect(onToggle).not.toHaveBeenCalled();
    });

    it('should not call onToggle on keyboard when disabled', async () => {
      const onToggle = vi.fn();
      const user = userEvent.setup();

      render(<RoleCard {...defaultProps} onToggle={onToggle} disabled />);

      const card = screen.getByTestId('role-card-developer');
      card.focus();
      await user.keyboard('{Enter}');
      expect(onToggle).not.toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('should have role="checkbox"', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.getByRole('checkbox')).toBeInTheDocument();
    });

    it('should have aria-checked=false when unselected', () => {
      render(<RoleCard {...defaultProps} selected={false} />);
      expect(screen.getByRole('checkbox')).toHaveAttribute('aria-checked', 'false');
    });

    it('should have aria-checked=true when selected', () => {
      render(<RoleCard {...defaultProps} selected />);
      expect(screen.getByRole('checkbox')).toHaveAttribute('aria-checked', 'true');
    });

    it('should have aria-disabled when disabled', () => {
      render(<RoleCard {...defaultProps} disabled />);
      expect(screen.getByRole('checkbox')).toHaveAttribute('aria-disabled', 'true');
    });

    it('should be focusable when not disabled', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.getByRole('checkbox')).toHaveAttribute('tabindex', '0');
    });

    it('should not be focusable when disabled', () => {
      render(<RoleCard {...defaultProps} disabled />);
      expect(screen.getByRole('checkbox')).toHaveAttribute('tabindex', '-1');
    });

    it('should include display name in aria-label', () => {
      render(<RoleCard {...defaultProps} />);
      expect(screen.getByRole('checkbox')).toHaveAttribute(
        'aria-label',
        expect.stringContaining('Developer')
      );
    });

    it('should include primary role in aria-label when primary', () => {
      render(<RoleCard {...defaultProps} isPrimary />);
      expect(screen.getByRole('checkbox')).toHaveAttribute(
        'aria-label',
        expect.stringContaining('primary role')
      );
    });

    it('should include default role info in aria-label', () => {
      render(<RoleCard {...defaultProps} isDefaultRole />);
      expect(screen.getByRole('checkbox')).toHaveAttribute(
        'aria-label',
        expect.stringContaining('your default role')
      );
    });

    it('should include suggested info in aria-label', () => {
      render(<RoleCard {...defaultProps} isSuggestedByOwner />);
      expect(screen.getByRole('checkbox')).toHaveAttribute(
        'aria-label',
        expect.stringContaining('suggested by workspace owner')
      );
    });
  });

  describe('compact variant', () => {
    it('should render with compact dimensions', () => {
      const { container } = render(<RoleCard {...defaultProps} variant="compact" />);
      const card = container.firstElementChild;
      expect(card?.className).toContain('w-[120px]');
      expect(card?.className).toContain('h-[100px]');
    });

    it('should not show description in compact variant', () => {
      render(<RoleCard {...defaultProps} variant="compact" />);
      expect(screen.queryByText('Code & architecture')).not.toBeInTheDocument();
    });

    it('should render with standard dimensions by default', () => {
      const { container } = render(<RoleCard {...defaultProps} />);
      const card = container.firstElementChild;
      expect(card?.className).toContain('w-[160px]');
      expect(card?.className).toContain('h-[140px]');
    });
  });
});
