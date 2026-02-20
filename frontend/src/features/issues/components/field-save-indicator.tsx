'use client';

import { observer } from 'mobx-react-lite';
import { AlertCircle, Check, Loader2 } from 'lucide-react';
import { useIssueStore } from '@/stores';

export interface FieldSaveIndicatorProps {
  fieldName: string;
}

export const FieldSaveIndicator = observer(function FieldSaveIndicator({
  fieldName,
}: FieldSaveIndicatorProps) {
  const issueStore = useIssueStore();
  const status = issueStore.getSaveStatus(fieldName);

  if (status === 'idle') return null;

  return (
    <span className="inline-flex items-center ml-1" aria-live="polite">
      {status === 'saving' && (
        <Loader2
          className="size-3 motion-safe:animate-spin text-muted-foreground"
          aria-label="Saving"
        />
      )}
      {status === 'saved' && <Check className="size-3 text-emerald-500" aria-label="Saved" />}
      {status === 'error' && (
        <AlertCircle className="size-3 text-destructive" aria-label="Save failed" role="img" />
      )}
    </span>
  );
});
