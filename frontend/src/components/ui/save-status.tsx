'use client';

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
      className={cn(
        'text-xs transition-opacity duration-300',
        status === 'saving' && 'text-foreground-muted animate-pulse',
        status === 'saved' && 'text-primary',
        status === 'error' && 'text-destructive',
        className
      )}
    >
      {status === 'saving' && 'Saving...'}
      {status === 'saved' && 'Saved'}
      {status === 'error' && (errorMessage || 'Save failed')}
    </span>
  );
}
