/**
 * Phase 88 Plan 02 — Task 1: HomepageGreeting RED phase.
 *
 * Per UI-SPEC §2:
 *  - h1 element, Fraunces 24 / 400 / tracking -1px (asserted via `font-display` utility)
 *  - Hours 0–11 → "Good morning, {firstName}."
 *  - Hours 12–17 → "Good afternoon, {firstName}."
 *  - Hours 18–23 → "Good evening, {firstName}."
 *  - When user has no displayName / store empty → loading variant `Welcome.`
 *  - When user displayName is the email-prefix fallback → `there` (per existing
 *    DailyBrief.tsx:135 firstName logic — only show first name if user actually
 *    set one, not the email-prefix fallback computed by AuthStore.userDisplayName)
 *
 * NOTE: Hour 17 is intentionally pinned to "Good afternoon" per the plan's
 * locked copy table (0–11 / 12–17 / 18–23). DailyBrief uses a different cutoff
 * (`<17` → afternoon, `>=17` → evening) — this divergence is intentional;
 * Launchpad follows the locked spec.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';

// Mocks must be hoisted before component import.
vi.mock('mobx-react-lite', () => ({
  observer: (component: unknown) => component,
}));

// Settable mock surface for AuthStore.
const authMock: {
  user: { email: string; name: string } | null;
  userDisplayName: string;
} = {
  user: null,
  userDisplayName: '',
};

vi.mock('@/stores', () => ({
  useAuthStore: () => authMock,
}));

import { HomepageGreeting } from '../components/HomepageGreeting';

beforeEach(() => {
  authMock.user = null;
  authMock.userDisplayName = '';
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});

function setHour(hour: number): void {
  const d = new Date(2026, 3, 24, hour, 0, 0); // 2026-04-24 local
  vi.setSystemTime(d);
}

describe('HomepageGreeting (Phase 88 Plan 02 — UI-SPEC §2)', () => {
  describe('time-of-day greeting (locked copy table)', () => {
    it('renders "Good morning, Tin." at hour 9', () => {
      setHour(9);
      authMock.user = { email: 'tin@pilot.space', name: 'Tin Dang' };
      authMock.userDisplayName = 'Tin Dang';
      render(<HomepageGreeting />);
      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toHaveTextContent('Good morning, Tin.');
    });

    it('renders "Good afternoon, Tin." at hour 12 (boundary)', () => {
      setHour(12);
      authMock.user = { email: 'tin@pilot.space', name: 'Tin Dang' };
      authMock.userDisplayName = 'Tin Dang';
      render(<HomepageGreeting />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Good afternoon, Tin.'
      );
    });

    it('renders "Good afternoon, Tin." at hour 17 (boundary — diverges from DailyBrief)', () => {
      setHour(17);
      authMock.user = { email: 'tin@pilot.space', name: 'Tin Dang' };
      authMock.userDisplayName = 'Tin Dang';
      render(<HomepageGreeting />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Good afternoon, Tin.'
      );
    });

    it('renders "Good evening, Tin." at hour 18 (boundary)', () => {
      setHour(18);
      authMock.user = { email: 'tin@pilot.space', name: 'Tin Dang' };
      authMock.userDisplayName = 'Tin Dang';
      render(<HomepageGreeting />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Good evening, Tin.'
      );
    });

    it('renders "Good evening, Tin." at hour 23 (boundary)', () => {
      setHour(23);
      authMock.user = { email: 'tin@pilot.space', name: 'Tin Dang' };
      authMock.userDisplayName = 'Tin Dang';
      render(<HomepageGreeting />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Good evening, Tin.'
      );
    });
  });

  describe('firstName fallback', () => {
    it('uses first whitespace-separated token of displayName', () => {
      setHour(9);
      authMock.user = { email: 'tin.dang@pilot.space', name: 'Tin Dang' };
      authMock.userDisplayName = 'Tin Dang';
      render(<HomepageGreeting />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Good morning, Tin.'
      );
    });

    it('falls back to "there" when displayName equals the email prefix (no real name set)', () => {
      // Per existing DailyBrief.tsx:133-136 — AuthStore.userDisplayName falls
      // back to email-prefix when user.name is empty. Treat that fallback as
      // "no real name" → render "there".
      setHour(9);
      authMock.user = { email: 'tin.dang@pilot.space', name: '' };
      authMock.userDisplayName = 'tin.dang';
      render(<HomepageGreeting />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Good morning, there.'
      );
    });
  });

  describe('loading state (no user)', () => {
    it('renders "Welcome." placeholder when user is null', () => {
      setHour(9);
      authMock.user = null;
      authMock.userDisplayName = '';
      render(<HomepageGreeting />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
        'Welcome.'
      );
    });
  });

  describe('typography contract', () => {
    it('uses the font-display utility (Fraunces)', () => {
      setHour(9);
      authMock.user = { email: 'tin@pilot.space', name: 'Tin Dang' };
      authMock.userDisplayName = 'Tin Dang';
      render(<HomepageGreeting />);
      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1.className).toMatch(/font-display/);
    });
  });
});
