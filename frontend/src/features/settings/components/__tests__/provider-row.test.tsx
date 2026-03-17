/**
 * Tests for ProviderRow component.
 *
 * Verifies service-based provider row with expandable config fields.
 * Supports 3 providers: Google Gemini (embedding), Anthropic (llm), Ollama (both).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

vi.mock('date-fns', () => ({
  formatDistanceToNow: () => '2 days ago',
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

const mockSettings = {
  isSaving: false,
  saveSettings: vi.fn(),
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    ai: { settings: mockSettings },
  }),
}));

// Mock APIKeyInput to avoid complex rendering
vi.mock('../api-key-input', () => ({
  APIKeyInput: ({
    label,
    provider,
  }: {
    label: string;
    provider?: string;
    value: string;
    onChange: (v: string) => void;
    isSet: boolean;
    disabled?: boolean;
  }) => (
    <div data-testid={`api-key-input-${provider ?? 'default'}`}>
      <label>{label}</label>
      <input aria-label={label} />
    </div>
  ),
}));

import { ProviderRow } from '../provider-row';

const defaultProps = {
  onSaved: vi.fn(),
};

describe('ProviderRow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSettings.saveSettings = vi.fn().mockResolvedValue(undefined);
  });

  it('renders Google Gemini provider name', () => {
    render(
      <ProviderRow {...defaultProps} provider="google" serviceType="embedding" status={undefined} />
    );
    expect(screen.getByText('Google Gemini')).toBeInTheDocument();
  });

  it('renders Anthropic provider name', () => {
    render(
      <ProviderRow {...defaultProps} provider="anthropic" serviceType="llm" status={undefined} />
    );
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('renders Ollama provider name', () => {
    render(
      <ProviderRow {...defaultProps} provider="ollama" serviceType="llm" status={undefined} />
    );
    expect(screen.getByText('Ollama')).toBeInTheDocument();
  });

  it('renders Ollama with Not configured badge when no status', () => {
    render(
      <ProviderRow {...defaultProps} provider="ollama" serviceType="embedding" status={undefined} />
    );
    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });

  it('shows "Not configured" badge when status is undefined', () => {
    render(
      <ProviderRow {...defaultProps} provider="anthropic" serviceType="llm" status={undefined} />
    );
    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });

  it('shows "Connected" badge when provider is configured and valid', () => {
    render(
      <ProviderRow
        {...defaultProps}
        provider="anthropic"
        serviceType="llm"
        status={{
          provider: 'anthropic',
          serviceType: 'llm',
          isConfigured: true,
          isValid: true,
          lastValidatedAt: null,
        }}
      />
    );
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('shows "Configured" badge when configured but not validated', () => {
    render(
      <ProviderRow
        {...defaultProps}
        provider="anthropic"
        serviceType="llm"
        status={{
          provider: 'anthropic',
          serviceType: 'llm',
          isConfigured: true,
          isValid: null,
          lastValidatedAt: null,
        }}
      />
    );
    expect(screen.getByText('Configured')).toBeInTheDocument();
  });

  it('Anthropic shows api_key + base_url fields when expanded', async () => {
    const user = userEvent.setup();
    render(
      <ProviderRow {...defaultProps} provider="anthropic" serviceType="llm" status={undefined} />
    );

    const trigger = screen.getByRole('button', { name: /Configure Anthropic/i });
    await user.click(trigger);

    expect(screen.getByTestId('api-key-input-anthropic')).toBeInTheDocument();
    expect(screen.getByLabelText(/Base URL/)).toBeInTheDocument();
  });

  it('Google Gemini shows api_key + base_url fields when expanded', async () => {
    const user = userEvent.setup();
    render(
      <ProviderRow {...defaultProps} provider="google" serviceType="embedding" status={undefined} />
    );

    const trigger = screen.getByRole('button', { name: /Configure Google Gemini/i });
    await user.click(trigger);

    expect(screen.getByTestId('api-key-input-google')).toBeInTheDocument();
    expect(screen.getByLabelText(/Base URL/)).toBeInTheDocument();
  });

  it('Ollama shows base_url + model_name + api_key fields when expanded', async () => {
    const user = userEvent.setup();
    render(
      <ProviderRow {...defaultProps} provider="ollama" serviceType="llm" status={undefined} />
    );

    const trigger = screen.getByRole('button', { name: /Configure Ollama/i });
    await user.click(trigger);

    expect(screen.getByLabelText('Base URL')).toBeInTheDocument();
    expect(screen.getByLabelText('Model Name')).toBeInTheDocument();
    expect(screen.getByTestId('api-key-input-ollama')).toBeInTheDocument();
  });

  it('Save button is present in expanded state', async () => {
    const user = userEvent.setup();
    render(
      <ProviderRow {...defaultProps} provider="anthropic" serviceType="llm" status={undefined} />
    );

    const trigger = screen.getByRole('button', { name: /Configure Anthropic/i });
    await user.click(trigger);

    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
  });
});
