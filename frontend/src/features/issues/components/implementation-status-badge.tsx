'use client';

/**
 * ImplementationStatusBadge - Status pill for batch run issue statuses.
 *
 * Renders a colored dot + label for 7 implementation statuses.
 * Uses React.memo (NOT observer) — safe for TipTap NodeView context.
 *
 * Phase 76: Sprint Batch Implementation UI
 */
import * as React from 'react';
import { cn } from '@/lib/utils';

export type ImplementationStatus =
  | 'queued'
  | 'cloning'
  | 'implementing'
  | 'creating_pr'
  | 'done'
  | 'failed'
  | 'cancelled';

export interface ImplementationStatusBadgeProps {
  status: ImplementationStatus | string;
  stage?: string | null;
  animated?: boolean;
  className?: string;
}

interface StatusConfig {
  label: string;
  dotClass: string;
  badgeClass: string;
}

const STATUS_CONFIG: Record<ImplementationStatus, StatusConfig> = {
  queued: {
    label: 'Queued',
    dotClass: 'bg-[hsl(var(--info))]',
    badgeClass: 'bg-[hsl(var(--info)/0.15)] text-[hsl(var(--info))]',
  },
  cloning: {
    label: 'Cloning repo',
    dotClass: 'bg-[hsl(var(--state-in-progress))]',
    badgeClass: 'bg-[hsl(var(--state-in-progress)/0.15)] text-[hsl(var(--state-in-progress))]',
  },
  implementing: {
    label: 'Implementing',
    dotClass: 'bg-[hsl(var(--state-in-progress))]',
    badgeClass: 'bg-[hsl(var(--state-in-progress)/0.15)] text-[hsl(var(--state-in-progress))]',
  },
  creating_pr: {
    label: 'Creating PR',
    dotClass: 'bg-[hsl(var(--ai))]',
    badgeClass: 'bg-[hsl(var(--ai)/0.15)] text-[hsl(var(--ai))]',
  },
  done: {
    label: 'Done',
    dotClass: 'bg-[hsl(var(--primary))]',
    badgeClass: 'bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]',
  },
  failed: {
    label: 'Failed',
    dotClass: 'bg-[hsl(var(--destructive))]',
    badgeClass: 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]',
  },
  cancelled: {
    label: 'Cancelled',
    dotClass: 'bg-[hsl(var(--destructive))]',
    badgeClass: 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]',
  },
};

const KNOWN_STATUSES = Object.keys(STATUS_CONFIG) as ImplementationStatus[];

function resolveConfig(status: string): StatusConfig {
  if (KNOWN_STATUSES.includes(status as ImplementationStatus)) {
    return STATUS_CONFIG[status as ImplementationStatus];
  }
  // Fallback for unknown statuses
  return {
    label: status,
    dotClass: 'bg-muted-foreground',
    badgeClass: 'bg-muted text-muted-foreground',
  };
}

export const ImplementationStatusBadge = React.memo(function ImplementationStatusBadge({
  status,
  animated = true,
  className,
}: ImplementationStatusBadgeProps) {
  const config = resolveConfig(status);
  const isPulsing = status === 'implementing' && animated;

  return (
    <span
      role="status"
      aria-label={`Implementation status: ${config.label}`}
      aria-live={isPulsing ? 'polite' : undefined}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5',
        'text-[12px] font-semibold leading-[1.4]',
        'motion-safe:transition-all motion-safe:duration-150 motion-safe:ease-out',
        config.badgeClass,
        className
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'inline-block size-2 flex-shrink-0 rounded-full',
          config.dotClass,
          isPulsing && 'motion-safe:animate-pulse'
        )}
      />
      {config.label}
    </span>
  );
});

ImplementationStatusBadge.displayName = 'ImplementationStatusBadge';
