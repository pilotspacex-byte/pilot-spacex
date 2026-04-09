/**
 * SessionResumeMenu - Session picker popup for \resume command
 *
 * Features:
 * - Date grouping (Today, Yesterday, weekday, date)
 * - Search input (filters by title and context)
 * - Session list with title, context badges, turn count, time ago
 * - Keyboard navigation via cmdk Command component
 */

import { useMemo, useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { FileText, GitBranch, MessageSquare, Clock } from 'lucide-react';

export interface ContextEntry {
  turn: number;
  noteId?: string;
  noteTitle?: string;
  issueId?: string;
  blockIds?: string[];
  selectedText?: string;
  timestamp: string;
}

export interface SessionSummary {
  sessionId: string;
  title?: string;
  contextHistory?: ContextEntry[];
  turnCount: number;
  updatedAt: Date;
  agentName?: string;
}

interface SessionResumeMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sessions: SessionSummary[];
  isLoading?: boolean;
  onSelect: (sessionId: string) => void;
  onSearch?: (query: string) => void;
  children: React.ReactNode;
  /** Width in pixels for popover content */
  popoverWidth?: number;
}

/**
 * Group sessions by date label (Today, Yesterday, weekday, date)
 */
function groupSessionsByDate(sessions: SessionSummary[]): Map<string, SessionSummary[]> {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);

  const groups = new Map<string, SessionSummary[]>();
  const order = ['Today', 'Yesterday'];
  const weekdays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  for (const session of sessions) {
    const sessionDate = new Date(
      session.updatedAt.getFullYear(),
      session.updatedAt.getMonth(),
      session.updatedAt.getDate()
    );

    let label: string;
    if (sessionDate.getTime() === today.getTime()) {
      label = 'Today';
    } else if (sessionDate.getTime() === yesterday.getTime()) {
      label = 'Yesterday';
    } else {
      const daysDiff = Math.floor(
        (today.getTime() - sessionDate.getTime()) / (24 * 60 * 60 * 1000)
      );
      if (daysDiff < 7) {
        label = weekdays[sessionDate.getDay()] ?? 'Unknown';
      } else {
        const dateOptions: Intl.DateTimeFormatOptions = {
          month: 'long',
          day: 'numeric',
        };
        if (sessionDate.getFullYear() !== now.getFullYear()) {
          dateOptions.year = 'numeric';
        }
        label = sessionDate.toLocaleDateString('en-US', dateOptions);
      }
    }

    if (!groups.has(label)) {
      groups.set(label, []);
      if (!order.includes(label)) {
        order.push(label);
      }
    }
    groups.get(label)!.push(session);
  }

  // Return in order
  const orderedGroups = new Map<string, SessionSummary[]>();
  for (const label of order) {
    if (groups.has(label)) {
      orderedGroups.set(label, groups.get(label)!);
    }
  }
  return orderedGroups;
}

/**
 * Format relative time (e.g., "2h ago", "3d ago")
 */
function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Get unique context types from context history
 */
function getContextBadges(
  contextHistory?: ContextEntry[]
): Array<{ type: 'note' | 'issue'; title?: string }> {
  if (!contextHistory || contextHistory.length === 0) return [];

  const badges: Array<{ type: 'note' | 'issue'; title?: string }> = [];
  const seenNotes = new Set<string>();
  const seenIssues = new Set<string>();

  for (const ctx of contextHistory) {
    if (ctx.noteId && !seenNotes.has(ctx.noteId)) {
      seenNotes.add(ctx.noteId);
      badges.push({ type: 'note', title: ctx.noteTitle });
    }
    if (ctx.issueId && !seenIssues.has(ctx.issueId)) {
      seenIssues.add(ctx.issueId);
      badges.push({ type: 'issue' });
    }
  }

  return badges.slice(0, 3); // Max 3 badges
}

export const SessionResumeMenu = observer<SessionResumeMenuProps>(
  ({ open, onOpenChange, sessions, isLoading, onSelect, onSearch, children, popoverWidth }) => {
    const dateGroups = useMemo(() => groupSessionsByDate(sessions), [sessions]);

    const handleSelect = useCallback(
      (sessionId: string) => {
        onSelect(sessionId);
        onOpenChange(false);
      },
      [onSelect, onOpenChange]
    );

    return (
      <Popover open={open} onOpenChange={onOpenChange}>
        <PopoverTrigger asChild>{children}</PopoverTrigger>
        <PopoverContent
          className={cn('p-0 w-auto')}
          align="start"
          side="top"
          sideOffset={8}
          style={{ width: popoverWidth ?? 450 }}
          onOpenAutoFocus={(e) => e.preventDefault()}
          onCloseAutoFocus={(e) => e.preventDefault()}
        >
          <Command shouldFilter={false}>
            <CommandInput placeholder="Search sessions..." onValueChange={onSearch} />
            <CommandList className="max-h-[350px]">
              {isLoading ? (
                <div className="p-2 space-y-3">
                  {/* Session skeleton items */}
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-3 p-2">
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-48" />
                        <div className="flex items-center gap-2">
                          <Skeleton className="h-5 w-16 rounded-full" />
                          <Skeleton className="h-5 w-12 rounded-full" />
                        </div>
                      </div>
                      <Skeleton className="h-4 w-14" />
                    </div>
                  ))}
                </div>
              ) : sessions.length === 0 ? (
                <CommandEmpty>No sessions found.</CommandEmpty>
              ) : (
                Array.from(dateGroups.entries()).map(([dateLabel, groupSessions]) => (
                  <CommandGroup key={dateLabel} heading={dateLabel}>
                    {groupSessions.map((session) => {
                      const badges = getContextBadges(session.contextHistory);
                      return (
                        <CommandItem
                          key={session.sessionId}
                          value={session.sessionId}
                          onSelect={handleSelect}
                          className="flex items-center gap-3 py-2.5"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm truncate">
                                {session.title || 'Untitled conversation'}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                              {/* Context badges */}
                              {badges.map((badge, idx) => (
                                <Badge
                                  key={idx}
                                  variant="secondary"
                                  className={cn(
                                    'text-xs px-1.5 py-0 h-5',
                                    badge.type === 'note'
                                      ? 'bg-blue-500/10 text-blue-600'
                                      : 'bg-purple-500/10 text-purple-600'
                                  )}
                                >
                                  {badge.type === 'note' ? (
                                    <FileText className="h-3 w-3 mr-1" />
                                  ) : (
                                    <GitBranch className="h-3 w-3 mr-1" />
                                  )}
                                  {badge.title
                                    ? badge.title.length > 15
                                      ? badge.title.slice(0, 15) + '...'
                                      : badge.title
                                    : badge.type}
                                </Badge>
                              ))}
                              {/* Turn count */}
                              <span className="text-xs text-muted-foreground flex items-center gap-1">
                                <MessageSquare className="h-3 w-3" />
                                {session.turnCount}
                              </span>
                            </div>
                          </div>
                          {/* Time ago */}
                          <span className="text-xs text-muted-foreground flex items-center gap-1 shrink-0">
                            <Clock className="h-3 w-3" />
                            {formatTimeAgo(session.updatedAt)}
                          </span>
                        </CommandItem>
                      );
                    })}
                  </CommandGroup>
                ))
              )}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    );
  }
);

SessionResumeMenu.displayName = 'SessionResumeMenu';
