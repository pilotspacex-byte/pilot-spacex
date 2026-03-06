/**
 * NotificationPanel - AI-prioritized notification center.
 *
 * Spec: ui-design-spec.md S12 "AI-Prioritized Notification Center"
 * - Priority-based display: urgent (red), important (amber), fyi (gray)
 * - Mark as read, mark all as read
 * - Unread indicator with subtle background tint
 * - Load more pagination
 * - Empty / loading / error states
 */

'use client';

import { observer } from 'mobx-react-lite';
import { formatDistanceToNow } from 'date-fns';
import {
  AlertTriangle,
  Bell,
  Check,
  CheckCheck,
  Loader2,
  MessageSquare,
  Star,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type {
  Notification,
  NotificationPriority,
  NotificationStore,
} from '@/stores/NotificationStore';

const PRIORITY_CONFIG: Record<
  NotificationPriority,
  { bg: string; icon: React.ElementType; color: string; label: string }
> = {
  urgent: {
    bg: 'bg-destructive/10',
    icon: AlertTriangle,
    color: 'text-destructive',
    label: 'Urgent',
  },
  important: {
    bg: 'bg-amber-500/10',
    icon: Star,
    color: 'text-amber-600',
    label: 'Important',
  },
  fyi: {
    bg: 'bg-muted',
    icon: MessageSquare,
    color: 'text-muted-foreground',
    label: 'FYI',
  },
};

function NotificationItem({
  notification,
  onMarkRead,
  onRemove,
}: {
  notification: Notification;
  onMarkRead: (id: string) => void;
  onRemove: (id: string) => void;
}) {
  const config = PRIORITY_CONFIG[notification.priority];
  const Icon = config.icon;

  const timeAgo = formatDistanceToNow(notification.createdAt, { addSuffix: true });

  return (
    <div
      className={cn(
        'group flex gap-3 rounded-lg p-2.5 transition-colors',
        !notification.read ? config.bg : 'hover:bg-muted/50'
      )}
      role="listitem"
      aria-label={`${notification.read ? '' : 'Unread '}${config.label} notification: ${notification.title}`}
    >
      <div className={cn('mt-0.5 shrink-0', config.color)}>
        <Icon className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            'text-xs leading-snug',
            !notification.read ? 'font-medium text-foreground' : 'text-muted-foreground'
          )}
        >
          {notification.title}
        </p>
        {notification.description && (
          <p className="mt-0.5 truncate text-[10px] text-muted-foreground">
            {notification.description}
          </p>
        )}
        <p className="mt-1 text-[10px] text-muted-foreground/70">{timeAgo}</p>
      </div>
      <div className="flex shrink-0 items-start gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
        {!notification.read && (
          <Tooltip delayDuration={0}>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={(e) => {
                  e.stopPropagation();
                  onMarkRead(notification.id);
                }}
                aria-label="Mark as read"
              >
                <Check className="h-3 w-3" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left">Mark as read</TooltipContent>
          </Tooltip>
        )}
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-destructive"
              onClick={(e) => {
                e.stopPropagation();
                onRemove(notification.id);
              }}
              aria-label="Dismiss notification"
            >
              <X className="h-3 w-3" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="left">Dismiss</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}

interface NotificationPanelProps {
  store: NotificationStore;
  /** Workspace ID used for API calls. When provided, panel uses async API actions. */
  workspaceId?: string;
  collapsed?: boolean;
}

export const NotificationPanel = observer(function NotificationPanel({
  store,
  workspaceId,
  collapsed = false,
}: NotificationPanelProps) {
  const hasUnread = store.unreadCount > 0;
  const notifications = store.sortedNotifications;
  const canLoadMore = store.currentPage < store.totalPages;

  function handleOpenChange(open: boolean) {
    if (open && workspaceId) {
      void store.fetchNotifications(workspaceId, 1);
    }
  }

  function handleMarkRead(id: string) {
    if (workspaceId) {
      void store.markRead(workspaceId, id);
    } else {
      store.markAsRead(id);
    }
  }

  function handleMarkAllRead() {
    if (workspaceId) {
      void store.markAllRead(workspaceId);
    } else {
      store.markAllAsRead();
    }
  }

  function handleLoadMore() {
    if (workspaceId) {
      void store.fetchNotifications(workspaceId, store.currentPage + 1);
    }
  }

  const bellButton = (
    <Button
      variant="ghost"
      size="icon"
      className={cn('relative h-8 w-8', collapsed && 'rounded-full')}
      aria-label={`Notifications${hasUnread ? `, ${store.unreadCount} unread` : ''}`}
    >
      <Bell className="h-4 w-4" />
      {hasUnread && (
        <Badge
          variant="destructive"
          className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center px-1 text-[9px]"
        >
          {store.unreadCount > 99 ? '99+' : store.unreadCount}
        </Badge>
      )}
    </Button>
  );

  return (
    <Popover onOpenChange={handleOpenChange}>
      <Tooltip delayDuration={collapsed ? 0 : 1000}>
        <TooltipTrigger asChild>
          <PopoverTrigger asChild>{bellButton}</PopoverTrigger>
        </TooltipTrigger>
        {collapsed && <TooltipContent side="right">Notifications</TooltipContent>}
      </Tooltip>

      <PopoverContent
        side="right"
        align="end"
        className="w-80 p-0"
        aria-label="Notification center"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-3 py-2.5">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">Notifications</h3>
            {hasUnread && (
              <Badge variant="secondary" className="h-5 px-1.5 text-[10px]">
                {store.unreadCount}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {hasUnread && (
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={handleMarkAllRead}
                    aria-label="Mark all as read"
                  >
                    <CheckCheck className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Mark all as read</TooltipContent>
              </Tooltip>
            )}
          </div>
        </div>

        {/* Loading state */}
        {store.isLoading && notifications.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" aria-hidden="true" />
            <span className="sr-only">Loading notifications</span>
          </div>
        ) : notifications.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <Bell className="h-8 w-8 text-muted-foreground/40" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-foreground">All caught up</p>
              <p className="text-xs text-muted-foreground">No notifications to show.</p>
            </div>
          </div>
        ) : (
          <ScrollArea className="max-h-[320px]">
            <div className="space-y-0.5 p-1.5" role="list" aria-label="Notifications list">
              {notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onMarkRead={handleMarkRead}
                  onRemove={(id) => store.removeNotification(id)}
                />
              ))}
            </div>

            {/* Pagination: load more */}
            {canLoadMore && (
              <div className="border-t px-3 py-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-xs text-muted-foreground"
                  onClick={handleLoadMore}
                  disabled={store.isLoading}
                >
                  {store.isLoading ? <Loader2 className="mr-1.5 h-3 w-3 animate-spin" /> : null}
                  Load more
                </Button>
              </div>
            )}
          </ScrollArea>
        )}

        {/* Error state */}
        {store.error && (
          <p className="px-3 pb-2 text-[10px] text-destructive" role="alert">
            {store.error}
          </p>
        )}
      </PopoverContent>
    </Popover>
  );
});
