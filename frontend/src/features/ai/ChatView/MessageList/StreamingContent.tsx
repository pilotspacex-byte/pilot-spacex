/**
 * StreamingContent - Animated streaming text indicator
 * Follows shadcn/ui AI loader/shimmer pattern
 */

import { memo } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StreamingContentProps {
  content: string;
  className?: string;
}

export const StreamingContent = memo<StreamingContentProps>(({ content, className }) => {
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Streaming...</span>
      </div>

      <div className="prose prose-sm max-w-none text-foreground dark:prose-invert">
        {content}
        <span className="inline-block w-1 h-4 bg-primary animate-pulse ml-0.5" />
      </div>
    </div>
  );
});

StreamingContent.displayName = 'StreamingContent';
