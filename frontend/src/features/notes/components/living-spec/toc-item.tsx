'use client';

/**
 * TocItem - Single entry in the Table of Contents panel
 * Phase 78: Living Specs sidebar
 *
 * React.memo — safe for use adjacent to TipTap (NOT observer).
 */
import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TocItemProps {
  text: string;
  level: 1 | 2 | 3;
  isActive: boolean;
  onClick: () => void;
}

/** Left padding by heading level (UI-SPEC: h1=0, h2=8px, h3=16px) */
const LEVEL_INDENT: Record<1 | 2 | 3, string> = {
  1: 'pl-0',
  2: 'pl-2',   // 8px
  3: 'pl-4',   // 16px
};

export const TocItem = React.memo(function TocItem({
  text,
  level,
  isActive,
  onClick,
}: TocItemProps) {
  return (
    <a
      role="link"
      aria-current={isActive ? 'location' : undefined}
      onClick={(e) => {
        e.preventDefault();
        onClick();
      }}
      href="#"
      className={cn(
        'flex min-h-[32px] cursor-pointer items-center rounded-sm px-1',
        'text-[14px] leading-[1.5] transition-colors duration-150 motion-safe:ease-out',
        'hover:bg-muted/50 hover:text-foreground',
        LEVEL_INDENT[level],
        isActive
          ? 'text-primary font-semibold'
          : 'font-normal text-muted-foreground'
      )}
    >
      <span className="truncate">{text}</span>
    </a>
  );
});

TocItem.displayName = 'TocItem';
