/**
 * Unit tests for TokenRing component.
 *
 * Validates:
 * 1. Renders nothing when totalTokens is 0
 * 2. Renders SVG with teal fill (--primary) when usage < 80%
 * 3. Renders with amber fill (--warning) when usage is 80-95%
 * 4. Renders with red fill (--destructive) when usage > 95%
 * 5. Center label shows formatted count (e.g., "4.2k" for 4200)
 * 6. Has role="progressbar" with correct aria attributes
 * 7. Tooltip shows "N,NNN / 8,000 tokens used this session"
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TokenRing } from '../TokenRing';

// Mock mobx-react-lite
vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

// Mock shadcn Tooltip — render content directly so we can assert on it
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: React.ReactNode; asChild?: boolean }) => (
    <>{children}</>
  ),
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <span data-testid="tooltip-content">{children}</span>
  ),
}));

describe('TokenRing', () => {
  it('Test 1: renders nothing when totalTokens is 0', () => {
    const { container } = render(<TokenRing totalTokens={0} />);
    expect(container.firstChild).toBeNull();
  });

  it('Test 1b: renders nothing when totalTokens is null-like (falsy)', () => {
    // TypeScript won't allow null directly, but test 0 thoroughly
    const { container } = render(<TokenRing totalTokens={0} budgetTokens={8000} />);
    expect(container.firstChild).toBeNull();
  });

  it('Test 2: renders SVG with primary (teal) fill color when usage < 80%', () => {
    // 4000 tokens = 50% of 8000 budget
    const { container } = render(<TokenRing totalTokens={4000} budgetTokens={8000} />);
    const progressCircle = container.querySelector('[data-testid="token-ring-progress"]');
    expect(progressCircle).toBeInTheDocument();
    expect(progressCircle).toHaveAttribute('stroke', 'var(--primary)');
  });

  it('Test 3: renders with warning (amber) fill when usage is 80-95%', () => {
    // 7000 tokens = 87.5% of 8000 budget
    const { container } = render(<TokenRing totalTokens={7000} budgetTokens={8000} />);
    const progressCircle = container.querySelector('[data-testid="token-ring-progress"]');
    expect(progressCircle).toBeInTheDocument();
    expect(progressCircle).toHaveAttribute('stroke', 'var(--warning)');
  });

  it('Test 4: renders with destructive (red) fill when usage > 95%', () => {
    // 7700 tokens = 96.25% of 8000 budget
    const { container } = render(<TokenRing totalTokens={7700} budgetTokens={8000} />);
    const progressCircle = container.querySelector('[data-testid="token-ring-progress"]');
    expect(progressCircle).toBeInTheDocument();
    expect(progressCircle).toHaveAttribute('stroke', 'var(--destructive)');
  });

  it('Test 5: center label shows formatted count "4.2k" for 4200 tokens', () => {
    render(<TokenRing totalTokens={4200} budgetTokens={8000} />);
    expect(screen.getByText('4.2k')).toBeInTheDocument();
  });

  it('Test 5b: center label shows raw number for tokens < 1000', () => {
    render(<TokenRing totalTokens={500} budgetTokens={8000} />);
    expect(screen.getByText('500')).toBeInTheDocument();
  });

  it('Test 6: has role="progressbar" with correct aria attributes', () => {
    render(<TokenRing totalTokens={4000} budgetTokens={8000} />);
    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toBeInTheDocument();
    expect(progressbar).toHaveAttribute('aria-valuenow', '4000');
    expect(progressbar).toHaveAttribute('aria-valuemin', '0');
    expect(progressbar).toHaveAttribute('aria-valuemax', '8000');
    expect(progressbar).toHaveAttribute('aria-label', 'Session token usage');
  });

  it('Test 7: tooltip shows formatted token count out of budget', () => {
    render(<TokenRing totalTokens={4200} budgetTokens={8000} />);
    const tooltip = screen.getByTestId('tooltip-content');
    expect(tooltip).toHaveTextContent('4,200');
    expect(tooltip).toHaveTextContent('8,000');
    expect(tooltip).toHaveTextContent('tokens used this session');
  });

  it('Test 7b: tooltip appends warning message when usage > 80%', () => {
    render(<TokenRing totalTokens={7000} budgetTokens={8000} />);
    const tooltip = screen.getByTestId('tooltip-content');
    expect(tooltip).toHaveTextContent('approaching session limit');
  });
});
