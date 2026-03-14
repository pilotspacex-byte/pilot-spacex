/**
 * Tests for APIKeyForm.
 *
 * T179: API key inputs with validation, save flow, error handling.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('mobx-react-lite', () => ({
  observer: <T,>(component: T) => component,
}));

const { mockToast } = vi.hoisted(() => ({
  mockToast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));
vi.mock('sonner', () => ({
  toast: mockToast,
}));

const mockSettings = {
  anthropicKeySet: false,
  openaiKeySet: false,
  isSaving: false,
  error: null as string | null,
  saveSettings: vi.fn(),
  validationErrors: {} as Record<string, string>,
};

vi.mock('@/stores', () => ({
  useStore: () => ({
    ai: { settings: mockSettings },
  }),
}));

import { APIKeyForm } from '../api-key-form';

function getAnthropicInput(): HTMLInputElement {
  return screen.getByPlaceholderText('sk-ant-...') as HTMLInputElement;
}

function getOpenAIInput(): HTMLInputElement {
  return screen.getByPlaceholderText('sk-...') as HTMLInputElement;
}

describe('APIKeyForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSettings.anthropicKeySet = false;
    mockSettings.openaiKeySet = false;
    mockSettings.isSaving = false;
    mockSettings.error = null;
    mockSettings.saveSettings = vi.fn().mockResolvedValue(undefined);
  });

  it('renders form with both API key inputs', () => {
    render(<APIKeyForm />);

    expect(screen.getByText('API Keys')).toBeInTheDocument();
    expect(screen.getByText('Anthropic API Key')).toBeInTheDocument();
    expect(screen.getByText('OpenAI API Key')).toBeInTheDocument();
  });

  it('save button is disabled when no changes', () => {
    render(<APIKeyForm />);

    expect(screen.getByRole('button', { name: /save keys/i })).toBeDisabled();
  });

  it('save button is enabled after typing a key', async () => {
    const user = userEvent.setup();
    render(<APIKeyForm />);

    await user.type(getAnthropicInput(), 'sk-ant-test-key-1234567890');

    expect(screen.getByRole('button', { name: /save keys/i })).not.toBeDisabled();
  });

  it('shows validation error for short API key', async () => {
    const user = userEvent.setup();
    render(<APIKeyForm />);

    await user.type(getAnthropicInput(), 'short');
    await user.click(screen.getByRole('button', { name: /save keys/i }));

    expect(screen.getByText('API key is too short')).toBeInTheDocument();
    expect(mockSettings.saveSettings).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid anthropic key prefix', async () => {
    const user = userEvent.setup();
    render(<APIKeyForm />);

    await user.type(getAnthropicInput(), 'invalid-prefix-key-1234567890');
    await user.click(screen.getByRole('button', { name: /save keys/i }));

    expect(screen.getByText('Anthropic API keys must start with "sk-ant-"')).toBeInTheDocument();
    expect(mockSettings.saveSettings).not.toHaveBeenCalled();
  });

  it('shows validation error for invalid openai key prefix', async () => {
    const user = userEvent.setup();
    render(<APIKeyForm />);

    await user.type(getOpenAIInput(), 'invalid-openai-key-1234567890');
    await user.click(screen.getByRole('button', { name: /save keys/i }));

    expect(screen.getByText('OpenAI API keys must start with "sk-"')).toBeInTheDocument();
    expect(mockSettings.saveSettings).not.toHaveBeenCalled();
  });

  it('calls saveSettings with valid keys and shows success toast', async () => {
    const user = userEvent.setup();
    render(<APIKeyForm />);

    await user.type(getAnthropicInput(), 'sk-ant-valid-key-1234567890');
    await user.click(screen.getByRole('button', { name: /save keys/i }));

    await waitFor(() => {
      expect(mockSettings.saveSettings).toHaveBeenCalledWith({
        api_keys: [{ provider: 'anthropic', api_key: 'sk-ant-valid-key-1234567890' }],
      });
    });

    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith('API keys saved securely');
    });
  });

  it('shows error toast when save fails', async () => {
    mockSettings.saveSettings = vi.fn().mockRejectedValue(new Error('Network error'));

    const user = userEvent.setup();
    render(<APIKeyForm />);

    await user.type(getAnthropicInput(), 'sk-ant-valid-key-1234567890');
    await user.click(screen.getByRole('button', { name: /save keys/i }));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'Failed to save API keys',
        expect.objectContaining({ description: 'Network error' })
      );
    });
  });

  it('shows "No pending changes" when no keys entered', () => {
    render(<APIKeyForm />);

    expect(screen.getByText('No pending changes')).toBeInTheDocument();
  });

  it('shows store error alert when present', () => {
    mockSettings.error = 'Server validation failed';
    render(<APIKeyForm />);

    expect(screen.getByText('Server validation failed')).toBeInTheDocument();
  });

  it('clears inputs after successful save', async () => {
    const user = userEvent.setup();
    render(<APIKeyForm />);

    const input = getAnthropicInput();
    await user.type(input, 'sk-ant-valid-key-1234567890');
    await user.click(screen.getByRole('button', { name: /save keys/i }));

    await waitFor(() => {
      expect(input).toHaveValue('');
    });
  });
});
