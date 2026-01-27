/**
 * ChatHeader - Chat title, status, and task badges
 */

import { observer } from 'mobx-react-lite';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sparkles, Loader2, X, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatHeaderProps {
  title?: string;
  isStreaming?: boolean;
  activeTaskCount?: number;
  sessionId?: string | null;
  onClear?: () => void;
  className?: string;
}

export const ChatHeader = observer<ChatHeaderProps>(
  ({ title, isStreaming, activeTaskCount = 0, sessionId, onClear, className }) => {
    return (
      <div className={cn('border-b bg-background', className)}>
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-9 w-9 rounded-full bg-gradient-to-br from-purple-500 to-pink-500">
              <Sparkles className="h-5 w-5 text-white" />
            </div>

            <div className="space-y-0.5">
              <h2 className="text-sm font-semibold leading-none">{title || 'PilotSpace AI'}</h2>

              <div className="flex items-center gap-2">
                {isStreaming && (
                  <Badge variant="secondary" className="gap-1.5 text-xs">
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
            {sessionId && (
              <Badge variant="outline" className="gap-1.5 font-mono text-xs">
                <MessageSquare className="h-3 w-3" />
                Session: {sessionId.slice(0, 8)}
              </Badge>
            )}

            {onClear && (
              <Button variant="ghost" size="icon" onClick={onClear} disabled={isStreaming}>
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
