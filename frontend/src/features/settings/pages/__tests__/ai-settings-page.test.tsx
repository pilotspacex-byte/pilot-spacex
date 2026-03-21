/**
 * Tests for AISettingsPage.
 *
 * Tabbed provider panel (Embedding | LLM) with feature toggles.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('next/navigation', () => ({
  useParams: () => ({ workspaceSlug: 'test-workspace' }),
}));

const mockProviders = [
  {
    provider: 'google',
    serviceType: 'embedding',
    isConfigured: true,
    isValid: true,
    lastValidatedAt: '2026-01-01T00:00:00Z',
    baseUrl: null,
    modelName: null,
  },
  {
    provider: 'ollama',
    serviceType: 'embedding',
    isConfigured: false,
    isValid: null,
    lastValidatedAt: null,
    baseUrl: null,
    modelName: null,
  },
  {
    provider: 'anthropic',
    serviceType: 'llm',
    isConfigured: true,
    isValid: true,
    lastValidatedAt: '2026-01-01T00:00:00Z',
    baseUrl: null,
    modelName: null,
  },
  {
    provider: 'ollama',
    serviceType: 'llm',
    isConfigured: false,
    isValid: null,
    lastValidatedAt: null,
    baseUrl: null,
    modelName: null,
  },
];

const mockSettings = {
  isLoading: false,
  isSaving: false,
  error: null as string | null,
  settings: {
    workspaceId: 'ws-1',
    providers: mockProviders,
    features: {
      ghostTextEnabled: true,
      marginAnnotationsEnabled: false,
      aiContextEnabled: true,
      issueExtractionEnabled: false,
      prReviewEnabled: false,
      autoApproveNonDestructive: false,
    },
    defaultLlmProvider: 'anthropic',
    defaultEmbeddingProvider: 'google',
    costLimitUsd: null,
  } as Record<string, unknown> | null,
  anthropicKeySet: true,
  llmConfigured: true,
  embeddingConfigured: true,
  ghostTextEnabled: true,
  marginAnnotationsEnabled: false,
  aiContextEnabled: true,
  loadSettings: vi.fn(),
  loadModels: vi.fn(),
  saveSettings: vi.fn(),
  validateKey: vi.fn().mockReturnValue(true),
  validationErrors: {} as Record<string, string>,
  getProviderStatus: vi.fn(),
  getProvidersByService: vi.fn((serviceType: string) =>
    mockProviders.filter((p) => p.serviceType === serviceType)
  ),
  getDefaultProvider: vi.fn((serviceType: string) =>
    serviceType === 'llm' ? 'anthropic' : 'google'
  ),
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

vi.mock('@/features/settings/components/provider-section', () => ({
  ProviderSection: ({
    serviceType,
    description,
  }: {
    serviceType: string;
    description: string;
    onSaved: () => void;
  }) => (
    <div data-testid={`provider-section-${serviceType}`}>
      <span>{description}</span>
    </div>
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
      providers: mockProviders,
      features: {
        ghostTextEnabled: true,
        marginAnnotationsEnabled: false,
        aiContextEnabled: true,
        issueExtractionEnabled: false,
        prReviewEnabled: false,
        autoApproveNonDestructive: false,
      },
      defaultLlmProvider: 'anthropic',
      defaultEmbeddingProvider: 'google',
      costLimitUsd: null,
    };
  });

  it('renders loading skeleton when loading', () => {
    mockSettings.isLoading = true;
    render(<AISettingsPage />);

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

  it('renders Embedding and LLM tabs', () => {
    render(<AISettingsPage />);
    expect(screen.getByRole('tab', { name: /Embedding/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /LLM/i })).toBeInTheDocument();
  });

  it('renders AIFeatureToggles component', () => {
    render(<AISettingsPage />);
    expect(screen.getByTestId('ai-feature-toggles')).toBeInTheDocument();
  });

  it('calls loadSettings on mount with workspace ID', () => {
    render(<AISettingsPage />);
    expect(mockSettings.loadSettings).toHaveBeenCalledWith('ws-1');
  });

  it('does NOT render old ProviderStatusCard or APIKeyForm sections', () => {
    render(<AISettingsPage />);

    expect(screen.queryByText('Provider Status')).not.toBeInTheDocument();
    expect(screen.queryByText('API Keys')).not.toBeInTheDocument();
    expect(screen.queryByText('Custom Providers')).not.toBeInTheDocument();
  });

  it('does NOT render standalone security alert', () => {
    render(<AISettingsPage />);

    // Security info is now inline in the config form, not a standalone alert
    expect(screen.queryByText('Security & Privacy')).not.toBeInTheDocument();
  });
});
