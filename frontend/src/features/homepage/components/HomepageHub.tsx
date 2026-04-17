'use client';

/**
 * HomepageHub — v3 chat-first launchpad entry point.
 *
 * v3 migration (Phase 5, .planning/quick/260417-eum-v3-design-system-migration-tokens-featur):
 *   The v2 4-section dashboard (ChatHero + RecentWork + ActiveRoutines + SprintProgress +
 *   RecentConversations) has been replaced by HomepageV3 (Hero → RedFlagRow → ContinueCard).
 *   The v2 sections remain available for `/[workspaceSlug]/dashboard` and are still
 *   imported through their own module paths; they are no longer composed here.
 *
 *   `buildContextualPrompts` stays exported from this module because unit tests
 *   consume it directly (see __tests__/HomepageHub.test.ts) and it still drives
 *   contextual prompt generation used by ChatHeroInput downstream.
 */

import type { DigestCategoryGroup } from '../hooks/useWorkspaceDigest';
import { HomepageV3 } from './HomepageV3';

// ── Backward-compatible export ───────────────────────────────────────────────

/** Fallback prompts when no digest data is available */
const FALLBACK_PROMPTS = [
  'What should I focus on today?',
  'Summarize my in-progress work',
  'Generate my daily standup update',
  'Find stale issues that need attention',
] as const;

export function buildContextualPrompts(groups: DigestCategoryGroup[]): readonly string[] {
  if (groups.length === 0) return FALLBACK_PROMPTS;

  const prompts: string[] = [];

  for (const group of groups) {
    if (prompts.length >= 4) break;
    const count = group.items.length;

    switch (group.category) {
      case 'stale_issues':
        prompts.push(`Review ${count} stale issue${count !== 1 ? 's' : ''} needing attention`);
        break;
      case 'cycle_risk':
        prompts.push('Sprint ends soon — prioritize remaining items?');
        break;
      case 'blocked_dependencies':
        prompts.push(`${count} item${count !== 1 ? 's are' : ' is'} blocked — help resolve?`);
        break;
      case 'unlinked_notes':
        prompts.push(
          `${count} note${count !== 1 ? 's have' : ' has'} extractable issues — review?`
        );
        break;
      case 'overdue_items':
        prompts.push(`${count} overdue item${count !== 1 ? 's' : ''} need attention`);
        break;
      case 'unassigned_priority':
        prompts.push(
          `${count} priority item${count !== 1 ? 's are' : ' is'} unassigned — assign?`
        );
        break;
    }
  }

  let fallbackIdx = 0;
  while (prompts.length < 4 && fallbackIdx < FALLBACK_PROMPTS.length) {
    const candidate = FALLBACK_PROMPTS[fallbackIdx]!;
    if (!prompts.includes(candidate)) {
      prompts.push(candidate);
    }
    fallbackIdx++;
  }

  return prompts;
}

// ── v3 public export ────────────────────────────────────────────────────────

interface HomepageHubProps {
  workspaceSlug: string;
}

/**
 * HomepageHub is preserved as a stable entry point so callers (e.g. the
 * workspace home route) don't need to switch imports during the v3 rollout.
 * Internally it simply delegates to the v3 launchpad.
 */
export function HomepageHub({ workspaceSlug }: HomepageHubProps) {
  return <HomepageV3 workspaceSlug={workspaceSlug} />;
}
