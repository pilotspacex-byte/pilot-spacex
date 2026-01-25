'use client';

/**
 * ContextItemList - Display related items (issues, notes, pages) in AI context.
 *
 * T212: Shows list of related items with icons, relevance badges,
 * excerpts on hover/expand, and navigation.
 */

import * as React from 'react';
import { FileText, Bug, BookOpen, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';

// ============================================================================
// Types
// ============================================================================

export type RelatedItemType = 'issue' | 'note' | 'page';

export interface RelatedItem {
  /** Unique identifier */
  id: string;
  /** Display title */
  title: string;
  /** Item type */
  type: RelatedItemType;
  /** Issue identifier (for issues only) */
  identifier?: string;
  /** Relevance score (0-1) */
  relevance: number;
  /** Brief excerpt */
  excerpt?: string;
  /** URL for navigation */
  url?: string;
}

export interface ContextItemListProps {
  /** List title */
  title: string;
  /** Related items */
  items: RelatedItem[];
  /** Item type filter */
  type: RelatedItemType;
  /** Maximum items to show before "Show more" */
  maxDisplay?: number;
  /** Called when item is clicked */
  onItemClick?: (item: RelatedItem) => void;
  /** Whether the section is collapsible */
  collapsible?: boolean;
  /** Default collapsed state */
  defaultCollapsed?: boolean;
  /** Additional class name */
  className?: string;
}

// ============================================================================
// Type Configuration
// ============================================================================

interface TypeConfig {
  icon: React.ElementType;
  label: string;
  color: string;
}

const typeConfig: Record<RelatedItemType, TypeConfig> = {
  issue: {
    icon: Bug,
    label: 'Issue',
    color: 'text-orange-600 dark:text-orange-400',
  },
  note: {
    icon: FileText,
    label: 'Note',
    color: 'text-blue-600 dark:text-blue-400',
  },
  page: {
    icon: BookOpen,
    label: 'Page',
    color: 'text-green-600 dark:text-green-400',
  },
};

// ============================================================================
// Relevance Badge
// ============================================================================

function RelevanceBadge({ relevance }: { relevance: number }) {
  const percentage = Math.round(relevance * 100);
  let variant: 'default' | 'secondary' | 'outline' = 'outline';
  let colorClass = 'text-muted-foreground';

  if (percentage >= 80) {
    variant = 'default';
    colorClass = '';
  } else if (percentage >= 60) {
    variant = 'secondary';
    colorClass = '';
  }

  return (
    <Badge variant={variant} className={cn('text-xs', colorClass)}>
      {percentage}%
    </Badge>
  );
}

// ============================================================================
// Item Row
// ============================================================================

interface ItemRowProps {
  item: RelatedItem;
  onClick?: (item: RelatedItem) => void;
}

function ItemRow({ item, onClick }: ItemRowProps) {
  const config = typeConfig[item.type];
  const Icon = config.icon;
  const [showExcerpt, setShowExcerpt] = React.useState(false);

  const handleClick = () => {
    if (item.url) {
      window.open(item.url, '_blank');
    }
    onClick?.(item);
  };

  const content = (
    <div
      className={cn(
        'group flex items-start gap-3 rounded-lg border p-3 transition-colors',
        (item.url || onClick) && 'cursor-pointer hover:bg-muted/50'
      )}
      onClick={handleClick}
      role={item.url || onClick ? 'button' : undefined}
      tabIndex={item.url || onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <Icon className={cn('size-4 shrink-0 mt-0.5', config.color)} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {item.identifier && (
            <span className="text-xs font-mono text-muted-foreground">{item.identifier}</span>
          )}
          <span className="text-sm font-medium truncate">{item.title}</span>
        </div>

        {/* Excerpt (expanded) */}
        {showExcerpt && item.excerpt && (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{item.excerpt}</p>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <RelevanceBadge relevance={item.relevance} />
        {item.url && (
          <ExternalLink className="size-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        )}
      </div>
    </div>
  );

  // Wrap with tooltip if excerpt exists and not expanded
  if (item.excerpt && !showExcerpt) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              onMouseEnter={() => setShowExcerpt(true)}
              onMouseLeave={() => setShowExcerpt(false)}
            >
              {content}
            </div>
          </TooltipTrigger>
          <TooltipContent side="right" className="max-w-xs">
            <p className="text-xs">{item.excerpt}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return content;
}

// ============================================================================
// Main Component
// ============================================================================

export function ContextItemList({
  title,
  items,
  type,
  maxDisplay = 5,
  onItemClick,
  collapsible = true,
  defaultCollapsed = false,
  className,
}: ContextItemListProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);
  const [showAll, setShowAll] = React.useState(false);

  // Filter items by type
  const filteredItems = items.filter((item) => item.type === type);

  if (filteredItems.length === 0) {
    return null;
  }

  // Sort by relevance
  const sortedItems = [...filteredItems].sort((a, b) => b.relevance - a.relevance);
  const displayedItems = showAll ? sortedItems : sortedItems.slice(0, maxDisplay);
  const hasMore = sortedItems.length > maxDisplay;

  const config = typeConfig[type];
  const TypeIcon = config.icon;

  const header = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {collapsible &&
          (isCollapsed ? <ChevronRight className="size-4" /> : <ChevronDown className="size-4" />)}
        <TypeIcon className={cn('size-4', config.color)} />
        <span className="text-sm font-medium">{title}</span>
        <Badge variant="secondary" className="text-xs">
          {filteredItems.length}
        </Badge>
      </div>
    </div>
  );

  const content = (
    <div className="space-y-2 mt-3">
      {displayedItems.map((item) => (
        <ItemRow key={item.id} item={item} onClick={onItemClick} />
      ))}

      {hasMore && !showAll && (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            setShowAll(true);
          }}
          className="w-full text-muted-foreground"
        >
          Show {sortedItems.length - maxDisplay} more
        </Button>
      )}

      {showAll && hasMore && (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            setShowAll(false);
          }}
          className="w-full text-muted-foreground"
        >
          Show less
        </Button>
      )}
    </div>
  );

  if (collapsible) {
    return (
      <Collapsible
        open={!isCollapsed}
        onOpenChange={(open) => setIsCollapsed(!open)}
        className={className}
      >
        <CollapsibleTrigger className="w-full text-left">{header}</CollapsibleTrigger>
        <CollapsibleContent>{content}</CollapsibleContent>
      </Collapsible>
    );
  }

  return (
    <div className={className}>
      {header}
      {content}
    </div>
  );
}

export default ContextItemList;
