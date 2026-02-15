/**
 * UserMessage - Display user messages in chat
 * Minimal design: light-gray background, no avatar
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';

interface UserMessageProps {
  message: ChatMessage;
  userName?: string;
  userAvatar?: string;
  className?: string;
}

export const UserMessage = memo<UserMessageProps>(({ message, userName = 'You', className }) => {
  // Hide answer protocol messages — Q&A is shown inline in the assistant message
  if (message.metadata?.isAnswerMessage) {
    return null;
  }

  return (
    <div
      className={cn('px-4 py-3 bg-muted/100 text-primary', className)}
      data-testid="message-user"
    >
      <div className="flex items-baseline gap-2 mb-1.5">
        <span className="text-[15px] font-semibold text-foreground">{userName}</span>
        <time className="text-[11px] text-muted-foreground/70">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
      </div>

      <div className="prose prose-sm max-w-none text-foreground dark:prose-invert leading-relaxed">
        {message.content}
      </div>
    </div>
  );
});

UserMessage.displayName = 'UserMessage';
