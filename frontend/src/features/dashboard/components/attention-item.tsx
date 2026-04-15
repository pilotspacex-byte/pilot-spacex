'use client';

/**
 * AttentionItem — Clickable card row for the attention feed.
 *
 * Navigates to PR (external), issue detail (internal), or approval (internal)
 * based on the item type. Uses <a> for external links and Next.js Link for internal.
 * Min height 44px per WCAG 2.5.5.
 *
 * Phase 77 — Implementation Dashboard (DSH-03, UIX-04)
 */
import * as React from 'react';
import Link from 'next/link';
import { ExternalLink, AlertTriangle, Clock } from 'lucide-react';
import type { AttentionItem as AttentionItemType } from '../types';
import { cn } from '@/lib/utils';

export interface AttentionItemProps {
  item: AttentionItemType;
  workspaceSlug: string;
  className?: string;
}

const ITEM_ICONS: Record<AttentionItemType['type'], React.ElementType> = {
  pr_ready: ExternalLink,
  blocked: AlertTriangle,
  pending_approval: Clock,
};

const ITEM_ICON_COLORS: Record<AttentionItemType['type'], string> = {
  pr_ready: 'text-[hsl(var(--primary))]',
  blocked: 'text-[hsl(var(--destructive))]',
  pending_approval: 'text-[hsl(var(--state-in-progress))]',
};

const baseRowClass = cn(
  'flex items-center gap-3 min-h-[44px] px-3 py-2.5 w-full',
  'cursor-pointer hover:bg-muted/60 transition-colors duration-150',
  'text-left rounded-md',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1'
);

export const AttentionItem = React.memo(function AttentionItem({
  item,
  workspaceSlug,
  className,
}: AttentionItemProps) {
  const Icon = ITEM_ICONS[item.type];
  const iconColor = ITEM_ICON_COLORS[item.type];

  const content = (
    <>
      <Icon
        className={cn('h-4 w-4 shrink-0', iconColor)}
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 min-w-0">
          {item.issueIdentifier && (
            <span className="text-[12px] font-semibold text-muted-foreground shrink-0">
              {item.issueIdentifier}
            </span>
          )}
          {item.issueTitle && (
            <span className="text-[14px] font-normal text-foreground truncate">
              {item.issueTitle}
            </span>
          )}
        </div>
      </div>
    </>
  );

  if (item.type === 'pr_ready' && item.prUrl) {
    return (
      <li role="listitem" className={className}>
        <a
          href={item.prUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={baseRowClass}
          aria-label={`Open PR for ${item.issueIdentifier ?? ''} ${item.issueTitle ?? ''} in new tab`}
        >
          {content}
        </a>
      </li>
    );
  }

  const href = `/${workspaceSlug}/issues/${item.issueId}`;

  return (
    <li role="listitem" className={className}>
      <Link
        href={href}
        className={baseRowClass}
        aria-label={`View issue ${item.issueIdentifier ?? ''} ${item.issueTitle ?? ''}`}
      >
        {content}
      </Link>
    </li>
  );
});

AttentionItem.displayName = 'AttentionItem';
