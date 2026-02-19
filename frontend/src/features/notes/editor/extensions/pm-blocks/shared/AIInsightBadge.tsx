'use client';

/**
 * AIInsightBadge — Traffic-light badge shown in PM block headers.
 *
 * FR-056: AI insight badges (green/yellow/red) on PM blocks.
 * FR-057: Badge tooltip with analysis, references, suggested actions.
 * FR-058: Graceful degradation with "Insufficient data" when <3 sprints.
 * FR-059: Dismissable insights.
 *
 * @module pm-blocks/shared/AIInsightBadge
 */

import { useState, useCallback } from 'react';
import { CheckCircle, AlertTriangle, AlertOctagon, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PMBlockInsight, InsightSeverity } from '@/services/api/pm-blocks';

// ── Severity config ─────────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<
  InsightSeverity | 'insufficient',
  {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    badge: string;
    tooltip: string;
  }
> = {
  green: {
    icon: CheckCircle,
    label: 'On Track',
    badge: 'bg-[#29A38618] text-[#29A386] border-[#29A386]/20',
    tooltip: 'bg-background',
  },
  yellow: {
    icon: AlertTriangle,
    label: 'At Risk',
    badge: 'bg-[#D9853F18] text-[#D9853F] border-[#D9853F]/20',
    tooltip: 'bg-background',
  },
  red: {
    icon: AlertOctagon,
    label: 'Blocked',
    badge: 'bg-[#D9534F18] text-[#D9534F] border-[#D9534F]/20',
    tooltip: 'bg-background',
  },
  insufficient: {
    icon: Info,
    label: 'Insufficient Data',
    badge: 'bg-muted text-muted-foreground border-border',
    tooltip: 'bg-background',
  },
};

// ── Props ───────────────────────────────────────────────────────────────────

export interface AIInsightBadgeProps {
  insight: PMBlockInsight | null;
  /** When true, shows "Insufficient Data" gray badge. */
  insufficientData?: boolean;
  onDismiss?: (insightId: string) => void;
  className?: string;
}

// ── Tooltip ──────────────────────────────────────────────────────────────────

interface InsightTooltipProps {
  insight: PMBlockInsight;
  onDismiss?: (id: string) => void;
  onClose: () => void;
}

function InsightTooltip({ insight, onDismiss, onClose }: InsightTooltipProps) {
  const handleDismiss = useCallback(() => {
    onDismiss?.(insight.id);
    onClose();
  }, [insight.id, onDismiss, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
      }
    },
    [onClose]
  );

  return (
    <div
      role="tooltip"
      className="absolute right-0 top-full z-50 mt-1 w-72 rounded-lg border bg-background shadow-md"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={handleKeyDown}
    >
      <div className="p-3">
        <div className="mb-2 flex items-start justify-between gap-2">
          <p className="text-sm font-medium leading-tight">{insight.title}</p>
          <button
            type="button"
            aria-label="Close insight tooltip"
            className="shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground"
            onClick={onClose}
          >
            <X className="size-3" />
          </button>
        </div>

        <p className="text-sm text-muted-foreground">{insight.analysis}</p>

        {insight.references.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-muted-foreground">References:</p>
            <p className="text-xs font-mono text-primary">{insight.references.join(', ')}</p>
          </div>
        )}

        {insight.suggestedActions.length > 0 && (
          <ul className="mt-2 space-y-0.5">
            {insight.suggestedActions.map((action, i) => (
              <li key={i} className="text-xs text-muted-foreground">
                • {action}
              </li>
            ))}
          </ul>
        )}

        {onDismiss && (
          <button
            type="button"
            aria-label="Dismiss AI insight"
            className="mt-3 text-xs text-muted-foreground hover:text-foreground"
            onClick={handleDismiss}
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function AIInsightBadge({
  insight,
  insufficientData = false,
  onDismiss,
  className,
}: AIInsightBadgeProps) {
  const [open, setOpen] = useState(false);

  const severityKey: InsightSeverity | 'insufficient' =
    insufficientData || !insight ? 'insufficient' : insight.severity;
  const config = SEVERITY_CONFIG[severityKey];
  const Icon = config.icon;

  const label = insight?.title ?? config.label;

  return (
    <div className={cn('relative inline-flex', className)}>
      <button
        type="button"
        aria-label={`AI insight: ${severityKey} - ${label}`}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        className={cn(
          'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] transition-opacity',
          config.badge
        )}
      >
        <Icon className="size-3 shrink-0" />
        <span>{label}</span>
      </button>

      {open && insight && !insufficientData && (
        <InsightTooltip insight={insight} onDismiss={onDismiss} onClose={() => setOpen(false)} />
      )}

      {open && insufficientData && (
        <div
          role="tooltip"
          className="absolute right-0 top-full z-50 mt-1 w-64 rounded-lg border bg-background p-3 shadow-md"
        >
          <p className="text-sm text-muted-foreground">
            AI insights require at least 3 completed sprints.
          </p>
        </div>
      )}
    </div>
  );
}
