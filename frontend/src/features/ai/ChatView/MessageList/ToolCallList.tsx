/**
 * ToolCallList - Display a group of tool calls with parallel indication.
 *
 * Renders ToolCallCard for each tool call. When multiple tools execute
 * in parallel, shows a "Parallel (N tools)" header with GitBranch icon
 * and a left border container. Single tool calls render directly.
 *
 * @module features/ai/ChatView/MessageList/ToolCallList
 */

import { memo, useState } from 'react';
import { GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ToolCallCard } from './ToolCallCard';
import { ToolStepTimeline } from './ToolStepTimeline';
import type { ToolCall } from '@/stores/ai/types/conversation';

interface ToolCallListProps {
  toolCalls: ToolCall[];
  className?: string;
}

export const ToolCallList = memo<ToolCallListProps>(({ toolCalls, className }) => {
  const [showTimeline, setShowTimeline] = useState(false);

  if (toolCalls.length === 0) return null;

  const isParallel = toolCalls.length > 1;
  const hasTimeline = toolCalls.length >= 3;

  return (
    <div className={cn('space-y-2', className)}>
      {isParallel && (
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground px-1">
          <GitBranch className="h-3 w-3 text-ai" />
          <span>Parallel ({toolCalls.length} tools)</span>
        </div>
      )}

      <div className={cn('space-y-2', isParallel && 'border-l-2 border-l-ai/20 pl-2')}>
        {toolCalls.map((toolCall) => (
          <ToolCallCard key={toolCall.id} toolCall={toolCall} />
        ))}
      </div>

      {hasTimeline && (
        <>
          <button
            type="button"
            className="text-xs text-ai hover:underline"
            onClick={() => setShowTimeline((prev) => !prev)}
          >
            {showTimeline ? 'Hide steps' : 'View steps'}
          </button>

          {showTimeline && <ToolStepTimeline toolCalls={toolCalls} />}
        </>
      )}
    </div>
  );
});

ToolCallList.displayName = 'ToolCallList';
