/**
 * Tests for SsoSettingsPage.
 *
 * AUTH-01, AUTH-02: SAML and OIDC configuration UI.
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
  getWorkspaceBySlug: vi.fn().mockReturnValue({ id: 'ws-123', slug: 'test-workspace' }),
  isAdmin: true,
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    workspaceStore: mockWorkspaceStore,
  }),
}));

const mockUseSamlConfig = vi.fn();
const mockUseUpdateSamlConfig = vi.fn();
const mockUseOidcConfig = vi.fn();
const mockUseUpdateOidcConfig = vi.fn();
const mockUseSetSsoRequired = vi.fn();
const mockUseRoleClaimMapping = vi.fn();
const mockUseUpdateRoleClaimMapping = vi.fn();

vi.mock('@/features/settings/hooks/use-sso-settings', () => ({
  useSamlConfig: (...args: unknown[]) => mockUseSamlConfig(...args),
  useUpdateSamlConfig: (...args: unknown[]) => mockUseUpdateSamlConfig(...args),
  useOidcConfig: (...args: unknown[]) => mockUseOidcConfig(...args),
  useUpdateOidcConfig: (...args: unknown[]) => mockUseUpdateOidcConfig(...args),
  useSetSsoRequired: (...args: unknown[]) => mockUseSetSsoRequired(...args),
  useRoleClaimMapping: (...args: unknown[]) => mockUseRoleClaimMapping(...args),
  useUpdateRoleClaimMapping: (...args: unknown[]) => mockUseUpdateRoleClaimMapping(...args),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@/services/api', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { SsoSettingsPage } from '../sso-settings-page';

function setupDefaultMocks() {
  mockUseSamlConfig.mockReturnValue({
    data: {
      entity_id: 'https://example.com/entity',
      sso_url: 'https://idp.example.com/sso',
      acs_url: 'https://app.example.com/acs',
      metadata_url: null,
      certificate: null,
      sso_required: false,
    },
    isLoading: false,
    error: null,
  });
  mockUseUpdateSamlConfig.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  mockUseOidcConfig.mockReturnValue({ data: null, isLoading: false, error: null });
  mockUseUpdateOidcConfig.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  mockUseSetSsoRequired.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  mockUseRoleClaimMapping.mockReturnValue({ data: null, isLoading: false });
  mockUseUpdateRoleClaimMapping.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
}

describe('SsoSettingsPage', () => {
  beforeEach(() => {
    mockWorkspaceStore.isAdmin = true;
    setupDefaultMocks();
  });

  it('renders SAML 2.0 configuration section', () => {
    render(<SsoSettingsPage />);

    expect(screen.getByText('SAML 2.0 Configuration')).toBeInTheDocument();
    expect(screen.getByLabelText('Entity ID')).toBeInTheDocument();
    expect(screen.getByLabelText('SSO URL')).toBeInTheDocument();
    expect(screen.getByLabelText(/X\.509 Certificate/i)).toBeInTheDocument();
  });

  it('renders OIDC provider section with provider dropdown', async () => {
    render(<SsoSettingsPage />);

    expect(screen.getByText('OIDC / OAuth 2.0 Configuration')).toBeInTheDocument();
    // Provider selector should exist
    expect(screen.getByLabelText('Client ID')).toBeInTheDocument();
    expect(screen.getByLabelText('Client Secret')).toBeInTheDocument();
  });

  it('renders SSO enforcement toggle', () => {
    render(<SsoSettingsPage />);

    expect(screen.getByText('SSO Enforcement')).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: /Require SSO/i })).toBeInTheDocument();
  });

  it('renders role claim mapping section', () => {
    render(<SsoSettingsPage />);

    expect(screen.getByText('Role Claim Mapping')).toBeInTheDocument();
    expect(screen.getByLabelText('Claim Key')).toBeInTheDocument();
  });

  it('shows read-only ACS URL with copy button', () => {
    render(<SsoSettingsPage />);

    expect(screen.getByText('https://app.example.com/acs')).toBeInTheDocument();
    expect(screen.getByLabelText(/Copy ACS URL/i)).toBeInTheDocument();
  });

  it('shows loading skeleton when SAML config is loading', () => {
    mockUseSamlConfig.mockReturnValue({ data: undefined, isLoading: true, error: null });

    const { container } = render(<SsoSettingsPage />);

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByText('SAML 2.0 Configuration')).not.toBeInTheDocument();
  });

  it('shows warning when enabling SSO enforcement', async () => {
    const user = userEvent.setup();
    render(<SsoSettingsPage />);

    const toggle = screen.getByRole('switch', { name: /Require SSO/i });
    await user.click(toggle);

    expect(screen.getByText(/Email\/password login will be disabled/i)).toBeInTheDocument();
  });

  it('shows access restricted for non-admin users', () => {
    mockWorkspaceStore.isAdmin = false;
    render(<SsoSettingsPage />);

    expect(screen.getByText('Access restricted')).toBeInTheDocument();
    expect(screen.queryByText('SAML 2.0 Configuration')).not.toBeInTheDocument();
  });

  it('calls updateSamlConfig mutation on save', async () => {
    const mockMutateAsync = vi.fn().mockResolvedValue({});
    mockUseUpdateSamlConfig.mockReturnValue({ mutateAsync: mockMutateAsync, isPending: false });

    const user = userEvent.setup();
    render(<SsoSettingsPage />);

    const saveButton = screen.getByRole('button', { name: /Save SAML Config/i });
    await user.click(saveButton);

    expect(mockMutateAsync).toHaveBeenCalled();
  });
});
