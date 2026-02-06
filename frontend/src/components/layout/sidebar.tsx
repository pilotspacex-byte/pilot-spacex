'use client';

import { observer } from 'mobx-react-lite';
import { motion } from 'motion/react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  Home,
  FileText,
  LayoutGrid,
  FolderKanban,
  Settings,
  ChevronLeft,
  ChevronRight,
  Plus,
  Compass,
  PinIcon,
  Clock,
  Loader2,
  Bell,
  LogOut,
  User,
  X,
} from 'lucide-react';
import { useUIStore, useNoteStore, useNotificationStore, useAuthStore } from '@/stores';
import { useCreateNote, createNoteDefaults } from '@/features/notes/hooks';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useResponsive } from '@/hooks/useMediaQuery';
import { cn } from '@/lib/utils';
import type { AuthStore } from '@/stores/AuthStore';
import type { NotificationStore } from '@/stores/NotificationStore';
import { addRecentWorkspace } from '@/components/workspace-selector';

const navigationItems = [
  { name: 'Home', path: '', icon: Home, testId: 'nav-home' },
  { name: 'Notes', path: 'notes', icon: FileText, testId: 'nav-notes' },
  { name: 'Issues', path: 'issues', icon: LayoutGrid, testId: 'nav-issues' },
  { name: 'Projects', path: 'projects', icon: FolderKanban, testId: 'nav-projects' },
];

/**
 * Small red dot indicator for unread notifications on user avatar
 */
const NotificationDot = () => (
  <span
    className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-destructive ring-2 ring-sidebar"
    aria-hidden="true"
    data-testid="notification-dot"
  />
);

/**
 * Claude iOS-inspired user card: single trigger with unified dropdown.
 * Consolidates notification bell, user avatar, profile, and settings.
 */
export const SidebarUserControls = observer(function SidebarUserControls({
  collapsed,
  workspaceSlug,
  authStore,
  notificationStore,
}: {
  collapsed: boolean;
  workspaceSlug: string;
  authStore: AuthStore;
  notificationStore: NotificationStore;
}) {
  const router = useRouter();

  const displayName = authStore.userDisplayName || 'User';
  const email = authStore.user?.email ?? '';
  const rawInitials = authStore.userInitials;
  const initials =
    rawInitials && rawInitials !== '??' ? rawInitials : displayName.charAt(0).toUpperCase();
  const hasUnread = notificationStore.unreadCount > 0;

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
      <DropdownMenuItem
        className="text-xs gap-2"
        onSelect={() => notificationStore.markAllAsRead()}
      >
        <Bell className="h-3.5 w-3.5" />
        Notifications
        {hasUnread && (
          <Badge variant="destructive" className="ml-auto h-4 min-w-4 px-1 text-[9px]">
            {notificationStore.unreadCount > 99 ? '99+' : notificationStore.unreadCount}
          </Badge>
        )}
      </DropdownMenuItem>
      <DropdownMenuItem
        className="text-xs gap-2"
        onSelect={() => router.push(`/${workspaceSlug}/settings/profile`)}
      >
        <User className="h-3.5 w-3.5" />
        Profile
      </DropdownMenuItem>
      <DropdownMenuItem
        className="text-xs gap-2"
        data-testid="nav-settings"
        onSelect={() => router.push(`/${workspaceSlug}/settings`)}
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
      <div className="flex items-center justify-center border-t border-sidebar-border p-1.5">
        <DropdownMenu>
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Account"
                  className="relative h-8 w-8 rounded-full"
                >
                  <Avatar className="h-6 w-6 border border-border">
                    <AvatarImage src={authStore.user?.avatarUrl ?? ''} alt="User" />
                    <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-medium">
                      {initials}
                    </AvatarFallback>
                  </Avatar>
                  {hasUnread && <NotificationDot />}
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
    <div className="border-t border-sidebar-border px-2 py-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-sidebar-accent/50"
            aria-label="Account"
          >
            <div className="relative shrink-0">
              <Avatar className="h-7 w-7 border border-border">
                <AvatarImage src={authStore.user?.avatarUrl ?? ''} alt="User" />
                <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-medium">
                  {initials}
                </AvatarFallback>
              </Avatar>
              {hasUnread && <NotificationDot />}
            </div>
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

/**
 * Extract workspace slug from pathname.
 * Pathname format: /{workspaceSlug}/... or /{workspaceSlug}
 */
function getWorkspaceSlugFromPathname(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0] ?? '';
  if (['login', 'callback', 'signup'].includes(firstSegment)) {
    return '';
  }
  return firstSegment;
}

export const Sidebar = observer(function Sidebar() {
  const uiStore = useUIStore();
  const noteStore = useNoteStore();
  const notificationStore = useNotificationStore();
  const authStore = useAuthStore();
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
  // Use slug as workspaceId for API calls (backend accepts both UUID and slug)
  const workspaceId = workspaceSlug;

  // Store workspace slug in localStorage for redirect on root URL
  useEffect(() => {
    if (workspaceSlug) {
      addRecentWorkspace(workspaceSlug);
    }
  }, [workspaceSlug]);

  const createNote = useCreateNote({
    workspaceId,
    onSuccess: (note) => {
      router.push(`/${workspaceSlug}/notes/${note.id}`);
    },
  });

  const navigation = useMemo(() => {
    return navigationItems.map((item) => ({
      ...item,
      href: item.path ? `/${workspaceSlug}/${item.path}` : `/${workspaceSlug}`,
    }));
  }, [workspaceSlug]);

  const pinnedNotes = useMemo(() => {
    return noteStore.pinnedNotes.slice(0, 5).map((note) => ({
      id: note.id,
      title: note.title,
      href: `/${workspaceSlug}/notes/${note.id}`,
    }));
  }, [noteStore.pinnedNotes, workspaceSlug]);

  const recentNotes = useMemo(() => {
    return noteStore.recentNotes
      .filter((note) => !noteStore.pinnedNotes.some((p) => p.id === note.id))
      .slice(0, 5)
      .map((note) => ({
        id: note.id,
        title: note.title,
        href: `/${workspaceSlug}/notes/${note.id}`,
      }));
  }, [noteStore.recentNotes, noteStore.pinnedNotes, workspaceSlug]);

  const handleNewNote = useCallback(() => {
    createNote.mutate(createNoteDefaults());
  }, [createNote]);

  return (
    <div className="flex h-full flex-col">
      {/* Logo & Workspace */}
      <div
        className={cn(
          'flex h-10 items-center gap-2 border-b border-sidebar-border',
          collapsed ? 'justify-center px-0' : 'px-3'
        )}
      >
        <motion.div
          whileHover={{ rotate: 15 }}
          transition={{ type: 'spring', stiffness: 400, damping: 10 }}
        >
          <Compass className="h-5 w-5 text-primary" />
        </motion.div>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="flex flex-col"
          >
            <span className="text-xs font-semibold text-sidebar-foreground">Pilot Space</span>
            <span className="text-[10px] text-muted-foreground">Workspace</span>
          </motion.div>
        )}
      </div>

      {/* Main Navigation */}
      <div className="flex flex-col gap-0.5 p-2">
        {navigation.map((item) => {
          // Use startsWith for non-home routes to highlight parent nav when on nested routes
          // e.g., /workspace/notes/123 should highlight "Notes" nav item
          const isActive = item.path ? pathname.startsWith(item.href) : pathname === item.href;
          return (
            <Tooltip key={item.name} delayDuration={collapsed ? 0 : 1000}>
              <TooltipTrigger asChild>
                <Link
                  href={item.href}
                  data-testid={item.testId}
                  className={cn(
                    'group flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all duration-200',
                    isActive
                      ? 'bg-sidebar-accent text-sidebar-primary shadow-warm-sm'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent/50',
                    collapsed && 'justify-center px-2'
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
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      {item.name}
                    </motion.span>
                  )}
                </Link>
              </TooltipTrigger>
              {collapsed && (
                <TooltipContent side="right" className="font-medium">
                  {item.name}
                </TooltipContent>
              )}
            </Tooltip>
          );
        })}
      </div>

      <Separator className="mx-2" />

      {/* Notes sections */}
      <ScrollArea className="flex-1 px-2 py-1.5">
        {!collapsed && (
          <>
            {/* Pinned Notes */}
            <div className="mb-3" data-testid="pinned-notes">
              <div className="mb-1.5 flex items-center gap-1.5 px-1.5">
                <PinIcon className="h-2.5 w-2.5 text-muted-foreground" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Pinned
                </span>
              </div>
              <div className="space-y-px">
                {pinnedNotes.map((note, index) => (
                  <motion.div
                    key={note.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <Link
                      href={note.href}
                      data-testid="note-item"
                      className="group flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-sidebar-foreground transition-colors hover:bg-sidebar-accent/50"
                    >
                      <FileText className="h-3 w-3 text-muted-foreground" />
                      <span className="truncate">{note.title}</span>
                    </Link>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Recent Notes */}
            <div data-testid="note-list">
              <div className="mb-1.5 flex items-center gap-1.5 px-1.5">
                <Clock className="h-2.5 w-2.5 text-muted-foreground" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Recent
                </span>
              </div>
              <div className="space-y-px">
                {recentNotes.map((note, index) => (
                  <motion.div
                    key={note.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 + 0.1 }}
                  >
                    <Link
                      href={note.href}
                      data-testid="note-item"
                      className="group flex items-center gap-1.5 rounded-md px-1.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                    >
                      <FileText className="h-3 w-3" />
                      <span className="truncate">{note.title}</span>
                    </Link>
                  </motion.div>
                ))}
              </div>
            </div>
          </>
        )}
      </ScrollArea>

      {/* New Note Button */}
      <div className={cn('border-t border-sidebar-border p-2', collapsed && 'flex justify-center')}>
        <Tooltip delayDuration={collapsed ? 0 : 1000}>
          <TooltipTrigger asChild>
            <Button
              variant="default"
              size={collapsed ? 'icon' : 'sm'}
              data-testid="new-note-button"
              onClick={handleNewNote}
              disabled={createNote.isPending}
              className={cn(
                'shadow-warm-sm transition-all duration-200',
                'hover:shadow-warm-md hover:-translate-y-0.5',
                collapsed ? 'h-8 w-8' : 'w-full'
              )}
            >
              {createNote.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
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

      {/* Notification + User Controls */}
      <SidebarUserControls
        collapsed={collapsed}
        workspaceSlug={workspaceSlug}
        authStore={authStore}
        notificationStore={notificationStore}
      />

      {/* Collapse Toggle — close button on mobile, chevron toggle on desktop */}
      <div className="border-t border-sidebar-border p-1.5">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                isSmallScreen ? uiStore.setSidebarCollapsed(true) : uiStore.toggleSidebar()
              }
              aria-label={
                isSmallScreen ? 'Close sidebar' : collapsed ? 'Expand sidebar' : 'Collapse sidebar'
              }
              className={cn(
                'h-6 w-full justify-center text-muted-foreground hover:text-sidebar-foreground',
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
  );
});
