/**
 * ChatHeader - Chat title, status, and task badges
 * T075-T079: Add session selector dropdown
 */

import { observer } from 'mobx-react-lite';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Sparkles, Loader2, X, MessageSquare, ChevronDown, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatHeaderProps {
  title?: string;
  isStreaming?: boolean;
  activeTaskCount?: number;
  sessionId?: string | null;
  recentSessions?: Array<{
    sessionId: string;
    title?: string;
    updatedAt: Date;
  }>;
  onClear?: () => void;
  onNewSession?: () => void;
  onSelectSession?: (sessionId: string) => void;
  className?: string;
}

export const ChatHeader = observer<ChatHeaderProps>(
  ({
    title,
    isStreaming,
    activeTaskCount = 0,
    sessionId,
    recentSessions = [],
    onClear,
    onNewSession,
    onSelectSession,
    className,
  }) => {
    return (
      <div className={cn('border-b bg-background', className)} data-testid="chat-header">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-9 w-9 rounded-full bg-gradient-to-br from-purple-500 to-pink-500">
              <Sparkles className="h-5 w-5 text-white" />
            </div>

            <div className="space-y-0.5">
              <h2 className="text-sm font-semibold leading-none">{title || 'PilotSpace AI'}</h2>

              <div className="flex items-center gap-2">
                {isStreaming && (
                  <Badge
                    variant="secondary"
                    className="gap-1.5 text-xs"
                    data-testid="streaming-indicator"
                  >
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Streaming
                  </Badge>
                )}

                {!isStreaming && activeTaskCount > 0 && (
                  <Badge variant="secondary" className="gap-1.5 text-xs">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {activeTaskCount} {activeTaskCount === 1 ? 'task' : 'tasks'} active
                  </Badge>
                )}

                {!isStreaming && activeTaskCount === 0 && sessionId && (
                  <span className="text-xs text-muted-foreground">Ready</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Session selector dropdown */}
            {recentSessions.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild data-testid="session-dropdown">
                  <Button variant="outline" size="sm" className="gap-1.5">
                    <MessageSquare className="h-3 w-3" />
                    {sessionId ? `Session: ${sessionId.slice(0, 8)}` : 'Select Session'}
                    <ChevronDown className="h-3 w-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64">
                  <DropdownMenuLabel>Recent Sessions</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {onNewSession && (
                    <>
                      <DropdownMenuItem
                        onClick={onNewSession}
                        className="gap-2"
                        data-testid="new-session-button"
                      >
                        <Plus className="h-4 w-4" />
                        <span>New Session</span>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                    </>
                  )}
                  {recentSessions.map((session) => (
                    <DropdownMenuItem
                      key={session.sessionId}
                      onClick={() => onSelectSession?.(session.sessionId)}
                      className={cn('gap-2', sessionId === session.sessionId && 'bg-accent')}
                      data-testid="session-item"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {session.title || `Session ${session.sessionId.slice(0, 8)}`}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {session.updatedAt.toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </p>
                      </div>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {/* Session badge (show if sessions not available) */}
            {sessionId && recentSessions.length === 0 && (
              <Badge variant="outline" className="gap-1.5 font-mono text-xs">
                <MessageSquare className="h-3 w-3" />
                Session: {sessionId.slice(0, 8)}
              </Badge>
            )}

            {onClear && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onClear}
                disabled={isStreaming}
                data-testid="clear-conversation-button"
              >
                <X className="h-4 w-4" />
                <span className="sr-only">Clear conversation</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }
);

ChatHeader.displayName = 'ChatHeader';
