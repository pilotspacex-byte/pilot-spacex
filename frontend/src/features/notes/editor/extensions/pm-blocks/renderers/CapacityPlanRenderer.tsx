'use client';

/**
 * CapacityPlanRenderer — Capacity plan PM block renderer.
 *
 * FR-053: Available vs committed hours per member, utilization bar.
 * FR-056–059: AI insight badge.
 *
 * Data shape (stored in block.data):
 *   { workspaceId: string, cycleId: string, title?: string }
 *
 * @module pm-blocks/renderers/CapacityPlanRenderer
 */
import { useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, RefreshCw, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlocksApi } from '@/services/api/pm-blocks';
import { pmBlockStyles } from '../pm-block-styles';
import { AIInsightBadge } from '../shared/AIInsightBadge';
import type { PMRendererProps } from '../PMBlockNodeView';
import type { CapacityMember, PMBlockInsight } from '@/services/api/pm-blocks';

// ── Utilization bar ───────────────────────────────────────────────────────────

function UtilizationBar({ pct, isOverAllocated }: { pct: number; isOverAllocated: boolean }) {
  const clamped = Math.min(pct, 100);
  const overflow = Math.max(0, pct - 100);
  const color = isOverAllocated ? 'bg-destructive' : pct >= 85 ? 'bg-[#D9853F]' : 'bg-primary';

  return (
    <div
      className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted"
      role="meter"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuetext={`${Math.round(pct)}% utilized`}
    >
      <div
        className={cn(
          'h-full rounded-full transition-all duration-300 motion-reduce:transition-none',
          color
        )}
        style={{ width: `${clamped}%` }}
      />
      {overflow > 0 && (
        <div
          className="absolute right-0 top-0 h-full rounded-full bg-destructive/40"
          style={{ width: `${Math.min(overflow, 20)}%` }}
        />
      )}
    </div>
  );
}

// ── Member row ────────────────────────────────────────────────────────────────

function MemberRow({ member }: { member: CapacityMember }) {
  return (
    <div
      role="row"
      className={cn(
        'flex items-center gap-3 rounded-lg border px-3 py-2',
        member.isOverAllocated
          ? 'border-destructive/30 bg-destructive/5'
          : 'border-border bg-background dark:bg-card'
      )}
      data-testid={`member-row-${member.userId}`}
    >
      {/* Avatar */}
      <div
        role="cell"
        className="size-7 shrink-0 rounded-full bg-muted flex items-center justify-center text-xs font-medium text-muted-foreground overflow-hidden"
      >
        {member.avatarUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={member.avatarUrl} alt={member.displayName} className="size-full object-cover" />
        ) : (
          member.displayName.charAt(0).toUpperCase()
        )}
      </div>

      {/* Name + bar */}
      <div role="cell" className="min-w-0 flex-1 flex flex-col gap-1">
        <div className="flex items-center justify-between gap-1">
          <span className="text-xs font-medium text-foreground truncate">{member.displayName}</span>
          <span
            className={cn(
              'shrink-0 text-[10px] font-mono tabular-nums',
              member.isOverAllocated ? 'text-destructive font-semibold' : 'text-muted-foreground'
            )}
          >
            {member.committedHours}h / {member.availableHours}h
          </span>
        </div>
        <UtilizationBar pct={member.utilizationPct} isOverAllocated={member.isOverAllocated} />
      </div>

      {/* Utilization % */}
      <div role="cell" className="shrink-0 flex items-center gap-1">
        {member.isOverAllocated && (
          <AlertTriangle className="size-3 text-destructive" aria-label="Over-allocated" />
        )}
        <span
          className={cn(
            'text-[11px] font-semibold tabular-nums',
            member.isOverAllocated
              ? 'text-destructive'
              : member.utilizationPct >= 85
                ? 'text-[#D9853F]'
                : 'text-foreground'
          )}
        >
          {Math.round(member.utilizationPct)}%
        </span>
      </div>
    </div>
  );
}

// ── Team summary row ──────────────────────────────────────────────────────────

function TeamSummary({
  available,
  committed,
  utilization,
}: {
  available: number;
  committed: number;
  utilization: number;
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 px-3 py-2.5 flex items-center justify-between gap-3">
      <div className="flex flex-col">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
          Team Total
        </span>
        <span className="text-sm font-semibold tabular-nums text-foreground">
          {committed}h{' '}
          <span className="text-xs font-normal text-muted-foreground">/ {available}h</span>
        </span>
      </div>

      <div className="flex-1 max-w-[160px]">
        <UtilizationBar pct={utilization} isOverAllocated={utilization > 100} />
        <p className="mt-0.5 text-right text-[10px] text-muted-foreground">
          {Math.round(utilization)}% utilized
        </p>
      </div>
    </div>
  );
}

// ── Block data types ──────────────────────────────────────────────────────────

interface CapacityBlockData {
  workspaceId?: string;
  cycleId?: string;
  title?: string;
}

// ── Query keys ────────────────────────────────────────────────────────────────

const QUERY_KEYS = {
  plan: (workspaceId: string, cycleId: string) =>
    ['pm-blocks', 'capacity-plan', workspaceId, cycleId] as const,
  insights: (workspaceId: string, blockId: string) =>
    ['pm-blocks', 'insights', workspaceId, blockId] as const,
};

// ── Main renderer ─────────────────────────────────────────────────────────────

export function CapacityPlanRenderer({ data: rawData }: PMRendererProps) {
  const data = rawData as CapacityBlockData;
  const workspaceId = data.workspaceId ?? '';
  const cycleId = data.cycleId ?? '';
  const blockId = `capacity-plan-${cycleId}`;

  const queryClient = useQueryClient();

  const {
    data: planData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.plan(workspaceId, cycleId),
    queryFn: () => pmBlocksApi.getCapacityPlan(workspaceId, cycleId),
    enabled: Boolean(workspaceId && cycleId),
    staleTime: 60_000,
  });

  const { data: insights, isLoading: isInsightsLoading } = useQuery({
    queryKey: QUERY_KEYS.insights(workspaceId, blockId),
    queryFn: () => pmBlocksApi.listInsights(workspaceId, blockId),
    enabled: Boolean(workspaceId),
    staleTime: 60_000,
  });

  const dismissMutation = useMutation({
    mutationFn: (insightId: string) => pmBlocksApi.dismissInsight(workspaceId, insightId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.insights(workspaceId, blockId) });
    },
  });

  const handleDismissInsight = useCallback(
    (insightId: string) => dismissMutation.mutate(insightId),
    [dismissMutation]
  );

  const topInsight = useMemo<PMBlockInsight | null>(() => {
    if (!insights?.length) return null;
    for (const sev of ['red', 'yellow', 'green'] as const) {
      const found = insights.find((i) => i.severity === sev && !i.dismissed);
      if (found) return found;
    }
    return null;
  }, [insights]);

  const overAllocatedCount = useMemo(
    () => planData?.members.filter((m) => m.isOverAllocated).length ?? 0,
    [planData]
  );

  if (!workspaceId || !cycleId) {
    return (
      <div className={pmBlockStyles.shared.container}>
        <div className={pmBlockStyles.shared.header}>
          <h3 className={pmBlockStyles.shared.title}>{data.title ?? 'Capacity Plan'}</h3>
        </div>
        <p className="text-sm text-muted-foreground py-4 text-center">
          Configure workspace and cycle to display capacity plan.
        </p>
      </div>
    );
  }

  return (
    <div className={pmBlockStyles.shared.container} data-testid="capacity-plan-renderer">
      {/* Header */}
      <div className={pmBlockStyles.shared.header}>
        <div className="flex items-center gap-2">
          <h3 className={pmBlockStyles.shared.title}>
            {planData?.cycleName ?? data.title ?? 'Capacity Plan'}
          </h3>
          {overAllocatedCount > 0 && (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] font-medium text-destructive"
              aria-label={`${overAllocatedCount} over-allocated`}
            >
              <AlertTriangle className="size-3" />
              {overAllocatedCount} over-allocated
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <AIInsightBadge
            insight={topInsight}
            insufficientData={!isInsightsLoading && !insights?.length}
            onDismiss={handleDismissInsight}
          />
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            onClick={() => refetch()}
            aria-label="Refresh capacity plan"
          >
            <RefreshCw className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          <span className="ml-2 text-sm">Loading capacity plan...</span>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="py-4 text-center text-sm text-destructive">
          Failed to load capacity plan.{' '}
          <button type="button" className="underline" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {/* No data */}
      {planData && !planData.hasData && !isLoading && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No capacity data available for this cycle.
        </p>
      )}

      {/* Members list — FR-053 */}
      {planData?.hasData && !isLoading && (
        <>
          <TeamSummary
            available={planData.teamAvailable}
            committed={planData.teamCommitted}
            utilization={planData.teamUtilizationPct}
          />

          <div className="flex flex-col gap-2" role="table" aria-label="Team member capacity">
            {planData.members
              .slice()
              .sort((a, b) => b.utilizationPct - a.utilizationPct)
              .map((member) => (
                <MemberRow key={member.userId} member={member} />
              ))}
          </div>
        </>
      )}
    </div>
  );
}
