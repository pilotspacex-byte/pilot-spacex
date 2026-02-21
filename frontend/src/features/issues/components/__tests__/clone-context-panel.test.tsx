/**
 * CloneContextPanel component tests.
 *
 * Tests for the redesigned export context popover with segmented tabs,
 * preview, and copy functionality.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CloneContextPanel, type CloneContextPanelProps } from '../clone-context-panel';

// Mock framer-motion
vi.mock('motion/react', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock Popover — renders content inline; trigger button sets data-open on root
vi.mock('@/components/ui/popover', async () => {
  const { createContext, useContext, useState, useEffect } = await import('react');

  const Ctx = createContext<{ isOpen: boolean; toggle: () => void }>({
    isOpen: false,
    toggle: () => {},
  });

  return {
    Popover: ({
      children,
      open,
      onOpenChange,
    }: {
      children: React.ReactNode;
      open?: boolean;
      onOpenChange?: (v: boolean) => void;
    }) => {
      const [internal, setInternal] = useState(open ?? false);
      const isOpen = open !== undefined ? open : internal;
      useEffect(() => {
        if (open !== undefined) setInternal(open);
      }, [open]);
      const toggle = () => {
        const next = !isOpen;
        setInternal(next);
        onOpenChange?.(next);
      };
      return (
        <Ctx.Provider value={{ isOpen, toggle }}>
          <div data-testid="popover-root">{children}</div>
        </Ctx.Provider>
      );
    },
    PopoverTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) => {
      const { toggle } = useContext(Ctx);
      if (asChild && React.isValidElement(children)) {
        return React.cloneElement(
          children as React.ReactElement,
          {
            onClick: (e: React.MouseEvent) => {
              const orig = (
                children as React.ReactElement<{ onClick?: (e: React.MouseEvent) => void }>
              ).props.onClick;
              orig?.(e);
              toggle();
            },
          } as Record<string, unknown>
        );
      }
      return (
        <div data-testid="popover-trigger" onClick={toggle}>
          {children}
        </div>
      );
    },
    PopoverContent: ({
      children,
      role,
      'aria-label': ariaLabel,
    }: {
      children: React.ReactNode;
      className?: string;
      align?: string;
      sideOffset?: number;
      role?: string;
      'aria-label'?: string;
      onOpenAutoFocus?: (e: Event) => void;
      onCloseAutoFocus?: (e: Event) => void;
    }) => {
      const { isOpen } = useContext(Ctx);
      if (!isOpen) return null;
      return (
        <div data-testid="popover-content" role={role} aria-label={ariaLabel}>
          {children}
        </div>
      );
    },
  };
});

// Mock Tooltip
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) =>
    asChild && React.isValidElement(children) ? children : <div>{children}</div>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  TerminalSquare: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="terminal-square-icon" className={className as string} {...props} />
  ),
  Terminal: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="terminal-icon" className={className as string} {...props} />
  ),
  Copy: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="copy-icon" className={className as string} {...props} />
  ),
  Check: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="check-icon" className={className as string} {...props} />
  ),
  ListChecks: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="list-checks-icon" className={className as string} {...props} />
  ),
  MessageSquare: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="message-square-icon" className={className as string} {...props} />
  ),
  FileText: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="file-text-icon" className={className as string} {...props} />
  ),
  FileQuestion: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="file-question-icon" className={className as string} {...props} />
  ),
  X: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="x-icon" className={className as string} {...props} />
  ),
}));

describe('CloneContextPanel', () => {
  const defaultProps: CloneContextPanelProps = {
    onExport: vi.fn().mockResolvedValue('# Exported content\n\nSome tasks here'),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  function renderPanel(props: Partial<CloneContextPanelProps> = {}) {
    return render(<CloneContextPanel {...defaultProps} {...props} />);
  }

  it('renders trigger button with "Clone" text', () => {
    renderPanel();
    expect(screen.getByText('Clone')).toBeInTheDocument();
  });

  it('disables trigger button when isLoading is true', () => {
    renderPanel({ isLoading: true });
    const button = screen.getByText('Clone').closest('button');
    expect(button).toBeDisabled();
  });

  it('has aria-haspopup="dialog" on trigger button', () => {
    renderPanel();
    const button = screen.getByText('Clone').closest('button');
    expect(button).toHaveAttribute('aria-haspopup', 'dialog');
  });

  it('opens popover on click and shows 3 tabs', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
  });

  it('shows Prompt, Markdown, and Checklist tabs', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    expect(screen.getByRole('tab', { name: 'Prompt' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Markdown' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Checklist' })).toBeInTheDocument();
  });

  it('defaults to Prompt tab (claude_code format) when popover opens', async () => {
    const onExport = vi.fn().mockResolvedValue('# Claude prompt');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith('claude_code');
    });
  });

  it('calls onExport with correct format when tab changes', async () => {
    const onExport = vi.fn().mockResolvedValue('exported content');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith('claude_code');
    });

    fireEvent.click(screen.getByRole('tab', { name: 'Markdown' }));

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith('markdown');
    });

    fireEvent.click(screen.getByRole('tab', { name: 'Checklist' }));

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith('task_list');
    });
  });

  it('shows preview content after loading', async () => {
    const onExport = vi.fn().mockResolvedValue('Preview content here');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByText('Preview content here')).toBeInTheDocument();
    });
  });

  it('shows loading skeleton while preview loads and resolves to content', async () => {
    let resolveExport!: (value: string) => void;
    const onExport = vi.fn().mockReturnValue(
      new Promise<string>((resolve) => {
        resolveExport = resolve;
      })
    );
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      // Skeleton container has aria-busy=true and aria-label
      const skeleton = screen.getByLabelText('Loading context...');
      expect(skeleton).toHaveAttribute('aria-busy', 'true');
    });

    await act(async () => {
      resolveExport('Loaded content');
    });

    await waitFor(() => {
      expect(screen.getByText('Loaded content')).toBeInTheDocument();
    });
  });

  it('shows empty state when export returns null', async () => {
    const onExport = vi.fn().mockResolvedValue(null);
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByText('No context to clone')).toBeInTheDocument();
    });
  });

  it('shows empty state when export fails', async () => {
    const onExport = vi.fn().mockRejectedValue(new Error('Export error'));
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByText('No context to clone')).toBeInTheDocument();
    });
  });

  it('copy button copies preview to clipboard', async () => {
    const onExport = vi.fn().mockResolvedValue('Content to copy');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByText('Content to copy')).toBeInTheDocument();
    });

    const copyButton = screen.getByRole('button', { name: /copy context to clipboard/i });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Content to copy');
    });
  });

  it('shows "Copied" feedback after copy', async () => {
    const onExport = vi.fn().mockResolvedValue('Content to copy');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByText('Content to copy')).toBeInTheDocument();
    });

    const copyButton = screen.getByRole('button', { name: /copy context/i });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(screen.getByText('Copied')).toBeInTheDocument();
    });
  });

  it('shows stats in context summary when provided', async () => {
    renderPanel({
      issueIdentifier: 'PS-42',
      issueTitle: 'Fix auth bug',
      stats: { tasksCount: 5, relatedIssuesCount: 3, relatedDocsCount: 2 },
    });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    expect(screen.getByText(/5 tasks/)).toBeInTheDocument();
    expect(screen.getByText(/3 issues/)).toBeInTheDocument();
    expect(screen.getByText(/2 docs/)).toBeInTheDocument();
  });

  it('shows issueIdentifier and issueTitle in context summary', async () => {
    renderPanel({ issueIdentifier: 'PS-99', issueTitle: 'Add dark mode' });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    expect(screen.getByText(/PS-99 · Add dark mode/)).toBeInTheDocument();
  });

  it('does not show context summary section when no identifier, title, or stats', async () => {
    renderPanel();

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    expect(screen.queryByText(/tasks · /)).not.toBeInTheDocument();
  });

  it('shows panel header "Clone Context"', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    // "Clone Context" appears in the panel header
    const headings = screen.getAllByText('Clone Context');
    expect(headings.length).toBeGreaterThanOrEqual(1);
  });

  it('has Copy & Close button in footer', async () => {
    const onExport = vi.fn().mockResolvedValue('Some content');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByText('Some content')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /copy.*close/i })).toBeInTheDocument();
  });

  it('Copy & Close button copies content and closes panel', async () => {
    const onExport = vi.fn().mockResolvedValue('Close content');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone'));

    await waitFor(() => {
      expect(screen.getByText('Close content')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /copy.*close/i }));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Close content');
    });
  });
});
