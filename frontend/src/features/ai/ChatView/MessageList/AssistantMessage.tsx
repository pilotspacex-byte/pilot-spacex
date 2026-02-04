/**
 * AssistantMessage - Display assistant messages with markdown support
 * Follows shadcn/ui AI message component pattern
 */

import { memo } from 'react';
import { Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { ToolCallList } from './ToolCallList';
import { ThinkingBlock } from './ThinkingBlock';
import { StructuredResultCard } from './StructuredResultCard';
import { MarkdownContent } from './MarkdownContent';
import { CitationList } from './CitationList';

interface AssistantMessageProps {
  message: ChatMessage;
  className?: string;
}

export const AssistantMessage = memo<AssistantMessageProps>(({ message, className }) => {
  return (
    <div
      className={cn('flex items-start gap-3 px-4 py-3 bg-muted/30', className)}
      data-testid="message-assistant"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-ai-muted">
        <Bot className="h-4 w-4 text-ai" />
      </div>

      <div className="flex-1 space-y-3 overflow-hidden">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold">PilotSpace Agent</span>
          <time className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
        </div>

        {/* G-12: Render multiple thinking blocks for interleaved thinking, fallback to single */}
        {message.thinkingBlocks && message.thinkingBlocks.length > 0
          ? message.thinkingBlocks.map((block) => (
              <ThinkingBlock
                key={block.blockIndex}
                content={block.content}
                durationMs={
                  block === message.thinkingBlocks![message.thinkingBlocks!.length - 1]
                    ? message.thinkingDurationMs
                    : undefined
                }
                isStreaming={false}
              />
            ))
          : message.thinkingContent && (
              <ThinkingBlock
                content={message.thinkingContent}
                durationMs={message.thinkingDurationMs}
                isStreaming={false}
              />
            )}

        {message.content && <MarkdownContent content={message.content} />}

        {message.structuredResult && (
          <StructuredResultCard
            schemaType={message.structuredResult.schemaType}
            data={message.structuredResult.data}
          />
        )}

        {message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}

        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallList toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  );
});

AssistantMessage.displayName = 'AssistantMessage';
