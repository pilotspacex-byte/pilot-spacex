/**
 * Launchpad — Phase 88 Plan 02 Task 4 (assembly)
 *
 * Calm single-column launchpad replacing the legacy `<HomepageHub />`
 * dashboard. Composes the four child components shipped in this plan and
 * leaves explicit slots (with TODO comments) for the two children delivered
 * by Plans 03 (RedFlagStrip) and 04 (ContinueCard).
 *
 * Layout per UI-SPEC §1:
 *  - <section role="main" aria-label="Workspace launchpad">
 *  - max-w-[720px] centered, px-6 (24px) horizontal
 *  - 120px top padding (responsive: 80 < 768, 56 < 640)
 *  - Vertical rhythm via explicit margins on each child wrapper:
 *      Greeting   →  composer:  36px (mt-9)
 *      Composer   →  red flags: 32px (mt-8)
 *      Red flags  →  prompts:   24px (mt-6)
 *      Prompts    →  continue:  32px (mt-8)
 *      Continue   →  bottom:    64px (pb-16)
 *
 * Cross-plan handoffs:
 *  - Plan 03 fills the RedFlagStrip slot below.
 *  - Plan 04 fills the ContinueCard slot below + swaps the barrel export
 *    in `index.ts` and the workspace home page entry to mount this component.
 *
 * NOT wrapped in observer() — children that need observability (HomeComposer
 * indirectly via ChatInput) handle their own subscriptions.
 *
 * @module features/homepage/Launchpad
 */

'use client';

import { useCallback, useRef } from 'react';

import { ContinueCard } from './components/ContinueCard';
import {
  HomeComposer,
  type HomeComposerHandle,
} from './components/HomeComposer';
import { HomepageGreeting } from './components/HomepageGreeting';
import { RedFlagStrip } from './components/RedFlagStrip';
import { SuggestedPromptsRow } from './components/SuggestedPromptsRow';

interface LaunchpadProps {
  workspaceId: string;
  workspaceSlug: string;
}

export function Launchpad({ workspaceId, workspaceSlug }: LaunchpadProps) {
  const composerRef = useRef<HomeComposerHandle>(null);

  // Suggested-prompt chips populate the draft (do NOT submit).
  const handlePickPrompt = useCallback((text: string) => {
    composerRef.current?.setDraft(text);
  }, []);

  return (
    <section
      role="main"
      aria-label="Workspace launchpad"
      className="mx-auto w-full max-w-[720px] px-6 pt-[120px] pb-16 max-md:pt-20 max-sm:pt-14 max-sm:px-4"
    >
      {/* Greeting */}
      <HomepageGreeting />

      {/* Composer — 36px from greeting */}
      <div className="mt-9">
        <HomeComposer
          ref={composerRef}
          workspaceId={workspaceId}
          workspaceSlug={workspaceSlug}
        />
      </div>

      {/*
        Red flag strip (Phase 88 Plan 03 — wired by Plan 04). The strip
        returns null when there are zero flags, so the mt-8 wrapper still
        holds the 32px gap regardless of state ("32px composer → prompts"
        when empty; banners absorb that gap visually when present).
      */}
      <div className="mt-8">
        <RedFlagStrip workspaceId={workspaceId} workspaceSlug={workspaceSlug} />
      </div>

      {/* Suggested prompts — 24px from red-flag strip slot */}
      <div className="mt-6">
        <SuggestedPromptsRow onPick={handlePickPrompt} />
      </div>

      {/*
        Continue card (Phase 88 Plan 04). Returns null when there is no
        prior chat session, collapsing the 32px gap to nothing.
      */}
      <div className="mt-8">
        <ContinueCard workspaceId={workspaceId} workspaceSlug={workspaceSlug} />
      </div>
    </section>
  );
}
