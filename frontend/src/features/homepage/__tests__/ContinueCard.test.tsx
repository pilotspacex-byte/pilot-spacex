/**
 * Phase 88 Plan 04 — Task 2: ContinueCard (RED).
 * E-02 Path B revision — empty/loading branches now render a 96px dashed
 * placeholder instead of `return null`, preserving launchpad rhythm and
 * giving new users a clear hint about what this surface is for.
 *
 * Component contract (PLAN §interfaces + E-02):
 *   <ContinueCard workspaceId workspaceSlug />
 *
 * Render branches:
 *   - useLastChatSession returns null → renders the
 *     `continue-card-empty` placeholder (role="status").
 *   - Loading → same placeholder.
 *   - Session present → renders an <a> link to /{slug}/chat?session={id}
 *     with section label, title, 1-line truncated preview, timestamp, and
 *     up to 3 artifact pills.
 *   - aria-label format: "Continue chat: {title}, last active {timeAgo}".
 *   - Artifact pills are aria-hidden="true".
 *   - Error from hook → hook returns null on errors, so the placeholder
 *     branch covers that path too.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';

// next/link mock — we just want a plain <a>.
vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

// Hook mock. Tests mutate the value before each render.
type LastSessionHookReturn = {
  session: {
    id: string;
    title: string;
    lastMessagePreview: string;
    lastMessageAt: string;
    artifacts: Array<{ kind: string; label: string; id: string }>;
  } | null;
  isLoading: boolean;
};
const sessionMock: LastSessionHookReturn = { session: null, isLoading: false };
vi.mock('../hooks/use-last-chat-session', () => ({
  useLastChatSession: () => sessionMock,
}));

import { ContinueCard } from '../components/ContinueCard';

beforeEach(() => {
  sessionMock.session = null;
  sessionMock.isLoading = false;
});

afterEach(() => cleanup());

describe('ContinueCard (Phase 88 Plan 04 — Task 2)', () => {
  it('renders the empty-state placeholder when session is null', () => {
    sessionMock.session = null;
    render(<ContinueCard workspaceId="ws-1" workspaceSlug="workspace" />);

    const placeholder = screen.getByTestId('continue-card-empty');
    expect(placeholder).toBeInTheDocument();
    expect(placeholder).toHaveAttribute('role', 'status');
    // Hint copy + section label both present so users know what this is.
    expect(screen.getByText(/your first chat will land here/i)).toBeInTheDocument();
    expect(screen.getByText(/continue where you left off/i)).toBeInTheDocument();
    // Same 96px height + dashed border so layout doesn't shift later.
    expect(placeholder.className).toMatch(/h-24/);
    expect(placeholder.className).toMatch(/border-dashed/);
    // No <a href> link rendered in empty mode.
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('renders the empty-state placeholder while loading', () => {
    sessionMock.session = null;
    sessionMock.isLoading = true;
    render(<ContinueCard workspaceId="ws-1" workspaceSlug="workspace" />);

    expect(screen.getByTestId('continue-card-empty')).toBeInTheDocument();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('renders link with session href and aria-label when session present (no pills)', () => {
    sessionMock.session = {
      id: 'sess-abc',
      title: 'Q3 planning thread',
      lastMessagePreview: 'discussed roadmap risks',
      lastMessageAt: new Date(Date.now() - 60_000).toISOString(), // 1 min ago
      artifacts: [],
    };

    render(<ContinueCard workspaceId="ws-1" workspaceSlug="workspace" />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/workspace/chat?session=sess-abc');
    // aria-label format: "Continue chat: {title}, last active {timeAgo}"
    expect(link.getAttribute('aria-label')).toMatch(
      /^Continue chat: Q3 planning thread, last active /,
    );
    // Title visible
    expect(screen.getByText('Q3 planning thread')).toBeInTheDocument();
    // Preview visible
    expect(screen.getByText('discussed roadmap risks')).toBeInTheDocument();
  });

  it('renders up to 3 artifact pills (aria-hidden)', () => {
    sessionMock.session = {
      id: 'sess-abc',
      title: 'Sprint review',
      lastMessagePreview: 'wrapping up the sprint',
      lastMessageAt: new Date(Date.now() - 120_000).toISOString(),
      artifacts: [
        { kind: 'ISSUE', label: 'PS-12', id: 'i1' },
        { kind: 'NOTE', label: 'Retro notes', id: 'n1' },
        { kind: 'SPEC', label: 'Sprint spec', id: 's1' },
      ],
    };

    render(<ContinueCard workspaceId="ws-1" workspaceSlug="workspace" />);

    expect(screen.getByText('PS-12')).toBeInTheDocument();
    expect(screen.getByText('Retro notes')).toBeInTheDocument();
    expect(screen.getByText('Sprint spec')).toBeInTheDocument();

    // Pills are aria-hidden.
    const pillContainer = screen.getByTestId('continue-card-pills');
    expect(pillContainer).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders the section label "Continue where you left off" (CSS uppercase)', () => {
    sessionMock.session = {
      id: 'sess-abc',
      title: 'Random title',
      lastMessagePreview: '',
      lastMessageAt: new Date().toISOString(),
      artifacts: [],
    };

    render(<ContinueCard workspaceId="ws-1" workspaceSlug="workspace" />);

    // Visual uppercasing comes from `uppercase` CSS class — assert the
    // underlying text + the class so the test survives a non-CSS render.
    const label = screen.getByText(/continue where you left off/i);
    expect(label).toBeInTheDocument();
    expect(label.className).toMatch(/uppercase/);
  });
});
