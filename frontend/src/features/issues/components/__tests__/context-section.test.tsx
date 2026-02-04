/**
 * ContextSection component tests.
 *
 * Tests for reusable context section with icon, title, copy functionality, and error handling.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ContextSection } from '../context-section';

// Mock icon component
function MockIcon(props: Record<string, unknown>) {
  return <svg data-testid="section-icon" {...props} />;
}

// Mock shadcn/ui components
vi.mock('@/components/ui/button', () => ({
  Button: (props: Record<string, unknown>) => (
    <button
      data-testid="copy-button"
      onClick={props.onClick as () => void}
      aria-label={props['aria-label'] as string}
    >
      {props.children as React.ReactNode}
    </button>
  ),
}));

vi.mock('lucide-react', () => ({
  Copy: () => <span data-testid="copy-icon">Copy</span>,
  Check: () => <span data-testid="check-icon">Check</span>,
  AlertCircle: () => <span data-testid="alert-icon">Alert</span>,
}));

describe('ContextSection', () => {
  it('renders icon and title', () => {
    render(
      <ContextSection icon={MockIcon} title="Related Issues">
        <div>Content</div>
      </ContextSection>
    );

    expect(screen.getByTestId('section-icon')).toBeInTheDocument();
    expect(screen.getByText('Related Issues')).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <ContextSection icon={MockIcon} title="Test Section">
        <div>Child content here</div>
        <p>Multiple children</p>
      </ContextSection>
    );

    expect(screen.getByText('Child content here')).toBeInTheDocument();
    expect(screen.getByText('Multiple children')).toBeInTheDocument();
  });

  it('triggers onCopy callback and shows Copied! feedback when onCopy returns true', async () => {
    const onCopyMock = vi.fn().mockResolvedValue(true);

    render(
      <ContextSection icon={MockIcon} title="Test Section" onCopy={onCopyMock}>
        <div>Content</div>
      </ContextSection>
    );

    const copyButton = screen.getByTestId('copy-button');
    fireEvent.click(copyButton);

    expect(onCopyMock).toHaveBeenCalledTimes(1);

    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
      expect(screen.getByTestId('check-icon')).toBeInTheDocument();
    });
  });

  it('does NOT show Copied! when onCopy returns false', async () => {
    const onCopyMock = vi.fn().mockResolvedValue(false);

    render(
      <ContextSection icon={MockIcon} title="Test Section" onCopy={onCopyMock}>
        <div>Content</div>
      </ContextSection>
    );

    const copyButton = screen.getByTestId('copy-button');
    fireEvent.click(copyButton);

    expect(onCopyMock).toHaveBeenCalledTimes(1);

    // Wait briefly to ensure no state change
    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(screen.queryByText('Copied!')).not.toBeInTheDocument();
    expect(screen.queryByTestId('check-icon')).not.toBeInTheDocument();
    expect(screen.getByTestId('copy-icon')).toBeInTheDocument();
  });

  it('renders error state with destructive alert and error message', () => {
    const errorMessage = 'Failed to load related issues';

    render(
      <ContextSection icon={MockIcon} title="Test Section" error={errorMessage}>
        <div>Content</div>
      </ContextSection>
    );

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(screen.getByTestId('alert-icon')).toBeInTheDocument();
  });

  it('does not render copy button when onCopy is not provided', () => {
    render(
      <ContextSection icon={MockIcon} title="Test Section">
        <div>Content</div>
      </ContextSection>
    );

    expect(screen.queryByTestId('copy-button')).not.toBeInTheDocument();
    expect(screen.queryByText('Copy')).not.toBeInTheDocument();
  });
});
