/**
 * Conversation Panel for multi-turn AI chat.
 *
 * Chat-style interface with:
 * - Message history display
 * - Streaming AI responses
 * - Message input with suggested prompts
 * - Session management
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T211
 */
'use client';

import * as React from 'react';
import { observer } from 'mobx-react-lite';
import { useStore } from '@/stores';
import { ConversationMessageList } from './conversation-message-list';
import { ConversationInput } from './conversation-input';
import { SuggestedPrompts } from './suggested-prompts';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ConversationPanelProps {
  issueId: string;
  className?: string;
}

/**
 * Conversation Panel for multi-turn AI chat within issue context.
 *
 * @example
 * ```tsx
 * <ConversationPanel issueId="123e4567-e89b-12d3-a456-426614174000" />
 * ```
 */
export const ConversationPanel = observer(function ConversationPanel({
  issueId,
  className,
}: ConversationPanelProps) {
  const { aiStore } = useStore();
  const { conversation } = aiStore;

  // Initialize session on mount
  React.useEffect(() => {
    if (conversation.currentIssueId !== issueId || !conversation.isSessionActive) {
      conversation.startSession(issueId);
    }
  }, [issueId, conversation]);

  const handleSendMessage = (content: string) => {
    conversation.sendMessage(content);
  };

  const handlePromptClick = (prompt: string) => {
    conversation.sendMessage(prompt);
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Error state */}
      {conversation.error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{conversation.error}</AlertDescription>
        </Alert>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-hidden">
        <ConversationMessageList
          messages={conversation.messages}
          isStreaming={conversation.isStreaming}
          streamContent={conversation.currentStreamContent}
        />
      </div>

      {/* Suggested prompts (show when no messages) */}
      {conversation.messageCount === 0 && !conversation.isStreaming && (
        <div className="px-4 pb-2">
          <SuggestedPrompts onPromptClick={handlePromptClick} />
        </div>
      )}

      {/* Input */}
      <div className="border-t bg-background">
        <ConversationInput
          onSend={handleSendMessage}
          disabled={conversation.isStreaming || !conversation.isSessionActive}
          placeholder={
            conversation.isSessionActive
              ? 'Ask about implementation, tests, or architecture...'
              : 'Starting session...'
          }
        />
      </div>
    </div>
  );
});
