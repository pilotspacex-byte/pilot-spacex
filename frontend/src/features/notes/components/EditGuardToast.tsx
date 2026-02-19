'use client';

/**
 * EditGuardToast — Shows a toast when user tries to edit an AI block (T-114, M6b)
 *
 * Triggered by OwnershipExtension.onGuardBlock callback.
 *
 * Per ui-design.md spec:
 * - Bottom-center of editor, above ChatInput
 * - Duration: 3 seconds, dismissable
 * - Style: rounded-lg, bg-foreground, text-background (inverted), shadow-lg
 * - Icon: Lucide Lock (16px)
 * - role="alert", aria-live="assertive"
 *
 * FR-003: AI blocks non-editable by humans (approve/reject only)
 * FR-008: Reject ownership violations — clear error feedback
 */
import { Lock } from 'lucide-react';
import { toast } from 'sonner';
import type { BlockOwner } from '@/features/notes/editor/extensions/OwnershipExtension';

function extractSkillName(owner: BlockOwner): string {
  return owner.startsWith('ai:') ? owner.slice(3) : owner;
}

/**
 * Show an edit guard toast when a user tries to edit a protected block.
 * Wraps sonner toast with block-ownership specific messaging.
 *
 * @param blockId - The blocked block's ID (for aria context)
 * @param owner   - The block's current owner
 */
export function showEditGuardToast(blockId: string, owner: BlockOwner): void {
  const skillName = owner.startsWith('ai:') ? extractSkillName(owner) : null;
  const ownerLabel = skillName ? `AI (${skillName})` : owner;

  toast.custom(
    () => (
      <div
        role="alert"
        aria-live="assertive"
        className="flex items-start gap-3 rounded-lg bg-foreground px-4 py-3 text-background shadow-lg"
        data-testid="edit-guard-toast"
        data-block-id={blockId}
      >
        <Lock size={16} className="mt-0.5 shrink-0 text-background/80" aria-hidden="true" />
        <div className="space-y-0.5 text-sm">
          <p className="font-medium">This block is owned by {ownerLabel}.</p>
          <p className="text-background/70">You can approve, reject, or convert to shared.</p>
        </div>
      </div>
    ),
    {
      duration: 6000,
      position: 'bottom-center',
    }
  );
}

export default showEditGuardToast;
