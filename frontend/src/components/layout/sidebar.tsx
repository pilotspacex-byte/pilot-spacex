'use client';

import { observer } from 'mobx-react-lite';
import { motion, useReducedMotion } from 'motion/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Home,
  FileText,
  Users,
  DollarSign,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Plus,
  Compass,
  Loader2,
  LogOut,
  User,
  Sparkles,
  X,
  Sun,
  Moon,
  Monitor,
  CheckCircle2,
  Brain,
  Zap,
  CircleDot,
  Folder,
  MessageSquare,
  Search,
  Plug,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useUIStore, useNotificationStore, useAuthStore, useWorkspaceStore } from '@/stores';
import { useCreateNote } from '@/features/notes/hooks';
import { TemplatePicker } from '@/features/notes/components/TemplatePicker';
import { useNewNoteFlow } from './useNewNoteFlow';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
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
import { getAIStore } from '@/stores/ai/AIStore';
import { SessionListStore } from '@/stores/ai/SessionListStore';
import type { SessionSummary } from '@/stores/ai/SessionListStore';
import { useSettingsModal } from '@/features/settings/settings-modal-context';
import type { WorkspaceFeatureToggles } from '@/types';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * Shared shape for any navigable item in the sidebar — primary nav, the WORKSPACE
 * accordion children, and (internally) the collapsed-rail rendering all use this.
 */
interface NavItem {
  name: string;
  /** Path segment appended to `/${workspaceSlug}/`. Use `''` for Home. */
  path: string;
  /** Fully resolved href (computed from workspaceSlug + path). */
  href: string;
  icon: LucideIcon;
  testId: string;
  /** Accent color class for the icon when not active (per v3 spec). */
  accentClass?: string;
  /** Show a numeric badge when value > 0. Value is injected at render time. */
  badgeKey?: string;
  /** When true, hidden from non-Owner/Admin members. */
  adminOnly?: boolean;
  /** Maps to a WorkspaceFeatureToggles key. Hidden when the feature is disabled. */
  featureKey?: keyof WorkspaceFeatureToggles;
}

type NavItemDef = Omit<NavItem, 'href'>;

// -----------------------------------------------------------------------------
// Static config (declared outside the component so references stay stable)
// -----------------------------------------------------------------------------

/**
 * Primary nav rendered above the WORKSPACE accordion.
 * v3.1: Home + Pilot AI are replaced by the prominent "+ New chat" CTA
 * rendered outside this list. Keep the array empty so the existing NavLink
 * loop is a no-op without restructuring render logic.
 */
const PRIMARY_NAV: readonly NavItemDef[] = [] as const;

/**
 * WORKSPACE accordion group — grouped domain nav collapsed by default.
 * Integrations routes to the settings sub-page per Phase 2 plan.
 */
const WORKSPACE_NAV: readonly NavItemDef[] = [
  {
    name: 'Projects',
    path: 'projects',
    icon: Folder,
    testId: 'nav-projects',
    featureKey: 'projects',
  },
  {
    name: 'Issues',
    path: 'issues',
    icon: CircleDot,
    testId: 'nav-issues',
    featureKey: 'issues',
  },
  {
    name: 'Notes',
    path: 'notes',
    icon: FileText,
    testId: 'nav-notes',
    featureKey: 'notes',
  },
  {
    name: 'Skills',
    path: 'skills',
    icon: Zap,
    testId: 'nav-skills',
    accentClass: 'text-amber-500',
    featureKey: 'skills',
  },
  {
    name: 'Knowledge Graph',
    path: 'knowledge',
    icon: Brain,
    testId: 'nav-knowledge',
    accentClass: 'text-purple-500',
    featureKey: 'knowledge',
  },
  {
    name: 'Members',
    path: 'members',
    icon: Users,
    testId: 'nav-members',
    featureKey: 'members',
  },
  {
    name: 'Integrations',
    path: 'settings/integrations',
    icon: Plug,
    testId: 'nav-integrations',
  },
] as const;

/**
 * AI-scoped utilities. Kept for Owners/Admins and feature-gated.
 */
const AI_NAV: readonly NavItemDef[] = [
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
] as const;

const THEME_OPTIONS = [
  { value: 'light' as const, label: 'Light', icon: Sun },
  { value: 'dark' as const, label: 'Dark', icon: Moon },
  { value: 'system' as const, label: 'System', icon: Monitor },
];

// -----------------------------------------------------------------------------
// SidebarUserControls (unchanged export — re-used by tests)
// -----------------------------------------------------------------------------

export const SidebarUserControls = observer(function SidebarUserControls({
  collapsed,
  workspaceId,
  authStore,
  notificationStore,
  uiStore,
  workspaceStore,
}: {
  collapsed: boolean;
  workspaceId: string;
  authStore: AuthStore;
  notificationStore: NotificationStore;
  uiStore: UIStore;
  workspaceStore: { isOwner: boolean; isAdmin: boolean };
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
              <p className="text-sm font-medium text-sidebar-foreground truncate">{displayName}</p>
            </div>
            <Settings className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
          </button>
        </DropdownMenuTrigger>
        {dropdownContent}
      </DropdownMenu>
    </div>
  );
});

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function getWorkspaceSlugFromPathname(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0] ?? '';
  if (['login', 'callback', 'signup'].includes(firstSegment)) {
    return '';
  }
  return firstSegment;
}

function isPathActive(pathname: string, href: string): boolean {
  if (!href) return false;
  return pathname === href || pathname.startsWith(`${href}/`);
}

// -----------------------------------------------------------------------------
// NavLink — single nav row shared by primary nav and accordion children
// -----------------------------------------------------------------------------

interface NavLinkProps {
  item: NavItem;
  collapsed: boolean;
  isActive: boolean;
  badgeCount: number;
  /** Tighter paddings for rows inside the WORKSPACE accordion. */
  dense?: boolean;
}

function NavLink({ item, collapsed, isActive, badgeCount, dense }: NavLinkProps) {
  const shouldReduceMotion = useReducedMotion();
  const Icon = item.icon;

  return (
    <Tooltip delayDuration={collapsed ? 0 : 1000}>
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
            'group relative flex items-center gap-2 rounded-lg text-xs font-medium transition-colors duration-200 outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar',
            dense ? 'px-2 py-1' : 'px-2.5 py-1.5',
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
          <Icon
            className={cn(
              'h-4 w-4 shrink-0 transition-colors',
              isActive
                ? 'text-sidebar-primary'
                : item.accentClass ?? 'text-muted-foreground group-hover:text-sidebar-foreground'
            )}
            aria-hidden="true"
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
          {collapsed && badgeCount > 0 && (
            <span
              className="absolute top-0.5 right-0.5 h-1.5 w-1.5 rounded-full bg-primary"
              aria-hidden="true"
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
}

// -----------------------------------------------------------------------------
// Search button — opens the global Command Palette (⌘K). Not an input.
// -----------------------------------------------------------------------------

interface SearchButtonProps {
  collapsed: boolean;
  onOpen: () => void;
}

function SearchButton({ collapsed, onOpen }: SearchButtonProps) {
  if (collapsed) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Search"
            onClick={onOpen}
            data-testid="nav-search"
            className="h-9 w-9 text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
          >
            <Search className="h-4 w-4" aria-hidden="true" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">Search (⌘K)</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <button
      type="button"
      aria-label="Search"
      onClick={onOpen}
      data-testid="nav-search"
      className={cn(
        'group flex h-9 w-full items-center gap-2 rounded-lg border border-sidebar-border bg-sidebar px-2.5 text-xs',
        'text-muted-foreground transition-colors',
        'hover:bg-sidebar-accent/50 hover:text-sidebar-foreground',
        'outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar'
      )}
    >
      <Search className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span className="flex-1 text-left">Search…</span>
      <kbd
        className="ml-auto hidden shrink-0 items-center gap-0.5 rounded border border-sidebar-border bg-muted px-1.5 py-0.5 font-mono text-[10px] font-semibold text-muted-foreground sm:inline-flex"
        aria-hidden="true"
      >
        ⌘K
      </kbd>
    </button>
  );
}

// -----------------------------------------------------------------------------
// Sidebar
// -----------------------------------------------------------------------------

export const Sidebar = observer(function Sidebar() {
  const shouldReduceMotion = useReducedMotion();
  const uiStore = useUIStore();
  const notificationStore = useNotificationStore();
  const authStore = useAuthStore();
  const workspaceStore = useWorkspaceStore();
  const canCreateContent = workspaceStore.currentUserRole !== 'guest';
  const isNotesEnabled = workspaceStore.isFeatureEnabled('notes');
  const pathname = usePathname();
  const router = useRouter();
  const collapsed = uiStore.sidebarCollapsed;
  const { isSmallScreen } = useResponsive();
  const prevPathnameRef = useRef(pathname);

  // Persisted accordion state — expanded by default per v3 spec screen 4.14.
  const [workspaceExpanded, setWorkspaceExpanded] = useState(true);

  // Auto-close sidebar on mobile when navigating
  useEffect(() => {
    if (isSmallScreen && prevPathnameRef.current !== pathname && !uiStore.sidebarCollapsed) {
      uiStore.setSidebarCollapsed(true);
    }
    prevPathnameRef.current = pathname;
  }, [pathname, isSmallScreen, uiStore]);

  // Derive workspace slug/id from the URL (not the store) so deep-links work on first paint.
  const workspaceSlug = getWorkspaceSlugFromPathname(pathname);
  const workspaceId =
    workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id ??
    workspaceStore.currentWorkspaceId ??
    workspaceSlug;
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const resolvedWorkspaceId = UUID_RE.test(workspaceId) ? workspaceId : undefined;

  useEffect(() => {
    if (workspaceSlug) {
      addRecentWorkspace(workspaceSlug);
    }
  }, [workspaceSlug]);

  const isAuthenticated = authStore.isAuthenticated;

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

  const isAdminOrOwner =
    workspaceStore.currentUserRole === 'owner' || workspaceStore.currentUserRole === 'admin';
  const pendingApprovalCount = usePendingApprovalCount(isAdminOrOwner ? workspaceId : '');

  const badgeValues: Record<string, number> = useMemo(
    () => ({
      pendingApprovals: pendingApprovalCount,
      dashboardAttention: 0,
    }),
    [pendingApprovalCount]
  );

  // Feature + admin gate for any nav-item group.
  const filterVisible = useCallback(
    (items: readonly NavItemDef[]): NavItem[] =>
      items
        .filter((item) => {
          if (item.featureKey && !workspaceStore.isFeatureEnabled(item.featureKey)) return false;
          if (item.adminOnly && !isAdminOrOwner) return false;
          return true;
        })
        .map((item) => ({
          ...item,
          href: item.path ? `/${workspaceSlug}/${item.path}` : `/${workspaceSlug}`,
        })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [workspaceSlug, workspaceStore.featureToggles, isAdminOrOwner]
  );

  const primaryItems = useMemo(() => filterVisible(PRIMARY_NAV), [filterVisible]);
  const workspaceItems = useMemo(() => filterVisible(WORKSPACE_NAV), [filterVisible]);
  const aiItems = useMemo(() => filterVisible(AI_NAV), [filterVisible]);

  // Recent chat sessions — lazy-load once on mount.
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([]);
  useEffect(() => {
    const aiStore = getAIStore();
    const pilotSpace = aiStore.pilotSpace;
    if (!pilotSpace) return;
    const sessionListStore = new SessionListStore(pilotSpace);
    sessionListStore
      .fetchSessions(5)
      .then(() => {
        setRecentSessions([...sessionListStore.sessions].slice(0, 5));
      })
      .catch(() => {
        /* non-fatal — empty recents is a valid state */
      });
  }, []);

  const newNoteFlow = useNewNoteFlow({
    onCreateNote: (data) => createNote.mutate(data),
  });
  const handleNewNote = newNoteFlow.open;

  const handleOpenCommandPalette = useCallback(() => {
    uiStore.openCommandPalette();
  }, [uiStore]);

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
            <Compass className="h-5 w-5 text-primary" aria-hidden="true" />
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

        {/* + New chat — primary CTA per v3.1 design. Creates a fresh AI session. */}
        <div className={cn('shrink-0 px-2 pt-2', collapsed && 'flex justify-center')}>
          <Tooltip delayDuration={collapsed ? 0 : 1000}>
            <TooltipTrigger asChild>
              <Button
                variant="default"
                size={collapsed ? 'icon' : 'sm'}
                data-testid="new-chat-button"
                aria-label={collapsed ? 'Start new chat' : undefined}
                onClick={() => router.push(`/${workspaceSlug}/chat?new=1`)}
                className={cn(
                  'shadow-warm-sm transition-[colors,box-shadow] duration-200',
                  'hover:shadow-warm-md',
                  collapsed ? 'h-9 w-9' : 'h-9 w-full justify-center rounded-full'
                )}
              >
                <Plus className={collapsed ? 'h-4 w-4' : 'h-3.5 w-3.5'} />
                {!collapsed && <span className="ml-1.5 text-[13px] font-medium">New chat</span>}
              </Button>
            </TooltipTrigger>
            {collapsed && <TooltipContent side="right">New chat</TooltipContent>}
          </Tooltip>
        </div>

        {/* Search — button (not input). Opens the global Command Palette. */}
        <div className={cn('shrink-0 px-2 pt-2', collapsed && 'flex justify-center')}>
          <SearchButton collapsed={collapsed} onOpen={handleOpenCommandPalette} />
        </div>

        {/* Scrollable area: primary nav + WORKSPACE accordion + recents + pinned */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="flex flex-col gap-0.5 p-2">
            {/* Primary nav — Home, Pilot AI */}
            <nav aria-label="Main navigation" className="flex flex-col gap-0.5">
              {primaryItems.map((item) => (
                <NavLink
                  key={item.name}
                  item={item}
                  collapsed={collapsed}
                  isActive={
                    item.path
                      ? isPathActive(pathname, item.href)
                      : pathname === item.href
                  }
                  badgeCount={item.badgeKey ? badgeValues[item.badgeKey] ?? 0 : 0}
                />
              ))}
            </nav>

            {/* WORKSPACE accordion — grouped domain nav. */}
            {workspaceItems.length > 0 && (
              <div className="mt-3">
                {collapsed ? (
                  // Collapsed rail: show children as a flat list (no accordion chrome).
                  <nav aria-label="Workspace navigation" className="flex flex-col gap-0.5">
                    <div
                      className="mx-auto mb-1.5 h-px w-4 rounded-full bg-sidebar-border"
                      aria-hidden="true"
                    />
                    {workspaceItems.map((item) => (
                      <NavLink
                        key={item.name}
                        item={item}
                        collapsed
                        isActive={isPathActive(pathname, item.href)}
                        badgeCount={item.badgeKey ? badgeValues[item.badgeKey] ?? 0 : 0}
                      />
                    ))}
                  </nav>
                ) : (
                  <Collapsible
                    open={workspaceExpanded}
                    onOpenChange={setWorkspaceExpanded}
                    data-testid="workspace-accordion"
                  >
                    <CollapsibleTrigger asChild>
                      <button
                        type="button"
                        className={cn(
                          'group flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left outline-none',
                          'transition-colors hover:bg-sidebar-accent/40',
                          'focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar'
                        )}
                        aria-expanded={workspaceExpanded}
                        aria-controls="workspace-accordion-content"
                        data-testid="workspace-accordion-trigger"
                      >
                        <ChevronDown
                          className={cn(
                            'h-3 w-3 shrink-0 text-sidebar-foreground/50 transition-transform duration-200',
                            !workspaceExpanded && '-rotate-90'
                          )}
                          aria-hidden="true"
                        />
                        <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                          Workspace
                        </span>
                      </button>
                    </CollapsibleTrigger>
                    <CollapsibleContent
                      id="workspace-accordion-content"
                      className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down"
                    >
                      <nav
                        aria-label="Workspace navigation"
                        className="mt-1 flex flex-col gap-0.5"
                      >
                        {workspaceItems.map((item) => (
                          <NavLink
                            key={item.name}
                            item={item}
                            collapsed={false}
                            isActive={isPathActive(pathname, item.href)}
                            badgeCount={item.badgeKey ? badgeValues[item.badgeKey] ?? 0 : 0}
                            dense
                          />
                        ))}
                      </nav>
                    </CollapsibleContent>
                  </Collapsible>
                )}
              </div>
            )}

            {/* v3.1: AI section (approvals + costs) relocated to Settings — no longer in primary sidebar nav. */}
          </div>

          <Separator className="mx-2" />

          {/* Recent chats — visible only when expanded. */}
          {!collapsed && recentSessions.length > 0 && (
            <div className="px-2 py-2" data-testid="recent-chats">
              <div className="mb-1.5 flex items-center gap-1.5 px-1.5">
                <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Recents
                </span>
              </div>
              <div className="space-y-px">
                {recentSessions.map((session, index) => {
                  const href = `/${workspaceSlug}/chat?session=${session.sessionId}`;
                  const isActive = pathname === href;
                  const noteCount =
                    session.contextHistory?.filter((c) => c.noteId).length ?? 0;
                  const issueCount =
                    session.contextHistory?.filter((c) => c.issueId).length ?? 0;
                  return (
                    <motion.div
                      key={session.sessionId}
                      initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={
                        shouldReduceMotion ? { duration: 0 } : { delay: index * 0.05 }
                      }
                    >
                      <Link
                        href={href}
                        data-testid="recent-chat-item"
                        aria-current={isActive ? 'page' : undefined}
                        className={cn(
                          'group relative flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar',
                          isActive
                            ? 'bg-sidebar-accent text-sidebar-primary font-semibold before:absolute before:left-0 before:top-1/2 before:-translate-y-1/2 before:h-3.5 before:w-[3px] before:rounded-full before:bg-primary'
                            : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                        )}
                      >
                        <MessageSquare
                          className="h-3 w-3 shrink-0 text-muted-foreground"
                          aria-hidden="true"
                        />
                        <span className="truncate">{session.title ?? 'Untitled chat'}</span>
                        {(noteCount > 0 || issueCount > 0) && (
                          <span className="ml-auto flex shrink-0 items-center gap-1 font-mono text-[10px] text-muted-foreground/60">
                            {noteCount > 0 && <span aria-label={`${noteCount} notes`}>📝{noteCount}</span>}
                            {issueCount > 0 && <span aria-label={`${issueCount} issues`}>🔗{issueCount}</span>}
                          </span>
                        )}
                      </Link>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          )}
        </ScrollArea>

        {/* v3.1: "+ New Note" CTA moved out of sidebar — new-note lives on /notes page toolbar. */}

        {/* Notification + User Controls */}
        <SidebarUserControls
          collapsed={collapsed}
          workspaceId={workspaceId}
          authStore={authStore}
          notificationStore={notificationStore}
          uiStore={uiStore}
          workspaceStore={workspaceStore}
        />

        {/* Collapse/Expand Toggle */}
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
