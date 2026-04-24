/**
 * HomeComposer — Phase 88 Plan 02 Task 2
 *
 * Navigation-submit adapter wrapping `<ChatInput surface="homepage"
 * slimToolbar />`. The homepage launchpad does NOT stream — submitting the
 * composer pushes the prompt + mode into `/{slug}/chat?prefill=...&mode=...
 * &from=home` and lets the chat page auto-send on first mount.
 *
 * Contract (consumed by `Launchpad.tsx` and Plan 04):
 *   export interface HomeComposerHandle {
 *     setDraft(text: string): void;  // populate textarea AND focus it
 *   }
 *
 * Mode handling: ChatInput is per-session via `pilotSpace.modeBySession`. The
 * homepage has no real session yet, so we use the sentinel session id
 * `"__homepage__"` to isolate launchpad mode state. At submit time we read
 * `getAIStore().pilotSpace.getMode("__homepage__")` and embed the result in
 * the URL query. Plan 04 reads `?mode=` on the chat page and primes the
 * pendingMode → first sendMessage on the new real session picks it up via
 * `getMode(null)` fallback.
 *
 * Wrapped in observer() — we read `pilotSpace.getMode(...)` at render time
 * and pass it down as `currentMode` prop, so we MUST re-render when the
 * sentinel-session mode changes. Without observer, clicking a mode chip
 * mutates the store but the UI never reflects it (verified bug 2026-04-24
 * during browser smoke).
 *
 * @module features/homepage/components/HomeComposer
 */

'use client';

import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import { useRouter } from 'next/navigation';
import { observer } from 'mobx-react-lite';

import { ChatInput } from '@/features/ai/ChatView/ChatInput/ChatInput';
import type { ChatMode } from '@/features/ai/ChatView/ChatInput/types';
import { getAIStore } from '@/stores/ai';

/** Sentinel session id used to isolate the launchpad's mode-selector state
 *  from any real chat session. Plan 04's chat-page query handler reads the
 *  literal `?mode=` value — it does not need to know about this sentinel. */
const HOMEPAGE_SENTINEL_SESSION_ID = '__homepage__';

/**
 * Imperative handle exposed to `Launchpad.tsx` so suggested-prompt chips can
 * populate the composer without re-rendering the entire launchpad tree.
 */
export interface HomeComposerHandle {
  /** Replace the composer draft with `text` AND focus the input. */
  setDraft(text: string): void;
}

interface HomeComposerProps {
  workspaceId: string;
  workspaceSlug: string;
}

export const HomeComposer = observer(forwardRef<HomeComposerHandle, HomeComposerProps>(
  function HomeComposer({ workspaceId, workspaceSlug }, ref) {
    const router = useRouter();

    // Local controlled state — ChatInput is a controlled component (value /
    // onChange). The homepage does not need MobX observability for the draft
    // because we never consume it elsewhere; we just push it into the URL on
    // submit.
    const [draft, setDraft] = useState('');
    const wrapperRef = useRef<HTMLDivElement>(null);

    // Read pilotSpace once per render; the sentinel-session helpers are pure
    // wrappers around the modeBySession map — calling getMode in render is
    // safe (no side effect, no async).
    const pilotSpace = getAIStore().pilotSpace;
    const currentMode: ChatMode = pilotSpace.getMode(HOMEPAGE_SENTINEL_SESSION_ID);

    const handleModeChange = useCallback(
      (next: ChatMode) => {
        pilotSpace.setMode(HOMEPAGE_SENTINEL_SESSION_ID, next);
      },
      [pilotSpace],
    );

    const handleSubmit = useCallback(() => {
      const trimmed = draft.trim();
      if (!trimmed) return;
      // Always re-read mode at submit time so the URL reflects the user's
      // most recent selection (avoid closure staleness across re-renders).
      const mode = pilotSpace.getMode(HOMEPAGE_SENTINEL_SESSION_ID);
      const url =
        `/${workspaceSlug}/chat` +
        `?prefill=${encodeURIComponent(trimmed)}` +
        `&mode=${encodeURIComponent(mode)}` +
        `&from=home`;
      router.push(url);
      // Reset the local draft so the composer is empty if the user navigates
      // back (browser back from /chat → /{slug}).
      setDraft('');
    }, [draft, pilotSpace, router, workspaceSlug]);

    useImperativeHandle(
      ref,
      () => ({
        setDraft(text: string) {
          setDraft(text);
          // ChatInput syncs its contenteditable DOM from `value` via a
          // useEffect — wait one tick for that effect to run before focusing,
          // otherwise the cursor lands in an empty node.
          setTimeout(() => {
            const el = wrapperRef.current?.querySelector<HTMLElement>(
              '[data-testid="chat-input"]',
            );
            el?.focus();
          }, 0);
        },
      }),
      [],
    );

    return (
      <div ref={wrapperRef}>
        <ChatInput
          value={draft}
          onChange={setDraft}
          onSubmit={handleSubmit}
          surface="homepage"
          slimToolbar
          currentMode={currentMode}
          onModeChange={handleModeChange}
          workspaceId={workspaceId}
          workspaceSlug={workspaceSlug}
          // Sentinel session id — exposes the homepage's mode bucket to
          // ChatInput-internal state machinery without colliding with real
          // chat sessions.
          sessionId={HOMEPAGE_SENTINEL_SESSION_ID}
        />
      </div>
    );
  },
));

HomeComposer.displayName = 'HomeComposer';
