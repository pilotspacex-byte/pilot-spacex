'use client';

import { observer } from 'mobx-react-lite';
import { motion, useReducedMotion } from 'motion/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef } from 'react';
import {
  Home,
  FileText,
  LayoutGrid,
  FolderKanban,
  Users,
  DollarSign,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
  Compass,
  PinIcon,
  Loader2,
  LogOut,
  User,
  UserCog,
  Sparkles,
  X,
  Sun,
  Moon,
  Monitor,
  CheckCircle2,
  Network,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useUIStore, useNotificationStore, useAuthStore, useWorkspaceStore } from '@/stores';
import { useCreateNote } from '@/features/notes/hooks';
import { TemplatePicker } from '@/features/notes/components/TemplatePicker';
import { useNewNoteFlow } from './useNewNoteFlow';
import { useProjects } from '@/features/projects/hooks/useProjects';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useResponsive } from '@/hooks/useMediaQuery';
import { cn } from '@/lib/utils';
import type { AuthStore } from '@/stores/AuthStore';
import type { NotificationStore } from '@/stores/NotificationStore';
import type { UIStore } from '@/stores/UIStore';
import { NotificationPanel } from '@/components/layout/notification-panel';
import { addRecentWorkspace } from '@/components/workspace-selector';
import { WorkspaceSwitcher } from '@/components/layout/workspace-switcher';
import { usePendingApprovalCount } from '@/features/approvals/hooks/use-approvals';
import { usePinnedNotes } from '@/hooks/usePinnedNotes';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import type { WorkspaceFeatureToggles } from '@/types';

interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon;
  testId: string;
  /** Show a numeric badge when value > 0. Value is injected at render time for dynamic counts. */
  badgeKey?: string;
  /** When true, hidden from non-Owner/Admin members. */
  adminOnly?: boolean;
  /** Maps to a WorkspaceFeatureToggles key. When set, item is hidden if the feature is disabled. */
  featureKey?: keyof WorkspaceFeatureToggles;
}

interface NavSection {
  label: string;
  icon?: LucideIcon;
  items: NavItem[];
}

const navigationSections: NavSection[] = [
  {
    label: 'Main',
    items: [
      { name: 'Home', path: '', icon: Home, testId: 'nav-home' },
      { name: 'Notes', path: 'notes', icon: FileText, testId: 'nav-notes', featureKey: 'notes' },
      { name: 'Issues', path: 'issues', icon: LayoutGrid, testId: 'nav-issues', featureKey: 'issues' },
      { name: 'Projects', path: 'projects', icon: FolderKanban, testId: 'nav-projects', featureKey: 'projects' },
      { name: 'Members', path: 'members', icon: Users, testId: 'nav-members', featureKey: 'members' },
      { name: 'Knowledge', path: 'knowledge', icon: Network, testId: 'nav-knowledge', featureKey: 'knowledge' },
    ],
  },
  {
    label: 'AI',
    icon: Sparkles,
    items: [
      { name: 'Skill', path: 'skills', icon: UserCog, testId: 'nav-roles', featureKey: 'skills' },
      { name: 'Costs', path: 'costs', icon: DollarSign, testId: 'nav-costs', featureKey: 'costs' },
      {
        name: 'Approvals',
        path: 'approvals',
        icon: CheckCircle2,
        testId: 'nav-approvals',
        badgeKey: 'pendingApprovals',
        adminOnly: true,
        featureKey: 'approvals',
      },
    ],
  },
];

const THEME_OPTIONS = [
  { value: 'light' as const, label: 'Light', icon: Sun },
  { value: 'dark' as const, label: 'Dark', icon: Moon },
  { value: 'system' as const, label: 'System', icon: Monitor },
];

export const SidebarUserControls = observer(function SidebarUserControls({
  collapsed,
  workspaceId,
  authStore,
  notificationStore,
  uiStore,
}: {
  collapsed: boolean;
  workspaceId: string;
  authStore: AuthStore;
  notificationStore: NotificationStore;
  uiStore: UIStore;
}) {
  const settingsModal = useSettingsModal();

  const displayName = authStore.userDisplayName || 'User';
  const email = authStore.user?.email ?? '';
  const rawInitials = authStore.userInitials;
  const initials =
    rawInitials && rawInitials !== '??' ? rawInitials : displayName.charAt(0).toUpperCase();

  const ThemeIcon = uiStore.theme === 'dark' ? Moon : uiStore.theme === 'light' ? Sun : Monitor;

  const dropdownContent = (
    <DropdownMenuContent side="right" align="end" className="w-56">
      <DropdownMenuLabel className="font-normal">
        <div className="flex items-center gap-2.5">
          <Avatar className="h-8 w-8 shrink-0 border border-border">
            <AvatarImage src={authStore.user?.avatarUrl ?? ''} alt="User" />
            <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="flex flex-col space-y-0.5 min-w-0">
            <p className="text-xs font-medium truncate">{displayName}</p>
            {email && <p className="text-[10px] text-muted-foreground truncate">{email}</p>}
          </div>
        </div>
      </DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuSub>
        <DropdownMenuSubTrigger className="text-xs gap-2">
          <ThemeIcon className="h-3.5 w-3.5" />
          Theme
        </DropdownMenuSubTrigger>
        <DropdownMenuSubContent>
          {THEME_OPTIONS.map((option) => (
            <DropdownMenuItem
              key={option.value}
              className={cn('text-xs gap-2', uiStore.theme === option.value && 'font-semibold')}
              onSelect={() => uiStore.setTheme(option.value)}
            >
              <option.icon className="h-3.5 w-3.5" />
              {option.label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuSubContent>
      </DropdownMenuSub>
      <DropdownMenuItem
        className="text-xs gap-2"
        onSelect={() => settingsModal.openSettings('profile')}
      >
        <User className="h-3.5 w-3.5" />
        Profile
      </DropdownMenuItem>
      <DropdownMenuItem
        className="text-xs gap-2"
        data-testid="nav-settings"
        onSelect={() => settingsModal.openSettings('general')}
      >
        <Settings className="h-3.5 w-3.5" />
        Settings
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem
        className="text-xs gap-2 text-destructive focus:text-destructive"
        onSelect={() => authStore.logout()}
      >
        <LogOut className="h-3.5 w-3.5" />
        Sign out
      </DropdownMenuItem>
    </DropdownMenuContent>
  );

  if (collapsed) {
    return (
      <div className="flex shrink-0 flex-col items-center gap-1.5 border-t border-sidebar-border p-2">
        <NotificationPanel store={notificationStore} workspaceId={workspaceId} collapsed />
        <DropdownMenu>
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Account"
                  className="relative h-10 w-10 rounded-full"
                >
                  <Avatar className="h-7 w-7 border border-border">
                    <AvatarImage src={authStore.user?.avatarUrl ?? ''} alt="User" />
                    <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-medium">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent side="right">Account</TooltipContent>
          </Tooltip>
          {dropdownContent}
        </DropdownMenu>
      </div>
    );
  }

  return (
    <div className="flex shrink-0 items-center gap-1 border-t border-sidebar-border px-2 py-2">
      <NotificationPanel store={notificationStore} workspaceId={workspaceId} />
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="flex flex-1 items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-sidebar-accent/50 outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar"
            aria-label="Account"
          >
            <Avatar className="h-7 w-7 shrink-0 border border-border">
              <AvatarImage src={authStore.user?.avatarUrl ?? ''} alt="User" />
              <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-medium">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-sidebar-foreground truncate">{displayName}</p>
            </div>
          </button>
        </DropdownMenuTrigger>
        {dropdownContent}
      </DropdownMenu>
    </div>
  );
});

function getWorkspaceSlugFromPathname(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0] ?? '';
  if (['login', 'callback', 'signup'].includes(firstSegment)) {
    return '';
  }
  return firstSegment;
}

export const Sidebar = observer(function Sidebar() {
  const shouldReduceMotion = useReducedMotion();
  const uiStore = useUIStore();
  const notificationStore = useNotificationStore();
  const authStore = useAuthStore();
  const workspaceStore = useWorkspaceStore();
  const canCreateContent = workspaceStore.currentUserRole !== 'guest';
  const pathname = usePathname();
  const router = useRouter();
  const collapsed = uiStore.sidebarCollapsed;
  const { isSmallScreen } = useResponsive();
  const prevPathnameRef = useRef(pathname);

  // Auto-close sidebar on mobile when navigating
  useEffect(() => {
    if (isSmallScreen && prevPathnameRef.current !== pathname && !uiStore.sidebarCollapsed) {
      uiStore.setSidebarCollapsed(true);
    }
    prevPathnameRef.current = pathname;
  }, [pathname, isSmallScreen, uiStore]);

  // Get workspace slug from URL pathname (not from store)
  const workspaceSlug = getWorkspaceSlugFromPathname(pathname);
  const workspaceId =
    workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id ??
    workspaceStore.currentWorkspaceId ??
    workspaceSlug;
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const resolvedWorkspaceId = UUID_RE.test(workspaceId) ? workspaceId : undefined;

  // Store workspace slug in localStorage for redirect on root URL
  useEffect(() => {
    if (workspaceSlug) {
      addRecentWorkspace(workspaceSlug);
    }
  }, [workspaceSlug]);

  const isAuthenticated = authStore.isAuthenticated;

  // Start polling unread count when workspace is active; stop on unmount or workspace change.
  // Only poll when workspaceId is a UUID (contains '-') to prevent spurious calls with slugs.
  useEffect(() => {
    if (workspaceId && isAuthenticated && workspaceId.includes('-')) {
      notificationStore.startPolling(workspaceId);
    }
    return () => {
      notificationStore.stopPolling();
    };
  }, [workspaceId, isAuthenticated, notificationStore]);

  const createNote = useCreateNote({
    workspaceId: resolvedWorkspaceId ?? '',
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

  // Pending approval count for sidebar badge (Owner/Admin only).
  // usePendingApprovalCount returns 0 when not authenticated or no data.
  const isAdminOrOwner =
    workspaceStore.currentUserRole === 'owner' || workspaceStore.currentUserRole === 'admin';
  const pendingApprovalCount = usePendingApprovalCount(isAdminOrOwner ? workspaceId : '');

  // Map badgeKey → dynamic badge value
  const badgeValues: Record<string, number> = {
    pendingApprovals: pendingApprovalCount,
  };

  // Workspace projects for sidebar tree sections
  const { data: projectsData } = useProjects({
    workspaceId,
    enabled: !!workspaceId && isAuthenticated,
  });

  const navigation = useMemo(() => {
    return navigationSections.map((section) => {
      const items = section.items
        .filter((item) => {
          // Hide items whose feature is disabled
          if (item.featureKey && !workspaceStore.isFeatureEnabled(item.featureKey)) {
            return false;
          }
          return true;
        })
        .map((item) => ({
          ...item,
          href: item.path ? `/${workspaceSlug}/${item.path}` : `/${workspaceSlug}`,
        }));
      return { label: section.label, icon: section.icon, items };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceSlug, workspaceStore.featureToggles]);

  const projectMap = useMemo(() => {
    const map: Record<string, string> = {};
    (projectsData?.items ?? []).forEach((p) => {
      map[p.id] = p.name;
    });
    return map;
  }, [projectsData]);

  const { data: rawPinnedNotes = [] } = usePinnedNotes({
    workspaceId: resolvedWorkspaceId ?? '',
    enabled: !!resolvedWorkspaceId && isAuthenticated,
  });

  const pinnedNotes = useMemo(() => {
    return rawPinnedNotes.slice(0, 5).map((note) => ({
      id: note.id,
      title: note.title,
      projectId: note.projectId,
      href: `/${workspaceSlug}/notes/${note.id}`,
    }));
  }, [rawPinnedNotes, workspaceSlug]);

  const newNoteFlow = useNewNoteFlow({
    onCreateNote: (data) => createNote.mutate(data),
  });
  const handleNewNote = newNoteFlow.open;

  return (
    <>
      <div className="flex h-full flex-col">
        {/* Logo & Workspace */}
        <div
          className={cn(
            'flex h-10 shrink-0 items-center gap-2 border-b border-sidebar-border',
            collapsed ? 'justify-center px-2' : 'px-3'
          )}
        >
          <motion.div
            whileHover={shouldReduceMotion ? undefined : { rotate: 15 }}
            transition={{ type: 'spring', stiffness: 400, damping: 10 }}
          >
            <Compass className="h-5 w-5 text-primary" />
          </motion.div>
          {collapsed ? (
            <WorkspaceSwitcher currentSlug={workspaceSlug} collapsed />
          ) : (
            <motion.div
              initial={shouldReduceMotion ? false : { opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={shouldReduceMotion ? undefined : { opacity: 0, x: -10 }}
              className="flex flex-1 flex-col min-w-0"
            >
              <WorkspaceSwitcher currentSlug={workspaceSlug} />
            </motion.div>
          )}
        </div>

        {/* Scrollable area: navigation + pinned notes */}
        <ScrollArea className="flex-1 min-h-0">
          {/* Main Navigation */}
          <div className="flex flex-col gap-0.5 p-2">
            {navigation.map((section, sectionIndex) => {
              // Compute visible items after adminOnly filtering
              const visibleItems = section.items.filter(
                (item) => !(item.adminOnly && !isAdminOrOwner)
              );
              // Hide section when no items are visible
              if (visibleItems.length === 0) return null;

              return (
                <nav
                  key={section.label}
                  aria-label={`${section.label} navigation`}
                  className={cn(sectionIndex > 0 && 'mt-3')}
                >
                  {!collapsed ? (
                    <div className="mb-1 flex items-center gap-1.5 px-2.5" aria-hidden="true">
                      {section.icon && (
                        <section.icon className="h-2.5 w-2.5 text-sidebar-foreground/40" />
                      )}
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
                        {section.label}
                      </span>
                    </div>
                  ) : (
                    sectionIndex > 0 && (
                      <div
                        className="mx-auto mb-1.5 h-px w-4 rounded-full bg-sidebar-border"
                        aria-hidden="true"
                      />
                    )
                  )}
                  {visibleItems.map((item) => {
                    const isActive = item.path
                      ? pathname === item.href || pathname.startsWith(`${item.href}/`)
                      : pathname === item.href;

                    const badgeCount =
                      item.badgeKey !== undefined ? (badgeValues[item.badgeKey] ?? 0) : 0;

                    return (
                      <Tooltip key={item.name} delayDuration={collapsed ? 0 : 1000}>
                        <TooltipTrigger asChild>
                          <Link
                            href={item.href}
                            data-testid={item.testId}
                            aria-current={isActive ? 'page' : undefined}
                            aria-label={
                              collapsed
                                ? badgeCount > 0
                                  ? `${item.name} (${badgeCount} pending)`
                                  : item.name
                                : undefined
                            }
                            className={cn(
                              'group relative flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar',
                              isActive
                                ? [
                                    'bg-sidebar-accent text-sidebar-primary font-semibold',
                                    !collapsed &&
                                      'before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-4 before:w-[3px] before:rounded-full before:bg-primary',
                                    collapsed &&
                                      'after:absolute after:bottom-0 after:left-1/2 after:-translate-x-1/2 after:h-[3px] after:w-3 after:rounded-full after:bg-primary',
                                  ]
                                : 'text-sidebar-foreground hover:bg-sidebar-accent/50',
                              collapsed && 'justify-center px-0 py-2'
                            )}
                          >
                            <item.icon
                              className={cn(
                                'h-4 w-4 shrink-0 transition-colors',
                                isActive
                                  ? 'text-sidebar-primary'
                                  : 'text-muted-foreground group-hover:text-sidebar-foreground'
                              )}
                            />
                            {!collapsed && (
                              <motion.span
                                initial={shouldReduceMotion ? false : { opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={shouldReduceMotion ? undefined : { opacity: 0 }}
                                className="flex flex-1 items-center justify-between"
                              >
                                {item.name}
                                {badgeCount > 0 && (
                                  <span
                                    className="ml-auto flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground"
                                    aria-label={`${badgeCount} pending`}
                                    data-testid={`${item.testId}-badge`}
                                  >
                                    {badgeCount}
                                  </span>
                                )}
                              </motion.span>
                            )}
                            {/* Collapsed badge dot */}
                            {collapsed && badgeCount > 0 && (
                              <span
                                className="absolute top-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-primary"
                                aria-hidden
                              />
                            )}
                          </Link>
                        </TooltipTrigger>
                        {collapsed && (
                          <TooltipContent side="right" className="font-medium">
                            {item.name}
                            {badgeCount > 0 && ` (${badgeCount} pending)`}
                          </TooltipContent>
                        )}
                      </Tooltip>
                    );
                  })}
                </nav>
              );
            })}
          </div>

          <Separator className="mx-2" />

          {/* Pinned Notes — inside scrollable area */}
          {!collapsed && (
            <div className="px-2 py-2">
              <div className="mb-4" data-testid="pinned-notes">
                <div className="mb-2 flex items-center gap-1.5 px-1.5">
                  <PinIcon className="h-2.5 w-2.5 text-muted-foreground" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Pinned
                  </span>
                </div>
                <div className="space-y-px">
                  {pinnedNotes.map((note, index) => {
                    const isActive = pathname === note.href;
                    return (
                      <motion.div
                        key={note.id}
                        initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={shouldReduceMotion ? { duration: 0 } : { delay: index * 0.05 }}
                      >
                        <Link
                          href={note.href}
                          data-testid="note-item"
                          aria-current={isActive ? 'page' : undefined}
                          className={cn(
                            'group relative flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar',
                            isActive
                              ? 'bg-sidebar-accent text-sidebar-primary font-semibold before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-3.5 before:w-[3px] before:rounded-full before:bg-primary'
                              : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                          )}
                        >
                          <FileText className="h-3 w-3 text-muted-foreground" />
                          <span className="truncate">{note.title}</span>
                          {note.projectId && projectMap[note.projectId] && (
                            <span className="ml-auto shrink-0 text-[10px] text-muted-foreground/60 truncate max-w-[80px]">
                              {projectMap[note.projectId]}
                            </span>
                          )}
                        </Link>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </ScrollArea>

        {/* New Note Button — hidden for guests */}
        {canCreateContent && (
          <div
            className={cn(
              'shrink-0 border-t border-sidebar-border p-2',
              collapsed && 'flex justify-center'
            )}
          >
            <Tooltip delayDuration={collapsed ? 0 : 1000}>
              <TooltipTrigger asChild>
                <Button
                  variant="default"
                  size={collapsed ? 'icon' : 'sm'}
                  data-testid="new-note-button"
                  aria-label={collapsed ? 'New Note' : undefined}
                  onClick={handleNewNote}
                  disabled={createNote.isPending || !resolvedWorkspaceId}
                  className={cn(
                    'shadow-warm-sm transition-[colors,box-shadow] duration-200',
                    'hover:shadow-warm-md',
                    collapsed ? 'h-9 w-9' : 'w-full'
                  )}
                >
                  {createNote.isPending ? (
                    <Loader2
                      className={cn(collapsed ? 'h-4 w-4' : 'h-3.5 w-3.5', 'animate-spin')}
                    />
                  ) : (
                    <Plus className={collapsed ? 'h-4 w-4' : 'h-3.5 w-3.5'} />
                  )}
                  {!collapsed && (
                    <span className="ml-1.5 text-xs">
                      {createNote.isPending ? 'Creating...' : 'New Note'}
                    </span>
                  )}
                </Button>
              </TooltipTrigger>
              {collapsed && <TooltipContent side="right">New Note</TooltipContent>}
            </Tooltip>
          </div>
        )}

        {/* Notification + User Controls */}
        <SidebarUserControls
          collapsed={collapsed}
          workspaceId={workspaceId}
          authStore={authStore}
          notificationStore={notificationStore}
          uiStore={uiStore}
        />

        {/* Collapse/Expand Toggle — always visible at bottom */}
        <div className="shrink-0 border-t border-sidebar-border p-2">
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  isSmallScreen ? uiStore.setSidebarCollapsed(true) : uiStore.toggleSidebar()
                }
                aria-label={
                  isSmallScreen
                    ? 'Close sidebar'
                    : collapsed
                      ? 'Expand sidebar'
                      : 'Collapse sidebar'
                }
                className={cn(
                  'h-8 w-full justify-center text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground',
                  collapsed && 'px-2'
                )}
              >
                {isSmallScreen ? (
                  <X className="h-3.5 w-3.5" />
                ) : collapsed ? (
                  <ChevronRight className="h-3.5 w-3.5" />
                ) : (
                  <ChevronLeft className="h-3.5 w-3.5" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side={collapsed ? 'right' : 'top'}>
              {isSmallScreen ? 'Close sidebar' : collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            </TooltipContent>
          </Tooltip>
        </div>
      </div>

      {newNoteFlow.showTemplatePicker && resolvedWorkspaceId && (
        <TemplatePicker
          workspaceId={resolvedWorkspaceId}
          isAdmin={isAdminOrOwner}
          onConfirm={newNoteFlow.handleTemplateConfirm}
          onClose={newNoteFlow.handleTemplateClose}
        />
      )}
    </>
  );
});
