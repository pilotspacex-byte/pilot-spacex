'use client';

/**
 * EditorToolbar - Top toolbar for note editor with AI controls
 * Per T129: Ghost text toggle with Sparkles icon
 */
import { observer } from 'mobx-react-lite';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { getAIStore } from '@/stores/ai';

export interface EditorToolbarProps {
  /** Note ID for context */
  noteId: string;
  /** Workspace ID for AI settings */
  workspaceId?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * EditorToolbar — AI status indicators only.
 * Content editing is handled by the Pilot Space Agent via content_update SSE events.
 * Text formatting is available through the floating SelectionToolbar.
 */
export const EditorToolbar = observer(function EditorToolbar({
  noteId: _noteId,
  workspaceId: _workspaceId,
  className,
}: EditorToolbarProps) {
  const aiStore = getAIStore();
  const isLoading = aiStore.ghostText.isLoading;
  const error = aiStore.ghostText.error;

  // Hide toolbar entirely when no AI activity
  if (!isLoading && !error) return null;

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 py-1.5 border-b border-border bg-background',
        className
      )}
      role="status"
      aria-label="AI status"
      aria-live="polite"
    >
      {isLoading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="flex gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-ai animate-bounce [animation-delay:0ms]" />
            <div className="h-1.5 w-1.5 rounded-full bg-ai animate-bounce [animation-delay:150ms]" />
            <div className="h-1.5 w-1.5 rounded-full bg-ai animate-bounce [animation-delay:300ms]" />
          </div>
          <span>AI thinking...</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-xs text-destructive">
          <span>{error}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              aiStore.ghostText.abort();
            }}
            className="h-6 px-2 text-xs"
          >
            Dismiss
          </Button>
        </div>
      )}
    </div>
  );
});

export default EditorToolbar;
