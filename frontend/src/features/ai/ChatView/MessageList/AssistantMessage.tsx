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

        {message.thinkingContent && (
          <ThinkingBlock
            content={message.thinkingContent}
            durationMs={message.thinkingDurationMs}
            isStreaming={false}
          />
        )}

        {message.content && (
          <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
            {message.content}
          </div>
        )}

        {message.structuredResult && (
          <StructuredResultCard
            schemaType={message.structuredResult.schemaType}
            data={message.structuredResult.data}
          />
        )}

        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallList toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  );
});

AssistantMessage.displayName = 'AssistantMessage';
