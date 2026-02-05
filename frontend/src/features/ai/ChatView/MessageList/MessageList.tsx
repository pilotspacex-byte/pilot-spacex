/**
 * MessageList - Virtualized auto-scrolling conversation container (T60)
 * Uses react-virtuoso for efficient rendering of 1000+ messages.
 * Follows shadcn/ui AI conversation component pattern with scroll-to-bottom.
 */

import { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { observer } from 'mobx-react-lite';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';
import { Button } from '@/components/ui/button';
import { ArrowDown, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage, ToolCall, ThinkingBlockEntry } from '@/stores/ai/types/conversation';
import { MessageGroup } from './MessageGroup';
import { StreamingContent } from './StreamingContent';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamContent?: string;
  /** Thinking content being streamed (extended thinking) */
  thinkingContent?: string;
  /** Individual thinking blocks for interleaved rendering (G-07) */
  thinkingBlocks?: ThinkingBlockEntry[];
  /** Whether thinking is actively streaming */
  isThinking?: boolean;
  /** Timestamp (ms) when thinking started, for live timer */
  thinkingStartedAt?: number | null;
  /** Whether the stream was interrupted by user */
  interrupted?: boolean;
  /** Pending tool calls buffered during streaming */
  pendingToolCalls?: ToolCall[];
  /** Ordered sequence of block types from SSE stream */
  blockOrder?: Array<'thinking' | 'text' | 'tool_use'>;
  /** Per-text-block segments for ordered rendering */
  textSegments?: string[];
  userName?: string;
  userAvatar?: string;
  className?: string;
  /** Trigger to scroll to bottom (increment to trigger scroll) */
  scrollToBottomTrigger?: number;
  /** Whether older messages exist (for scroll-up loading) */
  hasMoreMessages?: boolean;
  /** Whether older messages are currently being loaded */
  isLoadingMoreMessages?: boolean;
  /** Callback to load more older messages when scrolling up */
  onLoadMore?: () => void;
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
    thinkingBlocks,
    isThinking,
    thinkingStartedAt,
    interrupted,
    pendingToolCalls,
    blockOrder,
    textSegments,
    userName,
    userAvatar,
    className,
    scrollToBottomTrigger,
    hasMoreMessages,
    isLoadingMoreMessages,
    onLoadMore,
  }) => {
    const virtuosoRef = useRef<VirtuosoHandle>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [atBottom, setAtBottom] = useState(true);
    // Track pending scroll request to execute after render
    const pendingScrollRef = useRef(false);
    const lastTriggerRef = useRef(0);
    // Track previous message count to detect bulk message loads (e.g., session resume)
    const prevMessageCountRef = useRef(0);
    // Track if this is initial mount to handle page refresh scenario
    const isInitialMountRef = useRef(true);
    // Debounce for startReached to prevent multiple rapid calls
    const loadMoreTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const scrollToBottom = useCallback(() => {
      virtuosoRef.current?.scrollToIndex({
        index: 'LAST',
        behavior: 'smooth',
      });
    }, []);

    // Mark scroll as pending when trigger changes (manual resume via \resume command)
    useEffect(() => {
      if (scrollToBottomTrigger && scrollToBottomTrigger > lastTriggerRef.current) {
        lastTriggerRef.current = scrollToBottomTrigger;
        pendingScrollRef.current = true;
      }
    }, [scrollToBottomTrigger]);

    // Detect bulk message load (session resume on page refresh)
    // When messages go from 0 to N, or increase significantly, trigger scroll
    useEffect(() => {
      const prevCount = prevMessageCountRef.current;
      const currentCount = messages.length;

      // Detect initial load or bulk load (messages jumped from 0 or small number)
      const isBulkLoad = prevCount === 0 && currentCount > 0;
      const isInitialWithMessages = isInitialMountRef.current && currentCount > 0;

      if (isBulkLoad || isInitialWithMessages) {
        pendingScrollRef.current = true;
      }

      prevMessageCountRef.current = currentCount;
      isInitialMountRef.current = false;
    }, [messages.length]);

    // Execute pending scroll after messages are rendered
    // Uses double requestAnimationFrame to ensure DOM is painted
    useEffect(() => {
      if (pendingScrollRef.current && messages.length > 0) {
        // First rAF: scheduled before next paint
        requestAnimationFrame(() => {
          // Second rAF: scheduled after paint, DOM is ready
          requestAnimationFrame(() => {
            if (pendingScrollRef.current) {
              pendingScrollRef.current = false;
              scrollToBottom();
            }
          });
        });
      }
    }, [messages.length, scrollToBottom]);

    const handleAtBottomChange = useCallback((bottom: boolean) => {
      setAtBottom(bottom);
      setShowScrollButton(!bottom);
    }, []);

    /**
     * Handle scroll-up reaching the top of the list.
     * Triggers loading more older messages with debounce to prevent rapid calls.
     */
    const handleStartReached = useCallback(() => {
      if (!hasMoreMessages || isLoadingMoreMessages || !onLoadMore) {
        return;
      }

      // Debounce: clear existing timeout and set new one
      if (loadMoreTimeoutRef.current) {
        clearTimeout(loadMoreTimeoutRef.current);
      }

      loadMoreTimeoutRef.current = setTimeout(() => {
        onLoadMore();
      }, 100);
    }, [hasMoreMessages, isLoadingMoreMessages, onLoadMore]);

    // Note: messages.length in deps ensures recompute on MobX in-place push.
    // MobX observer tracks the array but useMemo's shallow ref check on
    // [messages] alone won't detect in-place mutations.
    const messageGroups = useMemo(
      () => groupMessagesByRole(messages),
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [messages, messages.length]
    );

    // Total items: message groups + optional streaming footer
    const hasStreamingFooter =
      isStreaming &&
      (streamContent ||
        thinkingContent ||
        (thinkingBlocks && thinkingBlocks.length > 0) ||
        (pendingToolCalls && pendingToolCalls.length > 0));
    const totalCount = messageGroups.length + (hasStreamingFooter ? 1 : 0);

    return (
      <div
        className={cn('relative flex-1 min-h-0', className)}
        role="log"
        aria-live="polite"
        aria-label="Chat messages"
      >
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
            className="absolute inset-0"
            totalCount={totalCount}
            followOutput={atBottom ? 'smooth' : false}
            atBottomStateChange={handleAtBottomChange}
            atBottomThreshold={100}
            startReached={handleStartReached}
            components={{
                Header: () =>
                  isLoadingMoreMessages ? (
                  <div className="flex justify-center py-3">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50 animate-pulse" />
                      <div
                        className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50 animate-pulse"
                        style={{ animationDelay: '0.2s' }}
                      />
                      <div
                        className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50 animate-pulse"
                        style={{ animationDelay: '0.4s' }}
                      />
                      <span className="ml-1">Loading older messages</span>
                    </div>
                  </div>
                ) : hasMoreMessages ? (
                  <div className="flex justify-center py-2">
                    <span className="text-xs text-muted-foreground">Scroll up for more</span>
                  </div>
                ) : null,
            }}
            itemContent={(index) => {
              // Streaming footer is the last item
              if (hasStreamingFooter && index === messageGroups.length) {
                return (
                  <div className="px-4 py-3">
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="text-sm font-semibold">PilotSpace Agent</span>
                    </div>
                    <StreamingContent
                      content={streamContent ?? ''}
                      thinkingContent={thinkingContent}
                      thinkingBlocks={thinkingBlocks}
                      isThinking={isThinking}
                      thinkingStartedAt={thinkingStartedAt}
                      interrupted={interrupted}
                      pendingToolCalls={pendingToolCalls}
                      blockOrder={blockOrder}
                      textSegments={textSegments}
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
