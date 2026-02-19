'use client';

/**
 * VersionTimeline — scrollable list of note version snapshots.
 *
 * Shows trigger icons, labels, timestamps, author, pin toggle.
 * Handles infinite scroll via `fetchNextPage`.
 *
 * T-216: Version history sidebar
 * T-220: Pin/unpin UI (star icon, aria-pressed, keyboard toggle)
 */
import { useCallback, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bookmark,
  Clock,
  ChevronRight,
  ChevronLeft,
  BookmarkPlus,
  Pin,
  Undo2,
  GitCompare,
} from 'lucide-react';
import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { versionApi, NoteVersionResponse, VersionTrigger } from '../services/versionApi';
import { VersionStore } from '../stores/VersionStore';

interface VersionTimelineProps {
  workspaceId: string;
  noteId: string;
  store: VersionStore;
  currentVersionNumber?: number;
  onUndoAI?: () => void;
}

const TRIGGER_CONFIG: Record<
  VersionTrigger,
  { label: string; dotClass: string; Icon: React.ElementType }
> = {
  manual: {
    label: 'Manual save',
    dotClass: 'bg-primary',
    Icon: Bookmark,
  },
  auto: {
    label: 'Auto-save',
    dotClass: 'bg-muted-foreground',
    Icon: Clock,
  },
  ai_before: {
    label: 'Before AI edit',
    dotClass: 'bg-ai',
    Icon: ChevronRight,
  },
  ai_after: {
    label: 'After AI edit',
    dotClass: 'bg-ai',
    Icon: ChevronLeft,
  },
};

function getDateGroup(dateStr: string): string {
  const d = new Date(dateStr);
  if (isToday(d)) return 'Today';
  if (isYesterday(d)) return 'Yesterday';
  return format(d, 'MMMM d, yyyy');
}

function getAuthorLabel(trigger: VersionTrigger, createdBy: string | null): string {
  if (trigger === 'auto') return 'System';
  if (trigger === 'ai_before' || trigger === 'ai_after') return 'AI';
  return createdBy ? 'You' : 'System';
}

/** A single version entry in the timeline */
const VersionEntry = observer(function VersionEntry({
  version,
  isSelected,
  onSelect,
  onDiff,
  onRestore,
  onPin,
  isPinning,
}: {
  version: NoteVersionResponse;
  isSelected: boolean;
  onSelect: () => void;
  onDiff: () => void;
  onRestore: () => void;
  onPin: (pinned: boolean) => void;
  isPinning: boolean;
}) {
  const cfg = TRIGGER_CONFIG[version.trigger];
  const timeAgo = formatDistanceToNow(new Date(version.createdAt), { addSuffix: true });
  const authorLabel = getAuthorLabel(version.trigger, version.createdBy);

  return (
    <li
      data-selected={isSelected}
      className={cn(
        'group relative flex gap-3 rounded-lg px-3 py-2 cursor-pointer motion-safe:transition-colors',
        isSelected
          ? 'bg-primary/10 border-l-2 border-primary'
          : 'hover:bg-muted/40 border-l-2 border-transparent'
      )}
      onClick={onSelect}
      onDoubleClick={onDiff}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onSelect();
        if (e.key === ' ') {
          e.preventDefault();
          onDiff();
        }
      }}
      tabIndex={0}
    >
      {/* Timeline dot */}
      <div className="flex flex-col items-center pt-0.5 shrink-0">
        <div className={cn('w-2 h-2 rounded-full shrink-0', cfg.dotClass)} />
        <div className="w-0.5 flex-1 bg-border mt-1" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-1">
        <div className="flex items-center justify-between gap-1">
          <div className="flex items-center gap-1.5 min-w-0">
            <cfg.Icon className="w-3 h-3 text-muted-foreground shrink-0" aria-hidden />
            <span className="text-sm font-medium truncate">{cfg.label}</span>
          </div>

          {/* Pin button — T-220 */}
          <button
            type="button"
            aria-label={version.pinned ? 'Unpin version' : 'Pin version'}
            aria-pressed={version.pinned}
            disabled={isPinning}
            className={cn(
              'p-0.5 rounded motion-safe:transition-opacity',
              version.pinned
                ? 'text-primary opacity-100'
                : 'text-muted-foreground opacity-0 group-hover:opacity-100 focus:opacity-100'
            )}
            onClick={(e) => {
              e.stopPropagation();
              onPin(!version.pinned);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                e.stopPropagation();
                onPin(!version.pinned);
              }
            }}
          >
            <Pin
              className="w-3.5 h-3.5"
              fill={version.pinned ? 'currentColor' : 'none'}
              aria-hidden
            />
          </button>
        </div>

        {/* User label */}
        {version.label && (
          <p className="text-xs text-muted-foreground truncate mt-0.5">
            &ldquo;{version.label}&rdquo;
          </p>
        )}

        <p className="text-xs text-muted-foreground tabular-nums mt-0.5">
          {timeAgo} · {authorLabel}
          {version.pinned && (
            <span className="ml-1.5 inline-flex items-center gap-0.5 text-primary font-medium">
              <Pin className="w-2.5 h-2.5" fill="currentColor" aria-hidden />
              Pinned
            </span>
          )}
        </p>

        {/* Action row — visible when selected */}
        {isSelected && (
          <div className="flex gap-1.5 mt-2" role="group" aria-label="Version actions">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs gap-1"
              onClick={(e) => {
                e.stopPropagation();
                onDiff();
              }}
            >
              <GitCompare className="w-3 h-3" aria-hidden />
              Compare
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs gap-1"
              onClick={(e) => {
                e.stopPropagation();
                onRestore();
              }}
            >
              <Undo2 className="w-3 h-3" aria-hidden />
              Restore
            </Button>
          </div>
        )}
      </div>
    </li>
  );
});

/** Full version timeline panel */
export const VersionTimeline = observer(function VersionTimeline({
  workspaceId,
  noteId,
  store,
  currentVersionNumber: _currentVersionNumber,
  onUndoAI,
}: VersionTimelineProps) {
  const qc = useQueryClient();
  const loadMoreRef = useRef<HTMLDivElement>(null);

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, error } =
    useInfiniteQuery({
      queryKey: ['versions', workspaceId, noteId],
      queryFn: ({ pageParam = 0 }) =>
        versionApi.list(workspaceId, noteId, { limit: 20, offset: pageParam as number }),
      getNextPageParam: (last, pages) => {
        const loaded = pages.reduce((sum, p) => sum + p.versions.length, 0);
        return loaded < last.total ? loaded : undefined;
      },
      initialPageParam: 0,
    });

  const pinMutation = useMutation({
    mutationFn: ({ versionId, pinned }: { versionId: string; pinned: boolean }) =>
      versionApi.pin(workspaceId, noteId, versionId, pinned),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['versions', workspaceId, noteId] }),
  });

  const saveMutation = useMutation({
    mutationFn: (label?: string) => versionApi.create(workspaceId, noteId, label),
    onMutate: () => store.setSaving(true),
    onSettled: () => store.setSaving(false),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['versions', workspaceId, noteId] }),
  });

  const versions = data?.pages.flatMap((p) => p.versions) ?? [];

  // Group by date
  const groups = versions.reduce<Map<string, NoteVersionResponse[]>>((acc, v) => {
    const key = getDateGroup(v.createdAt);
    const existing = acc.get(key);
    if (existing) {
      existing.push(v);
    } else {
      acc.set(key, [v]);
    }
    return acc;
  }, new Map());

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget;
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      if (nearBottom && hasNextPage && !isFetchingNextPage) {
        void fetchNextPage();
      }
    },
    [fetchNextPage, hasNextPage, isFetchingNextPage]
  );

  // Check if there's any ai_after version (for undo-ai fast path)
  const hasAIAfterVersion = versions.some((v) => v.trigger === 'ai_after');

  return (
    <div className="flex flex-col h-full">
      {/* Save Version button */}
      <div className="px-3 py-2 border-b border-border">
        <Button
          variant="outline"
          size="sm"
          className="w-full gap-2"
          aria-label="Save manual version snapshot"
          disabled={store.isSaving}
          onClick={() => saveMutation.mutate(undefined)}
        >
          <BookmarkPlus className="w-3.5 h-3.5" aria-hidden />
          {store.isSaving ? 'Saving…' : 'Save Version'}
        </Button>

        {/* Undo AI fast path — GAP-04 */}
        {hasAIAfterVersion && onUndoAI && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-1.5 gap-2 text-ai hover:text-ai"
            disabled={store.isUndoingAI}
            onClick={onUndoAI}
          >
            <Undo2 className="w-3.5 h-3.5" aria-hidden />
            {store.isUndoingAI ? 'Undoing…' : 'Undo AI Changes'}
          </Button>
        )}
      </div>

      {/* Timeline list */}
      <div
        className="flex-1 overflow-y-auto px-2 py-2"
        onScroll={handleScroll}
        aria-label="Version history"
      >
        {isLoading && (
          <div className="space-y-3 px-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 rounded-lg" />
            ))}
          </div>
        )}

        {error && (
          <p className="text-xs text-destructive px-3 py-2">
            Failed to load versions. Please try again.
          </p>
        )}

        {!isLoading && versions.length === 0 && (
          <p className="text-xs text-muted-foreground px-3 py-2 text-center">
            No versions yet. Save a version to start tracking history.
          </p>
        )}

        <ul role="list" aria-label="Version history entries" className="space-y-0.5">
          {Array.from(groups.entries()).map(([dateLabel, groupVersions]) => (
            <li key={dateLabel}>
              <div
                role="heading"
                aria-level={3}
                className="text-xs uppercase tracking-wider text-muted-foreground mt-4 mb-2 px-3 first:mt-2"
              >
                {dateLabel}
              </div>
              <ul role="list">
                {groupVersions.map((v) => (
                  <VersionEntry
                    key={v.id}
                    version={v}
                    isSelected={store.selectedVersionId === v.id}
                    onSelect={() => store.selectVersion(v.id)}
                    onDiff={() => {
                      // Diff against current (newest) version
                      const newest = versions[0];
                      if (newest && newest.id !== v.id) {
                        store.openDiff(v.id, newest.id);
                      }
                    }}
                    onRestore={() => store.openRestore(v.id)}
                    onPin={(pinned) => pinMutation.mutate({ versionId: v.id, pinned })}
                    isPinning={
                      pinMutation.isPending &&
                      (pinMutation.variables as { versionId: string }).versionId === v.id
                    }
                  />
                ))}
              </ul>
            </li>
          ))}
        </ul>

        {isFetchingNextPage && (
          <div className="py-2 text-center">
            <Skeleton className="h-8 mx-3 rounded-lg" />
          </div>
        )}

        {hasNextPage && !isFetchingNextPage && (
          <div ref={loadMoreRef} className="py-2 text-center">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              onClick={() => void fetchNextPage()}
            >
              Load more…
            </Button>
          </div>
        )}
      </div>
    </div>
  );
});
