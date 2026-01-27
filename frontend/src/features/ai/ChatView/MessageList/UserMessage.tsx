/**
 * UserMessage - Display user messages in chat
 * Follows shadcn/ui AI message component pattern
 */

import { memo } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';

interface UserMessageProps {
  message: ChatMessage;
  userName?: string;
  userAvatar?: string;
  className?: string;
}

export const UserMessage = memo<UserMessageProps>(
  ({ message, userName = 'You', userAvatar, className }) => {
    const initials = userName
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);

    return (
      <div className={cn('flex items-start gap-3 px-4 py-3', className)}>
        <Avatar className="h-8 w-8 shrink-0">
          {userAvatar && <AvatarImage src={userAvatar} alt={userName} />}
          <AvatarFallback className="bg-primary text-primary-foreground text-xs">
            {initials}
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 space-y-2 overflow-hidden">
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-semibold">{userName}</span>
            <time className="text-xs text-muted-foreground">
              {message.timestamp.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </time>
          </div>

          <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
            {message.content}
          </div>
        </div>
      </div>
    );
  }
);

UserMessage.displayName = 'UserMessage';
