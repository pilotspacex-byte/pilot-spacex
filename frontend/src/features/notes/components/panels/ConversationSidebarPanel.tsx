'use client';

/**
 * ConversationSidebarPanel — T-139 (Feature 016 M8)
 *
 * Threaded AI discussions scoped to the current note.
 * Links to the existing annotation/discussion system.
 * New thread button + thread list with unread count.
 * Mounts inside SidebarPanel as content for activePanel="conversation".
 */

import { useState } from 'react';
import { MessageSquare, Plus, ChevronRight, Circle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

export interface ConversationMessage {
  id: string;
  authorName: string;
  authorAvatarUrl?: string;
  isAI: boolean;
  content: string;
  createdAt: string;
}

export interface ConversationThread {
  id: string;
  blockId?: string;
  blockPreview?: string;
  messages: ConversationMessage[];
  unreadCount: number;
  resolvedAt?: string;
}

export interface ConversationSidebarPanelProps {
  threads?: ConversationThread[];
  isLoading?: boolean;
  /** Called when user wants to start a new thread */
  onNewThread?: () => void;
  /** Called when user opens a thread */
  onOpenThread?: (threadId: string) => void;
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function ThreadRow({ thread, onOpen }: { thread: ConversationThread; onOpen: () => void }) {
  const lastMsg = thread.messages[thread.messages.length - 1];
  const timeAgo = lastMsg
    ? formatDistanceToNow(new Date(lastMsg.createdAt), { addSuffix: true })
    : '';
  const isResolved = !!thread.resolvedAt;

  return (
    <button
      onClick={onOpen}
      className={cn(
        'w-full flex items-start gap-3 px-3 py-2.5 rounded-md text-left',
        'hover:bg-muted/50 transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
      )}
      aria-label={`Thread: ${thread.blockPreview ?? 'Note thread'}, ${thread.unreadCount} unread`}
    >
      {/* Author avatar of last message */}
      {lastMsg ? (
        <Avatar className="h-7 w-7 shrink-0 mt-0.5">
          <AvatarImage src={lastMsg.authorAvatarUrl} alt={lastMsg.authorName} />
          <AvatarFallback className="text-[10px]">{getInitials(lastMsg.authorName)}</AvatarFallback>
        </Avatar>
      ) : (
        <div className="h-7 w-7 rounded-full bg-muted shrink-0 mt-0.5" />
      )}

      <div className="flex-1 min-w-0">
        {/* Block preview (context) */}
        {thread.blockPreview && (
          <p className="text-xs text-muted-foreground truncate italic mb-0.5">
            &ldquo;{thread.blockPreview}&rdquo;
          </p>
        )}

        {/* Last message preview */}
        {lastMsg && (
          <p className="text-sm text-foreground line-clamp-2 leading-snug">{lastMsg.content}</p>
        )}

        <div className="flex items-center gap-2 mt-1">
          <span className="text-xs text-muted-foreground">{timeAgo}</span>
          <span className="text-xs text-muted-foreground">
            {thread.messages.length} {thread.messages.length === 1 ? 'message' : 'messages'}
          </span>
          {isResolved && (
            <Badge variant="outline" className="text-[10px]">
              Resolved
            </Badge>
          )}
        </div>
      </div>

      <div className="flex flex-col items-end gap-1 shrink-0">
        {thread.unreadCount > 0 && (
          <span
            className="flex items-center justify-center h-4 min-w-[1rem] px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-bold"
            aria-hidden="true"
          >
            {thread.unreadCount > 99 ? '99+' : thread.unreadCount}
          </span>
        )}
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
      </div>
    </button>
  );
}

export function ConversationSidebarPanel({
  threads = [],
  isLoading = false,
  onNewThread,
  onOpenThread,
}: ConversationSidebarPanelProps) {
  const [filter, setFilter] = useState<'all' | 'unread' | 'resolved'>('all');

  const filtered = threads.filter((t) => {
    if (filter === 'unread') return t.unreadCount > 0;
    if (filter === 'resolved') return !!t.resolvedAt;
    return true;
  });

  const totalUnread = threads.reduce((acc, t) => acc + t.unreadCount, 0);

  return (
    <div className="flex flex-col h-full">
      {/* Actions bar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <div className="flex gap-1">
          {(['all', 'unread', 'resolved'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors capitalize',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                filter === f
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
              )}
              aria-pressed={filter === f}
            >
              {f}
              {f === 'unread' && totalUnread > 0 && (
                <span className="ml-1 text-[10px] font-bold text-primary">{totalUnread}</span>
              )}
            </button>
          ))}
        </div>
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={onNewThread}
          aria-label="Start new thread"
          title="New thread"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 py-10 px-4 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <MessageSquare className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              {filter === 'all' ? 'No conversations yet' : `No ${filter} threads`}
            </p>
            {filter === 'all' && (
              <p className="text-xs text-muted-foreground mt-1">
                Start a thread to discuss AI suggestions with your team.
              </p>
            )}
          </div>
          {filter === 'all' && onNewThread && (
            <Button size="sm" variant="outline" onClick={onNewThread}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              New Thread
            </Button>
          )}
        </div>
      )}

      {/* Thread list */}
      {!isLoading && filtered.length > 0 && (
        <div
          className="flex flex-col gap-0.5 p-2 overflow-auto"
          role="list"
          aria-label="Conversation threads"
        >
          {filtered.map((thread) => (
            <div key={thread.id} role="listitem">
              {thread.unreadCount > 0 && !thread.resolvedAt && (
                <Circle
                  className="h-1.5 w-1.5 text-primary fill-primary absolute left-2"
                  aria-hidden="true"
                />
              )}
              <ThreadRow thread={thread} onOpen={() => onOpenThread?.(thread.id)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
