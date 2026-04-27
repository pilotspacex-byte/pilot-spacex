/**
 * Phase 88 Plan 02 — Task 4: Launchpad assembly smoke + integration.
 * Phase 88 Plan 04 — Task 4: extended to wire RedFlagStrip + ContinueCard.
 *
 * Smoke + integration tests:
 *  - Renders <section role="main" aria-label="Workspace launchpad">.
 *  - Greeting (h1) is present.
 *  - Composer (data-testid="chat-input") is present.
 *  - Suggested-prompts group is present with 4 chips.
 *  - Clicking the first chip populates the composer textarea via
 *    composerRef.current.setDraft (integration across Tasks 1–3).
 *  - With both useRedFlags + useLastChatSession returning empty: only
 *    greeting/composer/chips render. The two slot wrappers stay (mt-8)
 *    but their children render null (rhythm collapses).
 *  - With both populated: greeting + composer + RedFlagStrip banners +
 *    chips + ContinueCard all render in correct DOM order.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: (component: unknown) => component,
}));

const pushSpy = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushSpy }),
  useParams: () => ({ workspaceSlug: 'workspace' }),
}));

const authMock: {
  user: { email: string; name: string } | null;
  userDisplayName: string;
} = {
  user: { email: 'tin@pilot.space', name: 'Tin Dang' },
  userDisplayName: 'Tin Dang',
};
vi.mock('@/stores', () => ({
  useAuthStore: () => authMock,
}));

const modeMock: { mode: 'plan' | 'act' | 'research' | 'draft' } = { mode: 'plan' };
vi.mock('@/stores/ai', () => ({
  getAIStore: () => ({
    pilotSpace: {
      getMode: () => modeMock.mode,
      setMode: (_id: string, mode: 'plan' | 'act' | 'research' | 'draft') => {
        modeMock.mode = mode;
      },
      sendMessage: vi.fn(),
    },
  }),
}));

// ChatInput dependency mocks
vi.mock('@/features/ai/ChatView/hooks/useSkills', () => ({
  useSkills: () => ({ skills: [] }),
}));
vi.mock('@/features/ai/ChatView/hooks/useAttachments', () => ({
  useAttachments: () => ({
    attachments: [],
    attachmentIds: [],
    addFile: vi.fn(),
    addFromDrive: vi.fn(),
    removeFile: vi.fn(),
    reset: vi.fn(),
  }),
}));
vi.mock('@/features/ai/ChatView/hooks/useDriveStatus', () => ({
  useDriveStatus: () => ({ data: null }),
}));
vi.mock('@/services/api/attachments', () => ({
  attachmentsApi: { getDriveAuthUrl: vi.fn() },
}));
vi.mock('@/features/ai/ChatView/ChatInput/RecordButton', () => ({
  RecordButton: () => null,
}));
vi.mock('@/features/ai/ChatView/ChatInput/AudioPlaybackPill', () => ({
  AudioPlaybackPill: () => null,
}));
vi.mock('@/features/ai/ChatView/hooks/useRecentEntities', () => ({
  useRecentEntities: () => ({ recentEntities: [], addEntity: vi.fn() }),
}));
vi.mock('@/features/ai/ChatView/ChatInput/EntityPicker', () => ({
  EntityPicker: () => null,
}));

// Phase 88 Plan 04 — wire RedFlagStrip + ContinueCard into Launchpad. The
// two child hooks are mocked at the module boundary so the smoke test stays
// quiet by default (no banners, no card → identical to the Plan 02
// baseline). The "both populated" integration test mutates the controllers
// before render.
type RedFlagsHookReturn = {
  flags: Array<{ kind: 'stale' | 'sprint' | 'digest'; label: string; href: string; ariaLabel: string }>;
  isLoading: boolean;
  isError: boolean;
};
const redFlagsMock: RedFlagsHookReturn = { flags: [], isLoading: false, isError: false };
vi.mock('../hooks/use-red-flags', () => ({
  useRedFlags: () => redFlagsMock,
}));

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
const lastSessionMock: LastSessionHookReturn = { session: null, isLoading: false };
vi.mock('../hooks/use-last-chat-session', () => ({
  useLastChatSession: () => lastSessionMock,
}));

// next/link → plain anchor (RedFlagStrip + ContinueCard both use it).
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

import { Launchpad } from '../Launchpad';

beforeEach(() => {
  pushSpy.mockReset();
  modeMock.mode = 'plan';
  // Reset Plan-04 hook controllers to "empty" baseline.
  redFlagsMock.flags = [];
  redFlagsMock.isLoading = false;
  redFlagsMock.isError = false;
  lastSessionMock.session = null;
  lastSessionMock.isLoading = false;

  Element.prototype.scrollIntoView = vi.fn();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

afterEach(() => cleanup());

describe('Launchpad (Phase 88 Plan 02 — assembly smoke + integration)', () => {
  it('renders the main landmark with the launchpad aria-label', () => {
    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);
    const main = screen.getByRole('main', { name: 'Workspace launchpad' });
    expect(main).toBeInTheDocument();
  });

  it('renders the greeting h1', () => {
    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1).toHaveTextContent(/Good (morning|afternoon|evening), Tin\./);
  });

  it('renders the composer (data-testid="chat-input")', () => {
    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
  });

  it('renders the suggested-prompts group with 4 chips', () => {
    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);
    const group = screen.getByRole('group', { name: 'Suggested prompts' });
    expect(group).toBeInTheDocument();
    // The composer is a contenteditable div, not a button — the only buttons
    // inside the launchpad come from SuggestedPromptsRow (slimToolbar hides
    // the ChatInput menu cluster).
    const chips = screen.getAllByRole('button');
    expect(chips).toHaveLength(4);
  });

  it('clicking the first chip populates the composer with that prompt text', async () => {
    const user = userEvent.setup();
    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);

    const chip = screen.getByRole('button', {
      name: 'Use prompt: Draft a standup for me',
    });
    await user.click(chip);

    // ChatInput syncs DOM from value via useEffect — wait one tick.
    await new Promise((r) => setTimeout(r, 5));

    const input = screen.getByTestId('chat-input');
    expect(input.textContent).toBe('Draft a standup for me');
  });

  // ── Phase 88 Plan 04 — wired children ───────────────────────────────────

  it('with empty hooks: chip buttons render alongside the calm empty-state placeholders (E-02 Path B)', () => {
    // Default beforeEach state — empty hooks.
    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);

    const chips = screen.getAllByRole('button');
    expect(chips).toHaveLength(4);
    // No banner region landmark (that's reserved for actual flag content).
    expect(screen.queryByRole('region', { name: 'Workspace alerts' })).toBeNull();
    // No continue card link (link only renders when a session exists).
    expect(screen.queryByRole('link', { name: /Continue chat:/i })).toBeNull();

    // E-02 Path B — placeholders preserve vertical rhythm. Both surfaces
    // render their muted skeletal hint.
    const flagPlaceholder = screen.getByTestId('red-flag-strip-empty');
    const continuePlaceholder = screen.getByTestId('continue-card-empty');
    expect(flagPlaceholder).toBeInTheDocument();
    expect(continuePlaceholder).toBeInTheDocument();
    // Both use dashed borders so they read as "skeletal" not active.
    expect(flagPlaceholder.className).toMatch(/border-dashed/);
    expect(continuePlaceholder.className).toMatch(/border-dashed/);
  });

  it('placeholders sit in DOM order between composer/chips and after chips (rhythm holds when empty)', () => {
    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);

    const composer = screen.getByTestId('chat-input');
    const flagPlaceholder = screen.getByTestId('red-flag-strip-empty');
    const chips = screen.getByRole('group', { name: 'Suggested prompts' });
    const continuePlaceholder = screen.getByTestId('continue-card-empty');

    // Order: composer → red-flag placeholder → chips → continue placeholder.
    const order = [composer, flagPlaceholder, chips, continuePlaceholder];
    for (let i = 0; i < order.length - 1; i++) {
      const followsFlag = Node.DOCUMENT_POSITION_FOLLOWING;
      expect(order[i]!.compareDocumentPosition(order[i + 1]!) & followsFlag).toBeTruthy();
    }
  });

  it('with both hooks populated: greeting + composer + banners + chips + continue card all render in DOM order', () => {
    redFlagsMock.flags = [
      {
        kind: 'stale',
        label: '2 stale tasks',
        href: '/workspace/tasks?filter=stale',
        ariaLabel: '2 stale tasks. Open.',
      },
    ];
    lastSessionMock.session = {
      id: 'sess-xyz',
      title: 'Q3 planning thread',
      lastMessagePreview: 'last preview',
      lastMessageAt: new Date(Date.now() - 60_000).toISOString(),
      artifacts: [],
    };

    render(<Launchpad workspaceId="ws-1" workspaceSlug="workspace" />);

    // Greeting present.
    const h1 = screen.getByRole('heading', { level: 1 });
    expect(h1).toBeInTheDocument();
    // Composer present.
    const composer = screen.getByTestId('chat-input');
    expect(composer).toBeInTheDocument();
    // Banners region present.
    const banners = screen.getByRole('region', { name: 'Workspace alerts' });
    expect(banners).toBeInTheDocument();
    // Chips group present.
    const chips = screen.getByRole('group', { name: 'Suggested prompts' });
    expect(chips).toBeInTheDocument();
    // Continue card link present.
    const card = screen.getByRole('link', { name: /Continue chat: Q3 planning thread/i });
    expect(card).toBeInTheDocument();

    // DOM order check via documentPosition: greeting → composer → banners
    // → chips → continue card.
    const order = [h1, composer, banners, chips, card];
    for (let i = 0; i < order.length - 1; i++) {
      const followsFlag = Node.DOCUMENT_POSITION_FOLLOWING;
      expect(order[i]!.compareDocumentPosition(order[i + 1]!) & followsFlag).toBeTruthy();
    }
  });
});
