'use client';

/**
 * Chat Page - PilotSpace AI conversational interface
 * @route /[workspaceSlug]/chat
 *
 * Phase 88 Plan 04 — consumes ?prefill=, ?mode=, ?session= query params
 * for the launchpad → chat handoff. Auto-submits exactly once when
 * ?prefill is present (sentRef guard against effect re-runs / remounts).
 */
import { useEffect, useRef } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { observer } from 'mobx-react-lite';
import { ChatView } from '@/features/ai/ChatView';
import { getAIStore } from '@/stores/ai/AIStore';
import { useWorkspaceStore } from '@/stores';
import { CHAT_MODES, type ChatMode } from '@/features/ai/ChatView/ChatInput/types';

/** UUID v4 prefix pattern for distinguishing UUIDs from slugs */
const UUID_PREFIX_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-/i;

/** Type-guard: validate the ?mode= URL param against the locked ChatMode literals. */
function isChatMode(value: string | null): value is ChatMode {
  return value !== null && (CHAT_MODES as readonly string[]).includes(value);
}

export default observer(function ChatPage() {
  const aiStore = getAIStore();
  const store = aiStore.pilotSpace;
  const workspaceStore = useWorkspaceStore();
  const params = useParams<{ workspaceSlug: string }>();
  const slug = params.workspaceSlug;
  const router = useRouter();
  const searchParams = useSearchParams();
  const prefill = searchParams.get('prefill') ?? undefined;
  const modeParam = searchParams.get('mode');
  const sessionParam = searchParams.get('session');

  /** sentRef guards the auto-submit effect against re-runs and remounts. */
  const sentRef = useRef(false);

  // Ensure workspaces are loaded so slug→UUID resolution works
  useEffect(() => {
    if (workspaceStore.workspaceList.length === 0 && !workspaceStore.isLoading) {
      workspaceStore.fetchWorkspaces({ ensureSelection: true });
    }
  }, [workspaceStore]);

  // Resolve workspace UUID with cascading fallback:
  // 1. currentWorkspace from store (populated after fetchWorkspaces)
  // 2. Slug lookup from workspace store
  // 3. currentWorkspaceId from localStorage (may be UUID from previous session)
  // 4. URL slug as last resort (backend accepts null context)
  const currentWs = workspaceStore.currentWorkspace;
  const storedId = workspaceStore.currentWorkspaceId;
  const resolvedWorkspaceId =
    currentWs?.id ??
    (slug && workspaceStore.getWorkspaceBySlug(slug)?.id) ??
    (storedId && UUID_PREFIX_RE.test(storedId) ? storedId : null) ??
    slug;

  // Select workspace in store if resolved from slug (so sidebar/header also update)
  useEffect(() => {
    if (slug && !currentWs) {
      const ws = workspaceStore.getWorkspaceBySlug(slug);
      if (ws) {
        workspaceStore.selectWorkspace(ws.id);
      }
    }
  }, [slug, currentWs, workspaceStore]);

  // Set workspace ID on AI store so conversation context includes it
  useEffect(() => {
    if (store && resolvedWorkspaceId && store.workspaceId !== resolvedWorkspaceId) {
      store.setWorkspaceId(resolvedWorkspaceId);
    }
  }, [store, resolvedWorkspaceId]);

  // Phase 88 Plan 04 — launchpad → chat handoff. When ?prefill (and
  // optionally ?mode, ?session) are present:
  //   1. Wait for resolvedWorkspaceId AND store to be ready.
  //   2. If ?session present and store.sessionId !== id → setSessionId(id),
  //      then setMode(id, mode) directly (skip pendingMode path).
  //   3. Otherwise (new session) → setPendingMode(mode) so the next
  //      sendMessage reads it via getMode(null) → pendingMode fallback.
  //   4. sendMessage(prefill) — backend assigns sessionId; on response
  //      setSessionId migrates pendingMode → modeBySession[realId]
  //      automatically.
  //   5. router.replace('/{slug}/chat') strips the query params.
  // sentRef.current is set to true SYNCHRONOUSLY before awaiting
  // sendMessage so a re-render mid-await cannot fire a second send.
  useEffect(() => {
    if (!store || !resolvedWorkspaceId) return;
    if (sentRef.current) return;

    // ?session-only path: restore session, no auto-send.
    if (sessionParam && !prefill) {
      sentRef.current = true;
      if (store.sessionId !== sessionParam) {
        store.setSessionId(sessionParam);
      }
      return;
    }

    // No prefill → no auto-submit (and no session restore needed).
    if (!prefill) return;

    // Validate ?mode if provided. Invalid mode → log + skip auto-submit.
    if (modeParam !== null && !isChatMode(modeParam)) {
      sentRef.current = true;
      console.warn(
        `[chat-page] invalid ?mode= value: ${modeParam}. Skipping auto-submit.`,
      );
      return;
    }

    const validatedMode: ChatMode | null = isChatMode(modeParam) ? modeParam : null;

    // Mark sent BEFORE the await so a remount mid-async cannot double-fire.
    sentRef.current = true;

    if (sessionParam) {
      // Session-restore path: setSessionId then setMode (skip pendingMode).
      if (store.sessionId !== sessionParam) {
        store.setSessionId(sessionParam);
      }
      if (validatedMode) {
        store.setMode(sessionParam, validatedMode);
      }
    } else if (validatedMode) {
      // New-session path: stage the mode for the upcoming first send.
      store.setPendingMode(validatedMode);
    }

    // Fire-and-forget — sendMessage handles its own errors via store.error.
    // We do NOT await; the page still renders the input + ChatView shell.
    void store.sendMessage(prefill);

    // Strip params so back/forward + refresh do not re-fire the auto-submit.
    router.replace(`/${slug}/chat`);
  }, [store, resolvedWorkspaceId, prefill, modeParam, sessionParam, router, slug]);

  if (!store) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Loading AI Chat...</p>
      </div>
    );
  }

  return (
    <div className="h-full">
      <ChatView
        store={store}
        approvalStore={aiStore.approval}
        userName="User"
        className="h-full"
        prefillValue={prefill}
      />
    </div>
  );
});
