'use client';

/**
 * HomepageHub (H047) — Main 3-zone layout for the Homepage Hub (US-19).
 *
 * Zone 1: Compact ChatView (max-w-[720px], centered)
 * Zone 2: Activity Feed (flex-[3])
 * Zone 3: AI Digest Panel (flex-[2])
 *
 * Includes keyboard shortcuts (H049, H050) and ARIA landmarks (H051).
 * All animations use motion-safe: variants for reduced-motion support (H052).
 */

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import { useHomepageStore } from '@/stores/RootStore';
import type { HomepageZone } from '../types';
import { CompactChatView } from './CompactChatView';
import { ActivityFeed } from './ActivityFeed';
import { DigestPanel } from './DigestPanel';

/** Ordered zones for F6 cycling */
const ZONE_ORDER: readonly HomepageZone[] = ['chat', 'activity', 'digest'] as const;

interface HomepageHubProps {
  /** Workspace slug for navigation links */
  workspaceSlug: string;
  /** Whether an AI provider is configured */
  aiConfigured?: boolean;
}

export const HomepageHub = observer(function HomepageHub({
  workspaceSlug,
  aiConfigured = true,
}: HomepageHubProps) {
  const homepageStore = useHomepageStore();

  // Zone refs for F6 focus cycling
  const chatRef = useRef<HTMLElement>(null);
  const activityRef = useRef<HTMLElement>(null);
  const digestRef = useRef<HTMLElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  const zoneRefs = useMemo(
    () => ({
      chat: chatRef,
      activity: activityRef,
      digest: digestRef,
    }),
    []
  );

  /** Focus the given zone's section element */
  const focusZone = useCallback(
    (zone: HomepageZone) => {
      homepageStore.setActiveZone(zone);
      zoneRefs[zone].current?.focus();
    },
    [homepageStore, zoneRefs]
  );

  // H049: '/' shortcut to focus chat input
  // H050: F6 to cycle zones
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInputFocused =
        target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

      // '/' focuses chat input (only when not typing in another input)
      if (e.key === '/' && !isInputFocused) {
        e.preventDefault();
        chatInputRef.current?.focus();
      }

      // F6 cycles between zones
      if (e.key === 'F6') {
        e.preventDefault();
        const currentIndex = ZONE_ORDER.indexOf(homepageStore.activeZone);
        const nextIndex = e.shiftKey
          ? (currentIndex - 1 + ZONE_ORDER.length) % ZONE_ORDER.length
          : (currentIndex + 1) % ZONE_ORDER.length;
        const nextZone = ZONE_ORDER[nextIndex];
        if (nextZone) {
          focusZone(nextZone);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [homepageStore.activeZone, focusZone]);

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      {/* Zone 1: Compact ChatView */}
      <section
        ref={chatRef}
        role="region"
        aria-label="Quick AI chat"
        tabIndex={-1}
        className="mx-auto w-full max-w-[720px] outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:rounded-lg"
      >
        <CompactChatView inputRef={chatInputRef} />
      </section>

      {/* Zone 2 + Zone 3 wrapper */}
      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Zone 2: Activity Feed */}
        <section
          ref={activityRef}
          role="region"
          aria-label="Recent activity"
          tabIndex={-1}
          className="min-w-0 flex-[3] outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:rounded-lg lg:min-w-[380px]"
        >
          <ActivityFeed workspaceSlug={workspaceSlug} />
        </section>

        {/* Zone 3: AI Digest Panel */}
        <section
          ref={digestRef}
          role="region"
          aria-label="AI workspace insights"
          tabIndex={-1}
          className="min-w-0 flex-[2] outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:rounded-lg lg:min-w-[300px]"
        >
          <DigestPanel aiConfigured={aiConfigured} />
        </section>
      </div>
    </div>
  );
});
