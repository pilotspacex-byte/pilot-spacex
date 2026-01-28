/**
 * AssistantMessage - Display assistant messages with markdown support
 * Follows shadcn/ui AI message component pattern
 */

import { memo } from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { ToolCallList } from './ToolCallList';

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
      <Avatar className="h-8 w-8 shrink-0 bg-gradient-to-br from-purple-500 to-pink-500">
        <AvatarFallback className="bg-transparent">
          <Sparkles className="h-4 w-4 text-white" />
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 space-y-3 overflow-hidden">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold">PilotSpace AI</span>
          <time className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </time>
        </div>

        {message.content && (
          <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
            {message.content}
          </div>
        )}

        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallList toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  );
});

AssistantMessage.displayName = 'AssistantMessage';
