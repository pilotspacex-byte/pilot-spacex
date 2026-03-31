/**
 * Unit tests for SkillTestResultCard component.
 * Phase 64-03
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SkillTestResultCard } from '../SkillTestResultCard';

const defaultProps = {
  skillName: 'test-skill',
  score: 8,
  passed: ['Has trigger', 'Has examples'],
  failed: ['Missing description'],
  suggestions: ['Add examples', 'Improve trigger pattern'],
  sampleOutput: 'Sample skill output here',
};

describe('SkillTestResultCard', () => {
  let onRefine: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onRefine = vi.fn();
  });

  it('renders score as N/10 text', () => {
    render(<SkillTestResultCard {...defaultProps} onRefine={onRefine} />);
    expect(screen.getByText('8/10')).toBeInTheDocument();
  });

  it('renders passed items', () => {
    render(<SkillTestResultCard {...defaultProps} onRefine={onRefine} />);
    expect(screen.getByText('Has trigger')).toBeInTheDocument();
    expect(screen.getByText('Has examples')).toBeInTheDocument();
  });

  it('renders failed items', () => {
    render(<SkillTestResultCard {...defaultProps} onRefine={onRefine} />);
    expect(screen.getByText('Missing description')).toBeInTheDocument();
  });

  it('shows suggestion count toggle and expands on click', async () => {
    const user = userEvent.setup();
    render(<SkillTestResultCard {...defaultProps} onRefine={onRefine} />);
    // Suggestions hidden initially
    expect(screen.queryByText('Add examples')).not.toBeInTheDocument();
    // Toggle button visible
    const toggleBtn = screen.getByText(/2 suggestions/i);
    expect(toggleBtn).toBeInTheDocument();
    // Click to expand
    await user.click(toggleBtn);
    expect(screen.getByText(/Add examples/)).toBeInTheDocument();
    expect(screen.getByText(/Improve trigger pattern/)).toBeInTheDocument();
  });

  it('progressbar has correct aria-valuenow attribute', () => {
    render(<SkillTestResultCard {...defaultProps} onRefine={onRefine} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '8');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '10');
  });

  it('calls onRefine when Refine button clicked', async () => {
    const user = userEvent.setup();
    render(<SkillTestResultCard {...defaultProps} onRefine={onRefine} />);
    await user.click(screen.getByRole('button', { name: /refine/i }));
    expect(onRefine).toHaveBeenCalledTimes(1);
  });

  it('renders skill name in header', () => {
    render(<SkillTestResultCard {...defaultProps} onRefine={onRefine} />);
    expect(screen.getByText(/test-skill/)).toBeInTheDocument();
  });
});
