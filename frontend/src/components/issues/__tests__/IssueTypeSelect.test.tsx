/**
 * IssueTypeSelect component tests (T022).
 *
 * Verifies dropdown renders current value, shows all 4 types,
 * calls onChange, respects disabled state, and shows correct icons.
 */

import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IssueTypeSelect } from '../IssueTypeSelect';
import type { IssueType } from '@/types';

// ---------------------------------------------------------------------------
// Mocks - Radix DropdownMenu is portal-based, mock for testability
// ---------------------------------------------------------------------------

vi.mock('@/components/ui/dropdown-menu', () => {
  return {
    DropdownMenu: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
    DropdownMenuTrigger: ({ children }: { children: React.ReactNode; asChild?: boolean }) => (
      <div data-testid="dropdown-trigger">{children}</div>
    ),
    DropdownMenuContent: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="dropdown-content">{children}</div>
    ),
    DropdownMenuItem: ({
      children,
      onClick,
      className,
    }: {
      children: React.ReactNode;
      onClick?: () => void;
      className?: string;
    }) => (
      <button data-testid="dropdown-item" onClick={onClick} className={className}>
        {children}
      </button>
    ),
  };
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('IssueTypeSelect', () => {
  const defaultOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders current value label', () => {
    render(<IssueTypeSelect value="bug" onChange={defaultOnChange} />);
    const trigger = screen.getByTestId('dropdown-trigger');
    expect(within(trigger).getByText('Bug')).toBeInTheDocument();
  });

  it('renders current value for feature type', () => {
    render(<IssueTypeSelect value="feature" onChange={defaultOnChange} />);
    const trigger = screen.getByTestId('dropdown-trigger');
    expect(within(trigger).getByText('Feature')).toBeInTheDocument();
  });

  it('renders current value for improvement type', () => {
    render(<IssueTypeSelect value="improvement" onChange={defaultOnChange} />);
    const trigger = screen.getByTestId('dropdown-trigger');
    expect(within(trigger).getByText('Improvement')).toBeInTheDocument();
  });

  it('renders current value for task type', () => {
    render(<IssueTypeSelect value="task" onChange={defaultOnChange} />);
    const trigger = screen.getByTestId('dropdown-trigger');
    expect(within(trigger).getByText('Task')).toBeInTheDocument();
  });

  it('shows all 4 types in the dropdown content', () => {
    render(<IssueTypeSelect value="bug" onChange={defaultOnChange} />);

    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    expect(items).toHaveLength(4);
    expect(within(content).getByText('Bug')).toBeInTheDocument();
    expect(within(content).getByText('Feature')).toBeInTheDocument();
    expect(within(content).getByText('Improvement')).toBeInTheDocument();
    expect(within(content).getByText('Task')).toBeInTheDocument();
  });

  it('calls onChange when selecting a different type', () => {
    render(<IssueTypeSelect value="bug" onChange={defaultOnChange} />);

    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    // Click 'Feature' (second item)
    fireEvent.click(items.at(1)!);
    expect(defaultOnChange).toHaveBeenCalledWith('feature');
  });

  it('calls onChange with correct type for each option', () => {
    render(<IssueTypeSelect value="task" onChange={defaultOnChange} />);

    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    const expectedTypes: IssueType[] = ['bug', 'feature', 'improvement', 'task'];
    items.forEach((item, index) => {
      fireEvent.click(item);
      expect(defaultOnChange).toHaveBeenCalledWith(expectedTypes[index]);
    });

    expect(defaultOnChange).toHaveBeenCalledTimes(4);
  });

  it('disabled state prevents interaction', () => {
    render(<IssueTypeSelect value="bug" onChange={defaultOnChange} disabled />);

    const trigger = screen.getByTestId('dropdown-trigger');
    const button = within(trigger).getByRole('button');
    expect(button).toBeDisabled();
  });

  it('each type shows correct icon via SVG elements', () => {
    render(<IssueTypeSelect value="bug" onChange={defaultOnChange} />);

    // Each dropdown item should render an SVG icon
    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    items.forEach((item) => {
      const svg = item.querySelector('svg');
      expect(svg).toBeTruthy();
    });
  });

  it('applies custom className', () => {
    render(<IssueTypeSelect value="bug" onChange={defaultOnChange} className="custom-class" />);

    const trigger = screen.getByTestId('dropdown-trigger');
    const button = within(trigger).getByRole('button');
    expect(button.className).toContain('custom-class');
  });

  it('highlights selected item with bg-accent class', () => {
    render(<IssueTypeSelect value="feature" onChange={defaultOnChange} />);

    const content = screen.getByTestId('dropdown-content');
    const items = within(content).getAllByTestId('dropdown-item');

    // Feature is index 1
    expect(items.at(1)!.className).toContain('bg-accent');
    // Others should not have bg-accent
    expect(items.at(0)!.className).not.toContain('bg-accent');
  });
});
