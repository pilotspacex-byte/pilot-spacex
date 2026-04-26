/**
 * RejectedPill — compact demoted pill replacing an EditProposalCard
 * whose proposal ended up rejected / retried / reverted / errored.
 * UI-SPEC §3.
 *
 * The "Try again" CTA on the `rejected` variant re-runs the original
 * intent by firing a retry mutation through useRetryProposal.
 */

'use client';

import { memo } from 'react';
import { AlertTriangle, RotateCcw, Undo2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useRetryProposal } from './useProposalActions';
import type { ProposalEnvelope } from './types';

export type RejectedPillVariant = 'rejected' | 'retried' | 'reverted' | 'errored';

interface RejectedPillProps {
  envelope: ProposalEnvelope;
  variant?: RejectedPillVariant;
  errorMessage?: string;
  className?: string;
}

export const RejectedPill = memo<RejectedPillProps>(function RejectedPill({
  envelope,
  variant,
  errorMessage,
  className,
}) {
  const resolved: RejectedPillVariant =
    variant ??
    (envelope.status === 'retried'
      ? 'retried'
      : envelope.status === 'errored'
        ? 'errored'
        : 'rejected');

  const retry = useRetryProposal();

  const isErrored = resolved === 'errored';

  return (
    <span
      role="status"
      data-testid="rejected-pill"
      data-variant={resolved}
      className={cn(
        'inline-flex items-center gap-1.5 h-7 px-3 rounded-full border',
        'text-xs font-medium leading-none',
        isErrored
          ? 'bg-[#fbe8e7] border-[#D9534F] text-[#D9534F]'
          : 'bg-[#f3f4f6] border-[#e5e7eb] text-[#6b7280]',
        className
      )}
      aria-label={
        resolved === 'rejected'
          ? 'Proposal rejected. Click Try again to retry.'
          : resolved === 'retried'
            ? 'Retrying with a new approach'
            : resolved === 'reverted'
              ? `Reverted to previous version`
              : `Proposal errored: ${errorMessage ?? 'unknown error'}`
      }
    >
      {resolved === 'rejected' && <X className="h-3.5 w-3.5" aria-hidden="true" />}
      {resolved === 'retried' && (
        <RotateCcw className="h-3.5 w-3.5 motion-safe:animate-spin" aria-hidden="true" />
      )}
      {resolved === 'reverted' && <Undo2 className="h-3.5 w-3.5" aria-hidden="true" />}
      {resolved === 'errored' && <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />}

      {resolved === 'rejected' && (
        <>
          <span>Rejected</span>
          <span aria-hidden="true">·</span>
          <button
            type="button"
            data-testid="try-again-button"
            disabled={retry.isPending}
            onClick={() => retry.mutate({ id: envelope.id })}
            className="underline hover:text-[#4b5563] disabled:opacity-60"
            aria-label="Retry this proposal with a new approach"
          >
            Try again
          </button>
        </>
      )}
      {resolved === 'retried' && <span>Retrying with a new approach…</span>}
      {resolved === 'reverted' && (
        <span>
          Reverted
          {envelope.appliedVersion != null ? ` to v${envelope.appliedVersion - 1}` : ''}
        </span>
      )}
      {resolved === 'errored' && (
        <span title={errorMessage ?? undefined} className="truncate max-w-[280px]">
          Couldn&apos;t apply{errorMessage ? `: ${errorMessage}` : ''}
        </span>
      )}
    </span>
  );
});

RejectedPill.displayName = 'RejectedPill';
