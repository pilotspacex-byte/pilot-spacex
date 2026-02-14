/**
 * CloneContextPanel component tests.
 *
 * Tests for export context popover with tabs, preview, and copy functionality.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CloneContextPanel, type CloneContextPanelProps } from '../clone-context-panel';

// Mock shadcn/ui Popover to render content without portal/animation
vi.mock('@/components/ui/popover', () => {
  return {
    Popover: ({
      children,
      open,
      onOpenChange,
    }: {
      children: React.ReactNode;
      open?: boolean;
      onOpenChange?: (open: boolean) => void;
    }) => {
      const [internalOpen, setInternalOpen] = React.useState(open ?? false);
      const isOpen = open !== undefined ? open : internalOpen;

      React.useEffect(() => {
        if (open !== undefined) setInternalOpen(open);
      }, [open]);

      return (
        <div
          data-testid="popover-root"
          data-state={isOpen ? 'open' : 'closed'}
          onClick={() => {
            // Only toggle if not controlled
          }}
        >
          {React.Children.map(children, (child) => {
            if (React.isValidElement(child)) {
              return React.cloneElement(
                child as React.ReactElement,
                {
                  'data-popover-open': isOpen,
                  onToggle: () => {
                    const next = !isOpen;
                    setInternalOpen(next);
                    onOpenChange?.(next);
                  },
                } as Record<string, unknown>
              );
            }
            return child;
          })}
        </div>
      );
    },
    PopoverTrigger: ({
      children,
      asChild,
      onToggle,
      ...props
    }: {
      children: React.ReactNode;
      asChild?: boolean;
      onToggle?: () => void;
      'data-popover-open'?: boolean;
    }) => {
      if (asChild && React.isValidElement(children)) {
        return React.cloneElement(
          children as React.ReactElement,
          {
            onClick: (e: React.MouseEvent) => {
              const original = (
                children as React.ReactElement<{ onClick?: (e: React.MouseEvent) => void }>
              ).props.onClick;
              original?.(e);
              onToggle?.();
            },
          } as Record<string, unknown>
        );
      }
      return (
        <div data-testid="popover-trigger" onClick={onToggle} {...props}>
          {children}
        </div>
      );
    },
    PopoverContent: ({
      children,
      'data-popover-open': isOpen,
    }: {
      children: React.ReactNode;
      className?: string;
      align?: string;
      sideOffset?: number;
      id?: string;
      'data-popover-open'?: boolean;
    }) => {
      if (!isOpen) return null;
      return <div data-testid="popover-content">{children}</div>;
    },
  };
});

// Mock shadcn/ui Tabs - render all tab contents, show/hide based on value
vi.mock('@/components/ui/tabs', () => {
  const TabsContext = React.createContext<{
    value: string;
    onValueChange?: (v: string) => void;
  }>({ value: 'markdown' });

  return {
    Tabs: ({
      children,
      value,
      onValueChange,
    }: {
      children: React.ReactNode;
      value: string;
      onValueChange?: (value: string) => void;
    }) => (
      <TabsContext.Provider value={{ value, onValueChange }}>
        <div data-testid="tabs-root">{children}</div>
      </TabsContext.Provider>
    ),
    TabsList: ({ children }: { children: React.ReactNode }) => (
      <div role="tablist" data-testid="tabs-list">
        {children}
      </div>
    ),
    TabsTrigger: ({
      children,
      value,
      className,
    }: {
      children: React.ReactNode;
      value: string;
      className?: string;
    }) => {
      const ctx = React.useContext(TabsContext);
      return (
        <button
          role="tab"
          data-state={ctx.value === value ? 'active' : 'inactive'}
          aria-selected={ctx.value === value}
          onClick={() => ctx.onValueChange?.(value)}
          className={className}
        >
          {children}
        </button>
      );
    },
    TabsContent: ({
      children,
      value,
    }: {
      children: React.ReactNode;
      value: string;
      className?: string;
    }) => {
      const ctx = React.useContext(TabsContext);
      if (ctx.value !== value) return null;
      return (
        <div role="tabpanel" data-testid={`tab-content-${value}`}>
          {children}
        </div>
      );
    },
  };
});

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Terminal: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="terminal-icon" className={className as string} {...props} />
  ),
  Copy: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="copy-icon" className={className as string} {...props} />
  ),
  Check: ({ className, ...props }: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="check-icon" className={className as string} {...props} />
  ),
}));

describe('CloneContextPanel', () => {
  const defaultProps: CloneContextPanelProps = {
    onExport: vi.fn().mockResolvedValue('# Exported content\n\nSome tasks here'),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  function renderPanel(props: Partial<CloneContextPanelProps> = {}) {
    return render(<CloneContextPanel {...defaultProps} {...props} />);
  }

  it('renders trigger button with "Clone Context" text', () => {
    renderPanel();
    expect(screen.getByText('Clone Context')).toBeInTheDocument();
  });

  it('disables trigger button when isLoading is true', () => {
    renderPanel({ isLoading: true });
    const button = screen.getByText('Clone Context').closest('button');
    expect(button).toBeDisabled();
  });

  it('opens popover on click and shows tabs', async () => {
    renderPanel();

    const trigger = screen.getByText('Clone Context');
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    expect(screen.getByRole('tab', { name: 'Markdown' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Claude Code' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Task List' })).toBeInTheDocument();
  });

  it('displays 3 tabs: Markdown, Claude Code, Task List', async () => {
    renderPanel();
    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveTextContent('Markdown');
    expect(tabs[1]).toHaveTextContent('Claude Code');
    expect(tabs[2]).toHaveTextContent('Task List');
  });

  it('calls onExport with markdown format when popover opens', async () => {
    const onExport = vi.fn().mockResolvedValue('# Markdown content');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith('markdown');
    });
  });

  it('calls onExport with correct format when tab changes', async () => {
    const onExport = vi.fn().mockResolvedValue('exported content');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith('markdown');
    });

    fireEvent.click(screen.getByRole('tab', { name: 'Claude Code' }));

    await waitFor(() => {
      expect(onExport).toHaveBeenCalledWith('claude_code');
    });
  });

  it('shows preview content after loading', async () => {
    const onExport = vi.fn().mockResolvedValue('Preview content here');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByText('Preview content here')).toBeInTheDocument();
    });
  });

  it('shows loading state while preview loads', async () => {
    let resolveExport: (value: string) => void;
    const onExport = vi.fn().mockReturnValue(
      new Promise<string>((resolve) => {
        resolveExport = resolve;
      })
    );
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByText('Loading preview...')).toBeInTheDocument();
    });

    await act(async () => {
      resolveExport!('Loaded content');
    });

    await waitFor(() => {
      expect(screen.getByText('Loaded content')).toBeInTheDocument();
    });
  });

  it('copy button copies preview to clipboard', async () => {
    const onExport = vi.fn().mockResolvedValue('Content to copy');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByText('Content to copy')).toBeInTheDocument();
    });

    const copyButton = screen.getByRole('button', { name: /copy context/i });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Content to copy');
    });
  });

  it('shows "Copied!" feedback after copy', async () => {
    const onExport = vi.fn().mockResolvedValue('Content to copy');
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByText('Content to copy')).toBeInTheDocument();
    });

    const copyButton = screen.getByRole('button', { name: /copy context/i });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('shows stats when provided', async () => {
    renderPanel({
      stats: {
        tasksCount: 5,
        relatedIssuesCount: 3,
        relatedDocsCount: 2,
      },
    });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    expect(screen.getByText(/5 tasks/)).toBeInTheDocument();
    expect(screen.getByText(/3 issues/)).toBeInTheDocument();
    expect(screen.getByText(/2 docs/)).toBeInTheDocument();
  });

  it('does not show stats section when stats not provided', async () => {
    renderPanel({ stats: undefined });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByTestId('popover-content')).toBeInTheDocument();
    });

    expect(screen.queryByText(/Includes:/)).not.toBeInTheDocument();
  });

  it('shows "No content available" when export returns null', async () => {
    const onExport = vi.fn().mockResolvedValue(null);
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByText('No content available')).toBeInTheDocument();
    });
  });

  it('shows error message when export fails', async () => {
    const onExport = vi.fn().mockRejectedValue(new Error('Export error'));
    renderPanel({ onExport });

    fireEvent.click(screen.getByText('Clone Context'));

    await waitFor(() => {
      expect(screen.getByText('Failed to load preview.')).toBeInTheDocument();
    });
  });

  it('has correct aria-haspopup on trigger button', () => {
    renderPanel();
    const button = screen.getByText('Clone Context').closest('button');
    expect(button).toHaveAttribute('aria-haspopup', 'dialog');
  });
});
