/**
 * Unit tests for WaitingIndicator component.
 *
 * Tests rendering for question vs approval modes, ARIA attributes,
 * and visual indicator classes.
 *
 * Feature 014: Approval & User Input UX (T07)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WaitingIndicator } from '../WaitingIndicator';

describe('WaitingIndicator', () => {
  // -----------------------------------------------------------------------
  // 1. Renders correct text for question mode
  // -----------------------------------------------------------------------

  describe('question mode', () => {
    it('renders "Waiting for your response" message', () => {
      render(<WaitingIndicator waitingType="question" />);

      expect(screen.getByText('Waiting for your response')).toBeInTheDocument();
    });

    it('renders question-specific subtitle', () => {
      render(<WaitingIndicator waitingType="question" />);

      expect(screen.getByText('Answer the question above to continue')).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // 2. Renders correct text for approval mode
  // -----------------------------------------------------------------------

  describe('approval mode', () => {
    it('renders "Waiting for your approval" message', () => {
      render(<WaitingIndicator waitingType="approval" />);

      expect(screen.getByText('Waiting for your approval')).toBeInTheDocument();
    });

    it('renders approval-specific subtitle', () => {
      render(<WaitingIndicator waitingType="approval" />);

      expect(screen.getByText('Review the request above to continue')).toBeInTheDocument();
    });
  });

  // -----------------------------------------------------------------------
  // 3. ARIA attributes
  // -----------------------------------------------------------------------

  describe('ARIA compliance', () => {
    it('has role="status"', () => {
      render(<WaitingIndicator waitingType="question" />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has aria-live="polite"', () => {
      render(<WaitingIndicator waitingType="question" />);

      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveAttribute('aria-live', 'polite');
    });
  });

  // -----------------------------------------------------------------------
  // 4. Pulse dot indicator
  // -----------------------------------------------------------------------

  describe('pulse dot indicator', () => {
    it('renders a dot with animate-pulse class', () => {
      render(<WaitingIndicator waitingType="question" />);

      const statusElement = screen.getByRole('status');
      const dot = statusElement.querySelector('[aria-hidden="true"]');
      expect(dot).toBeInTheDocument();
      expect(dot).toHaveClass('animate-pulse');
    });

    it('renders dot with bg-ai class for AI theming', () => {
      render(<WaitingIndicator waitingType="approval" />);

      const statusElement = screen.getByRole('status');
      const dot = statusElement.querySelector('[aria-hidden="true"]');
      expect(dot).toHaveClass('bg-ai');
    });

    it('renders dot with rounded-full class', () => {
      render(<WaitingIndicator waitingType="question" />);

      const statusElement = screen.getByRole('status');
      const dot = statusElement.querySelector('[aria-hidden="true"]');
      expect(dot).toHaveClass('rounded-full');
    });

    it('dot is hidden from screen readers via aria-hidden', () => {
      render(<WaitingIndicator waitingType="question" />);

      const statusElement = screen.getByRole('status');
      const dot = statusElement.querySelector('[aria-hidden="true"]');
      expect(dot).toHaveAttribute('aria-hidden', 'true');
    });
  });

  // -----------------------------------------------------------------------
  // 5. data-testid and className
  // -----------------------------------------------------------------------

  describe('test utilities', () => {
    it('has data-testid="waiting-indicator"', () => {
      render(<WaitingIndicator waitingType="question" />);

      expect(screen.getByTestId('waiting-indicator')).toBeInTheDocument();
    });

    it('applies additional className prop', () => {
      render(<WaitingIndicator waitingType="question" className="custom-class" />);

      const element = screen.getByTestId('waiting-indicator');
      expect(element).toHaveClass('custom-class');
    });
  });
});
