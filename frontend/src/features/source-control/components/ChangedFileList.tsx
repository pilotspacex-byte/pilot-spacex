'use client';

import { useState } from 'react';
import { ChevronDown, Plus, Minus } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { ChangedFileItem } from './ChangedFileItem';
import type { ChangedFile } from '@/features/source-control/types';

interface ChangedFileListProps {
  title: string;
  files: ChangedFile[];
  onToggleStage: (path: string) => void;
  onStageAll?: () => void;
  onUnstageAll?: () => void;
  onSelect: (path: string) => void;
  selectedPath: string | null;
}

/**
 * Collapsible section of changed files (staged or unstaged).
 *
 * Shows a header with file count badge, expand/collapse toggle,
 * and a bulk stage/unstage action button.
 */
export function ChangedFileList({
  title,
  files,
  onToggleStage,
  onStageAll,
  onUnstageAll,
  onSelect,
  selectedPath,
}: ChangedFileListProps) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <div className="flex items-center justify-between px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
        <CollapsibleTrigger className="flex items-center gap-1 hover:text-foreground transition-colors">
          <ChevronDown
            className={cn('h-3.5 w-3.5 transition-transform', !isOpen && '-rotate-90')}
          />
          <span>{title}</span>
          <Badge variant="secondary" className="ml-1 h-4 min-w-[16px] px-1 text-[10px]">
            {files.length}
          </Badge>
        </CollapsibleTrigger>

        <div className="flex items-center gap-0.5">
          {onStageAll && files.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={onStageAll}
              title="Stage All"
            >
              <Plus className="h-3 w-3" />
            </Button>
          )}
          {onUnstageAll && files.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={onUnstageAll}
              title="Unstage All"
            >
              <Minus className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      <CollapsibleContent>
        {files.length === 0 ? (
          <p className="px-2 py-2 text-xs text-muted-foreground italic">No changes</p>
        ) : (
          <div className="space-y-px">
            {files.map((file) => (
              <ChangedFileItem
                key={file.path}
                file={file}
                onToggleStage={onToggleStage}
                onSelect={onSelect}
                isSelected={selectedPath === file.path}
              />
            ))}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
