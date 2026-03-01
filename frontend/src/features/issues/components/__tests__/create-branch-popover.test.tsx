/**
 * CreateBranchPopover component tests.
 *
 * Verifies rendering, popover open/close, branch name pre-fill from API,
 * mutation submission, and the copy git command button.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks — declared before component import so Vite can hoist them.
// vi.mock calls are hoisted to the top of the module by Vite/Vitest.
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();
const mockUseCreateBranch = vi.fn();

// Prevent NEXT_PUBLIC_SUPABASE_URL missing error — supabase.ts throws at module
// evaluation if the env var is not set. Mock it before any transitive import runs.
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

// Mock TanStack Query so no QueryClientProvider is needed.
// Each test controls what useQuery returns via mockUseQuery.
const mockUseQuery = vi.fn();
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@tanstack/react-query')>();
  return { ...actual, useQuery: (...args: unknown[]) => mockUseQuery(...args) };
});

vi.mock('../../hooks/use-create-branch', () => ({
  useCreateBranch: () => mockUseCreateBranch(),
}));

// ---------------------------------------------------------------------------
// Component under test (imported after mocks)
// ---------------------------------------------------------------------------

import { CreateBranchPopover } from '../create-branch-popover';

// ---------------------------------------------------------------------------
// Clipboard stub — must be configurable to survive repeated test runs
// ---------------------------------------------------------------------------

const clipboardWriteText = vi.fn().mockResolvedValue(undefined);
Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: clipboardWriteText },
  writable: true,
  configurable: true,
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const DEFAULT_PROPS = {
  workspaceId: 'ws-1',
  issueId: 'issue-1',
  integrationId: 'int-1',
};

const SUGGESTION = {
  branchName: 'feat/issue-1-fix-bug',
  gitCommand: 'git checkout -b feat/issue-1-fix-bug',
  format: 'default',
};

const REPOS = [
  {
    id: '1',
    fullName: 'org/repo',
    name: 'repo',
    owner: 'org',
    private: false,
    defaultBranch: 'main',
    syncEnabled: false,
    webhookActive: false,
  },
];

function buildSuggestionResult(
  override: Partial<{ data: typeof SUGGESTION | undefined; isLoading: boolean }> = {}
) {
  return { data: SUGGESTION, isLoading: false, ...override };
}

function buildReposResult(override: Partial<{ data: typeof REPOS; isLoading: boolean }> = {}) {
  return { data: REPOS, isLoading: false, ...override };
}

function setupDefaultMocks() {
  mockUseQuery.mockImplementation(({ queryKey }: { queryKey: unknown[] }) => {
    if (queryKey[0] === 'branch-name') return buildSuggestionResult();
    if (queryKey[0] === 'repositories') return buildReposResult();
    return { data: undefined, isLoading: false };
  });
  mockUseCreateBranch.mockReturnValue({ mutate: mockMutate, isPending: false });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CreateBranchPopover', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clipboardWriteText.mockResolvedValue(undefined);
    setupDefaultMocks();
  });

  it('renders the Create branch trigger button', () => {
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);
    expect(screen.getByRole('button', { name: /create github branch/i })).toBeInTheDocument();
  });

  it('opens popover on trigger click', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);

    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /create branch/i })).toBeInTheDocument();
    });
  });

  it('pre-fills branch name input from API suggestion', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);

    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    await waitFor(() => {
      const input = screen.getByRole('textbox', { name: /branch name/i });
      expect(input).toHaveValue('feat/issue-1-fix-bug');
    });
  });

  it('calls mutate with correct args when Create branch is clicked', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);

    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /branch name/i })).toHaveValue(
        'feat/issue-1-fix-bug'
      );
    });

    await user.click(screen.getByRole('button', { name: /^create branch$/i }));

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        workspaceId: DEFAULT_PROPS.workspaceId,
        issueId: DEFAULT_PROPS.issueId,
        integrationId: DEFAULT_PROPS.integrationId,
        branchName: 'feat/issue-1-fix-bug',
        repository: 'org/repo',
      }),
      expect.any(Object)
    );
  });

  it('copy button is enabled after branch name is populated', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);

    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /copy git checkout command/i })).not.toBeDisabled();
    });
  });

  it('copy button copies the correct git command via navigator.clipboard', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);

    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    // Wait for branch name to be populated and the copy button to be enabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /copy git checkout command/i })).not.toBeDisabled();
    });

    // Re-stub the clipboard AFTER userEvent setup so our spy is the active one.
    // userEvent.setup() with writeToClipboard:false still patches clipboard during
    // setup; we overwrite it here so the component's direct call reaches our mock.
    const localWriteText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: localWriteText },
      writable: true,
      configurable: true,
    });

    fireEvent.click(screen.getByRole('button', { name: /copy git checkout command/i }));

    await waitFor(() => {
      expect(localWriteText).toHaveBeenCalledWith('git checkout -b feat/issue-1-fix-bug');
    });
  });

  it('shows loading placeholder while repositories are loading', async () => {
    mockUseQuery.mockImplementation(({ queryKey }: { queryKey: unknown[] }) => {
      if (queryKey[0] === 'branch-name') return buildSuggestionResult();
      if (queryKey[0] === 'repositories') return buildReposResult({ data: [], isLoading: true });
      return { data: undefined, isLoading: false };
    });

    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);
    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    expect(screen.getByText('Loading repositories…')).toBeInTheDocument();
  });

  it('shows "No repositories connected." when repos list is empty', async () => {
    mockUseQuery.mockImplementation(({ queryKey }: { queryKey: unknown[] }) => {
      if (queryKey[0] === 'branch-name') return buildSuggestionResult();
      if (queryKey[0] === 'repositories') return buildReposResult({ data: [] });
      return { data: undefined, isLoading: false };
    });

    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);
    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    expect(screen.getByText('No repositories connected.')).toBeInTheDocument();
  });

  it('disables create button while mutation is pending', async () => {
    mockUseCreateBranch.mockReturnValue({ mutate: mockMutate, isPending: true });

    const user = userEvent.setup({ writeToClipboard: false });
    render(<CreateBranchPopover {...DEFAULT_PROPS} />);
    await user.click(screen.getByRole('button', { name: /create github branch/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^create branch$/i })).toBeDisabled();
    });
  });
});
