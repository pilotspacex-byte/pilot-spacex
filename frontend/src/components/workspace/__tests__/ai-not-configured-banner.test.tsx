/**
 * Tests for AiNotConfiguredBanner.
 *
 * AIGOV-05: Banner persistence with 7-day localStorage TTL.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const mockUseAIStatus = vi.fn().mockReturnValue({ data: { byok_configured: false } });

vi.mock('@/hooks/use-ai-status', () => ({
  useAIStatus: (...args: unknown[]) => mockUseAIStatus(...args),
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  },
}));

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>();
  return {
    ...actual,
    apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  };
});

import { AiNotConfiguredBanner } from '../ai-not-configured-banner';

const DISMISS_KEY = 'ai_banner_dismissed_at';
const DISMISS_TTL_MS = 7 * 24 * 60 * 60 * 1000;

describe('AiNotConfiguredBanner', () => {
  beforeEach(() => {
    localStorage.clear();
    mockUseAIStatus.mockReturnValue({ data: { byok_configured: false } });
  });

  it('renders banner for owner when AI is not configured', () => {
    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/AI features are disabled/i)).toBeInTheDocument();
  });

  it('does not render for non-owner', () => {
    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={false} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('does not render when AI is already configured', () => {
    mockUseAIStatus.mockReturnValue({ data: { byok_configured: true } });

    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('banner stays dismissed within 7-day TTL on re-mount', () => {
    const now = Date.now();
    const sixDaysAgo = now - 6 * 24 * 60 * 60 * 1000;
    localStorage.setItem(DISMISS_KEY, String(sixDaysAgo));

    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('dismiss writes timestamp to localStorage using fireEvent', () => {
    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    const dismissBtn = screen.getByRole('button', { name: /dismiss/i });
    const beforeClick = Date.now();
    fireEvent.click(dismissBtn);
    const afterClick = Date.now();

    const stored = localStorage.getItem(DISMISS_KEY);
    expect(stored).not.toBeNull();
    const storedNum = parseInt(stored!, 10);
    expect(storedNum).toBeGreaterThanOrEqual(beforeClick);
    expect(storedNum).toBeLessThanOrEqual(afterClick);
  });

  it('banner is hidden after dismiss click using fireEvent', () => {
    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();

    const dismissBtn = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissBtn);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('banner reappears after 7-day TTL expires', () => {
    const now = 1_700_000_000_000;
    const eightDaysAgo = now - 8 * 24 * 60 * 60 * 1000;
    localStorage.setItem(DISMISS_KEY, String(eightDaysAgo));
    vi.spyOn(Date, 'now').mockReturnValueOnce(now);

    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it('uses localStorage (not sessionStorage) for persistence', () => {
    const sessionStorageSpy = vi.spyOn(sessionStorage, 'setItem');
    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    const dismissBtn = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissBtn);

    expect(sessionStorageSpy).not.toHaveBeenCalled();
    expect(localStorage.getItem(DISMISS_KEY)).not.toBeNull();
    vi.restoreAllMocks();
  });

  it('TTL boundary: exactly at TTL shows banner', () => {
    const now = 1_700_000_000_000;
    // Exactly DISMISS_TTL_MS ago — Date.now() - ts = DISMISS_TTL_MS, NOT < DISMISS_TTL_MS
    const exactlyAtTTL = now - DISMISS_TTL_MS;
    localStorage.setItem(DISMISS_KEY, String(exactlyAtTTL));
    vi.spyOn(Date, 'now').mockReturnValueOnce(now);

    render(<AiNotConfiguredBanner workspaceSlug="test-ws" isOwner={true} />);

    // Date.now() - ts = DISMISS_TTL_MS, which is NOT < DISMISS_TTL_MS → show banner
    expect(screen.getByRole('alert')).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
