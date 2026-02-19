'use client';

/**
 * OwnershipPopover — Block ownership actions popover (T-114, M6b Feature 016)
 *
 * Rendered when user clicks the gutter icon of an AI or shared block.
 * Shows:
 * - Owner info (skill name, created time, intent reference)
 * - [Approve] [Reject] [Convert to Shared] buttons for AI blocks
 *
 * Per ui-design.md spec:
 * - Width: 240px, left of gutter, aligned to block
 * - Frosted glass background, rounded-lg (14px)
 * - Approve: accept content, optionally convert to "shared"
 * - Reject: remove block (with undo toast)
 * - Convert to Shared: change to "shared", unlocks human editing
 *
 * FR-003: AI blocks non-editable by humans (approve/reject only)
 *
 * Integration: Wire into NoteCanvasEditor via OwnershipExtension.onGuardBlock callback.
 * Pass editor.commands.undo as onUndo prop when rendering this component.
 * (Deferred: tracked in T-114 — requires NoteCanvasEditor layout changes)
 */
import { useState, useRef, useEffect } from 'react';
import { Bot, Users, Check, X, Share2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { apiClient } from '@/services/api/client';
import type { BlockOwner } from '@/features/notes/editor/extensions/OwnershipExtension';

export interface OwnershipPopoverProps {
  blockId: string;
  noteId: string;
  workspaceId: string;
  owner: BlockOwner;
  /** Called after successful approve/reject/convert to trigger editor refresh */
  onOwnershipChange?: (blockId: string, newOwner: BlockOwner | null) => void;
  /** Called when user triggers undo after block rejection */
  onUndo?: () => void;
  /** Called when popover should close (Escape, X button, or click-outside) */
  onClose?: () => void;
  className?: string;
}

async function fetchBlockAction(
  workspaceId: string,
  noteId: string,
  blockId: string,
  action: 'approve' | 'reject',
  body?: Record<string, unknown>
): Promise<{ owner?: string; removed?: boolean }> {
  return apiClient.post<{ owner?: string; removed?: boolean }>(
    `/workspaces/${workspaceId}/notes/${noteId}/blocks/${blockId}/${action}`,
    body
  );
}

function extractSkillName(owner: BlockOwner): string {
  return owner.startsWith('ai:') ? owner.slice(3) : owner;
}

export function OwnershipPopover({
  blockId,
  noteId,
  workspaceId,
  owner,
  onOwnershipChange,
  onUndo,
  onClose,
  className,
}: OwnershipPopoverProps) {
  const [loading, setLoading] = useState<'approve' | 'reject' | 'convert' | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Focus trap: keep focus within popover while open
  useEffect(() => {
    const el = popoverRef.current;
    if (!el) return;
    const focusable = el.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    first?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      // COL-C3: Escape closes the popover
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose?.();
        return;
      }
      if (e.key !== 'Tab') return;
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }
      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    }
    el.addEventListener('keydown', handleKeyDown);
    return () => el.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // COL-C3: click-outside closes the popover
  useEffect(() => {
    function handlePointerDown(e: PointerEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose?.();
      }
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [onClose]);

  const isAIBlock = owner.startsWith('ai:');
  const isShared = owner === 'shared';
  const skillName = isAIBlock ? extractSkillName(owner) : null;

  async function handleApprove() {
    setLoading('approve');
    try {
      const result = await fetchBlockAction(workspaceId, noteId, blockId, 'approve', {
        convertToShared: false,
      });
      toast.success('AI block approved');
      onOwnershipChange?.(blockId, (result.owner as BlockOwner) ?? owner);
    } catch (err) {
      toast.error(`Approve failed: ${(err as Error).message}`);
    } finally {
      setLoading(null);
    }
  }

  async function handleConvertToShared() {
    setLoading('convert');
    try {
      const result = await fetchBlockAction(workspaceId, noteId, blockId, 'approve', {
        convertToShared: true,
      });
      toast.success('Block converted to shared — now editable by both');
      onOwnershipChange?.(blockId, (result.owner as BlockOwner) ?? 'shared');
    } catch (err) {
      toast.error(`Convert failed: ${(err as Error).message}`);
    } finally {
      setLoading(null);
    }
  }

  async function handleReject() {
    setLoading('reject');
    try {
      await fetchBlockAction(workspaceId, noteId, blockId, 'reject');
      toast('AI block removed', {
        action: {
          label: 'Undo',
          onClick: () => {
            onUndo?.();
          },
        },
        duration: 5000,
      });
      onOwnershipChange?.(blockId, null); // null signals block removed
    } catch (err) {
      toast.error(`Reject failed: ${(err as Error).message}`);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div
      ref={popoverRef}
      className={cn(
        'w-60 rounded-[14px] border border-border bg-background p-3 shadow-lg',
        'backdrop-blur-sm',
        className
      )}
      role="dialog"
      aria-modal="true"
      aria-label="Block Ownership"
    >
      {/* Header */}
      <div className="mb-2 flex items-center gap-2">
        {isAIBlock && <Bot size={14} className="text-[var(--ai,#6B8FAD)]" aria-hidden="true" />}
        {isShared && <Users size={14} className="text-primary" aria-hidden="true" />}
        <span className="flex-1 text-sm font-medium text-foreground">Block Ownership</span>
        {/* COL-C3: visible X close button */}
        <button
          type="button"
          aria-label="Close"
          onClick={() => onClose?.()}
          className="ml-auto rounded p-0.5 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X size={14} aria-hidden="true" />
        </button>
      </div>

      {/* Owner info */}
      <div className="mb-3 space-y-1 text-xs text-muted-foreground">
        {isAIBlock && (
          <p>
            Owner:{' '}
            <span className="font-mono font-medium text-[var(--ai,#6B8FAD)]">AI ({skillName})</span>
          </p>
        )}
        {isShared && (
          <p>
            Owner: <span className="font-medium text-primary">Shared</span>
          </p>
        )}
        {owner === 'human' && (
          <p>
            Owner: <span className="font-medium">Human</span>
          </p>
        )}
      </div>

      {/* Actions — only for AI blocks */}
      {isAIBlock && (
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="default"
              className="flex-1 h-7 text-xs"
              onClick={handleApprove}
              disabled={loading !== null}
              aria-label="Approve AI block content"
            >
              {loading === 'approve' ? (
                <Loader2 size={12} className="animate-spin mr-1" aria-hidden="true" />
              ) : (
                <Check size={12} className="mr-1" aria-hidden="true" />
              )}
              Approve
            </Button>

            <Button
              size="sm"
              variant="destructive"
              className="flex-1 h-7 text-xs"
              onClick={handleReject}
              disabled={loading !== null}
              aria-label="Reject and remove AI block"
            >
              {loading === 'reject' ? (
                <Loader2 size={12} className="animate-spin mr-1" aria-hidden="true" />
              ) : (
                <X size={12} className="mr-1" aria-hidden="true" />
              )}
              Reject
            </Button>
          </div>

          <Button
            size="sm"
            variant="outline"
            className="w-full h-7 text-xs"
            onClick={handleConvertToShared}
            disabled={loading !== null}
            aria-label="Convert to shared block — unlocks human editing"
          >
            {loading === 'convert' ? (
              <Loader2 size={12} className="animate-spin mr-1" aria-hidden="true" />
            ) : (
              <Share2 size={12} className="mr-1" aria-hidden="true" />
            )}
            Convert to Shared
          </Button>
        </div>
      )}
    </div>
  );
}

export default OwnershipPopover;
