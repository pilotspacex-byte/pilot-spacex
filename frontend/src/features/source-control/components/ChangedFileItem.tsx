'use client';

import { Circle, Plus, Minus, ArrowRight, type LucideIcon } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import type { ChangedFile } from '@/features/source-control/types';

interface ChangedFileItemProps {
  file: ChangedFile;
  onToggleStage: (path: string) => void;
  onSelect: (path: string) => void;
  isSelected: boolean;
}

const STATUS_CONFIG: Record<
  ChangedFile['status'],
  { icon: LucideIcon; color: string; label: string }
> = {
  modified: { icon: Circle, color: 'text-orange-500', label: 'M' },
  added: { icon: Plus, color: 'text-green-500', label: 'A' },
  deleted: { icon: Minus, color: 'text-red-500', label: 'D' },
  renamed: { icon: ArrowRight, color: 'text-blue-500', label: 'R' },
};

/**
 * Single changed file row in the SCM panel.
 *
 * Shows a checkbox for staging, a status icon, and the file path
 * (basename in bold, directory in muted). NOT wrapped in observer()
 * -- receives all data via props.
 */
export function ChangedFileItem({
  file,
  onToggleStage,
  onSelect,
  isSelected,
}: ChangedFileItemProps) {
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
        className="h-3.5 w-3.5"
        aria-label={file.staged ? `Unstage ${basename}` : `Stage ${basename}`}
      />
      <StatusIcon className={cn('h-3.5 w-3.5 shrink-0', config.color)} />
      <span className="truncate min-w-0 flex-1">
        <span className="font-medium">{basename}</span>
        {directory && <span className="text-muted-foreground ml-1 text-xs">{directory}</span>}
      </span>
      <span className={cn('text-[10px] font-mono shrink-0', config.color)}>{config.label}</span>
    </div>
  );
}
