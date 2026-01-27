/**
 * MessageGroup - Group consecutive messages by role
 * Optimizes rendering and provides better visual hierarchy
 */

import { memo } from 'react';
import type { ChatMessage } from '@/stores/ai/types/conversation';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';

interface MessageGroupProps {
  messages: ChatMessage[];
  userName?: string;
  userAvatar?: string;
}

export const MessageGroup = memo<MessageGroupProps>(({ messages, userName, userAvatar }) => {
  if (messages.length === 0) return null;

  const role = messages[0]?.role;
  if (!role) return null;

  return (
    <div className="space-y-0">
      {messages.map((message) => {
        if (role === 'user') {
          return (
            <UserMessage
              key={message.id}
              message={message}
              userName={userName}
              userAvatar={userAvatar}
            />
          );
        }

        if (role === 'assistant') {
          return <AssistantMessage key={message.id} message={message} />;
        }

        // System messages (if any)
        return (
          <div key={message.id} className="px-4 py-2 text-xs text-center text-muted-foreground">
            {message.content}
          </div>
        );
      })}
    </div>
  );
});

MessageGroup.displayName = 'MessageGroup';
