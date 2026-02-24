/**
 * Unit tests for NoteHealthBadges component.
 *
 * @module components/editor/__tests__/NoteHealthBadges.test
 * @see T024
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NoteHealthBadges } from '../NoteHealthBadges';
import type { NoteHealthData } from '@/hooks/useNoteHealth';
import type { LinkedIssueBrief } from '@/types';

// Mock Tooltip components — render children directly
vi.mock('@/components/ui/tooltip', () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({
    children,
    asChild: _asChild,
  }: {
    children: React.ReactNode;
    asChild?: boolean;
  }) => <>{children}</>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="tooltip-content">{children}</div>
  ),
}));

const LINKED_ISSUES: LinkedIssueBrief[] = [
  {
    id: '1',
    identifier: 'PS-42',
    name: 'Fix login',
    priority: 'high' as const,
    state: { id: 's1', name: 'In Progress', group: 'started', color: '#000' },
  },
  {
    id: '2',
    identifier: 'PS-55',
    name: 'Add dark mode',
    priority: 'medium' as const,
    state: { id: 's2', name: 'Todo', group: 'unstarted', color: '#999' },
  },
];

function createHealth(overrides: Partial<NoteHealthData> = {}): NoteHealthData {
  return {
    extractableCount: 0,
    clarityIssueCount: 0,
    linkedIssues: [],
    suggestedPrompts: [],
    isComputing: false,
    ...overrides,
  };
}

describe('NoteHealthBadges', () => {
  const mockSendMessage = vi.fn();
  const mockOnOpenChat = vi.fn();

  const mockPilotSpaceStore = {
    sendMessage: mockSendMessage,
  } as unknown as import('@/stores/ai/PilotSpaceStore').PilotSpaceStore;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockSendMessage.mockClear();
    mockOnOpenChat.mockClear();
  });

  it('renders nothing when all counts are 0', () => {
    const { container } = render(
      <NoteHealthBadges
        health={createHealth()}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders extractable badge when extractableCount > 0', () => {
    render(
      <NoteHealthBadges
        health={createHealth({ extractableCount: 3 })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    const badge = screen.getByTestId('badge-extractable');
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain('3 extractable');
  });

  it('renders clarity badge when clarityIssueCount > 0', () => {
    render(
      <NoteHealthBadges
        health={createHealth({ clarityIssueCount: 2 })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    const badge = screen.getByTestId('badge-clarity');
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain('2 need clarity');
  });

  it('renders linked issues badge with identifiers', () => {
    render(
      <NoteHealthBadges
        health={createHealth({ linkedIssues: LINKED_ISSUES })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    const badge = screen.getByTestId('badge-linked');
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain('PS-42');
    expect(badge.textContent).toContain('PS-55');
  });

  it('hides extractable badge when count is 0', () => {
    render(
      <NoteHealthBadges
        health={createHealth({ clarityIssueCount: 1 })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    expect(screen.queryByTestId('badge-extractable')).toBeNull();
  });

  it('sends extract message on extractable badge click', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(
      <NoteHealthBadges
        health={createHealth({ extractableCount: 2 })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    await user.click(screen.getByTestId('badge-extractable'));

    expect(mockOnOpenChat).toHaveBeenCalledTimes(1);

    // Wait for setTimeout(100ms) inside handleBadgeClick
    vi.advanceTimersByTime(100);

    expect(mockSendMessage).toHaveBeenCalledWith('Extract 2 actionable items as issues');
  });

  it('sends clarity message on clarity badge click', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(
      <NoteHealthBadges
        health={createHealth({ clarityIssueCount: 3 })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    await user.click(screen.getByTestId('badge-clarity'));

    expect(mockOnOpenChat).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(100);

    expect(mockSendMessage).toHaveBeenCalledWith('Improve clarity in 3 sections');
  });

  it('sends linked issues message on linked badge click', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    render(
      <NoteHealthBadges
        health={createHealth({ linkedIssues: LINKED_ISSUES })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    await user.click(screen.getByTestId('badge-linked'));

    expect(mockOnOpenChat).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(100);

    expect(mockSendMessage).toHaveBeenCalledWith('Summarize progress on 2 linked issues');
  });

  it('collapses to single chip on mobile when isSmallScreen', () => {
    render(
      <NoteHealthBadges
        health={createHealth({ extractableCount: 2, clarityIssueCount: 1 })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
        isSmallScreen
      />
    );

    // No individual badges
    expect(screen.queryByTestId('badge-extractable')).toBeNull();
    expect(screen.queryByTestId('badge-clarity')).toBeNull();

    // Single collapsed chip with total count
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(1);
    expect(buttons[0]!.textContent).toContain('3 items');
  });

  it('truncates linked issues to first 3 identifiers', () => {
    const manyIssues: LinkedIssueBrief[] = [
      ...LINKED_ISSUES,
      {
        id: '3',
        identifier: 'PS-66',
        name: 'Third',
        priority: 'low' as const,
        state: { id: 's3', name: 'Backlog', group: 'backlog', color: '#ccc' },
      },
      {
        id: '4',
        identifier: 'PS-77',
        name: 'Fourth',
        priority: 'low' as const,
        state: { id: 's4', name: 'Backlog', group: 'backlog', color: '#ccc' },
      },
    ];

    render(
      <NoteHealthBadges
        health={createHealth({ linkedIssues: manyIssues })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    const badge = screen.getByTestId('badge-linked');
    expect(badge.textContent).toContain('PS-42');
    expect(badge.textContent).toContain('PS-55');
    expect(badge.textContent).toContain('PS-66');
    expect(badge.textContent).toContain('+1');
    expect(badge.textContent).not.toContain('PS-77');
  });

  it('renders all three badges when all counts > 0', () => {
    render(
      <NoteHealthBadges
        health={createHealth({
          extractableCount: 1,
          clarityIssueCount: 1,
          linkedIssues: LINKED_ISSUES,
        })}
        pilotSpaceStore={mockPilotSpaceStore}
        onOpenChat={mockOnOpenChat}
      />
    );

    expect(screen.getByTestId('badge-extractable')).toBeDefined();
    expect(screen.getByTestId('badge-clarity')).toBeDefined();
    expect(screen.getByTestId('badge-linked')).toBeDefined();
  });
});
