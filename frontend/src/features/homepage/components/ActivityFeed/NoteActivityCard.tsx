'use client';

/**
 * NoteActivityCard (H029) — Activity card for notes.
 * Shows title, project badge, topics, word count, AI annotation preview, timestamp.
 */

import { useRouter } from 'next/navigation';
import { FileText, Sparkles, AlertTriangle, ListTodo } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import type { ActivityCardNote } from '../../types';
import { MAX_ANNOTATION_PREVIEW_LENGTH } from '../../constants';

interface NoteActivityCardProps {
  card: ActivityCardNote;
  workspaceSlug: string;
}

const ANNOTATION_ICONS = {
  suggestion: Sparkles,
  warning: AlertTriangle,
  issue_candidate: ListTodo,
} as const;

export function NoteActivityCard({ card, workspaceSlug }: NoteActivityCardProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/${workspaceSlug}/notes/${card.id}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  const annotation = card.latest_annotation;
  const truncatedAnnotation = annotation
    ? annotation.content.length > MAX_ANNOTATION_PREVIEW_LENGTH
      ? `${annotation.content.slice(0, MAX_ANNOTATION_PREVIEW_LENGTH)}…`
      : annotation.content
    : null;

  const AnnotationIcon = annotation ? ANNOTATION_ICONS[annotation.type] : null;

  return (
    <article
      role="article"
      aria-label={`Note: ${card.title}, updated ${formatDistanceToNow(new Date(card.updated_at), { addSuffix: true })}`}
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'group relative flex h-[160px] cursor-pointer flex-col rounded-md',
        'border border-border-subtle bg-card p-4',
        'motion-safe:transition-all motion-safe:duration-200',
        'hover:-translate-y-0.5 hover:shadow-warm-md',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
      )}
    >
      {/* Header: icon + title + pin */}
      <div className="flex items-start gap-2">
        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <h3 className="line-clamp-1 flex-1 text-sm font-medium text-foreground">
          {card.title || 'Untitled'}
        </h3>
        {card.is_pinned && (
          <Badge variant="secondary" className="shrink-0 text-xs">
            Pinned
          </Badge>
        )}
      </div>

      {/* Meta: project + topics + word count */}
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {card.project && (
          <Badge variant="secondary" className="text-xs">
            {card.project.identifier}
          </Badge>
        )}
        {card.topics?.slice(0, 3).map((topic) => (
          <Badge key={topic} variant="outline" className="text-xs">
            {topic}
          </Badge>
        ))}
        <span className="ml-auto text-xs tabular-nums text-muted-foreground">
          {card.word_count.toLocaleString()} words
        </span>
      </div>

      {/* AI annotation preview */}
      {annotation && truncatedAnnotation && AnnotationIcon && (
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="mt-auto flex items-center gap-1.5 rounded-sm bg-ai-muted px-2 py-1">
              <AnnotationIcon className="h-3 w-3 shrink-0 text-ai" aria-hidden="true" />
              <span className="line-clamp-1 text-sm text-ai">{truncatedAnnotation}</span>
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <div className="flex items-start gap-2">
              <AnnotationIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ai" aria-hidden="true" />
              <p className="text-sm">{annotation.content}</p>
            </div>
          </TooltipContent>
        </Tooltip>
      )}

      {/* Timestamp (bottom-right when no annotation) */}
      <div className={cn('flex items-center justify-end', !annotation && 'mt-auto')}>
        <time dateTime={card.updated_at} className="text-xs text-muted-foreground">
          {formatDistanceToNow(new Date(card.updated_at), { addSuffix: true })}
        </time>
      </div>
    </article>
  );
}
