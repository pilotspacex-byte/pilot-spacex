/**
 * StreamingContent - Streaming text with enhanced ThinkingBlock.
 *
 * Renders thinking block (with its own indicator) and streaming
 * markdown content. ThinkingBlock handles its own visual state,
 * so no generic spinner is needed here.
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { ThinkingBlock } from './ThinkingBlock';
import { MarkdownContent } from './MarkdownContent';
import { Loader2 } from 'lucide-react';

interface StreamingContentProps {
  content: string;
  /** Thinking content being streamed (from extended thinking) */
  thinkingContent?: string;
  /** Whether thinking is actively streaming */
  isThinking?: boolean;
  /** Elapsed thinking duration in ms (computed by parent to avoid impure render) */
  thinkingDurationMs?: number;
  /** Timestamp (ms) when thinking started, for live timer */
  thinkingStartedAt?: number | null;
  /** Whether the stream was interrupted by user */
  interrupted?: boolean;
  className?: string;
}

export const StreamingContent = memo<StreamingContentProps>(
  ({
    content,
    thinkingContent,
    isThinking,
    thinkingDurationMs,
    thinkingStartedAt,
    interrupted,
    className,
  }) => {
    return (
      <div className={cn('space-y-2', className)}>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
          <span>{isThinking ? 'Thinking...' : 'Streaming...'}</span>
        </div>

        {thinkingContent && (
          <ThinkingBlock
            content={thinkingContent}
            durationMs={thinkingDurationMs}
            isStreaming={!!isThinking}
            thinkingStartedAt={thinkingStartedAt}
            interrupted={interrupted}
          />
        )}

        {content && <MarkdownContent content={content} isStreaming />}
      </div>
    );
  }
);

StreamingContent.displayName = 'StreamingContent';
