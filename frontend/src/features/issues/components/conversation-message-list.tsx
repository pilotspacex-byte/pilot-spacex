/**
 * Conversation Message List with auto-scroll.
 *
 * Displays:
 * - Message history
 * - Streaming indicator
 * - Auto-scroll to bottom on new messages
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T211
 */
'use client';

import * as React from 'react';
import { ConversationMessage } from './conversation-message';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { ConversationMessage as ConversationMessageType } from '@/stores/ai/ConversationStore';

export interface ConversationMessageListProps {
  messages: ConversationMessageType[];
  isStreaming: boolean;
  streamContent: string;
}

/**
 * Scrollable message list with auto-scroll behavior.
 */
export function ConversationMessageList({
  messages,
  isStreaming,
  streamContent,
}: ConversationMessageListProps) {
  const endRef = React.useRef<HTMLDivElement>(null);
  const scrollAreaRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming content
  React.useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages.length, streamContent]);

  return (
    <ScrollArea ref={scrollAreaRef} className="h-full">
      <div className="p-4 space-y-4">
        {messages.map((message) => (
          <ConversationMessage key={message.id} message={message} />
        ))}

        {/* Streaming message */}
        {isStreaming && streamContent && (
          <ConversationMessage
            message={{
              id: 'streaming',
              role: 'assistant',
              content: streamContent,
              created_at: new Date().toISOString(),
            }}
            isStreaming
          />
        )}

        {/* Auto-scroll anchor */}
        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
}
