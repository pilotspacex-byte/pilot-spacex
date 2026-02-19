/**
 * useIntentRehydration — fetches active intents + pending approvals on mount/refresh.
 *
 * Called by ChatView to restore intent state without a flash of empty state.
 * Runs when workspaceId changes or on first mount.
 *
 * Spec: specs/015-ai-workforce-platform/spec-m7-chat-engine.md §Chat session rehydration
 * T-062
 */
import { useEffect, useRef } from 'react';
import { runInAction } from 'mobx';
import { aiApi } from '@/services/api/ai';
import type { PilotSpaceStore } from '@/stores/ai/PilotSpaceStore';

export function useIntentRehydration(store: PilotSpaceStore): void {
  const hydrated = useRef<string | null>(null);

  useEffect(() => {
    const workspaceId = store.workspaceId;
    if (!workspaceId || hydrated.current === workspaceId) return;
    hydrated.current = workspaceId;

    const rehydrate = async () => {
      try {
        // Fetch detected (pending) intents
        const detectedIntents = await aiApi.listIntents(workspaceId, 'detected');
        runInAction(() => {
          for (const intent of detectedIntents) {
            // Only add if not already tracked (avoid overwriting live state)
            if (!store.intents.has(intent.id)) {
              store.upsertIntent({
                intentId: intent.id,
                what: intent.what,
                why: intent.why,
                constraints: Array.isArray(intent.constraints)
                  ? (intent.constraints as string[])
                  : [],
                confidence: intent.confidence,
                status: 'detected',
              });
            }
          }
        });
      } catch {
        // Non-critical: rehydration failure doesn't block the UI
      }

      try {
        // Fetch executing intents to restore SkillProgressCards
        const executingIntents = await aiApi.listIntents(workspaceId, 'executing');
        runInAction(() => {
          for (const intent of executingIntents) {
            if (!store.intents.has(intent.id)) {
              store.upsertIntent({
                intentId: intent.id,
                what: intent.what,
                why: intent.why,
                confidence: intent.confidence,
                status: 'executing',
              });
            }
          }
        });
      } catch {
        // Non-critical
      }
    };

    rehydrate();
  }, [store, store.workspaceId]);
}
