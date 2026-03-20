/**
 * MCPCatalogTabContent - Browsable MCP catalog with filter chips.
 *
 * Phase 35 Plan 02: Observer component that loads catalog entries,
 * provides filter chips (All/HTTP/SSE), and renders MCPCatalogCard grid.
 *
 * Pattern: mirrors existing observer settings tab components.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { MCPCatalogCard } from './mcp-catalog-card';
import { hasUpdate, isInstalled } from '@/stores/ai/MCPCatalogStore';
import { useStore } from '@/stores';
import type { McpCatalogEntry } from '@/services/api/mcp-catalog';
import type { MCPServer } from '@/stores/ai/MCPServersStore';

type TransportFilter = 'all' | 'http' | 'sse' | 'stdio';

interface MCPCatalogTabContentProps {
  workspaceId: string;
  installedServers: MCPServer[];
  onInstall: (entry: McpCatalogEntry) => void;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-[88px] w-full" />
      <Skeleton className="h-[88px] w-full" />
      <Skeleton className="h-[88px] w-full" />
    </div>
  );
}

const FILTER_CHIPS: { label: string; value: TransportFilter }[] = [
  { label: 'All', value: 'all' },
  { label: 'HTTP', value: 'http' },
  { label: 'SSE', value: 'sse' },
  { label: 'Stdio', value: 'stdio' },
];

export const MCPCatalogTabContent = observer(function MCPCatalogTabContent({
  workspaceId: _workspaceId,
  installedServers,
  onInstall,
}: MCPCatalogTabContentProps) {
  const { ai } = useStore();
  const catalogStore = ai.mcpCatalog;
  const [activeFilter, setActiveFilter] = React.useState<TransportFilter>('all');

  React.useEffect(() => {
    void catalogStore.loadCatalog();
  }, [catalogStore]);

  const filteredEntries = React.useMemo(() => {
    if (activeFilter === 'all') return catalogStore.entries;
    return catalogStore.entries.filter((e) => e.transport_type === activeFilter);
  }, [catalogStore.entries, activeFilter]);

  if (catalogStore.isLoading) {
    return <LoadingSkeleton />;
  }

  if (catalogStore.error && catalogStore.entries.length === 0) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Failed to load catalog</AlertTitle>
        <AlertDescription>{catalogStore.error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex items-center gap-2">
        {FILTER_CHIPS.map(({ label, value }) => (
          <button
            key={value}
            type="button"
            onClick={() => setActiveFilter(value)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              activeFilter === value
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Catalog grid */}
      {filteredEntries.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <p className="text-sm text-muted-foreground">
            {catalogStore.entries.length === 0
              ? 'No catalog entries available.'
              : 'No entries match the selected filter.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEntries.map((entry) => (
            <MCPCatalogCard
              key={entry.id}
              entry={entry}
              isInstalled={isInstalled(entry, installedServers)}
              hasUpdate={
                isInstalled(entry, installedServers)
                  ? installedServers.some(
                      (s) => s.catalog_entry_id === entry.id && hasUpdate(entry, s)
                    )
                  : false
              }
              onInstall={onInstall}
            />
          ))}
        </div>
      )}
    </div>
  );
});
