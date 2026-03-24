'use client';

/**
 * EditorToolbar - Mode toggle bar with file metadata.
 *
 * Shows file name, language badge, read-only indicator,
 * Edit/Preview toggle, and unsaved changes indicator.
 *
 * Height: 36px (tab bar height from UI-SPEC).
 * Background: --background-subtle.
 */

import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { EditorMode } from './types';

interface EditorToolbarProps {
  mode: EditorMode;
  onModeChange: (mode: EditorMode) => void;
  fileName: string;
  isDirty: boolean;
  isReadOnly: boolean;
  language: string;
}

export function EditorToolbar({
  mode,
  onModeChange,
  fileName,
  isDirty,
  isReadOnly,
  language,
}: EditorToolbarProps) {
  return (
    <div className="flex h-9 items-center bg-background-subtle border-b border-border-subtle px-4">
      {/* Left: file info */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className="text-sm font-sans text-foreground truncate">{fileName}</span>
        <Badge variant="outline" className="text-xs">
          {language}
        </Badge>
        {isReadOnly && (
          <Badge variant="secondary" className="text-xs">
            Read-only
          </Badge>
        )}
      </div>

      {/* Center: Edit/Preview toggle */}
      <div className="flex items-center gap-0">
        <button
          type="button"
          onClick={() => onModeChange('edit')}
          className={cn(
            'px-3 py-1 text-sm transition-colors relative',
            mode === 'edit'
              ? 'text-primary after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-primary'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => onModeChange('preview')}
          className={cn(
            'px-3 py-1 text-sm transition-colors relative',
            mode === 'preview'
              ? 'text-primary after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-primary'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          Preview
        </button>
      </div>

      {/* Right: dirty indicator */}
      <div className="flex items-center justify-end flex-1">
        {isDirty && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className="h-2 w-2 rounded-full bg-primary animate-in zoom-in-50 duration-150"
                  aria-label="Unsaved changes"
                />
              </TooltipTrigger>
              <TooltipContent>
                <p>Unsaved changes</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
}
