/**
 * Component tests for ApiKeySetupStep.
 *
 * ONBD-03: Inline API key setup for both AI services.
 * Tests both Anthropic (LLM) and Google Gemini (Embedding) key inputs.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiKeySetupStep } from '../ApiKeySetupStep';

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

  it('renders both provider sections', () => {
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    expect(screen.getAllByText('Anthropic (AI LLM)').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Google Gemini (Embedding)').length).toBeGreaterThan(0);
  });

  it('renders Anthropic format hint and console link', () => {
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    expect(screen.getByText('sk-ant-')).toBeInTheDocument();

    const links = screen.getAllByRole('link', { name: /get your key/i });
    const anthropicLink = links.find((l) =>
      l.getAttribute('href')?.includes('console.anthropic.com')
    );
    expect(anthropicLink).toBeTruthy();
    expect(anthropicLink).toHaveAttribute('target', '_blank');
  });

  it('renders Google Gemini format hint and console link', () => {
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    expect(screen.getByText('AIza')).toBeInTheDocument();

    const links = screen.getAllByRole('link', { name: /get your key/i });
    const geminiLink = links.find((l) => l.getAttribute('href')?.includes('aistudio.google.com'));
    expect(geminiLink).toBeTruthy();
  });

  it('both test buttons are disabled when inputs are empty', () => {
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    const buttons = screen.getAllByRole('button', { name: /test connection/i });
    expect(buttons).toHaveLength(2);
    buttons.forEach((btn) => expect(btn).toBeDisabled());
  });

  it('enables Anthropic test button when input has a value', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    const input = screen.getByPlaceholderText('sk-ant-...');
    await user.type(input, 'sk-ant-test-key');

    const buttons = screen.getAllByRole('button', { name: /test connection/i });
    // First button (Anthropic) should be enabled
    expect(buttons[0]).not.toBeDisabled();
    // Second button (Gemini) should still be disabled
    expect(buttons[1]).toBeDisabled();
  });

  it('enables Gemini test button when input has a value', async () => {
    const user = userEvent.setup();
    const wrapper = createWrapper();
    render(<ApiKeySetupStep {...defaultProps} />, { wrapper });

    const input = screen.getByPlaceholderText('AIza...');
    await user.type(input, 'AIza-test-key');

    const buttons = screen.getAllByRole('button', { name: /test connection/i });
    // Second button (Gemini) should be enabled
    expect(buttons[1]).not.toBeDisabled();
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
});
