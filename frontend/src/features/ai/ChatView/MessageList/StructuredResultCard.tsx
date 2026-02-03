/**
 * StructuredResultCard - Rich rendering of typed AI structured outputs.
 *
 * Renders schema-validated results (issue extraction, task decomposition,
 * duplicate detection) as interactive cards instead of plain text.
 *
 * Design: Warm, capable aesthetic per ui-design-spec.md v4.0
 */

'use client';

import { memo, useState, useCallback, useMemo } from 'react';
import { CheckCircle2, ListTodo, Search, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  ExtractedIssue,
  DecomposedSubtask,
  DuplicateCandidate,
} from '@/stores/ai/types/events';

interface StructuredResultCardProps {
  schemaType: string;
  data: Record<string, unknown>;
  className?: string;
}

/** Priority color mapping */
const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'text-red-500',
  high: 'text-orange-500',
  medium: 'text-amber-500',
  low: 'text-blue-400',
  none: 'text-muted-foreground',
};

/** Priority dot color mapping */
const PRIORITY_DOTS: Record<string, string> = {
  urgent: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-amber-500',
  low: 'bg-blue-400',
  none: 'bg-muted-foreground',
};

// ─── Extraction Result ───────────────────────────────────────────────────

function ExtractionResultCard({ data }: { data: Record<string, unknown> }) {
  const issues = useMemo(() => (data.issues ?? []) as ExtractedIssue[], [data.issues]);
  const summary = (data.summary ?? '') as string;
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const toggleIssue = useCallback((idx: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(issues.map((_, i) => i)));
  }, [issues]);

  if (issues.length === 0) {
    return <p className="text-sm text-muted-foreground">No issues found.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">
          Extracted {issues.length} Issue{issues.length !== 1 ? 's' : ''}
        </span>
      </div>

      {summary && <p className="text-xs text-muted-foreground">{summary}</p>}

      <div className="space-y-2">
        {issues.map((issue, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => toggleIssue(idx)}
            className={cn(
              'flex w-full items-start gap-3 rounded-[10px] border p-3 text-left transition-all duration-150',
              'hover:-translate-y-px hover:shadow-sm',
              selectedIds.has(idx)
                ? 'border-primary/40 bg-primary-muted'
                : 'border-border bg-background'
            )}
          >
            <div
              className={cn(
                'mt-0.5 h-4 w-4 shrink-0 rounded border transition-colors',
                selectedIds.has(idx) ? 'border-primary bg-primary' : 'border-muted-foreground/30'
              )}
            >
              {selectedIds.has(idx) && (
                <svg viewBox="0 0 16 16" className="h-4 w-4 text-white">
                  <path
                    d="M5 8l2 2 4-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{issue.title}</span>
                <span
                  className={cn(
                    'inline-flex h-2 w-2 shrink-0 rounded-full',
                    PRIORITY_DOTS[issue.priority] ?? PRIORITY_DOTS.none
                  )}
                  title={issue.priority}
                />
                <span className={cn('text-xs capitalize', PRIORITY_COLORS[issue.priority])}>
                  {issue.priority}
                </span>
              </div>
              {issue.description && (
                <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                  {issue.description}
                </p>
              )}
              <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                <span className="rounded bg-muted px-1.5 py-0.5 capitalize">
                  {issue.issue_type}
                </span>
                <span className="capitalize">{issue.category}</span>
                {issue.source_block_id && <span>Block #{issue.source_block_id}</span>}
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={selectAll}
          className="text-xs text-primary hover:text-primary-hover transition-colors"
        >
          Select All
        </button>
        {selectedIds.size > 0 && (
          <span className="text-xs text-muted-foreground">{selectedIds.size} selected</span>
        )}
      </div>
    </div>
  );
}

// ─── Decomposition Result ────────────────────────────────────────────────

function DecompositionResultCard({ data }: { data: Record<string, unknown> }) {
  const subtasks = (data.subtasks ?? []) as DecomposedSubtask[];
  const totalPoints = (data.totalPoints ?? 0) as number;
  const summary = (data.summary ?? '') as string;
  const [expanded, setExpanded] = useState(false);

  if (subtasks.length === 0) {
    return <p className="text-sm text-muted-foreground">No subtasks generated.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <ListTodo className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">
          Task Breakdown &mdash; {subtasks.length} subtask{subtasks.length !== 1 ? 's' : ''}
        </span>
      </div>

      {summary && <p className="text-xs text-muted-foreground">{summary}</p>}

      <div className="space-y-1.5">
        {subtasks.map((task, idx) => {
          const hasDeps = task.dependsOn && task.dependsOn.length > 0;
          return (
            <div
              key={idx}
              className="flex items-center gap-3 rounded-[10px] border border-border bg-background px-3 py-2"
            >
              <span className="text-xs font-mono text-muted-foreground w-5 shrink-0">
                {idx + 1}.
              </span>
              <span className="flex-1 text-sm">{task.title}</span>
              <span className="text-xs text-muted-foreground shrink-0">
                {task.storyPoints} pt{task.storyPoints !== 1 ? 's' : ''}
              </span>
              {hasDeps && (
                <span className="text-xs text-muted-foreground shrink-0">
                  ← {task.dependsOn.map((d) => d + 1).join(', ')}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between pt-1 text-xs text-muted-foreground">
        <span>
          Total: {totalPoints} point{totalPoints !== 1 ? 's' : ''}
        </span>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-primary hover:text-primary-hover transition-colors"
        >
          {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          {expanded ? 'Hide details' : 'Show details'}
        </button>
      </div>

      {expanded && (
        <div className="space-y-2 border-t border-border pt-2">
          {subtasks.map(
            (task, idx) =>
              task.description && (
                <div key={idx} className="text-xs text-muted-foreground">
                  <span className="font-medium">
                    {idx + 1}. {task.title}:
                  </span>{' '}
                  {task.description}
                </div>
              )
          )}
        </div>
      )}
    </div>
  );
}

// ─── Duplicate Search Result ─────────────────────────────────────────────

function DuplicateSearchResultCard({ data }: { data: Record<string, unknown> }) {
  const candidates = (data.candidates ?? []) as DuplicateCandidate[];
  const queryTitle = (data.queryTitle ?? '') as string;
  const threshold = (data.threshold ?? 0.7) as number;

  if (candidates.length === 0) {
    return (
      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-primary" />
        <span className="text-sm text-muted-foreground">
          No duplicates found above {Math.round(threshold * 100)}% similarity.
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">
          {candidates.length} Potential Duplicate{candidates.length !== 1 ? 's' : ''}
        </span>
      </div>

      {queryTitle && (
        <p className="text-xs text-muted-foreground">Searching for: &ldquo;{queryTitle}&rdquo;</p>
      )}

      <div className="space-y-2">
        {candidates.map((candidate, idx) => (
          <div
            key={idx}
            className="flex items-center gap-3 rounded-[10px] border border-border bg-background px-3 py-2"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-primary">{candidate.issueKey}</span>
                <span className="text-sm truncate">{candidate.title}</span>
              </div>
              {candidate.reason && (
                <p className="mt-0.5 text-xs text-muted-foreground">{candidate.reason}</p>
              )}
            </div>
            <div
              className={cn(
                'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                candidate.similarityScore >= 0.9
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  : candidate.similarityScore >= 0.8
                    ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                    : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
              )}
            >
              {Math.round(candidate.similarityScore * 100)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────

const SCHEMA_RENDERERS: Record<
  string,
  (props: { data: Record<string, unknown> }) => React.ReactElement
> = {
  extraction_result: ExtractionResultCard,
  decomposition_result: DecompositionResultCard,
  duplicate_search_result: DuplicateSearchResultCard,
};

export const StructuredResultCard = memo<StructuredResultCardProps>(
  ({ schemaType, data, className }) => {
    const Renderer = SCHEMA_RENDERERS[schemaType];

    if (!Renderer) {
      return (
        <div className={cn('text-xs text-muted-foreground', className)}>
          Unknown result type: {schemaType}
        </div>
      );
    }

    return (
      <div
        className={cn(
          'rounded-[12px] border border-border bg-background-subtle p-4',
          'shadow-sm',
          className
        )}
        role="region"
        aria-label={`Structured result: ${schemaType}`}
      >
        <Renderer data={data} />
      </div>
    );
  }
);

StructuredResultCard.displayName = 'StructuredResultCard';
