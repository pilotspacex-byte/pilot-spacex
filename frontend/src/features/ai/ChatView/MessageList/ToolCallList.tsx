/**
 * ToolCallList - Display tool calls with status indicators
 * Follows shadcn/ui AI tool component pattern
 */

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { CheckCircle2, Circle, XCircle, ChevronDown, Terminal, GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolCall } from '@/stores/ai/types/conversation';

interface ToolCallListProps {
  toolCalls: ToolCall[];
  className?: string;
}

const ToolCallItem = memo<{ toolCall: ToolCall }>(({ toolCall }) => {
  // Default to 'pending' if status is undefined
  const status = toolCall.status || 'pending';

  const StatusIcon =
    {
      pending: Circle,
      completed: CheckCircle2,
      failed: XCircle,
    }[status] || Circle;

  const statusColor =
    {
      pending: 'text-muted-foreground',
      completed: 'text-green-500',
      failed: 'text-destructive',
    }[status] || 'text-muted-foreground';

  const statusLabel =
    {
      pending: 'Pending',
      completed: 'Completed',
      failed: 'Failed',
    }[status] || 'Pending';

  return (
    <Collapsible>
      <Card className="overflow-hidden">
        <CollapsibleTrigger className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent/50 transition-colors">
          <StatusIcon className={cn('h-4 w-4 shrink-0', statusColor)} />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <Terminal className="h-3 w-3 text-muted-foreground" />
              <span className="text-sm font-mono font-medium truncate">{toolCall.name}</span>
            </div>

            {toolCall.errorMessage && (
              <p className="text-xs text-destructive mt-1 truncate">{toolCall.errorMessage}</p>
            )}
          </div>

          <Badge variant={status === 'completed' ? 'default' : 'secondary'} className="shrink-0">
            {statusLabel}
          </Badge>

          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="border-t px-4 py-3 space-y-3">
            {/* Input — show partialInput while streaming, full input when complete (G-09) */}
            {status === 'pending' && toolCall.partialInput ? (
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                  Input
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ai" />
                </span>
                <pre className="text-xs bg-muted/50 p-2 rounded overflow-x-auto opacity-70">
                  {toolCall.partialInput}
                </pre>
              </div>
            ) : Object.keys(toolCall.input).length > 0 ? (
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Input</span>
                <pre className="text-xs bg-muted/50 p-2 rounded overflow-x-auto">
                  {JSON.stringify(toolCall.input, null, 2)}
                </pre>
              </div>
            ) : null}

            {/* Output */}
            {toolCall.output !== undefined && (
              <div className="space-y-1">
                <span className="text-xs font-medium text-muted-foreground">Output</span>
                <pre className="text-xs bg-muted/50 p-2 rounded overflow-x-auto">
                  {typeof toolCall.output === 'string'
                    ? toolCall.output
                    : JSON.stringify(toolCall.output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
});

ToolCallItem.displayName = 'ToolCallItem';

export const ToolCallList = memo<ToolCallListProps>(({ toolCalls, className }) => {
  if (toolCalls.length === 0) return null;

  const isParallel = toolCalls.length > 1;

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground px-4">
        Tool Calls ({toolCalls.length}){/* G-13: Indicate parallel tool execution */}
        {isParallel && (
          <span className="inline-flex items-center gap-1 text-ai">
            <GitBranch className="h-3 w-3" />
            Parallel
          </span>
        )}
      </div>
      <div className={cn('space-y-2', isParallel && 'border-l-2 border-l-ai/20 pl-2')}>
        {toolCalls.map((toolCall) => (
          <ToolCallItem key={toolCall.id} toolCall={toolCall} />
        ))}
      </div>
    </div>
  );
});

ToolCallList.displayName = 'ToolCallList';
