/**
 * MessageList - Auto-scrolling conversation container
 * Follows shadcn/ui AI conversation component pattern with scroll-to-bottom
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { observer } from 'mobx-react-lite';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ArrowDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { MessageGroup } from './MessageGroup';
import { StreamingContent } from './StreamingContent';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamContent?: string;
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
  ({ messages, isStreaming, streamContent, userName, userAvatar, className }) => {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [autoScroll, setAutoScroll] = useState(true);

    // Auto-scroll to bottom on new messages or streaming
    useEffect(() => {
      if (autoScroll && scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }, [messages, streamContent, autoScroll]);

    // Detect manual scroll away from bottom
    const handleScroll = useCallback(() => {
      if (!scrollRef.current) return;

      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

      setAutoScroll(isNearBottom);
      setShowScrollButton(!isNearBottom);
    }, []);

    const scrollToBottom = useCallback(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        setAutoScroll(true);
      }
    }, []);

    const messageGroups = groupMessagesByRole(messages);

    return (
      <div className={cn('relative flex-1', className)}>
        <ScrollArea className="h-full" onScrollCapture={handleScroll}>
          <div ref={scrollRef} className="space-y-0">
            {messageGroups.length === 0 && !isStreaming && (
              <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-4">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-4">
                  <span className="text-2xl">✨</span>
                </div>
                <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
                <p className="text-sm text-muted-foreground max-w-sm">
                  Ask me anything about your notes, issues, or code. Use{' '}
                  <code className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">\skill</code>{' '}
                  to invoke skills or{' '}
                  <code className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">@agent</code>{' '}
                  to call specialized agents.
                </p>
              </div>
            )}

            {messageGroups.map((group, idx) => (
              <MessageGroup
                key={`group-${idx}`}
                messages={group}
                userName={userName}
                userAvatar={userAvatar}
              />
            ))}

            {isStreaming && streamContent && (
              <div className="px-4 py-3 bg-muted/30">
                <StreamingContent content={streamContent} />
              </div>
            )}
          </div>
        </ScrollArea>

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
