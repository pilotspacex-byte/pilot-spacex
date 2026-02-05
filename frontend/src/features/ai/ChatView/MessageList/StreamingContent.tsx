/**
 * StreamingContent - Streaming text with interleaved block ordering.
 *
 * Renders thinking, tool call, and text blocks in the order they arrive
 * from the SSE stream, matching the actual agent execution flow.
 * Falls back to grouped rendering when block order is not available.
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { ThinkingBlock } from './ThinkingBlock';
import { MarkdownContent } from './MarkdownContent';
import { ToolCallList } from './ToolCallList';
import { Loader2 } from 'lucide-react';
import type { ToolCall, ThinkingBlockEntry } from '@/stores/ai/types/conversation';

interface StreamingContentProps {
  content: string;
  /** Thinking content being streamed (from extended thinking) */
  thinkingContent?: string;
  /** Individual thinking blocks for interleaved rendering (G-07) */
  thinkingBlocks?: ThinkingBlockEntry[];
  /** Whether thinking is actively streaming */
  isThinking?: boolean;
  /** Elapsed thinking duration in ms (computed by parent to avoid impure render) */
  thinkingDurationMs?: number;
  /** Timestamp (ms) when thinking started, for live timer */
  thinkingStartedAt?: number | null;
  /** Whether the stream was interrupted by user */
  interrupted?: boolean;
  /** Pending tool calls buffered during streaming (visible before message_stop) */
  pendingToolCalls?: ToolCall[];
  /** Ordered sequence of block types from SSE stream */
  blockOrder?: Array<'thinking' | 'text' | 'tool_use'>;
  /** Per-text-block segments for ordered rendering */
  textSegments?: string[];
  className?: string;
}

export const StreamingContent = memo<StreamingContentProps>(
  ({
    content,
    thinkingContent,
    thinkingBlocks,
    isThinking,
    thinkingDurationMs,
    thinkingStartedAt,
    interrupted,
    pendingToolCalls,
    blockOrder,
    textSegments,
    className,
  }) => {
    // Render blocks in SSE arrival order when blockOrder is available
    const hasOrderedBlocks = blockOrder && blockOrder.length > 0;

    return (
      <div className={cn('space-y-2', className)}>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
          <span>{isThinking ? 'Thinking...' : 'Streaming...'}</span>
        </div>

        {hasOrderedBlocks ? (
          <OrderedStreamingBlocks
            blockOrder={blockOrder}
            thinkingBlocks={thinkingBlocks}
            textSegments={textSegments}
            pendingToolCalls={pendingToolCalls}
            isThinking={isThinking}
            thinkingDurationMs={thinkingDurationMs}
            thinkingStartedAt={thinkingStartedAt}
            interrupted={interrupted}
            streamContent={content}
          />
        ) : (
          <>
            {/* Fallback: grouped rendering for streams without blockOrder */}
            {thinkingBlocks && thinkingBlocks.length > 0
              ? thinkingBlocks.map((block, idx) => {
                  const isLastBlock = idx === thinkingBlocks.length - 1;
                  return (
                    <ThinkingBlock
                      key={block.blockIndex}
                      content={block.content}
                      durationMs={isLastBlock ? thinkingDurationMs : undefined}
                      isStreaming={isLastBlock && !!isThinking}
                      thinkingStartedAt={isLastBlock ? thinkingStartedAt : undefined}
                      interrupted={interrupted}
                    />
                  );
                })
              : thinkingContent && (
                  <ThinkingBlock
                    content={thinkingContent}
                    durationMs={thinkingDurationMs}
                    isStreaming={!!isThinking}
                    thinkingStartedAt={thinkingStartedAt}
                    interrupted={interrupted}
                  />
                )}

            {pendingToolCalls && pendingToolCalls.length > 0 && (
              <ToolCallList toolCalls={pendingToolCalls} />
            )}

            {content && <MarkdownContent content={content} isStreaming />}
          </>
        )}
      </div>
    );
  }
);

StreamingContent.displayName = 'StreamingContent';

/**
 * Renders streaming blocks in their actual SSE arrival order.
 * Uses counters to map each block type occurrence to the correct data source.
 */
const OrderedStreamingBlocks = memo<{
  blockOrder: Array<'thinking' | 'text' | 'tool_use'>;
  thinkingBlocks?: ThinkingBlockEntry[];
  textSegments?: string[];
  pendingToolCalls?: ToolCall[];
  isThinking?: boolean;
  thinkingDurationMs?: number;
  thinkingStartedAt?: number | null;
  interrupted?: boolean;
  streamContent: string;
}>(
  ({
    blockOrder,
    thinkingBlocks,
    textSegments,
    pendingToolCalls,
    isThinking,
    thinkingDurationMs,
    thinkingStartedAt,
    interrupted,
    streamContent,
  }) => {
    let thinkingIdx = 0;
    let textIdx = 0;
    let toolIdx = 0;

    const elements: React.ReactNode[] = [];

    for (let i = 0; i < blockOrder.length; i++) {
      const blockType = blockOrder[i];
      const isLastBlock = i === blockOrder.length - 1;

      if (blockType === 'thinking') {
        const block = thinkingBlocks?.[thinkingIdx];
        if (block) {
          const isLastThinking = thinkingIdx === (thinkingBlocks?.length ?? 0) - 1;
          elements.push(
            <ThinkingBlock
              key={`stream-thinking-${block.blockIndex}`}
              content={block.content}
              durationMs={isLastThinking ? thinkingDurationMs : undefined}
              isStreaming={isLastThinking && !!isThinking}
              thinkingStartedAt={isLastThinking ? thinkingStartedAt : undefined}
              interrupted={interrupted}
            />
          );
        }
        thinkingIdx++;
      } else if (blockType === 'text') {
        const segment = textSegments?.[textIdx];
        // Use the segment if available, otherwise fall back to full streamContent for last text block
        const textContent = segment ?? (isLastBlock ? streamContent : '');
        if (textContent?.trim()) {
          elements.push(
            <MarkdownContent
              key={`stream-text-${textIdx}`}
              content={textContent}
              isStreaming={isLastBlock}
            />
          );
        }
        textIdx++;
      } else if (blockType === 'tool_use') {
        const tc = pendingToolCalls?.[toolIdx];
        if (tc) {
          elements.push(<ToolCallList key={`stream-tool-${tc.id}`} toolCalls={[tc]} />);
        }
        toolIdx++;
      }
    }

    return <>{elements}</>;
  }
);

OrderedStreamingBlocks.displayName = 'OrderedStreamingBlocks';
