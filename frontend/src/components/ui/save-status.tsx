'use client';

import { Check, AlertCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

type SaveStatusState = 'idle' | 'saving' | 'saved' | 'error';

interface SaveStatusProps {
  status: SaveStatusState;
  className?: string;
  errorMessage?: string;
}

export function SaveStatus({ status, className, errorMessage }: SaveStatusProps) {
  if (status === 'idle') return null;

  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={
        status === 'saving'
          ? 'Saving'
          : status === 'saved'
            ? 'Saved'
            : errorMessage || 'Save failed'
      }
      className={cn('inline-flex items-center transition-opacity duration-300', className)}
    >
      {status === 'saving' && <Loader2 className="size-3.5 animate-spin text-muted-foreground" />}
      {status === 'saved' && <Check className="size-3.5 text-primary" />}
      {status === 'error' && <AlertCircle className="size-3.5 text-destructive" />}
    </span>
  );
}
