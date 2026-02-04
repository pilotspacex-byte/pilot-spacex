'use client';

import type * as React from 'react';
import { Copy, Check, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useCopyFeedback } from '@/features/issues/hooks/use-copy-feedback';

export interface ContextSectionProps {
  icon: React.ElementType;
  title: string;
  onCopy?: () => Promise<boolean>;
  error?: string | null;
  children: React.ReactNode;
  className?: string;
}

export function ContextSection({
  icon: Icon,
  title,
  onCopy,
  error,
  children,
  className,
}: ContextSectionProps) {
  const { copied, handleCopy } = useCopyFeedback();

  const onCopyClick = () => {
    if (onCopy) void handleCopy(onCopy);
  };

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-foreground-muted" aria-hidden="true" />
          <h3 className="text-sm font-medium">{title}</h3>
        </div>
        {onCopy && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onCopyClick}
            aria-label={`Copy ${title} section`}
          >
            {copied ? (
              <>
                <Check className="size-3.5" aria-hidden="true" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="size-3.5" aria-hidden="true" />
                <span>Copy</span>
              </>
            )}
          </Button>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
          <p>{error}</p>
        </div>
      )}
      {children}
    </div>
  );
}
