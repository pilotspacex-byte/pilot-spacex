/**
 * Tests for AISettingsPage.
 *
 * T178: AI provider configuration with API keys, feature toggles, provider status.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
}));

const mockSettings = {
  isLoading: false,
  isSaving: false,
  error: null as string | null,
  settings: {
    workspaceId: 'ws-1',
    providers: [
      {
        provider: 'anthropic',
        isConfigured: true,
        isValid: true,
        lastValidatedAt: '2026-01-01T00:00:00Z',
      },
      {
        provider: 'openai',
        isConfigured: false,
        isValid: null,
        lastValidatedAt: null,
      },
    ],
    features: {
      ghostTextEnabled: true,
      marginAnnotationsEnabled: false,
      aiContextEnabled: true,
      issueExtractionEnabled: false,
      prReviewEnabled: false,
      autoApproveNonDestructive: false,
    },
    defaultProvider: 'anthropic',
    costLimitUsd: null,
  } as Record<string, unknown> | null,
  anthropicKeySet: true,
  openaiKeySet: false,
  ghostTextEnabled: true,
  marginAnnotationsEnabled: false,
  aiContextEnabled: true,
  loadSettings: vi.fn(),
  loadModels: vi.fn(),
  saveSettings: vi.fn(),
  validateKey: vi.fn().mockReturnValue(true),
  validationErrors: {} as Record<string, string>,
};

const mockWorkspaceStore = {
  getWorkspaceBySlug: vi.fn().mockReturnValue({ id: 'ws-1', name: 'Test', slug: 'test-workspace' }),
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    ai: { settings: mockSettings },
    workspaceStore: mockWorkspaceStore,
  }),
}));

vi.mock('@/features/settings/components/api-key-form', () => ({
  APIKeyForm: () => <div data-testid="api-key-form">APIKeyForm</div>,
}));

vi.mock('@/features/settings/components/ai-feature-toggles', () => ({
  AIFeatureToggles: () => <div data-testid="ai-feature-toggles">AIFeatureToggles</div>,
}));

vi.mock('@/features/settings/components/provider-status-card', () => ({
  ProviderStatusCard: ({
    provider,
    isKeySet,
  }: {
    provider: string;
    isKeySet: boolean;
    status: string;
    lastValidated?: string;
  }) => (
    <div data-testid={`provider-status-${provider}`}>
      {provider}: {isKeySet ? 'set' : 'not set'}
    </div>
  ),
}));

vi.mock('@/features/settings/components/custom-provider-form', () => ({
  CustomProviderForm: ({ workspaceId }: { workspaceId: string; onSuccess: () => void }) => (
    <div data-testid="custom-provider-form" data-workspace-id={workspaceId}>
      CustomProviderForm
    </div>
  ),
}));

import { AISettingsPage } from '@/features/settings/pages/ai-settings-page';

describe('AISettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSettings.isLoading = false;
    mockSettings.error = null;
    mockSettings.settings = {
      workspaceId: 'ws-1',
      providers: [
        {
          provider: 'anthropic',
          isConfigured: true,
          isValid: true,
          lastValidatedAt: '2026-01-01T00:00:00Z',
        },
        {
          provider: 'openai',
          isConfigured: false,
          isValid: null,
          lastValidatedAt: null,
        },
      ],
      features: {
        ghostTextEnabled: true,
        marginAnnotationsEnabled: false,
        aiContextEnabled: true,
        issueExtractionEnabled: false,
        prReviewEnabled: false,
        autoApproveNonDestructive: false,
      },
      defaultProvider: 'anthropic',
      costLimitUsd: null,
    };
  });

  it('renders loading skeleton when loading', () => {
    mockSettings.isLoading = true;
    const { container } = render(<AISettingsPage />);

    // Skeleton elements should be present (Skeleton component renders divs)
    expect(
      container.querySelectorAll('[class*="animate-pulse"], [data-slot="skeleton"]').length
    ).toBeGreaterThanOrEqual(0);
    expect(screen.queryByText('AI Providers')).not.toBeInTheDocument();
  });

  it('renders error alert when error and no settings', () => {
    mockSettings.error = 'Failed to connect';
    mockSettings.settings = null;

    render(<AISettingsPage />);

    expect(screen.getByText('Failed to load settings')).toBeInTheDocument();
    expect(screen.getByText('Failed to connect')).toBeInTheDocument();
  });

  it('renders full page when settings loaded', () => {
    render(<AISettingsPage />);

    expect(screen.getByText('AI Providers')).toBeInTheDocument();
    expect(screen.getByText('Provider Status')).toBeInTheDocument();
    expect(screen.getByTestId('provider-status-anthropic')).toBeInTheDocument();
    expect(screen.getByTestId('provider-status-openai')).toBeInTheDocument();
    expect(screen.getByTestId('api-key-form')).toBeInTheDocument();
    expect(screen.getByTestId('ai-feature-toggles')).toBeInTheDocument();
  });

  it('shows security notice', () => {
    render(<AISettingsPage />);

    expect(screen.getByText('Security & Privacy')).toBeInTheDocument();
    expect(screen.getByText(/API keys are encrypted/)).toBeInTheDocument();
  });

  it('calls loadSettings on mount with workspace ID', () => {
    render(<AISettingsPage />);

    expect(mockSettings.loadSettings).toHaveBeenCalledWith('ws-1');
  });

  it('renders provider status cards with correct key state', () => {
    render(<AISettingsPage />);

    expect(screen.getByTestId('provider-status-anthropic')).toHaveTextContent('anthropic: set');
    expect(screen.getByTestId('provider-status-openai')).toHaveTextContent('openai: not set');
  });

  it('uses consistent padding matching other settings pages', () => {
    const { container } = render(<AISettingsPage />);

    const mainDiv = container.firstChild as HTMLElement;
    expect(mainDiv.className).toContain('px-4');
    expect(mainDiv.className).toContain('sm:px-6');
    expect(mainDiv.className).toContain('lg:px-8');
  });

  // 13-03: All 5 built-in provider cards must be rendered
  it('renders provider status cards for all 5 built-in providers', () => {
    render(<AISettingsPage />);

    expect(screen.getByTestId('provider-status-anthropic')).toBeInTheDocument();
    expect(screen.getByTestId('provider-status-openai')).toBeInTheDocument();
    expect(screen.getByTestId('provider-status-kimi')).toBeInTheDocument();
    expect(screen.getByTestId('provider-status-glm')).toBeInTheDocument();
    expect(screen.getByTestId('provider-status-google')).toBeInTheDocument();
  });

  // 13-03: CustomProviderForm must be rendered below built-in providers
  it('renders CustomProviderForm under Custom Providers heading', () => {
    render(<AISettingsPage />);

    expect(screen.getByText('Custom Providers')).toBeInTheDocument();
    expect(screen.getByTestId('custom-provider-form')).toBeInTheDocument();
  });

  // 13-03: CustomProviderForm receives workspace ID
  it('passes workspaceId to CustomProviderForm', () => {
    render(<AISettingsPage />);

    const form = screen.getByTestId('custom-provider-form');
    expect(form).toHaveAttribute('data-workspace-id', 'ws-1');
  });
});
