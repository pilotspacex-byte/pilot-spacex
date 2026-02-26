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
import type { AttachmentContext } from '@/types/attachments';
import { AttachmentPill } from './AttachmentPill';

interface ContextIndicatorProps {
  noteContext?: NoteContext | null;
  issueContext?: IssueContext | null;
  projectContext?: ProjectContext | null;
  onClearNoteContext?: () => void;
  onClearIssueContext?: () => void;
  onClearProjectContext?: () => void;
  attachments?: AttachmentContext[];
  onRemoveAttachment?: (id: string) => void;
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
    attachments,
    onRemoveAttachment,
    className,
  }) => {
    const hasStructuredContext = noteContext || issueContext || projectContext;
    const hasAttachments = (attachments?.length ?? 0) > 0;
    const hasContext = hasStructuredContext || hasAttachments;

    if (!hasContext) return null;

    const label = hasStructuredContext ? 'Context:' : 'Attachments:';

    return (
      <div
        data-testid="context-indicator"
        className={cn('flex flex-wrap items-center gap-2', className)}
      >
        <span className="text-xs text-muted-foreground">{label}</span>

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

        {attachments?.map((att) => (
          <AttachmentPill
            key={att.id}
            attachment={att}
            onRemove={() => onRemoveAttachment?.(att.id)}
          />
        ))}
      </div>
    );
  }
);

ContextIndicator.displayName = 'ContextIndicator';
