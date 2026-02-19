'use client';

/**
 * VersionPanel — content router for note version history sidebar.
 *
 * Routes between three views based on VersionStore.view:
 *   - timeline: scrollable list of versions (VersionTimeline)
 *   - diff:     side-by-side diff of two versions (VersionDiffViewer)
 *   - restore:  restore confirmation step (VersionRestoreConfirm)
 *
 * Designed to be mounted inside SidebarPanel (from Feature 016 infrastructure)
 * as the content for activePanel="versions".
 *
 * State lives in VersionStore (MobX). Version data lives in TanStack Query.
 *
 * T-216 through T-220: wires all sub-components + undo-AI fast path (GAP-04).
 */
import { useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { versionApi } from '../services/versionApi';
import { VersionStore } from '../stores/VersionStore';
import { VersionTimeline } from './VersionTimeline';
import { VersionDiffViewer } from './VersionDiffViewer';
import { VersionRestoreConfirm } from './VersionRestoreConfirm';

export interface VersionPanelProps {
  workspaceId: string;
  noteId: string;
  store: VersionStore;
  currentVersionNumber?: number;
  /** Called after restore so the editor can reload content */
  onRestored?: (newVersionId: string) => void;
}

export const VersionPanel = observer(function VersionPanel({
  workspaceId,
  noteId,
  store,
  currentVersionNumber,
  onRestored,
}: VersionPanelProps) {
  const qc = useQueryClient();

  // Undo-AI fast path (GAP-04)
  const undoAIMutation = useMutation({
    mutationFn: () => versionApi.undoAI(workspaceId, noteId, currentVersionNumber ?? 1),
    onMutate: () => store.setUndoingAI(true),
    onSettled: () => store.setUndoingAI(false),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: ['versions', workspaceId, noteId] });
      onRestored?.(result.newVersion.id);
    },
  });

  const handleUndoAI = useCallback(() => {
    undoAIMutation.mutate();
  }, [undoAIMutation]);

  const handleRestored = useCallback(
    (newVersionId: string) => {
      onRestored?.(newVersionId);
      store.close();
    },
    [onRestored, store]
  );

  // Fetch version details needed for diff/restore views
  const diffPair = store.diffVersionIds;
  const restoreVersionId = store.pendingRestoreVersionId;

  const { data: diffV1 } = useQuery({
    queryKey: ['version', workspaceId, noteId, diffPair?.[0]],
    queryFn: () => versionApi.get(workspaceId, noteId, diffPair![0]),
    enabled: diffPair !== null,
  });

  const { data: diffV2 } = useQuery({
    queryKey: ['version', workspaceId, noteId, diffPair?.[1]],
    queryFn: () => versionApi.get(workspaceId, noteId, diffPair![1]),
    enabled: diffPair !== null,
  });

  const { data: restoreVersion } = useQuery({
    queryKey: ['version', workspaceId, noteId, restoreVersionId],
    queryFn: () => versionApi.get(workspaceId, noteId, restoreVersionId!),
    enabled: restoreVersionId !== null,
  });

  // Timeline view
  if (store.view === 'timeline') {
    return (
      <VersionTimeline
        workspaceId={workspaceId}
        noteId={noteId}
        store={store}
        currentVersionNumber={currentVersionNumber}
        onUndoAI={handleUndoAI}
      />
    );
  }

  // Diff view — wait for both versions to load
  if (store.view === 'diff') {
    if (!diffV1 || !diffV2) {
      return (
        <div className="flex items-center justify-center h-full" role="status" aria-live="polite">
          <p className="text-xs text-muted-foreground">Loading versions…</p>
        </div>
      );
    }
    return (
      <VersionDiffViewer
        workspaceId={workspaceId}
        noteId={noteId}
        store={store}
        v1={diffV1}
        v2={diffV2}
        currentVersionNumber={currentVersionNumber}
        onRestore={(versionId) => store.openRestore(versionId)}
        onBack={() => store.closeDiff()}
      />
    );
  }

  // Restore confirm view — wait for version to load
  if (store.view === 'restore') {
    if (!restoreVersion || currentVersionNumber === undefined) {
      return (
        <div className="flex items-center justify-center h-full" role="status" aria-live="polite">
          <p className="text-xs text-muted-foreground">Loading version…</p>
        </div>
      );
    }
    return (
      <VersionRestoreConfirm
        workspaceId={workspaceId}
        noteId={noteId}
        store={store}
        version={restoreVersion}
        currentVersionNumber={currentVersionNumber}
        onRestored={handleRestored}
        onCancel={() => store.cancelRestore()}
      />
    );
  }

  return null;
});
