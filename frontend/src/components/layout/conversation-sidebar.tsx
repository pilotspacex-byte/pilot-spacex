'use client';

import { useEffect, useRef, useState } from 'react';
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
} from 'lucide-react';
import {
  useUIStore,
  useAuthStore,
  useNotificationStore,
  useWorkspaceStore,
} from '@/stores';
import { getAIStore } from '@/stores/ai/AIStore';
import { SessionListStore } from '@/stores/ai/SessionListStore';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { WorkspaceSwitcher } from '@/components/layout/workspace-switcher';
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
  const pathname = usePathname();
  const { isSmallScreen } = useResponsive();
  const collapsed = uiStore.sidebarCollapsed;

  const workspaceSlug = getWorkspaceSlugFromPathname(pathname);
  const workspaceId =
    workspaceStore.getWorkspaceBySlug(workspaceSlug)?.id ??
    workspaceStore.currentWorkspaceId ??
    workspaceSlug;

  // Create session list store lazily, tied to the PilotSpaceStore
  const aiStore = getAIStore();
  const pilotSpaceStore = aiStore.pilotSpace;
  const [sessionListStore] = useState(() =>
    pilotSpaceStore ? new SessionListStore(pilotSpaceStore) : null
  );

  // Fetch sessions on mount
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
        'flex h-full shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200',
        collapsed ? 'w-0 overflow-hidden' : 'w-[260px]'
      )}
    >
      {/* Header — workspace switcher */}
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-sidebar-border px-3">
        <WorkspaceSwitcher currentSlug={workspaceSlug} />
      </div>

      {/* New Chat button */}
      <div className="shrink-0 p-2">
        <Button
          variant="default"
          size="sm"
          className="w-full shadow-warm-sm text-xs"
          asChild
        >
          <Link href={`/${workspaceSlug}`}>
            <MessageSquarePlus className="h-3.5 w-3.5 mr-1.5" />
            New Chat
          </Link>
        </Button>
      </div>

      {/* Conversation history */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="flex flex-col gap-0.5 p-2">
          {sessions.length === 0 ? (
            <p className="px-2 py-8 text-center text-xs text-muted-foreground">
              No conversations yet
            </p>
          ) : (
            sessions.slice(0, 20).map((session) => (
              <button
                key={session.sessionId}
                type="button"
                className={cn(
                  'group flex items-start gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition-colors',
                  'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
                onClick={() => {
                  sessionListStore?.resumeSession(session.sessionId);
                }}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">
                    {session.title || `Session ${session.sessionId.slice(0, 8)}`}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {new Date(session.updatedAt).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                    })}
                    {' · '}
                    {session.turnCount} turns
                  </p>
                </div>
              </button>
            ))
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
                  className="h-8 w-8 text-muted-foreground hover:text-sidebar-foreground"
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
