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
import {
  CheckCircle2,
  ListTodo,
  Search,
  ChevronDown,
  ChevronRight,
  Loader2,
  Check,
  Pencil,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  ExtractedIssue,
  DecomposedSubtask,
  DuplicateCandidate,
} from '@/stores/ai/types/events';
import Link from 'next/link';
import { ContextNotesResultCard, ContextIssuesResultCard } from './ContextCards';
import { StandupResultCard } from './StandupResultCard';
import type { CreatedIssueData } from './AssistantMessage';

// Re-export so existing barrel imports continue to work
export { formatStandupForClipboard } from './StandupResultCard';

interface StructuredResultCardProps {
  schemaType: string;
  data: Record<string, unknown>;
  className?: string;
  onCreateIssues?: (
    selectedIndices: number[],
    editOverrides?: Map<number, { title?: string; priority?: string }>
  ) => Promise<CreatedIssueData[] | void> | void;
  isCreatingIssues?: boolean;
  createdIssues?: CreatedIssueData[] | null;
  workspaceSlug?: string;
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

const PRIORITY_OPTIONS = ['urgent', 'high', 'medium', 'low', 'none'] as const;

/** Confidence label and color based on score */
function getConfidenceDisplay(score: number): { label: string; className: string } {
  if (score >= 0.7)
    return {
      label: 'High',
      className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    };
  if (score >= 0.5)
    return {
      label: 'Medium',
      className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    };
  return {
    label: 'Low',
    className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };
}

// ─── Extraction Result ───────────────────────────────────────────────────

interface ExtractionResultCardProps {
  data: Record<string, unknown>;
  onCreateIssues?: (
    selectedIndices: number[],
    editOverrides?: Map<number, { title?: string; priority?: string }>
  ) => Promise<CreatedIssueData[] | void> | void;
  isCreatingIssues?: boolean;
  createdIssues?: CreatedIssueData[] | null;
  workspaceSlug?: string;
}

function ExtractionResultCard({
  data,
  onCreateIssues,
  isCreatingIssues,
  createdIssues,
  workspaceSlug,
}: ExtractionResultCardProps) {
  const issues = useMemo(() => (data.issues ?? []) as ExtractedIssue[], [data.issues]);
  const summary = (data.summary ?? '') as string;
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editOverrides, setEditOverrides] = useState<
    Map<number, { title?: string; priority?: string }>
  >(new Map());
  const [isPostCreationExpanded, setIsPostCreationExpanded] = useState(false);

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

  const selectRecommended = useCallback(() => {
    const recommended = new Set<number>();
    issues.forEach((issue, i) => {
      if (issue.priority === 'high' || issue.priority === 'urgent') {
        recommended.add(i);
      }
    });
    // If no high/urgent, select all as fallback
    setSelectedIds(recommended.size > 0 ? recommended : new Set(issues.map((_, i) => i)));
  }, [issues]);

  const updateOverride = useCallback((idx: number, field: 'title' | 'priority', value: string) => {
    setEditOverrides((prev) => {
      const next = new Map(prev);
      const existing = next.get(idx) ?? {};
      next.set(idx, { ...existing, [field]: value });
      return next;
    });
  }, []);

  const handleCreate = useCallback(() => {
    if (onCreateIssues) {
      onCreateIssues(Array.from(selectedIds), editOverrides);
    }
  }, [onCreateIssues, selectedIds, editOverrides]);

  if (issues.length === 0) {
    return <p className="text-sm text-muted-foreground">No issues found.</p>;
  }

  // R2: Post-creation collapsed success state
  if (createdIssues && createdIssues.length > 0) {
    return (
      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setIsPostCreationExpanded(!isPostCreationExpanded)}
          className="flex w-full items-center gap-2 text-left"
          aria-expanded={isPostCreationExpanded}
        >
          <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
          <span className="text-sm font-medium text-green-700 dark:text-green-400">
            Created {createdIssues.length} issue{createdIssues.length !== 1 ? 's' : ''}
          </span>
          <ChevronDown
            className={cn(
              'ml-auto h-3 w-3 text-muted-foreground transition-transform',
              isPostCreationExpanded && 'rotate-180'
            )}
          />
        </button>
        {isPostCreationExpanded && (
          <div className="flex flex-wrap gap-2 pl-6">
            {createdIssues.map((issue) =>
              workspaceSlug ? (
                <Link
                  key={issue.id}
                  href={`/${workspaceSlug}/issues/${issue.id}`}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-md px-2 py-1',
                    'text-xs font-medium text-primary',
                    'bg-primary/10 hover:bg-primary/20 transition-colors'
                  )}
                  title={issue.title}
                >
                  {issue.identifier}
                </Link>
              ) : (
                <span
                  key={issue.id}
                  className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                >
                  {issue.identifier}
                </span>
              )
            )}
          </div>
        )}
      </div>
    );
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
        {issues.map((issue, idx) => {
          const isEditing = editingIdx === idx;
          const override = editOverrides.get(idx);
          const displayTitle = override?.title ?? issue.title;
          const displayPriority = override?.priority ?? issue.priority;
          const confidenceDisplay =
            issue.confidence != null ? getConfidenceDisplay(issue.confidence) : null;

          return (
            <div
              key={idx}
              className={cn(
                'rounded-[10px] border p-3 transition-all duration-150',
                selectedIds.has(idx)
                  ? 'border-primary/40 bg-primary-muted'
                  : 'border-border bg-background'
              )}
            >
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <button
                  type="button"
                  onClick={() => toggleIssue(idx)}
                  className="mt-0.5 shrink-0"
                  aria-label={`${selectedIds.has(idx) ? 'Deselect' : 'Select'} issue: ${displayTitle}`}
                >
                  <div
                    className={cn(
                      'h-4 w-4 rounded border transition-colors',
                      selectedIds.has(idx)
                        ? 'border-primary bg-primary'
                        : 'border-muted-foreground/30'
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
                </button>

                <div className="flex-1 min-w-0">
                  {/* R3: Inline editing mode */}
                  {isEditing ? (
                    <div className="space-y-2">
                      <input
                        type="text"
                        value={displayTitle}
                        onChange={(e) => updateOverride(idx, 'title', e.target.value)}
                        className={cn(
                          'w-full rounded-md border border-border bg-background px-2 py-1',
                          'text-sm font-medium focus:outline-none focus:ring-1 focus:ring-primary'
                        )}
                        aria-label="Edit issue title"
                      />
                      <div className="flex items-center gap-2">
                        <select
                          value={displayPriority}
                          onChange={(e) => updateOverride(idx, 'priority', e.target.value)}
                          className={cn(
                            'rounded-md border border-border bg-background px-2 py-1',
                            'text-xs focus:outline-none focus:ring-1 focus:ring-primary'
                          )}
                          aria-label="Edit issue priority"
                        >
                          {PRIORITY_OPTIONS.map((p) => (
                            <option key={p} value={p}>
                              {p.charAt(0).toUpperCase() + p.slice(1)}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => setEditingIdx(null)}
                          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                          aria-label="Done editing"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">{displayTitle}</span>
                        <span
                          className={cn(
                            'inline-flex h-2 w-2 shrink-0 rounded-full',
                            PRIORITY_DOTS[displayPriority] ?? PRIORITY_DOTS.none
                          )}
                          title={displayPriority}
                        />
                        <span
                          className={cn('text-xs capitalize', PRIORITY_COLORS[displayPriority])}
                        >
                          {displayPriority}
                        </span>
                        {/* R4: Confidence badge */}
                        {confidenceDisplay && (
                          <span
                            className={cn(
                              'text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0',
                              confidenceDisplay.className
                            )}
                          >
                            {confidenceDisplay.label}
                          </span>
                        )}
                        {/* R3: Edit toggle */}
                        {onCreateIssues && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingIdx(idx);
                            }}
                            className="ml-auto shrink-0 text-muted-foreground hover:text-foreground transition-colors"
                            aria-label="Edit issue"
                          >
                            <Pencil className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                      {issue.description && (
                        <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                          {issue.description}
                        </p>
                      )}
                      {/* R5: Labels display */}
                      {issue.labels && issue.labels.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {issue.labels.map((label, i) => (
                            <span
                              key={i}
                              className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                            >
                              {label}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="rounded bg-muted px-1.5 py-0.5 capitalize">
                          {issue.issue_type}
                        </span>
                        <span className="capitalize">{issue.category}</span>
                        {issue.source_block_id && <span>Block #{issue.source_block_id}</span>}
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-2 pt-1">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={selectAll}
            className="text-xs text-primary hover:text-primary-hover transition-colors"
          >
            Select All
          </button>
          <button
            type="button"
            onClick={selectRecommended}
            className="text-xs text-primary hover:text-primary-hover transition-colors"
          >
            Select Recommended
          </button>
          {selectedIds.size > 0 && (
            <span className="text-xs text-muted-foreground">{selectedIds.size} selected</span>
          )}
        </div>
        {onCreateIssues && selectedIds.size > 0 && (
          <button
            type="button"
            onClick={handleCreate}
            disabled={isCreatingIssues}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-[10px] px-3 py-1.5 text-xs font-medium transition-all',
              'bg-[var(--ai)] text-white hover:bg-[var(--ai)]/90',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {isCreatingIssues ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <CheckCircle2 className="h-3 w-3" />
            )}
            {isCreatingIssues
              ? 'Creating...'
              : `Create ${selectedIds.size} Issue${selectedIds.size !== 1 ? 's' : ''}`}
          </button>
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

export const StructuredResultCard = memo<StructuredResultCardProps>(
  ({
    schemaType,
    data,
    className,
    onCreateIssues,
    isCreatingIssues,
    createdIssues,
    workspaceSlug,
  }) => {
    const renderContent = () => {
      switch (schemaType) {
        case 'extraction_result':
          return (
            <ExtractionResultCard
              data={data}
              onCreateIssues={onCreateIssues}
              isCreatingIssues={isCreatingIssues}
              createdIssues={createdIssues}
              workspaceSlug={workspaceSlug}
            />
          );
        case 'decomposition_result':
          return <DecompositionResultCard data={data} />;
        case 'duplicate_search_result':
          return <DuplicateSearchResultCard data={data} />;
        case 'standup_result':
          return <StandupResultCard data={data} />;
        case 'context_notes_result':
          return <ContextNotesResultCard data={data} />;
        case 'context_issues_result':
          return <ContextIssuesResultCard data={data} />;
        default:
          return (
            <div className="text-xs text-muted-foreground">Unknown result type: {schemaType}</div>
          );
      }
    };

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
        {renderContent()}
      </div>
    );
  }
);

StructuredResultCard.displayName = 'StructuredResultCard';
