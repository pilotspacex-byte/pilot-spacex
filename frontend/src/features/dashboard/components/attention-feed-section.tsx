'use client';

/**
 * AttentionFeedSection — Three-category attention feed for the Implementation Dashboard.
 *
 * Categories: PRs Ready for Review, Blocked Issues, Pending Approvals.
 * Each category shows "None right now" when empty (per copywriting contract).
 * Wraps in ScrollArea when total items > 5.
 *
 * Phase 77 — Implementation Dashboard (DSH-03, UIX-04)
 */
import * as React from 'react';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AttentionItem } from './attention-item';
import type { AttentionItem as AttentionItemType } from '../types';
import { cn } from '@/lib/utils';

export interface AttentionFeedSectionProps {
  attentionItems: AttentionItemType[];
  workspaceSlug: string;
  className?: string;
}

interface CategoryConfig {
  key: AttentionItemType['type'];
  label: string;
}

const CATEGORIES: CategoryConfig[] = [
  { key: 'pr_ready', label: 'PRs Ready for Review' },
  { key: 'blocked', label: 'Blocked Issues' },
  { key: 'pending_approval', label: 'Pending Approvals' },
];

export const AttentionFeedSection = React.memo(function AttentionFeedSection({
  attentionItems,
  workspaceSlug,
  className,
}: AttentionFeedSectionProps) {
  const categorized = React.useMemo(() => {
    const map: Record<string, AttentionItemType[]> = {
      pr_ready: [],
      blocked: [],
      pending_approval: [],
    };
    for (const item of attentionItems) {
      if (map[item.type]) {
        map[item.type].push(item);
      }
    }
    return map;
  }, [attentionItems]);

  const totalItems = attentionItems.length;

  const feedContent = (
    <ul
      role="list"
      className={cn('flex flex-col gap-0', className)}
    >
      {CATEGORIES.map((category, index) => {
        const items = categorized[category.key] ?? [];

        return (
          <React.Fragment key={category.key}>
            {index > 0 && <Separator className="my-3" />}
            <div className="flex flex-col gap-1">
              {/* Section header */}
              <p className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wide px-3 py-1">
                {category.label}
              </p>
              {items.length > 0 ? (
                items.map((item) => (
                  <AttentionItem
                    key={item.issueId + item.type}
                    item={item}
                    workspaceSlug={workspaceSlug}
                  />
                ))
              ) : (
                <p className="text-[14px] font-normal text-muted-foreground px-3 py-2">
                  None right now
                </p>
              )}
            </div>
          </React.Fragment>
        );
      })}
    </ul>
  );

  if (totalItems > 5) {
    return (
      <ScrollArea className="max-h-[320px]">
        {feedContent}
      </ScrollArea>
    );
  }

  return feedContent;
});

AttentionFeedSection.displayName = 'AttentionFeedSection';
