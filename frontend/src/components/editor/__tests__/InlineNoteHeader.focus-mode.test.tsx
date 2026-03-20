/**
 * Unit tests for InlineNoteHeader focus mode button behavior.
 *
 * Tests cover:
 * - Focus button renders with correct aria-label when isFocusMode=false
 * - Focus button has correct aria-pressed value
 * - Focus button aria-label changes when isFocusMode=true
 * - Clicking focus button calls onToggleFocusMode
 * - Focus button NOT rendered when onToggleFocusMode is undefined
 *
 * @module components/editor/__tests__/InlineNoteHeader.focus-mode.test
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { InlineNoteHeader } from '../InlineNoteHeader';

// Mock next/link to render a plain anchor
vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const baseProps = {
  title: 'Test Note',
  createdAt: new Date().toISOString(),
  wordCount: 0,
  workspaceSlug: 'test',
};

describe('InlineNoteHeader — focus mode button', () => {
  it('renders focus button with aria-label "Focus mode" when isFocusMode=false and onToggleFocusMode is provided', () => {
    renderWithProviders(
      <InlineNoteHeader {...baseProps} isFocusMode={false} onToggleFocusMode={vi.fn()} />
    );
    const focusBtn = screen.getByRole('button', { name: 'Focus mode' });
    expect(focusBtn).toBeInTheDocument();
  });

  it('focus button has aria-pressed="false" when isFocusMode=false', () => {
    renderWithProviders(
      <InlineNoteHeader {...baseProps} isFocusMode={false} onToggleFocusMode={vi.fn()} />
    );
    const focusBtn = screen.getByRole('button', { name: 'Focus mode' });
    expect(focusBtn).toHaveAttribute('aria-pressed', 'false');
  });

  it('focus button has aria-pressed="true" when isFocusMode=true', () => {
    renderWithProviders(
      <InlineNoteHeader {...baseProps} isFocusMode={true} onToggleFocusMode={vi.fn()} />
    );
    const focusBtn = screen.getByRole('button', { name: 'Exit focus mode' });
    expect(focusBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('focus button has aria-label "Exit focus mode" when isFocusMode=true', () => {
    renderWithProviders(
      <InlineNoteHeader {...baseProps} isFocusMode={true} onToggleFocusMode={vi.fn()} />
    );
    expect(screen.getByRole('button', { name: 'Exit focus mode' })).toBeInTheDocument();
  });

  it('clicking focus button calls onToggleFocusMode', () => {
    const mockToggle = vi.fn();
    renderWithProviders(
      <InlineNoteHeader {...baseProps} isFocusMode={false} onToggleFocusMode={mockToggle} />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Focus mode' }));
    expect(mockToggle).toHaveBeenCalledOnce();
  });

  it('focus button is NOT rendered when onToggleFocusMode is undefined', () => {
    renderWithProviders(
      <InlineNoteHeader
        {...baseProps}
        isFocusMode={false}
        // onToggleFocusMode not provided
      />
    );
    expect(screen.queryByRole('button', { name: /focus mode/i })).not.toBeInTheDocument();
  });
});
