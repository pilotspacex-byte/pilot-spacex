'use client';

/**
 * HomepageHub (H047) -- Two-column layout: DailyBrief + ChatView.
 *
 * Layout (desktop, lg+):
 * - Left column (flex-1): DailyBrief document
 * - Right column (w-[380px]): Full ChatView as persistent command center
 *
 * Layout (mobile, < lg):
 * - Single column: DailyBrief only. Users navigate to /chat on mobile.
 *
 * Replaces the previous 3-zone layout (CompactChatView, ActivityFeed, DigestPanel)
 * with a cleaner 2-panel approach.
 */

import { useEffect, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { useAuthStore, useWorkspaceStore } from '@/stores/RootStore';
import { getAIStore } from '@/stores/ai/AIStore';
import { ChatView } from '@/features/ai/ChatView';
import { DailyBrief } from './DailyBrief';
import { useWorkspaceDigest } from '../hooks/useWorkspaceDigest';
import type { DigestCategoryGroup } from '../hooks/useWorkspaceDigest';

/** Fallback prompts when no digest data is available */
const FALLBACK_PROMPTS = [
  'What should I focus on today?',
  'Summarize my in-progress work',
  'Generate my daily standup update',
  'Find stale issues that need attention',
] as const;

/**
 * Build contextual prompts from digest category groups.
 * Returns up to 4 prompts derived from active digest categories,
 * padded with fallback prompts if fewer than 4 categories are present.
 */
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
        prompts.push(`${count} priority item${count !== 1 ? 's are' : ' is'} unassigned — assign?`);
        break;
    }
  }

  // Pad with fallback prompts to reach 4
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

interface HomepageHubProps {
  /** Workspace slug for navigation links */
  workspaceSlug: string;
}

export const HomepageHub = observer(function HomepageHub({ workspaceSlug }: HomepageHubProps) {
  const authStore = useAuthStore();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';
  const aiStore = getAIStore();
  const store = aiStore.pilotSpace;
  const userName = authStore.userDisplayName || 'User';

  const { groups, suggestionCount } = useWorkspaceDigest({ workspaceId });

  const suggestedPrompts = useMemo(() => buildContextualPrompts(groups), [groups]);

  // Set workspace on AI store when it changes
  useEffect(() => {
    if (store && workspaceId && store.workspaceId !== workspaceId) {
      store.setWorkspaceId(workspaceId);
    }
  }, [store, workspaceId]);

  // Inject homepage context into AI store for context-aware chat (T033)
  useEffect(() => {
    if (!store || !workspaceId) return;

    const staleCount = groups
      .filter((g) => g.category === 'stale_issues')
      .reduce((sum, g) => sum + g.items.length, 0);
    const cycleRiskCount = groups
      .filter((g) => g.category === 'cycle_risk')
      .reduce((sum, g) => sum + g.items.length, 0);
    const blockedCount = groups
      .filter((g) => g.category === 'blocked_dependencies')
      .reduce((sum, g) => sum + g.items.length, 0);
    const noteGroups = groups.filter((g) => g.category === 'unlinked_notes');
    const recentNotes = noteGroups.flatMap((g) =>
      g.items.map((item) => ({ id: item.entityId ?? item.id, title: item.title }))
    );

    const parts: string[] = [];
    if (staleCount > 0) parts.push(`${staleCount} stale issues`);
    if (cycleRiskCount > 0) parts.push(`${cycleRiskCount} cycle risks`);
    if (blockedCount > 0) parts.push(`${blockedCount} blocked items`);
    if (recentNotes.length > 0) parts.push(`${recentNotes.length} recent notes active`);
    const digestSummary =
      parts.length > 0
        ? `Workspace has ${parts.join(', ')}.`
        : `Workspace has ${suggestionCount} suggestions.`;

    store.setHomepageContext({
      digestSummary,
      totalSuggestionCount: suggestionCount,
      staleIssueCount: staleCount,
      cycleRiskCount,
      recentNotes,
    });

    return () => {
      store.clearHomepageContext();
    };
  }, [store, workspaceId, groups, suggestionCount]);

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 lg:flex-row">
      {/* Left: Daily Brief document (scrolls independently) */}
      <section className="min-w-0 flex-1 overflow-y-auto px-6 py-6 lg:px-10 lg:py-8">
        <DailyBrief workspaceSlug={workspaceSlug} />
      </section>

      {/* Right: ChatView command center (desktop only, viewport-pinned) */}
      <aside
        className="hidden lg:flex lg:w-[380px] lg:shrink-0 lg:border-l lg:border-border"
        aria-label="AI command center"
      >
        {store ? (
          <ChatView
            store={store}
            userName={userName}
            className="h-full w-full"
            autoFocus={false}
            suggestedPrompts={suggestedPrompts}
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">Loading AI...</p>
          </div>
        )}
      </aside>
    </div>
  );
});
