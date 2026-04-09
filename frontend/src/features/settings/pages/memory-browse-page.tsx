/**
 * MemoryBrowsePage — Admin memory management page inside the settings modal.
 *
 * Phase 71: Paginated table with filters, search, detail drawer, bulk actions,
 * and stats header. NOT observer — uses TanStack Query, not MobX.
 */

'use client';

import * as React from 'react';
import { useStore } from '@/stores';
import { Brain } from 'lucide-react';
import { MemoryStatsHeader } from '../components/memory-stats-header';
import { MemorySearchBar } from '../components/memory-search-bar';
import { MemoryFacetBar } from '../components/memory-facet-bar';
import { MemoryBrowseTable } from '../components/memory-browse-table';
import { MemoryBulkActionBar } from '../components/memory-bulk-action-bar';
import { MemoryDetailDrawer } from '../components/memory-detail-drawer';
import { MemoryRecallPlayground } from '../components/memory-recall-playground';
import { MemoryProducerToggles } from '../components/memory-producer-toggles';
import { MemoryTelemetryCard } from '../components/memory-telemetry-card';
import { GdprForgetUserCard } from '../components/gdpr-forget-user-card';
import { useBulkMemoryAction, useMemoryList } from '../hooks/use-ai-memory';
import type { MemoryListParams } from '../hooks/use-ai-memory';

const DEFAULT_LIMIT = 50;

export function MemoryBrowsePage() {
  const { workspaceStore } = useStore();
  const workspaceId = workspaceStore.currentWorkspace?.id;

  const [offset, setOffset] = React.useState(0);
  const [filters, setFilters] = React.useState<
    Pick<MemoryListParams, 'type' | 'kind' | 'pinned'>
  >({});
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set());
  const [selectedMemoryId, setSelectedMemoryId] = React.useState<string | null>(null);

  const params: MemoryListParams = React.useMemo(
    () => ({
      offset,
      limit: DEFAULT_LIMIT,
      ...filters,
      ...(searchQuery ? { q: searchQuery } : {}),
    }),
    [offset, filters, searchQuery],
  );

  const { data: listData, isLoading } = useMemoryList(workspaceId, params);
  const resultCount = listData?.total ?? 0;

  const bulkAction = useBulkMemoryAction(workspaceId);

  const handleSearchChange = React.useCallback((q: string) => {
    setSearchQuery(q);
    setOffset(0);
    setSelectedIds(new Set());
  }, []);

  const handleFiltersChange = React.useCallback(
    (next: Pick<MemoryListParams, 'type' | 'kind' | 'pinned'>) => {
      setFilters(next);
      setOffset(0);
      setSelectedIds(new Set());
    },
    [],
  );

  const handlePageChange = React.useCallback((newOffset: number) => {
    setOffset(newOffset);
    setSelectedIds(new Set());
  }, []);

  const handleBulkPin = React.useCallback(() => {
    if (!selectedIds.size) return;
    bulkAction.mutate(
      { action: 'pin', memoryIds: Array.from(selectedIds) },
      { onSuccess: () => setSelectedIds(new Set()) },
    );
  }, [selectedIds, bulkAction]);

  const handleBulkForget = React.useCallback(() => {
    if (!selectedIds.size) return;
    bulkAction.mutate(
      { action: 'forget', memoryIds: Array.from(selectedIds) },
      { onSuccess: () => setSelectedIds(new Set()) },
    );
  }, [selectedIds, bulkAction]);

  if (!workspaceId) return null;

  return (
    <div className="max-w-5xl px-4 py-6 sm:px-6 lg:px-8 space-y-8">
      {/* Page Header */}
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
          <Brain className="h-5 w-5 text-muted-foreground" />
        </div>
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Memory</h1>
          <p className="text-sm text-muted-foreground max-w-lg">
            Memories power Pilot&apos;s ability to recall prior decisions, notes, and conversations.
            They&apos;re created automatically as your team works.
          </p>
        </div>
      </div>

      <MemoryStatsHeader workspaceId={workspaceId} />

      {/* Browse section */}
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1 min-w-0">
            <MemorySearchBar value={searchQuery} onChange={handleSearchChange} />
            {!isLoading && (
              <span id="memory-search-results" className="sr-only" aria-live="polite" aria-atomic="true">
                {resultCount} {resultCount === 1 ? 'result' : 'results'} found
              </span>
            )}
          </div>
          <MemoryFacetBar filters={filters} onChange={handleFiltersChange} />
        </div>

        <MemoryBrowseTable
          workspaceId={workspaceId}
          params={params}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onRowClick={setSelectedMemoryId}
          offset={offset}
          limit={DEFAULT_LIMIT}
          onPageChange={handlePageChange}
        />

        <div role="status" aria-live="polite">
          {selectedIds.size > 0 && (
            <MemoryBulkActionBar
              selectedCount={selectedIds.size}
              onPin={handleBulkPin}
              onForget={handleBulkForget}
              isPending={bulkAction.isPending}
            />
          )}
        </div>
      </div>

      {/* Recall playground */}
      <div className="space-y-4 border-t pt-8">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">Recall Playground</h2>
          <p className="text-sm text-muted-foreground max-w-lg">
            Test what Pilot would recall for a given query. Results show the same memories
            the AI sees when composing a response.
          </p>
        </div>
        <MemoryRecallPlayground workspaceId={workspaceId} />
      </div>

      {/* Producer controls */}
      <div className="space-y-4 border-t pt-8">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">Collection Settings</h2>
          <p className="text-sm text-muted-foreground max-w-lg">
            Control which interactions feed into long-term memory. Disabling a source stops
            new memories from being created but doesn&apos;t delete existing ones.
          </p>
        </div>
        <MemoryProducerToggles workspaceId={workspaceId} />
        <MemoryTelemetryCard workspaceId={workspaceId} />
      </div>

      {/* Danger zone */}
      <div className="space-y-4 border-t pt-8">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight text-destructive">Danger Zone</h2>
          <p className="text-sm text-muted-foreground max-w-lg">
            Irreversible actions for compliance and data management.
          </p>
        </div>
        <GdprForgetUserCard workspaceId={workspaceId} />
      </div>

      <MemoryDetailDrawer
        workspaceId={workspaceId}
        nodeId={selectedMemoryId}
        open={!!selectedMemoryId}
        onClose={() => setSelectedMemoryId(null)}
      />
    </div>
  );
}
