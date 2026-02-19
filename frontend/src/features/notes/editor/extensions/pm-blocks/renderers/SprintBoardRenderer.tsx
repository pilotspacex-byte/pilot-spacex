'use client';

/**
 * SprintBoardRenderer — Sprint board PM block renderer.
 *
 * FR-049: 6 state-based lanes (backlog/todo/in_progress/in_review/done/cancelled).
 * FR-050: AI-proposed state transitions with Approve/Reject.
 * FR-060: Read-only fallback when CRDT unavailable.
 * FR-056–059: AI insight badge.
 *
 * Data shape (stored in block.data):
 *   { workspaceId: string, cycleId: string, title?: string }
 *
 * Live sprint board data is fetched from the API via TanStack Query.
 *
 * @module pm-blocks/renderers/SprintBoardRenderer
 */
import { useCallback, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, RefreshCw, Lock, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlocksApi } from '@/services/api/pm-blocks';
import { issuesApi } from '@/services/api/issues';
import { pmBlockStyles } from '../pm-block-styles';
import { AIInsightBadge } from '../shared/AIInsightBadge';
import type { PMRendererProps } from '../PMBlockNodeView';
import type {
  SprintBoardLane,
  SprintBoardIssueCard,
  PMBlockInsight,
} from '@/services/api/pm-blocks';

// ── Lane config ───────────────────────────────────────────────────────────────

const LANE_COLORS: Record<string, string> = {
  backlog: 'bg-muted/40',
  todo: 'bg-[#5B8FC9]/8',
  in_progress: 'bg-[#D9853F]/8',
  in_review: 'bg-primary/8',
  done: 'bg-primary/12',
  cancelled: 'bg-muted/20',
};

const LANE_LABEL_COLORS: Record<string, string> = {
  backlog: 'text-muted-foreground',
  todo: 'text-[#5B8FC9] dark:text-[#7DA4C4]',
  in_progress: 'text-[#D9853F]',
  in_review: 'text-primary',
  done: 'text-primary',
  cancelled: 'text-muted-foreground/60',
};

const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'bg-red-500/15 text-red-600 dark:text-red-400',
  high: 'bg-orange-500/15 text-orange-600 dark:text-orange-400',
  medium: 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400',
  low: 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
  none: 'bg-muted text-muted-foreground',
};

// ── Sub-components ────────────────────────────────────────────────────────────

interface IssueCardProps {
  issue: SprintBoardIssueCard;
  readOnly: boolean;
  onDragStart?: (issueId: string, fromStateGroup: string) => void;
  onProposeTransition?: (issueId: string, newState: string) => void;
}

function IssueCard({ issue, readOnly, onDragStart, onProposeTransition }: IssueCardProps) {
  const priorityColor = PRIORITY_COLORS[issue.priority?.toLowerCase()] ?? PRIORITY_COLORS.none;

  return (
    <div
      className={cn(
        'group/card rounded-lg border border-border bg-background p-2.5 shadow-sm dark:bg-card',
        !readOnly && 'cursor-grab active:cursor-grabbing'
      )}
      data-testid={`issue-card-${issue.id}`}
      role="listitem"
      draggable={!readOnly}
      onDragStart={
        !readOnly && onDragStart
          ? (e) => {
              e.dataTransfer.setData(
                'text/plain',
                JSON.stringify({ issueId: issue.id, fromStateGroup: issue.stateName })
              );
              e.dataTransfer.effectAllowed = 'move';
              onDragStart(issue.id, issue.stateName);
            }
          : undefined
      }
    >
      <div className="flex items-start justify-between gap-1.5">
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-mono text-muted-foreground">{issue.identifier}</p>
          <p className="mt-0.5 text-xs font-medium leading-snug text-foreground line-clamp-2">
            {issue.name}
          </p>
        </div>
        <span
          className={cn(
            'shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium leading-none',
            priorityColor
          )}
        >
          {issue.priority ?? 'none'}
        </span>
      </div>

      {(issue.assigneeName || (issue.labels?.length ?? 0) > 0) && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1">
          {issue.assigneeName && (
            <span className="text-[10px] text-muted-foreground">{issue.assigneeName}</span>
          )}
          {issue.labels?.slice(0, 2).map((label) => (
            <span
              key={label}
              className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
              {label}
            </span>
          ))}
        </div>
      )}

      {!readOnly && onProposeTransition && (
        <div className="mt-1.5 flex justify-end opacity-0 group-hover/card:opacity-100 transition-opacity motion-reduce:transition-none">
          <button
            type="button"
            className="text-[10px] text-primary hover:underline"
            onClick={() => onProposeTransition(issue.id, issue.stateName)}
            aria-label={`Propose state transition for ${issue.identifier}`}
          >
            Move →
          </button>
        </div>
      )}
    </div>
  );
}

interface LaneColumnProps {
  lane: SprintBoardLane;
  readOnly: boolean;
  onDropIssue?: (issueId: string, fromStateGroup: string, toStateGroup: string) => void;
  onProposeTransition?: (issueId: string, newState: string) => void;
}

function LaneColumn({ lane, readOnly, onDropIssue, onProposeTransition }: LaneColumnProps) {
  const stateKey = lane.stateGroup?.toLowerCase().replace(/\s+/g, '_') ?? 'backlog';
  const bgColor = LANE_COLORS[stateKey] ?? 'bg-muted/30';
  const labelColor = LANE_LABEL_COLORS[stateKey] ?? 'text-muted-foreground';
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      if (readOnly) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      setIsDragOver(true);
    },
    [readOnly]
  );

  const handleDragLeave = useCallback(() => setIsDragOver(false), []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      if (readOnly || !onDropIssue) return;
      e.preventDefault();
      setIsDragOver(false);
      try {
        const payload = JSON.parse(e.dataTransfer.getData('text/plain')) as {
          issueId: string;
          fromStateGroup: string;
        };
        if (payload.fromStateGroup !== lane.stateGroup) {
          onDropIssue(payload.issueId, payload.fromStateGroup, lane.stateGroup);
        }
      } catch {
        // Malformed drag payload — ignore
      }
    },
    [readOnly, onDropIssue, lane.stateGroup]
  );

  return (
    <div
      className={cn(
        'flex min-w-[180px] flex-col gap-2 rounded-lg p-2 transition-colors motion-reduce:transition-none',
        bgColor,
        isDragOver && !readOnly && 'ring-2 ring-primary/40'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Lane header */}
      <div className="flex items-center justify-between px-0.5">
        <span className={cn('text-[11px] font-semibold uppercase tracking-wide', labelColor)}>
          {lane.stateName}
        </span>
        <span className="text-[11px] font-mono text-muted-foreground">{lane.count}</span>
      </div>

      {/* Issue cards */}
      <div className="flex flex-col gap-1.5" role="list" aria-label={`${lane.stateName} issues`}>
        {lane.issues.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            readOnly={readOnly}
            onProposeTransition={onProposeTransition}
          />
        ))}
        {lane.issues.length === 0 && (
          <p className="py-4 text-center text-[11px] text-muted-foreground/60">Empty</p>
        )}
      </div>
    </div>
  );
}

// ── AI Transition Proposal ────────────────────────────────────────────────────

interface TransitionProposalBannerProps {
  proposal: { issueId: string; currentState: string } | null;
  onApprove: () => void;
  onReject: () => void;
}

export function TransitionProposalBanner({
  proposal,
  onApprove,
  onReject,
}: TransitionProposalBannerProps) {
  if (!proposal) return null;

  return (
    <div
      className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-xs"
      role="alert"
      aria-live="polite"
    >
      <span className="flex-1 text-foreground">AI proposes moving issue to next state. Apply?</span>
      <button
        type="button"
        className="flex items-center gap-1 rounded-md px-2 py-1 font-medium text-primary hover:bg-primary/10 transition-colors"
        onClick={onApprove}
        aria-label="Approve AI state transition"
      >
        <CheckCircle className="size-3" />
        Approve
      </button>
      <button
        type="button"
        className="flex items-center gap-1 rounded-md px-2 py-1 font-medium text-muted-foreground hover:bg-muted transition-colors"
        onClick={onReject}
        aria-label="Reject AI state transition"
      >
        <XCircle className="size-3" />
        Reject
      </button>
    </div>
  );
}

// ── Board data types ──────────────────────────────────────────────────────────

interface SprintBoardBlockData {
  workspaceId?: string;
  cycleId?: string;
  title?: string;
}

// ── Main renderer ─────────────────────────────────────────────────────────────

const QUERY_KEYS = {
  board: (workspaceId: string, cycleId: string) =>
    ['pm-blocks', 'sprint-board', workspaceId, cycleId] as const,
  insights: (workspaceId: string, blockId: string) =>
    ['pm-blocks', 'insights', workspaceId, blockId] as const,
};

export function SprintBoardRenderer({ data: rawData, readOnly }: PMRendererProps) {
  const data = rawData as SprintBoardBlockData;
  const workspaceId = data.workspaceId ?? '';
  const cycleId = data.cycleId ?? '';
  const blockId = `sprint-board-${cycleId}`;

  const queryClient = useQueryClient();
  const boardQueryKey = QUERY_KEYS.board(workspaceId, cycleId);

  const {
    data: boardData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: boardQueryKey,
    queryFn: () => pmBlocksApi.getSprintBoard(workspaceId, cycleId),
    enabled: Boolean(workspaceId && cycleId),
    staleTime: 30_000,
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

  // T-232: Drag-drop optimistic update — move issue between lanes
  const moveIssueMutation = useMutation({
    mutationFn: ({
      issueId,
      newStateGroup,
    }: {
      issueId: string;
      fromStateGroup: string;
      newStateGroup: string;
    }) => issuesApi.updateState(workspaceId, issueId, newStateGroup),
    onMutate: async ({ issueId, fromStateGroup, newStateGroup }) => {
      await queryClient.cancelQueries({ queryKey: boardQueryKey });
      const snapshot = queryClient.getQueryData(boardQueryKey);

      queryClient.setQueryData(boardQueryKey, (prev: typeof boardData) => {
        if (!prev) return prev;
        let movedCard: SprintBoardIssueCard | undefined;
        const lanes = prev.lanes.map((lane) => {
          if (lane.stateGroup === fromStateGroup || lane.issues.some((i) => i.id === issueId)) {
            const filtered = lane.issues.filter((i) => i.id !== issueId);
            movedCard = lane.issues.find((i) => i.id === issueId);
            return { ...lane, issues: filtered, count: filtered.length };
          }
          return lane;
        });
        const withTarget = lanes.map((lane) => {
          if (lane.stateGroup === newStateGroup && movedCard) {
            const updated = { ...movedCard, stateName: lane.stateName, stateId: lane.stateId };
            return { ...lane, issues: [...lane.issues, updated], count: lane.count + 1 };
          }
          return lane;
        });
        return { ...prev, lanes: withTarget };
      });

      return { snapshot };
    },
    onError: (_err, _vars, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData(boardQueryKey, context.snapshot);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: boardQueryKey });
    },
  });

  const handleDropIssue = useCallback(
    (issueId: string, fromStateGroup: string, toStateGroup: string) => {
      moveIssueMutation.mutate({ issueId, fromStateGroup, newStateGroup: toStateGroup });
    },
    [moveIssueMutation]
  );

  const handleDismissInsight = useCallback(
    (insightId: string) => dismissMutation.mutate(insightId),
    [dismissMutation]
  );

  const topInsight = useMemo<PMBlockInsight | null>(() => {
    if (!insights?.length) return null;
    const priority = ['red', 'yellow', 'green'] as const;
    for (const sev of priority) {
      const found = insights.find((i) => i.severity === sev && !i.dismissed);
      if (found) return found;
    }
    return null;
  }, [insights]);

  // T-230: Missing workspace/cycle → config prompt
  if (!workspaceId || !cycleId) {
    return (
      <div className={pmBlockStyles.shared.container}>
        <div className={pmBlockStyles.shared.header}>
          <h3 className={pmBlockStyles.shared.title}>{data.title ?? 'Sprint Board'}</h3>
        </div>
        <p className="text-sm text-muted-foreground py-4 text-center">
          Configure workspace and cycle to display sprint board.
        </p>
      </div>
    );
  }

  return (
    <div className={pmBlockStyles.shared.container} data-testid="sprint-board-renderer">
      {/* Header */}
      <div className={pmBlockStyles.shared.header}>
        <div className="flex items-center gap-2">
          <h3 className={pmBlockStyles.shared.title}>
            {boardData?.cycleName ?? data.title ?? 'Sprint Board'}
          </h3>
          {boardData?.isReadOnly && (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
              aria-label="Read-only mode"
            >
              <Lock className="size-3" />
              Read-only
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* FR-056: AI insight badge */}
          <AIInsightBadge
            insight={topInsight}
            insufficientData={!isInsightsLoading && !insights?.length}
            onDismiss={handleDismissInsight}
          />
          <button
            type="button"
            className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors motion-reduce:transition-none"
            onClick={() => refetch()}
            aria-label="Refresh sprint board"
          >
            <RefreshCw className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          <span className="ml-2 text-sm">Loading sprint board...</span>
        </div>
      )}

      {/* Error state */}
      {isError && !isLoading && (
        <div className="py-4 text-center text-sm text-destructive">
          Failed to load sprint board.{' '}
          <button type="button" className="underline hover:no-underline" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {/* Board lanes — FR-049: 6 state lanes, horizontal scroll */}
      {boardData && (
        <>
          {/* Summary row */}
          <p className="text-xs text-muted-foreground">
            {boardData.totalIssues} issue{boardData.totalIssues !== 1 ? 's' : ''} in{' '}
            {boardData.cycleName}
          </p>

          <div
            className="flex gap-2 overflow-x-auto overscroll-x-contain pb-2"
            role="region"
            aria-label="Sprint board lanes"
          >
            {boardData.lanes.map((lane) => (
              <LaneColumn
                key={lane.stateId}
                lane={lane}
                readOnly={readOnly || Boolean(boardData.isReadOnly)}
                onDropIssue={readOnly || boardData.isReadOnly ? undefined : handleDropIssue}
                onProposeTransition={
                  readOnly || boardData.isReadOnly
                    ? undefined
                    : (issueId, state) => {
                        // FR-050: Dispatch AI propose transition event for the orchestrator
                        document.dispatchEvent(
                          new CustomEvent('pm-block:propose-transition', {
                            detail: { issueId, currentState: state, cycleId },
                          })
                        );
                      }
                }
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
