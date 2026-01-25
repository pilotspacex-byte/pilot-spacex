'use client';

/**
 * GitHubIntegration - GitHub connection and repository management.
 *
 * T188: Connect GitHub account, manage repositories, view webhook status.
 *
 * @example
 * ```tsx
 * <GitHubIntegration workspaceId={workspace.id} />
 * ```
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import {
  Github,
  RefreshCw,
  AlertCircle,
  Loader2,
  Settings,
  Unplug,
  Globe,
  Lock,
  Webhook,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { integrationsApi, type GitHubRepository } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

export interface GitHubIntegrationProps {
  /** Workspace ID */
  workspaceId: string;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Query Keys
// ============================================================================

const integrationKeys = {
  all: ['integrations'] as const,
  github: (workspaceId: string) => [...integrationKeys.all, 'github', workspaceId] as const,
  repositories: (workspaceId: string) =>
    [...integrationKeys.github(workspaceId), 'repositories'] as const,
};

// ============================================================================
// Repository Row Component
// ============================================================================

interface RepositoryRowProps {
  repository: GitHubRepository;
  onToggle: (enabled: boolean) => void;
  onSync: () => void;
  isToggling: boolean;
  isSyncing: boolean;
}

const RepositoryRow = React.memo(function RepositoryRow({
  repository,
  onToggle,
  onSync,
  isToggling,
  isSyncing,
}: RepositoryRowProps) {
  return (
    <div className="flex items-center justify-between py-3 px-4 rounded-lg border bg-card hover:bg-muted/30 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        {repository.private ? (
          <Lock className="size-4 text-muted-foreground shrink-0" />
        ) : (
          <Globe className="size-4 text-muted-foreground shrink-0" />
        )}

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-medium truncate">{repository.fullName}</p>
            {repository.webhookActive && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <Webhook className="size-3 text-green-500" />
                  </TooltipTrigger>
                  <TooltipContent>Webhook active</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Default: {repository.defaultBranch}
            {repository.lastSyncedAt && (
              <span className="ml-2">
                Last synced: {new Date(repository.lastSyncedAt).toLocaleDateString()}
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {repository.syncEnabled && (
          <Button variant="ghost" size="icon" onClick={onSync} disabled={isSyncing}>
            <RefreshCw className={cn('size-4', isSyncing && 'animate-spin')} />
          </Button>
        )}

        <Switch checked={repository.syncEnabled} onCheckedChange={onToggle} disabled={isToggling} />
      </div>
    </div>
  );
});

// ============================================================================
// Loading Skeleton
// ============================================================================

function GitHubIntegrationSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Skeleton className="size-10 rounded-full" />
          <div>
            <Skeleton className="h-5 w-32 mb-2" />
            <Skeleton className="h-4 w-48" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
        <Skeleton className="h-16" />
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Not Connected State
// ============================================================================

interface NotConnectedStateProps {
  onConnect: () => void;
  isConnecting: boolean;
}

function NotConnectedState({ onConnect, isConnecting }: NotConnectedStateProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-muted p-2">
            <Github className="size-6" />
          </div>
          <div>
            <CardTitle className="text-lg">GitHub</CardTitle>
            <CardDescription>
              Connect your GitHub account to link commits and pull requests
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <p className="text-muted-foreground mb-4 max-w-md">
            Link your GitHub repositories to automatically track commits, pull requests, and enable
            branch name suggestions for issues.
          </p>
          <Button onClick={onConnect} disabled={isConnecting}>
            {isConnecting ? (
              <>
                <Loader2 className="size-4 mr-2 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <Github className="size-4 mr-2" />
                Connect GitHub
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export const GitHubIntegration = observer(function GitHubIntegration({
  workspaceId,
  className,
}: GitHubIntegrationProps) {
  const queryClient = useQueryClient();
  const [showDisconnectDialog, setShowDisconnectDialog] = React.useState(false);
  const [syncingRepoId, setSyncingRepoId] = React.useState<string | null>(null);

  // Query: Get GitHub installation
  const {
    data: installation,
    isLoading: isLoadingInstallation,
    error: installationError,
  } = useQuery({
    queryKey: integrationKeys.github(workspaceId),
    queryFn: () => integrationsApi.getGitHubInstallation(workspaceId),
    enabled: !!workspaceId,
  });

  // Query: Get repositories
  const { data: repositories, isLoading: isLoadingRepos } = useQuery({
    queryKey: integrationKeys.repositories(workspaceId),
    queryFn: () => integrationsApi.listRepositories(workspaceId),
    enabled: !!workspaceId && !!installation,
  });

  // Mutation: Connect GitHub
  const connectMutation = useMutation({
    mutationFn: () => integrationsApi.getGitHubAuthUrl(workspaceId),
    onSuccess: (data) => {
      // Redirect to GitHub OAuth
      window.location.href = data.url;
    },
    onError: (error: Error) => {
      toast.error('Failed to connect GitHub', {
        description: error.message,
      });
    },
  });

  // Mutation: Disconnect GitHub
  const disconnectMutation = useMutation({
    mutationFn: () => integrationsApi.disconnectGitHub(workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.github(workspaceId),
      });
      toast.success('GitHub disconnected');
      setShowDisconnectDialog(false);
    },
    onError: (error: Error) => {
      toast.error('Failed to disconnect GitHub', {
        description: error.message,
      });
    },
  });

  // Mutation: Toggle repository
  const toggleRepoMutation = useMutation({
    mutationFn: ({ repositoryId, enabled }: { repositoryId: string; enabled: boolean }) =>
      integrationsApi.toggleRepository(workspaceId, repositoryId, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: integrationKeys.repositories(workspaceId),
      });
    },
    onError: (error: Error) => {
      toast.error('Failed to update repository', {
        description: error.message,
      });
    },
  });

  // Mutation: Sync repository
  const syncRepoMutation = useMutation({
    mutationFn: (repositoryId: string) => integrationsApi.syncRepository(workspaceId, repositoryId),
    onMutate: (repositoryId) => {
      setSyncingRepoId(repositoryId);
    },
    onSuccess: () => {
      toast.success('Repository sync started');
    },
    onError: (error: Error) => {
      toast.error('Failed to sync repository', {
        description: error.message,
      });
    },
    onSettled: () => {
      setSyncingRepoId(null);
    },
  });

  // Loading state
  if (isLoadingInstallation) {
    return <GitHubIntegrationSkeleton />;
  }

  // Error state
  if (installationError) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center py-8">
          <AlertCircle className="size-12 text-destructive mb-4" />
          <p className="text-muted-foreground">Failed to load GitHub integration</p>
        </CardContent>
      </Card>
    );
  }

  // Not connected state
  if (!installation) {
    return (
      <NotConnectedState
        onConnect={() => connectMutation.mutate()}
        isConnecting={connectMutation.isPending}
      />
    );
  }

  // Connected state
  return (
    <>
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Avatar className="size-10">
                <AvatarImage src={installation.avatarUrl} />
                <AvatarFallback>
                  <Github className="size-5" />
                </AvatarFallback>
              </Avatar>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg">{installation.accountLogin}</CardTitle>
                  <Badge variant="outline" className="text-green-600 border-green-300">
                    <CheckCircle2 className="size-3 mr-1" />
                    Connected
                  </Badge>
                </div>
                <CardDescription>
                  {installation.accountType} account &middot;{' '}
                  {installation.repositorySelection === 'all'
                    ? 'All repositories'
                    : 'Selected repositories'}
                </CardDescription>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() =>
                        window.open(
                          `https://github.com/settings/installations/${installation.installationId}`,
                          '_blank'
                        )
                      }
                    >
                      <Settings className="size-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Manage on GitHub</TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setShowDisconnectDialog(true)}
                    >
                      <Unplug className="size-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Disconnect</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Repositories ({repositories?.length ?? 0})</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  queryClient.invalidateQueries({
                    queryKey: integrationKeys.repositories(workspaceId),
                  })
                }
              >
                <RefreshCw className="size-4 mr-2" />
                Refresh
              </Button>
            </div>

            {isLoadingRepos ? (
              <div className="space-y-2">
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
              </div>
            ) : repositories?.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No repositories available
              </div>
            ) : (
              <div className="space-y-2">
                {repositories?.map((repo) => (
                  <RepositoryRow
                    key={repo.id}
                    repository={repo}
                    onToggle={(enabled) =>
                      toggleRepoMutation.mutate({
                        repositoryId: repo.id,
                        enabled,
                      })
                    }
                    onSync={() => syncRepoMutation.mutate(repo.id)}
                    isToggling={toggleRepoMutation.isPending}
                    isSyncing={syncingRepoId === repo.id}
                  />
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Disconnect Confirmation Dialog */}
      <AlertDialog open={showDisconnectDialog} onOpenChange={setShowDisconnectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disconnect GitHub?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the connection to <strong>{installation.accountLogin}</strong>.
              Existing links to commits and pull requests will be preserved, but no new data will be
              synced.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={disconnectMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => disconnectMutation.mutate()}
              disabled={disconnectMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {disconnectMutation.isPending ? (
                <>
                  <Loader2 className="size-4 mr-2 animate-spin" />
                  Disconnecting...
                </>
              ) : (
                'Disconnect'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
});

export default GitHubIntegration;
