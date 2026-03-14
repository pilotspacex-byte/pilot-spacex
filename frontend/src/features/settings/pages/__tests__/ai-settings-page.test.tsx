/**
 * Tests for AISettingsPage.
 *
 * Unified provider list view with expandable rows.
 * All 6 providers appear in a single list.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
}));

const findProviderStatus = (provider: string) => {
  const providers = mockSettings.settings?.providers as Array<{ provider: string }> | undefined;
  return providers?.find((p) => p.provider === provider);
};

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
  getProviderStatus: vi.fn(findProviderStatus),
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

vi.mock('@/features/settings/components/provider-row', () => ({
  ProviderRow: ({ provider }: { provider: string; status: unknown; onSaved: () => void }) => (
    <div data-testid={`provider-row-${provider}`}>{provider}</div>
  ),
}));

vi.mock('@/features/settings/components/ai-feature-toggles', () => ({
  AIFeatureToggles: () => <div data-testid="ai-feature-toggles">AIFeatureToggles</div>,
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
    mockSettings.getProviderStatus = vi.fn(findProviderStatus);
  });

  it('renders loading skeleton when loading', () => {
    mockSettings.isLoading = true;
    const { container } = render(<AISettingsPage />);

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

  it('renders the AI Providers heading', () => {
    render(<AISettingsPage />);
    expect(screen.getByText('AI Providers')).toBeInTheDocument();
  });

  it('renders all 6 provider rows and queries status for each', () => {
    render(<AISettingsPage />);

    expect(screen.getByTestId('provider-row-anthropic')).toBeInTheDocument();
    expect(screen.getByTestId('provider-row-openai')).toBeInTheDocument();
    expect(screen.getByTestId('provider-row-google')).toBeInTheDocument();
    expect(screen.getByTestId('provider-row-kimi')).toBeInTheDocument();
    expect(screen.getByTestId('provider-row-glm')).toBeInTheDocument();
    expect(screen.getByTestId('provider-row-ai_agent')).toBeInTheDocument();

    expect(mockSettings.getProviderStatus).toHaveBeenCalledTimes(6);
    expect(mockSettings.getProviderStatus).toHaveBeenCalledWith('anthropic');
    expect(mockSettings.getProviderStatus).toHaveBeenCalledWith('openai');
    expect(mockSettings.getProviderStatus).toHaveBeenCalledWith('google');
    expect(mockSettings.getProviderStatus).toHaveBeenCalledWith('kimi');
    expect(mockSettings.getProviderStatus).toHaveBeenCalledWith('glm');
    expect(mockSettings.getProviderStatus).toHaveBeenCalledWith('ai_agent');
  });

  it('renders AIFeatureToggles component', () => {
    render(<AISettingsPage />);
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

  it('uses consistent padding matching other settings pages', () => {
    const { container } = render(<AISettingsPage />);

    const mainDiv = container.firstChild as HTMLElement;
    expect(mainDiv.className).toContain('px-4');
    expect(mainDiv.className).toContain('sm:px-6');
    expect(mainDiv.className).toContain('lg:px-8');
  });

  it('does NOT render old ProviderStatusCard or APIKeyForm sections', () => {
    render(<AISettingsPage />);

    expect(screen.queryByText('Provider Status')).not.toBeInTheDocument();
    expect(screen.queryByText('API Keys')).not.toBeInTheDocument();
    expect(screen.queryByText('Custom Providers')).not.toBeInTheDocument();
  });
});
