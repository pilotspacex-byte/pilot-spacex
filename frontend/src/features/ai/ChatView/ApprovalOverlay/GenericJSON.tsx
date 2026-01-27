/**
 * GenericJSON - Display JSON payload with syntax highlighting
 */

import { memo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface GenericJSONProps {
  payload: Record<string, unknown>;
  className?: string;
}

export const GenericJSON = memo<GenericJSONProps>(({ payload, className }) => {
  return (
    <ScrollArea className={cn('h-[300px] rounded border', className)}>
      <pre className="p-4 text-xs font-mono">{JSON.stringify(payload, null, 2)}</pre>
    </ScrollArea>
  );
});

GenericJSON.displayName = 'GenericJSON';
