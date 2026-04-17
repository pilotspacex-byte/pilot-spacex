'use client';

/**
 * HomepageV3 — v3 chat-first launchpad.
 *
 * Layout (per .planning/design.md §Homepage Layout v3):
 *
 *   Hero group (pt-16):
 *     WorkspacePill → Fraunces greeting → ChatHeroInput → SuggestedPrompts
 *
 *   72px breathing-room spacer
 *
 *   Below-fold group:
 *     RedFlagRow (stale/blocked/overdue/unlinked chips)
 *     ContinueCard (resume last session)
 *
 * Data flow:
 *   - useAuthStore → firstName for greeting
 *   - useWorkspaceStore → workspaceId for digest + AI context
 *   - useWorkspaceDigest → fuels RedFlagRow and AI context injection
 *   - SessionListStore.fetchSessions(1) → fuels ContinueCard
 *
 * The 4-section v2 dashboard (ActiveRoutines + SprintProgress + RecentWorkSection +
 * DailyBrief + DigestInsights) has been relocated to /[workspaceSlug]/dashboard.
 *
 * Animation:
 *   - motion/react staggered fade+rise on section mount, respects prefers-reduced-motion.
 *
 * Accessibility:
 *   - `<h1>` for greeting, `<h2>` for below-fold sections (via child components).
 *   - RedFlagRow scrolls horizontally on small screens; everything else stacks.
 */

import { useEffect, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { motion, useReducedMotion, type Variants } from 'motion/react';
import { useAuthStore, useWorkspaceStore } from '@/stores/RootStore';
import { getAIStore } from '@/stores/ai/AIStore';
import { SessionListStore } from '@/stores/ai/SessionListStore';
import type { SessionSummary } from '@/stores/ai/types/session';
import { useWorkspaceDigest } from '../hooks/useWorkspaceDigest';
import { ChatHeroInput } from './ChatHeroInput';
import { ExamplePrompts } from './ExamplePrompts';
import { WorkspacePill } from './WorkspacePill';
import { RedFlagRow } from './RedFlagRow';
import { ContinueCard } from './ContinueCard';

// ── Motion variants ──────────────────────────────────────────────────────────

const containerVariants: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06, delayChildren: 0.04 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.2, 0.8, 0.2, 1] } },
};

// ── Component ────────────────────────────────────────────────────────────────

interface HomepageV3Props {
  workspaceSlug: string;
}

export const HomepageV3 = observer(function HomepageV3({ workspaceSlug }: HomepageV3Props) {
  const authStore = useAuthStore();
  const workspaceStore = useWorkspaceStore();
  const workspaceId = workspaceStore.currentWorkspace?.id ?? '';
  const reduceMotion = useReducedMotion();

  // ── Greeting: prefer first name, fall back to display name, then none ────
  const rawDisplayName = authStore.userDisplayName ?? '';
  const emailPrefix = authStore.user?.email?.split('@')[0] ?? '';
  const firstName =
    rawDisplayName && rawDisplayName !== emailPrefix ? rawDisplayName.split(' ')[0] : '';
  const greeting = firstName ? `Hi ${firstName}, what do you want to work on?` : 'What do you want to work on?';

  // ── Digest powers both AI context injection and RedFlagRow ───────────────
  const { groups, suggestionCount } = useWorkspaceDigest({ workspaceId });

  useEffect(() => {
    const store = getAIStore().pilotSpace;
    if (!store || !workspaceId) return;

    if (store.workspaceId !== workspaceId) {
      store.setWorkspaceId(workspaceId);
    }

    const staleCount = groups
      .filter((g) => g.category === 'stale_issues')
      .reduce((sum, g) => sum + g.items.length, 0);
    const cycleRiskCount = groups
      .filter((g) => g.category === 'cycle_risk')
      .reduce((sum, g) => sum + g.items.length, 0);
    const noteGroups = groups.filter((g) => g.category === 'unlinked_notes');
    const recentNotes = noteGroups.flatMap((g) =>
      g.items.map((item) => ({ id: item.entityId ?? item.id, title: item.title }))
    );

    const parts: string[] = [];
    if (staleCount > 0) parts.push(`${staleCount} stale issues`);
    if (cycleRiskCount > 0) parts.push(`${cycleRiskCount} cycle risks`);
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
  }, [workspaceId, groups, suggestionCount]);

  // ── Latest session for ContinueCard (one-shot fetch, no MobX subscription) ──
  const [latestSession, setLatestSession] = useState<SessionSummary | null>(null);

  useEffect(() => {
    const pilotSpace = getAIStore().pilotSpace;
    if (!pilotSpace) return;

    let cancelled = false;
    const store = new SessionListStore(pilotSpace);
    store
      .fetchSessions(1)
      .then(() => {
        if (cancelled) return;
        setLatestSession(store.recentSessions[0] ?? null);
      })
      .catch(() => {
        // Non-fatal — ContinueCard simply won't render.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // ── Motion wrappers — bypass stagger when reduced motion is requested ────
  const rootInitial = reduceMotion ? 'visible' : 'hidden';

  return (
    <div className="flex-1 overflow-y-auto bg-background">
      <motion.div
        className="mx-auto flex min-h-full max-w-3xl flex-col px-6"
        variants={containerVariants}
        initial={rootInitial}
        animate="visible"
      >
        {/* ── Hero group ──────────────────────────────────────────────── */}
        <motion.section className="pt-16 pb-4" variants={itemVariants}>
          <div className="flex justify-center">
            <WorkspacePill />
          </div>

          <h1 className="mt-9 text-center font-display text-[34px] font-normal leading-[1.12] tracking-[-0.02em] text-foreground">
            {greeting}
          </h1>

          <div className="mx-auto mt-6 max-w-[680px]">
            <ChatHeroInput workspaceSlug={workspaceSlug} />
          </div>

          <div className="mt-4">
            <ExamplePrompts workspaceSlug={workspaceSlug} />
          </div>
        </motion.section>

        {/* ── 72px breathing room ─────────────────────────────────────── */}
        <div className="h-[72px]" aria-hidden="true" />

        {/* ── Below-fold group ────────────────────────────────────────── */}
        <motion.section
          className="flex flex-col gap-6 pb-16"
          variants={containerVariants}
          // Let the below-fold section stagger its own children
        >
          <motion.div variants={itemVariants}>
            <RedFlagRow workspaceSlug={workspaceSlug} workspaceId={workspaceId} />
          </motion.div>
          <motion.div variants={itemVariants}>
            <ContinueCard latestSession={latestSession} workspaceSlug={workspaceSlug} />
          </motion.div>
        </motion.section>
      </motion.div>
    </div>
  );
});
