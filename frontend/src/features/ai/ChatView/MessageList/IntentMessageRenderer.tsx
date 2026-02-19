/**
 * IntentMessageRenderer — polymorphic renderer for intent lifecycle messages.
 *
 * Routes message types to the correct component:
 *   text          → existing AssistantMessage/UserMessage (not handled here)
 *   intent_card   → IntentCard
 *   skill_progress → SkillProgressCard
 *   approval      → SkillApprovalCard
 *   conversation  → ConversationBlock (already handled by QuestionBlock)
 *
 * This component is consumed by ChatView to render intent-related messages
 * alongside the standard message list.
 *
 * Spec: specs/015-ai-workforce-platform/spec-m7-chat-engine.md §Polymorphic Message Renderer
 * T-056
 */
'use client';

import { observer } from 'mobx-react-lite';
import { useCallback } from 'react';
import { IntentCard } from './IntentCard';
import { SkillProgressCard } from './SkillProgressCard';
import { SkillApprovalCard } from './SkillApprovalCard';
import type { PilotSpaceStore, WorkIntentState } from '@/stores/ai/PilotSpaceStore';
import { aiApi } from '@/services/api/ai';
import { toast } from 'sonner';

interface IntentMessageRendererProps {
  store: PilotSpaceStore;
  onNavigateToArtifact?: (id: string, type: string) => void;
  onPrefillInput?: (text: string) => void;
}

/**
 * Renders all intents tracked in the store in the correct visual state.
 * Called once per ChatView render — renders all intent cards in intent insertion order.
 */
export const IntentMessageRenderer = observer<IntentMessageRendererProps>(
  function IntentMessageRenderer({ store, onNavigateToArtifact, onPrefillInput }) {
    const handleConfirm = useCallback(
      async (intentId: string) => {
        if (!store.workspaceId) return;
        const snapshot = store.optimisticConfirmIntent(intentId);
        try {
          await aiApi.confirmIntent(store.workspaceId, intentId, store.sessionId ?? undefined);

          // C-NEW-3: ConfirmationBus uses in-process ClassVar dicts. In a
          // multi-worker uvicorn deployment, signal() fires in Worker A but
          // wait_for_confirmation() blocks in Worker B — it always times out
          // (5s, FR-084) and the skill never executes. The confirm API still
          // returns 200, so we cannot detect the failure from the HTTP response.
          //
          // Mitigation: If the intent hasn't transitioned to 'executing' within
          // 8s (5s backend timeout + 3s SSE delivery buffer), revert to
          // 'detected' and prompt the user to retry.
          //
          // Production fix: replace ConfirmationBus with Redis pub/sub (backend).
          const CONFIRMATION_DELIVERY_MS = 8_000;
          const intentIdCapture = intentId;
          // Capture the current state now so revertIntentStatus has a full snapshot
          const preConfirmSnapshot = store.intents.get(intentIdCapture);
          setTimeout(() => {
            const current = store.intents.get(intentIdCapture);
            if (current?.status === 'confirmed' && preConfirmSnapshot) {
              // Still confirmed after grace period — ConfirmationBus signal was lost
              // (C-NEW-3: multi-worker issue; backend fix is Redis pub/sub)
              store.revertIntentStatus({ ...preConfirmSnapshot, status: 'detected' });
              toast.error('Confirmation timed out', {
                description:
                  'The agent did not receive the signal in time. Please try confirming again.',
              });
            }
          }, CONFIRMATION_DELIVERY_MS);
        } catch (err) {
          if (snapshot) store.revertIntentStatus(snapshot);
          toast.error('Failed to confirm intent', {
            description: err instanceof Error ? err.message : 'Please try again.',
          });
        }
      },
      [store]
    );

    const handleDismiss = useCallback(
      async (intentId: string) => {
        if (!store.workspaceId) return;
        const snapshot = store.optimisticDismissIntent(intentId);
        try {
          await aiApi.rejectIntent(store.workspaceId, intentId, store.sessionId ?? undefined);
        } catch (err) {
          if (snapshot) store.revertIntentStatus(snapshot);
          toast.error('Failed to dismiss intent', {
            description: err instanceof Error ? err.message : 'Please try again.',
          });
        }
      },
      [store]
    );

    const handleEdit = useCallback(
      async (
        intentId: string,
        patch: { new_what?: string; new_why?: string; new_constraints?: string[] }
      ) => {
        if (!store.workspaceId) return;
        try {
          const updated = await aiApi.editIntent(store.workspaceId, intentId, patch);
          const existing = store.intents.get(intentId);
          if (existing) {
            store.upsertIntent({
              ...existing,
              what: updated.what,
              why: updated.why ?? existing.why,
              constraints: Array.isArray(updated.constraints)
                ? (updated.constraints as string[])
                : existing.constraints,
            });
          }
        } catch (err) {
          toast.error('Failed to edit intent', {
            description: err instanceof Error ? err.message : 'Please try again.',
          });
        }
      },
      [store]
    );

    const handleApproveSkill = useCallback(
      async (intentId: string, approvalId: string) => {
        if (!store.workspaceId) return;
        try {
          await aiApi.approveSkillOutput(store.workspaceId, approvalId);
          store.updateIntentStatus(intentId, 'completed', { requiresApproval: false });
        } catch (err) {
          toast.error('Failed to approve skill output', {
            description: err instanceof Error ? err.message : 'Please try again.',
          });
        }
      },
      [store]
    );

    const handleRejectSkill = useCallback(
      async (intentId: string, approvalId: string, reason?: string) => {
        if (!store.workspaceId) return;
        try {
          await aiApi.rejectSkillOutput(store.workspaceId, approvalId, reason);
          store.updateIntentStatus(intentId, 'failed', { requiresApproval: false });
        } catch (err) {
          toast.error('Failed to reject skill output', {
            description: err instanceof Error ? err.message : 'Please try again.',
          });
        }
      },
      [store]
    );

    const handleRevise = useCallback(
      (intentId: string) => {
        // Start a new intent cycle: clear the current intent and pre-fill input
        const intent = store.intents.get(intentId);
        if (intent) {
          store.updateIntentStatus(intentId, 'rejected');
          onPrefillInput?.(intent.what);
        }
      },
      [store, onPrefillInput]
    );

    const handleDismissCard = useCallback(
      (intentId: string) => {
        store.updateIntentStatus(intentId, 'rejected');
      },
      [store]
    );

    const intents = Array.from(store.intents.values());

    return (
      <>
        {intents.map((intent) =>
          renderIntent(intent, {
            onConfirm: handleConfirm,
            onDismiss: handleDismiss,
            onEdit: handleEdit,
            onApproveSkill: handleApproveSkill,
            onRejectSkill: handleRejectSkill,
            onRevise: handleRevise,
            onDismissCard: handleDismissCard,
            onNavigateToArtifact,
            onPrefillInput,
          })
        )}
      </>
    );
  }
);

interface Handlers {
  onConfirm: (id: string) => Promise<void>;
  onDismiss: (id: string) => Promise<void>;
  onEdit: (
    id: string,
    patch: { new_what?: string; new_why?: string; new_constraints?: string[] }
  ) => Promise<void>;
  onApproveSkill: (intentId: string, approvalId: string) => Promise<void>;
  onRejectSkill: (intentId: string, approvalId: string, reason?: string) => Promise<void>;
  onRevise: (id: string) => void;
  onDismissCard: (id: string) => void;
  onNavigateToArtifact?: (id: string, type: string) => void;
  onPrefillInput?: (text: string) => void;
}

function renderIntent(intent: WorkIntentState, handlers: Handlers): React.ReactNode {
  const { intentId } = intent;

  // Rejected intents hidden entirely after a moment (card collapsed briefly)
  if (intent.status === 'rejected') {
    return (
      <IntentCard
        key={intentId}
        intent={intent}
        onConfirm={handlers.onConfirm}
        onDismiss={handlers.onDismiss}
        onEdit={handlers.onEdit}
      />
    );
  }

  // Show approval card when skill output needs approval
  if (
    (intent.status === 'completed' || intent.status === 'executing') &&
    intent.requiresApproval &&
    intent.approvalId
  ) {
    return (
      <SkillApprovalCard
        key={intentId}
        intent={intent}
        expiresAt={new Date(Date.now() + 24 * 3_600_000)} // 24h default
        actionLabel={`Run ${intent.skillName ?? 'skill'} output`}
        onApprove={handlers.onApproveSkill}
        onReject={handlers.onRejectSkill}
      />
    );
  }

  // Skill is executing or completed
  if (
    intent.status === 'executing' ||
    intent.status === 'completed' ||
    intent.status === 'failed'
  ) {
    return (
      <SkillProgressCard
        key={intentId}
        intent={intent}
        onViewArtifact={handlers.onNavigateToArtifact}
        onRevise={handlers.onRevise}
        onDismiss={handlers.onDismissCard}
      />
    );
  }

  // Default: detected (show IntentCard)
  return (
    <IntentCard
      key={intentId}
      intent={intent}
      onConfirm={handlers.onConfirm}
      onDismiss={handlers.onDismiss}
      onEdit={handlers.onEdit}
    />
  );
}
