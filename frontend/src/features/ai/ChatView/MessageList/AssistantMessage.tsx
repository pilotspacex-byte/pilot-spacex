/**
 * AssistantMessage - Display assistant messages with markdown support
 * Minimal design: no avatar, primary-colored agent name
 */

import { memo, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import type { ChatMessage, ContentBlock } from '@/stores/ai/types/conversation';
import type { ExtractedIssue } from '@/stores/ai/types/events';
import { useStore } from '@/stores';
import { aiApi } from '@/services/api/ai';
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
  const store = useStore();
  const [isCreatingIssues, setIsCreatingIssues] = useState(false);

  const handleCreateIssues = useCallback(
    async (selectedIndices: number[]) => {
      const noteId = store.aiStore.pilotSpace.noteContext?.noteId;
      const workspaceId = store.workspaceStore.currentWorkspace?.id;

      if (!noteId || !workspaceId) {
        toast.error('Missing context', {
          description: 'Could not determine note or workspace. Please try again.',
        });
        return;
      }

      const allIssues = (message.structuredResult?.data?.issues ?? []) as ExtractedIssue[];
      const selected = selectedIndices
        .map((i) => allIssues[i])
        .filter((issue): issue is ExtractedIssue => issue !== undefined);

      if (selected.length === 0) return;

      setIsCreatingIssues(true);
      try {
        const result = await aiApi.createExtractedIssues(
          workspaceId,
          noteId,
          selected.map((issue) => ({
            title: issue.title,
            description: issue.description || undefined,
            priority: issue.priority,
            type: issue.issue_type,
            source_block_id: issue.source_block_id,
          }))
        );
        toast.success(`Created ${result.count} issue${result.count !== 1 ? 's' : ''}`, {
          description: 'Issues have been created and linked to the note.',
        });
      } catch (error) {
        toast.error('Failed to create issues', {
          description: error instanceof Error ? error.message : 'An unexpected error occurred.',
        });
      } finally {
        setIsCreatingIssues(false);
      }
    },
    [store, message.structuredResult]
  );

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
                      block.durationMs ??
                      (isLastThinkingBlock(block, message.contentBlocks!)
                        ? message.thinkingDurationMs
                        : undefined)
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
                      block.durationMs ??
                      (block === message.thinkingBlocks![message.thinkingBlocks!.length - 1]
                        ? message.thinkingDurationMs
                        : undefined)
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
            onCreateIssues={
              message.structuredResult.schemaType === 'extraction_result'
                ? handleCreateIssues
                : undefined
            }
            isCreatingIssues={isCreatingIssues}
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
