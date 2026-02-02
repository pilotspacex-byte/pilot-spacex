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

  it('should show "Saving..." with pulse animation when status is saving', () => {
    render(<SaveStatus status="saving" />);

    const element = screen.getByText('Saving...');
    expect(element).toBeInTheDocument();
    expect(element).toHaveClass('animate-pulse');
    expect(element).toHaveClass('text-foreground-muted');
  });

  it('should show "Saved" with primary color when status is saved', () => {
    render(<SaveStatus status="saved" />);

    const element = screen.getByText('Saved');
    expect(element).toBeInTheDocument();
    expect(element).toHaveClass('text-primary');
  });

  it('should show "Save failed" when status is error without custom message', () => {
    render(<SaveStatus status="error" />);

    expect(screen.getByText('Save failed')).toBeInTheDocument();
  });

  it('should show custom error message when provided', () => {
    render(<SaveStatus status="error" errorMessage="Network timeout" />);

    expect(screen.getByText('Network timeout')).toBeInTheDocument();
    expect(screen.queryByText('Save failed')).not.toBeInTheDocument();
  });

  it('should have role="status" and aria-live="polite" for accessibility', () => {
    render(<SaveStatus status="saving" />);

    const element = screen.getByRole('status');
    expect(element).toBeInTheDocument();
    expect(element).toHaveAttribute('aria-live', 'polite');
  });

  it('should accept and apply className prop', () => {
    render(<SaveStatus status="saved" className="ml-2 font-medium" />);

    const element = screen.getByText('Saved');
    expect(element).toHaveClass('ml-2');
    expect(element).toHaveClass('font-medium');
  });

  it('should apply base transition classes for all visible states', () => {
    render(<SaveStatus status="saved" />);

    const element = screen.getByText('Saved');
    expect(element).toHaveClass('text-xs');
    expect(element).toHaveClass('transition-opacity');
    expect(element).toHaveClass('duration-300');
  });

  it('should apply destructive class when status is error', () => {
    render(<SaveStatus status="error" />);

    const element = screen.getByText('Save failed');
    expect(element).toHaveClass('text-destructive');
  });
});
