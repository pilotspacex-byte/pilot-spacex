'use client';

/**
 * VersionRestoreConfirm — confirmation step before restoring a version.
 *
 * Shows: version info, CRDT-safe warning, conflict state (409),
 * and Restore / Cancel actions.
 *
 * T-218: Restore confirmation dialog
 */
import { observer } from 'mobx-react-lite';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Undo2, AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { versionApi, NoteVersionResponse } from '../services/versionApi';
import { VersionStore } from '../stores/VersionStore';

interface VersionRestoreConfirmProps {
  workspaceId: string;
  noteId: string;
  store: VersionStore;
  version: NoteVersionResponse;
  currentVersionNumber: number;
  /** Called after a successful restore so the parent can apply the new content */
  onRestored: (newVersionId: string) => void;
  /** Called when user cancels */
  onCancel: () => void;
}

export const VersionRestoreConfirm = observer(function VersionRestoreConfirm({
  workspaceId,
  noteId,
  store,
  version,
  currentVersionNumber,
  onRestored,
  onCancel,
}: VersionRestoreConfirmProps) {
  const qc = useQueryClient();

  const restoreMutation = useMutation({
    mutationFn: () => versionApi.restore(workspaceId, noteId, version.id, currentVersionNumber),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: ['versions', workspaceId, noteId] });
      onRestored(result.newVersion.id);
    },
    onError: (
      err: Error & { status?: number; body?: { detail?: { currentVersionNumber?: number } } }
    ) => {
      if (err.status === 409) {
        const serverVersionNumber =
          err.body?.detail?.currentVersionNumber ?? currentVersionNumber + 1;
        store.setConflict(serverVersionNumber);
      }
    },
  });

  const isConflict = store.conflictVersionNumber !== null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border shrink-0">
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 gap-1 text-xs"
          onClick={onCancel}
          aria-label="Back to timeline"
        >
          <ArrowLeft className="w-3 h-3" aria-hidden />
          Back
        </Button>
        <span className="text-sm font-medium flex-1 truncate">Restore version</span>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        {/* Version summary card */}
        <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-1">
          <p className="text-sm font-medium">
            v{version.versionNumber} — {version.trigger.replace('_', ' ')}
          </p>
          {version.label && (
            <p className="text-xs text-muted-foreground truncate">&ldquo;{version.label}&rdquo;</p>
          )}
          <p className="text-xs text-muted-foreground tabular-nums">
            {formatDistanceToNow(new Date(version.createdAt), { addSuffix: true })}
          </p>
        </div>

        {/* CRDT safety note */}
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-3 flex gap-2">
          <AlertTriangle
            className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5"
            aria-hidden
          />
          <div className="space-y-1">
            <p className="text-xs font-medium text-amber-800 dark:text-amber-300">
              Restore creates a new version
            </p>
            <p className="text-xs text-amber-700 dark:text-amber-400">
              The current note content will be saved as a new snapshot before restoring. You can
              always return to it from the history.
            </p>
          </div>
        </div>

        {/* 409 conflict state */}
        {isConflict && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 space-y-2">
            <div className="flex gap-2">
              <AlertTriangle className="w-4 h-4 text-destructive shrink-0 mt-0.5" aria-hidden />
              <div className="space-y-1">
                <p className="text-xs font-medium text-destructive">Version conflict detected</p>
                <p className="text-xs text-muted-foreground">
                  The note has been updated (now at v{store.conflictVersionNumber}) while you were
                  reviewing. Reload to get the latest version, then try restoring again.
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full h-7 text-xs gap-1.5"
              onClick={() => {
                void qc.invalidateQueries({ queryKey: ['note', workspaceId, noteId] });
                void qc.invalidateQueries({ queryKey: ['versions', workspaceId, noteId] });
              }}
            >
              <RefreshCw className="w-3 h-3" aria-hidden />
              Reload page
            </Button>
          </div>
        )}

        {/* Mutation error (non-conflict) */}
        {restoreMutation.isError && !isConflict && (
          <p className="text-xs text-destructive">Restore failed. Please try again.</p>
        )}
      </div>

      {/* Footer actions */}
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-3 border-t border-border shrink-0',
          isConflict && 'opacity-50 pointer-events-none'
        )}
      >
        <Button
          variant="outline"
          size="sm"
          className="flex-1 h-8 text-xs"
          onClick={onCancel}
          disabled={restoreMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          variant="default"
          size="sm"
          className="flex-1 h-8 text-xs gap-1.5"
          disabled={restoreMutation.isPending || isConflict}
          onClick={() => restoreMutation.mutate()}
          aria-label={`Restore note to version ${version.versionNumber}`}
        >
          <Undo2 className="w-3 h-3" aria-hidden />
          {restoreMutation.isPending ? 'Restoring…' : 'Restore'}
        </Button>
      </div>
    </div>
  );
});
