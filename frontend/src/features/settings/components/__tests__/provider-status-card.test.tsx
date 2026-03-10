/**
 * Tests for ProviderStatusCard - generalized multi-provider support.
 *
 * 13-03: ProviderStatusCard must accept any string provider (not just anthropic/openai).
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProviderStatusCard } from '../provider-status-card';

describe('ProviderStatusCard', () => {
  it('renders anthropic provider with correct display name', () => {
    render(<ProviderStatusCard provider="anthropic" isKeySet={true} status="connected" />);
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('renders openai provider with correct display name', () => {
    render(<ProviderStatusCard provider="openai" isKeySet={false} />);
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
  });

  it('renders kimi provider with correct display name', () => {
    render(<ProviderStatusCard provider="kimi" isKeySet={false} />);
    expect(screen.getByText('Kimi (Moonshot)')).toBeInTheDocument();
  });

  it('renders glm provider with correct display name', () => {
    render(<ProviderStatusCard provider="glm" isKeySet={false} />);
    expect(screen.getByText('GLM (Zhipu)')).toBeInTheDocument();
  });

  it('renders google provider with correct display name', () => {
    render(<ProviderStatusCard provider="google" isKeySet={false} />);
    expect(screen.getByText('Google Gemini')).toBeInTheDocument();
  });

  it('renders unknown provider with generic fallback name', () => {
    render(<ProviderStatusCard provider="some-unknown-provider" isKeySet={false} />);
    // Should show provider string as fallback (capitalized or as-is)
    expect(screen.getByText(/some-unknown-provider|Some-Unknown-Provider/i)).toBeInTheDocument();
  });

  it('shows Not configured badge when key is not set', () => {
    render(<ProviderStatusCard provider="kimi" isKeySet={false} />);
    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });

  it('shows Connected badge when status is connected and key is set', () => {
    render(<ProviderStatusCard provider="kimi" isKeySet={true} status="connected" />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('shows Configured badge when key is set but status unknown', () => {
    render(<ProviderStatusCard provider="glm" isKeySet={true} status="unknown" />);
    expect(screen.getByText('Configured')).toBeInTheDocument();
  });

  it('renders custom provider with display name fallback', () => {
    render(<ProviderStatusCard provider="custom" isKeySet={false} />);
    expect(screen.getByText('Custom Provider')).toBeInTheDocument();
  });
});
