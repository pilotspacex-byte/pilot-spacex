/**
 * MessageList - Virtualized auto-scrolling conversation container (T60)
 * Uses react-virtuoso for efficient rendering of 1000+ messages.
 * Follows shadcn/ui AI conversation component pattern with scroll-to-bottom.
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import type React from 'react';
import { observer } from 'mobx-react-lite';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';
import { Button } from '@/components/ui/button';
import { ArrowDown, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type {
  ChatMessage,
  ToolCall,
  ThinkingBlockEntry,
  StreamingPhase,
} from '@/stores/ai/types/conversation';
import { MessageGroup } from './MessageGroup';
import { StreamingContent } from './StreamingContent';
import { InlineStreamingIndicator } from './InlineStreamingIndicator';

const DEFAULT_SUGGESTED_PROMPTS = [
  'Extract issues from this note',
  'Summarize my project',
  'Improve the writing in this note',
  'Decompose this into subtasks',
] as const;

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
  /** Callback when user clicks a suggested prompt pill */
  onSuggestedPrompt?: (prompt: string) => void;
  /** Custom suggested prompts (overrides defaults when provided) */
  suggestedPrompts?: readonly string[];
  /** Current streaming phase for inline indicator */
  streamingPhase?: StreamingPhase;
  /** Active tool name during tool_use phase */
  activeToolName?: string | null;
  /** Word count during content phase */
  wordCount?: number;
  /** Custom empty state slot — replaces the default empty state UI when provided */
  emptyStateSlot?: React.ReactNode;
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
    onSuggestedPrompt,
    suggestedPrompts,
    streamingPhase,
    activeToolName,
    wordCount,
    emptyStateSlot,
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
    // Track if startReached fired while guards blocked it (race condition fix)
    const startReachedPendingRef = useRef(false);

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
        // Track that startReached fired but was blocked (e.g., during session resume
        // when hasMoreMessages hasn't been set yet). The retry effect below will
        // call onLoadMore once guards are satisfied.
        startReachedPendingRef.current = true;
        return;
      }

      startReachedPendingRef.current = false;

      // Debounce: clear existing timeout and set new one
      if (loadMoreTimeoutRef.current) {
        clearTimeout(loadMoreTimeoutRef.current);
      }

      loadMoreTimeoutRef.current = setTimeout(() => {
        onLoadMore();
      }, 100);
    }, [hasMoreMessages, isLoadingMoreMessages, onLoadMore]);

    // Retry loading when hasMoreMessages becomes true after startReached was blocked.
    // Race condition: Virtuoso fires startReached on mount (short list, user already
    // at top), but hasMoreMessages is still false (async resume not yet complete).
    // When hasMoreMessages later becomes true, startReached won't re-fire since
    // the scroll position hasn't changed. This effect bridges that gap.
    useEffect(() => {
      if (
        startReachedPendingRef.current &&
        hasMoreMessages &&
        !isLoadingMoreMessages &&
        onLoadMore
      ) {
        startReachedPendingRef.current = false;
        onLoadMore();
      }
    }, [hasMoreMessages, isLoadingMoreMessages, onLoadMore]);

    // Compute fresh groups on every render — no useMemo.
    // MobX observer triggers re-render when any element is replaced
    // (e.g. resolveQuestion updates questionData.answers). Using useMemo
    // with [messages, messages.length] misses element replacements because
    // the array reference and length don't change. Individual MessageGroup/
    // AssistantMessage memo wrappers still prevent unnecessary DOM updates.
    //
    // Filter out answer protocol messages before grouping to avoid empty
    // Virtuoso items (UserMessage returns null but the group wrapper remains).
    const visibleMessages = messages.filter((m) => !m.metadata?.isAnswerMessage);
    const messageGroups = groupMessagesByRole(visibleMessages);

    // Total items: message groups + optional streaming footer
    const hasStreamingContent =
      streamContent ||
      thinkingContent ||
      (thinkingBlocks && thinkingBlocks.length > 0) ||
      (pendingToolCalls && pendingToolCalls.length > 0);
    const hasStreamingFooter = isStreaming && (hasStreamingContent || streamingPhase);
    const totalCount = messageGroups.length + (hasStreamingFooter ? 1 : 0);

    return (
      <div
        className={cn('relative flex-1 min-h-0', className)}
        role="log"
        aria-live="polite"
        aria-label="Chat messages"
      >
        {totalCount === 0 && !isStreaming ? (
          (emptyStateSlot ?? (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-4">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/80 to-ai/80 flex items-center justify-center mb-4">
                <Sparkles className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Start a conversation</h3>
              <p className="text-sm text-muted-foreground max-w-sm mb-5">
                Ask me anything about your notes, issues, or code. Use{' '}
                <code className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">\skill</code> to
                invoke skills or{' '}
                <code className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono">@agent</code> to
                call specialized agents.
              </p>
              {onSuggestedPrompt && (
                <div className="flex flex-wrap justify-center gap-2 max-w-md">
                  {(suggestedPrompts ?? DEFAULT_SUGGESTED_PROMPTS).map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => onSuggestedPrompt(prompt)}
                      className={cn(
                        'rounded-full border border-border px-3 py-1.5 text-xs',
                        'text-muted-foreground hover:text-foreground hover:border-primary/40',
                        'hover:bg-primary/5 transition-colors min-h-[36px]'
                      )}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))
        ) : (
          <Virtuoso
            ref={virtuosoRef}
            className="absolute inset-0"
            totalCount={totalCount}
            increaseViewportBy={200}
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
                    <div className="flex items-baseline gap-2 mb-2.5">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
                        <span className="text-[15px] font-semibold text-primary">
                          PilotSpace Agent
                        </span>
                      </span>
                    </div>
                    {hasStreamingContent ? (
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
                    ) : (
                      <InlineStreamingIndicator
                        phase={streamingPhase}
                        activeToolName={activeToolName}
                        wordCount={wordCount}
                        thinkingStartedAt={thinkingStartedAt}
                      />
                    )}
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
