/**
 * AssistantMessage - Display assistant messages with markdown support
 * Minimal design: no avatar, primary-colored agent name
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';
import type { ChatMessage, ContentBlock } from '@/stores/ai/types/conversation';
import { ToolCallList } from './ToolCallList';
import { ThinkingBlock } from './ThinkingBlock';
import { StructuredResultCard } from './StructuredResultCard';
import { MarkdownContent } from './MarkdownContent';
import { CitationList } from './CitationList';

/** Check if a thinking block is the last thinking block in the content blocks sequence */
function isLastThinkingBlock(block: ContentBlock, blocks: ContentBlock[]): boolean {
  if (block.type !== 'thinking') return false;
  for (let i = blocks.length - 1; i >= 0; i--) {
    if (blocks[i]!.type === 'thinking') {
      return blocks[i]! === block;
    }
  }
  return false;
}

interface AssistantMessageProps {
  message: ChatMessage;
  className?: string;
}

export const AssistantMessage = memo<AssistantMessageProps>(({ message, className }) => {
  return (
    <div className={cn('px-4 py-3', className)} data-testid="message-assistant">
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-sm font-semibold text-primary">PilotSpace Agent</span>
        <time className="text-xs text-muted-foreground">
          {message.timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </time>
      </div>

      <div className="space-y-3 overflow-hidden">

        {/* Ordered content blocks: render in server-received order when available */}
        {message.contentBlocks ? (
          <>
            {message.contentBlocks.map((block, idx) => {
              if (block.type === 'thinking') {
                return (
                  <ThinkingBlock
                    key={`thinking-${block.blockIndex}`}
                    content={block.content}
                    durationMs={
                      isLastThinkingBlock(block, message.contentBlocks!)
                        ? message.thinkingDurationMs
                        : undefined
                    }
                    isStreaming={false}
                  />
                );
              }
              if (block.type === 'text') {
                return <MarkdownContent key={`text-${idx}`} content={block.content} />;
              }
              if (block.type === 'tool_call') {
                const tc = message.toolCalls?.find((t) => t.id === block.toolCallId);
                return tc ? (
                  <ToolCallList key={`tool-${block.toolCallId}`} toolCalls={[tc]} />
                ) : null;
              }
              return null;
            })}
          </>
        ) : (
          <>
            {/* Fallback: grouped rendering for messages without contentBlocks */}
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

            {message.toolCalls && message.toolCalls.length > 0 && (
              <ToolCallList toolCalls={message.toolCalls} />
            )}
          </>
        )}

        {message.structuredResult && (
          <StructuredResultCard
            schemaType={message.structuredResult.schemaType}
            data={message.structuredResult.data}
          />
        )}

        {message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}
      </div>
    </div>
  );
});

AssistantMessage.displayName = 'AssistantMessage';
