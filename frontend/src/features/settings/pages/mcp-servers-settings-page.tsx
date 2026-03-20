/**
 * MCPServersSettingsPage - Manage remote MCP servers for workspace.
 *
 * Phase 14 Plan 04: Observer component that loads registered MCP servers,
 * provides registration form, and renders server cards with status/delete actions.
 *
 * Phase 35 Plan 02: Added "Catalog" tab for browsable catalog with one-click install.
 *
 * Pattern: mirrors ai-settings-page.tsx (useStore() + observer + useParams).
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams, useSearchParams } from 'next/navigation';
import { AlertCircle, ServerCog } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MCPServerCard } from '../components/mcp-server-card';
import { MCPServerForm } from '../components/mcp-server-form';
import { MCPCatalogTabContent } from '../components/mcp-catalog-tab-content';
import { useStore } from '@/stores';
import { toast } from 'sonner';
import type { McpCatalogEntry } from '@/services/api/mcp-catalog';

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-80" />
      <Skeleton className="h-[120px] w-full" />
      <Skeleton className="h-[80px] w-full" />
      <Skeleton className="h-[80px] w-full" />
    </div>
  );
}

export const MCPServersSettingsPage = observer(function MCPServersSettingsPage() {
  const { ai, workspaceStore } = useStore();
  const mcpStore = ai.mcpServers;
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id ?? workspaceSlug;

  const searchParams = useSearchParams();
  const [deletingServerId, setDeletingServerId] = React.useState<string | null>(null);
  const [activeTab, setActiveTab] = React.useState<string>('registered');

  React.useEffect(() => {
    if (workspaceId) {
      mcpStore.loadServers(workspaceId);
    }
  }, [workspaceId, mcpStore]);

  // Handle OAuth callback status from redirect
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

  const handleRegister = async (data: Parameters<typeof mcpStore.registerServer>[1]) => {
    await mcpStore.registerServer(workspaceId, data);
  };

  const handleDelete = async (serverId: string) => {
    setDeletingServerId(serverId);
    try {
      await mcpStore.removeServer(workspaceId, serverId);
      toast.success('MCP server removed');
    } catch {
      toast.error('Failed to remove server');
    } finally {
      setDeletingServerId(null);
    }
  };

  const handleRefreshStatus = async (serverId: string) => {
    await mcpStore.refreshStatus(workspaceId, serverId);
  };

  const handleAuthorize = async (serverId: string) => {
    try {
      const authUrl = await mcpStore.getOAuthUrl(workspaceId, serverId);
      window.location.href = authUrl;
    } catch {
      toast.error('Failed to start OAuth authorization');
    }
  };

  const handleUpdateApprovalMode = async (
    serverId: string,
    mode: 'auto_approve' | 'require_approval'
  ) => {
    try {
      await mcpStore.updateApprovalMode(workspaceId, serverId, mode);
    } catch {
      toast.error('Failed to update approval mode');
    }
  };

  const handleInstallFromCatalog = async (entry: McpCatalogEntry) => {
    try {
      if (entry.transport_type === 'stdio') {
        // url_template stores "command|arg1|arg2|..." for stdio entries
        const parts = entry.url_template.split('|');
        const [command, ...args] = parts;
        await mcpStore.registerServer(workspaceId, {
          display_name: entry.name,
          url: '',
          auth_type: entry.auth_type,
          transport_type: 'stdio',
          stdio_command: command,
          stdio_args: args,
          catalog_entry_id: entry.id,
          installed_catalog_version: entry.catalog_version,
        });
      } else {
        await mcpStore.registerServer(workspaceId, {
          display_name: entry.name,
          url: entry.url_template,
          auth_type: entry.auth_type,
          transport_type: entry.transport_type,
          oauth_auth_url: entry.oauth_auth_url ?? undefined,
          oauth_token_url: entry.oauth_token_url ?? undefined,
          oauth_scopes: entry.oauth_scopes ?? undefined,
          catalog_entry_id: entry.id,
          installed_catalog_version: entry.catalog_version,
        });
      }
      toast.success('Server installed — add your auth token to activate it.');
      setActiveTab('registered');
    } catch {
      toast.error('Failed to install server from catalog');
    }
  };

  if (mcpStore.isLoading) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (mcpStore.error && mcpStore.servers.length === 0) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load MCP servers</AlertTitle>
          <AlertDescription>{mcpStore.error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ServerCog className="h-6 w-6" />
            <h1 className="text-2xl font-semibold tracking-tight">Remote MCP Servers</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Register remote MCP servers to extend the AI agent with custom tools. Registered servers
            are automatically loaded on every chat request.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="registered">Registered Servers</TabsTrigger>
            <TabsTrigger value="catalog">Catalog</TabsTrigger>
          </TabsList>

          {/* Registered Servers tab */}
          <TabsContent value="registered" className="space-y-6 mt-6">
            {/* Registration Form */}
            <MCPServerForm
              workspaceId={workspaceId}
              onRegister={handleRegister}
              onSuccess={() => mcpStore.loadServers(workspaceId)}
            />

            {/* Server List */}
            {mcpStore.servers.length > 0 && (
              <>
                <Separator />
                <div className="space-y-3">
                  <h2 className="text-lg font-semibold">Registered Servers</h2>
                  <div className="space-y-3">
                    {mcpStore.servers.map((server) => (
                      <MCPServerCard
                        key={server.id}
                        server={server}
                        onDelete={handleDelete}
                        onRefreshStatus={handleRefreshStatus}
                        onAuthorize={handleAuthorize}
                        onUpdateApprovalMode={handleUpdateApprovalMode}
                        isDeleting={deletingServerId === server.id}
                      />
                    ))}
                  </div>
                </div>
              </>
            )}

            {mcpStore.servers.length === 0 && !mcpStore.isLoading && (
              <div className="rounded-lg border border-dashed border-border p-8 text-center">
                <ServerCog className="mx-auto h-8 w-8 text-muted-foreground/50" />
                <p className="mt-2 text-sm text-muted-foreground">No MCP servers registered yet.</p>
                <p className="text-xs text-muted-foreground">
                  Use the form above to add your first remote MCP server, or browse the Catalog tab.
                </p>
              </div>
            )}

            {/* Info Alert */}
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>About Remote MCP Servers</AlertTitle>
              <AlertDescription>
                MCP (Model Context Protocol) servers expose custom tools to the AI agent. Bearer
                tokens are encrypted server-side. OAuth2 servers require authorization before tools
                become available.
              </AlertDescription>
            </Alert>
          </TabsContent>

          {/* Catalog tab */}
          <TabsContent value="catalog" className="mt-6">
            <MCPCatalogTabContent
              workspaceId={workspaceId}
              installedServers={mcpStore.servers}
              onInstall={handleInstallFromCatalog}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
});
