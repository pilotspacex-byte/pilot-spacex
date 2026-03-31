'use client';

import { useState } from 'react';
import { ChevronDown, Plus, Minus, Circle, ArrowRight } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import type { ChangedFile } from '../git-types';

// ─── Status config (warm diff colors per CONTEXT.md) ─────────────────────────

const STATUS_CONFIG: Record<
  ChangedFile['status'],
  { icon: LucideIcon; color: string; label: string }
> = {
  // Modified = amber (in-progress amber from Monaco palette)
  modified: { icon: Circle, color: 'text-amber-500', label: 'M' },
  // Added = teal (primary teal from Monaco palette)
  added: { icon: Plus, color: 'text-teal-500', label: 'A' },
  // Deleted = red (warm red)
  deleted: { icon: Minus, color: 'text-red-500', label: 'D' },
  // Renamed = blue (todo blue)
  renamed: { icon: ArrowRight, color: 'text-blue-500', label: 'R' },
};

// ─── ChangedFileItem ──────────────────────────────────────────────────────────

interface ChangedFileItemProps {
  file: ChangedFile;
  onToggleStage: (path: string) => void;
  onSelect: (path: string) => void;
  isSelected: boolean;
}

/**
 * Single changed file row in the SCM panel.
 *
 * Shows a checkbox for staging, a status icon, and the file path
 * (basename bold, directory in muted). Receives all data via props (not observer).
 */
function ChangedFileItem({ file, onToggleStage, onSelect, isSelected }: ChangedFileItemProps) {
  const config = STATUS_CONFIG[file.status];
  const StatusIcon = config.icon;
  const basename = file.path.split('/').pop() ?? file.path;
  const directory = file.path.includes('/') ? file.path.slice(0, file.path.lastIndexOf('/')) : '';

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 px-2 py-0.5 cursor-pointer rounded-sm text-sm hover:bg-accent/50 group',
        isSelected && 'bg-accent'
      )}
      onClick={() => onSelect(file.path)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(file.path);
        }
      }}
    >
      <Checkbox
        checked={file.staged}
        onCheckedChange={() => onToggleStage(file.path)}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
        className="h-3.5 w-3.5"
        aria-label={file.staged ? `Unstage ${basename}` : `Stage ${basename}`}
      />
      <StatusIcon className={cn('h-3.5 w-3.5 shrink-0', config.color)} />
      <span className="truncate min-w-0 flex-1">
        <span className="font-medium">{basename}</span>
        {directory && (
          <span className="text-muted-foreground ml-1 text-xs">{directory}</span>
        )}
      </span>
      <span className={cn('text-[10px] font-mono shrink-0', config.color)}>{config.label}</span>
    </div>
  );
}

// ─── ChangedFileList ──────────────────────────────────────────────────────────

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
 *
 * Uses warm diff colors per CONTEXT.md:
 * - Modified = amber
 * - Added = teal
 * - Deleted = red
 * - Renamed = blue
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
