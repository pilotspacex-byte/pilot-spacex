/**
 * Component tests for SaveStatus.
 *
 * T001/T002: Tests for save status indicator rendering and accessibility.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SaveStatus } from '../save-status';

describe('SaveStatus', () => {
  it('should return null when status is idle', () => {
    const { container } = render(<SaveStatus status="idle" />);

    expect(container.innerHTML).toBe('');
  });

  it('should show spinning loader icon when status is saving', () => {
    render(<SaveStatus status="saving" />);

    const element = screen.getByRole('status');
    expect(element).toBeInTheDocument();
    expect(element).toHaveAttribute('aria-label', 'Saving');

    const svg = element.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass('animate-spin');
    expect(svg).toHaveClass('text-muted-foreground');
  });

  it('should show check icon with primary color when status is saved', () => {
    render(<SaveStatus status="saved" />);

    const element = screen.getByRole('status');
    expect(element).toBeInTheDocument();
    expect(element).toHaveAttribute('aria-label', 'Saved');

    const svg = element.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass('text-primary');
  });

  it('should show alert icon when status is error without custom message', () => {
    render(<SaveStatus status="error" />);

    const element = screen.getByRole('status');
    expect(element).toHaveAttribute('aria-label', 'Save failed');

    const svg = element.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass('text-destructive');
  });

  it('should use custom error message in aria-label when provided', () => {
    render(<SaveStatus status="error" errorMessage="Network timeout" />);

    const element = screen.getByRole('status');
    expect(element).toHaveAttribute('aria-label', 'Network timeout');
  });

  it('should have role="status" and aria-live="polite" for accessibility', () => {
    render(<SaveStatus status="saving" />);

    const element = screen.getByRole('status');
    expect(element).toBeInTheDocument();
    expect(element).toHaveAttribute('aria-live', 'polite');
  });

  it('should accept and apply className prop', () => {
    render(<SaveStatus status="saved" className="ml-2 font-medium" />);

    const element = screen.getByRole('status');
    expect(element).toHaveClass('ml-2');
    expect(element).toHaveClass('font-medium');
  });

  it('should apply base transition classes for all visible states', () => {
    render(<SaveStatus status="saved" />);

    const element = screen.getByRole('status');
    expect(element).toHaveClass('transition-opacity');
    expect(element).toHaveClass('duration-300');
  });
});
