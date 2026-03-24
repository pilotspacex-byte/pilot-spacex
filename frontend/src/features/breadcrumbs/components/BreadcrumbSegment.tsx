'use client';

import { ChevronRight } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { BreadcrumbSegment as BreadcrumbSegmentType } from '../types';

interface BreadcrumbSegmentProps {
  segment: BreadcrumbSegmentType;
  onNavigate: (sibling: { id: string; name: string; path: string }) => void;
}

export function BreadcrumbSegment({ segment, onNavigate }: BreadcrumbSegmentProps) {
  return (
    <div className="flex items-center">
      {!segment.isFirst && (
        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground/60" />
      )}
      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            className={`max-w-[160px] truncate rounded px-1 py-0.5 text-xs hover:bg-accent ${
              segment.isLast ? 'font-semibold text-foreground' : 'text-muted-foreground'
            }`}
          >
            {segment.label}
          </button>
        </PopoverTrigger>
        {segment.siblings.length > 0 && (
          <PopoverContent align="start" className="w-56 p-1" sideOffset={4}>
            <div className="flex flex-col">
              {segment.siblings.map((sibling) => (
                <button
                  key={sibling.id}
                  type="button"
                  className={`w-full truncate rounded px-2 py-1 text-left text-xs hover:bg-accent ${
                    sibling.name === segment.label
                      ? 'font-medium text-foreground'
                      : 'text-muted-foreground'
                  }`}
                  onClick={() => onNavigate(sibling)}
                >
                  {sibling.name}
                </button>
              ))}
            </div>
          </PopoverContent>
        )}
      </Popover>
    </div>
  );
}
