'use client';

/**
 * DigestInsights — Renders categorized AI insight cards from digest data.
 *
 * Each category displays as a compact card with icon, count badge,
 * suggestion list (collapsible beyond 5), and dismiss buttons.
 *
 * References:
 * - US-1: Wire digest API to homepage (T010-T016)
 * - FR-004: Hide empty categories
 */

import { useState, useCallback } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  Lock,
  RefreshCw,
  Timer,
  UserX,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { MAX_SUGGESTIONS_VISIBLE } from '../constants';
import type { DigestCategory, DigestSuggestion } from '../types';
import type { DigestCategoryGroup } from '../hooks/useWorkspaceDigest';

// ---------------------------------------------------------------------------
// Category metadata
// ---------------------------------------------------------------------------

interface CategoryMeta {
  icon: LucideIcon;
  label: string;
  colorClass: string;
  iconColorClass: string;
}

const CATEGORY_META: Record<DigestCategory, CategoryMeta> = {
  stale_issues: {
    icon: AlertTriangle,
    label: 'Stale Issues',
    colorClass: 'border-amber-200 dark:border-amber-800/40',
    iconColorClass: 'text-amber-500',
  },
  unlinked_notes: {
    icon: FileText,
    label: 'Unlinked Notes',
    colorClass: 'border-blue-200 dark:border-blue-800/40',
    iconColorClass: 'text-blue-500',
  },
  cycle_risk: {
    icon: Timer,
    label: 'Cycle Risk',
    colorClass: 'border-orange-200 dark:border-orange-800/40',
    iconColorClass: 'text-orange-500',
  },
  blocked_dependencies: {
    icon: Lock,
    label: 'Blocked',
    colorClass: 'border-red-200 dark:border-red-800/40',
    iconColorClass: 'text-red-500',
  },
  overdue_items: {
    icon: Clock,
    label: 'Overdue',
    colorClass: 'border-red-200 dark:border-red-800/40',
    iconColorClass: 'text-red-500',
  },
  unassigned_priority: {
    icon: UserX,
    label: 'Unassigned',
    colorClass: 'border-yellow-200 dark:border-yellow-800/40',
    iconColorClass: 'text-yellow-500',
  },
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface DigestInsightsProps {
  groups: DigestCategoryGroup[];
  generatedAt: string | null;
  isLoading: boolean;
  isError: boolean;
  isRefreshing: boolean;
  onDismiss: (suggestion: DigestSuggestion) => void;
  onRefresh: () => void;
  onRetry: () => void;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function InsightsSkeleton() {
  return (
    <div className="space-y-3" aria-label="Loading insights">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="h-24 motion-safe:animate-pulse rounded-lg border border-border bg-muted/20"
        />
      ))}
    </div>
  );
}

function CategoryCard({
  group,
  onDismiss,
}: {
  group: DigestCategoryGroup;
  onDismiss: (suggestion: DigestSuggestion) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const meta = CATEGORY_META[group.category];

  if (!meta) return null;

  const Icon = meta.icon;
  const hasOverflow = group.items.length > MAX_SUGGESTIONS_VISIBLE;
  const visibleItems = expanded ? group.items : group.items.slice(0, MAX_SUGGESTIONS_VISIBLE);
  const hiddenCount = group.items.length - MAX_SUGGESTIONS_VISIBLE;

  return (
    <div
      className={cn('overflow-hidden rounded-lg border bg-card', meta.colorClass)}
      role="region"
      aria-label={`${meta.label} insights`}
    >
      {/* Category header */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <Icon className={cn('h-4 w-4 shrink-0', meta.iconColorClass)} aria-hidden="true" />
        <span className="text-sm font-medium text-foreground">{meta.label}</span>
        <Badge variant="secondary" className="ml-auto px-1.5 py-0 text-xs tabular-nums">
          {group.items.length}
        </Badge>
      </div>

      {/* Suggestion list */}
      <ul className="border-t border-border/50" role="list" aria-label={`${meta.label} items`}>
        {visibleItems.map((suggestion) => (
          <SuggestionRow key={suggestion.id} suggestion={suggestion} onDismiss={onDismiss} />
        ))}
      </ul>

      {/* Expand/collapse toggle */}
      {hasOverflow && (
        <div className="border-t border-border/50">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded((prev) => !prev)}
            className="h-8 w-full gap-1.5 rounded-none text-xs text-muted-foreground"
            aria-expanded={expanded}
          >
            {expanded ? (
              <>
                <ChevronDown className="h-3 w-3" aria-hidden="true" />
                Show less
              </>
            ) : (
              <>
                <ChevronRight className="h-3 w-3" aria-hidden="true" />
                Show {hiddenCount} more
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

function SuggestionRow({
  suggestion,
  onDismiss,
}: {
  suggestion: DigestSuggestion;
  onDismiss: (suggestion: DigestSuggestion) => void;
}) {
  const handleDismiss = useCallback(() => {
    onDismiss(suggestion);
  }, [onDismiss, suggestion]);

  return (
    <li
      className={cn(
        'flex items-start gap-2 px-3 py-2',
        'border-b border-border/30 last:border-b-0',
        'motion-safe:transition-colors hover:bg-muted/30'
      )}
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm text-foreground leading-snug">{suggestion.title}</p>
        {suggestion.entityIdentifier && (
          <span className="mt-0.5 inline-block rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
            {suggestion.entityIdentifier}
          </span>
        )}
      </div>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDismiss}
            className="h-6 w-6 shrink-0 p-0 text-muted-foreground/60 hover:text-foreground"
            aria-label={`Dismiss: ${suggestion.title}`}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="left">Dismiss suggestion</TooltipContent>
      </Tooltip>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function DigestInsights({
  groups,
  generatedAt,
  isLoading,
  isError,
  isRefreshing,
  onDismiss,
  onRefresh,
  onRetry,
}: DigestInsightsProps) {
  if (isLoading) {
    return <InsightsSkeleton />;
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-2 py-6">
        <p className="text-sm text-muted-foreground">Failed to load insights.</p>
        <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Retry
        </Button>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className="flex flex-col items-center gap-1 py-6">
        <p className="text-sm text-muted-foreground">No suggestions right now.</p>
        <p className="text-xs text-muted-foreground/70">
          AI insights will appear as your workspace grows.
        </p>
      </div>
    );
  }

  const freshnessLabel = generatedAt
    ? `Updated ${formatDistanceToNow(new Date(generatedAt), { addSuffix: true })}`
    : null;

  return (
    <div className="space-y-3">
      {/* Freshness header */}
      <div className="flex items-center justify-between">
        {freshnessLabel && (
          <span className="text-xs text-muted-foreground/70">{freshnessLabel}</span>
        )}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
              className="ml-auto h-6 gap-1 px-2 text-xs text-muted-foreground"
              aria-label="Refresh digest"
            >
              <RefreshCw
                className={cn('h-3 w-3', isRefreshing && 'animate-spin')}
                aria-hidden="true"
              />
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </Button>
          </TooltipTrigger>
          <TooltipContent>Regenerate AI insights</TooltipContent>
        </Tooltip>
      </div>

      {/* Category cards */}
      {groups.map((group) => (
        <CategoryCard key={group.category} group={group} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
