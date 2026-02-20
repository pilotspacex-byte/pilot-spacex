'use client';

/**
 * CollapsibleSection - Collapsible wrapper for issue detail page sections.
 *
 * Provides progressive disclosure with a chevron toggle, optional icon,
 * and a count badge. Uses shadcn Collapsible primitives for accessibility.
 */

import * as React from 'react';
import { ChevronRight } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';

export interface CollapsibleSectionProps {
  /** Section heading text */
  title: string;
  /** Optional leading icon rendered before the title */
  icon?: React.ReactNode;
  /** Whether the section is expanded on first render */
  defaultOpen?: boolean;
  /** Optional badge count displayed before the chevron */
  count?: number;
  children: React.ReactNode;
}

export function CollapsibleSection({
  title,
  icon,
  defaultOpen = true,
  count,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen);

  // Sync open state when defaultOpen transitions to true (async data load)
  React.useEffect(() => {
    if (defaultOpen) setIsOpen(true);
  }, [defaultOpen]);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <button
          className={cn(
            'flex w-full items-center gap-2 py-3 text-sm font-medium',
            'text-foreground hover:text-foreground/80',
            'focus-visible:outline-none focus-visible:ring-2',
            'focus-visible:ring-ring focus-visible:ring-offset-2',
            'rounded-md'
          )}
        >
          {icon}
          <span>{title}</span>
          {count !== undefined && count > 0 && (
            <span className="mr-2 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground tabular-nums">
              {count}
            </span>
          )}
          <ChevronRight
            className={cn(
              'ml-auto size-4 text-muted-foreground motion-safe:transition-transform duration-150',
              isOpen && 'rotate-90'
            )}
          />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="pb-2">{children}</div>
      </CollapsibleContent>
    </Collapsible>
  );
}
