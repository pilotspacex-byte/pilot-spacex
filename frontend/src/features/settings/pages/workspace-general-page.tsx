/**
 * WorkspaceGeneralPage - General workspace settings.
 *
 * T029: Name/slug/description editing, metadata display, danger zone.
 * Non-admin users see read-only view without danger zone.
 */

'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useParams } from 'next/navigation';
import { AlertCircle, Building2, Calendar, Loader2, Users } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
// Card imports removed — using flat sections for cleaner settings layout
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { useStore } from '@/stores';
import { useWorkspaceSettings, useUpdateWorkspaceSettings } from '../hooks/use-workspace-settings';
import { DeleteWorkspaceDialog } from '../components/delete-workspace-dialog';
import { workspacesApi } from '@/services/api/workspaces';
import { ApiError } from '@/services/api/client';

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full sm:w-96" />
      </div>
      <Skeleton className="h-[300px] w-full" />
    </div>
  );
}

export const WorkspaceGeneralPage = observer(function WorkspaceGeneralPage() {
  const { workspaceStore } = useStore();
  const params = useParams();
  const workspaceSlug = params?.workspaceSlug as string;

  const currentWorkspace = workspaceStore.getWorkspaceBySlug(workspaceSlug);
  const workspaceId = currentWorkspace?.id || workspaceSlug;

  const isAdmin = workspaceStore.isAdmin;

  const { data: workspaceData, isLoading, error } = useWorkspaceSettings(workspaceId);

  const updateSettings = useUpdateWorkspaceSettings(workspaceId);

  const [name, setName] = React.useState('');
  const [slug, setSlug] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [hasChanges, setHasChanges] = React.useState(false);
  const [slugError, setSlugError] = React.useState<string | null>(null);
  const [isCheckingSlug, setIsCheckingSlug] = React.useState(false);

  const workspaceDescription = workspaceData?.description ?? '';

  React.useEffect(() => {
    if (workspaceData) {
      setName(workspaceData.name);
      setSlug(workspaceData.slug);
      setDescription(workspaceDescription);
    }
  }, [workspaceData, workspaceDescription]);

  React.useEffect(() => {
    if (!workspaceData) return;
    setHasChanges(
      name !== workspaceData.name ||
        slug !== workspaceData.slug ||
        description !== workspaceDescription
    );
  }, [name, slug, description, workspaceData, workspaceDescription]);

  React.useEffect(() => {
    if (!hasChanges) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = ''; // Required for Chromium browsers
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [hasChanges]);

  const handleSlugChange = (value: string) => {
    const next = value.trim();
    setSlug(next);
    if (!next) {
      setSlugError('Slug is required.');
    } else if (!SLUG_PATTERN.test(next)) {
      setSlugError('Slug must contain only lowercase letters, numbers, and hyphens.');
    } else {
      setSlugError(null);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasChanges || !workspaceData || slugError) return;

    // Check slug availability only if slug has changed
    if (slug !== workspaceData.slug) {
      setIsCheckingSlug(true);
      try {
        await workspacesApi.get(slug);
        // Resolved → slug is taken by another workspace
        setSlugError('This slug is already taken.');
        return;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          // 404 = slug is free, proceed
        } else {
          setSlugError('Unable to check slug availability. Please try again.');
          return;
        }
      } finally {
        setIsCheckingSlug(false);
      }
    }

    try {
      await updateSettings.mutateAsync({ name, slug, description });
      toast.success('Workspace updated', {
        description: 'Workspace settings have been saved.',
      });
    } catch (err) {
      toast.error('Failed to update workspace', {
        description: err instanceof Error ? err.message : 'An unexpected error occurred.',
      });
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load workspace settings</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : 'An error occurred.'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!workspaceData) return null;

  const createdAt = new Date(workspaceData.createdAt).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });

  const memberCount = workspaceData.memberCount ?? 0;

  return (
    <div className="max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">General</h1>
          <p className="text-sm text-muted-foreground">
            Manage workspace details and configuration.
          </p>
        </div>

        {/* Workspace Details */}
        <section>
          <h2 className="text-sm font-semibold text-foreground">Workspace Details</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {isAdmin
              ? 'Update your workspace name, URL slug, and description.'
              : 'View workspace information.'}
          </p>

          <form onSubmit={handleSave} className="mt-4 space-y-5">
            {/* Name */}
            <div className="space-y-1.5">
              <Label htmlFor="workspace-name">Workspace Name</Label>
              <Input
                id="workspace-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                readOnly={!isAdmin}
                disabled={updateSettings.isPending}
                className={`w-full sm:max-w-md ${!isAdmin ? 'cursor-default opacity-70' : ''}`}
                aria-describedby="workspace-name-hint"
              />
              <p id="workspace-name-hint" className="text-xs text-muted-foreground">
                The display name for your workspace.
              </p>
            </div>

            {/* Slug */}
            <div className="space-y-1.5">
              <Label htmlFor="workspace-slug">URL Slug</Label>
              <Input
                id="workspace-slug"
                type="text"
                required
                minLength={1}
                value={slug}
                onChange={(e) => handleSlugChange(e.target.value)}
                readOnly={!isAdmin}
                disabled={updateSettings.isPending}
                className={`w-full sm:max-w-md ${slugError ? 'border-destructive' : ''}`}
                aria-describedby={slugError ? 'workspace-slug-error' : 'workspace-slug-hint'}
                aria-invalid={!!slugError}
              />
              {slugError ? (
                <p id="workspace-slug-error" className="text-xs text-destructive" role="alert">
                  {slugError}
                </p>
              ) : (
                <p id="workspace-slug-hint" className="text-xs text-muted-foreground">
                  Used in the URL: /{slug}
                </p>
              )}
              {!slugError && isAdmin && slug !== workspaceData.slug && (
                <p className="text-xs text-[var(--warning)]" role="alert">
                  Changing the slug will update all URLs. Share the new URL with your team.
                </p>
              )}
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <Label htmlFor="workspace-description">Description</Label>
              <Textarea
                id="workspace-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                readOnly={!isAdmin}
                disabled={updateSettings.isPending}
                placeholder="A brief description of this workspace"
                className={`w-full sm:max-w-md ${!isAdmin ? 'cursor-default opacity-70' : ''}`}
                rows={3}
              />
            </div>

            {/* Save Button */}
            {isAdmin && (
              <div className="flex items-center gap-3 pt-1">
                <Button
                  type="submit"
                  disabled={!hasChanges || updateSettings.isPending || isCheckingSlug}
                  aria-busy={updateSettings.isPending || isCheckingSlug}
                  className="min-w-[120px]"
                >
                  {(updateSettings.isPending || isCheckingSlug) && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  )}
                  {isCheckingSlug
                    ? 'Checking...'
                    : updateSettings.isPending
                      ? 'Saving...'
                      : 'Save Changes'}
                </Button>
                {hasChanges && (
                  <p className="text-xs text-muted-foreground" role="status">
                    You have unsaved changes.
                  </p>
                )}
              </div>
            )}
          </form>
        </section>

        <Separator />

        {/* Metadata */}
        <section>
          <h2 className="text-sm font-semibold text-foreground">Workspace Information</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="flex items-center gap-3 rounded-lg bg-background-subtle p-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Created</p>
                <p className="text-sm font-medium">{createdAt}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-background-subtle p-3">
              <Users className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Members</p>
                <p className="text-sm font-medium">{memberCount}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-background-subtle p-3">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Workspace ID</p>
                <p className="font-mono text-xs">{workspaceId.slice(0, 8)}...</p>
              </div>
            </div>
          </div>
        </section>

        {/* Danger Zone */}
        {isAdmin && (
          <>
            <Separator />
            <section>
              <h2 className="text-sm font-semibold text-destructive">Danger Zone</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Irreversible actions. Proceed with extreme caution.
              </p>
              <div className="mt-3 flex flex-col gap-3 rounded-lg border border-destructive/20 bg-destructive/5 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium">Delete this workspace</p>
                  <p className="text-xs text-muted-foreground">
                    Permanently delete this workspace and all of its data.
                  </p>
                </div>
                <DeleteWorkspaceDialog
                  workspaceId={workspaceId}
                  workspaceName={workspaceData.name}
                />
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
});
