'use client';

/**
 * EditorToolbar - Top toolbar for note editor with AI controls
 * Per T129: Ghost text toggle with Sparkles icon
 */
import { observer } from 'mobx-react-lite';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent } from '@/components/ui/tooltip';
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
 * EditorToolbar with AI feature toggles
 *
 * Features:
 * - Ghost text AI suggestions toggle
 * - Future: Auto-format, spell check, etc.
 *
 * @example
 * ```tsx
 * <EditorToolbar
 *   noteId={noteId}
 *   workspaceId={workspaceId}
 * />
 * ```
 */
export const EditorToolbar = observer(function EditorToolbar({
  noteId: _noteId,
  workspaceId: _workspaceId,
  className,
}: EditorToolbarProps) {
  const aiStore = getAIStore();

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 py-2 border-b border-border bg-background',
        className
      )}
      role="toolbar"
      aria-label="Editor toolbar"
    >
      {/* AI Features Section */}
      <div className="flex items-center gap-2">
        <Tooltip>
          <TooltipContent side="bottom" className="max-w-xs">
            <p className="font-medium">Ghost Text AI Suggestions</p>
            <p className="text-xs text-muted-foreground mt-1">
              Get real-time AI-powered text completions while typing. Press Tab to accept, Esc to
              dismiss.
            </p>
          </TooltipContent>
        </Tooltip>
      </div>

      <Separator orientation="vertical" className="h-6" />

      {/* Future: Additional editor controls */}
      <div className="flex items-center gap-1">{/* Placeholder for future features */}</div>

      {/* Status indicator when loading */}
      {aiStore.ghostText.isLoading && (
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          <div className="flex gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-ai animate-bounce [animation-delay:0ms]" />
            <div className="h-1.5 w-1.5 rounded-full bg-ai animate-bounce [animation-delay:150ms]" />
            <div className="h-1.5 w-1.5 rounded-full bg-ai animate-bounce [animation-delay:300ms]" />
          </div>
          <span>Thinking...</span>
        </div>
      )}

      {/* Error indicator */}
      {aiStore.ghostText.error && (
        <div className="ml-auto flex items-center gap-2 text-xs text-destructive">
          <span>{aiStore.ghostText.error}</span>
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
