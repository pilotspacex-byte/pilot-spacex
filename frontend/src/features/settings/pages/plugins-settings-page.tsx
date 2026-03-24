/**
 * PluginsSettingsPage - Workspace editor plugin management.
 *
 * Phase 45-04: Admin gallery for uploading, enabling/disabling, and deleting
 * editor plugins. Members see a read-only view of installed plugins.
 * Plain component (NOT observer) -- no MobX observables consumed directly.
 */

'use client';

import * as React from 'react';
import { useParams } from 'next/navigation';
import { AlertCircle, Lock, Puzzle, Trash2, Upload } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { useWorkspaceStore } from '@/stores/RootStore';
import { ConfirmActionDialog } from '../components/confirm-action-dialog';
import {
  usePlugins,
  useUploadPlugin,
  useTogglePlugin,
  useDeletePlugin,
} from '@/features/plugins/hooks/usePlugins';
import type { WorkspacePlugin } from '@/features/plugins/types';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-40" />
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-xl border bg-card overflow-hidden">
            <div className="p-4 space-y-2">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-8 w-full mt-2" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function GuestView() {
  return (
    <div className="py-8">
      <Alert role="alert">
        <Lock className="h-4 w-4" />
        <AlertDescription>
          Plugin management requires Member or higher access. Contact a workspace admin for
          permission.
        </AlertDescription>
      </Alert>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center rounded-2xl bg-gradient-to-b from-primary/[0.04] to-ai/[0.04] border border-border/40 p-10 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20 shadow-sm">
        <Puzzle className="h-6 w-6 text-primary" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-foreground font-display">
        No plugins installed
      </h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground leading-relaxed">
        Upload a .zip file containing a plugin manifest and JavaScript bundle to get started.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Plugin card
// ---------------------------------------------------------------------------

interface PluginCardProps {
  plugin: WorkspacePlugin;
  isAdmin: boolean;
  onToggle: (plugin: WorkspacePlugin) => void;
  onDelete: (plugin: WorkspacePlugin) => void;
}

function PluginCard({ plugin, isAdmin, onToggle, onDelete }: PluginCardProps) {
  const isEnabled = plugin.status === 'enabled';

  return (
    <div className="flex flex-col rounded-xl border bg-card p-4 shadow-warm-sm transition-shadow hover:shadow-warm-md">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-foreground">{plugin.displayName}</h3>
            <Badge variant={isEnabled ? 'default' : 'secondary'} className="shrink-0 text-[10px]">
              {isEnabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">
            v{plugin.version} by {plugin.author}
          </p>
        </div>
      </div>

      {/* Description */}
      <p className="mt-2 line-clamp-2 text-xs text-muted-foreground leading-relaxed">
        {plugin.description}
      </p>

      {/* Admin controls */}
      {isAdmin && (
        <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-3">
          <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
            <Switch
              checked={isEnabled}
              onCheckedChange={() => onToggle(plugin)}
              aria-label={`${isEnabled ? 'Disable' : 'Enable'} ${plugin.displayName}`}
            />
            {isEnabled ? 'Enabled' : 'Disabled'}
          </label>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-destructive"
            onClick={() => onDelete(plugin)}
            aria-label={`Delete ${plugin.displayName}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function PluginsSettingsPage() {
  const workspaceStore = useWorkspaceStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;
  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  const isAdmin = workspaceStore.isAdmin;
  const isGuest = workspaceStore.currentUserRole === 'guest';

  // Data hooks
  const { data: plugins, isLoading, isError, error } = usePlugins(workspaceId);
  const uploadPlugin = useUploadPlugin(workspaceId);
  const togglePlugin = useTogglePlugin(workspaceId);
  const deletePluginMutation = useDeletePlugin(workspaceId);

  // File input ref
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Delete confirmation state
  const [pluginToDelete, setPluginToDelete] = React.useState<WorkspacePlugin | null>(null);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadPlugin.mutate(file);
      // Reset input so re-uploading the same file triggers onChange
      e.target.value = '';
    }
  };

  const handleToggle = (plugin: WorkspacePlugin) => {
    const newStatus = plugin.status === 'enabled' ? 'disabled' : 'enabled';
    togglePlugin.mutate({ pluginId: plugin.id, status: newStatus });
  };

  const handleDeleteConfirm = () => {
    if (!pluginToDelete) return;
    deletePluginMutation.mutate(pluginToDelete.id, {
      onSettled: () => setPluginToDelete(null),
    });
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (isGuest) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-6 font-display">Plugins</h1>
        <GuestView />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="px-4 py-4 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load plugins: {error?.message ?? 'Unknown error'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const pluginCount = plugins?.length ?? 0;

  return (
    <div className="px-4 py-4 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight font-display">Plugins</h1>
          {pluginCount > 0 && (
            <p className="mt-1 text-sm text-muted-foreground">
              {pluginCount} plugin{pluginCount !== 1 ? 's' : ''} installed
            </p>
          )}
        </div>
        {isAdmin && (
          <>
            <Button size="sm" onClick={handleUploadClick} disabled={uploadPlugin.isPending}>
              <Upload className="mr-1.5 h-4 w-4" />
              {uploadPlugin.isPending ? 'Uploading...' : 'Upload Plugin'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={handleFileChange}
              aria-label="Upload plugin zip file"
            />
          </>
        )}
      </div>

      {/* Plugin list or empty state */}
      {pluginCount > 0 ? (
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {plugins?.map((plugin, index) => (
            <div
              key={plugin.id}
              className="animate-fade-up"
              style={{ animationDelay: `${index * 60}ms` }}
            >
              <PluginCard
                plugin={plugin}
                isAdmin={isAdmin}
                onToggle={handleToggle}
                onDelete={setPluginToDelete}
              />
            </div>
          ))}
        </div>
      ) : (
        <EmptyState />
      )}

      {/* Delete confirmation */}
      {pluginToDelete && (
        <ConfirmActionDialog
          open={!!pluginToDelete}
          onCancel={() => setPluginToDelete(null)}
          onConfirm={handleDeleteConfirm}
          title={`Delete "${pluginToDelete.displayName}"?`}
          description="This will permanently remove this plugin and its bundle from the workspace. Any blocks created by this plugin will lose their custom rendering."
          confirmLabel="Delete Plugin"
          variant="destructive"
        />
      )}
    </div>
  );
}
