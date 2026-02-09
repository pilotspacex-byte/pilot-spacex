'use client';

/**
 * CompactMessageList (H036) — Scrollable message container for compact chat.
 * Renders user/AI bubbles with auto-scroll. Reuses StreamingContent for SSE.
 */

import { useEffect, useRef } from 'react';
import { Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { StreamingContent } from '@/features/ai/ChatView/MessageList/StreamingContent';
import type { ChatMessage } from '@/stores/ai/types/conversation';

interface CompactMessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamContent: string;
}

export function CompactMessageList({
  messages,
  isStreaming,
  streamContent,
}: CompactMessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);

  // Auto-scroll to bottom on new messages (unless user scrolled up)
  useEffect(() => {
    if (!userScrolledRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, streamContent]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    userScrolledRef.current = !isAtBottom;
  };

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto p-4"
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      <div className="space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn('flex gap-2', msg.role === 'user' ? 'flex-row-reverse' : 'flex-row')}
          >
            {/* Avatar */}
            <div className="mt-0.5 shrink-0">
              {msg.role === 'user' ? (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-background-muted">
                  <User className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                </div>
              ) : (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-ai-muted">
                  <Bot className="h-3.5 w-3.5 text-ai" aria-hidden="true" />
                </div>
              )}
            </div>

            {/* Bubble */}
            <div
              className={cn(
                'max-w-[80%] rounded-lg px-3 py-2 text-sm',
                msg.role === 'user'
                  ? 'bg-background-subtle text-foreground'
                  : 'bg-card text-foreground shadow-sm'
              )}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Streaming indicator */}
        {isStreaming && streamContent && (
          <div className="flex gap-2">
            <div className="mt-0.5 shrink-0">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-ai-muted">
                <Bot className="h-3.5 w-3.5 text-ai" aria-hidden="true" />
              </div>
            </div>
            <div className="max-w-[80%] rounded-lg bg-card px-3 py-2 text-sm shadow-sm">
              <StreamingContent content={streamContent} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
