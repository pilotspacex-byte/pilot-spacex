/**
 * Component tests for ApiKeySetupStep.
 *
 * ONBD-03: Inline API key guidance within onboarding dialog.
 * Source: FR-005, FR-006, US1
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiKeySetupStep } from '../ApiKeySetupStep';
import * as useOnboardingActionsModule from '../../hooks/useOnboardingActions';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock the onboarding API so hook doesn't need a real server
vi.mock('@/services/api/onboarding', () => ({
  onboardingApi: {
    validateProviderKey: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const defaultProps = {
  workspaceId: 'ws-uuid-123',
  workspaceSlug: 'my-workspace',
  onNavigateToSettings: vi.fn(),
};

describe('ApiKeySetupStep', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders format hint and console link', () => {
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    // Format hint
    expect(screen.getByText('sk-ant-')).toBeInTheDocument();

    // Console link
    const link = screen.getByRole('link', { name: /get your key/i });
    expect(link).toHaveAttribute('href', 'https://console.anthropic.com/settings/keys');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('test button is disabled when input is empty', () => {
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    const button = screen.getByRole('button', { name: /test connection/i });
    expect(button).toBeDisabled();
  });

  it('enables test button when input has a value', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    const input = screen.getByPlaceholderText('sk-ant-...');
    await user.type(input, 'sk-ant-test-key');

    const button = screen.getByRole('button', { name: /test connection/i });
    expect(button).not.toBeDisabled();
  });

  it('calls validateKey with anthropic provider and trimmed key on button click', async () => {
    const mutateMock = vi.fn();
    vi.spyOn(useOnboardingActionsModule, 'useValidateProviderKey').mockReturnValue({
      mutate: mutateMock,
      isPending: false,
      data: undefined,
    } as unknown as ReturnType<typeof useOnboardingActionsModule.useValidateProviderKey>);

    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    const input = screen.getByPlaceholderText('sk-ant-...');
    await user.type(input, '  sk-ant-test  ');

    const button = screen.getByRole('button', { name: /test connection/i });
    await user.click(button);

    expect(mutateMock).toHaveBeenCalledWith({ provider: 'anthropic', apiKey: 'sk-ant-test' });
  });

  it('shows connected message with model count on valid response', () => {
    vi.spyOn(useOnboardingActionsModule, 'useValidateProviderKey').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      data: { valid: true, modelsAvailable: ['claude-3-opus'], errorMessage: undefined },
    } as unknown as ReturnType<typeof useOnboardingActionsModule.useValidateProviderKey>);

    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    expect(screen.getByText(/connected/i)).toBeInTheDocument();
    expect(screen.getByText(/1 model/i)).toBeInTheDocument();
  });

  it('shows plural models when multiple available', () => {
    vi.spyOn(useOnboardingActionsModule, 'useValidateProviderKey').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      data: {
        valid: true,
        modelsAvailable: ['claude-3-opus', 'claude-3-sonnet'],
        errorMessage: undefined,
      },
    } as unknown as ReturnType<typeof useOnboardingActionsModule.useValidateProviderKey>);

    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    expect(screen.getByText(/2 models/i)).toBeInTheDocument();
  });

  it('shows error message on invalid key response', () => {
    vi.spyOn(useOnboardingActionsModule, 'useValidateProviderKey').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      data: { valid: false, modelsAvailable: [], errorMessage: 'Invalid API key' },
    } as unknown as ReturnType<typeof useOnboardingActionsModule.useValidateProviderKey>);

    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    expect(screen.getByText('Invalid API key')).toBeInTheDocument();
  });

  it('shows fallback error text when errorMessage is absent', () => {
    vi.spyOn(useOnboardingActionsModule, 'useValidateProviderKey').mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
      data: { valid: false, modelsAvailable: [], errorMessage: undefined },
    } as unknown as ReturnType<typeof useOnboardingActionsModule.useValidateProviderKey>);

    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    expect(screen.getByText('Invalid key')).toBeInTheDocument();
  });

  it('calls onNavigateToSettings when fallback link is clicked', async () => {
    const onNavigateToSettings = vi.fn();
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} onNavigateToSettings={onNavigateToSettings} />, {
      wrapper,
    });

    const fallbackButton = screen.getByRole('button', { name: /open full settings/i });
    await user.click(fallbackButton);

    expect(onNavigateToSettings).toHaveBeenCalledOnce();
  });

  it('shows loading spinner while request is pending', () => {
    vi.spyOn(useOnboardingActionsModule, 'useValidateProviderKey').mockReturnValue({
      mutate: vi.fn(),
      isPending: true,
      data: undefined,
    } as unknown as ReturnType<typeof useOnboardingActionsModule.useValidateProviderKey>);

    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    // Button should be disabled during loading
    const button = screen.getByRole('button', { name: /test connection/i });
    expect(button).toBeDisabled();
  });
});
