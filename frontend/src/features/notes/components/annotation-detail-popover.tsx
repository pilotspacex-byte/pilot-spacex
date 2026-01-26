/**
 * Annotation Detail Popover - Full annotation content with actions
 * T170: Shows detailed content, suggested text, and apply/dismiss actions
 *
 * Features:
 * - Full annotation content
 * - Suggested text preview
 * - References list
 * - Apply and dismiss actions
 */
'use client';

import { observer } from 'mobx-react-lite';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Check, X, ExternalLink } from 'lucide-react';
import { useStores } from '@/stores/RootStore';
import type { NoteAnnotation } from '@/types';

interface AnnotationDetailPopoverProps {
  annotation: NoteAnnotation;
  children: React.ReactNode;
  onApply?: () => void;
  onDismiss?: () => void;
}

export const AnnotationDetailPopover = observer(function AnnotationDetailPopover({
  annotation,
  children,
  onApply,
  onDismiss,
}: AnnotationDetailPopoverProps) {
  const { ai } = useStores();

  const handleApply = () => {
    if (annotation.aiMetadata?.suggestedText) {
      onApply?.();
    }
    ai.marginAnnotation.applyAnnotation(annotation.id);
  };

  const handleDismiss = () => {
    ai.marginAnnotation.dismissAnnotation(annotation.id);
    onDismiss?.();
  };

  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        className="w-96 max-h-[500px] overflow-y-auto"
        align="end"
        side="left"
        sideOffset={8}
      >
        <div className="space-y-4">
          {/* Header */}
          <div>
            <h4 className="font-semibold text-base">
              {annotation.aiMetadata?.title ?? 'Annotation'}
            </h4>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-muted-foreground capitalize">{annotation.type}</span>
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">
                {Math.round(annotation.confidence * 100)}% confidence
              </span>
            </div>
          </div>

          {/* Content */}
          <div>
            <p className="text-sm text-muted-foreground leading-relaxed">{annotation.content}</p>
          </div>

          {/* Suggested Text */}
          {annotation.aiMetadata?.suggestedText && (
            <div className="bg-muted rounded-md p-3 border">
              <p className="text-xs text-muted-foreground font-medium mb-2">
                Suggested replacement:
              </p>
              <p className="text-sm font-mono leading-relaxed whitespace-pre-wrap">
                {annotation.aiMetadata.suggestedText}
              </p>
            </div>
          )}

          {/* References */}
          {annotation.aiMetadata?.references && annotation.aiMetadata.references.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground font-medium mb-2">References:</p>
              <ul className="space-y-1.5">
                {annotation.aiMetadata.references.map(
                  (ref: { title: string; url: string }, i: number) => (
                    <li key={i}>
                      <a
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1"
                      >
                        {ref.title}
                        <ExternalLink className="w-3 h-3" aria-hidden="true" />
                      </a>
                    </li>
                  )
                )}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleDismiss}
              aria-label="Dismiss annotation"
            >
              <X className="w-4 h-4 mr-1" aria-hidden="true" />
              Dismiss
            </Button>
            {annotation.aiMetadata?.suggestedText && (
              <Button size="sm" onClick={handleApply} aria-label="Apply suggestion">
                <Check className="w-4 h-4 mr-1" aria-hidden="true" />
                Apply
              </Button>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
});
