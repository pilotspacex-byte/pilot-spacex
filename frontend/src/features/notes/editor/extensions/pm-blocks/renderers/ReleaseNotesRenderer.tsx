'use client';

/**
 * ReleaseNotesRenderer — Release notes PM block renderer.
 *
 * FR-054: Auto-generate release notes from completed issues with AI classification.
 * FR-055: Preserve human edits during regeneration (humanEdited flag).
 * FR-056–059: AI insight badge.
 *
 * Data shape (stored in block.data):
 *   { workspaceId: string, cycleId: string, title?: string }
 *
 * @module pm-blocks/renderers/ReleaseNotesRenderer
 */
import { useCallback, useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, RefreshCw, PenLine } from 'lucide-react';
import { cn } from '@/lib/utils';
import { pmBlocksApi } from '@/services/api/pm-blocks';
import { pmBlockStyles } from '../pm-block-styles';
import { AIInsightBadge } from '../shared/AIInsightBadge';
import type { PMRendererProps } from '../PMBlockNodeView';
import type { ReleaseEntry, PMBlockInsight } from '@/services/api/pm-blocks';

// ── Category config ───────────────────────────────────────────────────────────

const CATEGORY_CONFIG: Record<string, { label: string; badge: string }> = {
  feature: {
    label: 'New Features',
    badge: 'bg-primary/10 text-primary border-primary/20',
  },
  improvement: {
    label: 'Improvements',
    badge: 'bg-[#5B8FC9]/10 text-[#5B8FC9] border-[#5B8FC9]/20 dark:text-[#7DA4C4]',
  },
  bug: {
    label: 'Bug Fixes',
    badge: 'bg-destructive/10 text-destructive border-destructive/20',
  },
  chore: {
    label: 'Maintenance',
    badge: 'bg-muted text-muted-foreground border-border',
  },
  other: {
    label: 'Other',
    badge: 'bg-muted text-muted-foreground border-border',
  },
};

const CATEGORY_ORDER = ['feature', 'improvement', 'bug', 'chore', 'other'];

// ── Entry row ─────────────────────────────────────────────────────────────────

interface EntryRowProps {
  entry: ReleaseEntry;
  readOnly: boolean;
}

function EntryRow({ entry, readOnly: _readOnly }: EntryRowProps) {
  const confidencePct = Math.round(entry.confidence * 100);

  return (
    <div
      className="flex items-start gap-2.5 rounded-md px-2 py-1.5 hover:bg-muted/40 transition-colors motion-reduce:transition-none"
      data-testid={`release-entry-${entry.issueId}`}
      role="listitem"
    >
      <span className="shrink-0 font-mono text-[11px] text-muted-foreground mt-0.5 w-16 truncate">
        {entry.identifier}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-foreground leading-snug">{entry.name}</p>
        {entry.humanEdited && (
          <span className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground mt-0.5">
            <PenLine className="size-2.5" />
            Edited
          </span>
        )}
      </div>
      <span
        className="shrink-0 text-[10px] tabular-nums text-muted-foreground/70 mt-0.5"
        title={`AI confidence: ${confidencePct}%`}
        aria-label={`AI confidence ${confidencePct}%`}
      >
        {confidencePct}%
      </span>
    </div>
  );
}

// ── Category section ──────────────────────────────────────────────────────────

interface CategorySectionProps {
  category: string;
  entries: ReleaseEntry[];
  readOnly: boolean;
}

function CategorySection({ category, entries, readOnly }: CategorySectionProps) {
  const config = (CATEGORY_CONFIG[category] ?? CATEGORY_CONFIG.other)!;

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-2 mb-1">
        <span
          className={cn(
            'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
            config.badge
          )}
        >
          {config.label}
        </span>
        <span className="text-[11px] text-muted-foreground">{entries.length}</span>
      </div>
      <div role="list" aria-label={config.label}>
        {entries.map((entry) => (
          <EntryRow key={entry.issueId} entry={entry} readOnly={readOnly} />
        ))}
      </div>
    </div>
  );
}

// ── Block data types ──────────────────────────────────────────────────────────

interface ReleaseNotesBlockData {
  workspaceId?: string;
  cycleId?: string;
  title?: string;
}

// ── Query keys ────────────────────────────────────────────────────────────────

const QUERY_KEYS = {
  notes: (workspaceId: string, cycleId: string) =>
    ['pm-blocks', 'release-notes', workspaceId, cycleId] as const,
  insights: (workspaceId: string, blockId: string) =>
    ['pm-blocks', 'insights', workspaceId, blockId] as const,
};

// ── Main renderer ─────────────────────────────────────────────────────────────

export function ReleaseNotesRenderer({ data: rawData, readOnly }: PMRendererProps) {
  const data = rawData as ReleaseNotesBlockData;
  const workspaceId = data.workspaceId ?? '';
  const cycleId = data.cycleId ?? '';
  const blockId = `release-notes-${cycleId}`;

  const [showHumanOnly, setShowHumanOnly] = useState(false);
  const queryClient = useQueryClient();

  const {
    data: notesData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: QUERY_KEYS.notes(workspaceId, cycleId),
    queryFn: () => pmBlocksApi.getReleaseNotes(workspaceId, cycleId),
    enabled: Boolean(workspaceId && cycleId),
    staleTime: 120_000,
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

  // Group entries by category, respecting showHumanOnly filter
  const groupedEntries = useMemo(() => {
    const entries = notesData?.entries ?? [];
    const filtered = showHumanOnly ? entries.filter((e) => e.humanEdited) : entries;
    const groups = new Map<string, ReleaseEntry[]>();
    for (const cat of CATEGORY_ORDER) {
      const items = filtered.filter((e) => e.category === cat);
      if (items.length > 0) groups.set(cat, items);
    }
    // Catch any unknown categories
    const unknownCats = new Set(
      filtered.map((e) => e.category).filter((c) => !CATEGORY_ORDER.includes(c))
    );
    for (const cat of unknownCats) {
      const items = filtered.filter((e) => e.category === cat);
      if (items.length > 0) groups.set(cat, items);
    }
    return groups;
  }, [notesData, showHumanOnly]);

  const humanEditedCount = useMemo(
    () => notesData?.entries.filter((e) => e.humanEdited).length ?? 0,
    [notesData]
  );

  const generatedAt = useMemo(() => {
    if (!notesData?.generatedAt) return null;
    try {
      return new Intl.DateTimeFormat('en', { dateStyle: 'medium', timeStyle: 'short' }).format(
        new Date(notesData.generatedAt)
      );
    } catch {
      return notesData.generatedAt;
    }
  }, [notesData]);

  if (!workspaceId || !cycleId) {
    return (
      <div className={pmBlockStyles.shared.container}>
        <div className={pmBlockStyles.shared.header}>
          <h3 className={pmBlockStyles.shared.title}>{data.title ?? 'Release Notes'}</h3>
        </div>
        <p className="text-sm text-muted-foreground py-4 text-center">
          Configure workspace and cycle to display release notes.
        </p>
      </div>
    );
  }

  return (
    <div className={pmBlockStyles.shared.container} data-testid="release-notes-renderer">
      {/* Header */}
      <div className={pmBlockStyles.shared.header}>
        <div className="flex flex-col gap-0.5">
          <h3 className={pmBlockStyles.shared.title}>
            {notesData?.versionLabel ?? data.title ?? 'Release Notes'}
          </h3>
          {generatedAt && (
            <p className="text-[10px] text-muted-foreground">Generated {generatedAt}</p>
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
            aria-label="Refresh release notes"
          >
            <RefreshCw className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          <span className="ml-2 text-sm">Generating release notes...</span>
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="py-4 text-center text-sm text-destructive">
          Failed to load release notes.{' '}
          <button type="button" className="underline" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {/* Entries */}
      {notesData && !isLoading && (
        <>
          {/* Toolbar */}
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {notesData.entries.length} issue{notesData.entries.length !== 1 ? 's' : ''} classified
              {humanEditedCount > 0 && (
                <span className="ml-1">· {humanEditedCount} manually edited</span>
              )}
            </p>
            {/* FR-055: filter to show only human-edited entries */}
            {humanEditedCount > 0 && !readOnly && (
              <button
                type="button"
                className={cn(
                  'flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] transition-colors',
                  showHumanOnly
                    ? 'border-primary/40 bg-primary/10 text-primary'
                    : 'border-border bg-transparent text-muted-foreground hover:text-foreground'
                )}
                onClick={() => setShowHumanOnly((v) => !v)}
                aria-pressed={showHumanOnly}
                aria-label="Show only manually edited entries"
              >
                <PenLine className="size-3" />
                Edited only
              </button>
            )}
          </div>

          {notesData.entries.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No completed issues found for this cycle.
            </p>
          ) : groupedEntries.size === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              No manually edited entries.
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              {[...groupedEntries.entries()].map(([category, entries]) => (
                <CategorySection
                  key={category}
                  category={category}
                  entries={entries}
                  readOnly={readOnly}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
