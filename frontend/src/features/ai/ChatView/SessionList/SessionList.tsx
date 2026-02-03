/**
 * SessionList - List of recent conversation sessions
 * T075-T079: Session Persistence UI
 */

import { useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Loader2, MessageSquare, Trash2, Clock, Activity, GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SessionListStore } from '@/stores/ai/SessionListStore';

interface SessionListProps {
  store: SessionListStore;
  onResumeSession?: (sessionId: string) => void;
  className?: string;
}

export const SessionList = observer<SessionListProps>(({ store, onResumeSession, className }) => {
  useEffect(() => {
    // Fetch sessions on mount
    store.fetchSessions();
  }, [store]);

  const handleResume = async (sessionId: string) => {
    await store.resumeSession(sessionId);
    onResumeSession?.(sessionId);
  };

  const handleDelete = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();

    if (confirm('Are you sure you want to delete this session?')) {
      await store.deleteSession(sessionId);
    }
  };

  if (store.isLoading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (store.error) {
    return (
      <Card className={cn('border-destructive/50', className)}>
        <CardContent className="py-4">
          <p className="text-sm text-destructive">{store.error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => store.fetchSessions()}
            className="mt-2"
          >
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const grouped = store.sessionsWithForks;

  const renderSessionCard = (session: (typeof grouped)[0]['session'], isFork = false) => {
    const isExpired = session.expiresAt < new Date();
    const isSelected = store.selectedSessionId === session.sessionId;

    return (
      <Card
        key={session.sessionId}
        className={cn(
          'p-3 cursor-pointer hover:bg-accent/50 transition-colors',
          isSelected && 'border-primary bg-primary/5',
          isExpired && 'opacity-60',
          isFork && 'ml-4 border-l-2 border-l-[#8B7EC8]/40'
        )}
        onClick={() => !isExpired && handleResume(session.sessionId)}
      >
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium line-clamp-1">
                {isFork && <GitBranch className="inline h-3 w-3 mr-1 text-[#8B7EC8]" />}
                {session.title || `Session ${session.sessionId.slice(0, 8)}`}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="secondary" className="text-xs font-mono">
                  {session.agentName}
                </Badge>
                {session.contextType && (
                  <Badge variant="outline" className="text-xs">
                    {session.contextType}
                  </Badge>
                )}
                {isFork && (
                  <Badge variant="outline" className="text-xs text-[#8B7EC8] border-[#8B7EC8]/40">
                    Fork
                  </Badge>
                )}
                {!isFork && (session.forkCount ?? 0) > 0 && (
                  <Badge variant="outline" className="text-xs text-[#8B7EC8] border-[#8B7EC8]/40">
                    <GitBranch className="h-3 w-3 mr-0.5" />
                    {session.forkCount}
                  </Badge>
                )}
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 shrink-0"
              onClick={(e) => handleDelete(session.sessionId, e)}
            >
              <Trash2 className="h-3 w-3" />
              <span className="sr-only">Delete session</span>
            </Button>
          </div>

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              <span>{session.turnCount} turns</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>
                {new Date(session.updatedAt).toLocaleDateString([], {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
          </div>

          {isExpired && (
            <Badge variant="destructive" className="text-xs">
              Expired
            </Badge>
          )}
        </div>
      </Card>
    );
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <MessageSquare className="h-4 w-4" />
          Recent Sessions
        </CardTitle>
      </CardHeader>
      <CardContent>
        {grouped.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No recent sessions</p>
          </div>
        ) : (
          <ScrollArea className="h-[400px]">
            <div className="space-y-2 pr-4">
              {grouped.map(({ session, forks }) => (
                <div key={session.sessionId}>
                  {renderSessionCard(session)}
                  {forks.map((fork) => renderSessionCard(fork, true))}
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
});

SessionList.displayName = 'SessionList';
