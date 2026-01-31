/**
 * ContextIndicator - Shows active context (note, issue, project)
 * Allows dismissing context
 */

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { FileText, ListTodo, FolderOpen, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { NoteContext, IssueContext, ProjectContext } from '../types';

interface ContextIndicatorProps {
  noteContext?: NoteContext | null;
  issueContext?: IssueContext | null;
  projectContext?: ProjectContext | null;
  onClearNoteContext?: () => void;
  onClearIssueContext?: () => void;
  onClearProjectContext?: () => void;
  className?: string;
}

export const ContextIndicator = memo<ContextIndicatorProps>(
  ({
    noteContext,
    issueContext,
    projectContext,
    onClearNoteContext,
    onClearIssueContext,
    onClearProjectContext,
    className,
  }) => {
    const hasContext = noteContext || issueContext || projectContext;

    if (!hasContext) return null;

    return (
      <div
        data-testid="context-indicator"
        className={cn('flex flex-wrap items-center gap-2', className)}
      >
        <span className="text-xs text-muted-foreground">Context:</span>

        {noteContext && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge variant="secondary" className="gap-1.5">
                <FileText className="h-3 w-3" />
                <span className="truncate max-w-[200px]">
                  Note: {noteContext.noteTitle || noteContext.noteId.slice(0, 8)}
                  {noteContext.selectedBlockIds && noteContext.selectedBlockIds.length > 0 && (
                    <span className="ml-1 text-muted-foreground">
                      ({noteContext.selectedBlockIds.length}{' '}
                      {noteContext.selectedBlockIds.length === 1 ? 'block' : 'blocks'})
                    </span>
                  )}
                </span>
                {onClearNoteContext && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-3 w-3 p-0 hover:bg-transparent"
                    onClick={onClearNoteContext}
                  >
                    <X className="h-2.5 w-2.5" />
                    <span className="sr-only">Clear note context</span>
                  </Button>
                )}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p>
                {noteContext.selectedBlockIds && noteContext.selectedBlockIds.length > 0
                  ? `AI will use the ${noteContext.selectedBlockIds.length} selected block${noteContext.selectedBlockIds.length === 1 ? '' : 's'} as context for your request`
                  : 'AI will use the entire note content as context for your request'}
              </p>
            </TooltipContent>
          </Tooltip>
        )}

        {issueContext && (
          <Badge variant="secondary" className="gap-1.5">
            <ListTodo className="h-3 w-3" />
            <span className="truncate max-w-[120px]">{issueContext.title}</span>
            {onClearIssueContext && (
              <Button
                variant="ghost"
                size="icon"
                className="h-3 w-3 p-0 hover:bg-transparent"
                onClick={onClearIssueContext}
              >
                <X className="h-2.5 w-2.5" />
                <span className="sr-only">Clear issue context</span>
              </Button>
            )}
          </Badge>
        )}

        {projectContext && (
          <Badge variant="secondary" className="gap-1.5">
            <FolderOpen className="h-3 w-3" />
            <span className="truncate max-w-[120px]">{projectContext.name}</span>
            {onClearProjectContext && (
              <Button
                variant="ghost"
                size="icon"
                className="h-3 w-3 p-0 hover:bg-transparent"
                onClick={onClearProjectContext}
              >
                <X className="h-2.5 w-2.5" />
                <span className="sr-only">Clear project context</span>
              </Button>
            )}
          </Badge>
        )}
      </div>
    );
  }
);

ContextIndicator.displayName = 'ContextIndicator';
