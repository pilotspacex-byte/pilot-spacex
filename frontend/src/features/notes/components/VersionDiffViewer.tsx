'use client';

/**
 * VersionDiffViewer — block-level diff between two note versions.
 *
 * Added blocks: green bg, + prefix.
 * Removed blocks: red bg, - prefix.
 * Modified blocks: amber bg, inline text changes.
 * Unchanged: default bg, muted foreground.
 *
 * Shows AI digest strip at bottom (FR-040).
 * Full-screen modal mode available via expand button.
 *
 * T-217: Visual diff view
 * T-219: Version digest display
 */
import { useState } from 'react';
import { observer } from 'mobx-react-lite';
import { useQuery, useMutation } from '@tanstack/react-query';
import { X, Expand, Shrink, ArrowLeft, Undo2, Sparkles } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { versionApi, NoteVersionResponse, BlockDiffResponse } from '../services/versionApi';
import { VersionStore } from '../stores/VersionStore';

interface VersionDiffViewerProps {
  workspaceId: string;
  noteId: string;
  store: VersionStore;
  v1: NoteVersionResponse;
  v2: NoteVersionResponse;
  currentVersionNumber?: number;
  onRestore: (versionId: string) => void;
  onBack: () => void;
}

/** Extract a human-readable text preview from a TipTap block's content */
function blockText(content: Record<string, unknown> | null): string {
  if (!content) return '(empty)';
  const type = content.type as string | undefined;
  if (type === 'text') return (content.text as string | undefined) ?? '';
  const children = (content.content as Record<string, unknown>[] | undefined) ?? [];
  return children.map(blockText).join('').slice(0, 120) || `[${type ?? 'block'}]`;
}

/** One row in the diff display */
const DiffRow = observer(function DiffRow({
  block,
  side,
}: {
  block: BlockDiffResponse;
  side: 'old' | 'new';
}) {
  const isAdd = block.diffType === 'added';
  const isRemove = block.diffType === 'removed';
  const isModified = block.diffType === 'modified';
  const isUnchanged = block.diffType === 'unchanged';

  const content = side === 'old' ? block.oldContent : block.newContent;
  const isEmpty = content === null;

  const prefix = isAdd && side === 'new' ? '+' : isRemove && side === 'old' ? '-' : ' ';

  const rowClass = cn(
    'flex gap-2 px-3 py-1 text-sm font-mono leading-relaxed min-h-[28px]',
    isAdd && side === 'new' && 'bg-[#29A38618] text-foreground',
    isRemove && side === 'old' && 'bg-[#D9534F18] text-foreground',
    isModified && 'bg-[#D9853F18] text-foreground',
    isUnchanged && 'bg-background text-muted-foreground',
    isEmpty && 'opacity-30'
  );

  const prefixClass = cn(
    'w-4 shrink-0 select-none text-center',
    isAdd && side === 'new' && 'text-primary font-bold',
    isRemove && side === 'old' && 'text-destructive font-bold'
  );

  return (
    <div
      className={rowClass}
      aria-label={
        isAdd && side === 'new'
          ? 'Added line'
          : isRemove && side === 'old'
            ? 'Removed line'
            : isModified
              ? 'Modified line'
              : undefined
      }
    >
      <span className={prefixClass} aria-hidden>
        {prefix}
      </span>
      <span className="flex-1 break-words whitespace-pre-wrap min-w-0">
        {isEmpty ? '' : blockText(content)}
      </span>
    </div>
  );
});

/** The actual diff content; used in both inline panel and full-screen modal */
const DiffContent = observer(function DiffContent({
  workspaceId,
  noteId,
  store,
  v1,
  v2,
  currentVersionNumber,
  onRestore,
  onBack,
  isModal = false,
}: VersionDiffViewerProps & { isModal?: boolean }) {
  const [digestError, setDigestError] = useState(false);

  const {
    data: diff,
    isLoading: isDiffLoading,
    error: diffError,
  } = useQuery({
    queryKey: ['version-diff', workspaceId, noteId, v1.id, v2.id],
    queryFn: () => versionApi.diff(workspaceId, noteId, v1.id, v2.id),
  });

  const { data: digest, isLoading: isDigestLoading } = useQuery({
    queryKey: ['version-digest', workspaceId, noteId, v2.id],
    queryFn: () => versionApi.digest(workspaceId, noteId, v2.id),
    enabled: !digestError,
    retry: 1,
  });

  const retryDigestMutation = useMutation({
    mutationFn: () => versionApi.digest(workspaceId, noteId, v2.id),
    onError: () => setDigestError(true),
  });

  const blocks = diff?.blocks ?? [];

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header row */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 gap-1 text-xs"
          onClick={onBack}
          aria-label="Back to timeline"
        >
          <ArrowLeft className="w-3 h-3" aria-hidden />
          Back
        </Button>
        <span className="text-sm font-medium flex-1 truncate text-center">Compare versions</span>
      </div>

      {/* Version labels */}
      <div className="grid grid-cols-2 border-b border-border shrink-0">
        <div className="px-3 py-1.5 border-r border-border">
          <p className="text-xs font-medium text-muted-foreground truncate">
            v{v1.versionNumber} · {formatDistanceToNow(new Date(v1.createdAt), { addSuffix: true })}
          </p>
          <p className="text-xs text-muted-foreground capitalize">{v1.trigger.replace('_', ' ')}</p>
        </div>
        <div className="px-3 py-1.5">
          <p className="text-xs font-medium text-muted-foreground truncate">
            v{v2.versionNumber} · {formatDistanceToNow(new Date(v2.createdAt), { addSuffix: true })}
          </p>
          <p className="text-xs text-muted-foreground capitalize">{v2.trigger.replace('_', ' ')}</p>
        </div>
      </div>

      {/* Diff body */}
      <div
        className="flex-1 overflow-y-auto"
        role="region"
        aria-label="Version comparison"
        aria-live="off"
      >
        {isDiffLoading && (
          <div className="space-y-2 p-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-7 rounded" />
            ))}
          </div>
        )}

        {diffError && (
          <p className="text-xs text-destructive px-3 py-3">
            Failed to load diff. Please try again.
          </p>
        )}

        {!isDiffLoading && !diffError && blocks.length === 0 && (
          <p className="text-xs text-muted-foreground px-3 py-3 text-center">
            No differences found between these versions.
          </p>
        )}

        {!isDiffLoading && blocks.length > 0 && (
          <div className={cn('grid', isModal ? 'grid-cols-2' : 'grid-cols-1')}>
            {/* Left column (v1) — in modal: show old content; in panel: unified view, skip modified (shown below as new) */}
            <div className={cn(isModal && 'border-r border-border')}>
              {blocks.map((block) => {
                if (block.diffType === 'added') {
                  return (
                    <div
                      key={block.blockId}
                      className="min-h-[28px] bg-background/50"
                      aria-hidden
                    />
                  );
                }
                // In panel (unified) mode, skip modified blocks here — they are shown as new content below
                if (!isModal && block.diffType === 'modified') {
                  return null;
                }
                return <DiffRow key={block.blockId} block={block} side="old" />;
              })}
            </div>

            {/* Right column (v2) — always shown in side-by-side modal, stacked in panel */}
            {isModal && (
              <div>
                {blocks.map((block) =>
                  block.diffType !== 'removed' ? (
                    <DiffRow key={block.blockId} block={block} side="new" />
                  ) : (
                    <div
                      key={block.blockId}
                      className="min-h-[28px] bg-background/50"
                      aria-hidden
                    />
                  )
                )}
              </div>
            )}

            {/* In-panel unified view: show new content for non-removed blocks */}
            {!isModal &&
              blocks.map((block) =>
                block.diffType !== 'removed' && block.diffType !== 'unchanged' ? (
                  <DiffRow key={`${block.blockId}-new`} block={block} side="new" />
                ) : null
              )}
          </div>
        )}
      </div>

      {/* Stats bar */}
      {diff && (
        <div className="flex items-center gap-3 px-3 py-1.5 border-t border-border text-xs text-muted-foreground shrink-0">
          {diff.addedCount > 0 && <span className="text-primary">+{diff.addedCount} added</span>}
          {diff.removedCount > 0 && (
            <span className="text-destructive">−{diff.removedCount} removed</span>
          )}
          {diff.modifiedCount > 0 && (
            <span className="text-[#D9853F]">{diff.modifiedCount} modified</span>
          )}
          {!diff.hasChanges && <span>No changes</span>}
        </div>
      )}

      {/* AI Digest (FR-040, T-219) */}
      <div
        role="note"
        aria-label="AI change summary"
        className="shrink-0 border-t border-[var(--ai-border,theme(colors.border))] bg-[hsl(var(--ai)/0.05)] px-3 py-2"
      >
        <div className="flex items-start gap-2">
          <Sparkles className="w-3.5 h-3.5 text-ai mt-0.5 shrink-0" aria-hidden />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-ai mb-0.5">AI Digest</p>
            {isDigestLoading && (
              <div className="space-y-1">
                <Skeleton className="h-3 w-full rounded" />
                <Skeleton className="h-3 w-3/4 rounded" />
              </div>
            )}
            {!isDigestLoading && digest && (
              <p className="text-xs text-foreground leading-relaxed line-clamp-3">
                {digest.digest}
              </p>
            )}
            {!isDigestLoading && !digest && digestError && (
              <span className="text-xs text-muted-foreground">
                Summary unavailable.{' '}
                <button
                  className="underline hover:text-foreground"
                  onClick={() => {
                    setDigestError(false);
                    retryDigestMutation.mutate();
                  }}
                >
                  Retry
                </button>
              </span>
            )}
            {!isDigestLoading && !digest && !digestError && (
              <p className="text-xs text-muted-foreground italic">Generating summary…</p>
            )}
          </div>
        </div>
      </div>

      {/* Restore footer */}
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-t border-border shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs gap-1"
          onClick={() => onRestore(v1.id)}
          disabled={store.isUndoingAI}
        >
          <Undo2 className="w-3 h-3" aria-hidden />
          Restore v{v1.versionNumber}
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-7 px-2 text-xs gap-1"
          onClick={() => onRestore(v2.id)}
          disabled={currentVersionNumber !== undefined && v2.versionNumber === currentVersionNumber}
        >
          <Undo2 className="w-3 h-3" aria-hidden />
          Restore v{v2.versionNumber}
        </Button>
      </div>
    </div>
  );
});

/** Full version diff viewer — inline in sidebar with expand-to-modal support */
export const VersionDiffViewer = observer(function VersionDiffViewer(
  props: VersionDiffViewerProps
) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <div className="flex flex-col h-full relative">
        <DiffContent {...props} isModal={false} />

        {/* Expand button — top-right overlay */}
        <button
          type="button"
          aria-label="Expand to full screen"
          onClick={() => setIsModalOpen(true)}
          className={cn(
            'absolute top-2 right-2 p-1 rounded motion-safe:transition-opacity',
            'text-muted-foreground hover:text-foreground',
            'bg-background/80 hover:bg-muted'
          )}
        >
          <Expand className="w-3.5 h-3.5" aria-hidden />
        </button>
      </div>

      {/* Full-screen modal (spec: full viewport, frosted glass overlay) */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent
          className="max-w-5xl w-[95vw] h-[90vh] p-0 overflow-hidden flex flex-col"
          showCloseButton={false}
        >
          <DialogHeader className="sr-only">
            <DialogTitle>
              Version diff: v{props.v1.versionNumber} vs v{props.v2.versionNumber}
            </DialogTitle>
          </DialogHeader>

          {/* Close + shrink button */}
          <div className="absolute top-3 right-3 z-10 flex gap-1">
            <button
              type="button"
              aria-label="Collapse to sidebar"
              onClick={() => setIsModalOpen(false)}
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted motion-safe:transition-colors"
            >
              <Shrink className="w-3.5 h-3.5" aria-hidden />
            </button>
            <button
              type="button"
              aria-label="Close diff"
              onClick={() => setIsModalOpen(false)}
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted motion-safe:transition-colors"
            >
              <X className="w-3.5 h-3.5" aria-hidden />
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
            <DiffContent {...props} isModal={true} />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});
