'use client';

/**
 * RelatedIssuesSection - Displays related issues with relation type badges and status pills.
 *
 * Part of AI Context panel: shows issues linked by blocks/relates/blocked_by relations.
 *
 * @example
 * ```tsx
 * <RelatedIssuesSection items={aiContext.relatedIssues} />
 * ```
 */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ContextRelatedIssue } from '@/stores/ai/AIContextStore';

// ============================================================================
// Types
// ============================================================================

export interface RelatedIssuesSectionProps {
  items: ContextRelatedIssue[];
}

// ============================================================================
// Helpers
// ============================================================================

function getRelationBadgeStyles(type: string): { label: string; className: string } {
  switch (type) {
    case 'blocks':
      return { label: 'BLOCKS', className: 'bg-destructive/10 text-destructive' };
    case 'relates':
      return { label: 'RELATES', className: 'bg-ai/10 text-ai' };
    case 'blocked_by':
      return {
        label: 'BLOCKED BY',
        className: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400',
      };
    default:
      return { label: type.toUpperCase(), className: 'bg-muted text-muted-foreground' };
  }
}

function getStatusPillStyles(stateGroup: string): string {
  switch (stateGroup) {
    case 'backlog':
    case 'unstarted':
      return 'bg-muted text-muted-foreground';
    case 'started':
      return 'bg-primary/10 text-primary';
    case 'completed':
      return 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400';
    case 'cancelled':
      return 'bg-destructive/10 text-destructive';
    default:
      return 'bg-muted text-muted-foreground';
  }
}

// ============================================================================
// Item Component
// ============================================================================

function RelatedIssueRow({ item }: { item: ContextRelatedIssue }) {
  const relation = getRelationBadgeStyles(item.relationType);
  const statusStyles = getStatusPillStyles(item.stateGroup);

  return (
    <div className="flex flex-col gap-1.5 rounded-lg border p-3 transition-colors hover:bg-muted/50">
      <div className="flex items-center gap-2">
        <Badge
          variant="secondary"
          className={cn('text-[10px] font-semibold px-1.5 py-0', relation.className)}
        >
          {relation.label}
        </Badge>
        <span className="font-mono text-xs text-muted-foreground">{item.identifier}</span>
        <Badge variant="secondary" className={cn('ml-auto text-[10px] px-1.5 py-0', statusStyles)}>
          {item.status}
        </Badge>
      </div>
      <p className="text-sm font-medium leading-snug">{item.title}</p>
      {item.summary && <p className="text-xs text-muted-foreground line-clamp-2">{item.summary}</p>}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function RelatedIssuesSection({ items }: RelatedIssuesSectionProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <RelatedIssueRow key={item.issueId} item={item} />
      ))}
    </div>
  );
}

export default RelatedIssuesSection;
