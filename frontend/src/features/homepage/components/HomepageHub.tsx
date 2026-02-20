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

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { useAuthStore, useWorkspaceStore } from '@/stores/RootStore';
import { getAIStore } from '@/stores/ai/AIStore';
import { ChatView } from '@/features/ai/ChatView';
import { DailyBrief } from './DailyBrief';

/** Homepage-specific suggested prompts for daily routine */
const HOMEPAGE_PROMPTS = [
  'What should I focus on today?',
  'Summarize my in-progress work',
  'Generate my daily standup update',
  'Find stale issues that need attention',
] as const;

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

  // Set workspace on AI store when it changes
  useEffect(() => {
    if (store && workspaceId && store.workspaceId !== workspaceId) {
      store.setWorkspaceId(workspaceId);
    }
  }, [store, workspaceId]);

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
            suggestedPrompts={HOMEPAGE_PROMPTS}
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
