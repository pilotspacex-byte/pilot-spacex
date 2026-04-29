'use client';

import { observer } from 'mobx-react-lite';
import { useRouter } from 'next/navigation';
import { useState, useRef, useCallback, useMemo } from 'react';
import {
  Building2,
  Check,
  ChevronsUpDown,
  Loader2,
  LogOut,
  Settings,
  Shield,
  UserPlus,
} from 'lucide-react';
import { useAuthStore, useUIStore, useWorkspaceStore } from '@/stores';
import { workspacesApi } from '@/services/api/workspaces';
import { addRecentWorkspace } from '@/components/workspace-selector';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
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
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { toSlug } from '@/lib/slug';
import { getLastWorkspacePath, getOrderedRecentWorkspaces } from '@/lib/workspace-nav';
import { useSwitcherQueryStringSync } from '@/hooks/useSwitcherQueryStringSync';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import { ApiError } from '@/services/api/client';
import type { Workspace, WorkspaceRole } from '@/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const SLUG_PATTERN = /^[a-z0-9-]*$/;

// Deterministic color palette for workspace identity dots.
// Hashed from workspace.id so the same workspace always gets the same color.
const AVATAR_PALETTE = [
  '#10b981', // emerald
  '#3b82f6', // blue
  '#a855f7', // purple
  '#f97316', // orange
  '#ef4444', // red
  '#06b6d4', // cyan
  '#eab308', // yellow
  '#ec4899', // pink
];

function colorForId(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0;
  return AVATAR_PALETTE[Math.abs(hash) % AVATAR_PALETTE.length]!;
}

function roleLabel(role: WorkspaceRole | null | undefined): string | null {
  if (!role) return null;
  return role.charAt(0).toUpperCase() + role.slice(1);
}

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
      setSlugError('Slug already taken — try another.');
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setSlugError(null);
      } else {
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
// LeaveWorkspaceDialog — confirm leaving the current workspace.
// ---------------------------------------------------------------------------

interface LeaveWorkspaceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceName: string;
  workspaceId: string;
  memberId: string | null;
}

const LeaveWorkspaceDialog = observer(function LeaveWorkspaceDialog({
  open,
  onOpenChange,
  workspaceName,
  workspaceId,
  memberId,
}: LeaveWorkspaceDialogProps) {
  const workspaceStore = useWorkspaceStore();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLeave = useCallback(async () => {
    if (!memberId) {
      setError('Could not resolve your membership. Try again in a moment.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await workspacesApi.removeMember(workspaceId, memberId);
      await workspaceStore.fetchWorkspaces({ ensureSelection: true });
      onOpenChange(false);
      router.push('/');
    } catch {
      setError('Failed to leave workspace. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }, [memberId, workspaceId, workspaceStore, onOpenChange, router]);

  return (
    <Dialog open={open} onOpenChange={(o) => !submitting && onOpenChange(o)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold">Leave {workspaceName}?</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            You&apos;ll lose access immediately. An admin will need to invite you back.
          </DialogDescription>
        </DialogHeader>

        {error && (
          <p role="alert" className="text-xs text-destructive">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            size="sm"
            className="h-7 text-xs"
            onClick={() => void handleLeave()}
            disabled={submitting || !memberId}
            aria-busy={submitting}
            data-testid="leave-workspace-confirm"
          >
            {submitting ? (
              <>
                <Loader2 className="mr-1.5 h-3 w-3 animate-spin" aria-hidden="true" />
                Leaving...
              </>
            ) : (
              'Leave workspace'
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
});

// ---------------------------------------------------------------------------
// WorkspacePill — exported trigger button (Surface 2 anchor)
// ---------------------------------------------------------------------------

interface WorkspacePillProps {
  name: string;
  ariaLabel?: string;
  onClick?: () => void;
}

export const WorkspacePill = observer(function WorkspacePill({
  name,
  ariaLabel,
  onClick,
}: WorkspacePillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid="workspace-pill"
      aria-label={ariaLabel ?? 'Switch workspace'}
      className={cn(
        'flex h-9 w-full items-center gap-2 rounded-full border border-border',
        'bg-background px-3',
        'transition-colors hover:bg-sidebar-accent',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
      )}
    >
      <Building2 className="h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
      <span className="flex-1 truncate text-left text-[13px] font-medium text-[var(--text-heading)]">
        {name}
      </span>
      <ChevronsUpDown
        className="h-3 w-3 shrink-0 text-[var(--text-muted)]"
        aria-hidden="true"
      />
    </button>
  );
});

// ---------------------------------------------------------------------------
// WorkspaceSwitcher — Popover + cmdk Surface 2.
// Layout (top → bottom):
//   - Search input
//   - CURRENT band: ws header + Workspace settings / AI providers / Members &
//     invites / Leave (non-owners only)
//   - SWITCH TO band: RECENT subgroup + ALL subgroup
//   - Footer: + New workspace
// JUMP TO (Projects/Tasks/Topics/...) was removed — those destinations are
// already permanent rows in the sidebar's WORKSPACE accordion and reachable
// via the global ⌘K command palette.
// ---------------------------------------------------------------------------

interface WorkspaceSwitcherProps {
  currentSlug: string;
  collapsed?: boolean;
}

export const WorkspaceSwitcher = observer(function WorkspaceSwitcher({
  currentSlug,
  collapsed,
}: WorkspaceSwitcherProps) {
  const uiStore = useUIStore();
  const workspaceStore = useWorkspaceStore();
  const authStore = useAuthStore();
  const router = useRouter();
  const settings = useSettingsModal();

  useSwitcherQueryStringSync();

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);

  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (next) uiStore.openWorkspaceSwitcher();
      else uiStore.closeWorkspaceSwitcher();
    },
    [uiStore]
  );

  const currentWorkspace: Workspace | undefined =
    workspaceStore.getWorkspaceBySlug(currentSlug) ?? workspaceStore.currentWorkspace ?? undefined;

  const displayName = currentWorkspace?.name ?? currentSlug;

  // Per-workspace role lookup from auth profile (covers ALL workspaces, not
  // just the currently selected one — same data shape WorkspaceStore.currentUserRole uses).
  const membershipsByWs = useMemo(() => {
    const map = new Map<string, WorkspaceRole>();
    for (const m of authStore.user?.workspaceMemberships ?? []) {
      map.set(m.workspaceId, m.role.toLowerCase() as WorkspaceRole);
    }
    return map;
  }, [authStore.user?.workspaceMemberships]);

  const currentRole: WorkspaceRole | null = currentWorkspace
    ? (membershipsByWs.get(currentWorkspace.id) ?? null)
    : null;

  // Member id for the current user inside the current workspace — needed to
  // call removeMember(workspaceId, memberId). Null if not yet loaded.
  const currentSelfMemberId = useMemo(() => {
    const userId = authStore.user?.id;
    const wsId = currentWorkspace?.id;
    if (!userId || !wsId) return null;
    const members = workspaceStore.members.get(wsId) ?? [];
    return members.find((m) => m.userId === userId)?.id ?? null;
  }, [authStore.user?.id, currentWorkspace?.id, workspaceStore.members]);

  // Recents (excluding current) and the alphabetical leftovers.
  const { recentWorkspaces, otherWorkspaces } = useMemo(() => {
    const all = workspaceStore.workspaceList;
    const currentId = currentWorkspace?.id;
    const recents = getOrderedRecentWorkspaces(workspaceStore).filter((w) => w.id !== currentId);
    const seen = new Set<string>(recents.map((w) => w.id));
    if (currentId) seen.add(currentId);
    const others: Workspace[] = [];
    for (const w of all) {
      if (!seen.has(w.id)) others.push(w);
    }
    others.sort((a, b) => a.name.localeCompare(b.name));
    return { recentWorkspaces: recents, otherWorkspaces: others };
  }, [workspaceStore, currentWorkspace?.id]);

  const handleSelectWorkspace = useCallback(
    (ws: Workspace) => {
      addRecentWorkspace(ws.slug);
      const lastPath = getLastWorkspacePath(ws.slug);
      router.push(lastPath ?? `/${ws.slug}`);
      uiStore.closeWorkspaceSwitcher();
    },
    [router, uiStore]
  );

  const handleOpenSettings = useCallback(
    (section: 'general' | 'ai-providers') => {
      settings.openSettings(section);
      uiStore.closeWorkspaceSwitcher();
    },
    [settings, uiStore]
  );

  // Members management lives at a dedicated route, not as a settings-modal tab.
  const handleOpenMembers = useCallback(() => {
    if (currentWorkspace) {
      router.push(`/${currentWorkspace.slug}/settings/members`);
    }
    uiStore.closeWorkspaceSwitcher();
  }, [router, uiStore, currentWorkspace]);

  const handleOpenCreate = useCallback(() => {
    uiStore.closeWorkspaceSwitcher();
    setCreateDialogOpen(true);
  }, [uiStore]);

  const handleOpenLeave = useCallback(() => {
    uiStore.closeWorkspaceSwitcher();
    setLeaveDialogOpen(true);
  }, [uiStore]);

  const showLeaveRow = !!currentWorkspace && currentRole !== null && currentRole !== 'owner';

  // ---------------------------------------------------------------------------
  // Popover content
  // ---------------------------------------------------------------------------

  const popoverContent = (
    <PopoverContent
      side="bottom"
      align="start"
      sideOffset={8}
      className="w-[320px] rounded-2xl p-0 border border-border"
      style={{
        backgroundColor: '#ffffff',
        boxShadow: '0 12px 32px 0 #0a0a2025, 0 2px 6px 0 #0a0a2010',
      }}
    >
      <Command className="bg-transparent">
        <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--border-card)]">
          <CommandInput
            placeholder="Search workspaces…"
            className="text-[15px] placeholder:text-[var(--text-muted)] font-medium border-0 px-0 h-8"
          />
        </div>
        <CommandList className="max-h-[420px] p-2">
          <CommandEmpty className="py-6 text-center text-[13px] text-[var(--text-muted)]">
            No matches.
          </CommandEmpty>

          {currentWorkspace && (
            <CommandGroup heading="CURRENT">
              {/* Header row — workspace identity + quick settings */}
              <CommandItem
                value={`current-header-${currentWorkspace.slug}`}
                onSelect={() => handleOpenSettings('general')}
                data-testid="switcher-current-header"
                className="gap-2 rounded-md px-2 py-2"
              >
                <span
                  className="h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: colorForId(currentWorkspace.id) }}
                  aria-hidden="true"
                />
                <span className="flex-1 truncate text-[13px] font-semibold text-[var(--text-heading)]">
                  {currentWorkspace.name}
                </span>
                {currentRole && (
                  <span
                    className="shrink-0 rounded-full bg-[var(--surface-input)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--text-muted)]"
                    data-testid="switcher-current-role"
                  >
                    {roleLabel(currentRole)}
                  </span>
                )}
                <span className="shrink-0 text-[10px] text-[var(--text-muted)]">
                  · {currentWorkspace.memberCount}
                </span>
                <Settings
                  className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]"
                  aria-hidden="true"
                />
              </CommandItem>

              <CommandItem
                value="current-action-settings"
                onSelect={() => handleOpenSettings('general')}
                data-testid="switcher-current-settings"
                className="gap-2 rounded-md px-2 py-2"
              >
                <Settings
                  className="h-4 w-4 shrink-0 text-[var(--text-muted)]"
                  aria-hidden="true"
                />
                <span className="flex-1 truncate text-[13px] text-[var(--text-heading)]">
                  Workspace settings
                </span>
              </CommandItem>

              <CommandItem
                value="current-action-ai-providers"
                onSelect={() => handleOpenSettings('ai-providers')}
                data-testid="switcher-current-ai-providers"
                className="gap-2 rounded-md px-2 py-2"
              >
                <Shield
                  className="h-4 w-4 shrink-0 text-[var(--text-muted)]"
                  aria-hidden="true"
                />
                <span className="flex-1 truncate text-[13px] text-[var(--text-heading)]">
                  AI providers
                </span>
              </CommandItem>

              <CommandItem
                value="current-action-members"
                onSelect={handleOpenMembers}
                data-testid="switcher-current-members"
                className="gap-2 rounded-md px-2 py-2"
              >
                <UserPlus
                  className="h-4 w-4 shrink-0 text-[var(--text-muted)]"
                  aria-hidden="true"
                />
                <span className="flex-1 truncate text-[13px] text-[var(--text-heading)]">
                  Members &amp; invites
                </span>
              </CommandItem>

              {showLeaveRow && (
                <CommandItem
                  value="current-action-leave"
                  onSelect={handleOpenLeave}
                  data-testid="switcher-current-leave"
                  className="gap-2 rounded-md px-2 py-2 text-destructive data-[selected=true]:text-destructive"
                >
                  <LogOut className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span className="flex-1 truncate text-[13px]">Leave workspace</span>
                </CommandItem>
              )}
            </CommandGroup>
          )}

          {recentWorkspaces.length > 0 && (
            <CommandGroup heading="RECENT">
              {recentWorkspaces.map((ws, idx) => {
                const role = membershipsByWs.get(ws.id) ?? null;
                return (
                  <CommandItem
                    key={ws.id}
                    value={`ws-${ws.slug}-${ws.name}`}
                    onSelect={() => handleSelectWorkspace(ws)}
                    data-testid={`switcher-ws-${ws.slug}`}
                    className="gap-2 rounded-md px-2 py-2"
                  >
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: colorForId(ws.id) }}
                      aria-hidden="true"
                    />
                    <span className="flex-1 truncate text-[13px] text-[var(--text-heading)]">
                      {ws.name}
                    </span>
                    {role && (
                      <span className="shrink-0 text-[10px] text-[var(--text-muted)]">
                        {roleLabel(role)}
                      </span>
                    )}
                    {idx === 0 && (
                      <kbd className="font-mono text-[10px] text-[var(--text-muted)]">⌘2</kbd>
                    )}
                    {idx === 1 && (
                      <kbd className="font-mono text-[10px] text-[var(--text-muted)]">⌘3</kbd>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          )}

          {otherWorkspaces.length > 0 && (
            <CommandGroup heading="ALL">
              {otherWorkspaces.map((ws) => {
                const role = membershipsByWs.get(ws.id) ?? null;
                return (
                  <CommandItem
                    key={ws.id}
                    value={`ws-${ws.slug}-${ws.name}`}
                    onSelect={() => handleSelectWorkspace(ws)}
                    data-testid={`switcher-ws-${ws.slug}`}
                    className="gap-2 rounded-md px-2 py-2"
                  >
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ backgroundColor: colorForId(ws.id) }}
                      aria-hidden="true"
                    />
                    <span className="flex-1 truncate text-[13px] text-[var(--text-heading)]">
                      {ws.name}
                    </span>
                    {role && (
                      <span className="shrink-0 text-[10px] text-[var(--text-muted)]">
                        {roleLabel(role)}
                      </span>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          )}

          {currentWorkspace && (
            <Check
              className="hidden"
              aria-label="Current workspace"
              data-testid={`switcher-active-check-${currentWorkspace.slug}`}
            />
          )}
        </CommandList>

        <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border-card)]">
          <button
            type="button"
            onClick={handleOpenCreate}
            data-testid="switcher-new-workspace"
            className="text-[13px] font-medium text-[var(--brand-primary)] hover:text-[var(--brand-dark)] focus-visible:outline-none focus-visible:underline"
          >
            + New workspace
          </button>
        </div>
      </Command>
    </PopoverContent>
  );

  // ---------------------------------------------------------------------------
  // Collapsed sidebar — show icon-only trigger inside Tooltip
  // ---------------------------------------------------------------------------

  if (collapsed) {
    return (
      <>
        <Popover open={uiStore.workspaceSwitcherOpen} onOpenChange={handleOpenChange}>
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  data-testid="workspace-pill"
                  className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-sidebar-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label={`Switch workspace (current: ${displayName})`}
                  aria-haspopup="dialog"
                  aria-expanded={uiStore.workspaceSwitcherOpen}
                >
                  <Building2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                </button>
              </PopoverTrigger>
            </TooltipTrigger>
            <TooltipContent side="right">{displayName}</TooltipContent>
          </Tooltip>
          {popoverContent}
        </Popover>
        <CreateWorkspaceDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} />
        {currentWorkspace && (
          <LeaveWorkspaceDialog
            open={leaveDialogOpen}
            onOpenChange={setLeaveDialogOpen}
            workspaceName={currentWorkspace.name}
            workspaceId={currentWorkspace.id}
            memberId={currentSelfMemberId}
          />
        )}
      </>
    );
  }

  // ---------------------------------------------------------------------------
  // Expanded sidebar — full WorkspacePill trigger
  // ---------------------------------------------------------------------------

  return (
    <>
      <Popover open={uiStore.workspaceSwitcherOpen} onOpenChange={handleOpenChange}>
        <PopoverTrigger asChild>
          <WorkspacePill name={displayName} ariaLabel="Switch workspace" />
        </PopoverTrigger>
        {popoverContent}
      </Popover>

      <CreateWorkspaceDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} />
      {currentWorkspace && (
        <LeaveWorkspaceDialog
          open={leaveDialogOpen}
          onOpenChange={setLeaveDialogOpen}
          workspaceName={currentWorkspace.name}
          workspaceId={currentWorkspace.id}
          memberId={currentSelfMemberId}
        />
      )}
    </>
  );
});
