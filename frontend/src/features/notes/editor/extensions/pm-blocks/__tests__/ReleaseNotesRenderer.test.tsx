/**
 * Tests for ReleaseNotesRenderer component.
 *
 * ReleaseNotesRenderer renders release notes PM block with:
 * - Category sections (feature/improvement/bug/chore) (FR-054)
 * - Human-edit filter toggle (FR-055)
 * - AI confidence percentage per entry
 * - Empty state handling
 * - AI insight badge (FR-056–059)
 *
 * @module pm-blocks/__tests__/ReleaseNotesRenderer.test
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';

import { ReleaseNotesRenderer } from '../renderers/ReleaseNotesRenderer';
import type { ReleaseNotesData } from '@/services/api/pm-blocks';

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('@/services/api/pm-blocks', () => ({
  pmBlocksApi: {
    getReleaseNotes: vi.fn(),
    listInsights: vi.fn(),
    dismissInsight: vi.fn(),
  },
}));

import { pmBlocksApi } from '@/services/api/pm-blocks';
const mockGetReleaseNotes = vi.mocked(pmBlocksApi.getReleaseNotes);
const mockListInsights = vi.mocked(pmBlocksApi.listInsights);

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={makeQueryClient()}>{children}</QueryClientProvider>;
}

const WORKSPACE_ID = 'ws-123';
const CYCLE_ID = 'cycle-456';

const defaultProps = {
  data: { workspaceId: WORKSPACE_ID, cycleId: CYCLE_ID } as Record<string, unknown>,
  readOnly: false,
  onDataChange: vi.fn(),
  blockType: 'release-notes' as const,
};

function makeNotesData(overrides: Partial<ReleaseNotesData> = {}): ReleaseNotesData {
  return {
    cycleId: CYCLE_ID,
    versionLabel: 'v1.2.0',
    generatedAt: '2025-01-15T10:00:00Z',
    entries: [
      {
        issueId: 'issue-1',
        identifier: 'PS-1',
        name: 'Add dark mode support',
        category: 'feature',
        confidence: 0.92,
        humanEdited: false,
      },
      {
        issueId: 'issue-2',
        identifier: 'PS-2',
        name: 'Fix login redirect bug',
        category: 'bug',
        confidence: 0.88,
        humanEdited: true,
      },
      {
        issueId: 'issue-3',
        identifier: 'PS-3',
        name: 'Upgrade dependencies',
        category: 'chore',
        confidence: 0.75,
        humanEdited: false,
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockListInsights.mockResolvedValue([]);
});

// ── Config missing ────────────────────────────────────────────────────────────

describe('ReleaseNotesRenderer config missing', () => {
  it('shows config prompt when workspaceId missing', () => {
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <ReleaseNotesRenderer
          {...defaultProps}
          data={{ cycleId: CYCLE_ID } as Record<string, unknown>}
        />
      </QueryClientProvider>
    );
    expect(screen.getByText(/Configure workspace and cycle/i)).toBeInTheDocument();
  });
});

// ── Loading ───────────────────────────────────────────────────────────────────

describe('ReleaseNotesRenderer loading', () => {
  it('shows loading while fetching', async () => {
    mockGetReleaseNotes.mockReturnValue(new Promise(() => {}));
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <ReleaseNotesRenderer {...defaultProps} />
      </QueryClientProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Generating release notes/i)).toBeInTheDocument();
    });
  });
});

// ── Category sections (FR-054) ────────────────────────────────────────────────

describe('ReleaseNotesRenderer category sections (FR-054)', () => {
  it('renders testid for release notes block', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('release-notes-renderer')).toBeInTheDocument();
    });
  });

  it('renders version label in header', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('v1.2.0')).toBeInTheDocument();
    });
  });

  it('renders New Features category section', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('New Features')).toBeInTheDocument();
    });
  });

  it('renders Bug Fixes category section', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Bug Fixes')).toBeInTheDocument();
    });
  });

  it('renders Maintenance category section', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Maintenance')).toBeInTheDocument();
    });
  });

  it('renders issue identifiers', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('PS-1')).toBeInTheDocument();
      expect(screen.getByText('PS-2')).toBeInTheDocument();
    });
  });

  it('renders entry names', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Add dark mode support')).toBeInTheDocument();
    });
  });

  it('renders total issue count', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/3 issues classified/)).toBeInTheDocument();
    });
  });

  it('renders confidence percentage', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      // 0.92 → 92%
      expect(screen.getByLabelText('AI confidence 92%')).toBeInTheDocument();
    });
  });
});

// ── Human edit filter (FR-055) ────────────────────────────────────────────────

describe('ReleaseNotesRenderer human edit filter (FR-055)', () => {
  it('shows "Edited only" toggle when human edits exist', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByLabelText('Show only manually edited entries')).toBeInTheDocument();
    });
  });

  it('shows "1 manually edited" count', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/1 manually edited/)).toBeInTheDocument();
    });
  });

  it('filters to human-edited entries only when toggle pressed', async () => {
    const user = userEvent.setup();
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('PS-1')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('Show only manually edited entries'));

    // PS-2 is human edited, PS-1 and PS-3 are not
    expect(screen.queryByText('PS-1')).not.toBeInTheDocument();
    expect(screen.getByText('PS-2')).toBeInTheDocument();
    expect(screen.queryByText('PS-3')).not.toBeInTheDocument();
  });

  it('shows "Edited" label on human-edited entries', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Edited')).toBeInTheDocument();
    });
  });

  it('does not show edited filter toggle when readOnly', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData());
    render(
      <QueryClientProvider client={makeQueryClient()}>
        <ReleaseNotesRenderer {...defaultProps} readOnly />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.queryByLabelText('Show only manually edited entries')).not.toBeInTheDocument();
    });
  });
});

// ── Empty state ───────────────────────────────────────────────────────────────

describe('ReleaseNotesRenderer empty state', () => {
  it('shows empty message when no entries', async () => {
    mockGetReleaseNotes.mockResolvedValue(makeNotesData({ entries: [] }));
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/No completed issues found/)).toBeInTheDocument();
    });
  });
});

// ── Error state ───────────────────────────────────────────────────────────────

describe('ReleaseNotesRenderer error', () => {
  it('shows error message when API fails', async () => {
    mockGetReleaseNotes.mockRejectedValue(new Error('500'));
    render(<ReleaseNotesRenderer {...defaultProps} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Failed to load release notes/)).toBeInTheDocument();
    });
  });
});
