'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ContextRelatedDoc } from '@/stores/ai/AIContextStore';

export interface RelatedDocsSectionProps {
  items: ContextRelatedDoc[];
}

function getDocBadgeStyles(type: string): { label: string; className: string } {
  switch (type) {
    case 'note':
      return { label: 'NOTE', className: 'bg-primary/10 text-primary' };
    case 'adr':
      return {
        label: 'ADR',
        className: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400',
      };
    case 'spec':
      return { label: 'SPEC', className: 'bg-ai/10 text-ai' };
    default:
      return { label: type.toUpperCase(), className: 'bg-muted text-muted-foreground' };
  }
}

export function RelatedDocsSection({ items }: RelatedDocsSectionProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {items.map((item, index) => {
        const badge = getDocBadgeStyles(item.docType);

        return (
          <div
            key={`${item.docType}-${item.title}-${index}`}
            className={cn(
              'flex items-start gap-3 rounded-lg p-3',
              'hover:bg-muted/50 transition-colors'
            )}
          >
            <Badge
              variant="secondary"
              className={cn('shrink-0 text-[10px] font-semibold px-1.5 py-0', badge.className)}
            >
              {badge.label}
            </Badge>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{item.title}</p>
              {item.summary && (
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{item.summary}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default RelatedDocsSection;
