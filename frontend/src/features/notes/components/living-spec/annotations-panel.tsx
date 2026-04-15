'use client';

/**
 * AnnotationsPanel - Collapsible list of AI deviation and decision annotation cards
 * Phase 78: Living Specs sidebar
 *
 * React.memo — safe for use adjacent to TipTap (NOT observer).
 */
import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import type { SpecAnnotationResponse } from '@/services/api/notes';
import { DeviationCard } from './deviation-card';
import { DecisionLogCard } from './decision-log-card';

export interface AnnotationsPanelProps {
  annotations: SpecAnnotationResponse[] | undefined;
  isLoading: boolean;
  error: Error | null;
}

export const AnnotationsPanel = React.memo(function AnnotationsPanel({
  annotations,
  isLoading,
  error,
}: AnnotationsPanelProps) {
  const [open, setOpen] = React.useState(true);

  const annotationList = annotations ?? [];
  const count = annotationList.length;

  // Sort by createdAt descending (newest first)
  const sorted = React.useMemo(
    () =>
      [...annotationList].sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      ),
    [annotationList]
  );

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      {/* Section header */}
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center justify-between group"
          aria-label={open ? 'Collapse AI annotations' : 'Expand AI annotations'}
        >
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-semibold leading-[1.4] uppercase tracking-wide text-muted-foreground">
              AI Annotations
            </span>
            {count > 0 && (
              <Badge
                variant="secondary"
                className="h-4 px-1.5 text-[11px] font-semibold leading-none"
              >
                {count}
              </Badge>
            )}
          </div>
          <ChevronDown
            className={`h-3.5 w-3.5 text-muted-foreground transition-transform duration-200 motion-safe:ease-out ${open ? 'rotate-0' : '-rotate-90'}`}
            aria-hidden="true"
          />
        </button>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-2">
        <div role="feed" aria-busy={isLoading} aria-label="AI annotations feed" className="space-y-2">
          {isLoading ? (
            /* Loading state — 2 skeleton cards */
            <>
              <Skeleton className="h-20 w-full rounded-md" />
              <Skeleton className="h-16 w-full rounded-md" />
            </>
          ) : error ? (
            /* Error state */
            <p className="text-[12px] font-semibold leading-[1.4] text-destructive">
              Could not load annotations. Refresh to try again.
            </p>
          ) : sorted.length === 0 ? (
            /* Empty state */
            <div className="py-1">
              <p className="text-[14px] font-normal leading-[1.5] text-foreground">
                No annotations yet
              </p>
              <p className="text-[12px] font-normal leading-[1.4] text-muted-foreground mt-0.5">
                AI will add notes here when implementation deviates from this spec.
              </p>
            </div>
          ) : (
            /* Annotation cards */
            sorted.map((annotation, idx) =>
              annotation.type === 'deviation' ? (
                <DeviationCard
                  key={`deviation-${annotation.createdAt}-${idx}`}
                  content={annotation.content}
                  issueId={annotation.issueId}
                  createdAt={annotation.createdAt}
                  prUrl={annotation.prUrl}
                />
              ) : (
                <DecisionLogCard
                  key={`decision-${annotation.createdAt}-${idx}`}
                  action={annotation.action}
                  issues={annotation.issues}
                  userId={annotation.userId}
                  createdAt={annotation.createdAt}
                  content={annotation.content}
                />
              )
            )
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
});

AnnotationsPanel.displayName = 'AnnotationsPanel';
