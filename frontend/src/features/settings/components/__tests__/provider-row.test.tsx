/**
 * Tests for ProviderRow component.
 *
 * Verifies unified provider row with expandable config fields.
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

  it('renders Anthropic provider name', () => {
    render(<ProviderRow {...defaultProps} provider="anthropic" status={undefined} />);
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('renders OpenAI provider name', () => {
    render(<ProviderRow {...defaultProps} provider="openai" status={undefined} />);
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
  });

  it('renders Google Gemini provider name', () => {
    render(<ProviderRow {...defaultProps} provider="google" status={undefined} />);
    expect(screen.getByText('Google Gemini')).toBeInTheDocument();
  });

  it('renders Kimi provider name', () => {
    render(<ProviderRow {...defaultProps} provider="kimi" status={undefined} />);
    expect(screen.getByText('Kimi (Moonshot)')).toBeInTheDocument();
  });

  it('renders GLM provider name', () => {
    render(<ProviderRow {...defaultProps} provider="glm" status={undefined} />);
    expect(screen.getByText('GLM (Zhipu)')).toBeInTheDocument();
  });

  it('renders AI Agent provider name', () => {
    render(<ProviderRow {...defaultProps} provider="ai_agent" status={undefined} />);
    expect(screen.getByText('AI Agent')).toBeInTheDocument();
  });

  it('shows "Not configured" badge when status is undefined', () => {
    render(<ProviderRow {...defaultProps} provider="anthropic" status={undefined} />);
    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });

  it('shows "Connected" badge when provider is configured and valid', () => {
    render(
      <ProviderRow
        {...defaultProps}
        provider="anthropic"
        status={{
          provider: 'anthropic',
          isConfigured: true,
          isValid: true,
          lastValidatedAt: null,
        }}
      />
    );
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('shows "Configured" badge when provider is configured but not validated', () => {
    render(
      <ProviderRow
        {...defaultProps}
        provider="anthropic"
        status={{
          provider: 'anthropic',
          isConfigured: true,
          isValid: null,
          lastValidatedAt: null,
        }}
      />
    );
    expect(screen.getByText('Configured')).toBeInTheDocument();
  });

  it('expands to show config fields when clicked', async () => {
    const user = userEvent.setup();
    render(<ProviderRow {...defaultProps} provider="anthropic" status={undefined} />);

    const trigger = screen.getByRole('button', { name: /Configure Anthropic/i });
    await user.click(trigger);

    expect(screen.getByTestId('api-key-input-anthropic')).toBeInTheDocument();
  });

  it('Google Gemini row shows api_key + base_url fields when expanded', async () => {
    const user = userEvent.setup();
    render(<ProviderRow {...defaultProps} provider="google" status={undefined} />);

    const trigger = screen.getByRole('button', { name: /Configure Google Gemini/i });
    await user.click(trigger);

    expect(screen.getByTestId('api-key-input-google')).toBeInTheDocument();
    expect(screen.getByLabelText('Base URL')).toBeInTheDocument();
    expect(screen.queryByLabelText('Model Name')).not.toBeInTheDocument();
  });

  it('AI Agent row shows base_url + model_name + api_key fields when expanded', async () => {
    const user = userEvent.setup();
    render(<ProviderRow {...defaultProps} provider="ai_agent" status={undefined} />);

    const trigger = screen.getByRole('button', { name: /Configure AI Agent/i });
    await user.click(trigger);

    expect(screen.getByLabelText('Base URL')).toBeInTheDocument();
    expect(screen.getByLabelText('Model Name')).toBeInTheDocument();
    expect(screen.getByTestId('api-key-input-ai_agent')).toBeInTheDocument();
  });

  it('Anthropic row shows only api_key field when expanded', async () => {
    const user = userEvent.setup();
    render(<ProviderRow {...defaultProps} provider="anthropic" status={undefined} />);

    const trigger = screen.getByRole('button', { name: /Configure Anthropic/i });
    await user.click(trigger);

    expect(screen.getByTestId('api-key-input-anthropic')).toBeInTheDocument();
    expect(screen.queryByLabelText('Base URL')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Model Name')).not.toBeInTheDocument();
  });

  it('Save button is present in expanded state', async () => {
    const user = userEvent.setup();
    render(<ProviderRow {...defaultProps} provider="openai" status={undefined} />);

    const trigger = screen.getByRole('button', { name: /Configure OpenAI/i });
    await user.click(trigger);

    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
  });
});
