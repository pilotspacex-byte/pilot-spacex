/**
 * MCPServersSettingsPage - Full-featured MCP server management page.
 *
 * Phase 25: Observer page with data table, filter bar, New/Edit dialog,
 * bulk import, connection testing, enable/disable, delete, and 30s polling.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useSearchParams } from 'next/navigation';
import { AlertCircle, RefreshCw, Plus, ServerCog } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { MCPServersTable } from '../components/mcp-servers-table';
import { MCPServerDialog } from '../components/mcp-server-dialog';
import { useStore } from '@/stores';
import { toast } from 'sonner';
import type {
  MCPServer,
  MCPServerRegisterRequest,
  MCPServerUpdateRequest,
} from '@/stores/ai/MCPServersStore';

// ── Loading skeleton ────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-32" />
        </div>
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-9 w-[140px]" />
        <Skeleton className="h-9 w-[160px]" />
        <Skeleton className="h-9 flex-1" />
      </div>
      <Skeleton className="h-[300px] w-full rounded-md" />
    </div>
  );
}

// ── Empty state ─────────────────────────────────────────────

function EmptyState({ onAddClick }: { onAddClick: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-border p-12 text-center">
      <ServerCog className="mx-auto h-10 w-10 text-muted-foreground/50" />
      <h3 className="mt-4 text-sm font-medium">No MCP servers configured yet</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Click New MCP to add your first server.
      </p>
      <Button className="mt-4 gap-1.5" onClick={onAddClick}>
        <Plus className="h-4 w-4" />
        New MCP
      </Button>
    </div>
  );
}

// ── Page component ──────────────────────────────────────────

export const MCPServersSettingsPage = observer(function MCPServersSettingsPage() {
  const { ai, workspaceStore } = useStore();
  const mcpStore = ai.mcpServers;
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id ?? workspaceSlug;

  const searchParams = useSearchParams();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editServer, setEditServer] = React.useState<MCPServer | undefined>(undefined);
  const [deletingServerId, setDeletingServerId] = React.useState<string | null>(null);
  const [testingServerId, setTestingServerId] = React.useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  // ── Load on mount + 30s polling ────────────────────────

  React.useEffect(() => {
    if (workspaceId) {
      mcpStore.loadServers(workspaceId);
    }
  }, [workspaceId, mcpStore]);

  React.useEffect(() => {
    if (!workspaceId) return;
    const interval = setInterval(() => {
      mcpStore.loadServers(workspaceId);
    }, 30_000);
    return () => clearInterval(interval);
  }, [workspaceId, mcpStore]);

  // ── Handle OAuth callback status from redirect ─────────

  React.useEffect(() => {
    const status = searchParams.get('status');
    const reason = searchParams.get('reason');
    if (status === 'connected') {
      toast.success('MCP server authorized successfully');
      mcpStore.loadServers(workspaceId);
    } else if (status === 'error') {
      toast.error(`OAuth authorization failed: ${reason || 'Unknown error'}`);
    }
  }, [searchParams, mcpStore, workspaceId]);

  // ── Handlers ──────────────────────────────────────────

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await mcpStore.loadServers(workspaceId);
    setIsRefreshing(false);
  };

  const openAddDialog = () => {
    setEditServer(undefined);
    setDialogOpen(true);
  };

  const openEditDialog = (server: MCPServer) => {
    setEditServer(server);
    setDialogOpen(true);
  };

  const handleSave = async (data: MCPServerRegisterRequest | MCPServerUpdateRequest) => {
    try {
      if (editServer) {
        await mcpStore.updateServer(workspaceId, editServer.id, data as MCPServerUpdateRequest);
        toast.success('Server updated');
      } else {
        await mcpStore.registerServer(workspaceId, data as MCPServerRegisterRequest);
        toast.success('Server added');
      }
      setDialogOpen(false);
      setEditServer(undefined);
    } catch {
      toast.error(editServer ? 'Failed to update server' : 'Failed to add server');
    }
  };

  const handleImport = async (jsonString: string) => {
    try {
      const result = await mcpStore.importServers(workspaceId, jsonString);
      const msgs: string[] = [];
      if (result.imported.length > 0) {
        msgs.push(`${result.imported.length} imported`);
      }
      if (result.skipped.length > 0) {
        msgs.push(`${result.skipped.length} skipped (name conflict)`);
      }
      if (result.errors.length > 0) {
        msgs.push(`${result.errors.length} errors`);
      }
      toast.success(`Import complete: ${msgs.join(', ')}`);
      if (result.errors.length === 0 && result.skipped.length === 0) {
        setDialogOpen(false);
      }
    } catch {
      toast.error('Failed to import servers');
    }
  };

  const handleTestConnection = async (serverId: string) => {
    setTestingServerId(serverId);
    try {
      const result = await mcpStore.testConnection(workspaceId, serverId);
      if (result.status === 'enabled') {
        toast.success(`Connection successful (${result.latency_ms}ms)`);
      } else {
        toast.error(`Connection ${result.status}: ${result.error_detail || 'Check server configuration'}`);
      }
      return result;
    } catch {
      toast.error('Connection test failed');
      throw new Error('Connection test failed');
    } finally {
      setTestingServerId(null);
    }
  };

  const handleToggleEnabled = async (serverId: string, enabled: boolean) => {
    try {
      if (enabled) {
        await mcpStore.enableServer(workspaceId, serverId);
        toast.success('Server enabled');
      } else {
        await mcpStore.disableServer(workspaceId, serverId);
        toast.success('Server disabled');
      }
    } catch {
      toast.error(`Failed to ${enabled ? 'enable' : 'disable'} server`);
    }
  };

  const handleDelete = async (serverId: string) => {
    setDeletingServerId(serverId);
    try {
      await mcpStore.removeServer(workspaceId, serverId);
      toast.success('Server removed');
    } catch {
      toast.error('Failed to remove server');
    } finally {
      setDeletingServerId(null);
    }
  };

  // ── Render ────────────────────────────────────────────

  if (mcpStore.isLoading && mcpStore.servers.length === 0 && !dialogOpen) {
    return (
      <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (mcpStore.error && mcpStore.servers.length === 0) {
    return (
      <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load MCP servers</AlertTitle>
          <AlertDescription>{mcpStore.error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="w-full px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <ServerCog className="h-6 w-6" />
              <h1 className="text-2xl font-semibold tracking-tight">MCP Servers</h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Manage MCP server connections for the AI agent. Supports Remote, NPX, and UVX servers.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="gap-1.5"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button size="sm" onClick={openAddDialog} className="gap-1.5">
              <Plus className="h-4 w-4" />
              New MCP
            </Button>
          </div>
        </div>

        {/* Content: table or empty state */}
        {mcpStore.servers.length === 0 && !mcpStore.isLoading ? (
          <EmptyState onAddClick={openAddDialog} />
        ) : (
          <MCPServersTable
            servers={mcpStore.filteredServers}
            totalCount={mcpStore.servers.length}
            filterType={mcpStore.filter.serverType}
            filterStatus={mcpStore.filter.status}
            filterSearch={mcpStore.filter.search}
            onFilterTypeChange={(type) => mcpStore.setFilter({ serverType: type })}
            onFilterStatusChange={(status) => mcpStore.setFilter({ status })}
            onFilterSearchChange={(search) => mcpStore.setFilter({ search })}
            onEdit={openEditDialog}
            onTestConnection={handleTestConnection}
            onToggleEnabled={handleToggleEnabled}
            onDelete={handleDelete}
            deletingServerId={deletingServerId}
            testingServerId={testingServerId}
          />
        )}

        {/* Dialog */}
        <MCPServerDialog
          open={dialogOpen}
          onOpenChange={(open) => {
            setDialogOpen(open);
            if (!open) setEditServer(undefined);
          }}
          initialData={editServer}
          onSave={handleSave}
          onImport={handleImport}
          onTestConnection={editServer ? handleTestConnection : undefined}
          isSaving={mcpStore.isSaving}
        />
      </div>
    </div>
  );
});
