/**
 * Tests for RolesSettingsPage.
 *
 * AUTH-04, AUTH-05: Custom RBAC role management UI.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
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
  getWorkspaceBySlug: vi.fn().mockReturnValue({ id: 'ws-123', slug: 'test-workspace' }),
  isAdmin: true,
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: mockWorkspaceStore,
  }),
}));

const mockUseCustomRoles = vi.fn();
const mockUseCreateRole = vi.fn();
const mockUseUpdateRole = vi.fn();
const mockUseDeleteRole = vi.fn();

vi.mock('@/features/settings/hooks/use-custom-roles', () => ({
  useCustomRoles: (...args: unknown[]) => mockUseCustomRoles(...args),
  useCreateRole: (...args: unknown[]) => mockUseCreateRole(...args),
  useUpdateRole: (...args: unknown[]) => mockUseUpdateRole(...args),
  useDeleteRole: (...args: unknown[]) => mockUseDeleteRole(...args),
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

import { RolesSettingsPage } from '../roles-settings-page';

const mockRoles = [
  {
    id: 'role-1',
    workspace_id: 'ws-123',
    name: 'Developer',
    description: 'Can manage issues and notes',
    permissions: ['issues:read', 'issues:write', 'notes:read', 'notes:write'],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'role-2',
    workspace_id: 'ws-123',
    name: 'Viewer',
    description: 'Read-only access',
    permissions: ['issues:read', 'notes:read'],
    created_at: '2025-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
  },
];

function setupDefaultMocks() {
  mockUseCustomRoles.mockReturnValue({ data: mockRoles, isLoading: false, error: null });
  mockUseCreateRole.mockReturnValue({ mutateAsync: vi.fn(), isPending: false, error: null });
  mockUseUpdateRole.mockReturnValue({ mutateAsync: vi.fn(), isPending: false, error: null });
  mockUseDeleteRole.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
}

describe('RolesSettingsPage', () => {
  beforeEach(() => {
    mockWorkspaceStore.isAdmin = true;
    setupDefaultMocks();
  });

  it('renders roles list with two custom roles', () => {
    render(<RolesSettingsPage />);

    expect(screen.getByText('Developer')).toBeInTheDocument();
    expect(screen.getByText('Viewer')).toBeInTheDocument();
    expect(screen.getByText('Can manage issues and notes')).toBeInTheDocument();
    expect(screen.getByText('Read-only access')).toBeInTheDocument();
  });

  it('shows empty state when no roles', () => {
    mockUseCustomRoles.mockReturnValue({ data: [], isLoading: false, error: null });

    render(<RolesSettingsPage />);

    expect(screen.getByText(/No custom roles yet/i)).toBeInTheDocument();
    expect(screen.getByText(/Create your first role/i)).toBeInTheDocument();
  });

  it('renders Create Role button', () => {
    render(<RolesSettingsPage />);

    expect(screen.getByRole('button', { name: /Create Role/i })).toBeInTheDocument();
  });

  it('opens creation dialog when Create Role button is clicked', async () => {
    const user = userEvent.setup();
    render(<RolesSettingsPage />);

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    // Dialog should be visible with form fields
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
  });

  it('displays permissions as badges grouped by resource', () => {
    render(<RolesSettingsPage />);

    // Developer role has issues:read, issues:write, notes:read, notes:write
    const developerRow = screen.getByText('Developer').closest('tr');
    expect(developerRow).not.toBeNull();
    const developerRowContainer = within(developerRow as HTMLElement);
    expect(developerRowContainer.getByText('issues:read')).toBeInTheDocument();
    expect(developerRowContainer.getByText('issues:write')).toBeInTheDocument();
  });

  it('shows delete confirmation dialog before deleting a role', async () => {
    const user = userEvent.setup();
    render(<RolesSettingsPage />);

    const deleteButtons = screen.getAllByRole('button', { name: /Delete/i });
    await user.click(deleteButtons[0]!);

    // AlertDialog should appear
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByText(/Delete role/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Members using this role will revert to their built-in role/i)
    ).toBeInTheDocument();
  });

  it('opens edit dialog when Edit button is clicked', async () => {
    const user = userEvent.setup();
    render(<RolesSettingsPage />);

    const editButtons = screen.getAllByRole('button', { name: /Edit/i });
    await user.click(editButtons[0]!);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    // Should pre-fill with role data
    expect(screen.getByDisplayValue('Developer')).toBeInTheDocument();
  });

  it('shows permission checkboxes grouped by resource in dialog', async () => {
    const user = userEvent.setup();
    render(<RolesSettingsPage />);

    await user.click(screen.getByRole('button', { name: /Create Role/i }));

    // Should have permission checkboxes for each resource
    expect(screen.getByText('issues')).toBeInTheDocument();
    expect(screen.getByText('notes')).toBeInTheDocument();
    expect(screen.getByText('members')).toBeInTheDocument();
  });

  it('shows loading skeleton when roles are loading', () => {
    mockUseCustomRoles.mockReturnValue({ data: undefined, isLoading: true, error: null });

    const { container } = render(<RolesSettingsPage />);

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Create Role/i })).not.toBeInTheDocument();
  });

  it('shows access restricted for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    render(<RolesSettingsPage />);

    expect(screen.getByText('Access restricted')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Create Role/i })).not.toBeInTheDocument();
  });

  it('shows inline error for duplicate role name (409)', async () => {
    const { ApiError } = await import('@/services/api');
    const conflictError = new ApiError({ status: 409, title: 'Role name already exists' });
    mockUseCreateRole.mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(conflictError),
      isPending: false,
      error: null,
    });

    const user = userEvent.setup();
    render(<RolesSettingsPage />);

    await user.click(screen.getByRole('button', { name: /Create Role/i }));
    const nameInput = screen.getByLabelText('Name');
    await user.type(nameInput, 'Developer');

    // Check at least one permission so form is valid
    const firstCheckbox = screen.getAllByRole('checkbox')[0]!;
    await user.click(firstCheckbox);

    const submitButton = screen.getByRole('button', { name: /Create$/i });
    await user.click(submitButton);

    expect(screen.getByText(/A role with this name already exists/i)).toBeInTheDocument();
  });
});
