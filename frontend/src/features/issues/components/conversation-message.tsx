/**
 * Conversation Message component.
 *
 * Displays individual message with:
 * - User vs AI styling
 * - Markdown rendering
 * - Code block syntax highlighting
 * - Copy button for AI responses
 * - Timestamp
 *
 * @see specs/004-mvp-agents-build/tasks/P22-P25-T178-T222.md#T212
 */
'use client';

import * as React from 'react';
import { format } from 'date-fns';
import { Copy, Check, User, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ConversationMessage as ConversationMessageType } from '@/stores/ai/ConversationStore';

export interface ConversationMessageProps {
  message: ConversationMessageType;
  isStreaming?: boolean;
}

/**
 * Message bubble component with role-specific styling.
 *
 * @example
 * ```tsx
 * <ConversationMessage
 *   message={{ role: 'user', content: 'Hello', ... }}
 * />
 * ```
 */
export function ConversationMessage({ message, isStreaming = false }: ConversationMessageProps) {
  const [copied, setCopied] = React.useState(false);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn('flex gap-3 group', isUser ? 'flex-row-reverse' : 'flex-row')}
      role="article"
      aria-label={`${isUser ? 'User' : 'AI'} message`}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser ? 'bg-primary/10 text-primary' : 'bg-ai/10 text-ai border border-ai/20'
        )}
        aria-hidden="true"
      >
        {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
      </div>

      {/* Message content */}
      <div className={cn('flex-1 max-w-[80%]', isUser && 'flex flex-col items-end')}>
        {/* Message bubble */}
        <div
          className={cn(
            'rounded-lg px-4 py-2 break-words',
            isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground border border-border',
            isStreaming && 'animate-pulse'
          )}
        >
          <MessageContent content={message.content} />
        </div>

        {/* Metadata row */}
        <div
          className={cn(
            'flex items-center gap-2 mt-1 text-xs text-muted-foreground',
            isUser && 'flex-row-reverse'
          )}
        >
          {/* Timestamp */}
          <time dateTime={message.created_at}>{format(new Date(message.created_at), 'HH:mm')}</time>

          {/* Copy button for AI messages */}
          {!isUser && (
            <Button
              variant="ghost"
              size="icon-sm"
              className="opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={handleCopy}
              aria-label="Copy message"
            >
              {copied ? <Check className="h-3 w-3 text-green-600" /> : <Copy className="h-3 w-3" />}
            </Button>
          )}

          {/* Streaming indicator */}
          {isStreaming && (
            <span className="inline-flex items-center gap-1">
              <span className="animate-pulse">●</span>
              <span>Typing</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Render message content with basic markdown support.
 */
function MessageContent({ content }: { content: string }) {
  // Split content by code blocks
  const parts = content.split(/(```[\s\S]*?```|`[^`]+`)/g);

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      {parts.map((part, index) => {
        // Inline code
        if (part.startsWith('`') && part.endsWith('`') && !part.startsWith('```')) {
          return (
            <code key={index} className="bg-muted/50 px-1.5 py-0.5 rounded text-sm font-mono">
              {part.slice(1, -1)}
            </code>
          );
        }

        // Code block
        if (part.startsWith('```')) {
          const lines = part.slice(3, -3).split('\n');
          // Language can be extracted from first line if needed
          const code = lines.slice(1).join('\n');

          return (
            <pre key={index} className="bg-muted/50 rounded-md p-4 overflow-x-auto my-2">
              <code className="text-sm font-mono">{code}</code>
            </pre>
          );
        }

        // Regular text with line breaks
        return (
          <span key={index} className="whitespace-pre-wrap">
            {part}
          </span>
        );
      })}
    </div>
  );
}
