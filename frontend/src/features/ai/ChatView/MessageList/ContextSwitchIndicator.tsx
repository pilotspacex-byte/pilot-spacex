/**
 * ContextSwitchIndicator - Visual indicator when context changes mid-conversation
 *
 * Displayed between messages when the conversation context (note/issue) changes,
 * helping users track which content is being discussed at each point.
 */

import { ArrowRight, FileText, GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ContextInfo {
  noteId?: string;
  noteTitle?: string;
  issueId?: string;
  issueTitle?: string;
}

interface ContextSwitchIndicatorProps {
  previousContext?: ContextInfo;
  newContext: ContextInfo;
  className?: string;
}

export function ContextSwitchIndicator({
  previousContext: _previousContext,
  newContext,
  className,
}: ContextSwitchIndicatorProps) {
  // Determine what type of context we're switching to
  const isNote = !!newContext.noteId;
  const isIssue = !!newContext.issueId;

  // Get display title
  const title =
    newContext.noteTitle ||
    newContext.issueTitle ||
    (isNote ? 'Untitled note' : isIssue ? 'Issue' : 'Unknown');

  // Determine icon
  const Icon = isNote ? FileText : GitBranch;

  return (
    <div
      className={cn(
        'flex items-center gap-2 py-2 px-3 mx-4 my-2',
        'bg-ai-muted/50 rounded-lg border border-ai-border/30',
        className
      )}
    >
      <ArrowRight className="h-3.5 w-3.5 text-ai shrink-0" />
      <span className="text-xs text-muted-foreground">Context switched to</span>
      <span className="flex items-center gap-1.5 text-xs font-medium text-foreground">
        <Icon
          className={cn(
            'h-3.5 w-3.5',
            isNote ? 'text-blue-500' : 'text-purple-500'
          )}
        />
        <span className="truncate max-w-[200px]">{title}</span>
      </span>
    </div>
  );
}

ContextSwitchIndicator.displayName = 'ContextSwitchIndicator';
