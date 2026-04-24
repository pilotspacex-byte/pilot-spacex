/**
 * HomepageGreeting — Phase 88 Plan 02 Task 1
 *
 * Calm launchpad hero greeting per UI-SPEC §2:
 *  - <h1>, Fraunces 24 / 400 / tracking -1px (mapped to project `font-display`
 *    + `text-2xl font-normal tracking-tighter` utilities)
 *  - Hour bands (locked copy):
 *      0–11  → "Good morning, {firstName}."
 *      12–17 → "Good afternoon, {firstName}."
 *      18–23 → "Good evening, {firstName}."
 *  - firstName resolves from `authStore.userDisplayName` (first whitespace
 *    token), falling back to "there" when the displayName is the email-prefix
 *    fallback (i.e. user has not set a real name) — same heuristic as
 *    DailyBrief.tsx:133-136.
 *  - When user is null (auth still loading), render "Welcome." placeholder so
 *    the layout height stays stable.
 *  - 240ms fade-in on mount; suppressed under prefers-reduced-motion.
 *
 * NOTE: NOT wrapped in `observer()` — this component reads only synchronous
 * MobX getters at render time. Rerendering on hour change is not a concern
 * (page mount window is short; greeting refreshes on next navigation).
 *
 * @module features/homepage/components/HomepageGreeting
 */

import { useAuthStore } from '@/stores';
import { cn } from '@/lib/utils';

type TimeOfDay = 'morning' | 'afternoon' | 'evening';

function getTimeOfDay(hour: number): TimeOfDay {
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
}

function resolveFirstName(
  userDisplayName: string,
  emailPrefix: string,
): string {
  // If displayName is empty OR matches the email-prefix fallback that
  // AuthStore.userDisplayName synthesizes when user.name is empty, treat
  // as "no real name".
  if (!userDisplayName || userDisplayName === emailPrefix) {
    return 'there';
  }
  const first = userDisplayName.trim().split(/\s+/)[0];
  return first || 'there';
}

export function HomepageGreeting(): JSX.Element {
  const authStore = useAuthStore();
  const user = authStore.user;
  const userDisplayName = authStore.userDisplayName ?? '';
  const emailPrefix = user?.email?.split('@')[0] ?? '';

  // Loading variant — preserve a single-line h1 height so launchpad rhythm
  // does not jump when auth resolves.
  const isLoading = user === null;
  const greeting = isLoading
    ? 'Welcome.'
    : `Good ${getTimeOfDay(new Date().getHours())}, ${resolveFirstName(
        userDisplayName,
        emailPrefix,
      )}.`;

  return (
    <h1
      className={cn(
        // Typography — UI-SPEC §2 (Fraunces 24/400, tight tracking)
        'font-display text-2xl font-normal tracking-tighter text-foreground',
        // Mount fade-in (240ms ease-out, no translate). Reduced-motion users
        // see the final state immediately.
        'animate-in fade-in duration-200 motion-reduce:animate-none',
      )}
    >
      {greeting}
    </h1>
  );
}
