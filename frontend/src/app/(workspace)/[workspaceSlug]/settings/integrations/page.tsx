'use client';

/**
 * IntegrationsSettingsPage - Manage workspace integrations.
 *
 * T192: GitHub integration settings, Slack placeholder, auto-transition toggles.
 */

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { Github, Slack, Settings, AlertCircle, Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useStore } from '@/stores';
import { GitHubIntegration } from '@/components/integrations';
import { integrationsApi, type IntegrationSettings } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface IntegrationCardProps {
  name: string;
  description: string;
  icon: React.ElementType;
  connected: boolean;
  comingSoon?: boolean;
  children?: React.ReactNode;
}

// ============================================================================
// Query Keys
// ============================================================================

const settingsKeys = {
  all: ['integration-settings'] as const,
  workspace: (workspaceId: string) => [...settingsKeys.all, workspaceId] as const,
};

// ============================================================================
// Integration Card Wrapper
// ============================================================================

function IntegrationCard({
  name,
  description,
  icon: Icon,
  connected,
  comingSoon = false,
  children,
}: IntegrationCardProps) {
  return (
    <Card className={cn(comingSoon && 'opacity-60')}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-muted p-2">
              <Icon className="size-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="text-lg">{name}</CardTitle>
                {comingSoon && (
                  <Badge variant="secondary" className="text-xs">
                    Coming Soon
                  </Badge>
                )}
              </div>
              <CardDescription>{description}</CardDescription>
            </div>
          </div>

          {!comingSoon && (
            <Badge
              variant={connected ? 'default' : 'outline'}
              className={cn(
                connected && 'bg-green-100 text-green-700 border-green-200 hover:bg-green-100'
              )}
            >
              {connected ? (
                <>
                  <Check className="size-3 mr-1" />
                  Connected
                </>
              ) : (
                'Not connected'
              )}
            </Badge>
          )}
        </div>
      </CardHeader>
      {children && <CardContent>{children}</CardContent>}
    </Card>
  );
}

// ============================================================================
// Settings Form
// ============================================================================

interface SettingsFormProps {
  settings: IntegrationSettings;
  onSave: (settings: Partial<IntegrationSettings>) => void;
  isSaving: boolean;
}

function SettingsForm({ settings, onSave, isSaving }: SettingsFormProps) {
  const [autoTransition, setAutoTransition] = React.useState(settings.autoTransitionEnabled);
  const [branchFormat, setBranchFormat] = React.useState(settings.branchNamingFormat);
  const [mergeTransition, setMergeTransition] = React.useState(settings.prMergeTransition);

  const hasChanges =
    autoTransition !== settings.autoTransitionEnabled ||
    branchFormat !== settings.branchNamingFormat ||
    mergeTransition !== settings.prMergeTransition;

  const handleSave = () => {
    onSave({
      autoTransitionEnabled: autoTransition,
      branchNamingFormat: branchFormat,
      prMergeTransition: mergeTransition,
    });
  };

  return (
    <div className="space-y-6">
      {/* Auto-transition */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label htmlFor="auto-transition" className="text-base font-medium">
            Auto-transition Issues
          </Label>
          <p className="text-sm text-muted-foreground">
            Automatically update issue status based on Git activity
          </p>
        </div>
        <Switch id="auto-transition" checked={autoTransition} onCheckedChange={setAutoTransition} />
      </div>

      <Separator />

      {/* Branch naming format */}
      <div className="space-y-3">
        <Label htmlFor="branch-format" className="text-base font-medium">
          Branch Naming Format
        </Label>
        <p className="text-sm text-muted-foreground">
          Template for generating branch names from issues
        </p>
        <Select value={branchFormat} onValueChange={setBranchFormat}>
          <SelectTrigger id="branch-format">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="feature/{identifier}-{slug}">
              feature/PILOT-123-short-title
            </SelectItem>
            <SelectItem value="{type}/{identifier}-{slug}">fix/PILOT-123-short-title</SelectItem>
            <SelectItem value="{identifier}/{slug}">PILOT-123/short-title</SelectItem>
            <SelectItem value="{identifier}-{slug}">PILOT-123-short-title</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Separator />

      {/* PR merge transition */}
      <div className="space-y-3">
        <Label htmlFor="merge-transition" className="text-base font-medium">
          PR Merge Transition
        </Label>
        <p className="text-sm text-muted-foreground">Status to set when a linked PR is merged</p>
        <Select
          value={mergeTransition}
          onValueChange={setMergeTransition}
          disabled={!autoTransition}
        >
          <SelectTrigger id="merge-transition">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="done">Done</SelectItem>
            <SelectItem value="in_review">In Review</SelectItem>
            <SelectItem value="none">No change</SelectItem>
          </SelectContent>
        </Select>
        {!autoTransition && (
          <p className="text-xs text-amber-600">Enable auto-transition to use this setting</p>
        )}
      </div>

      {/* Save button */}
      <div className="flex items-center gap-3 pt-4">
        <Button
          onClick={handleSave}
          disabled={isSaving || !hasChanges}
          aria-busy={isSaving}
          className="min-w-[120px]"
        >
          {isSaving ? (
            <>
              <Loader2 className="size-4 mr-2 animate-spin" aria-hidden="true" />
              Saving...
            </>
          ) : (
            'Save Changes'
          )}
        </Button>
        {hasChanges && (
          <p className="text-sm text-muted-foreground" role="status">
            You have unsaved changes.
          </p>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Loading Skeleton
// ============================================================================

function SettingsSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-12" />
      <Skeleton className="h-px w-full" />
      <Skeleton className="h-20" />
      <Skeleton className="h-px w-full" />
      <Skeleton className="h-20" />
    </div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

const IntegrationsSettingsPage = observer(function IntegrationsSettingsPage() {
  const params = useParams();
  const workspaceSlug = params.workspaceSlug as string;
  const queryClient = useQueryClient();

  const { workspaceStore } = useStore();
  const workspace = workspaceStore.currentWorkspace;
  // Fallback to slug when workspace not loaded (matches pattern from note detail page)
  const workspaceId = workspace?.id ?? workspaceSlug;

  // Query: Get integration settings
  const {
    data: settings,
    isLoading: isLoadingSettings,
    error: settingsError,
  } = useQuery({
    queryKey: settingsKeys.workspace(workspaceId),
    queryFn: () => integrationsApi.getSettings(workspaceId),
    enabled: !!workspaceId,
  });

  // Query: Get GitHub installation status
  const { data: githubInstallation } = useQuery({
    queryKey: ['integrations', 'github', workspaceId],
    queryFn: () => integrationsApi.getGitHubInstallation(workspaceId),
    enabled: !!workspaceId,
  });

  // Mutation: Update settings
  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: Partial<IntegrationSettings>) =>
      integrationsApi.updateSettings(workspaceId, newSettings),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: settingsKeys.workspace(workspaceId),
      });
      toast.success('Settings saved');
    },
    onError: (error: Error) => {
      toast.error('Failed to save settings', {
        description: error.message,
      });
    },
  });

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Integrations</h1>
          <p className="text-sm text-muted-foreground">
            Connect external services to enhance your workflow.
          </p>
        </div>

        {/* Integration Status Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Connected Services</CardTitle>
            <CardDescription>Overview of your workspace integrations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div
                      className={cn(
                        'flex items-center gap-2 rounded-full px-3 py-1.5 border',
                        githubInstallation
                          ? 'bg-green-50 border-green-200 text-green-700 dark:bg-green-900/30 dark:border-green-800 dark:text-green-400'
                          : 'bg-muted text-muted-foreground'
                      )}
                    >
                      <Github className="size-4" />
                      <span className="text-sm font-medium">GitHub</span>
                      {githubInstallation && <Check className="size-3" />}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    {githubInstallation
                      ? `Connected as ${githubInstallation.accountLogin}`
                      : 'Not connected'}
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-2 rounded-full px-3 py-1.5 border bg-muted text-muted-foreground opacity-60">
                      <Slack className="size-4" />
                      <span className="text-sm font-medium">Slack</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>Coming soon</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </CardContent>
        </Card>

        {/* GitHub Integration */}
        <GitHubIntegration workspaceId={workspaceId} />

        {/* Slack Placeholder */}
        <IntegrationCard
          name="Slack"
          description="Get notifications and interact with issues from Slack"
          icon={Slack}
          connected={false}
          comingSoon
        >
          <div className="py-4 text-center text-muted-foreground">
            <p className="text-sm">Slack integration is coming soon. Stay tuned for updates!</p>
          </div>
        </IntegrationCard>

        {/* Settings */}
        {githubInstallation && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Settings className="size-5" />
                Integration Settings
              </CardTitle>
              <CardDescription>
                Configure how integrations interact with your issues
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoadingSettings ? (
                <SettingsSkeleton />
              ) : settingsError ? (
                <div className="flex items-center gap-2 text-destructive">
                  <AlertCircle className="size-4" />
                  <span>Failed to load settings</span>
                </div>
              ) : settings ? (
                <SettingsForm
                  settings={settings}
                  onSave={(newSettings) => updateSettingsMutation.mutate(newSettings)}
                  isSaving={updateSettingsMutation.isPending}
                />
              ) : null}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
});

export default IntegrationsSettingsPage;
