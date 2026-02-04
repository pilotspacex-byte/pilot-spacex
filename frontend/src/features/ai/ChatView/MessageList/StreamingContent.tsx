/**
 * StreamingContent - Animated streaming text indicator
 * Follows shadcn/ui AI loader/shimmer pattern
 */

import { memo } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ThinkingBlock } from './ThinkingBlock';
import { MarkdownContent } from './MarkdownContent';

interface StreamingContentProps {
  content: string;
  /** Thinking content being streamed (from extended thinking) */
  thinkingContent?: string;
  /** Whether thinking is actively streaming */
  isThinking?: boolean;
  /** Elapsed thinking duration in ms (computed by parent to avoid impure render) */
  thinkingDurationMs?: number;
  className?: string;
}

export const StreamingContent = memo<StreamingContentProps>(
  ({ content, thinkingContent, isThinking, thinkingDurationMs, className }) => {
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
          />
        )}

        {content && <MarkdownContent content={content} isStreaming />}
      </div>
    );
  }
);

StreamingContent.displayName = 'StreamingContent';
