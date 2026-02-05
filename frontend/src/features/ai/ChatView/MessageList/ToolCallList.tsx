/**
 * ToolCallList - Display a group of tool calls.
 *
 * Renders ToolCallCard for each tool call in a compact list.
 * Claude.ai style: no "Parallel" header, just sequential inline rows.
 *
 * @module features/ai/ChatView/MessageList/ToolCallList
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { ToolCallCard } from './ToolCallCard';
import type { ToolCall } from '@/stores/ai/types/conversation';

interface ToolCallListProps {
  toolCalls: ToolCall[];
  className?: string;
}

export const ToolCallList = memo<ToolCallListProps>(({ toolCalls, className }) => {
  if (toolCalls.length === 0) return null;

  return (
    <div className={cn('space-y-1', className)}>
      {toolCalls.map((toolCall) => (
        <ToolCallCard key={toolCall.id} toolCall={toolCall} />
      ))}
    </div>
  );
});

ToolCallList.displayName = 'ToolCallList';
