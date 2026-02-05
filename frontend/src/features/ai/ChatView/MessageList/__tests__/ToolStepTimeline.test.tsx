/**
 * Unit tests for ToolStepTimeline component.
 *
 * Tests vertical step timeline rendering for messages with 3+ tool calls,
 * status-based circle styling, display names, durations, and accessibility.
 *
 * @module features/ai/ChatView/MessageList/__tests__/ToolStepTimeline
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock useElapsedTime for running tool elapsed time
vi.mock('@/hooks/useElapsedTime', () => ({
  useElapsedTime: vi.fn(() => '2.1s'),
}));

// Mock lucide-react icons with data-testid for assertion
vi.mock('lucide-react', () => ({
  Check: (props: Record<string, unknown>) => <span data-testid="check-icon" {...props} />,
  X: (props: Record<string, unknown>) => <span data-testid="x-icon" {...props} />,
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader2-icon" {...props} />,
}));

import { useElapsedTime } from '@/hooks/useElapsedTime';
import { ToolStepTimeline } from '../ToolStepTimeline';
import type { ToolCall } from '@/stores/ai/types/conversation';

const mockUseElapsedTime = vi.mocked(useElapsedTime);

function makeToolCall(overrides: Partial<ToolCall> = {}): ToolCall {
  return {
    id: 'tc-1',
    name: 'extract_issues',
    input: {},
    status: 'pending',
    ...overrides,
  };
}

describe('ToolStepTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseElapsedTime.mockReturnValue('2.1s');
  });

  // ========================================
  // Threshold: renders nothing when < 3 tool calls
  // ========================================

  it('renders nothing when toolCalls is empty', () => {
    const { container } = render(<ToolStepTimeline toolCalls={[]} />);

    expect(container.firstElementChild).toBeNull();
  });

  it('renders nothing when toolCalls has 1 item', () => {
    const { container } = render(<ToolStepTimeline toolCalls={[makeToolCall()]} />);

    expect(container.firstElementChild).toBeNull();
  });

  it('renders nothing when toolCalls has 2 items', () => {
    const { container } = render(
      <ToolStepTimeline toolCalls={[makeToolCall({ id: 'tc-1' }), makeToolCall({ id: 'tc-2' })]} />
    );

    expect(container.firstElementChild).toBeNull();
  });

  // ========================================
  // Renders step circles for 3+ tool calls
  // ========================================

  it('renders numbered step circles for each tool call', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    const listItems = screen.getAllByRole('listitem');
    expect(listItems).toHaveLength(3);
  });

  // ========================================
  // Completed steps: green checkmark circle
  // ========================================

  it('renders completed steps with green checkmark circle', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({
        id: 'tc-3',
        name: 'create_issue_from_note',
        status: 'completed',
        durationMs: 500,
      }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    const checkIcons = screen.getAllByTestId('check-icon');
    expect(checkIcons).toHaveLength(3);

    // Check icons should have white text color
    checkIcons.forEach((icon) => {
      expect(icon.className).toContain('text-white');
    });
  });

  // ========================================
  // Running steps: spinning loader indicator
  // ========================================

  it('renders running steps with spinning Loader2 indicator', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    // The last tool is "pending" but it's the first non-completed, treated as running
    // based on the component logic. However, the ToolCall type uses 'pending' for both
    // waiting and running states. The component distinguishes by checking if it's the
    // first pending tool (running) vs subsequent (waiting).
    // For this test, we need a tool that is actively running.
    // The status field doesn't have a 'running' value, so we test the 'pending' status
    // which shows the spinner when it's the active tool.

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    const loaderIcon = screen.getByTestId('loader2-icon');
    expect(loaderIcon).toBeInTheDocument();
    expect(loaderIcon.className).toContain('animate-spin');
  });

  // ========================================
  // Failed steps: red X circle
  // ========================================

  it('renders failed steps with red X circle', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({
        id: 'tc-2',
        name: 'extract_issues',
        status: 'failed',
        errorMessage: 'timeout',
      }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    const xIcon = screen.getByTestId('x-icon');
    expect(xIcon).toBeInTheDocument();
    expect(xIcon.className).toContain('text-white');
  });

  // ========================================
  // Pending steps: muted hollow circle
  // ========================================

  it('renders pending steps with muted hollow circle (no icon)', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
      makeToolCall({ id: 'tc-4', name: 'link_existing_issues', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    // The first pending tool (tc-3) shows spinner (running),
    // the second pending tool (tc-4) shows hollow circle (waiting).
    // Hollow circle has no icon inside, just border styling.
    const listItems = screen.getAllByRole('listitem');
    expect(listItems).toHaveLength(4);

    // Last item (tc-4) should be truly pending (hollow), no icon
    const lastItem = listItems[3]!;
    expect(lastItem.querySelector('[data-testid="check-icon"]')).toBeNull();
    expect(lastItem.querySelector('[data-testid="x-icon"]')).toBeNull();
    expect(lastItem.querySelector('[data-testid="loader2-icon"]')).toBeNull();
  });

  // ========================================
  // Vertical connecting line
  // ========================================

  it('renders vertical connecting line between steps', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    const { container } = render(<ToolStepTimeline toolCalls={toolCalls} />);

    // Non-last items should have a connecting line segment (border-l-2)
    const connectors = container.querySelectorAll('.border-l-2.border-l-border-subtle');
    expect(connectors.length).toBeGreaterThan(0);
  });

  // ========================================
  // Display names
  // ========================================

  it('shows mapped display name per step', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    expect(screen.getByText('Summarizing Note')).toBeInTheDocument();
    expect(screen.getByText('Extracting Issues')).toBeInTheDocument();
    expect(screen.getByText('Creating Issue')).toBeInTheDocument();
  });

  // ========================================
  // Duration badge for completed tools
  // ========================================

  it('shows duration badge for completed tools', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    expect(screen.getByText('0.8s')).toBeInTheDocument();
    expect(screen.getByText('1.2s')).toBeInTheDocument();
  });

  it('shows elapsed time for the running (first pending) tool', () => {
    mockUseElapsedTime.mockReturnValue('3.5s');

    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    expect(screen.getByText('3.5s')).toBeInTheDocument();
  });

  // ========================================
  // Accessibility
  // ========================================

  it('renders as ordered list with aria-label "Tool execution steps"', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    const list = screen.getByRole('list');
    expect(list.tagName).toBe('OL');
    expect(list).toHaveAttribute('aria-label', 'Tool execution steps');
  });

  it('each step has aria-label with tool name and status', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'failed', errorMessage: 'err' }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    render(<ToolStepTimeline toolCalls={toolCalls} />);

    const listItems = screen.getAllByRole('listitem');
    expect(listItems[0]).toHaveAttribute('aria-label', 'Summarizing Note — completed');
    expect(listItems[1]).toHaveAttribute('aria-label', 'Extracting Issues — failed');
    expect(listItems[2]).toHaveAttribute('aria-label', 'Creating Issue — running');
  });

  // ========================================
  // className forwarding
  // ========================================

  it('forwards className to root element', () => {
    const toolCalls = [
      makeToolCall({ id: 'tc-1', name: 'summarize_note', status: 'completed', durationMs: 800 }),
      makeToolCall({ id: 'tc-2', name: 'extract_issues', status: 'completed', durationMs: 1200 }),
      makeToolCall({ id: 'tc-3', name: 'create_issue_from_note', status: 'pending' }),
    ];

    const { container } = render(
      <ToolStepTimeline toolCalls={toolCalls} className="extra-class" />
    );

    expect(container.firstElementChild?.className).toContain('extra-class');
  });
});
