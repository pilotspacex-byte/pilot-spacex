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
  CalendarCheck,
  Copy,
  Check,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  ExtractedIssue,
  DecomposedSubtask,
  DuplicateCandidate,
} from '@/stores/ai/types/events';
import { ContextNotesResultCard, ContextIssuesResultCard } from './ContextCards';

interface StructuredResultCardProps {
  schemaType: string;
  data: Record<string, unknown>;
  className?: string;
  onCreateIssues?: (selectedIndices: number[]) => void;
  isCreatingIssues?: boolean;
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

interface ExtractionResultCardProps {
  data: Record<string, unknown>;
  onCreateIssues?: (selectedIndices: number[]) => void;
  isCreatingIssues?: boolean;
}

function ExtractionResultCard({
  data,
  onCreateIssues,
  isCreatingIssues,
}: ExtractionResultCardProps) {
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
            onClick={() => onCreateIssues(Array.from(selectedIds))}
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

// ─── Standup Result ─────────────────────────────────────────────────────

interface StandupItem {
  identifier: string;
  title: string;
  reason?: string;
}

interface StandupResultData {
  yesterday: StandupItem[];
  today: StandupItem[];
  blockers: StandupItem[];
  period: string;
}

/** Format standup data as clean markdown text for Slack/clipboard. */
export function formatStandupForClipboard(data: StandupResultData): string {
  const lines: string[] = [];

  lines.push(`**Daily Standup** — ${data.period}`);
  lines.push('');

  lines.push('**Yesterday (Completed)**');
  if (data.yesterday.length === 0) {
    lines.push('(No items)');
  } else {
    for (const item of data.yesterday) {
      lines.push(`- ${item.identifier}: ${item.title}`);
    }
  }
  lines.push('');

  lines.push('**Today (In Progress)**');
  if (data.today.length === 0) {
    lines.push('(No items)');
  } else {
    for (const item of data.today) {
      lines.push(`- ${item.identifier}: ${item.title}`);
    }
  }
  lines.push('');

  lines.push('**Blockers**');
  if (data.blockers.length === 0) {
    lines.push('(No items)');
  } else {
    for (const item of data.blockers) {
      const suffix = item.reason ? ` — ${item.reason}` : '';
      lines.push(`- ${item.identifier}: ${item.title}${suffix}`);
    }
  }

  return lines.join('\n');
}

function StandupSection({
  heading,
  items,
  accentClass,
  showReason,
}: {
  heading: string;
  items: StandupItem[];
  accentClass: string;
  showReason?: boolean;
}) {
  return (
    <div>
      <h4 className={cn('text-xs font-semibold uppercase tracking-wider mb-2', accentClass)}>
        {heading}
      </h4>
      {items.length === 0 ? (
        <p className="text-xs italic text-muted-foreground">(No items)</p>
      ) : (
        <ul className="space-y-1.5" role="list">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-sm">
              <span
                className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-current opacity-40"
                aria-hidden="true"
              />
              <span>
                <code className="font-mono text-xs text-primary">{item.identifier}</code>{' '}
                <span className="text-foreground">{item.title}</span>
                {showReason && item.reason && (
                  <span className="text-xs text-muted-foreground"> — {item.reason}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StandupResultCard({ data }: { data: Record<string, unknown> }) {
  const standup = data as unknown as StandupResultData;
  const yesterday = standup.yesterday ?? [];
  const today = standup.today ?? [];
  const blockers = standup.blockers ?? [];
  const period = standup.period ?? '';

  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    const text = formatStandupForClipboard({ yesterday, today, blockers, period });
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {
        // Clipboard API may fail (permission denied, non-HTTPS, no user gesture)
      });
  }, [yesterday, today, blockers, period]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CalendarCheck className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="text-sm font-medium">Daily Standup</span>
          {period && <span className="text-xs text-muted-foreground">{period}</span>}
        </div>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={copied ? 'Copied to clipboard' : 'Copy standup to clipboard'}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium',
            'transition-colors duration-150',
            'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            copied ? 'text-primary' : 'text-muted-foreground'
          )}
        >
          {copied ? (
            <>
              <Check className="h-3 w-3" aria-hidden="true" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" aria-hidden="true" />
              Copy
            </>
          )}
        </button>
      </div>

      <StandupSection
        heading="Yesterday (Completed)"
        items={yesterday}
        accentClass="text-muted-foreground"
      />
      <StandupSection heading="Today (In Progress)" items={today} accentClass="text-primary" />
      <StandupSection heading="Blockers" items={blockers} accentClass="text-amber-500" showReason />
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────

export const StructuredResultCard = memo<StructuredResultCardProps>(
  ({ schemaType, data, className, onCreateIssues, isCreatingIssues }) => {
    const renderContent = () => {
      switch (schemaType) {
        case 'extraction_result':
          return (
            <ExtractionResultCard
              data={data}
              onCreateIssues={onCreateIssues}
              isCreatingIssues={isCreatingIssues}
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
