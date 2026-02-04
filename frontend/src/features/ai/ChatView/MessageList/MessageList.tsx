/**
 * MessageList - Virtualized auto-scrolling conversation container (T60)
 * Uses react-virtuoso for efficient rendering of 1000+ messages.
 * Follows shadcn/ui AI conversation component pattern with scroll-to-bottom.
 */

import { useRef, useState, useCallback, useMemo } from 'react';
import { observer } from 'mobx-react-lite';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';
import { Button } from '@/components/ui/button';
import { ArrowDown, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { MessageGroup } from './MessageGroup';
import { StreamingContent } from './StreamingContent';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamContent?: string;
  /** Thinking content being streamed (extended thinking) */
  thinkingContent?: string;
  /** Whether thinking is actively streaming */
  isThinking?: boolean;
  /** Timestamp (ms) when thinking started, for live timer */
  thinkingStartedAt?: number | null;
  /** Whether the stream was interrupted by user */
  interrupted?: boolean;
  userName?: string;
  userAvatar?: string;
  className?: string;
}

/**
 * Group consecutive messages by role for better visual hierarchy
 */
function groupMessagesByRole(messages: ChatMessage[]): ChatMessage[][] {
  const groups: ChatMessage[][] = [];
  let currentGroup: ChatMessage[] = [];

  messages.forEach((message) => {
    if (currentGroup.length === 0) {
      currentGroup.push(message);
    } else if (currentGroup[0]?.role === message.role) {
      currentGroup.push(message);
    } else {
      groups.push(currentGroup);
      currentGroup = [message];
    }
  });

  if (currentGroup.length > 0) {
    groups.push(currentGroup);
  }

  return groups;
}

export const MessageList = observer<MessageListProps>(
  ({
    messages,
    isStreaming,
    streamContent,
    thinkingContent,
    isThinking,
    thinkingStartedAt,
    interrupted,
    userName,
    userAvatar,
    className,
  }) => {
    const virtuosoRef = useRef<VirtuosoHandle>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [atBottom, setAtBottom] = useState(true);

    const scrollToBottom = useCallback(() => {
      virtuosoRef.current?.scrollToIndex({
        index: 'LAST',
        behavior: 'smooth',
      });
    }, []);

    const handleAtBottomChange = useCallback((bottom: boolean) => {
      setAtBottom(bottom);
      setShowScrollButton(!bottom);
    }, []);

    // Note: messages.length in deps ensures recompute on MobX in-place push.
    // MobX observer tracks the array but useMemo's shallow ref check on
    // [messages] alone won't detect in-place mutations.
    const messageGroups = useMemo(
      () => groupMessagesByRole(messages),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [messages, messages.length]
    );

    // Total items: message groups + optional streaming footer
    const hasStreamingFooter = isStreaming && (streamContent || thinkingContent);
    const totalCount = messageGroups.length + (hasStreamingFooter ? 1 : 0);

    return (
      <div className={cn('relative flex-1', className)} role="log" aria-live="polite" aria-label="Chat messages">
        {totalCount === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-4">
              <Sparkles className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Ask me anything about your notes, issues, or code. Use{' '}
              <code className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">\skill</code> to
              invoke skills or{' '}
              <code className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">@agent</code> to
              call specialized agents.
            </p>
          </div>
        ) : (
          <Virtuoso
            ref={virtuosoRef}
            style={{ height: '100%' }}
            totalCount={totalCount}
            followOutput={atBottom ? 'smooth' : false}
            atBottomStateChange={handleAtBottomChange}
            atBottomThreshold={100}
            itemContent={(index) => {
              // Streaming footer is the last item
              if (hasStreamingFooter && index === messageGroups.length) {
                return (
                  <div className="px-4 py-3 bg-muted/30">
                    <StreamingContent
                      content={streamContent ?? ''}
                      thinkingContent={thinkingContent}
                      isThinking={isThinking}
                      thinkingStartedAt={thinkingStartedAt}
                      interrupted={interrupted}
                    />
                  </div>
                );
              }

              const group = messageGroups[index];
              if (!group) return null;

              return (
                <MessageGroup
                  key={`group-${index}`}
                  messages={group}
                  userName={userName}
                  userAvatar={userAvatar}
                />
              );
            }}
          />
        )}

        {/* Scroll to bottom button */}
        {showScrollButton && (
          <Button
            size="icon"
            variant="outline"
            className="absolute bottom-4 right-4 rounded-full shadow-lg"
            onClick={scrollToBottom}
          >
            <ArrowDown className="h-4 w-4" />
            <span className="sr-only">Scroll to bottom</span>
          </Button>
        )}
      </div>
    );
  }
);

MessageList.displayName = 'MessageList';
