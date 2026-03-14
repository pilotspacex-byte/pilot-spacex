/**
 * Tests for AuditSettingsPage.
 *
 * AUDIT-03: Filter UI for audit log.
 * AUDIT-04: Export UI (JSON/CSV).
 * AUDIT-06: No write affordances (no delete/edit buttons).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/test-workspace/settings/audit',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>();
  return {
    ...actual,
    apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  };
});

const mockUseAuditLog = vi.fn();
const mockUseExportAuditLog = vi.fn();
const mockUseWorkspaceMembers = vi.fn();

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: {
      getWorkspaceBySlug: vi.fn().mockReturnValue({ id: 'ws-123', slug: 'test-workspace' }),
      isAdmin: true,
    },
  }),
}));

vi.mock('@/features/issues/hooks/use-workspace-members', () => ({
  useWorkspaceMembers: (...args: unknown[]) => mockUseWorkspaceMembers(...args),
}));

vi.mock('@/features/settings/hooks/use-audit-log', () => ({
  useAuditLog: (...args: unknown[]) => mockUseAuditLog(...args),
  useExportAuditLog: (...args: unknown[]) => mockUseExportAuditLog(...args),
  useRollbackAIArtifact: () => ({ mutate: vi.fn(), isPending: false, variables: null }),
}));

const mockAuditEntries = [
  {
    id: 'audit-1',
    actorId: 'user-abc123de',
    actorType: 'USER' as const,
    action: 'issue.create',
    resourceType: 'issue',
    resourceId: 'issue-abcdef12',
    payload: {
      before: {},
      after: { title: 'New issue', status: 'open' },
    },
    aiModel: null,
    aiTokenCost: null,
    aiRationale: null,
    ipAddress: '192.168.1.1',
    createdAt: '2026-03-08T01:00:00Z',
  },
  {
    id: 'audit-2',
    actorId: null,
    actorType: 'AI' as const,
    action: 'issue.update',
    resourceType: 'issue',
    resourceId: 'issue-abcdef12',
    payload: {
      before: { title: 'Old title' },
      after: { title: 'New title' },
    },
    aiModel: 'claude-3-sonnet',
    aiTokenCost: 0.005,
    aiRationale: 'Improved clarity',
    ipAddress: null,
    createdAt: '2026-03-08T02:00:00Z',
  },
];

const mockPaginatedResponse = {
  items: mockAuditEntries,
  hasNext: false,
  nextCursor: null,
  pageSize: 50,
};

const mockMembers = [
  {
    userId: 'user-abc123de',
    email: 'alice@example.com',
    fullName: 'Alice Johnson',
    avatarUrl: null,
    role: 'member' as const,
    joinedAt: '2026-01-01T00:00:00Z',
    weeklyAvailableHours: 40,
  },
];

function setupDefaultMocks() {
  mockUseAuditLog.mockReturnValue({
    data: mockPaginatedResponse,
    isLoading: false,
    error: null,
    isFetchingNextPage: false,
  });
  mockUseExportAuditLog.mockReturnValue({
    triggerExport: vi.fn(),
    isExporting: false,
  });
  mockUseWorkspaceMembers.mockReturnValue({ data: mockMembers });
}

import { AuditSettingsPage } from '../audit-settings-page';

describe('AuditSettingsPage', () => {
  beforeEach(() => {
    setupDefaultMocks();
    vi.clearAllMocks();
    setupDefaultMocks();
  });

  it('renders filter controls: actor input, action select, resource type select, date inputs', () => {
    render(<AuditSettingsPage />);

    expect(screen.getByPlaceholderText(/actor/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /action/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /resource type/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
  });

  it('renders table with correct column headers', () => {
    render(<AuditSettingsPage />);

    expect(screen.getByRole('columnheader', { name: /timestamp/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /actor/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /action/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /resource type/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /resource id/i })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /ip address/i })).toBeInTheDocument();
  });

  it('renders audit log rows', () => {
    render(<AuditSettingsPage />);

    expect(screen.getByText('Issue Created')).toBeInTheDocument();
    expect(screen.getByText('Issue Updated')).toBeInTheDocument();
  });

  it('renders no delete or edit buttons on rows', () => {
    render(<AuditSettingsPage />);

    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument();
  });

  it('Export CSV button is visible', () => {
    render(<AuditSettingsPage />);

    expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument();
  });

  it('Export JSON button is visible', () => {
    render(<AuditSettingsPage />);

    expect(screen.getByRole('button', { name: /export json/i })).toBeInTheDocument();
  });

  it('row expansion shows payload on click', async () => {
    const user = userEvent.setup();
    render(<AuditSettingsPage />);

    // Click first row to expand
    const rows = screen.getAllByRole('row');
    // rows[0] is header, rows[1] is first data row
    const firstDataRow = rows[1];
    expect(firstDataRow).toBeDefined();
    await user.click(firstDataRow!);

    // Payload should be visible after expansion
    await waitFor(() => {
      expect(screen.getByText(/after/i)).toBeInTheDocument();
    });
  });

  it('shows AI fields for AI actor type rows when expanded', async () => {
    const user = userEvent.setup();
    render(<AuditSettingsPage />);

    // Click second row (AI actor)
    const rows = screen.getAllByRole('row');
    const secondDataRow = rows[2];
    expect(secondDataRow).toBeDefined();
    await user.click(secondDataRow!);

    await waitFor(() => {
      expect(screen.getByText(/claude-3-sonnet/i)).toBeInTheDocument();
    });
  });

  it('shows loading skeleton while fetching', () => {
    mockUseAuditLog.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      isFetchingNextPage: false,
    });
    mockUseExportAuditLog.mockReturnValue({
      triggerExport: vi.fn(),
      isExporting: false,
    });

    render(<AuditSettingsPage />);

    // Skeleton rows should be visible
    const skeletons = document.querySelectorAll('[data-testid="skeleton"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows empty state when no results', () => {
    mockUseAuditLog.mockReturnValue({
      data: { items: [], hasNext: false, nextCursor: null, pageSize: 50 },
      isLoading: false,
      error: null,
      isFetchingNextPage: false,
    });
    mockUseExportAuditLog.mockReturnValue({
      triggerExport: vi.fn(),
      isExporting: false,
    });

    render(<AuditSettingsPage />);

    expect(screen.getByText(/no audit log entries/i)).toBeInTheDocument();
  });

  it('does not wrap component in observer (plain React)', () => {
    // AuditSettingsPage should be importable as a plain named export without observer
    expect(typeof AuditSettingsPage).toBe('function');
    // If it were wrapped in observer, displayName would contain 'observer'
    const displayName = (AuditSettingsPage as { displayName?: string }).displayName ?? '';
    expect(displayName).not.toContain('observer');
  });

  it('resolves actor UUID to display name when member is found', () => {
    render(<AuditSettingsPage />);

    // actorId 'user-abc123de' should be resolved to 'Alice Johnson' (from mockMembers)
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    // Raw UUID should not appear as actor label
    expect(screen.queryByText('user-abc')).not.toBeInTheDocument();
  });

  it('falls back to truncated UUID when actor is not in members list', () => {
    // mockAuditEntries has actorId 'user-abc123de' which is in members.
    // Provide empty members to force fallback.
    mockUseWorkspaceMembers.mockReturnValue({ data: [] });

    render(<AuditSettingsPage />);

    // truncate('user-abc123de', 8) = 'user-abc' (8 chars) + '…' (unicode ellipsis)
    expect(screen.getByText('user-abc\u2026')).toBeInTheDocument();
  });

  it('renders dash for null actorId', () => {
    render(<AuditSettingsPage />);

    // Second entry has actorId: null (AI actor) — should show '—'
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('uses email prefix as fallback when member has no fullName', () => {
    mockUseWorkspaceMembers.mockReturnValue({
      data: [
        {
          userId: 'user-abc123de',
          email: 'alice@example.com',
          fullName: null,
          avatarUrl: null,
          role: 'member' as const,
          joinedAt: '2026-01-01T00:00:00Z',
          weeklyAvailableHours: 40,
        },
      ],
    });

    render(<AuditSettingsPage />);

    // fullName is null, so email prefix 'alice' should be shown
    expect(screen.getByText('alice')).toBeInTheDocument();
  });
});
