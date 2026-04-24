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

import { HomepageGreeting } from './components/HomepageGreeting';
import {
  HomeComposer,
  type HomeComposerHandle,
} from './components/HomeComposer';
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
        TODO(88-03): <RedFlagStrip
          workspaceId={workspaceId}
          workspaceSlug={workspaceSlug}
        />

        Plan 03 (Wave 3) drops the strip in here. When the strip renders zero
        flags it MUST return null so the rhythm collapses to the next gap. The
        wrapper below holds the 32px gap (mt-8) regardless — the empty strip
        adds no height, so this still reads as "32px composer → prompts".
      */}
      <div className="mt-8" />

      {/* Suggested prompts — 24px from red-flag strip slot */}
      <div className="mt-6">
        <SuggestedPromptsRow onPick={handlePickPrompt} />
      </div>

      {/*
        TODO(88-04): <ContinueCard
          workspaceId={workspaceId}
          workspaceSlug={workspaceSlug}
        />

        Plan 04 (Wave 4) drops the card in here AND owns:
          - The `frontend/src/features/homepage/index.ts` barrel swap
            (export Launchpad, drop HomepageHub).
          - The `app/(workspace)/[workspaceSlug]/page.tsx` page swap.
          - The chat-page `?prefill=...&mode=...&from=home` query handler.
        ContinueCard returns null when there is no prior session.
      */}
      <div className="mt-8" />
    </section>
  );
}
