'use client';

import { useEffect, useMemo, useRef } from 'react';
import { observer } from 'mobx-react-lite';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  MessageSquarePlus,
  FileText,
  LayoutGrid,
  FolderKanban,
  ChevronLeft,
  ChevronRight,
  X,
  MoreHorizontal,
  Trash2,
  Search,
} from 'lucide-react';
import {
  useUIStore,
  useAuthStore,
  useNotificationStore,
  useWorkspaceStore,
  useArtifactPanelStore,
} from '@/stores';
import { getAIStore } from '@/stores/ai/AIStore';
import { SessionListStore, type SessionSummary } from '@/stores/ai/SessionListStore';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { SidebarUserControls } from '@/components/layout/sidebar';
import { useResponsive } from '@/hooks/useMediaQuery';
import { cn } from '@/lib/utils';

function getWorkspaceSlugFromPathname(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0] ?? '';
  if (['login', 'callback', 'signup'].includes(firstSegment)) {
    return '';
  }
  return firstSegment;
}

const BROWSE_ITEMS = [
  { icon: FileText, label: 'Notes', path: 'notes' },
  { icon: LayoutGrid, label: 'Issues', path: 'issues' },
  { icon: FolderKanban, label: 'Projects', path: 'projects' },
] as const;

export const ConversationSidebar = observer(function ConversationSidebar() {
  const uiStore = useUIStore();
  const authStore = useAuthStore();
  const notificationStore = useNotificationStore();
  const workspaceStore = useWorkspaceStore();
  const artifactPanel = useArtifactPanelStore();
  const pathname = usePathname();
  const { isSmallScreen } = useResponsive();
  const collapsed = uiStore.sidebarCollapsed;

  const workspaceSlug = getWorkspaceSlugFromPathname(pathname);
  const workspaceId =
    workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id ??
    workspaceStore.currentWorkspaceId ??
    workspaceSlug;

  // Create session list store, re-create when pilotSpaceStore becomes available
  const aiStore = getAIStore();
  const pilotSpaceStore = aiStore.pilotSpace;
  const sessionListStore = useMemo(
    () => (pilotSpaceStore ? new SessionListStore(pilotSpaceStore) : null),
    [pilotSpaceStore]
  );

  // Fetch sessions on mount or when store changes
  useEffect(() => {
    sessionListStore?.fetchSessions();
  }, [sessionListStore]);

  const sessions = sessionListStore?.sessions ?? [];

  // Auto-close on mobile navigation
  const prevPathnameRef = useRef(pathname);
  useEffect(() => {
    if (isSmallScreen && prevPathnameRef.current !== pathname && !uiStore.sidebarCollapsed) {
      uiStore.setSidebarCollapsed(true);
    }
    prevPathnameRef.current = pathname;
  }, [pathname, isSmallScreen, uiStore]);

  // Notification polling
  const isAuthenticated = authStore.isAuthenticated;
  useEffect(() => {
    if (workspaceId && isAuthenticated && workspaceId.includes('-')) {
      notificationStore.startPolling(workspaceId);
    }
    return () => {
      notificationStore.stopPolling();
    };
  }, [workspaceId, isAuthenticated, notificationStore]);

  return (
    <aside
      className={cn(
        'flex h-full w-[260px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar',
        'transition-transform duration-200 ease-out',
        collapsed && '-translate-x-full absolute -z-10'
      )}
    >
      {/* Header — workspace name (switcher moved to user menu) */}
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-sidebar-border px-3">
        <span className="text-xs font-semibold text-sidebar-foreground truncate flex-1">
          {workspaceStore.currentWorkspace?.name ?? workspaceSlug}
        </span>
      </div>

      {/* New Chat button — resets to chat-first mode */}
      <div className="shrink-0 p-2">
        <Button
          variant="default"
          size="sm"
          className="w-full shadow-warm-sm text-xs"
          onClick={() => {
            uiStore.setLayoutMode('chat-first');
            artifactPanel.closeAllUnpinned();
            pilotSpaceStore?.clearConversation();
          }}
          asChild
        >
          <Link href={`/${workspaceSlug}`}>
            <MessageSquarePlus className="h-3.5 w-3.5 mr-1.5" />
            New Chat
          </Link>
        </Button>
      </div>

      {/* Search sessions */}
      <div className="shrink-0 px-2 pb-1">
        <div className="flex items-center gap-2 rounded-lg bg-sidebar-accent/30 px-2.5 py-1.5">
          <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <input
            type="text"
            placeholder="Search conversations..."
            className="flex-1 bg-transparent text-xs text-sidebar-foreground placeholder:text-muted-foreground/50 outline-none"
            onChange={(e) => {
              sessionListStore?.searchSessions(e.target.value);
            }}
          />
        </div>
      </div>

      {/* Conversation history — grouped by date */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="flex flex-col gap-0.5 p-2">
          {sessions.length === 0 ? (
            <p className="px-2 py-8 text-center text-xs text-muted-foreground">
              No conversations yet
            </p>
          ) : (
            Array.from(sessionListStore?.sessionsGroupedByDate ?? new Map<string, SessionSummary[]>()).map(
              ([dateLabel, groupSessions]) => (
                <div key={dateLabel}>
                  <div className="sticky top-0 z-10 bg-sidebar px-2.5 py-1.5">
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/50">
                      {dateLabel}
                    </span>
                  </div>
                  {groupSessions.map((session) => (
                    <div
                      key={session.sessionId}
                      className={cn(
                        'group flex w-full items-center rounded-lg text-left text-xs transition-colors',
                        'text-sidebar-foreground hover:bg-sidebar-accent/50'
                      )}
                    >
                      <button
                        type="button"
                        aria-label={`Resume conversation: ${session.title || `Session ${session.sessionId.slice(0, 8)}`}`}
                        className="flex-1 min-w-0 px-2.5 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring rounded-l-lg"
                        onClick={() => {
                          sessionListStore?.resumeSession(session.sessionId);
                        }}
                      >
                        <span className="block font-medium truncate">
                          {session.title || `Session ${session.sessionId.slice(0, 8)}`}
                        </span>
                        <span className="block text-[10px] text-muted-foreground mt-0.5">
                          {session.turnCount} turns
                        </span>
                      </button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            type="button"
                            aria-label="Session options"
                            className={cn(
                              'shrink-0 p-1.5 rounded-r-lg',
                              'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100',
                              'focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring',
                              'hover:bg-sidebar-accent transition-opacity'
                            )}
                          >
                            <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent side="right" align="start" className="w-40">
                          <DropdownMenuItem
                            className="text-xs gap-2 text-destructive focus:text-destructive"
                            onSelect={() => {
                              if (confirm('Delete this conversation?')) {
                                sessionListStore?.deleteSession(session.sessionId);
                              }
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  ))}
                </div>
              )
            )
          )}
        </div>
      </ScrollArea>

      <Separator />

      {/* Browse shortcuts — Notes, Issues, Projects */}
      <div className="shrink-0 p-2">
        <div className="flex items-center justify-center gap-1">
          {BROWSE_ITEMS.map(({ icon: Icon, label, path }) => (
            <Tooltip key={label} delayDuration={0}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-11 w-11 text-muted-foreground hover:text-sidebar-foreground"
                  asChild
                >
                  <Link href={`/${workspaceSlug}/${path}`}>
                    <Icon className="h-4 w-4" />
                    <span className="sr-only">{label}</span>
                  </Link>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top" className="text-xs">
                {label}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </div>

      {/* User controls (notifications + account menu) */}
      <SidebarUserControls
        collapsed={false}
        workspaceId={workspaceId}
        authStore={authStore}
        notificationStore={notificationStore}
        uiStore={uiStore}
      />

      {/* Collapse toggle */}
      <div className="shrink-0 border-t border-sidebar-border p-2">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                isSmallScreen ? uiStore.setSidebarCollapsed(true) : uiStore.toggleSidebar()
              }
              aria-label={isSmallScreen ? 'Close sidebar' : collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              className="h-8 w-full justify-center text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
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
    </aside>
  );
});
