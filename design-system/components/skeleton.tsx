/**
 * Skeleton/Loading Component v2.0
 *
 * Design Direction: Warm, Capable, Collaborative
 * Key Features:
 * - Squircle corners matching component styles
 * - Warm shimmer effect
 * - AI loading variant
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-xl bg-muted', className)}
      aria-busy="true"
      aria-live="polite"
      {...props}
    />
  );
}

export { Skeleton };

/**
 * Shimmer Skeleton
 *
 * Alternative loading style with shimmer animation
 */
export function ShimmerSkeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-xl bg-gradient-to-r from-muted via-muted-foreground/10 to-muted bg-[length:200%_100%] animate-shimmer',
        className
      )}
      aria-busy="true"
      aria-live="polite"
      {...props}
    />
  );
}

/**
 * AI Loading Skeleton
 *
 * Loading state for AI-generated content
 */
export function AILoadingSkeleton({
  className,
  message = 'AI is thinking...',
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { message?: string }) {
  return (
    <div
      className={cn(
        'rounded-2xl border-l-4 border-l-ai bg-ai-muted/30 p-4',
        className
      )}
      aria-busy="true"
      aria-live="polite"
      {...props}
    >
      <div className="flex items-center gap-3">
        <div className="h-5 w-5 rounded-full border-2 border-ai border-t-transparent animate-spin" />
        <span className="text-sm text-ai">{message}</span>
      </div>
    </div>
  );
}

/**
 * Issue Card Skeleton
 */
export function IssueCardSkeleton() {
  return (
    <div className="rounded-2xl border bg-card p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <Skeleton className="h-4 w-4 rounded" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-12 rounded-full" />
      </div>
      <div className="mt-3 flex items-center justify-between">
        <Skeleton className="h-6 w-6 rounded-full" />
        <Skeleton className="h-4 w-20" />
      </div>
    </div>
  );
}

/**
 * Issue List Skeleton
 */
export function IssueListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 rounded-xl border bg-card p-3">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-6 w-6 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/**
 * Board Column Skeleton
 */
export function BoardColumnSkeleton() {
  return (
    <div className="w-board-column min-w-board-column flex-shrink-0">
      <div className="mb-3 flex items-center justify-between">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-5 w-8 rounded-full" />
      </div>
      <div className="space-y-3">
        <IssueCardSkeleton />
        <IssueCardSkeleton />
        <IssueCardSkeleton />
      </div>
    </div>
  );
}

/**
 * Board Skeleton
 */
export function BoardSkeleton({ columns = 4 }: { columns?: number }) {
  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {Array.from({ length: columns }).map((_, i) => (
        <BoardColumnSkeleton key={i} />
      ))}
    </div>
  );
}

/**
 * Page Editor Skeleton
 */
export function PageEditorSkeleton() {
  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      <Skeleton className="h-10 w-2/3" />
      <Skeleton className="h-4 w-1/3" />
      <div className="space-y-3 pt-6">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/5" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
      <Skeleton className="mt-6 h-48 w-full rounded-2xl" />
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}

/**
 * Sidebar Skeleton
 */
export function SidebarSkeleton() {
  return (
    <div className="flex h-full w-sidebar flex-col border-r bg-background-subtle p-4">
      <div className="flex items-center gap-3 pb-6">
        <Skeleton className="h-8 w-8 rounded-xl" />
        <Skeleton className="h-5 flex-1" />
      </div>
      <div className="space-y-1">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 rounded-xl p-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 flex-1" />
          </div>
        ))}
      </div>
      <div className="mt-6 space-y-1">
        <Skeleton className="mb-2 h-3 w-20" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 rounded-xl p-2">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 flex-1" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * AI Suggestion Card Skeleton
 */
export function AISuggestionCardSkeleton() {
  return (
    <div className="rounded-2xl border-l-4 border-l-ai bg-ai-muted/30 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-5 rounded-full" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
      </div>
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-9 w-20 rounded-xl" />
        <Skeleton className="h-9 w-16 rounded-xl" />
      </div>
    </div>
  );
}
