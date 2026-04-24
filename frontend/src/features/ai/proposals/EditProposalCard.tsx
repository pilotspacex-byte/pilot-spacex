/**
 * EditProposalCard — pending-state review surface for an AI mutation.
 *
 * UI-SPEC §1. Anatomy: header (badge + target + scope + version) / body
 * (diff + optional reasoning) / footer (Accept / Retry / Reject / Open
 * + DD-003 rail).
 *
 * Mode variants (REV-89-01-A policy flags):
 *   - plan  → Accept disabled; "Plan mode preview only" badge; tooltip
 *             "Switch to Act to apply"
 *   - draft → Accept visible + clickable, but onClick fires a toast
 *             "Draft mode does not persist" and does NOT call the API
 *   - act/research → full behavior
 *
 * Keyboard: ⌘↵ / Ctrl+Enter accepts while focus is inside the card.
 *
 * Safe to wrap in observer() — this component does NOT live inside a
 * TipTap NodeView, so the flushSync constraint (per .claude/rules/tiptap.md)
 * does not apply.
 */

'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { observer } from 'mobx-react-lite';
import { toast } from 'sonner';
import {
  Check,
  ExternalLink,
  Info,
  RotateCcw,
  Sparkles,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { TextDiffBlock } from './TextDiffBlock';
import { FieldDiffRow } from './FieldDiffRow';
import {
  useAcceptProposal,
  useRejectProposal,
  useRetryProposal,
} from './useProposalActions';
import type {
  FieldsDiffPayload,
  ProposalEnvelope,
  TextDiffPayload,
} from './types';

interface EditProposalCardProps {
  envelope: ProposalEnvelope;
  /** Called when the user clicks "Open in editor". Plan 06+ wires peek drawer. */
  onOpenInEditor?: (artifactType: string, artifactId: string) => void;
  className?: string;
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  });
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, []);
  return reduced;
}

function shortId(id: string): string {
  return id.slice(0, 8);
}

function computeVersionLabel(envelope: ProposalEnvelope): string {
  const applied = envelope.appliedVersion ?? 0;
  // When appliedVersion is known, `applied` is the version AFTER apply.
  // Pending: we don't know the current version; show "v? → v?+1" pattern
  // with applied==null meaning "current → +1".
  if (envelope.appliedVersion != null) {
    return `v${applied - 1} → v${applied}`;
  }
  return `current → +1`;
}

export const EditProposalCard = observer<EditProposalCardProps>(function EditProposalCard({
  envelope,
  onOpenInEditor,
  className,
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const reduced = usePrefersReducedMotion();
  const accept = useAcceptProposal();
  const reject = useRejectProposal();
  const retry = useRetryProposal();

  const isPlan = envelope.mode === 'plan' || envelope.planPreviewOnly;
  const isDraft = envelope.mode === 'draft' || !envelope.persist;
  const acceptDisabledByMode = isPlan || envelope.acceptDisabled;

  const versionLabel = useMemo(() => computeVersionLabel(envelope), [envelope]);

  const scopeLabel = useMemo(() => {
    if (envelope.diffKind === 'fields') {
      const rows = (envelope.diffPayload as FieldsDiffPayload).rows ?? [];
      return `${rows.length} field${rows.length === 1 ? '' : 's'}`;
    }
    const hunks = (envelope.diffPayload as TextDiffPayload).hunks ?? [];
    const changedChunks = hunks.filter((h) => h.op !== 'equal').length;
    return `${changedChunks} change${changedChunks === 1 ? '' : 's'}`;
  }, [envelope.diffKind, envelope.diffPayload]);

  const handleAccept = useCallback(() => {
    if (acceptDisabledByMode) {
      toast.message('Plan mode preview only', {
        description: 'Switch to Act to apply this proposal.',
      });
      return;
    }
    if (isDraft) {
      toast.message('Draft mode does not persist', {
        description: 'Switch to Act to persist this change.',
      });
      return;
    }
    accept.mutate(envelope.id, {
      onError: (err) => {
        toast.error("Couldn't apply proposal", {
          description: err instanceof Error ? err.message : 'Unknown error',
        });
      },
    });
  }, [accept, acceptDisabledByMode, envelope.id, isDraft]);

  const handleReject = useCallback(() => {
    reject.mutate(
      { id: envelope.id },
      {
        onError: (err) => {
          toast.error("Couldn't reject proposal", {
            description: err instanceof Error ? err.message : 'Unknown error',
          });
        },
      }
    );
  }, [reject, envelope.id]);

  const handleRetry = useCallback(() => {
    retry.mutate(
      { id: envelope.id },
      {
        onError: (err) => {
          toast.error("Couldn't retry proposal", {
            description: err instanceof Error ? err.message : 'Unknown error',
          });
        },
      }
    );
  }, [retry, envelope.id]);

  // ⌘↵ / Ctrl+Enter when focus is inside the card.
  useEffect(() => {
    const node = cardRef.current;
    if (!node) return;
    const onKey = (e: KeyboardEvent) => {
      const isMod = e.metaKey || e.ctrlKey;
      if (isMod && e.key === 'Enter') {
        e.preventDefault();
        handleAccept();
      }
    };
    node.addEventListener('keydown', onKey);
    return () => node.removeEventListener('keydown', onKey);
  }, [handleAccept]);

  const transition = reduced ? '' : 'transition-all duration-200';

  return (
    <div
      ref={cardRef}
      role="region"
      aria-label={`Edit proposal for ${envelope.targetArtifactType.toLowerCase()} ${shortId(envelope.targetArtifactId)}`}
      className={cn(
        'w-full max-w-[720px] rounded-2xl border-[1.5px] border-[#f97316] bg-white overflow-hidden',
        transition,
        className
      )}
      data-testid="edit-proposal-card"
      data-mode={envelope.mode}
    >
      {/* HEADER */}
      <div className="bg-[#fffbeb] px-4 py-3 flex items-center gap-3 flex-wrap border-b border-[#f9731633] min-h-[56px]">
        <span
          aria-hidden="true"
          data-testid="edit-proposal-badge"
          className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded',
            'font-mono text-[10px] font-semibold tracking-wider uppercase',
            'text-[#9a3412]'
          )}
          style={{ background: 'rgba(249,115,22,0.12)' }}
        >
          <Sparkles className="h-3 w-3" aria-hidden="true" />
          Edit proposal
        </span>
        <span
          data-testid="target-chip"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium leading-snug text-foreground truncate"
        >
          <span className="font-mono text-[10px] font-semibold tracking-wider uppercase text-muted-foreground">
            {envelope.targetArtifactType}
          </span>
          <span className="text-muted-foreground">·</span>
          <code className="text-[12px] font-mono text-foreground/80">
            {shortId(envelope.targetArtifactId)}
          </code>
        </span>
        {isPlan && (
          <span
            data-testid="plan-mode-badge"
            aria-label="Plan mode — preview only, Accept disabled"
            className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
            style={{
              background: 'rgba(100,116,139,0.10)',
              color: '#64748b',
            }}
          >
            Plan mode preview only
          </span>
        )}
        {isDraft && (
          <span
            data-testid="draft-mode-badge"
            className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium bg-muted text-muted-foreground"
          >
            Draft
          </span>
        )}
        <span className="flex-1" />
        <span className="text-xs text-muted-foreground hidden sm:inline">{scopeLabel}</span>
        <span className="font-mono text-[11px] font-semibold text-[#6b7280]" data-testid="version-label">
          {versionLabel}
        </span>
      </div>

      {/* BODY */}
      <div className="px-4 py-4 bg-white">
        {envelope.diffKind === 'text' ? (
          <TextDiffBlock payload={envelope.diffPayload as TextDiffPayload} />
        ) : (
          <div className="space-y-0.5" data-testid="field-diff-list">
            {((envelope.diffPayload as FieldsDiffPayload).rows ?? []).map((row) => (
              <FieldDiffRow key={row.field} row={row} />
            ))}
          </div>
        )}

        {envelope.reasoning && (
          <div
            role="note"
            className="mt-3 rounded-xl bg-[#f3f4f6] p-3 flex gap-2 items-start"
            data-testid="reasoning-callout"
          >
            <Info className="h-4 w-4 text-[#6B8FAD] shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Reasoning
              </div>
              <div className="text-[13px] leading-[1.5]" style={{ color: 'rgba(26,26,46,0.85)' }}>
                {envelope.reasoning}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* FOOTER */}
      <div className="px-4 pt-2 pb-2 bg-white border-t border-[#e5e7eb]">
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            type="button"
            onClick={handleAccept}
            disabled={accept.isPending || acceptDisabledByMode}
            title={acceptDisabledByMode ? 'Switch to Act to apply' : undefined}
            aria-label="Accept proposal. Keyboard shortcut: Command Enter"
            data-testid="accept-button"
            className={cn(
              'h-8 gap-1.5 bg-[#29a386] text-white hover:bg-[#1e7a63]',
              acceptDisabledByMode && 'bg-[#e5e7eb] text-[#64748b] hover:bg-[#e5e7eb] cursor-not-allowed'
            )}
          >
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="text-[13px] font-medium leading-none">Accept</span>
            <kbd className="font-mono text-[10px] font-semibold bg-white/25 px-1 py-0.5 rounded ml-1">
              ⌘↵
            </kbd>
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleRetry}
            disabled={retry.isPending}
            aria-label="Retry proposal with a different approach"
            data-testid="retry-button"
            className="h-8 gap-1.5"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="text-[13px] font-medium leading-none">Retry</span>
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={handleReject}
            disabled={reject.isPending}
            aria-label="Reject proposal"
            data-testid="reject-button"
            className="h-8 gap-1.5"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="text-[13px] font-medium leading-none">Reject</span>
          </Button>
          {envelope.targetArtifactType !== 'DECISION' && onOpenInEditor && (
            <Button
              type="button"
              variant="ghost"
              onClick={() =>
                onOpenInEditor(envelope.targetArtifactType, envelope.targetArtifactId)
              }
              aria-label={`Open ${envelope.targetArtifactType.toLowerCase()} in editor`}
              data-testid="open-in-editor-button"
              className="h-8 gap-1.5"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="text-[13px] font-medium leading-none">Open in editor</span>
            </Button>
          )}
        </div>
        <div
          className="mt-2 pt-2 border-t text-[11px] text-[#6b7280]"
          style={{ borderColor: 'rgba(229,231,235,0.4)' }}
          data-testid="dd003-rail"
        >
          Nothing saved until you accept.
        </div>
      </div>
    </div>
  );
});

EditProposalCard.displayName = 'EditProposalCard';
