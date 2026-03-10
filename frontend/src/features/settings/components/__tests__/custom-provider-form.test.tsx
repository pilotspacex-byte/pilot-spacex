/**
 * Tests for CustomProviderForm.
 *
 * 13-03: Custom OpenAI-compatible provider registration form.
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

const { mockPost } = vi.hoisted(() => ({
  mockPost: vi.fn(),
}));
vi.mock('@/services/api/client', () => ({
  apiClient: {
    post: mockPost,
  },
}));

import { CustomProviderForm } from '../custom-provider-form';

describe('CustomProviderForm', () => {
  const mockOnSuccess = vi.fn();
  const defaultProps = {
    workspaceId: 'ws-1',
    onSuccess: mockOnSuccess,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ id: 'cfg-1', provider: 'custom' });
  });

  it('renders form with all required fields', () => {
    render(<CustomProviderForm {...defaultProps} />);

    expect(screen.getByLabelText(/display name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/base url/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api key/i)).toBeInTheDocument();
  });

  it('has a submit button', () => {
    render(<CustomProviderForm {...defaultProps} />);
    expect(screen.getByRole('button', { name: /add provider/i })).toBeInTheDocument();
  });

  it('submit button is disabled when fields are empty', () => {
    render(<CustomProviderForm {...defaultProps} />);
    expect(screen.getByRole('button', { name: /add provider/i })).toBeDisabled();
  });

  it('submits with correct payload on valid input', async () => {
    const user = userEvent.setup();
    render(<CustomProviderForm {...defaultProps} />);

    await user.type(screen.getByLabelText(/display name/i), 'My LLM');
    await user.type(screen.getByLabelText(/base url/i), 'https://api.example.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-key-1234');

    await user.click(screen.getByRole('button', { name: /add provider/i }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        '/ai/configurations',
        expect.objectContaining({
          provider: 'custom',
          display_name: 'My LLM',
          base_url: 'https://api.example.com/v1',
          api_key: 'sk-test-key-1234',
        })
      );
    });
  });

  it('calls onSuccess and shows toast on 201', async () => {
    const user = userEvent.setup();
    render(<CustomProviderForm {...defaultProps} />);

    await user.type(screen.getByLabelText(/display name/i), 'My LLM');
    await user.type(screen.getByLabelText(/base url/i), 'https://api.example.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-key-1234');

    await user.click(screen.getByRole('button', { name: /add provider/i }));

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
      expect(mockToast.success).toHaveBeenCalledWith(expect.stringMatching(/provider added/i));
    });
  });

  it('shows error message on submit failure', async () => {
    mockPost.mockRejectedValueOnce(new Error('Invalid base URL'));

    const user = userEvent.setup();
    render(<CustomProviderForm {...defaultProps} />);

    await user.type(screen.getByLabelText(/display name/i), 'My LLM');
    await user.type(screen.getByLabelText(/base url/i), 'https://api.example.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-key-1234');

    await user.click(screen.getByRole('button', { name: /add provider/i }));

    await waitFor(() => {
      expect(screen.getByText('Invalid base URL')).toBeInTheDocument();
    });
  });

  it('clears form after successful submit', async () => {
    const user = userEvent.setup();
    render(<CustomProviderForm {...defaultProps} />);

    const nameInput = screen.getByLabelText(/display name/i);
    await user.type(nameInput, 'My LLM');
    await user.type(screen.getByLabelText(/base url/i), 'https://api.example.com/v1');
    await user.type(screen.getByLabelText(/api key/i), 'sk-test-key-1234');

    await user.click(screen.getByRole('button', { name: /add provider/i }));

    await waitFor(() => {
      expect(nameInput).toHaveValue('');
    });
  });
});
