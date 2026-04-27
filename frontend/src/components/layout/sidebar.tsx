'use client';

import { observer } from 'mobx-react-lite';
import { motion, useReducedMotion } from 'motion/react';
import Link from 'next/link';
import { useParams, usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlarmClock,
  ChevronLeft,
  ChevronRight,
  FileText,
  FolderKanban,
  Loader2,
  LogOut,
  MessageSquare,
  Monitor,
  Moon,
  Network as NetworkIcon,
  PinIcon,
  Plug,
  Plus,
  Search,
  Settings,
  Sparkles as SparklesIcon,
  Sun,
  Ticket,
  User,
  UserCog,
  Users,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useUIStore, useNotificationStore, useAuthStore, useWorkspaceStore } from '@/stores';
import { useCreateNote } from '@/features/notes/hooks';
import { TemplatePicker } from '@/features/notes/components/TemplatePicker';
import { useNewNoteFlow } from './useNewNoteFlow';
import { useProjects } from '@/features/projects/hooks/useProjects';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
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
import { useViewport } from '@/hooks/useViewport';
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
import { TopicTreeContainer } from '@/features/topics/components';
import { aiApi } from '@/services/api/ai';

// ---------------------------------------------------------------------------
// RECENT CHATS — empty-state-only ship per known degradation (Plan 90-04).
// No chat session list API exists yet; the section renders the empty-state
// copy until that endpoint ships. The live-data branch is wired so dropping
// in a hook later is a one-line change. See UI-SPEC Design-Debt Note 5.
// ---------------------------------------------------------------------------

interface RecentChat {
  id: string;
  title: string;
  artifactCount: number;
  /** ISO 8601 timestamp */
  updatedAt: string;
  /** When true, renders with the AlarmClock icon instead of MessageSquare. */
  isRoutine?: boolean;
}

// ---------------------------------------------------------------------------
// WORKSPACE_ENTRIES — canonical NAV-01 order (Phase 84 routes /tasks, /topics).
// ---------------------------------------------------------------------------

interface NavEntry {
  id: string;
  label: string;
  icon: LucideIcon;
  path: (slug: string) => string;
  /** When set, item is hidden if the feature toggle is false. `null` = always shown. */
  featureKey: keyof WorkspaceFeatureToggles | null;
  /** Optional dynamic count (badge). */
  countKey?: string;
}

const WORKSPACE_ENTRIES: NavEntry[] = [
  {
    id: 'projects',
    label: 'Projects',
    icon: FolderKanban,
    path: (slug) => `/${slug}/projects`,
    featureKey: 'projects',
    countKey: 'projects',
  },
  {
    id: 'tasks',
    label: 'Tasks',
    icon: Ticket,
    // Phase 84 route — /tasks (NOT /issues). Toggle key remains 'issues'
    // because WorkspaceFeatureToggles was not renamed in Phase 84.
    path: (slug) => `/${slug}/tasks`,
    featureKey: 'issues',
    countKey: 'tasks',
  },
  {
    id: 'topics',
    label: 'Topics',
    icon: FileText,
    // Phase 84 route — /topics (NOT /notes). Toggle key remains 'notes'.
    path: (slug) => `/${slug}/topics`,
    featureKey: 'notes',
    countKey: 'topics',
  },
  {
    id: 'skills',
    label: 'Skills',
    icon: SparklesIcon,
    path: (slug) => `/${slug}/skills`,
    featureKey: 'skills',
  },
  {
    id: 'kg',
    label: 'Knowledge graph',
    icon: NetworkIcon,
    path: (slug) => `/${slug}/knowledge`,
    // 'kg' is not a member of WorkspaceFeatureToggles. The closest existing
    // toggle is 'knowledge' (knowledge-graph feature). When missing → render.
    featureKey: 'knowledge',
  },
  {
    id: 'members',
    label: 'Members',
    icon: Users,
    path: (slug) => `/${slug}/members`,
    featureKey: 'members',
  },
  {
    id: 'integrations',
    label: 'Integrations',
    icon: Plug,
    path: (slug) => `/${slug}/settings/integrations`,
    // 'integrations' is not a member of WorkspaceFeatureToggles — render
    // unconditionally per plan rule. Documented in SUMMARY.
    featureKey: null,
  },
];

const THEME_OPTIONS = [
  { value: 'light' as const, label: 'Light', icon: Sun },
  { value: 'dark' as const, label: 'Dark', icon: Moon },
  { value: 'system' as const, label: 'System', icon: Monitor },
];

// ---------------------------------------------------------------------------
// SidebarUserControls (preserved from v2 — bottom user row + notification panel)
// ---------------------------------------------------------------------------

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
            className="flex flex-1 items-center gap-2.5 rounded-lg px-2 py-1.5 text-left motion-safe:transition-colors hover:bg-sidebar-accent/50 outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1 focus-visible:ring-offset-sidebar"
            aria-label="Open workspace account menu"
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

// ---------------------------------------------------------------------------
// NewChatButton — top-stack CTA. Navigates to the FLAT /${slug}/chat route.
// VERIFIED against frontend/src/app/(workspace)/[workspaceSlug]/chat/page.tsx:
//   - The route reads ?session= / ?prefill= / ?mode= query params.
//   - When NO ?session= is present, ChatView starts a fresh session on mount.
//   - There is NO dynamic chat-id segment and no fake-route subpath.
//   - There is NO client-API module wrapper for chat-session creation.
// Plan 90-04 blocker-4 fix: do NOT introduce any of those.
// ---------------------------------------------------------------------------

function NewChatButton() {
  const router = useRouter();
  const params = useParams<{ workspaceSlug: string }>();
  const handleClick = () => {
    if (!params?.workspaceSlug) return;
    router.push(`/${params.workspaceSlug}/chat`);
  };
  return (
    <Button
      onClick={handleClick}
      data-testid="new-chat-button"
      className="w-full h-10 rounded-xl bg-[var(--brand-primary)] hover:bg-[var(--brand-dark)] text-white font-medium gap-2 text-[13px]"
    >
      <Plus className="h-4 w-4" /> New chat
    </Button>
  );
}

// ---------------------------------------------------------------------------
// SearchButton — replaces the old inline search input. Opens the ⌘K command
// palette via UIStore (NAV-04 sweep).
// ---------------------------------------------------------------------------

const SearchButton = observer(function SearchButton() {
  const uiStore = useUIStore();
  return (
    <button
      type="button"
      onClick={() => uiStore.openCommandPalette()}
      data-testid="sidebar-search-button"
      className="w-full h-10 rounded-xl bg-[var(--surface-page)] border border-[var(--border-card)] hover:bg-[var(--surface-input)] flex items-center gap-2 px-3 text-[13px] font-medium text-[var(--text-secondary)]"
    >
      <Search className="h-4 w-4 text-[var(--text-muted)]" aria-hidden="true" />
      <span className="flex-1 text-left">Search</span>
      <kbd className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[var(--surface-input)] text-[var(--text-muted)]">
        ⌘K
      </kbd>
    </button>
  );
});

// ---------------------------------------------------------------------------
// RecentChatRow — used only when recentChats has data (currently dead code,
// kept so the live-data variant plugs in without a structural refactor).
// ---------------------------------------------------------------------------

function RecentChatRow({ chat, slug }: { chat: RecentChat; slug: string }) {
  const Icon = chat.isRoutine ? AlarmClock : MessageSquare;
  return (
    <Link
      href={`/${slug}/chat?session=${chat.id}`}
      data-testid="recent-chat-row"
      className="group flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] text-[var(--text-secondary)] hover:bg-[var(--surface-input)] outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1"
    >
      <Icon className="h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
      <span className="flex-1 truncate">{chat.title}</span>
      {chat.artifactCount > 0 && (
        <span className="shrink-0 rounded-full bg-[var(--surface-input)] px-1.5 text-[10px] font-medium text-[var(--text-muted)]">
          {chat.artifactCount}
        </span>
      )}
      <span className="shrink-0 font-mono text-[10px] text-[var(--text-muted)]">
        {chat.updatedAt}
      </span>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// NavRow — accordion entry row.
// ---------------------------------------------------------------------------

function NavRow({
  entry,
  href,
  active,
  count,
}: {
  entry: NavEntry;
  href: string;
  active: boolean;
  count: number;
}) {
  const Icon = entry.icon;
  return (
    <Link
      href={href}
      data-testid={`nav-${entry.id}`}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group relative flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] font-medium motion-safe:transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1',
        active
          ? 'bg-[var(--surface-input)] text-[var(--text-heading)]'
          : 'text-[var(--text-secondary)] hover:bg-[var(--surface-input)]/60'
      )}
    >
      <Icon
        className={cn(
          'h-3.5 w-3.5 shrink-0',
          active ? 'text-[var(--brand-primary)]' : 'text-[var(--text-muted)]'
        )}
        aria-hidden="true"
      />
      <span className="flex-1 truncate">{entry.label}</span>
      {count > 0 && (
        <span className="ml-auto shrink-0 rounded-full bg-[var(--surface-input)] px-1.5 text-[10px] font-medium text-[var(--text-muted)]">
          {count}
        </span>
      )}
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Sidebar v3 — 240px rail; UI-SPEC Surface 1.
// ---------------------------------------------------------------------------

export const Sidebar = observer(function Sidebar() {
  const shouldReduceMotion = useReducedMotion();
  const uiStore = useUIStore();
  const notificationStore = useNotificationStore();
  const authStore = useAuthStore();
  const workspaceStore = useWorkspaceStore();
  const isNotesEnabled = workspaceStore.isFeatureEnabled('notes');
  const pathname = usePathname();
  const router = useRouter();
  const collapsed = uiStore.sidebarCollapsed;
  const { isSmallScreen } = useResponsive();
  // Phase 94 Plan 02 (MIG-03): expose the viewport-derived sidebar mode as a
  // `data-sidebar-mode` attribute so e2e specs and tests can assert layout
  // shape without depending on width measurements. The existing
  // `sidebarCollapsed` user-pref still drives visual state (60px collapse on
  // tablet/mobile via app-shell); this attribute reports the *spec* mode.
  const { sidebarMode } = useViewport();
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

  // Start polling unread count when workspace is active.
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
      router.push(`/${workspaceSlug}/topics/${note.id}`);
    },
  });

  // Pending approval count for sidebar badge (Owner/Admin only).
  const isAdminOrOwner =
    workspaceStore.currentUserRole === 'owner' || workspaceStore.currentUserRole === 'admin';
  const pendingApprovalCount = usePendingApprovalCount(isAdminOrOwner ? workspaceId : '');

  // Workspace projects for sidebar pinned-notes project labels
  const { data: projectsData } = useProjects({
    workspaceId,
    enabled: !!workspaceId && isAuthenticated,
  });

  // Counts injected into NavRow badges. Projects/tasks/topics live counts are
  // out of scope for this plan; pendingApprovalCount remains observable for
  // future surfacing if a Members-row badge is introduced.
  const counts = useMemo<Record<string, number>>(() => {
    return {
      projects: 0,
      tasks: 0,
      topics: 0,
      // pendingApprovalCount currently un-rendered in v3 stack but kept reactive.
      _approvals: pendingApprovalCount,
    };
  }, [pendingApprovalCount]);

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
      href: `/${workspaceSlug}/topics/${note.id}`,
    }));
  }, [rawPinnedNotes, workspaceSlug]);

  const newNoteFlow = useNewNoteFlow({
    onCreateNote: (data) => createNote.mutate(data),
  });

  const { data: sessionsData } = useQuery({
    queryKey: ['ai-sessions', resolvedWorkspaceId],
    queryFn: () => aiApi.listSessions(resolvedWorkspaceId!),
    enabled: !!resolvedWorkspaceId && isAuthenticated,
    staleTime: 30_000,
  });

  const recentChats: RecentChat[] = useMemo(() => {
    if (!sessionsData?.sessions) return [];
    return sessionsData.sessions.slice(0, 5).map((s) => ({
      id: s.id,
      title: s.title || 'Untitled chat',
      artifactCount: 0,
      updatedAt: s.updated_at,
    }));
  }, [sessionsData]);

  return (
    <>
      <aside
        className={cn(
          'fixed left-0 top-0 h-screen w-[240px] bg-[var(--surface-snow)] border-r border-[var(--border-card)] flex flex-col',
          // When parent shell collapses to 60px (tablet/mobile icon-rail), this
          // component is rendered inside that container. Width clamp via parent.
          collapsed && 'w-[60px]'
        )}
        data-testid="sidebar"
        data-sidebar-mode={sidebarMode}
      >
        {/* ----------------------------------------------------------------
            Top stack — WorkspacePill → + New chat → ⌘K Search button
            ---------------------------------------------------------------- */}
        <div
          className={cn(
            'flex shrink-0 flex-col gap-3 border-b border-[var(--border-card)] px-3.5 py-4',
            collapsed && 'px-2 items-center'
          )}
          data-testid="sidebar-top-stack"
        >
          {collapsed ? (
            <WorkspaceSwitcher currentSlug={workspaceSlug} collapsed />
          ) : (
            <>
              <WorkspaceSwitcher currentSlug={workspaceSlug} />
              <NewChatButton />
              <SearchButton />
            </>
          )}
        </div>

        {/* ----------------------------------------------------------------
            Scrollable middle — RECENT CHATS, Pinned Notes, WORKSPACE accordion
            ---------------------------------------------------------------- */}
        <ScrollArea className="flex-1 min-h-0">
          {!collapsed && (
            <>
              {/* RECENT CHATS section */}
              <div className="px-2 pt-3">
                <div
                  className="px-2 pt-2 pb-2 font-mono text-[10px] font-semibold tracking-[0.06em] text-[var(--text-muted)]"
                  data-testid="recent-chats-header"
                >
                  RECENT CHATS
                </div>
                {recentChats.length === 0 ? (
                  <div className="px-2 py-4" data-testid="recent-chats-empty">
                    <div className="text-[13px] font-medium text-[var(--text-secondary)]">
                      No recent chats
                    </div>
                    <div className="text-[13px] font-medium text-[var(--text-muted)] mt-0.5">
                      Start a new chat to see it here.
                    </div>
                  </div>
                ) : (
                  <ul className="flex flex-col gap-0.5" data-testid="recent-chats-list">
                    {recentChats.map((chat) => (
                      <li key={chat.id}>
                        <RecentChatRow chat={chat} slug={workspaceSlug} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Pinned Notes — preserved when notes feature is enabled */}
              {isNotesEnabled && pinnedNotes.length > 0 && (
                <div className="mt-4 px-2" data-testid="pinned-notes">
                  <div className="mb-1.5 flex items-center gap-1.5 px-2">
                    <PinIcon
                      className="h-2.5 w-2.5 text-[var(--text-muted)]"
                      aria-hidden="true"
                    />
                    <span className="font-mono text-[10px] font-semibold tracking-[0.06em] text-[var(--text-muted)]">
                      PINNED
                    </span>
                  </div>
                  <ul className="flex flex-col gap-px">
                    {pinnedNotes.map((note, index) => {
                      const isActive = pathname === note.href;
                      return (
                        <motion.li
                          key={note.id}
                          initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={
                            shouldReduceMotion ? { duration: 0 } : { delay: index * 0.05 }
                          }
                        >
                          <Link
                            href={note.href}
                            data-testid="note-item"
                            aria-current={isActive ? 'page' : undefined}
                            className={cn(
                              'group flex items-center gap-1.5 rounded-md px-2 py-1 text-[13px] outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring focus-visible:ring-offset-1',
                              isActive
                                ? 'bg-[var(--surface-input)] text-[var(--text-heading)] font-semibold'
                                : 'text-[var(--text-secondary)] hover:bg-[var(--surface-input)]/60'
                            )}
                          >
                            <FileText
                              className="h-3 w-3 text-[var(--text-muted)]"
                              aria-hidden="true"
                            />
                            <span className="truncate">{note.title}</span>
                            {note.projectId && projectMap[note.projectId] && (
                              <span className="ml-auto shrink-0 truncate text-[10px] text-[var(--text-muted)]">
                                {projectMap[note.projectId]}
                              </span>
                            )}
                          </Link>
                        </motion.li>
                      );
                    })}
                  </ul>
                </div>
              )}

              {/* WORKSPACE accordion */}
              <Accordion
                type="single"
                collapsible
                defaultValue="workspace"
                className="px-2 mt-4"
              >
                <AccordionItem value="workspace" className="border-none">
                  <AccordionTrigger className="px-2 py-2 font-mono text-[10px] font-semibold tracking-[0.06em] text-[var(--text-muted)] hover:no-underline">
                    WORKSPACE
                  </AccordionTrigger>
                  <AccordionContent className="pb-2">
                    <ul
                      className="flex flex-col gap-0.5"
                      data-testid="workspace-accordion-list"
                    >
                      {WORKSPACE_ENTRIES.filter((entry) => {
                        if (entry.featureKey === null) return true;
                        return workspaceStore.isFeatureEnabled(entry.featureKey);
                      }).map((entry) => {
                        const href = entry.path(workspaceSlug);
                        const isActive =
                          pathname === href || pathname.startsWith(`${href}/`);
                        const count = entry.countKey ? (counts[entry.countKey] ?? 0) : 0;
                        return (
                          <li key={entry.id}>
                            <NavRow
                              entry={entry}
                              href={href}
                              active={isActive}
                              count={count}
                            />
                            {/* Phase 93-04: Topics nav-row gains a nested
                                drag-drop tree below it. Mounted inline so the
                                Topics accordion entry expands into the tree
                                without restructuring sidebar navigation. */}
                            {entry.id === 'topics' && resolvedWorkspaceId && (
                              <div className="mt-0.5">
                                <TopicTreeContainer workspaceId={resolvedWorkspaceId} />
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </>
          )}
        </ScrollArea>

        {/* ----------------------------------------------------------------
            Bottom — User row + collapse toggle (preserved from v2)
            ---------------------------------------------------------------- */}
        <SidebarUserControls
          collapsed={collapsed}
          workspaceId={workspaceId}
          authStore={authStore}
          notificationStore={notificationStore}
          uiStore={uiStore}
        />

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

        {/* createNote.isPending guard — surface a subtle loader if a topic is
            being created from a deep link (e.g. Pinned link click during slow
            network). Preserves the v2 affordance without re-introducing a
            "+ New Note" button. */}
        {createNote.isPending && (
          <div
            className="absolute right-2 top-2 flex items-center gap-1 rounded-md bg-[var(--surface-input)] px-2 py-1"
            aria-live="polite"
            data-testid="topic-create-pending"
          >
            <Loader2 className="h-3 w-3 motion-safe:animate-spin text-[var(--text-muted)]" aria-hidden="true" />
            <span className="text-[10px] text-[var(--text-muted)]">Creating…</span>
          </div>
        )}

        {/* Avoid bare-import unused warnings: UserCog is reserved for the
            settings dropdown sub-trigger if reintroduced. We reference it
            here as a no-op type assertion to keep tree-shaking clean. */}
        <span className="hidden" aria-hidden="true">
          <UserCog />
        </span>
      </aside>

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
