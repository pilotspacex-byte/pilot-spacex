'use client';

import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import { useState, useRef, useCallback, useEffect } from 'react';
import { Building2, Check, ChevronsUpDown, Loader2, Plus } from 'lucide-react';
import { useWorkspaceStore } from '@/stores';
import { workspacesApi } from '@/services/api/workspaces';
import { addRecentWorkspace } from '@/components/workspace-selector';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { toSlug } from '@/lib/slug';
import { getLastWorkspacePath } from '@/lib/workspace-nav';
import { ApiError } from '@/services/api/client';
import type { Workspace } from '@/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SLUG_PATTERN = /^[a-z0-9-]*$/;

// ---------------------------------------------------------------------------
// CreateWorkspaceDialog — internal, not exported
// ---------------------------------------------------------------------------

interface CreateWorkspaceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const CreateWorkspaceDialog = observer(function CreateWorkspaceDialog({
  open,
  onOpenChange,
}: CreateWorkspaceDialogProps) {
  const workspaceStore = useWorkspaceStore();
  const router = useRouter();

  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugManuallyEdited, setSlugManuallyEdited] = useState(false);
  const [slugError, setSlugError] = useState<string | null>(null);
  const [isCheckingSlug, setIsCheckingSlug] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Tracks the slug that was last validated so we don't re-check on unchanged values
  const lastCheckedSlugRef = useRef<string>('');

  const reset = useCallback(() => {
    setName('');
    setSlug('');
    setSlugManuallyEdited(false);
    setSlugError(null);
    setIsCheckingSlug(false);
    setIsCreating(false);
    setSubmitError(null);
    lastCheckedSlugRef.current = '';
  }, []);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) reset();
      onOpenChange(nextOpen);
    },
    [onOpenChange, reset]
  );

  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setName(value);
      if (!slugManuallyEdited) {
        setSlug(toSlug(value));
        setSlugError(null);
        lastCheckedSlugRef.current = '';
      }
    },
    [slugManuallyEdited]
  );

  const handleSlugChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '')
      .slice(0, 48);
    setSlug(raw);
    setSlugManuallyEdited(true);
    setSlugError(null);
    lastCheckedSlugRef.current = '';
  }, []);

  const validateSlugAvailability = useCallback(async () => {
    const trimmed = slug.trim();
    if (!trimmed) return;
    if (!SLUG_PATTERN.test(trimmed)) {
      setSlugError('Only lowercase letters, numbers, and hyphens are allowed.');
      return;
    }
    if (trimmed === lastCheckedSlugRef.current) return;

    setIsCheckingSlug(true);
    setSlugError(null);
    try {
      await workspacesApi.get(trimmed);
      // Resolved → slug is taken
      setSlugError('Slug already taken — try another.');
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // 404 = slug is free
        setSlugError(null);
      } else {
        // Network / 5xx — block submission, show error
        setSlugError('Unable to check availability. Please try again.');
      }
    } finally {
      lastCheckedSlugRef.current = trimmed;
      setIsCheckingSlug(false);
    }
  }, [slug]);

  const isFormValid =
    name.trim().length > 0 &&
    slug.trim().length > 0 &&
    slugError === null &&
    !isCheckingSlug &&
    !isCreating;

  const handleCreate = useCallback(async () => {
    if (!isFormValid) return;

    setIsCreating(true);
    setSubmitError(null);

    try {
      const workspace = await workspaceStore.createWorkspace({
        name: name.trim(),
        slug: slug.trim(),
      });

      if (workspace) {
        addRecentWorkspace(workspace.slug);
        handleOpenChange(false);
        router.push(`/${workspace.slug}`);
      } else {
        setSubmitError(workspaceStore.error ?? 'Failed to create workspace.');
      }
    } catch {
      setSubmitError('Unexpected error. Please try again.');
    } finally {
      setIsCreating(false);
    }
  }, [isFormValid, name, slug, workspaceStore, handleOpenChange, router]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && isFormValid) {
        void handleCreate();
      }
    },
    [isFormValid, handleCreate]
  );

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md" onKeyDown={handleKeyDown}>
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold">Create workspace</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Workspaces are shared environments for your team.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          {/* Name field */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ws-name" className="text-xs font-medium">
              Name
            </Label>
            <Input
              id="ws-name"
              value={name}
              onChange={handleNameChange}
              placeholder="My Workspace"
              className="h-8 text-sm"
              autoComplete="off"
              maxLength={100}
              aria-required="true"
            />
          </div>

          {/* Slug field */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="ws-slug" className="text-xs font-medium">
              Slug
              <span className="ml-1 text-[10px] text-muted-foreground font-normal">
                (used in URL)
              </span>
            </Label>
            <div className="relative">
              <Input
                id="ws-slug"
                value={slug}
                onChange={handleSlugChange}
                onBlur={() => void validateSlugAvailability()}
                placeholder="my-workspace"
                className={cn(
                  'h-8 text-sm pr-8',
                  slugError && 'border-destructive focus-visible:ring-destructive'
                )}
                autoComplete="off"
                maxLength={48}
                aria-required="true"
                aria-describedby="ws-slug-hint"
                aria-invalid={slugError !== null}
              />
              {isCheckingSlug && (
                <Loader2
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 animate-spin text-muted-foreground"
                  aria-hidden="true"
                />
              )}
            </div>

            <p id="ws-slug-hint" className="text-[10px] text-muted-foreground">
              {isCheckingSlug ? (
                'Checking availability...'
              ) : slugError ? (
                <span className="text-destructive">{slugError}</span>
              ) : (
                <>Lowercase letters, numbers, and hyphens only. Max 48 chars.</>
              )}
            </p>
          </div>

          {/* Submit error */}
          {submitError && (
            <p role="alert" className="text-xs text-destructive">
              {submitError}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => handleOpenChange(false)}
            disabled={isCreating}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            className="h-7 text-xs"
            onClick={() => void handleCreate()}
            disabled={!isFormValid}
            aria-busy={isCreating}
          >
            {isCreating ? (
              <>
                <Loader2 className="mr-1.5 h-3 w-3 animate-spin" aria-hidden="true" />
                Creating...
              </>
            ) : (
              'Create workspace'
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
});

// ---------------------------------------------------------------------------
// WorkspaceSwitcher — exported
// ---------------------------------------------------------------------------

interface WorkspaceSwitcherProps {
  currentSlug: string;
  collapsed?: boolean;
}

export const WorkspaceSwitcher = observer(function WorkspaceSwitcher({
  currentSlug,
  collapsed,
}: WorkspaceSwitcherProps) {
  const workspaceStore = useWorkspaceStore();
  const router = useRouter();

  const [popoverOpen, setPopoverOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // Fetch all workspaces when popover opens so the list is populated
  useEffect(() => {
    if (popoverOpen) {
      workspaceStore.fetchWorkspaces();
    }
  }, [popoverOpen, workspaceStore]);

  const currentWorkspace: Workspace | undefined =
    workspaceStore.getWorkspaceBySlug(currentSlug) ?? workspaceStore.currentWorkspace ?? undefined;

  const displayName = currentWorkspace?.name ?? currentSlug;

  const handleSelectWorkspace = useCallback(
    (ws: Workspace) => {
      workspaceStore.selectWorkspace(ws.id);
      addRecentWorkspace(ws.slug);
      setPopoverOpen(false);
      const lastPath = getLastWorkspacePath(ws.slug);
      router.push(lastPath ?? `/${ws.slug}`);
    },
    [workspaceStore, router]
  );

  const handleOpenCreate = useCallback(() => {
    setPopoverOpen(false);
    setCreateDialogOpen(true);
  }, []);

  const popoverListContent = (
    <div role="menu" aria-label="Workspaces">
      {workspaceStore.workspaceList.length === 0 ? (
        <p className="px-2 py-3 text-center text-xs text-muted-foreground">No workspaces found.</p>
      ) : (
        workspaceStore.workspaceList.map((ws) => {
          const isActive = ws.slug === currentSlug;
          return (
            <button
              key={ws.id}
              type="button"
              aria-current={isActive ? 'true' : undefined}
              onClick={() => handleSelectWorkspace(ws)}
              className={cn(
                'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-xs',
                'transition-colors hover:bg-accent hover:text-accent-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isActive && 'font-medium text-foreground'
              )}
            >
              <Building2
                className={cn(
                  'h-3.5 w-3.5 shrink-0',
                  isActive ? 'text-primary' : 'text-muted-foreground'
                )}
                aria-hidden="true"
              />
              <div className="flex flex-col items-start flex-1 min-w-0">
                <span className="truncate text-left text-xs font-medium leading-tight">
                  {ws.name}
                </span>
                <span className="text-[10px] text-muted-foreground leading-tight">
                  {ws.memberCount} member{ws.memberCount !== 1 ? 's' : ''}
                </span>
              </div>
              {isActive && <Check className="h-3 w-3 shrink-0 text-primary" aria-hidden="true" />}
            </button>
          );
        })
      )}

      <Separator className="my-1" />

      <button
        type="button"
        onClick={handleOpenCreate}
        className={cn(
          'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-xs',
          'text-muted-foreground transition-colors',
          'hover:bg-accent hover:text-accent-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
      >
        <Plus className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>Create workspace</span>
      </button>
    </div>
  );

  if (collapsed) {
    return (
      <>
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-sidebar-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label={`Switch workspace (current: ${displayName})`}
                  aria-haspopup="listbox"
                  aria-expanded={popoverOpen}
                >
                  <Building2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-52 p-1" side="right" align="start" sideOffset={6}>
                {popoverListContent}
              </PopoverContent>
            </Popover>
          </TooltipTrigger>
          <TooltipContent side="right">{displayName}</TooltipContent>
        </Tooltip>
        <CreateWorkspaceDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} />
      </>
    );
  }

  return (
    <>
      <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            className={cn(
              'flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 min-h-[36px] text-left',
              'transition-colors hover:bg-sidebar-accent/50',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
            )}
            aria-label="Switch workspace"
            aria-haspopup="listbox"
            aria-expanded={popoverOpen}
          >
            <span className="max-w-[96px] truncate text-xs font-semibold text-sidebar-foreground leading-tight">
              {displayName}
            </span>
            <ChevronsUpDown className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
          </button>
        </PopoverTrigger>

        <PopoverContent className="w-52 p-1" side="bottom" align="start" sideOffset={6}>
          {popoverListContent}
        </PopoverContent>
      </Popover>

      <CreateWorkspaceDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} />
    </>
  );
});
