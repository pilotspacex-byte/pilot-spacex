/**
 * Tests for WordCountBar component.
 *
 * T040: Word count bar rendering and color states.
 * Source: FR-009, FR-010, US6
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WordCountBar } from '../word-count-bar';

describe('WordCountBar', () => {
  it('should render word count text', () => {
    render(<WordCountBar wordCount={500} />);
    expect(screen.getByText('500 / 2000 words')).toBeInTheDocument();
  });

  it('should render meter role with correct aria attributes', () => {
    render(<WordCountBar wordCount={500} maxWords={2000} />);
    const meter = screen.getByRole('meter');
    expect(meter).toHaveAttribute('aria-valuenow', '500');
    expect(meter).toHaveAttribute('aria-valuemin', '0');
    expect(meter).toHaveAttribute('aria-valuemax', '2000');
  });

  it('should show green bar for normal count', () => {
    const { container } = render(<WordCountBar wordCount={500} />);
    const bar = container.querySelector('.bg-primary');
    expect(bar).toBeInTheDocument();
  });

  it('should show orange bar for warning count (1800+)', () => {
    const { container } = render(<WordCountBar wordCount={1850} />);
    const bar = container.querySelector('.bg-\\[var\\(--warning\\)\\]');
    expect(bar).toBeInTheDocument();
  });

  it('should show red bar for over-limit count (2000+)', () => {
    const { container } = render(<WordCountBar wordCount={2100} />);
    const bar = container.querySelector('.bg-destructive');
    expect(bar).toBeInTheDocument();
  });

  it('should cap bar width at 100%', () => {
    const { container } = render(<WordCountBar wordCount={3000} maxWords={2000} />);
    const bar = container.querySelector('[style*="width"]');
    expect(bar).toHaveStyle('width: 100%');
  });

  it('should accept custom maxWords', () => {
    render(<WordCountBar wordCount={500} maxWords={1000} />);
    expect(screen.getByText('500 / 1000 words')).toBeInTheDocument();
  });
});
