/**
 * CitationList - Display source citations from AI responses
 * Renders inline citation markers and a reference list (G-05)
 */

import { memo } from 'react';
import { ExternalLink, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '@/stores/ai/types/conversation';

type Citation = NonNullable<ChatMessage['citations']>[number];

interface CitationListProps {
  citations: Citation[];
  className?: string;
}

const CitationItem = memo<{ citation: Citation; index: number }>(({ citation, index }) => {
  const Icon = citation.sourceType === 'url' ? ExternalLink : FileText;

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="shrink-0 flex h-4 w-4 items-center justify-center rounded-full bg-ai-muted text-ai text-[10px] font-semibold">
        {index + 1}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1 text-muted-foreground">
          <Icon className="h-3 w-3 shrink-0" />
          <span className="font-medium truncate">{citation.sourceTitle || citation.sourceId}</span>
        </div>
        {citation.citedText && (
          <p className="mt-0.5 text-muted-foreground/70 line-clamp-2 italic">
            &ldquo;{citation.citedText}&rdquo;
          </p>
        )}
      </div>
    </div>
  );
});

CitationItem.displayName = 'CitationItem';

export const CitationList = memo<CitationListProps>(({ citations, className }) => {
  if (citations.length === 0) return null;

  return (
    <div className={cn('space-y-2 border-t border-border/50 pt-2', className)}>
      <span className="text-xs font-medium text-muted-foreground">
        Sources ({citations.length})
      </span>
      <div className="space-y-1.5">
        {citations.map((citation, idx) => (
          <CitationItem
            key={`${citation.sourceId}-${citation.startIndex ?? idx}`}
            citation={citation}
            index={idx}
          />
        ))}
      </div>
    </div>
  );
});

CitationList.displayName = 'CitationList';
