'use client';

/**
 * GraphEmptyState — loading, empty, error, and forbidden placeholder for knowledge graph.
 *
 * Four variants:
 *  - loading:   pulsing skeleton circles with SVG connector lines
 *  - empty:     SVG placeholder + "No knowledge graph yet" + optional chat CTA
 *  - error:     error message + optional retry button
 *  - forbidden: permission denied message with explanation
 */

import { Loader2, ShieldX, Sparkles } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/services/api/client';

/**
 * Check if a TanStack Query error is a 403 Forbidden.
 * @deprecated Use `ApiError.isForbidden(error)` instead.
 */
export function isForbiddenError(error: unknown): boolean {
  return ApiError.isForbidden(error);
}

export interface GraphEmptyStateProps {
  variant: 'loading' | 'empty' | 'error' | 'forbidden';
  onRetry?: () => void;
  onOpenChat?: () => void;
  /** Trigger KG regeneration for the current entity. */
  onRegenerate?: () => void;
  /** Whether regeneration is in progress. */
  isRegenerating?: boolean;
  /** Container height in px. Defaults to 200. */
  height?: number;
}

export function GraphEmptyState({
  variant,
  onRetry,
  onOpenChat,
  onRegenerate,
  isRegenerating,
  height = 200,
}: GraphEmptyStateProps) {
  if (variant === 'loading') {
    return (
      <div
        role="status"
        aria-label="Loading knowledge graph"
        className="flex items-center justify-center gap-6"
        style={{ height }}
      >
        {/* SVG connector lines behind the circles */}
        <svg
          aria-hidden="true"
          className="absolute pointer-events-none opacity-30"
          width="160"
          height="40"
          viewBox="0 0 160 40"
        >
          <line x1="30" y1="20" x2="65" y2="20" stroke="currentColor" strokeWidth="1.5" />
          <line x1="95" y1="20" x2="130" y2="20" stroke="currentColor" strokeWidth="1.5" />
        </svg>

        <Skeleton className="size-10 rounded-full shrink-0" />
        <Skeleton className="size-8 rounded-full shrink-0" />
        <Skeleton className="size-10 rounded-full shrink-0" />
      </div>
    );
  }

  if (variant === 'forbidden') {
    return (
      <div
        role="alert"
        className="flex flex-col items-center justify-center gap-3 text-center"
        style={{ height }}
      >
        <ShieldX className="size-10 text-muted-foreground/60" aria-hidden="true" />
        <p className="text-sm font-medium text-foreground">Access denied</p>
        <p className="text-xs text-muted-foreground max-w-xs">
          You don&apos;t have permission to view this knowledge graph. Contact a workspace admin to
          request access.
        </p>
      </div>
    );
  }

  if (variant === 'error') {
    return (
      <div
        role="alert"
        className="flex flex-col items-center justify-center gap-3 text-center"
        style={{ height }}
      >
        <p className="text-sm text-muted-foreground">Failed to load knowledge graph</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="text-xs text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  // empty — show generating skeleton when in-flight, static placeholder otherwise
  if (isRegenerating) {
    return (
      <div
        role="status"
        aria-label="Generating knowledge graph"
        className="flex flex-col items-center justify-center gap-4 text-center"
        style={{ height }}
      >
        {/* Animated graph skeleton — nodes appearing with staggered fade-in */}
        <div className="relative" style={{ width: 280, height: 120 }}>
          {/* Connector lines (pulse) */}
          <svg
            aria-hidden="true"
            className="absolute inset-0 pointer-events-none"
            width="280"
            height="120"
            viewBox="0 0 280 120"
          >
            {[
              { x1: 140, y1: 30, x2: 60, y2: 65 },
              { x1: 140, y1: 30, x2: 140, y2: 65 },
              { x1: 140, y1: 30, x2: 220, y2: 65 },
              { x1: 60, y1: 65, x2: 30, y2: 100 },
              { x1: 60, y1: 65, x2: 90, y2: 100 },
              { x1: 220, y1: 65, x2: 190, y2: 100 },
              { x1: 220, y1: 65, x2: 250, y2: 100 },
            ].map((l, i) => (
              <line
                key={i}
                {...l}
                stroke="currentColor"
                strokeWidth="1.5"
                className="text-muted-foreground/20 animate-pulse"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </svg>
          {/* Skeleton nodes with staggered animation */}
          {[
            { x: 116, y: 10, w: 48, h: 28, delay: 0 },
            { x: 28, y: 50, w: 64, h: 24, delay: 200 },
            { x: 108, y: 50, w: 64, h: 24, delay: 400 },
            { x: 188, y: 50, w: 64, h: 24, delay: 600 },
            { x: 4, y: 88, w: 52, h: 20, delay: 800 },
            { x: 64, y: 88, w: 52, h: 20, delay: 1000 },
            { x: 164, y: 88, w: 52, h: 20, delay: 1200 },
            { x: 224, y: 88, w: 52, h: 20, delay: 1400 },
          ].map((n, i) => (
            <div
              key={i}
              className="absolute animate-pulse"
              style={{
                left: n.x,
                top: n.y,
                width: n.w,
                height: n.h,
                animationDelay: `${n.delay}ms`,
              }}
            >
              <Skeleton className="w-full h-full rounded-md" />
            </div>
          ))}
        </div>

        <div className="flex flex-col items-center gap-1.5">
          <p className="text-sm font-medium text-foreground flex items-center gap-2">
            <Loader2 className="size-3.5 animate-spin text-primary" />
            Building knowledge graph
          </p>
          <p className="text-xs text-muted-foreground">
            Processing issues, notes, and relationships...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-3 text-center" style={{ height }}>
      {/* Abstract graph placeholder: diamond — circle — square */}
      <svg
        aria-hidden="true"
        width="96"
        height="28"
        viewBox="0 0 96 28"
        className="text-muted-foreground opacity-40"
      >
        <line x1="18" y1="14" x2="34" y2="14" stroke="currentColor" strokeWidth="1.5" />
        <line x1="62" y1="14" x2="78" y2="14" stroke="currentColor" strokeWidth="1.5" />
        <polygon
          points="8,14 14,8 20,14 14,20"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
        />
        <circle cx="48" cy="14" r="8" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <rect
          x="78"
          y="6"
          width="16"
          height="16"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          rx="2"
        />
      </svg>

      <p className="text-sm text-muted-foreground">No knowledge graph yet</p>
      <p className="mt-1 text-xs text-muted-foreground max-w-xs text-center">
        The knowledge graph visualizes relationships between your notes, issues, and code.
      </p>

      {onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          className="mt-1 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Sparkles className="size-3" />
          Generate Knowledge Graph
        </button>
      )}

      {onOpenChat && !onRegenerate && (
        <button
          type="button"
          onClick={onOpenChat}
          className="text-xs text-primary underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          Open AI Chat →
        </button>
      )}
    </div>
  );
}
