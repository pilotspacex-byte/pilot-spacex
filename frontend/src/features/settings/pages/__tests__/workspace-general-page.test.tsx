/**
 * Tests for WorkspaceGeneralPage.
 *
 * T029: Name/slug/description editing, metadata display, danger zone.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

const mockWorkspaceStore = {
  getWorkspaceBySlug: vi.fn().mockReturnValue({ id: 'ws-123456789', slug: 'test-workspace' }),
  isAdmin: true,
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: mockWorkspaceStore,
  }),
}));

const mockUseWorkspaceSettings = vi.fn();
const mockUseUpdateWorkspaceSettings = vi.fn();

vi.mock('@/features/settings/hooks/use-workspace-settings', () => ({
  useWorkspaceSettings: (...args: unknown[]) => mockUseWorkspaceSettings(...args),
  useUpdateWorkspaceSettings: (...args: unknown[]) => mockUseUpdateWorkspaceSettings(...args),
}));

vi.mock('@/features/settings/components/delete-workspace-dialog', () => ({
  DeleteWorkspaceDialog: () => <div data-testid="delete-dialog">Delete Dialog</div>,
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@/services/api', () => ({
  apiClient: { get: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { WorkspaceGeneralPage } from '../workspace-general-page';

const defaultWorkspaceData = {
  id: 'ws-123456789',
  name: 'Test Workspace',
  slug: 'test-workspace',
  createdAt: '2025-06-15T10:00:00Z',
  memberIds: ['u1', 'u2', 'u3'],
};

describe('WorkspaceGeneralPage', () => {
  beforeEach(() => {
    mockWorkspaceStore.isAdmin = true;
    mockUseUpdateWorkspaceSettings.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
  });

  it('shows loading skeleton when loading', () => {
    mockUseWorkspaceSettings.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    const { container } = render(<WorkspaceGeneralPage />);

    // Skeleton renders animated placeholder divs
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByText('General')).not.toBeInTheDocument();
  });

  it('shows error alert when error occurs', () => {
    mockUseWorkspaceSettings.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network failure'),
    });

    render(<WorkspaceGeneralPage />);

    expect(screen.getByText('Failed to load workspace settings')).toBeInTheDocument();
    expect(screen.getByText('Network failure')).toBeInTheDocument();
  });

  it('renders workspace details form when data loaded', () => {
    mockUseWorkspaceSettings.mockReturnValue({
      data: defaultWorkspaceData,
      isLoading: false,
      error: null,
    });

    render(<WorkspaceGeneralPage />);

    expect(screen.getByText('General')).toBeInTheDocument();
    expect(screen.getByLabelText('Workspace Name')).toHaveValue('Test Workspace');
    expect(screen.getByLabelText('URL Slug')).toHaveValue('test-workspace');
    expect(screen.getByText('3')).toBeInTheDocument(); // member count
    expect(screen.getByText('ws-12345...')).toBeInTheDocument(); // truncated ID
  });

  it('hides danger zone for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    mockUseWorkspaceSettings.mockReturnValue({
      data: {
        ...defaultWorkspaceData,
        memberIds: ['u1'],
      },
      isLoading: false,
      error: null,
    });

    render(<WorkspaceGeneralPage />);

    expect(screen.queryByText('Danger Zone')).not.toBeInTheDocument();
    expect(screen.queryByTestId('delete-dialog')).not.toBeInTheDocument();
  });

  it('shows slug validation error for invalid input', async () => {
    mockUseWorkspaceSettings.mockReturnValue({
      data: defaultWorkspaceData,
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    render(<WorkspaceGeneralPage />);

    const slugInput = screen.getByLabelText('URL Slug');
    await user.clear(slugInput);
    await user.type(slugInput, 'INVALID SLUG!');

    expect(
      screen.getByText('Slug must contain only lowercase letters, numbers, and hyphens.')
    ).toBeInTheDocument();
  });

  it('clears slug validation error for valid input', async () => {
    mockUseWorkspaceSettings.mockReturnValue({
      data: defaultWorkspaceData,
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    render(<WorkspaceGeneralPage />);

    const slugInput = screen.getByLabelText('URL Slug');
    await user.clear(slugInput);
    await user.type(slugInput, 'valid-slug-123');

    expect(
      screen.queryByText('Slug must contain only lowercase letters, numbers, and hyphens.')
    ).not.toBeInTheDocument();
  });

  it('shows delete workspace dialog for admin', () => {
    mockUseWorkspaceSettings.mockReturnValue({
      data: defaultWorkspaceData,
      isLoading: false,
      error: null,
    });

    render(<WorkspaceGeneralPage />);

    expect(screen.getByText('Danger Zone')).toBeInTheDocument();
    expect(screen.getByTestId('delete-dialog')).toBeInTheDocument();
  });

  it('uses readOnly for non-admin inputs', () => {
    mockWorkspaceStore.isAdmin = false;
    mockUseWorkspaceSettings.mockReturnValue({
      data: defaultWorkspaceData,
      isLoading: false,
      error: null,
    });

    render(<WorkspaceGeneralPage />);

    const nameInput = screen.getByLabelText('Workspace Name');
    expect(nameInput).toHaveAttribute('readOnly');
    expect(nameInput).not.toBeDisabled();
  });
});
